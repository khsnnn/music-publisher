from contextlib import ExitStack
import asyncio

from telegram import Bot, InputMediaAudio
from telegram.error import NetworkError, TimedOut
from telegram.request import HTTPXRequest

from config import (
    BOT_TOKEN,
    CHANNEL,
    DISCUSSION_CHAT
)
from .transcode import transcode_track


UPLOAD_CONNECT_TIMEOUT = 15
UPLOAD_READ_TIMEOUT = 180
UPLOAD_WRITE_TIMEOUT = 180
UPLOAD_POOL_TIMEOUT = 15

# Безопасный суммарный размер одной media group.
# У Bot API жёсткий потолок 50 МБ на файл и общий
# лимит на тело запроса; берём с запасом, чтобы не
# упираться и в возможные ограничения VPN/прокси.
MAX_GROUP_BYTES = 40 * 1024 * 1024
MAX_GROUP_COUNT = 10


class PayloadTooLarge(Exception):
    """
    Файл(ы) не влезают в лимит Bot API по размеру
    запроса — повторные попытки здесь бессмысленны.
    """


def get_request():
    """
    Единый профиль по умолчанию — используется для
    ВСЕХ вызовов, включая инициализацию (get_me) и
    get_updates. Таймауты короткие, чтобы при обрыве
    VPN сбой определялся за секунды, а не за минуты.
    """
    return HTTPXRequest(
        connect_timeout=10,
        read_timeout=40,
        write_timeout=20,
        pool_timeout=10,
    )


def is_payload_too_large(error):
    return "too large" in str(error).lower()


async def call_with_retries(factory, max_retries=8):
    """
    Повторяет сетевой вызов при обрывах связи.
    НЕ повторяет, если сервер ответил "тело запроса
    слишком большое" — размер от ретрая не изменится.
    """

    retries = 0

    while True:

        try:
            return await factory()

        except (NetworkError, TimedOut) as e:

            if is_payload_too_large(e):
                raise PayloadTooLarge(str(e)) from e

            retries += 1

            if retries > max_retries:
                raise

            wait = min(2 ** retries, 60)

            print(
                f"[network] {e} — "
                f"retry {retries}/{max_retries} "
                f"in {wait}s"
            )

            await asyncio.sleep(wait)


async def send_album(image_path, caption):

    bot = Bot(
        token=BOT_TOKEN,
        request=get_request()
    )

    async def attempt():

        await bot.initialize()

        with open(image_path, "rb") as photo:

            return await bot.send_photo(
                chat_id=CHANNEL,
                photo=photo,
                caption=caption,
                parse_mode="HTML",
                connect_timeout=UPLOAD_CONNECT_TIMEOUT,
                read_timeout=UPLOAD_READ_TIMEOUT,
                write_timeout=UPLOAD_WRITE_TIMEOUT,
                pool_timeout=UPLOAD_POOL_TIMEOUT,
            )

    try:
        message = await call_with_retries(attempt)

    finally:
        await bot.shutdown()

    return message.message_id


async def wait_for_discussion_message(channel_message_id, max_retries=8):

    bot = Bot(
        token=BOT_TOKEN,
        request=get_request()
    )

    try:

        await call_with_retries(
            bot.initialize,
            max_retries=max_retries
        )

        await call_with_retries(
            lambda: bot.get_updates(offset=-1),
            max_retries=max_retries
        )

        while True:

            updates = await call_with_retries(
                lambda: bot.get_updates(timeout=30),
                max_retries=max_retries
            )

            for update in updates:

                if not update.message:
                    continue

                msg = update.message

                if msg.chat.id != int(DISCUSSION_CHAT):
                    continue

                origin = msg.forward_origin

                if (
                    origin
                    and origin.message_id == channel_message_id
                ):
                    return msg.message_id

    finally:
        await bot.shutdown()


async def send_tracklist(reply_id, text):

    bot = Bot(
        token=BOT_TOKEN,
        request=get_request()
    )

    async def attempt():

        await bot.initialize()

        return await bot.send_message(
            chat_id=DISCUSSION_CHAT,
            text=text,
            reply_to_message_id=reply_id,
            parse_mode="HTML"
        )

    try:
        message = await call_with_retries(attempt)

    finally:
        await bot.shutdown()

    return message.message_id


def build_batches(
    tracks,
    max_count=MAX_GROUP_COUNT,
    max_bytes=MAX_GROUP_BYTES
):
    """
    Транскодирует лослесс-треки (см. transcode.py) и
    группирует их так, чтобы в одной media group было
    не больше max_count файлов и не больше max_bytes
    суммарно (уже после сжатия). Трек тяжелее max_bytes
    сам по себе едет в собственной "группе" из одного
    файла (отправляется через send_audio).

    Возвращает список батчей, где каждый батч — список
    пар (track, upload_path).
    """

    prepared = [
        (track, transcode_track(track.filename))
        for track in tracks
    ]

    batches = []
    current = []
    current_bytes = 0

    for track, upload_path in prepared:

        size = upload_path.stat().st_size

        if current and (
            len(current) >= max_count
            or current_bytes + size > max_bytes
        ):
            batches.append(current)
            current = []
            current_bytes = 0

        current.append((track, upload_path))
        current_bytes += size

    if current:
        batches.append(current)

    return batches


async def send_tracks(reply_id, album, cover=None):
    """
    Отправляет реальные аудиофайлы альбома
    в обсуждение (комментарии под постом).

    Группирует треки по размеру и количеству,
    чтобы не упереться в лимит Bot API на размер
    запроса (Request Entity Too Large). Одиночные
    треки (или те, что не влезли в группу) идут
    через send_audio, а не media group — Telegram
    не разрешает группы из одного файла.
    """

    bot = Bot(
        token=BOT_TOKEN,
        request=get_request()
    )

    message_ids = []
    failures = []

    try:

        await call_with_retries(bot.initialize)

        batches = build_batches(album.tracks)

        for batch in batches:

            async def attempt(batch=batch):

                with ExitStack() as stack:

                    if len(batch) == 1:

                        track, upload_path = batch[0]

                        audio_file = stack.enter_context(
                            open(upload_path, "rb")
                        )

                        thumb = None

                        if cover:
                            thumb = stack.enter_context(
                                open(cover, "rb")
                            )

                        message = await bot.send_audio(
                            chat_id=DISCUSSION_CHAT,
                            audio=audio_file,
                            title=track.title,
                            performer=album.artist,
                            duration=track.duration or None,
                            thumbnail=thumb,
                            reply_to_message_id=reply_id,
                            connect_timeout=UPLOAD_CONNECT_TIMEOUT,
                            read_timeout=UPLOAD_READ_TIMEOUT,
                            write_timeout=UPLOAD_WRITE_TIMEOUT,
                            pool_timeout=UPLOAD_POOL_TIMEOUT,
                        )

                        return [message]

                    media = []

                    for track, upload_path in batch:

                        audio_file = stack.enter_context(
                            open(upload_path, "rb")
                        )

                        thumb = None

                        if cover:
                            thumb = stack.enter_context(
                                open(cover, "rb")
                            )

                        media.append(
                            InputMediaAudio(
                                media=audio_file,
                                title=track.title,
                                performer=album.artist,
                                duration=track.duration or None,
                                thumbnail=thumb,
                            )
                        )

                    return await bot.send_media_group(
                        chat_id=DISCUSSION_CHAT,
                        media=media,
                        reply_to_message_id=reply_id,
                        connect_timeout=UPLOAD_CONNECT_TIMEOUT,
                        read_timeout=UPLOAD_READ_TIMEOUT,
                        write_timeout=UPLOAD_WRITE_TIMEOUT,
                        pool_timeout=UPLOAD_POOL_TIMEOUT,
                    )

            try:
                messages = await call_with_retries(attempt)

                message_ids.extend(
                    m.message_id for m in messages
                )

            except PayloadTooLarge:

                names = ", ".join(
                    t.filename.name for t, _ in batch
                )

                print(
                    f"[skip] Слишком большой пакет, "
                    f"пропускаю: {names}"
                )

                failures.extend(t for t, _ in batch)

    finally:
        await bot.shutdown()

    if failures:
        print(
            f"[warning] Не отправлено треков: "
            f"{len(failures)} из {len(album.tracks)}"
        )

    return message_ids
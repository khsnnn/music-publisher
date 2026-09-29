import json
from pathlib import Path

from config import CACHE_FILE



def load_cache():
    """
    Загружает список опубликованных альбомов.
    """

    if not CACHE_FILE.exists():
        return {}


    try:
        with open(
            CACHE_FILE,
            "r",
            encoding="utf-8"
        ) as f:
            return json.load(f)

    except Exception:
        return {}



def save_cache(data):
    """
    Сохраняет кэш.
    """

    CACHE_FILE.parent.mkdir(
        parents=True,
        exist_ok=True
    )


    with open(
        CACHE_FILE,
        "w",
        encoding="utf-8"
    ) as f:

        json.dump(
            data,
            f,
            ensure_ascii=False,
            indent=2
        )



def is_published(album):
    """
    Проверяет, был ли альбом опубликован.
    """

    cache = load_cache()

    return album.key in cache



def get_message_id(album):
    """
    Возвращает ID сообщения Telegram.
    """

    cache = load_cache()

    return cache.get(
        album.key
    )



def mark_published(album, message_id):
    """
    Записывает публикацию.
    """

    cache = load_cache()

    cache[album.key] = message_id

    save_cache(cache)



def remove_album(album):
    """
    Удаляет запись из кэша.
    """

    cache = load_cache()

    if album.key in cache:
        del cache[album.key]

    save_cache(cache)

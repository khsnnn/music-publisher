from pathlib import Path
import hashlib

from mutagen.flac import FLAC
from mutagen.mp3 import MP3
from mutagen.id3 import ID3

from config import Path as ConfigPath


CACHE_DIR = Path("cache/covers")


def cache_name(source: Path):
    """
    Уникальное имя для кэша.
    """

    h = hashlib.md5(
        str(source).encode()
    ).hexdigest()

    return CACHE_DIR / f"{h}.jpg"



def extract_flac_cover(path: Path):
    """
    Достает картинку из FLAC.
    """

    try:
        audio = FLAC(path)

        if not audio.pictures:
            return None

        picture = audio.pictures[0]

        output = cache_name(path)

        output.parent.mkdir(
            parents=True,
            exist_ok=True
        )

        output.write_bytes(
            picture.data
        )

        return output

    except Exception:
        return None



def extract_mp3_cover(path: Path):
    """
    Достает картинку из MP3 ID3.
    """

    try:
        audio = MP3(path)

        if not audio.tags:
            return None


        for tag in audio.tags.values():

            if tag.FrameID == "APIC":

                output = cache_name(path)

                output.parent.mkdir(
                    parents=True,
                    exist_ok=True
                )

                output.write_bytes(
                    tag.data
                )

                return output


    except Exception:
        pass


    return None



def get_embedded_cover(track_file: Path):
    """
    Универсальное извлечение.
    """

    ext = track_file.suffix.lower()


    if ext == ".flac":
        return extract_flac_cover(track_file)


    if ext == ".mp3":
        return extract_mp3_cover(track_file)


    return None



def get_album_cover(album):
    """
    Возвращает путь к обложке альбома.

    Приоритет:
    1. внешняя картинка
    2. встроенная в первый трек
    """

    if album.cover:
        return album.cover


    if not album.tracks:
        return None


    return get_embedded_cover(
        album.tracks[0].filename
    )

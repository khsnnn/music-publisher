from pathlib import Path
from mutagen import File


AUDIO_EXTENSIONS = {
    ".flac",
    ".mp3",
    ".m4a",
    ".ogg",
    ".opus",
}


def is_audio(path: Path):
    return path.suffix.lower() in AUDIO_EXTENSIONS


def read_metadata(path: Path):
    """
    Читает основные метаданные трека.
    """

    audio = File(path, easy=True)

    if audio is None:
        return {}


    def get(name):
        value = audio.get(name)

        if isinstance(value, list):
            return value[0]

        return value or ""


    return {
        "title": get("title"),
        "artist": get("artist"),
        "album": get("album"),
        "albumartist": get("albumartist"),
        "date": get("date"),
        "genre": get("genre"),
        "tracknumber": get("tracknumber"),
        "discnumber": get("discnumber"),
        "duration": int(audio.info.length)
            if audio.info else 0
    }

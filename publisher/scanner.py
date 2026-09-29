from pathlib import Path
from collections import Counter

from .models import Album, Track
from .metadata import read_metadata, is_audio


COVER_NAMES = {
    "cover.jpg",
    "cover.jpeg",
    "folder.jpg",
    "folder.jpeg",
    "front.jpg",
    "front.jpeg",
}


def find_cover(folder: Path):
    """
    Ищет внешнюю обложку в папке альбома.
    """

    for name in COVER_NAMES:
        cover = folder / name

        if cover.exists():
            return cover

    return None


def clean_artist(name: str):
    """
    Чистит имя артиста от мусора.
    """

    if not name:
        return ""

    return (
        name
        .replace("\x00", "")
        .strip()
    )


def choose_artist(tracks):
    """
    Выбор артиста альбома.

    Приоритет:
    1. ALBUMARTIST
    2. самый частый ARTIST
    3. первый ARTIST
    """

    album_artists = [
        clean_artist(t["albumartist"])
        for t in tracks
        if t.get("albumartist")
    ]

    if album_artists:
        return Counter(album_artists).most_common(1)[0][0]


    artists = [
        clean_artist(t["artist"])
        for t in tracks
        if t.get("artist")
    ]

    if not artists:
        return "Unknown Artist"


    return Counter(artists).most_common(1)[0][0]


def scan_album(folder: Path):
    """
    Создает объект Album из одной папки.
    """

    files = [
        f for f in folder.iterdir()
        if f.is_file() and is_audio(f)
    ]

    if not files:
        return None


    metadata = []

    for file in files:
        data = read_metadata(file)

        if data:
            data["filename"] = file
            metadata.append(data)


    if not metadata:
        return None


    album_title = metadata[0].get("album")

    if not album_title:
        album_title = folder.name


    album = Album(
        path=folder,
        title=album_title,
        artist=choose_artist(metadata),
        year=metadata[0].get("date", "")[:4],
        genre=metadata[0].get("genre", ""),
        cover=find_cover(folder),
    )


    tracks = []

    for item in metadata:

        track_number = item.get("tracknumber", "0")

        try:
            number = int(
                track_number.split("/")[0]
            )
        except:
            number = 0


        tracks.append(
            Track(
                number=number,
                title=item.get(
                    "title",
                    item["filename"].stem
                ),
                filename=item["filename"],
                duration=item.get(
                    "duration",
                    0
                ),
            )
        )


    album.tracks = sorted(
        tracks,
        key=lambda x: x.number
    )


    return album



def scan_library(root: Path):
    """
    Сканирует всю библиотеку.

    Любая папка с аудиофайлами
    считается альбомом.
    """

    albums = []


    for folder in root.rglob("*"):

        if not folder.is_dir():
            continue


        album = scan_album(folder)


        if album:
            albums.append(album)


    return sorted(
        albums,
        key=lambda a: (
            a.artist.lower(),
            a.title.lower()
        )
    )

import asyncio
from pathlib import Path

import typer
from rich import print
from rich.table import Table
from rich.console import Console

from config import MUSIC_PATH

from publisher.scanner import scan_library
from publisher.card import make_card
from publisher.formatter import (
    make_caption,
    make_tracklist
)
from publisher.telegram import (
    send_album,
    wait_for_discussion_message,
    send_tracklist,
    send_tracks
)
from publisher.cache import (
    is_published,
    mark_published,
)


app = typer.Typer()

console = Console()


def get_albums():
    return scan_library(MUSIC_PATH)



@app.command()
def list():
    """
    Показать все найденные альбомы.
    """

    albums = get_albums()

    table = Table(
        title="Music Library"
    )

    table.add_column("#")
    table.add_column("Artist")
    table.add_column("Album")
    table.add_column("Tracks")


    for i, album in enumerate(
        albums,
        start=1
    ):
        table.add_row(
            str(i),
            album.artist,
            album.title,
            str(album.track_count)
        )


    console.print(table)



@app.command()
def preview(name: str):
    """
    Создать карточку без публикации.
    """

    albums = get_albums()

    query = name.lower()

    # 1. точное совпадение
    for album in albums:
        if (
            album.title.lower() == query
            or album.artist.lower() == query
        ):
            image = make_card(album)

            print(
                f"[green]Created:[/green] {image}"
            )

            return


    # 2. поиск по названию + артисту
    matches = []

    for album in albums:

        text = (
            album.artist + " "
            + album.title
        ).lower()

        if query in text:
            matches.append(album)


    if len(matches) == 1:

        image = make_card(matches[0])

        print(
            f"[green]Created:[/green] {image}"
        )

        return


    if len(matches) > 1:

        print(
            "[yellow]Several matches:[/yellow]"
        )

        for i, album in enumerate(
            matches,
            start=1
        ):
            print(
                f"{i}. "
                f"{album.artist} - "
                f"{album.title}"
            )

        return


    print(
        "[red]Album not found[/red]"
    )

@app.command()
def publish(name: str):
    """
    Опубликовать один альбом.
    """

    albums = get_albums()

    query = name.lower()


    # 1. точное совпадение
    for album in albums:

        if (
            album.title.lower() == query
            or album.artist.lower() == query
            or f"{album.artist} {album.title}".lower() == query
        ):
            publish_album(album)
            return


    # 2. частичные совпадения
    matches = []

    for album in albums:

        text = (
            album.artist + " "
            + album.title
        ).lower()

        if query in text:
            matches.append(album)


    if len(matches) == 1:

        publish_album(matches[0])
        return


    if len(matches) > 1:

        print("[yellow]Найдено несколько альбомов:[/yellow]\n")

        for i, album in enumerate(matches, start=1):

            print(
                f"{i}. {album.artist} - {album.title}"
            )

        print(
            "\nУточни название."
        )

        return


    print(
        "[red]Альбом не найден[/red]"
    )


@app.command()
def publish_folder(
    skip_existing: bool = False
):
    """
    Опубликовать всю библиотеку.
    """

    albums = get_albums()


    print(
        f"Found albums: {len(albums)}"
    )


    for album in albums:

        if skip_existing and is_published(album):

            print(
                f"[yellow]Skip:[/yellow] "
                f"{album.artist} - {album.title}"
            )

            continue


        publish_album(album)



def publish_album(album):

    print(
        f"[cyan]Publishing:[/cyan] "
        f"{album.artist} - {album.title}"
    )


    image = make_card(album)


    if not image:

        print(
            "[red]No cover found[/red]"
        )

        return


    caption = make_caption(album)


    message_id = asyncio.run(
        send_album(
            image,
            caption
        )
    )


    discussion_id = asyncio.run(
        wait_for_discussion_message(
            message_id
        )
    )


    if discussion_id is None:

        print(
            "[red]Discussion message not found[/red]"
        )

        return


    track_ids = asyncio.run(
        send_tracks(
            discussion_id,
            album,
            cover=image
        )
    )

    print(
        f"Tracks sent: {len(track_ids)}"
    )

    list_id = asyncio.run(
        send_tracklist(
            discussion_id,
            make_tracklist(album)
        )
    )

    print(
        f"Tracklist message id: {list_id}"
    )


    mark_published(
        album,
        message_id
    )


    print(
        f"[green]Done[/green] "
        f"message={message_id}"
    )



if __name__ == "__main__":
    app()
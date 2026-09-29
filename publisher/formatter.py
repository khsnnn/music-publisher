from .models import Album


def format_duration(seconds: int):

    if not seconds:
        return ""

    minutes = seconds // 60
    seconds = seconds % 60

    return f"{minutes}:{seconds:02d}"



def hashtag(text: str):

    if not text:
        return ""

    return "#" + "".join(
        c for c in text
        if c.isalnum()
    )



def make_caption(album: Album):

    lines = []


    lines.append(
        f"🎵 <b>{album.artist}</b>"
    )

    lines.append(
        f"<i>{album.title}</i>"
    )


    lines.append("")


    info = []


    if album.year:
        info.append(
            album.year
        )


    if album.genre:
        info.append(
            album.genre
        )


    if info:
        lines.append(
            " • ".join(info)
        )


    details = []


    if album.track_count:
        details.append(
            f"{album.track_count} tracks"
        )


    duration = format_duration(
        album.duration
    )


    if duration:
        details.append(
            duration
        )


    if details:
        lines.append(
            " • ".join(details)
        )


    lines.append("")


    tags = []


    if album.artist:
        tags.append(
            hashtag(album.artist)
        )


    if album.genre:
        tags.append(
            hashtag(album.genre)
        )


    if album.year:
        tags.append(
            "#" + album.year
        )


    if tags:
        lines.append(
            " ".join(tags)
        )


    return "\n".join(lines)



def make_tracklist(album: Album):

    lines = [
        "<b>Tracklist:</b>",
        ""
    ]


    for track in album.tracks:

        lines.append(
            f"{track.number:02d}. {track.title}"
        )


    return "\n".join(lines)

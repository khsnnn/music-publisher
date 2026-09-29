from pathlib import Path

from PIL import Image, ImageDraw, ImageFont, ImageFilter

from config import CARD_WIDTH, CARD_HEIGHT
from .artwork import get_album_cover


OUTPUT_DIR = Path("output")


def get_font(size):
    """
    Пытается найти нормальный шрифт.
    """

    fonts = [
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        "/usr/share/fonts/truetype/liberation2/LiberationSans-Regular.ttf",
    ]

    for font in fonts:
        if Path(font).exists():
            return ImageFont.truetype(
                font,
                size
            )

    return ImageFont.load_default()



def resize_cover(image, size):
    """
    Обрезает картинку под квадрат.
    """

    image = image.convert("RGB")

    ratio = max(
        size[0] / image.width,
        size[1] / image.height
    )

    new_size = (
        int(image.width * ratio),
        int(image.height * ratio)
    )

    image = image.resize(
        new_size,
        Image.LANCZOS
    )

    left = (
        image.width - size[0]
    ) // 2

    top = (
        image.height - size[1]
    ) // 2


    return image.crop(
        (
            left,
            top,
            left + size[0],
            top + size[1]
        )
    )



def make_card(album):

    cover = get_album_cover(album)

    if cover is None:
        return None


    OUTPUT_DIR.mkdir(
        exist_ok=True
    )


    output = OUTPUT_DIR / (
        album.artist
        + " - "
        + album.title
        + ".jpg"
    )


    # фон

    canvas = Image.new(
        "RGB",
        (
            CARD_WIDTH,
            CARD_HEIGHT
        ),
        "black"
    )


    draw = ImageDraw.Draw(canvas)


    # обложка

    img = Image.open(cover)

    img = resize_cover(
        img,
        (
            CARD_WIDTH,
            CARD_WIDTH
        )
    )


    canvas.paste(
        img,
        (
            0,
            0
        )
    )


    # затемнение снизу

    overlay = Image.new(
        "RGBA",
        canvas.size,
        (0,0,0,0)
    )

    odraw = ImageDraw.Draw(
        overlay
    )


    odraw.rectangle(
        (
            0,
            CARD_WIDTH - 150,
            CARD_WIDTH,
            CARD_HEIGHT
        ),
        fill=(
            0,
            0,
            0,
            190
        )
    )


    canvas = Image.alpha_composite(
        canvas.convert("RGBA"),
        overlay
    ).convert("RGB")


    draw = ImageDraw.Draw(canvas)


    title_font = get_font(70)
    artist_font = get_font(55)
    info_font = get_font(40)


    y = CARD_WIDTH + 40


    draw.text(
        (
            50,
            y
        ),
        album.artist,
        font=artist_font,
        fill="white"
    )


    y += 80


    draw.text(
        (
            50,
            y
        ),
        album.title,
        font=title_font,
        fill="white"
    )


    y += 120


    info = []

    if album.year:
        info.append(
            album.year
        )

    if album.genre:
        info.append(
            album.genre
        )

    info.append(
        f"{album.track_count} tracks"
    )


    draw.text(
        (
            50,
            y
        ),
        " • ".join(info),
        font=info_font,
        fill="white"
    )


    canvas.save(
        output,
        quality=95
    )


    return output

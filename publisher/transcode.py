import hashlib
import shutil
import subprocess
from pathlib import Path


CACHE_DIR = Path("cache/transcoded")

# Кодируем только лослесс-форматы — перекодировать
# уже сжатый mp3/m4a/ogg смысла нет, только качество
# потеряем без выигрыша в размере.
LOSSLESS_EXTENSIONS = {".flac", ".wav", ".aiff", ".ape", ".wv"}

AAC_BITRATE = "224k"

_ffmpeg_available = None


def ffmpeg_available():
    """
    Проверяет наличие ffmpeg один раз за запуск.
    """

    global _ffmpeg_available

    if _ffmpeg_available is None:
        _ffmpeg_available = shutil.which("ffmpeg") is not None

    return _ffmpeg_available


def needs_transcode(path: Path):
    return path.suffix.lower() in LOSSLESS_EXTENSIONS


def cache_name(source: Path):
    """
    Уникальное имя для кэша. В хэш добавлены mtime
    и размер файла — если исходник поменяется,
    закэшированная версия не будет использована.
    """

    stat = source.stat()

    key = f"{source}|{stat.st_mtime}|{stat.st_size}"

    h = hashlib.md5(
        key.encode()
    ).hexdigest()

    return CACHE_DIR / f"{h}.m4a"


def transcode_track(path: Path):
    """
    Перекодирует лослесс-трек в AAC (.m4a) ~224kbps
    для загрузки в Telegram. Если перекодировать не
    нужно (уже lossy) или ffmpeg недоступен — отдаёт
    исходный файл как есть.

    Результат кэшируется в cache/transcoded/, повторный
    вызов для того же файла просто вернёт готовый путь.
    """

    if not needs_transcode(path):
        return path

    if not ffmpeg_available():
        print(
            "[warning] ffmpeg не найден — "
            f"отправляю оригинал без сжатия: {path.name}"
        )
        return path

    output = cache_name(path)

    if output.exists():
        return output

    output.parent.mkdir(
        parents=True,
        exist_ok=True
    )

    result = subprocess.run(
        [
            "ffmpeg",
            "-y",
            "-i", str(path),
            "-vn",
            "-c:a", "aac",
            "-b:a", AAC_BITRATE,
            str(output),
        ],
        capture_output=True,
        encoding="utf-8",
        errors="replace",
    )

    if result.returncode != 0:

        print(
            f"[warning] ffmpeg не смог перекодировать "
            f"{path.name}, отправляю оригинал:\n"
            f"{result.stderr[-500:]}"
        )

        return path

    return output
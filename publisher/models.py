from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class Track:
    number: int
    title: str
    filename: Path
    duration: int = 0


@dataclass
class Album:
    path: Path

    artist: str = ""
    title: str = ""
    year: str = ""
    genre: str = ""

    cover: Path | None = None

    tracks: list[Track] = field(default_factory=list)

    @property
    def key(self):
        """
        Уникальный идентификатор альбома.
        Используется для проверки дублей.
        """
        return f"{self.artist}|{self.title}"

    @property
    def track_count(self):
        return len(self.tracks)

    @property
    def duration(self):
        return sum(t.duration for t in self.tracks)

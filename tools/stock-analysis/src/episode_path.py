"""Episode paths: Ting-Media/episodes/<niche>/YYYY-MM-DD_theme/."""
from __future__ import annotations

from datetime import date
from pathlib import Path

MEDIA_ROOT = Path(__file__).resolve().parents[3]

_BAD = {chr(92), "/", ":", "*", "?", chr(34), "<", ">", "|"}


def _slug_theme(theme: str) -> str:
    theme = "".join(ch for ch in theme.strip() if ch not in _BAD and not ch.isspace())
    return theme or "未命名"


def episode_dir(*, niche: str = "finance", theme: str, day: date | None = None, media_root: Path | None = None) -> Path:
    day = day or date.today()
    root = media_root or MEDIA_ROOT
    folder = f"{day.isoformat()}_{_slug_theme(theme)}"
    return root / "episodes" / niche / folder

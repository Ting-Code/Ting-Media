"""Episode paths for Ting-Tools speak-pack.

成片: episodes/<niche>/YYYY-MM-DD_theme/
"""
from __future__ import annotations

from datetime import date
from pathlib import Path

MEDIA_ROOT = Path(__file__).resolve().parents[3]

_BAD = {chr(92), "/", ":", "*", "?", chr(34), "<", ">", "|"}


def _slug(text: str) -> str:
    text = "".join(ch for ch in text.strip() if ch not in _BAD)
    text = "".join(text.split())
    return text or "未命名"


def episode_folder_name(*, theme: str, day: date | None = None) -> str:
    day = day or date.today()
    return f"{day.isoformat()}_{_slug(theme)}"


def episode_dir(
    *,
    niche: str = "english",
    theme: str,
    day: date | None = None,
    media_root: Path | None = None,
) -> Path:
    root = media_root or MEDIA_ROOT
    return root / "episodes" / niche / episode_folder_name(theme=theme, day=day)

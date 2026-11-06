"""Episode + analysis cache paths for Ting-Media.

成片: episodes/<niche>/YYYY-MM-DD_theme/
缓存: cache/<分析名>/   （仓库根目录，不放 tools/ 下）
"""
from __future__ import annotations

from datetime import date
from pathlib import Path

MEDIA_ROOT = Path(__file__).resolve().parents[3]

_BAD = {chr(92), "/", ":", "*", "?", chr(34), "<", ">", "|"}


def _slug(text: str) -> str:
    text = "".join(ch for ch in text.strip() if ch not in _BAD)
    # collapse whitespace to nothing (keep CJK); strip leftover spaces
    text = "".join(text.split())
    return text or "未命名"


def episode_folder_name(*, theme: str, day: date | None = None) -> str:
    day = day or date.today()
    return f"{day.isoformat()}_{_slug(theme)}"


def episode_dir(
    *,
    niche: str = "finance",
    theme: str,
    day: date | None = None,
    media_root: Path | None = None,
) -> Path:
    root = media_root or MEDIA_ROOT
    return root / "episodes" / niche / episode_folder_name(theme=theme, day=day)


def cache_dir(
    name: str,
    *,
    media_root: Path | None = None,
) -> Path:
    """Root analysis cache: Ting-Media/cache/<分析名>/."""
    root = media_root or MEDIA_ROOT
    return root / "cache" / _slug(name)


def episode_cache_dir(
    *,
    theme: str,
    day: date | None = None,
    media_root: Path | None = None,
) -> Path:
    """Cache folder named like the episode: cache/YYYY-MM-DD_theme/."""
    return cache_dir(episode_folder_name(theme=theme, day=day), media_root=media_root)

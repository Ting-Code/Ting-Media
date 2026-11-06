"""Paths for stock-data: tool-local financial cache + Tongdaxin roots."""

from __future__ import annotations

import os
from pathlib import Path


def tool_root() -> Path:
    """tools/stock-data"""
    return Path(__file__).resolve().parents[1]


def repo_root() -> Path:
    return Path(__file__).resolve().parents[3]


def stock_data_cache() -> Path:
    """Financial raw-data cache lives inside this tool (not repo cache/)."""
    override = os.environ.get("STOCK_DATA_CACHE")
    if override:
        return Path(override)
    return tool_root() / "cache"


def tdx_root() -> Path | None:
    env = os.environ.get("TDX_DIR")
    candidates = []
    if env:
        candidates.append(Path(env))
    candidates.extend(
        [
            Path(r"D:/app/tdx"),
            Path(r"C:/new_tdx"),
            Path(r"D:/new_tdx"),
            Path.home() / "tdx",
        ]
    )
    for p in candidates:
        if (p / "vipdoc").is_dir():
            return p
    return None


def tdx_vipdoc() -> Path | None:
    env = os.environ.get("TDX_VIPDOC")
    if env:
        p = Path(env)
        if p.is_dir():
            return p
    root = tdx_root()
    return (root / "vipdoc") if root else None


def tdx_gbbq() -> Path | None:
    env = os.environ.get("TDX_GBBQ")
    if env:
        p = Path(env)
        if p.is_file():
            return p
    root = tdx_root()
    if not root:
        return None
    p = root / "T0002" / "hq_cache" / "gbbq"
    return p if p.is_file() else None

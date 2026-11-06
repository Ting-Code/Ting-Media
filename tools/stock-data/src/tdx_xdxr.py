"""Tongdaxin gbbq (权息) reader + decoded cache."""

from __future__ import annotations

import time
from pathlib import Path

import pandas as pd

from paths import tdx_gbbq
from store import gbbq_cache_path, read_frame, write_frame


def _parse_gbbq(path: Path) -> pd.DataFrame:
    from pytdx.reader import GbbqReader

    df = GbbqReader().get_df(str(path))
    df = df.rename(
        columns={
            "datetime": "date_i",
            "hongli_panqianliutong": "fenhong",
            "peigujia_qianzongguben": "peigujia",
            "songgu_qianzongguben": "songzhuangu",
            "peigu_houzongguben": "peigu",
        }
    )
    df["code"] = df["code"].astype(str).str.zfill(6)
    df["date"] = pd.to_datetime(df["date_i"].astype(str), format="%Y%m%d", errors="coerce")
    df = df.dropna(subset=["date", "code"])
    return df[
        ["market", "code", "date", "category", "fenhong", "peigujia", "songzhuangu", "peigu"]
    ].reset_index(drop=True)


def load_gbbq(*, refresh: bool = False, max_age_hours: float = 24.0) -> pd.DataFrame:
    """Load full gbbq; prefer decoded parquet cache under tools/stock-data/cache/tdx/."""
    cache = gbbq_cache_path()
    src = tdx_gbbq()
    if not refresh and cache.exists():
        # refresh if source newer than cache, or cache too old
        stale = False
        age_h = (time.time() - cache.stat().st_mtime) / 3600
        if age_h > max_age_hours:
            stale = True
        if src and src.exists() and src.stat().st_mtime > cache.stat().st_mtime:
            stale = True
        if not stale:
            df = read_frame(cache)
            if df is not None and not df.empty:
                df["date"] = pd.to_datetime(df["date"])
                return df
    if src is None:
        raise FileNotFoundError("未找到通达信 gbbq，请设置 TDX_DIR / TDX_GBBQ")
    df = _parse_gbbq(src)
    write_frame(cache, df)
    return df


def load_xdxr(code: str, *, category: int | None = 1, refresh: bool = False) -> pd.DataFrame:
    """Per-code 除权除息 rows (default category=1)."""
    digits = "".join(ch for ch in str(code) if ch.isdigit())[-6:]
    df = load_gbbq(refresh=refresh)
    sub = df[df["code"] == digits].copy()
    if category is not None:
        sub = sub[sub["category"] == category]
    return sub.sort_values("date").reset_index(drop=True)

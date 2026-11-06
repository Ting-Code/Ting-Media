"""A-share spot snapshot (market cap) via AkShare, day-cached under stock-data."""

from __future__ import annotations

import threading
from datetime import date
from pathlib import Path

import pandas as pd

from data_path import ensure_stock_data_on_path

ensure_stock_data_on_path()
from paths import stock_data_cache  # noqa: E402

_SPOT: dict[str, float] | None = None  # code6 -> 总市值(元)
_LOCK = threading.Lock()


def _cache_path() -> Path:
    d = stock_data_cache() / "em_spot"
    d.mkdir(parents=True, exist_ok=True)
    return d / f"a_spot_{date.today().isoformat()}.parquet"


def load_market_cap_map(*, refresh: bool = False) -> dict[str, float]:
    """code6 -> 总市值（元）。"""
    global _SPOT
    if _SPOT is not None and not refresh:
        return _SPOT
    with _LOCK:
        if _SPOT is not None and not refresh:
            return _SPOT
        path = _cache_path()
        if path.exists() and not refresh:
            df = pd.read_parquet(path)
        else:
            import akshare as ak

            raw = ak.stock_zh_a_spot_em()
            cols = {str(c): c for c in raw.columns}
            code_col = cols.get("代码") or raw.columns[1]
            cap_col = cols.get("总市值")
            if cap_col is None:
                raise KeyError(f"spot 无总市值列: {list(raw.columns)}")
            df = pd.DataFrame(
                {
                    "code": raw[code_col].astype(str).str.zfill(6).str[-6:],
                    "market_cap": pd.to_numeric(raw[cap_col], errors="coerce"),
                }
            ).dropna(subset=["market_cap"])
            df.to_parquet(path, index=False)
        _SPOT = {str(r.code): float(r.market_cap) for r in df.itertuples(index=False)}
        return _SPOT

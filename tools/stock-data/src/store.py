"""Local parquet cache helpers under tools/stock-data/cache/."""

from __future__ import annotations

import json
import time
from pathlib import Path

import pandas as pd

from paths import stock_data_cache


def cache_stem(code: str) -> str:
    """A 股 6 位，港股 5 位（00700.HK -> 00700）。用于缓存文件名。"""
    raw = str(code).strip().upper()
    if raw.endswith('.HK'):
        digits = ''.join(ch for ch in raw if ch.isdigit())
        if not digits or len(digits) > 5:
            raise ValueError(f'无效港股代码: {code}')
        return digits.zfill(5)
    return code6(code)


def hk_profit_code_path(code: str) -> Path:
    return _ensure(stock_data_cache() / 'em_hk_profit' / 'by_code') / f'{cache_stem(code)}.parquet'


def hk_balance_code_path(code: str) -> Path:
    return _ensure(stock_data_cache() / 'em_hk_balance' / 'by_code') / f'{cache_stem(code)}.parquet'


def fx_path(symbol: str = 'HKDCNYC') -> Path:
    return _ensure(stock_data_cache() / 'em_fx') / f'{symbol}.parquet'


def code6(code: str) -> str:
    digits = "".join(ch for ch in str(code) if ch.isdigit())
    if len(digits) < 6:
        raise ValueError(f"无效代码: {code}")
    return digits[-6:]


def _ensure(dir_path: Path) -> Path:
    dir_path.mkdir(parents=True, exist_ok=True)
    return dir_path


def profit_code_path(code: str) -> Path:
    return _ensure(stock_data_cache() / "em_profit" / "by_code") / f"{code6(code)}.parquet"


def profit_quarter_dir(report_date: str | pd.Timestamp) -> Path:
    d = pd.Timestamp(report_date).strftime("%Y%m%d")
    return _ensure(stock_data_cache() / "em_profit" / "by_quarter" / d)


def balance_code_path(code: str) -> Path:
    return _ensure(stock_data_cache() / "em_balance" / "by_code") / f"{code6(code)}.parquet"


def gbbq_cache_path() -> Path:
    return _ensure(stock_data_cache() / "tdx") / "gbbq.parquet"


def dividend_code_path(code: str) -> Path:
    return _ensure(stock_data_cache() / "em_dividend" / "by_code") / f"{code6(code)}.parquet"


def dividend_period_path(report_date: str) -> Path:
    d = pd.Timestamp(report_date).strftime("%Y%m%d")
    return _ensure(stock_data_cache() / "em_dividend" / "by_period") / f"{d}.parquet"


def meta_path(kind: str, code: str) -> Path:
    return _ensure(stock_data_cache() / kind / "by_code") / f"{code6(code)}.meta.json"


def write_frame(path: Path, df: pd.DataFrame) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    df.to_parquet(path, index=False)


def read_frame(path: Path) -> pd.DataFrame | None:
    if path.exists():
        return pd.read_parquet(path)
    return None


def write_meta(kind: str, code: str, **extra) -> None:
    payload = {"code": code6(code), "fetched_at": time.time(), **extra}
    meta_path(kind, code).write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def read_meta(kind: str, code: str) -> dict | None:
    p = meta_path(kind, code)
    if not p.exists():
        return None
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except Exception:
        return None


def is_fresh(kind: str, code: str, max_age_hours: float = 24.0) -> bool:
    meta = read_meta(kind, code)
    if not meta or "fetched_at" not in meta:
        return False
    return (time.time() - float(meta["fetched_at"])) < max_age_hours * 3600

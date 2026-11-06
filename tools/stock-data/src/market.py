"""A-share OHLCV：通达信本地（lday + gbbq 复权）。"""

from __future__ import annotations

from datetime import datetime

import pandas as pd

from adjust import apply_adjust
from tdx_day import fetch_tdx_daily
from tdx_xdxr import load_xdxr


def fetch_daily(
    code: str,
    start_date: str = "2015-01-01",
    end_date: str | None = None,
    adjust: str = "qfq",
) -> pd.DataFrame:
    """
    日线 OHLCV。
    adjust: qfq 前复权（默认）| hfq 后复权 | bfq/none 不复权
    """
    end_date = end_date or datetime.today().strftime("%Y-%m-%d")
    how = {"1": "bfq", "2": "qfq", "3": "hfq"}.get(str(adjust), adjust)

    full = fetch_tdx_daily(code, start_date=None, end_date=end_date)
    if full.empty:
        raise ValueError(f"no daily bars for {code}")

    if how not in ("bfq", "none", ""):
        full = apply_adjust(full, load_xdxr(code, category=1), how=how)

    out = full[full["date"] >= pd.Timestamp(start_date)]
    return out.reset_index(drop=True)


def resample_ohlcv(daily: pd.DataFrame, period: str) -> pd.DataFrame:
    if period == "D":
        return daily.copy()
    rule = {"W": "W-FRI", "M": "ME", "Q": "QE"}[period]
    g = daily.set_index("date").resample(rule)
    out = pd.DataFrame(
        {
            "open": g["open"].first(),
            "high": g["high"].max(),
            "low": g["low"].min(),
            "close": g["close"].last(),
            "volume": g["volume"].sum(),
            "amount": g["amount"].sum(),
        }
    ).dropna(subset=["open", "close"])
    return out.reset_index()


def month_end_close_on_or_before(
    daily: pd.DataFrame, day: pd.Timestamp
) -> tuple[pd.Timestamp, float] | None:
    sub = daily[daily["date"] <= day]
    if sub.empty:
        return None
    row = sub.iloc[-1]
    return pd.Timestamp(row["date"]), float(row["close"])

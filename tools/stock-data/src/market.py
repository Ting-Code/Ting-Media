"""A-share OHLCV：通达信本地（lday + gbbq 复权）。"""

from __future__ import annotations

from datetime import datetime

import pandas as pd

from adjust import apply_adjust
from tdx_day import classify_board, fetch_tdx_daily, list_a_share_codes, list_day_files, read_day_tail
from tdx_xdxr import cash_dividends, load_xdxr


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


def fetch_cash_dividends(code: str, *, refresh: bool = False) -> pd.DataFrame:
    """单只股票已除息的每股现金分红（税前）。通达信 gbbq，不另做缓存。

    列：code, ex_date, cash_per_share。无分红时返回空表。
    这里含特别分红，用于复权。股息率分子用 fundamentals.fetch_dividends
    或 fetch_period_cash_dividends，分母用不复权收盘价。
    """
    return cash_dividends(codes=[code], refresh=refresh)


def fetch_a_share_cash_dividends(*, refresh: bool = False) -> pd.DataFrame:
    """全 A 已除息现金分红。一次读 gbbq 解密缓存，再按本机日线里的 A 股过滤。"""
    return cash_dividends(codes=list_a_share_codes(), refresh=refresh)


def fetch_a_share_last_close() -> pd.DataFrame:
    """全 A 最新一根不复权收盘。列：code, asof, close。直读 vipdoc，不落盘。"""
    rows = []
    for exch, code, path in list_day_files():
        if classify_board(exch, code) is None:
            continue
        tail = read_day_tail(path, max_bars=1)
        if tail.empty:
            continue
        row = tail.iloc[-1]
        rows.append(
            {
                "code": code,
                "asof": pd.Timestamp(row["date"]).normalize(),
                "close": float(row["close"]),
            }
        )
    if not rows:
        return pd.DataFrame(columns=["code", "asof", "close"])
    return pd.DataFrame(rows)


def month_end_close_on_or_before(
    daily: pd.DataFrame, day: pd.Timestamp
) -> tuple[pd.Timestamp, float] | None:
    sub = daily[daily["date"] <= day]
    if sub.empty:
        return None
    row = sub.iloc[-1]
    return pd.Timestamp(row["date"]), float(row["close"])

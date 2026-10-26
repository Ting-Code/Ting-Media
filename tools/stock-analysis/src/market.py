"""A-share OHLCV via BaoStock + period resampling."""

from __future__ import annotations

from datetime import datetime

import baostock as bs
import pandas as pd

from .codes import to_baostock


def fetch_daily(
    code: str,
    start_date: str = "2015-01-01",
    end_date: str | None = None,
    adjustflag: str = "2",
) -> pd.DataFrame:
    end_date = end_date or datetime.today().strftime("%Y-%m-%d")
    symbol = to_baostock(code)
    lg = bs.login()
    if lg.error_code != "0":
        raise RuntimeError(f"BaoStock login failed: {lg.error_msg}")
    try:
        rs = bs.query_history_k_data_plus(
            symbol,
            "date,open,high,low,close,volume,amount",
            start_date=start_date,
            end_date=end_date,
            frequency="d",
            adjustflag=adjustflag,
        )
        if rs.error_code != "0":
            raise RuntimeError(rs.error_msg)
        rows = []
        while rs.error_code == "0" and rs.next():
            rows.append(rs.get_row_data())
    finally:
        bs.logout()

    if not rows:
        raise ValueError(f"no daily bars for {symbol}")
    df = pd.DataFrame(rows, columns=["date", "open", "high", "low", "close", "volume", "amount"])
    for c in ["open", "high", "low", "close", "volume", "amount"]:
        df[c] = pd.to_numeric(df[c], errors="coerce")
    df["date"] = pd.to_datetime(df["date"])
    df = df.dropna(subset=["open", "high", "low", "close"]).sort_values("date")
    return df.reset_index(drop=True)


def resample_ohlcv(daily: pd.DataFrame, period: str) -> pd.DataFrame:
    """period: D/W/M/Q"""
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


def month_end_close_on_or_before(daily: pd.DataFrame, day: pd.Timestamp) -> tuple[pd.Timestamp, float] | None:
    """Last trading day close on or before `day`."""
    sub = daily[daily["date"] <= day]
    if sub.empty:
        return None
    row = sub.iloc[-1]
    return pd.Timestamp(row["date"]), float(row["close"])


def next_month_end_anchor(notice_date: pd.Timestamp, daily: pd.DataFrame) -> tuple[pd.Timestamp, float] | None:
    """Month-end of the calendar month after notice_date."""
    notice_date = pd.Timestamp(notice_date).normalize()
    # first day of next-next month, then go back one day -> end of next month
    y, m = notice_date.year, notice_date.month
    m2 = m + 2
    y2 = y + (m2 - 1) // 12
    m2 = (m2 - 1) % 12 + 1
    boundary = pd.Timestamp(year=y2, month=m2, day=1) - pd.Timedelta(days=1)
    return month_end_close_on_or_before(daily, boundary)

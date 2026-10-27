"""A-share daily bars via BaoStock."""

from __future__ import annotations

from datetime import datetime

import baostock as bs
import pandas as pd


def _to_baostock_code(code: str) -> str:
    """Accept 600519 / sh.600519 / 600519.SH and normalize to sh.600519."""
    raw = code.strip().lower().replace(" ", "")
    if raw.startswith(("sh.", "sz.", "bj.")):
        return raw
    if raw.endswith(".sh"):
        return f"sh.{raw[:-3]}"
    if raw.endswith(".sz"):
        return f"sz.{raw[:-3]}"
    if raw.endswith(".bj"):
        return f"bj.{raw[:-3]}"

    digits = "".join(ch for ch in raw if ch.isdigit())
    if len(digits) != 6:
        raise ValueError(f"无效代码: {code}")

    if digits.startswith(("5", "6", "9")):
        return f"sh.{digits}"
    if digits.startswith(("4", "8")):
        return f"bj.{digits}"
    return f"sz.{digits}"


def fetch_daily(
    code: str,
    start_date: str = "2015-01-01",
    end_date: str | None = None,
) -> pd.DataFrame:
    """Fetch daily OHLCV. Dates as YYYY-MM-DD."""
    end_date = end_date or datetime.today().strftime("%Y-%m-%d")
    symbol = _to_baostock_code(code)

    lg = bs.login()
    if lg.error_code != "0":
        raise RuntimeError(f"BaoStock 登录失败: {lg.error_msg}")

    try:
        rs = bs.query_history_k_data_plus(
            symbol,
            "date,open,high,low,close,volume,amount,pctChg",
            start_date=start_date,
            end_date=end_date,
            frequency="d",
            adjustflag="2",  # 前复权
        )
        if rs.error_code != "0":
            raise RuntimeError(f"查询失败: {rs.error_msg}")

        rows: list[list[str]] = []
        while rs.error_code == "0" and rs.next():
            rows.append(rs.get_row_data())
    finally:
        bs.logout()

    if not rows:
        raise ValueError(f"未获取到数据: {symbol} ({start_date} ~ {end_date})")

    df = pd.DataFrame(
        rows,
        columns=["date", "open", "high", "low", "close", "volume", "amount", "pctChg"],
    )
    for col in ["open", "high", "low", "close", "volume", "amount", "pctChg"]:
        df[col] = pd.to_numeric(df[col], errors="coerce")
    df["date"] = pd.to_datetime(df["date"])
    df = df.dropna(subset=["open", "high", "low", "close"]).sort_values("date")
    df["code"] = symbol
    return df.reset_index(drop=True)

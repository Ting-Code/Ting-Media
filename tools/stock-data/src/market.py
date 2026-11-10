"""A-share OHLCV：通达信本地（lday + gbbq 复权）。"""

from __future__ import annotations

from datetime import datetime

import pandas as pd

from adjust import apply_adjust
from paths import tdx_vipdoc
from tdx_day import (
    classify_board,
    fetch_tdx_daily,
    list_a_share_codes,
    list_day_files,
    read_day_dates_amount,
    read_day_file,
    read_day_tail,
)
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

# 6 位指数代码和股票撞号（000300 不是深市股票）。只在这里查指数文件。
_INDEX_MARKET = {
    "000001": "sh",
    "000016": "sh",
    "000300": "sh",
    "000680": "sh",
    "000688": "sh",
    "000905": "sh",
    "000852": "sh",
    "399001": "sz",
    "399005": "sz",
    "399006": "sz",
    "399102": "sz",
    "399673": "sz",
}


def _index_location(code: str) -> tuple[str, str]:
    raw = code.strip().lower()
    if len(raw) >= 8 and raw[:2] in ("sh", "sz", "bj") and raw[2:8].isdigit():
        return raw[:2], raw[2:8]
    digits = "".join(ch for ch in raw if ch.isdigit())
    market = _INDEX_MARKET.get(digits)
    if len(digits) != 6 or market is None:
        raise ValueError(f"无法识别指数: {code}。请用 sh000300、sz399006 这种带市场的代码。")
    return market, digits


def fetch_index_daily(
    code: str,
    start_date: str = "2015-01-01",
    end_date: str | None = None,
) -> pd.DataFrame:
    """指数日线，不复权。

    用 sh000300、sz399006。不要把 000300 交给 fetch_daily，那个会去找深市文件。
    """
    end_date = end_date or datetime.today().strftime("%Y-%m-%d")
    market, digits = _index_location(code)
    root = tdx_vipdoc()
    if root is None:
        raise FileNotFoundError("未找到通达信 vipdoc，请设置 TDX_DIR / TDX_VIPDOC")
    path = root / market / "lday" / f"{market}{digits}.day"
    if not path.is_file():
        raise FileNotFoundError(f"无指数日线: {path}")
    full = read_day_file(path)
    if full.empty:
        raise ValueError(f"no daily bars for index {market}{digits}")
    out = full[(full["date"] >= pd.Timestamp(start_date)) & (full["date"] <= pd.Timestamp(end_date))]
    return out.reset_index(drop=True)


def fetch_boards_daily_amount() -> dict[str, pd.DataFrame]:
    """一次扫描本机 A 股日线，按板块加总成交额（元）。

    键：all、main、star、chinext、bse。all 是四块合计。
    只计能归到板块的股票，不含指数、ETF、债券。直读 vipdoc，不落盘。
    """
    import numpy as np

    codes = {"main": 0, "star": 1, "chinext": 2, "bse": 3}
    date_parts: list[np.ndarray] = []
    amount_parts: list[np.ndarray] = []
    board_parts: list[np.ndarray] = []
    for market, _code, path in list_day_files():
        board = classify_board(market, _code)
        bid = codes.get(board or "")
        if bid is None:
            continue
        dates, amounts = read_day_dates_amount(path)
        if len(dates) == 0:
            continue
        date_parts.append(dates)
        amount_parts.append(amounts)
        board_parts.append(np.full(len(dates), bid, dtype=np.int8))

    empty = pd.DataFrame(columns=["date", "amount"])
    if not date_parts:
        return {key: empty.copy() for key in ("all", "main", "star", "chinext", "bse")}

    frame = pd.DataFrame(
        {
            "date_i": np.concatenate(date_parts),
            "amount": np.concatenate(amount_parts),
            "board": np.concatenate(board_parts),
        }
    )
    frame = frame[frame["amount"] > 0]
    grouped = frame.groupby(["board", "date_i"], sort=False)["amount"].sum().reset_index()

    def _one(sub: pd.DataFrame) -> pd.DataFrame:
        if sub.empty:
            return empty.copy()
        out = sub[["date_i", "amount"]].copy()
        out["date"] = pd.to_datetime(out["date_i"].astype(str), format="%Y%m%d")
        return out.drop(columns=["date_i"]).sort_values("date").reset_index(drop=True)

    names = {0: "main", 1: "star", 2: "chinext", 3: "bse"}
    result = {name: _one(grouped[grouped["board"] == bid]) for bid, name in names.items()}
    result["all"] = _one(frame.groupby("date_i", sort=False)["amount"].sum().reset_index())
    return result

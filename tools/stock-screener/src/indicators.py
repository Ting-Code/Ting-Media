"""Technical indicators from OHLCV frames."""

from __future__ import annotations

import pandas as pd


def ma(series: pd.Series, window: int) -> float | None:
    if len(series) < window:
        return None
    return float(series.iloc[-window:].mean())


def pct_change(series: pd.Series, days: int) -> float | None:
    if len(series) < days + 1:
        return None
    a = float(series.iloc[-1])
    b = float(series.iloc[-(days + 1)])
    if b == 0:
        return None
    return (a / b - 1.0) * 100.0


def avg_volume(series: pd.Series, window: int) -> float | None:
    if len(series) < window:
        return None
    return float(series.iloc[-window:].mean())


def sma_tdx(series: pd.Series, n: int, m: int) -> pd.Series:
    """通达信 SMA(X,N,M)：Y = (M*X + (N-M)*Y')/N。"""
    out: list[float] = []
    prev: float | None = None
    for x in series.tolist():
        if x is None or (isinstance(x, float) and pd.isna(x)):
            out.append(float("nan"))
            continue
        xf = float(x)
        if prev is None or pd.isna(prev):
            prev = xf
        else:
            prev = (m * xf + (n - m) * prev) / n
        out.append(prev)
    return pd.Series(out, index=series.index, dtype=float)


def kdj(
    high: pd.Series,
    low: pd.Series,
    close: pd.Series,
    n: int = 9,
    m1: int = 3,
    m2: int = 3,
) -> pd.DataFrame:
    """通达信 KDJ：RSV=n；K=SMA(RSV,m1,1)；D=SMA(K,m2,1)；J=3K-2D。"""
    lowest = low.rolling(n, min_periods=n).min()
    highest = high.rolling(n, min_periods=n).max()
    denom = (highest - lowest).replace(0, pd.NA)
    rsv = (close - lowest) / denom * 100.0
    k = sma_tdx(rsv, m1, 1)
    d = sma_tdx(k, m2, 1)
    j = 3 * k - 2 * d
    return pd.DataFrame({"k": k, "d": d, "j": j, "rsv": rsv})


def enrich_row(df: pd.DataFrame) -> dict:
    """Compute common fields for one symbol's bar frame."""
    if df.empty:
        return {}
    close = df["close"]
    vol = df["volume"]
    last = df.iloc[-1]
    out: dict = {
        "close": float(last["close"]),
        "open": float(last["open"]),
        "high": float(last["high"]),
        "low": float(last["low"]),
        "volume": float(last["volume"]),
        "amount": float(last["amount"]),
        "amount_yi": float(last["amount"]) / 1e8,
        "date": pd.Timestamp(last["date"]).strftime("%Y-%m-%d"),
        "pct_chg_1d": None,
        "pct_chg_5d": None,
        "ma5": ma(close, 5),
        "ma10": ma(close, 10),
        "ma20": ma(close, 20),
        "ma60": ma(close, 60),
        "vol_ma5": avg_volume(vol, 5),
        "kdj_k": None,
        "kdj_d": None,
        "kdj_j": None,
    }
    if len(df) >= 2:
        prev = float(df.iloc[-2]["close"])
        if prev:
            out["pct_chg_1d"] = (out["close"] / prev - 1.0) * 100.0
    out["pct_chg_5d"] = pct_change(close, 5)

    if len(df) >= 9:
        kd = kdj(df["high"], df["low"], df["close"])
        for src, dst in [("k", "kdj_k"), ("d", "kdj_d"), ("j", "kdj_j")]:
            v = kd[src].iloc[-1]
            out[dst] = float(v) if pd.notna(v) else None
    return out

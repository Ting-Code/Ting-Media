"""Built-in technical filters (no fundamentals / PE)."""

from __future__ import annotations

from typing import Any

from registry import register


def _num(row: dict[str, Any], key: str) -> float | None:
    v = row.get(key)
    if v is None:
        return None
    try:
        return float(v)
    except (TypeError, ValueError):
        return None


@register("min_amount")
def min_amount(row: dict[str, Any], params: dict[str, Any]) -> bool:
    """Latest day amount in 亿元."""
    min_yi = float(params.get("min_yi", 1.0))
    v = _num(row, "amount_yi")
    return v is not None and v >= min_yi


@register("price_change_nday")
def price_change_nday(row: dict[str, Any], params: dict[str, Any]) -> bool:
    days = int(params.get("days", 5))
    key = f"pct_chg_{days}d" if days != 1 else "pct_chg_1d"
    # enrich always has pct_chg_5d; for other days compute if present
    v = _num(row, key)
    if v is None and days == 5:
        v = _num(row, "pct_chg_5d")
    if v is None:
        return False
    lo = params.get("min_pct")
    hi = params.get("max_pct")
    if lo is not None and v < float(lo):
        return False
    if hi is not None and v > float(hi):
        return False
    return True


@register("above_ma")
def above_ma(row: dict[str, Any], params: dict[str, Any]) -> bool:
    window = int(params.get("ma", 20))
    ma_v = _num(row, f"ma{window}")
    close = _num(row, "close")
    if ma_v is None or close is None:
        return False
    return close >= ma_v


@register("ma_stack")
def ma_stack(row: dict[str, Any], params: dict[str, Any]) -> bool:
    """Bullish MA stack: short > mid > long."""
    s = int(params.get("short", 5))
    m = int(params.get("mid", 10))
    l = int(params.get("long", 20))
    a, b, c = _num(row, f"ma{s}"), _num(row, f"ma{m}"), _num(row, f"ma{l}")
    if a is None or b is None or c is None:
        return False
    return a >= b >= c


@register("volume_expand")
def volume_expand(row: dict[str, Any], params: dict[str, Any]) -> bool:
    """Today volume / lookback avg volume (lookback=5 uses vol_ma5)."""
    lookback = int(params.get("lookback", 5))
    min_ratio = float(params.get("min_ratio", 1.2))
    vol = _num(row, "volume")
    avg_key = "vol_ma5" if lookback == 5 else f"vol_ma{lookback}"
    avg = _num(row, avg_key)
    if vol is None or avg is None or avg <= 0:
        return False
    return (vol / avg) >= min_ratio

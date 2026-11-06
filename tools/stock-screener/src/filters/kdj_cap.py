"""KDJ + market-cap filters."""

from __future__ import annotations

from typing import Any

from registry import register
from spot import load_market_cap_map


@register("kdj_j_below")
def kdj_j_below(row: dict[str, Any], params: dict[str, Any]) -> bool:
    """当日 J < max（默认 13）。"""
    j = row.get("kdj_j")
    if j is None:
        return False
    try:
        return float(j) < float(params.get("max", 13))
    except (TypeError, ValueError):
        return False


@register("market_cap")
def market_cap(row: dict[str, Any], params: dict[str, Any]) -> bool:
    """
    总市值过滤（亿元）。
    params: min_yi / max_yi（可只设一端）
    """
    code = str(row.get("code") or "").zfill(6)[-6:]
    caps = load_market_cap_map()
    cap = caps.get(code)
    if cap is None:
        return False
    yi = cap / 1e8
    row["market_cap_yi"] = yi
    lo = params.get("min_yi")
    hi = params.get("max_yi")
    if lo is not None and yi < float(lo):
        return False
    if hi is not None and yi > float(hi):
        return False
    return True

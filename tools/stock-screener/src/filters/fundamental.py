"""Fundamental filters (uses stock-data cache / East Money)."""

from __future__ import annotations

from typing import Any

from data_path import ensure_stock_data_on_path
from registry import register

ensure_stock_data_on_path()
from fundamentals import fetch_quarterly_profit  # noqa: E402


@register("profitable")
def profitable(row: dict[str, Any], params: dict[str, Any]) -> bool:
    """Latest report PARENT_NETPROFIT (or deduct) > 0. Put after cheap tech filters."""
    code = str(row.get("code") or "")
    if len(code) < 6:
        return False
    field = str(params.get("field") or "parent").lower()
    col = "DEDUCT_PARENT_NETPROFIT" if field in ("deduct", "扣非") else "PARENT_NETPROFIT"
    try:
        df = fetch_quarterly_profit(code)
    except Exception:
        return False
    if df is None or df.empty or col not in df.columns:
        return False
    val = df.iloc[-1][col]
    try:
        return float(val) > 0
    except (TypeError, ValueError):
        return False

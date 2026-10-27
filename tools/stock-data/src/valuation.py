"""Quarterly valuation points: PE/PB/dividend yield at next-month month-end."""

from __future__ import annotations

import pandas as pd

from market import next_month_end_anchor


def trailing_dividend_per_share(dividends: pd.DataFrame, asof: pd.Timestamp) -> float:
    if dividends.empty:
        return 0.0
    start = asof - pd.DateOffset(months=12)
    sub = dividends[(dividends["ex_date"] > start) & (dividends["ex_date"] <= asof)]
    return float(sub["cash_per_share"].sum()) if not sub.empty else 0.0


def build_valuation_series(
    fundamentals: pd.DataFrame,
    daily: pd.DataFrame,
    dividends: pd.DataFrame,
) -> pd.DataFrame:
    rows = []
    for _, r in fundamentals.iterrows():
        if pd.isna(r.get("deduct_np_ttm")) or pd.isna(r.get("NOTICE_DATE")):
            continue
        if pd.isna(r.get("SHARE_CAPITAL")) or r["SHARE_CAPITAL"] <= 0:
            continue
        if pd.isna(r.get("TOTAL_PARENT_EQUITY")):
            continue
        anchor = next_month_end_anchor(r["NOTICE_DATE"], daily)
        if anchor is None:
            continue
        anchor_date, price = anchor
        shares = float(r["SHARE_CAPITAL"])
        ttm = float(r["deduct_np_ttm"])
        equity = float(r["TOTAL_PARENT_EQUITY"])
        pe = (price / (ttm / shares)) if ttm > 0 else None
        pb = (price / (equity / shares)) if equity > 0 else None
        dps = trailing_dividend_per_share(dividends, anchor_date)
        div_yield = (dps / price * 100) if price > 0 else None
        rows.append(
            {
                "report_date": r["REPORT_DATE"],
                "notice_date": r["NOTICE_DATE"],
                "anchor_date": anchor_date,
                "price": price,
                "pe_ttm_deduct": pe,
                "pb": pb,
                "div_yield_pct": div_yield,
                "deduct_np_ttm": ttm,
                "revenue_q": r.get("revenue_q"),
                "deduct_np_q": r.get("deduct_np_q"),
            }
        )
    return pd.DataFrame(rows)


def current_snapshot(
    fundamentals: pd.DataFrame,
    daily: pd.DataFrame,
    dividends: pd.DataFrame,
) -> dict:
    last = daily.iloc[-1]
    price = float(last["close"])
    asof = pd.Timestamp(last["date"])
    f = fundamentals.dropna(subset=["deduct_np_ttm", "SHARE_CAPITAL", "TOTAL_PARENT_EQUITY"]).iloc[-1]
    shares = float(f["SHARE_CAPITAL"])
    ttm = float(f["deduct_np_ttm"])
    equity = float(f["TOTAL_PARENT_EQUITY"])
    pe = price / (ttm / shares) if ttm > 0 else None
    pb = price / (equity / shares) if equity > 0 else None
    dps = trailing_dividend_per_share(dividends, asof)
    return {
        "asof": asof,
        "price": price,
        "pe_ttm_deduct": pe,
        "pb": pb,
        "div_yield_pct": (dps / price * 100) if price > 0 else None,
        "report_date": f["REPORT_DATE"],
    }


def percentile(series: pd.Series, value: float | None) -> float | None:
    s = series.dropna()
    if s.empty or value is None:
        return None
    return float((s <= value).mean() * 100)

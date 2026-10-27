"""Single-stock PE/PB: prior-quarter deduct NP (x4) + this quarter-end price."""

from __future__ import annotations

import pandas as pd

from market import month_end_close_on_or_before


def trailing_dividend_per_share(dividends: pd.DataFrame, asof: pd.Timestamp) -> float:
    if dividends.empty:
        return 0.0
    start = asof - pd.DateOffset(months=12)
    sub = dividends[(dividends["ex_date"] > start) & (dividends["ex_date"] <= asof)]
    return float(sub["cash_per_share"].sum()) if not sub.empty else 0.0


def _prev_quarter_end(q_end: pd.Timestamp) -> pd.Timestamp:
    q_end = pd.Timestamp(q_end).normalize()
    return (q_end.to_period("Q") - 1).to_timestamp(how="end").normalize()


def _match_fundamental(fundamentals: pd.DataFrame, report_q_end: pd.Timestamp) -> pd.Series | None:
    """Row whose REPORT_DATE falls in the same quarter as report_q_end."""
    if fundamentals.empty:
        return None
    f = fundamentals.copy()
    f["REPORT_DATE"] = pd.to_datetime(f["REPORT_DATE"])
    period = pd.Timestamp(report_q_end).to_period("Q")
    sub = f[f["REPORT_DATE"].dt.to_period("Q") == period]
    if sub.empty:
        return None
    return sub.sort_values("REPORT_DATE").iloc[-1]


def build_valuation_series(
    fundamentals: pd.DataFrame,
    daily: pd.DataFrame,
    dividends: pd.DataFrame,
) -> pd.DataFrame:
    """One point per observation quarter T: PE/PB with prior-quarter earnings and T price."""
    daily = daily.sort_values("date").reset_index(drop=True)
    f = fundamentals.dropna(
        subset=["deduct_np_q", "SHARE_CAPITAL", "TOTAL_PARENT_EQUITY", "REPORT_DATE"]
    ).copy()
    if f.empty or daily.empty:
        return pd.DataFrame()

    f["REPORT_DATE"] = pd.to_datetime(f["REPORT_DATE"])
    last_daily = pd.Timestamp(daily["date"].iloc[-1]).normalize()
    first_report = f["REPORT_DATE"].min()
    # first observation = end of quarter after first report quarter
    start_obs = (first_report.to_period("Q") + 1).to_timestamp(how="end")
    end_obs = last_daily.to_period("Q").to_timestamp(how="end")
    if start_obs > end_obs:
        return pd.DataFrame()

    q_ends = pd.period_range(
        start_obs.to_period("Q"), end_obs.to_period("Q"), freq="Q"
    ).to_timestamp(how="end")

    rows = []
    for q_end in q_ends:
        q_end = pd.Timestamp(q_end).normalize()
        prev_q = _prev_quarter_end(q_end)
        r = _match_fundamental(f, prev_q)
        if r is None:
            continue

        incomplete = q_end > last_daily
        if incomplete:
            price_date = last_daily
            price = float(daily.iloc[-1]["close"])
        else:
            anchor = month_end_close_on_or_before(daily, q_end)
            if anchor is None:
                continue
            price_date, price = anchor

        shares = float(r["SHARE_CAPITAL"])
        deduct_q = float(r["deduct_np_q"])
        equity = float(r["TOTAL_PARENT_EQUITY"])
        if shares <= 0:
            continue

        # Annualize prior single-quarter 扣非
        pe = (price / ((deduct_q * 4) / shares)) if deduct_q > 0 else None
        pb = (price / (equity / shares)) if equity > 0 else None
        dps = trailing_dividend_per_share(dividends, price_date)
        div_yield = (dps / price * 100) if price > 0 else None

        rows.append(
            {
                "quarter_end": q_end,
                "anchor_date": price_date,  # actual price date used
                "price": price,
                "incomplete_quarter": incomplete,
                "prev_report_date": pd.Timestamp(r["REPORT_DATE"]),
                "pe": pe,
                "pe_ttm_deduct": pe,  # compat alias for templates/scripts
                "pb": pb,
                "div_yield_pct": div_yield,
                "deduct_np_q": deduct_q,
                "revenue_q": r.get("revenue_q"),
                "SHARE_CAPITAL": shares,
                "TOTAL_PARENT_EQUITY": equity,
            }
        )
    return pd.DataFrame(rows)


def current_snapshot(
    fundamentals: pd.DataFrame,
    daily: pd.DataFrame,
    dividends: pd.DataFrame,
) -> dict:
    """Latest price + prior quarter 扣非 (same rule as series)."""
    series = build_valuation_series(fundamentals, daily, dividends)
    last = daily.iloc[-1]
    asof = pd.Timestamp(last["date"])
    price = float(last["close"])
    if series.empty:
        return {
            "asof": asof,
            "price": price,
            "pe_ttm_deduct": None,
            "pe": None,
            "pb": None,
            "div_yield_pct": None,
            "report_date": None,
        }
    row = series.iloc[-1]
    return {
        "asof": asof,
        "price": price,
        "pe_ttm_deduct": row.get("pe"),
        "pe": row.get("pe"),
        "pb": row.get("pb"),
        "div_yield_pct": row.get("div_yield_pct"),
        "report_date": row.get("prev_report_date"),
    }


def percentile(series: pd.Series, value: float | None) -> float | None:
    s = series.dropna()
    if s.empty or value is None:
        return None
    return float((s <= value).mean() * 100)

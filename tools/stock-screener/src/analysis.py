"""基本面面板 + PE/PB 估值（原始数据来自 stock-data）。"""

from __future__ import annotations

import pandas as pd

from data_path import ensure_stock_data_on_path

ensure_stock_data_on_path()
from fundamentals import fetch_quarterly_balance, fetch_quarterly_profit  # noqa: E402
from market import month_end_close_on_or_before  # noqa: E402


def ytd_to_single_quarter(ytd: pd.Series) -> pd.Series:
    """累计报告期 → 单季。"""
    s = ytd.sort_index()
    out = s.copy()
    prev_year = None
    prev_val = 0.0
    for dt, val in s.items():
        year, month = dt.year, dt.month
        if month == 3:
            q = val
        elif prev_year == year:
            q = val - prev_val
        else:
            q = val
        out.loc[dt] = q
        prev_year, prev_val = year, val
    return out


def build_fundamental_panel(code: str, *, refresh: bool = False) -> pd.DataFrame:
    profit = fetch_quarterly_profit(code, refresh=refresh)
    for c in ["REPORT_DATE", "TOTAL_OPERATE_INCOME", "PARENT_NETPROFIT", "DEDUCT_PARENT_NETPROFIT"]:
        if c not in profit.columns:
            raise KeyError(f"利润表缺少字段: {c}")
    balance = fetch_quarterly_balance(code, refresh=refresh)
    bcols = [c for c in ["REPORT_DATE", "TOTAL_PARENT_EQUITY", "SHARE_CAPITAL"] if c in balance.columns]
    df = profit.merge(balance[bcols], on="REPORT_DATE", how="left")
    df = df.dropna(subset=["REPORT_DATE", "DEDUCT_PARENT_NETPROFIT"])
    df = df.set_index("REPORT_DATE").sort_index()
    for col, new in [
        ("TOTAL_OPERATE_INCOME", "revenue_q"),
        ("PARENT_NETPROFIT", "parent_np_q"),
        ("DEDUCT_PARENT_NETPROFIT", "deduct_np_q"),
    ]:
        df[new] = ytd_to_single_quarter(df[col])
    df["deduct_np_ttm"] = df["deduct_np_q"].rolling(4).sum()
    df["revenue_ttm"] = df["revenue_q"].rolling(4).sum()
    return df.reset_index()


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
    """观察季 T：上一季单季扣非×4 + 本季末价 → PE/PB。"""
    daily = daily.sort_values("date").reset_index(drop=True)
    f = fundamentals.dropna(
        subset=["deduct_np_q", "SHARE_CAPITAL", "TOTAL_PARENT_EQUITY", "REPORT_DATE"]
    ).copy()
    if f.empty or daily.empty:
        return pd.DataFrame()

    f["REPORT_DATE"] = pd.to_datetime(f["REPORT_DATE"])
    last_daily = pd.Timestamp(daily["date"].iloc[-1]).normalize()
    first_report = f["REPORT_DATE"].min()
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
        r = _match_fundamental(f, _prev_quarter_end(q_end))
        if r is None:
            continue
        incomplete = q_end > last_daily
        if incomplete:
            price_date, price = last_daily, float(daily.iloc[-1]["close"])
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
        pe = (price / ((deduct_q * 4) / shares)) if deduct_q > 0 else None
        pb = (price / (equity / shares)) if equity > 0 else None
        dps = trailing_dividend_per_share(dividends, price_date)
        rows.append(
            {
                "quarter_end": q_end,
                "anchor_date": price_date,
                "price": price,
                "incomplete_quarter": incomplete,
                "prev_report_date": pd.Timestamp(r["REPORT_DATE"]),
                "pe": pe,
                "pe_ttm_deduct": pe,
                "pb": pb,
                "div_yield_pct": (dps / price * 100) if price > 0 else None,
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

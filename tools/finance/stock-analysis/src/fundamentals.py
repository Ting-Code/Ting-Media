"""Quarterly fundamentals from East Money via AkShare."""

from __future__ import annotations

import pandas as pd
import akshare as ak

from .codes import to_baostock


def _em_symbol(code: str) -> str:
    digits = "".join(ch for ch in code if ch.isdigit())
    bs = to_baostock(digits)
    return ("SH" if bs.startswith("sh") else "SZ") + digits


def fetch_quarterly_profit(code: str) -> pd.DataFrame:
    raw = ak.stock_profit_sheet_by_report_em(symbol=_em_symbol(code))
    df = raw[
        [
            "REPORT_DATE",
            "NOTICE_DATE",
            "REPORT_TYPE",
            "TOTAL_OPERATE_INCOME",
            "PARENT_NETPROFIT",
            "DEDUCT_PARENT_NETPROFIT",
        ]
    ].copy()
    df["REPORT_DATE"] = pd.to_datetime(df["REPORT_DATE"])
    df["NOTICE_DATE"] = pd.to_datetime(df["NOTICE_DATE"])
    for c in ["TOTAL_OPERATE_INCOME", "PARENT_NETPROFIT", "DEDUCT_PARENT_NETPROFIT"]:
        df[c] = pd.to_numeric(df[c], errors="coerce")
    df = df.dropna(subset=["REPORT_DATE", "DEDUCT_PARENT_NETPROFIT"])
    df = df.sort_values("REPORT_DATE").drop_duplicates("REPORT_DATE", keep="last")
    return df.reset_index(drop=True)


def fetch_quarterly_balance(code: str) -> pd.DataFrame:
    raw = ak.stock_balance_sheet_by_report_em(symbol=_em_symbol(code))
    df = raw[["REPORT_DATE", "NOTICE_DATE", "TOTAL_PARENT_EQUITY", "SHARE_CAPITAL"]].copy()
    df["REPORT_DATE"] = pd.to_datetime(df["REPORT_DATE"])
    df["NOTICE_DATE"] = pd.to_datetime(df["NOTICE_DATE"])
    df["TOTAL_PARENT_EQUITY"] = pd.to_numeric(df["TOTAL_PARENT_EQUITY"], errors="coerce")
    df["SHARE_CAPITAL"] = pd.to_numeric(df["SHARE_CAPITAL"], errors="coerce")
    df = df.dropna(subset=["REPORT_DATE", "TOTAL_PARENT_EQUITY"])
    df = df.sort_values("REPORT_DATE").drop_duplicates("REPORT_DATE", keep="last")
    return df.reset_index(drop=True)


def fetch_dividends(code: str) -> pd.DataFrame:
    """Cash dividend events; cash_per_share in yuan."""
    digits = "".join(ch for ch in code if ch.isdigit())
    raw = ak.stock_fhps_detail_em(symbol=digits)
    # columns are Chinese; pick by known positions from akshare schema
    # 0 report period, 5 cash per 10 shares, 16 ex-div date, 17 status, 13 total shares
    cols = list(raw.columns)
    out = pd.DataFrame(
        {
            "report_date": pd.to_datetime(raw[cols[0]]),
            "cash_per_10": pd.to_numeric(raw[cols[5]], errors="coerce"),
            "ex_date": pd.to_datetime(raw[cols[16]], errors="coerce"),
            "status": raw[cols[17]].astype(str),
            "total_share": pd.to_numeric(raw[cols[13]], errors="coerce"),
        }
    )
    out = out[out["status"].str.contains("实施", na=False)]
    out["cash_per_share"] = out["cash_per_10"] / 10.0
    out = out.dropna(subset=["ex_date", "cash_per_share"])
    return out.sort_values("ex_date").reset_index(drop=True)


def ytd_to_single_quarter(ytd: pd.Series) -> pd.Series:
    """Convert cumulative report figures to single-quarter values."""
    s = ytd.sort_index()
    out = s.copy()
    prev_year = None
    prev_val = 0.0
    for dt, val in s.items():
        year = dt.year
        month = dt.month
        if month == 3:
            q = val
        else:
            if prev_year == year:
                q = val - prev_val
            else:
                q = val
        out.loc[dt] = q
        prev_year, prev_val = year, val
    return out


def build_fundamental_panel(code: str) -> pd.DataFrame:
    profit = fetch_quarterly_profit(code)
    balance = fetch_quarterly_balance(code)
    df = profit.merge(
        balance[["REPORT_DATE", "TOTAL_PARENT_EQUITY", "SHARE_CAPITAL"]],
        on="REPORT_DATE",
        how="left",
    )
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

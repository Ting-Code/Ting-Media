"""用已缓存的东财按季主要指标拼官方基本面面板，不改 analysis.py 取数路径。"""

from __future__ import annotations

import pandas as pd

from analysis import ytd_to_single_quarter
from em_market_quarter import load_market_main_range


def panel_from_market(g: pd.DataFrame) -> pd.DataFrame:
    g = g.sort_values("REPORT_DATE").drop_duplicates("REPORT_DATE", keep="last").copy()
    df = pd.DataFrame(
        {
            "REPORT_DATE": pd.to_datetime(g["REPORT_DATE"]),
            "DEDUCT_PARENT_NETPROFIT": pd.to_numeric(g.get("KCFJCXSYJLR"), errors="coerce"),
            "PARENT_NETPROFIT": pd.to_numeric(g.get("PARENTNETPROFIT"), errors="coerce"),
            "TOTAL_OPERATE_INCOME": pd.to_numeric(g.get("TOTALOPERATEREVE"), errors="coerce"),
            "SHARE_CAPITAL": pd.to_numeric(g.get("TOTAL_SHARE"), errors="coerce"),
            "BPS": pd.to_numeric(g.get("BPS"), errors="coerce"),
        }
    )
    df["TOTAL_PARENT_EQUITY"] = df["BPS"] * df["SHARE_CAPITAL"]
    df = df.dropna(subset=["REPORT_DATE", "DEDUCT_PARENT_NETPROFIT"])
    if df.empty:
        return df
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


def load_market_panels() -> dict[str, pd.DataFrame]:
    market = load_market_main_range()
    if market is None or market.empty:
        return {}
    panels: dict[str, pd.DataFrame] = {}
    for code, g in market.groupby("SECURITY_CODE", sort=False):
        panels[str(code).zfill(6)] = panel_from_market(g)
    return panels
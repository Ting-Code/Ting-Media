"""ETF 份额和板块总市值。来自上交所、深交所，不写入财报缓存。"""

from __future__ import annotations

import pandas as pd
import requests

_SSE = {
    "Referer": "https://www.sse.com.cn/",
    "User-Agent": "Mozilla/5.0",
}


def _yyyymmdd(date: str) -> str:
    digits = "".join(ch for ch in date if ch.isdigit())
    if len(digits) != 8:
        raise ValueError(f"日期需要 YYYYMMDD: {date}")
    return digits


def fetch_sse_etf_shares(date: str) -> pd.DataFrame:
    """上交所某一天全部 ETF 份额。列 code, shares，单位份。"""
    import akshare as ak

    raw = ak.fund_etf_scale_sse(date=_yyyymmdd(date))
    out = pd.DataFrame(
        {
            "code": raw["基金代码"].astype(str).str.zfill(6),
            "shares": pd.to_numeric(raw["基金份额"], errors="coerce"),
        }
    )
    return out.dropna(subset=["shares"])


def fetch_szse_etf_shares(start: str, end: str) -> pd.DataFrame:
    """深交所一段日期里的 ETF 份额。列 date, code, shares，单位份。"""
    import akshare as ak

    raw = ak.fund_scale_daily_szse(
        start_date=_yyyymmdd(start),
        end_date=_yyyymmdd(end),
        symbol="ETF",
    )
    out = pd.DataFrame(
        {
            "date": pd.to_datetime(raw["日期"]),
            "code": raw["基金代码"].astype(str).str.zfill(6),
            "shares": pd.to_numeric(raw["基金份额"], errors="coerce"),
        }
    )
    return out.dropna(subset=["date", "shares"])


def fetch_board_caps(date: str) -> dict[str, float] | None:
    """某一天板块总市值，单位元。

    star 科创板，chinext 创业板，all 沪市主板A + 科创板 + 深市主板A + 创业板。
    不含 B 股和北交所。没有数据时返回 None。
    """
    import akshare as ak

    day = _yyyymmdd(date)
    dashed = f"{day[:4]}-{day[4:6]}-{day[6:]}"
    response = requests.get(
        "https://query.sse.com.cn/commonQuery.do",
        params={
            "sqlId": "COMMON_SSE_SJ_GPSJ_CJGK_MRGK_C",
            "PRODUCT_CODE": "01,02,03,11,17",
            "type": "inParams",
            "SEARCH_DATE": dashed,
        },
        headers=_SSE,
        timeout=20,
    )
    response.raise_for_status()
    rows = response.json().get("result") or []
    by_code = {}
    for row in rows:
        value = pd.to_numeric(row.get("TOTAL_VALUE"), errors="coerce")
        if pd.notna(value):
            by_code[str(row.get("PRODUCT_CODE"))] = float(value) * 1e8
    if "01" not in by_code or "03" not in by_code:
        return None
    summary = ak.stock_szse_summary(date=day)
    caps = {}
    for _, row in summary.iterrows():
        caps[str(row["证券类别"])] = pd.to_numeric(row["总市值"], errors="coerce")
    sz_main = caps.get("主板A股")
    chinext = caps.get("创业板A股")
    if pd.isna(sz_main) or pd.isna(chinext):
        return None
    star = by_code["03"]
    total = by_code["01"] + star + float(sz_main) + float(chinext)
    return {"star": star, "chinext": float(chinext), "all": total}

"""Quarterly fundamentals from East Money via AkShare — full sheet cached locally."""

from __future__ import annotations

import pandas as pd
import akshare as ak

from codes import hk_code5, is_hk, to_exchange
from store import (
    balance_code_path,
    code6,
    dividend_code_path,
    dividend_period_path,
    fx_path,
    hk_balance_code_path,
    hk_profit_code_path,
    profit_code_path,
    profit_quarter_dir,
    read_frame,
    write_frame,
    write_meta,
)

# slim columns kept for older call sites / panel
PROFIT_CORE_COLS = [
    "REPORT_DATE",
    "NOTICE_DATE",
    "REPORT_TYPE",
    "TOTAL_OPERATE_INCOME",
    "PARENT_NETPROFIT",
    "DEDUCT_PARENT_NETPROFIT",
]


def _em_symbol(code: str) -> str:
    digits = "".join(ch for ch in code if ch.isdigit())
    bs = to_exchange(digits)
    prefix = "SH" if bs.startswith("sh") else ("BJ" if bs.startswith("bj") else "SZ")
    return prefix + digits


def _coerce_profit(raw: pd.DataFrame) -> pd.DataFrame:
    df = raw.copy()
    df["REPORT_DATE"] = pd.to_datetime(df["REPORT_DATE"], errors="coerce")
    if "NOTICE_DATE" in df.columns:
        df["NOTICE_DATE"] = pd.to_datetime(df["NOTICE_DATE"], errors="coerce")
    if "UPDATE_DATE" in df.columns:
        df["UPDATE_DATE"] = pd.to_datetime(df["UPDATE_DATE"], errors="coerce")
    # numeric-coerce obvious amount / ratio fields
    skip = {
        "SECUCODE",
        "SECURITY_CODE",
        "SECURITY_NAME_ABBR",
        "ORG_CODE",
        "ORG_TYPE",
        "REPORT_TYPE",
        "REPORT_DATE_NAME",
        "SECURITY_TYPE_CODE",
        "CURRENCY",
        "OPINION_TYPE",
    }
    for c in df.columns:
        if c in skip or str(c).endswith("_DATE") or str(c).endswith("_NAME"):
            continue
        if df[c].dtype == object:
            converted = pd.to_numeric(df[c], errors="coerce")
            # keep original if almost all became NaN (likely strings)
            if converted.notna().sum() >= max(1, int(0.5 * len(df))):
                df[c] = converted
    df = df.dropna(subset=["REPORT_DATE"])
    df = df.sort_values("REPORT_DATE").drop_duplicates("REPORT_DATE", keep="last")
    if "SECURITY_CODE" in df.columns:
        df["SECURITY_CODE"] = df["SECURITY_CODE"].astype(str).map(
            lambda x: "".join(ch for ch in x if ch.isdigit())[-6:].zfill(6)
        )
    return df.reset_index(drop=True)


def _write_profit_quarters(df: pd.DataFrame, code: str) -> None:
    """Also materialize one-row-per-quarter files for cross-section reads."""
    c6 = code6(code)
    for _, row in df.iterrows():
        qdir = profit_quarter_dir(row["REPORT_DATE"])
        one = pd.DataFrame([row])
        write_frame(qdir / f"{c6}.parquet", one)


def sync_quarterly_profit(code: str, *, force: bool = False) -> pd.DataFrame:
    """Fetch full EM profit sheet and cache by code + by quarter.

    有本地缓存就直接用，不按时间过期；只有 force=True 才重新请求东财。
    """
    path = profit_code_path(code)
    if not force:
        cached = read_frame(path)
        if cached is not None and not cached.empty:
            cached["REPORT_DATE"] = pd.to_datetime(cached["REPORT_DATE"])
            if "NOTICE_DATE" in cached.columns:
                cached["NOTICE_DATE"] = pd.to_datetime(cached["NOTICE_DATE"])
            return cached

    raw = ak.stock_profit_sheet_by_report_em(symbol=_em_symbol(code))
    df = _coerce_profit(raw)
    write_frame(path, df)
    _write_profit_quarters(df, code)
    write_meta(
        "em_profit",
        code,
        n_quarters=int(len(df)),
        max_report=str(df["REPORT_DATE"].max().date()) if len(df) else None,
        n_cols=int(df.shape[1]),
    )
    return df


def fetch_quarterly_profit(
    code: str,
    *,
    columns: list[str] | None = None,
    refresh: bool = False,
) -> pd.DataFrame:
    """
    东财利润表（报告期）。默认返回**全字段**（本地缓存）。
    有缓存先读缓存；refresh=True 才重新请求。
    columns=PROFIT_CORE_COLS 可取旧版精简列。
    港股走东财港股报告期，字段已对齐到同一套列名。
    """
    if is_hk(code):
        df = sync_hk_profit(code, force=refresh)
    else:
        df = sync_quarterly_profit(code, force=refresh)
    if columns is not None:
        keep = [c for c in columns if c in df.columns]
        df = df[keep].copy()
    return df.reset_index(drop=True)


def load_profit_quarter(report_date: str | pd.Timestamp) -> pd.DataFrame:
    """Cross-section: all cached codes for one REPORT_DATE."""
    qdir = profit_quarter_dir(report_date)
    frames = []
    for p in sorted(qdir.glob("*.parquet")):
        frames.append(pd.read_parquet(p))
    if not frames:
        return pd.DataFrame()
    out = pd.concat(frames, ignore_index=True)
    out["REPORT_DATE"] = pd.to_datetime(out["REPORT_DATE"])
    return out


def sync_quarterly_balance(code: str, *, force: bool = False) -> pd.DataFrame:
    """有本地缓存就直接用，不按时间过期；只有 force=True 才重新请求东财。"""
    path = balance_code_path(code)
    if not force:
        cached = read_frame(path)
        if cached is not None and not cached.empty:
            cached["REPORT_DATE"] = pd.to_datetime(cached["REPORT_DATE"])
            if "NOTICE_DATE" in cached.columns:
                cached["NOTICE_DATE"] = pd.to_datetime(cached["NOTICE_DATE"])
            return cached

    raw = ak.stock_balance_sheet_by_report_em(symbol=_em_symbol(code))
    df = raw.copy()
    df["REPORT_DATE"] = pd.to_datetime(df["REPORT_DATE"], errors="coerce")
    if "NOTICE_DATE" in df.columns:
        df["NOTICE_DATE"] = pd.to_datetime(df["NOTICE_DATE"], errors="coerce")
    df = df.dropna(subset=["REPORT_DATE"])
    df = df.sort_values("REPORT_DATE").drop_duplicates("REPORT_DATE", keep="last")
    write_frame(path, df.reset_index(drop=True))
    write_meta("em_balance", code, n_quarters=int(len(df)), n_cols=int(df.shape[1]))
    return df.reset_index(drop=True)


def fetch_quarterly_balance(code: str, *, refresh: bool = False) -> pd.DataFrame:
    """资产负债表全字段缓存；有缓存先读；panel 仍只用 TOTAL_PARENT_EQUITY / SHARE_CAPITAL。"""
    if is_hk(code):
        return sync_hk_balance(code, force=refresh)
    return sync_quarterly_balance(code, force=refresh)


def sync_dividends(code: str, *, force: bool = False) -> pd.DataFrame:
    """东财分红配送 → cache/em_dividend/by_code。有缓存先读，不按时间过期。"""
    path = dividend_code_path(code)
    if not force:
        cached = read_frame(path)
        if cached is not None:
            cached["report_date"] = pd.to_datetime(cached["report_date"])
            cached["ex_date"] = pd.to_datetime(cached["ex_date"])
            return cached

    digits = code6(code)
    raw = ak.stock_fhps_detail_em(symbol=digits)
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
    out = out.sort_values("ex_date").reset_index(drop=True)
    write_frame(path, out)
    write_meta("em_dividend", code, n_events=int(len(out)))
    return out


def fetch_dividends(code: str, *, refresh: bool = False) -> pd.DataFrame:
    """单只股票的定期报告期现金分红，东财，已实施且已除息。

    列：report_date, cash_per_10, ex_date, status, total_share, cash_per_share。
    cash_per_10 是每 10 股税前派现，cash_per_share = cash_per_10 / 10。
    东财这张表只列年报、中报、一季报、三季报，不含特别分红。
    股息率分子用它，再按最近四个已结束报告期加总。
    有缓存先读；refresh=True 才重新请求。
    港股暂不取东财 A 股分红表，返回空表。
    """
    if is_hk(code):
        return pd.DataFrame(
            columns=["report_date", "cash_per_10", "ex_date", "status", "total_share", "cash_per_share"]
        )
    return sync_dividends(code, force=refresh)


def fetch_period_cash_dividends(report_date: str, *, refresh: bool = False) -> pd.DataFrame:
    """某一个定期报告期的全市场已实施现金分红。东财分红送配。

    report_date 用 YYYYMMDD，例如 20251231。
    「现金分红-现金分红比例」是每 10 股税前派现，每股 = 该数 / 10。
    只保留方案进度含「实施」、现金大于 0、且有除权除息日的记录。
    这张表按定期报告期列示，不含特别分红。
    列：code, name, report_date, cash_per_share, ex_date, status。
    有缓存先读；refresh=True 才重新请求。
    """
    key = pd.Timestamp(report_date).strftime("%Y%m%d")
    path = dividend_period_path(key)
    if not refresh:
        cached = read_frame(path)
        if cached is not None:
            cached["report_date"] = pd.to_datetime(cached["report_date"])
            cached["ex_date"] = pd.to_datetime(cached["ex_date"])
            return cached

    columns = ["code", "name", "report_date", "cash_per_share", "ex_date", "status"]
    raw = ak.stock_fhps_em(date=key)
    if raw is None or raw.empty:
        out = pd.DataFrame(columns=columns)
        write_frame(path, out)
        return out
    out = pd.DataFrame(
        {
            "code": raw["代码"].astype(str).str.replace(r"\D", "", regex=True).str[-6:].str.zfill(6),
            "name": raw["名称"].astype(str).str.replace(" ", "", regex=False),
            "report_date": pd.Timestamp(key),
            "cash_per_share": pd.to_numeric(raw["现金分红-现金分红比例"], errors="coerce") / 10.0,
            "ex_date": pd.to_datetime(raw["除权除息日"], errors="coerce"),
            "status": raw["方案进度"].astype(str),
        }
    )
    out = out[out["status"].str.contains("实施", na=False)]
    out = out[out["cash_per_share"] > 0]
    out = out.dropna(subset=["ex_date", "code"])
    out = out[out["code"].str.fullmatch(r"\d{6}")]
    out = out.sort_values("code").reset_index(drop=True)
    write_frame(path, out[columns])
    return out

HK_INCOME_ITEMS = {
    "营业额": "TOTAL_OPERATE_INCOME",
    "股东应占溢利": "PARENT_NETPROFIT",
    "每股基本盈利": "BASIC_EPS",
}
HK_BALANCE_ITEMS = {
    "股东权益": "TOTAL_PARENT_EQUITY",
    "净资产": "NET_ASSETS",
}


def _hk_stock(code: str) -> str:
    return hk_code5(code)


def _pivot_hk_report(raw: pd.DataFrame, mapping: dict[str, str]) -> pd.DataFrame:
    if raw is None or raw.empty:
        return pd.DataFrame()
    df = raw.copy()
    name_col = "STD_ITEM_NAME" if "STD_ITEM_NAME" in df.columns else None
    amount_col = "AMOUNT" if "AMOUNT" in df.columns else None
    if name_col is None or amount_col is None:
        raise KeyError("港股财报缺少 STD_ITEM_NAME / AMOUNT")
    df["REPORT_DATE"] = pd.to_datetime(df["REPORT_DATE"], errors="coerce")
    df[amount_col] = pd.to_numeric(df[amount_col], errors="coerce")
    sub = df[df[name_col].isin(mapping.keys())].copy()
    if sub.empty:
        return pd.DataFrame()
    wide = (
        sub.pivot_table(index="REPORT_DATE", columns=name_col, values=amount_col, aggfunc="last")
        .rename(columns=mapping)
        .sort_index()
        .reset_index()
    )
    if "SECURITY_NAME_ABBR" in df.columns:
        names = df.dropna(subset=["REPORT_DATE"]).sort_values("REPORT_DATE")
        name_map = names.drop_duplicates("REPORT_DATE").set_index("REPORT_DATE")["SECURITY_NAME_ABBR"]
        wide["SECURITY_NAME_ABBR"] = wide["REPORT_DATE"].map(name_map)
    return wide


def sync_hk_profit(code: str, *, force: bool = False) -> pd.DataFrame:
    """东财港股利润表（报告期，长表转宽表）。有缓存先读，不按时间过期。"""
    path = hk_profit_code_path(code)
    if not force:
        cached = read_frame(path)
        if cached is not None and not cached.empty:
            cached["REPORT_DATE"] = pd.to_datetime(cached["REPORT_DATE"])
            return cached

    raw = ak.stock_financial_hk_report_em(stock=_hk_stock(code), symbol="利润表", indicator="报告期")
    df = _pivot_hk_report(raw, HK_INCOME_ITEMS)
    if df.empty:
        raise ValueError(f"无港股利润表: {code}")
    if "PARENT_NETPROFIT" in df.columns:
        df["DEDUCT_PARENT_NETPROFIT"] = df["PARENT_NETPROFIT"]
    df["market"] = "hk"
    df["CURRENCY"] = "CNY"
    write_frame(path, df)
    return df.reset_index(drop=True)


def sync_hk_balance(code: str, *, force: bool = False) -> pd.DataFrame:
    """东财港股资产负债表。有缓存先读，不按时间过期。"""
    path = hk_balance_code_path(code)
    if not force:
        cached = read_frame(path)
        if cached is not None and not cached.empty:
            cached["REPORT_DATE"] = pd.to_datetime(cached["REPORT_DATE"])
            return cached

    raw = ak.stock_financial_hk_report_em(stock=_hk_stock(code), symbol="资产负债表", indicator="报告期")
    df = _pivot_hk_report(raw, HK_BALANCE_ITEMS)
    if df.empty:
        raise ValueError(f"无港股资产负债表: {code}")
    if "TOTAL_PARENT_EQUITY" not in df.columns and "NET_ASSETS" in df.columns:
        df["TOTAL_PARENT_EQUITY"] = df["NET_ASSETS"]
    if "SHARE_CAPITAL" not in df.columns:
        df["SHARE_CAPITAL"] = pd.NA
    df["market"] = "hk"
    df["CURRENCY"] = "CNY"
    write_frame(path, df)
    return df.reset_index(drop=True)


def fetch_fx_hkdcnyc(*, refresh: bool = False) -> pd.DataFrame:
    """港币人民币中间价（1 港元兑人民币）。列：date, cny_per_hkd。有缓存先读。"""
    path = fx_path("HKDCNYC")
    if not refresh:
        cached = read_frame(path)
        if cached is not None and not cached.empty:
            cached["date"] = pd.to_datetime(cached["date"])
            return cached.sort_values("date").reset_index(drop=True)

    raw = ak.forex_hist_em("HKDCNYC")
    out = raw.rename(columns={"日期": "date", "最新价": "cny_per_hkd"})[["date", "cny_per_hkd"]].copy()
    out["date"] = pd.to_datetime(out["date"])
    out["cny_per_hkd"] = pd.to_numeric(out["cny_per_hkd"], errors="coerce")
    out = out.dropna().sort_values("date").drop_duplicates("date").reset_index(drop=True)
    write_frame(path, out)
    return out

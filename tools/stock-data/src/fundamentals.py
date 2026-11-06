"""Quarterly fundamentals from East Money via AkShare — full sheet cached locally."""

from __future__ import annotations

import pandas as pd
import akshare as ak

from codes import to_exchange
from store import (
    balance_code_path,
    code6,
    dividend_code_path,
    is_fresh,
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


def sync_quarterly_profit(code: str, *, force: bool = False, max_age_hours: float = 24.0) -> pd.DataFrame:
    """Fetch full EM profit sheet and cache by code + by quarter."""
    path = profit_code_path(code)
    if not force and is_fresh("em_profit", code, max_age_hours=max_age_hours):
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
    max_age_hours: float = 24.0,
) -> pd.DataFrame:
    """
    东财利润表（报告期）。默认返回**全字段**（本地缓存）。
    columns=PROFIT_CORE_COLS 可取旧版精简列。
    """
    df = sync_quarterly_profit(code, force=refresh, max_age_hours=max_age_hours)
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


def sync_quarterly_balance(code: str, *, force: bool = False, max_age_hours: float = 24.0) -> pd.DataFrame:
    path = balance_code_path(code)
    if not force and is_fresh("em_balance", code, max_age_hours=max_age_hours):
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


def fetch_quarterly_balance(code: str, *, refresh: bool = False, max_age_hours: float = 24.0) -> pd.DataFrame:
    """资产负债表全字段缓存；panel 仍只用 TOTAL_PARENT_EQUITY / SHARE_CAPITAL。"""
    return sync_quarterly_balance(code, force=refresh, max_age_hours=max_age_hours)


def sync_dividends(code: str, *, force: bool = False, max_age_hours: float = 24.0) -> pd.DataFrame:
    """东财分红配送 → cache/em_dividend/by_code。"""
    path = dividend_code_path(code)
    if not force and is_fresh("em_dividend", code, max_age_hours=max_age_hours):
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


def fetch_dividends(
    code: str, *, refresh: bool = False, max_age_hours: float = 24.0
) -> pd.DataFrame:
    """Cash dividend events; cash_per_share in yuan. Cached under em_dividend."""
    return sync_dividends(code, force=refresh, max_age_hours=max_age_hours)


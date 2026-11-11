"""按报告期全市场拉取东财主要指标（含扣非、每股净资产、总股本）。有缓存不重拉。"""

from __future__ import annotations

import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

import pandas as pd
import requests

from paths import stock_data_cache
from store import read_frame, write_frame

URL = "https://datacenter.eastmoney.com/securities/api/data/get"
KEEP = [
    "SECURITY_CODE",
    "SECURITY_NAME_ABBR",
    "REPORT_DATE",
    "NOTICE_DATE",
    "KCFJCXSYJLR",
    "PARENTNETPROFIT",
    "TOTALOPERATEREVE",
    "BPS",
    "TOTAL_SHARE",
    "A_FREE_SHARE",
]


def market_main_dir() -> Path:
    path = stock_data_cache() / "em_market" / "main"
    path.mkdir(parents=True, exist_ok=True)
    return path


def market_main_path(report_date: str | pd.Timestamp) -> Path:
    day = pd.Timestamp(report_date).strftime("%Y%m%d")
    return market_main_dir() / f"{day}.parquet"


def quarter_ends(start: str = "2014-12-31", end: str | None = None) -> list[pd.Timestamp]:
    end_ts = pd.Timestamp(end) if end else pd.Timestamp.today().normalize()
    last = (end_ts.to_period("Q") - (0 if end_ts == end_ts.to_period("Q").to_timestamp(how="end").normalize() else 1)).to_timestamp(how="end").normalize()
    start_ts = pd.Timestamp(start).normalize()
    return [
        ts.normalize()
        for ts in pd.period_range(start_ts.to_period("Q"), last.to_period("Q"), freq="Q").to_timestamp(how="end")
    ]


def fetch_market_main_quarter(report_date: str | pd.Timestamp, *, page_size: int = 500) -> pd.DataFrame:
    day = pd.Timestamp(report_date).strftime("%Y-%m-%d")
    filt = f'(REPORT_DATE=\'{day}\')(SECURITY_TYPE_CODE in ("058001001","058001008"))'
    rows: list[dict] = []
    page = 1
    total = None
    while True:
        params = {
            "type": "RPT_F10_FINANCE_MAINFINADATA",
            "sty": "ALL",
            "filter": filt,
            "p": str(page),
            "ps": str(page_size),
            "sr": "-1",
            "st": "SECURITY_CODE",
            "source": "HSF10",
            "client": "PC",
        }
        last_exc = None
        js = None
        for attempt in range(3):
            try:
                r = requests.get(URL, params=params, timeout=45)
                r.raise_for_status()
                js = r.json()
                last_exc = None
                break
            except Exception as exc:
                last_exc = exc
                time.sleep(1.5 * (2**attempt))
        if last_exc:
            raise last_exc
        result = (js or {}).get("result") or {}
        data = result.get("data") or []
        if not data:
            break
        rows.extend(data)
        total = result.get("count")
        if total is not None and len(rows) >= int(total):
            break
        page += 1
        if page > 80:
            break
    df = pd.DataFrame(rows)
    if df.empty:
        return df
    keep = [c for c in KEEP if c in df.columns]
    df = df[keep].copy()
    df["SECURITY_CODE"] = df["SECURITY_CODE"].astype(str).str.zfill(6)
    df["REPORT_DATE"] = pd.to_datetime(df["REPORT_DATE"])
    if "NOTICE_DATE" in df.columns:
        df["NOTICE_DATE"] = pd.to_datetime(df["NOTICE_DATE"], errors="coerce")
    for col in ("KCFJCXSYJLR", "PARENTNETPROFIT", "TOTALOPERATEREVE", "BPS", "TOTAL_SHARE", "A_FREE_SHARE"):
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")
    df = df.drop_duplicates(["SECURITY_CODE", "REPORT_DATE"], keep="last")
    return df.reset_index(drop=True)


def sync_market_main_quarter(report_date: str | pd.Timestamp, *, force: bool = False) -> pd.DataFrame:
    path = market_main_path(report_date)
    if not force:
        cached = read_frame(path)
        if cached is not None and not cached.empty:
            cached["REPORT_DATE"] = pd.to_datetime(cached["REPORT_DATE"])
            return cached
    df = fetch_market_main_quarter(report_date)
    if not df.empty:
        write_frame(path, df)
    return df


def sync_market_main_range(
    start: str = "2014-12-31",
    end: str | None = None,
    *,
    workers: int = 3,
    force: bool = False,
) -> list[pd.Timestamp]:
    dates = quarter_ends(start, end)
    print(f"sync market main quarters={len(dates)} workers={workers} force={force}", flush=True)
    t0 = time.time()
    done = 0

    def one(day: pd.Timestamp) -> tuple[pd.Timestamp, int, bool]:
        path = market_main_path(day)
        hit = (not force) and path.exists()
        df = sync_market_main_quarter(day, force=force)
        return day, int(len(df)), bool(hit and not df.empty)

    with ThreadPoolExecutor(max_workers=max(1, workers)) as pool:
        futs = [pool.submit(one, d) for d in dates]
        for fut in as_completed(futs):
            day, n, cached = fut.result()
            done += 1
            elapsed = time.time() - t0
            print(
                f"{done}/{len(dates)} {day.date()} rows={n} {'cache' if cached else 'fetch'} {elapsed:.0f}s",
                flush=True,
            )
    return dates


def load_market_main_range(start: str = "2014-12-31", end: str | None = None) -> pd.DataFrame:
    frames = []
    for day in quarter_ends(start, end):
        df = read_frame(market_main_path(day))
        if df is None or df.empty:
            continue
        df["REPORT_DATE"] = pd.to_datetime(df["REPORT_DATE"])
        if "SECURITY_CODE" in df.columns:
            df["SECURITY_CODE"] = df["SECURITY_CODE"].astype(str).str.zfill(6)
        frames.append(df)
    if not frames:
        return pd.DataFrame()
    out = pd.concat(frames, ignore_index=True)
    return out.drop_duplicates(["SECURITY_CODE", "REPORT_DATE"], keep="last")
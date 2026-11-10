"""头部宽基 ETF 持有规模占对应板块总市值。"""

from __future__ import annotations

import json
from concurrent.futures import ThreadPoolExecutor, as_completed

import pandas as pd

from cache_io import repo_root
from data_path import ensure_stock_data_on_path

ensure_stock_data_on_path()

from codes import load_security_names  # noqa: E402
from holdings import (  # noqa: E402
    fetch_board_caps,
    fetch_sse_etf_shares,
    fetch_szse_etf_shares,
)
from market import fetch_daily, fetch_index_daily  # noqa: E402

# 通达信基金日线按 3 位小数存储，现有读法按 2 位小数解析，价格放大了 10 倍。
PRICE_SCALE = 10.0
HEAD_RATIO = 0.10
HEAD_LIMIT = 4
HISTORY_START = "2022-01-01"

GROUPS = (
    {
        "id": "csi300",
        "label": "沪深300",
        "token": "沪深300ETF",
        "index": "sh000300",
        "index_name": "沪深300",
        "board": "all",
        "market_name": "全A",
    },
    {
        "id": "star50",
        "label": "科创50",
        "token": "科创50ETF",
        "index": "sh000688",
        "index_name": "科创50",
        "board": "star",
        "market_name": "科创板",
    },
    {
        "id": "chinext",
        "label": "创业板",
        "token": "创业板ETF",
        "index": "sz399006",
        "index_name": "创业板指",
        "board": "chinext",
        "market_name": "创业板",
    },
)


def _raw_dir():
    path = repo_root() / "cache" / "etf_holdings_src"
    path.mkdir(parents=True, exist_ok=True)
    return path


def _is_sh(code: str) -> bool:
    return code.startswith(("5", "6", "9"))


def _stamp(day) -> str:
    return pd.Timestamp(day).strftime("%Y%m%d")


def _etf_bars(code: str) -> pd.DataFrame | None:
    try:
        bars = fetch_daily(code, start_date="2018-01-01", adjust="bfq")
    except (FileNotFoundError, ValueError):
        return None
    if bars.empty:
        return None
    bars = bars.copy()
    bars["date"] = pd.to_datetime(bars["date"]).dt.normalize()
    bars["px"] = bars["close"] / PRICE_SCALE
    return bars


def _latest_share_map(asof: pd.Timestamp) -> dict[str, float]:
    day = _stamp(asof)
    sse = fetch_sse_etf_shares(day)
    sz = fetch_szse_etf_shares(day, day)
    shares = dict(zip(sse["code"], sse["shares"]))
    shares.update(dict(zip(sz["code"], sz["shares"])))
    return {code: float(value) for code, value in shares.items() if pd.notna(value)}


def _select_heads(rows: list[dict]) -> list[dict]:
    ranked = sorted(rows, key=lambda item: item["aum"], reverse=True)
    if not ranked:
        return []
    floor = ranked[0]["aum"] * HEAD_RATIO
    return [item for item in ranked if item["aum"] >= floor][:HEAD_LIMIT]


def _weekly_ohlc(daily: pd.DataFrame) -> pd.DataFrame:
    frame = daily.copy()
    frame["week"] = frame["date"].dt.to_period("W-FRI")
    rows = []
    for _, group in frame.groupby("week", sort=True):
        rows.append(
            {
                "date": pd.Timestamp(group["date"].iloc[-1]).normalize(),
                "open": float(group["open"].iloc[0]),
                "high": float(group["high"].max()),
                "low": float(group["low"].min()),
                "close": float(group["close"].iloc[-1]),
            }
        )
    return pd.DataFrame(rows)


def _ensure_szse(codes: list[str], start: pd.Timestamp, end: pd.Timestamp) -> pd.DataFrame:
    folder = _raw_dir() / "szse"
    folder.mkdir(parents=True, exist_ok=True)
    frames = []
    cursor = pd.Timestamp(start)
    while cursor <= end:
        chunk_end = min(cursor + pd.DateOffset(months=6) - pd.Timedelta(days=1), pd.Timestamp(end))
        path = folder / f"{cursor:%Y%m%d}_{chunk_end:%Y%m%d}.csv"
        if not path.exists():
            print(f"深交所份额 {cursor:%Y-%m-%d} 至 {chunk_end:%Y-%m-%d}", flush=True)
            raw = fetch_szse_etf_shares(_stamp(cursor), _stamp(chunk_end))
            raw = raw[raw["code"].isin(codes)]
            raw.to_csv(path, index=False)
        frames.append(pd.read_csv(path, parse_dates=["date"], dtype={"code": str}))
        cursor = chunk_end + pd.Timedelta(days=1)
    if not frames:
        return pd.DataFrame(columns=["date", "code", "shares"])
    out = pd.concat(frames, ignore_index=True)
    out["date"] = pd.to_datetime(out["date"]).dt.normalize()
    return out


def _week_path(day: pd.Timestamp):
    folder = _raw_dir() / "weeks"
    folder.mkdir(parents=True, exist_ok=True)
    return folder / f"{_stamp(day)}.json"


def _fetch_week(day: pd.Timestamp, sh_codes: list[str]) -> None:
    path = _week_path(day)
    if path.exists():
        return
    last_error = "empty"
    for _ in range(3):
        try:
            shares = fetch_sse_etf_shares(_stamp(day))
            caps = fetch_board_caps(_stamp(day))
        except Exception as exc:  # noqa: BLE001
            last_error = str(exc)
            continue
        if caps is None:
            last_error = "no market cap"
            continue
        table = shares.drop_duplicates("code").set_index("code")["shares"]
        kept = {}
        for code in sh_codes:
            if code in table.index and pd.notna(table.loc[code]):
                kept[code] = float(table.loc[code])
        path.write_text(json.dumps({"shares": kept, "caps": caps}, ensure_ascii=False), encoding="utf-8")
        return
    print(f"跳过 {_stamp(day)} {last_error}", flush=True)


def _ensure_weeks(dates: list[pd.Timestamp], sh_codes: list[str]) -> None:
    missing = [day for day in dates if not _week_path(day).exists()]
    if not missing:
        return
    print(f"补交易所周数据 {len(missing)} 天", flush=True)
    done = 0
    with ThreadPoolExecutor(max_workers=8) as pool:
        futures = [pool.submit(_fetch_week, day, sh_codes) for day in missing]
        for future in as_completed(futures):
            future.result()
            done += 1
            if done % 40 == 0 or done == len(missing):
                print(f"  {done}/{len(missing)}", flush=True)


def _load_week(day: pd.Timestamp) -> dict | None:
    path = _week_path(day)
    if not path.exists():
        return None
    payload = json.loads(path.read_text(encoding="utf-8"))
    if "caps" not in payload:
        return None
    return payload



def _flow_summary(weekly: pd.DataFrame) -> dict:
    """用份额看申购赎回。高点之后的低点到现在，净申购占当前份额的比例。"""
    frame = weekly.reset_index(drop=True)
    peak_at = int(frame["shares"].idxmax())
    trough_at = int(frame.iloc[peak_at:]["shares"].idxmin())
    now = frame.iloc[-1]
    peak = frame.iloc[peak_at]
    trough = frame.iloc[trough_at]
    now_shares = float(now["shares"])
    added = now_shares - float(trough["shares"])
    added_pct = added / now_shares * 100.0 if now_shares else 0.0

    def yi(value: float) -> str:
        return f"{value / 1e8:.0f}"

    def day(row) -> str:
        return pd.Timestamp(row["date"]).strftime("%Y-%m-%d")

    if trough_at == len(frame) - 1 and peak_at < trough_at:
        text = (
            f"份额高点在 {day(peak)}（{yi(float(peak['shares']))} 亿份），"
            f"之后净赎回，当前 {yi(now_shares)} 亿份。"
        )
    elif trough_at == peak_at:
        first = frame.iloc[0]
        text = (
            f"份额从 {day(first)} 的 {yi(float(first['shares']))} 亿份"
            f"增加到当前 {yi(now_shares)} 亿份。"
        )
    else:
        text = (
            f"份额高点 {day(peak)} {yi(float(peak['shares']))} 亿份，"
            f"之后低点 {day(trough)} {yi(float(trough['shares']))} 亿份，"
            f"低点至今净申购 {yi(added)} 亿份，占当前 {yi(now_shares)} 亿份的 {added_pct:.0f}%。"
        )
    return {
        "text": text,
        "peak_date": day(peak),
        "trough_date": day(trough),
        "now_shares_yi": round(now_shares / 1e8, 2),
        "added_since_trough_pct": round(added_pct, 1),
    }


def build_etf_market_share() -> list[dict]:
    """三组头部 ETF 的周持有规模、板块总市值和占比。"""
    asof = pd.Timestamp(fetch_index_daily("sh000300", start_date="2020-01-01")["date"].iloc[-1]).normalize()
    share_map = _latest_share_map(asof)
    names = load_security_names()
    selected = []
    sh_codes: set[str] = set()
    sz_codes: set[str] = set()
    for spec in GROUPS:
        rows = []
        for code, name in names.items():
            if spec["token"] not in name or code not in share_map:
                continue
            bars = _etf_bars(code)
            if bars is None:
                continue
            px = float(bars.iloc[-1]["px"])
            rows.append(
                {
                    "group": spec["id"],
                    "code": code,
                    "name": name,
                    "shares": share_map[code],
                    "px": px,
                    "aum": share_map[code] * px,
                    "bars": bars,
                }
            )
        heads = _select_heads(rows)
        if not heads:
            raise ValueError(f"没有选中 {spec['token']}")
        for item in heads:
            (sh_codes if _is_sh(item["code"]) else sz_codes).add(item["code"])
        selected.append((spec, heads))

    anchor = _weekly_ohlc(fetch_index_daily("sh000300", start_date=HISTORY_START))
    week_dates = [pd.Timestamp(day).normalize() for day in anchor["date"]]
    sz_shares = _ensure_szse(sorted(sz_codes), week_dates[0], week_dates[-1])
    sz_lookup = {
        (pd.Timestamp(row.date).normalize(), str(row.code).zfill(6)): float(row.shares)
        for row in sz_shares.itertuples(index=False)
    }
    _ensure_weeks(week_dates, sorted(sh_codes))

    groups = []
    for spec, heads in selected:
        index = fetch_index_daily(spec["index"], start_date=HISTORY_START)
        ohlc = _weekly_ohlc(index).set_index("date")
        price_maps = {item["code"]: item["bars"].set_index("date")["px"] for item in heads}
        rows = []
        last_held: dict[str, float] = {}
        for day in week_dates:
            payload = _load_week(day)
            if payload is None or day not in ohlc.index:
                continue
            cap = float(payload["caps"][spec["board"]])
            aum = 0.0
            total_shares = 0.0
            held: dict[str, float] = {}
            for item in heads:
                code = item["code"]
                if _is_sh(code):
                    shares = payload["shares"].get(code)
                else:
                    shares = sz_lookup.get((day, code))
                series = price_maps[code]
                if shares is None or day not in series.index or pd.isna(series.loc[day]):
                    continue
                held[code] = float(shares)
                total_shares += float(shares)
                aum += float(shares) * float(series.loc[day])
            if aum <= 0 or cap <= 0 or total_shares <= 0:
                continue
            bar = ohlc.loc[day]
            rows.append(
                {
                    "group": spec["id"],
                    "label": spec["label"],
                    "date": day,
                    "open": float(bar["open"]),
                    "high": float(bar["high"]),
                    "low": float(bar["low"]),
                    "close": float(bar["close"]),
                    "aum": aum,
                    "market_cap": cap,
                    "share_pct": aum / cap * 100.0,
                    "shares": total_shares,
                }
            )
            last_held = held
        weekly = pd.DataFrame(rows)
        members = [
            {
                "group": spec["id"],
                "code": item["code"],
                "name": item["name"],
                "aum_yi": round(item["aum"] / 1e8, 2),
                "shares_yi": round(last_held.get(item["code"], 0.0) / 1e8, 2),
            }
            for item in heads
        ]
        groups.append({**spec, "asof": asof, "members": members, "weekly": weekly, "flow": _flow_summary(weekly)})
    return groups

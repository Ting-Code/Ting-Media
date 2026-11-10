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
from market import fetch_boards_daily_amount, fetch_daily, fetch_index_daily  # noqa: E402

# 通达信基金日线按 3 位小数存储，现有读法按 2 位小数解析，价格放大了 10 倍。
PRICE_SCALE = 10.0
HEAD_RATIO = 0.10
HEAD_LIMIT = 4
HISTORY_START = "2022-01-01"
ANOMALY_START = "2013-01-04"

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
        bars = fetch_daily(code, start_date="2013-01-01", adjust="bfq")
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
        tried_path = path.with_suffix(".tried")
        tried = set(tried_path.read_text(encoding="utf-8").split()) if tried_path.exists() else set()
        if path.exists():
            have = set(pd.read_csv(path, dtype={"code": str})["code"].astype(str).str.zfill(6))
        else:
            have = set()
        if any(code not in have and code not in tried for code in codes):
            print(f"深交所份额 {cursor:%Y-%m-%d} 至 {chunk_end:%Y-%m-%d}", flush=True)
            raw = fetch_szse_etf_shares(_stamp(cursor), _stamp(chunk_end))
            raw["code"] = raw["code"].astype(str).str.zfill(6)
            keep = set(codes) | have
            raw = raw[raw["code"].isin(keep)]
            raw.to_csv(path, index=False)
            tried |= set(codes)
            tried_path.write_text('\n'.join(sorted(tried)) + '\n', encoding="utf-8")
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


def _fetch_week(day: pd.Timestamp, sh_codes: list[str], need_caps: bool = True) -> None:
    path = _week_path(day)
    if path.exists():
        payload = json.loads(path.read_text(encoding="utf-8"))
        shares_map = payload.get("shares") or {}
        missing = [code for code in sh_codes if code not in shares_map]
        if not missing:
            if need_caps and not payload.get("caps") and day >= pd.Timestamp(HISTORY_START):
                try:
                    caps = fetch_board_caps(_stamp(day))
                except Exception as exc:  # noqa: BLE001
                    print(f"跳过总市值 {_stamp(day)} {exc}", flush=True)
                    return
                if caps:
                    payload["caps"] = caps
                    path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
            return
        try:
            fresh = fetch_sse_etf_shares(_stamp(day)).drop_duplicates("code").set_index("code")["shares"]
        except Exception as exc:  # noqa: BLE001
            print(f"跳过 {_stamp(day)} {exc}", flush=True)
            return
        for code in missing:
            value = fresh.get(code) if code in fresh.index else None
            shares_map[code] = float(value) if value is not None and pd.notna(value) else None
        payload["shares"] = shares_map
        path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
        return
    last_error = "empty"
    shares = None
    caps = None
    for _ in range(3):
        try:
            if shares is None:
                shares = fetch_sse_etf_shares(_stamp(day))
            if need_caps and caps is None and day >= pd.Timestamp(HISTORY_START):
                caps = fetch_board_caps(_stamp(day))
        except Exception as exc:  # noqa: BLE001
            last_error = str(exc)
            continue
        if shares is not None and (not need_caps or caps is not None or day < pd.Timestamp(HISTORY_START)):
            break
    else:
        if shares is None:
            print(f"跳过 {_stamp(day)} {last_error}", flush=True)
            return
    if shares is None:
        print(f"跳过 {_stamp(day)} {last_error}", flush=True)
        return
    table = shares.drop_duplicates("code").set_index("code")["shares"]
    kept = {}
    for code in sh_codes:
        if code in table.index and pd.notna(table.loc[code]):
            kept[code] = float(table.loc[code])
        else:
            kept[code] = None
    path.write_text(json.dumps({"shares": kept, "caps": caps}, ensure_ascii=False), encoding="utf-8")


def _week_needs_codes(day: pd.Timestamp, sh_codes: list[str], need_caps: bool = True) -> bool:
    path = _week_path(day)
    if not path.exists():
        return True
    payload = json.loads(path.read_text(encoding="utf-8"))
    shares = payload.get("shares") or {}
    if any(code not in shares for code in sh_codes):
        return True
    return bool(need_caps and not payload.get("caps") and day >= pd.Timestamp(HISTORY_START))


def _ensure_weeks(dates: list[pd.Timestamp], sh_codes: list[str], need_caps: bool = True) -> None:
    missing = [day for day in dates if _week_needs_codes(day, sh_codes, need_caps)]
    if not missing:
        return
    print(f"补交易所周数据 {len(missing)} 天", flush=True)
    done = 0
    with ThreadPoolExecutor(max_workers=8) as pool:
        futures = [pool.submit(_fetch_week, day, sh_codes, need_caps) for day in missing]
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
    text = "按当周头部合计。" + text
    return {
        "text": text,
        "peak_date": day(peak),
        "trough_date": day(trough),
        "now_shares_yi": round(now_shares / 1e8, 2),
        "added_since_trough_pct": round(added_pct, 1),
    }



def _long_index_daily(index_code: str, sina_symbol: str) -> pd.DataFrame:
    """指数日线。通达信覆盖的日期用通达信。更早的日期只用已缓存、且早于通达信起点的新浪。"""
    local = fetch_index_daily(index_code, start_date="1990-01-01")
    local = local.copy()
    local["date"] = pd.to_datetime(local["date"]).dt.normalize()
    first = pd.Timestamp(local["date"].iloc[0])
    start = pd.Timestamp(ANOMALY_START)
    cols = ["date", "open", "high", "low", "close"]
    local = local.loc[local["date"] >= start, cols]
    if first <= start:
        return local.reset_index(drop=True)
    path = _raw_dir() / f"{sina_symbol}_before_tdx.csv"
    if not path.exists():
        return local.reset_index(drop=True)
    early = pd.read_csv(path, parse_dates=["date"])
    early["date"] = pd.to_datetime(early["date"]).dt.normalize()
    early = early[(early["date"] >= start) & (early["date"] < first)]
    if early.empty:
        return local.reset_index(drop=True)
    out = pd.concat([early[cols], local], ignore_index=True)
    return out.sort_values("date").drop_duplicates("date").reset_index(drop=True)


def _anomaly_held(
    dates: list[pd.Timestamp],
    ohlc: pd.DataFrame,
    sz_lookup: dict,
    codes: tuple[str, ...] = ("510300", "510310", "510330", "159919"),
    min_names: int = 3,
) -> list[dict]:
    rows = []
    sh_codes = [code for code in codes if _is_sh(code)]
    sz_codes = [code for code in codes if not _is_sh(code)]
    for day in dates:
        payload = _load_week(day)
        if payload is None or day not in ohlc.index:
            continue
        held: dict[str, float] = {}
        shares = payload.get("shares") or {}
        for code in sh_codes:
            value = shares.get(code)
            if value is not None:
                held[code] = float(value)
        for code in sz_codes:
            value = sz_lookup.get((day, code))
            if value is not None:
                held[code] = float(value)
        if len(held) < min_names:
            continue
        rows.append({"date": day, "close": float(ohlc.loc[day, "close"]), "held": held})
    return rows


def _csi_anomaly(
    path: list[dict],
    codes: tuple[str, ...] = ("510300", "510310", "510330", "159919"),
    total_min: float = 40,
    each_min: float = 5,
    sync_min: int = 3,
) -> list[dict]:
    """周净申购异动。逆势同步：指数下跌、合计达到门槛、足够多只各自超过单只门槛。"""
    out = []
    prev = None
    prev_close = None
    prev_date = None
    for row in path:
        held = row["held"]
        close = float(row["close"])
        if prev is not None and prev_close:
            if (pd.Timestamp(row["date"]) - pd.Timestamp(prev_date)).days > 12:
                prev = held
                prev_close = close
                prev_date = row["date"]
                continue
            deltas = {}
            wanted = row["heads"] if "heads" in row else codes
            for code in wanted:
                if code in held and code in prev:
                    deltas[code] = (held[code] - prev[code]) / 1e8
            total = sum(deltas.values())
            buy_sync = sum(1 for value in deltas.values() if value > each_min)
            sell_sync = sum(1 for value in deltas.values() if value < -each_min)
            sync = sell_sync if total < 0 else buy_sync
            ret = close / prev_close - 1
            if buy_sync >= sync_min and total >= total_min and ret < 0:
                kind = "counter"
            elif buy_sync >= sync_min and total >= total_min:
                kind = "syncup"
            elif total <= -total_min:
                kind = "sell"
            elif total > 0 and ret >= 0:
                kind = "chase"
            else:
                kind = "other"
            out.append(
                {
                    "date": pd.Timestamp(row["date"]).strftime("%Y-%m-%d"),
                    "close": round(close, 2),
                    "total": round(total, 2),
                    "sync": sync,
                    "ret": round(ret * 100, 2),
                    "kind": kind,
                }
            )
        prev = held
        prev_close = close
        prev_date = row["date"]
    return out



def _board_amount(boards: dict[str, pd.DataFrame], key: str) -> pd.Series:
    names = ("main", "star", "chinext") if key == "all" else (key,)
    parts = [boards[name].set_index("date")["amount"] for name in names]
    frame = pd.concat(parts, axis=1).fillna(0.0)
    series = frame.sum(axis=1)
    series.index = pd.to_datetime(series.index).normalize()
    return series.groupby(series.index).sum()


def _weekly_turn(index: pd.DataFrame, amounts: list[pd.Series], board: pd.Series) -> pd.DataFrame:
    """当周成交额合计。周标签用指数这周最后一个交易日。"""
    frame = index.loc[:, ["date"]].copy()
    frame["date"] = pd.to_datetime(frame["date"]).dt.normalize()
    frame = frame[frame["date"] >= pd.Timestamp(HISTORY_START)]
    frame["week"] = frame["date"].dt.to_period("W-FRI")
    etf = None
    for series in amounts:
        values = series.copy()
        values.index = pd.to_datetime(values.index).normalize()
        values = values.groupby(values.index).sum()
        etf = values if etf is None else etf.add(values, fill_value=0.0)
    rows = []
    for _, group in frame.groupby("week", sort=True):
        days = [pd.Timestamp(day).normalize() for day in group["date"]]
        end = days[-1]
        board_amount = float(board.reindex(days).fillna(0.0).sum())
        etf_amount = float(etf.reindex(days).fillna(0.0).sum()) if etf is not None else 0.0
        if board_amount <= 0:
            continue
        rows.append(
            {
                "date": end,
                "etf_amount": etf_amount,
                "board_amount": board_amount,
                "turn_pct": etf_amount / board_amount * 100.0,
            }
        )
    return pd.DataFrame(rows)



def _week_books(day, candidates: list[dict], sh_lookup: dict, sz_lookup: dict):
    """按当天持有规模重选头部。返回头部名单，以及当天有行情的全部候选份额。"""
    ranked = []
    held = {}
    for item in candidates:
        code = item["code"]
        shares = sh_lookup.get((day, code)) if _is_sh(code) else sz_lookup.get((day, code))
        series = item["px"]
        if shares is None or day not in series.index or pd.isna(series.loc[day]):
            continue
        shares = float(shares)
        px = float(series.loc[day])
        held[code] = shares
        ranked.append({"code": code, "name": item["name"], "shares": shares, "aum": shares * px})
    return _select_heads(ranked), held


def build_etf_market_share() -> list[dict]:
    """三组头部 ETF 的周持有规模、板块总市值和占比。"""
    asof = pd.Timestamp(fetch_index_daily("sh000300", start_date="2020-01-01")["date"].iloc[-1]).normalize()
    names = load_security_names()
    selected = []
    sh_codes: set[str] = set()
    sz_codes: set[str] = set()
    for spec in GROUPS:
        rows = []
        for code, name in names.items():
            if spec["token"] not in name:
                continue
            bars = _etf_bars(code)
            if bars is None:
                continue
            rows.append({"group": spec["id"], "code": code, "name": name, "px": bars.set_index("date")["px"]})
            (sh_codes if _is_sh(code) else sz_codes).add(code)
        if not rows:
            raise ValueError(f"没有选中 {spec['token']}")
        selected.append((spec, rows))

    rules = (
        {"id": "csi300", "index": "sh000300", "sina": "sh000300", "total": 40, "each": 5, "sync": 3},
        {"id": "star50", "index": "sh000688", "sina": "sh000688", "total": 40, "each": 5, "sync": 2},
        {"id": "chinext", "index": "sz399006", "sina": "sz399006", "total": 20, "each": 2, "sync": 2},
    )
    ohlc_by_id = {}
    all_dates: list[pd.Timestamp] = []
    for rule in rules:
        ohlc = _weekly_ohlc(_long_index_daily(rule["index"], rule["sina"])).set_index("date")
        ohlc_by_id[rule["id"]] = ohlc
        all_dates.extend(pd.Timestamp(day).normalize() for day in ohlc.index)
    all_dates = sorted(set(all_dates))
    print(f"候选份额 沪市 {len(sh_codes)} 只，深市 {len(sz_codes)} 只", flush=True)
    _ensure_weeks(all_dates, sorted(sh_codes), need_caps=True)
    sz_frame = _ensure_szse(sorted(sz_codes), pd.Timestamp("2013-01-03"), all_dates[-1])
    sz_lookup = {
        (pd.Timestamp(row.date).normalize(), str(row.code).zfill(6)): float(row.shares)
        for row in sz_frame.itertuples(index=False)
        if pd.notna(row.shares)
    }
    sh_lookup: dict[tuple, float] = {}
    caps_by_day: dict[pd.Timestamp, dict] = {}
    for day in all_dates:
        payload = _load_week(day)
        if not payload:
            continue
        for code, value in (payload.get("shares") or {}).items():
            if value is not None:
                sh_lookup[(day, str(code))] = float(value)
        if payload.get("caps"):
            caps_by_day[day] = payload["caps"]

    groups = []
    history_start = pd.Timestamp(HISTORY_START)
    for spec, candidates in selected:
        rule = next(item for item in rules if item["id"] == spec["id"])
        ohlc = ohlc_by_id[spec["id"]]
        rows = []
        anomaly_path = []
        last_heads: list[dict] = []
        for day in ohlc.index:
            day = pd.Timestamp(day).normalize()
            heads, held = _week_books(day, candidates, sh_lookup, sz_lookup)
            if not heads:
                continue
            bar = ohlc.loc[day]
            anomaly_path.append(
                {
                    "date": day,
                    "close": float(bar["close"]),
                    "held": held,
                    "heads": [item["code"] for item in heads],
                }
            )
            last_heads = heads
            caps = caps_by_day.get(day)
            cap = float(caps[spec["board"]]) if caps else 0.0
            aum = sum(item["aum"] for item in heads)
            total_shares = sum(item["shares"] for item in heads)
            if aum <= 0 or total_shares <= 0:
                continue
            use_cap = bool(caps) and cap > 0 and day >= history_start
            rows.append(
                {
                    "group": spec["id"],
                    "label": spec["label"],
                    "date": day,
                    "heads": " ".join(item["code"] for item in heads),
                    "open": float(bar["open"]),
                    "high": float(bar["high"]),
                    "low": float(bar["low"]),
                    "close": float(bar["close"]),
                    "aum": aum,
                    "market_cap": cap if use_cap else float("nan"),
                    "share_pct": aum / cap * 100.0 if use_cap else float("nan"),
                    "shares": total_shares,
                }
            )
        weekly = pd.DataFrame(rows)
        members = [
            {
                "group": spec["id"],
                "code": item["code"],
                "name": item["name"],
                "aum_yi": round(item["aum"] / 1e8, 2),
                "shares_yi": round(item["shares"] / 1e8, 2),
            }
            for item in last_heads
        ]
        groups.append(
            {
                **spec,
                "asof": asof,
                "members": members,
                "weekly": weekly,
                "flow": _flow_summary(weekly),
                "anomaly": _csi_anomaly(
                    anomaly_path,
                    tuple(item["code"] for item in candidates),
                    rule["total"],
                    rule["each"],
                    rule["sync"],
                ),
                "anomaly_rule": rule,
            }
        )
    return groups

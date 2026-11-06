#!/usr/bin/env python3
"""Walk-forward backtest: accumulation_shrink_hold as-of -> forward returns / breakout."""

from __future__ import annotations

import argparse
import json
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

import pandas as pd
import yaml

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT.parent / "stock-data" / "src"))

import filters  # noqa: F401
from filters.pattern import accumulation_shrink_hold
from indicators import enrich_row
from universe import build_universe
from tdx_day import read_day_file


def _load_one(item: dict):
    try:
        df = read_day_file(Path(item["path"]))
    except Exception:
        return None
    if df is None or df.empty or len(df) < 120:
        return None
    df = df.copy()
    df["date"] = pd.to_datetime(df["date"])
    for c in ("open", "high", "low", "close", "volume", "amount"):
        if c in df.columns:
            df[c] = df[c].astype(float)
    return item["code"], df


def trading_asofs(all_dates, start: str, end: str, step: int):
    dates = [d for d in all_dates if pd.Timestamp(start) <= d <= pd.Timestamp(end)]
    return dates[:: max(1, step)]


def forward_stats(full: pd.DataFrame, asof_i: int, box_high: float, cost: float, horizons=(5, 10, 20)) -> dict:
    entry = float(full["close"].iloc[asof_i])
    out = {"entry": entry}
    for h in horizons:
        end = min(len(full) - 1, asof_i + h)
        if end <= asof_i:
            out[f"ret_{h}d"] = None
            out[f"max_ret_{h}d"] = None
            out[f"min_ret_{h}d"] = None
            continue
        window = full.iloc[asof_i + 1 : end + 1]
        last = float(window["close"].iloc[-1])
        hi = float(window["high"].max())
        lo = float(window["low"].min())
        out[f"ret_{h}d"] = (last / entry - 1.0) * 100.0
        out[f"max_ret_{h}d"] = (hi / entry - 1.0) * 100.0
        out[f"min_ret_{h}d"] = (lo / entry - 1.0) * 100.0
    end20 = min(len(full) - 1, asof_i + 20)
    if end20 > asof_i:
        w = full.iloc[asof_i + 1 : end20 + 1]
        out["break_box_20d"] = bool(float(w["high"].max()) >= box_high * 1.03)
        out["break_cost_down_20d"] = bool(float(w["low"].min()) < cost * 0.97)
        days_to_break = None
        for j in range(len(w)):
            if float(w["high"].iloc[j]) >= box_high * 1.03:
                days_to_break = j + 1
                break
        out["days_to_break"] = days_to_break
    else:
        out["break_box_20d"] = None
        out["break_cost_down_20d"] = None
        out["days_to_break"] = None
    return out


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--config", default="configs/v1_accum_shrink_hold.yaml")
    ap.add_argument("--start", default="2025-01-01")
    ap.add_argument("--end", default="2026-09-30")
    ap.add_argument("--step", type=int, default=15)
    ap.add_argument("--workers", type=int, default=8)
    ap.add_argument("--max-bars", type=int, default=200)
    args = ap.parse_args()

    cfg_path = Path(args.config)
    if not cfg_path.is_file():
        cfg_path = ROOT / args.config
    cfg = yaml.safe_load(cfg_path.read_text(encoding="utf-8"))
    params = dict((cfg.get("filters") or [{}])[0].get("params") or {})
    vipdoc = (cfg.get("tdx") or {}).get("vipdoc") or "D:/app/tdx/vipdoc"
    uni = build_universe(vipdoc, cfg.get("universe") or {})

    print(f"loading bars universe={len(uni)} ...", flush=True)
    bars = {}
    meta = {i["code"]: i for i in uni}
    with ThreadPoolExecutor(max_workers=max(1, args.workers)) as ex:
        futs = [ex.submit(_load_one, it) for it in uni]
        for fut in as_completed(futs):
            r = fut.result()
            if r:
                bars[r[0]] = r[1]
    print(f"loaded={len(bars)}", flush=True)

    cal_code = "600519" if "600519" in bars else next(iter(bars))
    all_dates = pd.DatetimeIndex(sorted(bars[cal_code]["date"].unique()))
    asofs = trading_asofs(all_dates, args.start, args.end, args.step)
    print(f"asofs={len(asofs)} {asofs[0].date()} -> {asofs[-1].date()} step={args.step}", flush=True)

    rows = []
    for ai, asof in enumerate(asofs, start=1):
        hits = 0
        for code, full in bars.items():
            full_pos = full.reset_index(drop=True)
            mask = full_pos["date"] <= asof
            if not mask.any():
                continue
            f_i = int(full_pos.index[mask][-1])
            if f_i + 5 >= len(full_pos):
                continue
            sub2 = full_pos.iloc[: f_i + 1].tail(args.max_bars).reset_index(drop=True)
            if len(sub2) < 120:
                continue
            row = {**meta[code], **enrich_row(sub2), "_bars": sub2}
            try:
                ok = accumulation_shrink_hold(row, params)
            except Exception:
                continue
            if not ok:
                continue
            hits += 1
            box_high = float(row["pattern_box_high"])
            cost = float(row["pattern_cost_anchor"])
            stats = forward_stats(full_pos, f_i, box_high, cost)
            rows.append(
                {
                    "asof": str(asof.date()),
                    "code": code,
                    "name": meta[code].get("name"),
                    "board": meta[code].get("board"),
                    "close": stats["entry"],
                    "box_low": row.get("pattern_box_low"),
                    "box_high": box_high,
                    "cost_anchor": cost,
                    "pull_vol_ratio": row.get("pattern_pull_vol_ratio"),
                    "peak": row.get("pattern_peak"),
                    **{k: v for k, v in stats.items() if k != "entry"},
                }
            )
        print(f"[{ai}/{len(asofs)}] asof={asof.date()} hits={hits} total_signals={len(rows)}", flush=True)

    repo = ROOT.parent.parent
    out_dir = repo / "cache" / f"backtest_accum_shrink_hold_{args.start[:4]}_{args.end[:4]}"
    out_dir.mkdir(parents=True, exist_ok=True)

    df = pd.DataFrame(rows)
    df.to_csv(out_dir / "signals.csv", index=False, encoding="utf-8-sig")

    summary = {
        "config": str(cfg_path),
        "start": args.start,
        "end": args.end,
        "step": args.step,
        "n_asofs": len(asofs),
        "n_signals": int(len(df)),
        "n_unique_codes": int(df["code"].nunique()) if len(df) else 0,
        "note": "break_box_20d = high>=box_high*1.03 within 20 trading days",
    }
    if len(df):
        for h in (5, 10, 20):
            col = f"ret_{h}d"
            s = df[col].dropna()
            summary[f"avg_{col}"] = float(s.mean()) if len(s) else None
            summary[f"med_{col}"] = float(s.median()) if len(s) else None
            summary[f"winrate_{col}"] = float((s > 0).mean()) if len(s) else None
            mx = df[f"max_ret_{h}d"].dropna()
            summary[f"avg_max_{h}d"] = float(mx.mean()) if len(mx) else None
        b = df["break_box_20d"].dropna()
        d = df["break_cost_down_20d"].dropna()
        summary["break_box_20d_rate"] = float(b.mean()) if len(b) else None
        summary["break_cost_down_20d_rate"] = float(d.mean()) if len(d) else None
        good = df.dropna(subset=["break_box_20d", "break_cost_down_20d"])
        if len(good):
            summary["breakout_hold_cost_rate"] = float(
                ((good["break_box_20d"] == True) & (good["break_cost_down_20d"] == False)).mean()
            )
        dtb = df["days_to_break"].dropna()
        summary["avg_days_to_break"] = float(dtb.mean()) if len(dtb) else None

    (out_dir / "summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    print(f"wrote {out_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

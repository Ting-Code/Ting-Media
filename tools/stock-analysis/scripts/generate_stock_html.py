"""Generate episode HTML using stock-data + local deck renderer.

Usage:
  python scripts/generate_stock_html.py <名称或代码>
  python scripts/generate_stock_html.py 300750 --theme 主题
  python scripts/generate_stock_html.py 300750 --date YYYY-MM-DD --niche finance
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import date, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from _pathsetup import ensure_stock_data_on_path

ensure_stock_data_on_path()

from codes import resolve_code
from episode_path import episode_dir
from fundamentals import build_fundamental_panel, fetch_dividends
from market import fetch_daily
from render_report import render_html
from valuation import build_valuation_series, current_snapshot


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate 9:16 PPT episode HTML")
    parser.add_argument("query", nargs="?", default="300750", help="名称或代码")
    parser.add_argument("--theme", default="", help="期节目主题（默认：{名}）")
    parser.add_argument("--date", default="", help="节目日期 YYYY-MM-DD（默认今天）")
    parser.add_argument("--niche", default="finance", help="赛道目录名（默认 finance）")
    args = parser.parse_args()

    code, name = resolve_code(args.query)
    if name == code:
        name = args.query
    theme = args.theme.strip() or name
    day = date.fromisoformat(args.date) if args.date else date.today()

    print("[1/4] daily", code)
    daily = fetch_daily(code, start_date="2018-01-01")
    print(
        "  bars",
        len(daily),
        "last",
        daily["date"].iloc[-1].date(),
        "close",
        round(float(daily["close"].iloc[-1]), 2),
    )

    print("[2/4] fundamentals")
    fundamentals = build_fundamental_panel(code)
    dividends = fetch_dividends(code)
    print("  quarters", len(fundamentals), "dividends", len(dividends))

    print("[3/4] valuation")
    valuation = build_valuation_series(fundamentals, daily, dividends)
    snap = current_snapshot(fundamentals, daily, dividends)
    pe, pb, dv = snap["pe_ttm_deduct"], snap["pb"], snap["div_yield_pct"]
    print(
        "  points",
        len(valuation),
        "PE",
        None if pe is None else round(pe, 1),
        "PB",
        None if pb is None else round(pb, 2),
        "div",
        None if dv is None else round(dv, 2),
    )

    ep = episode_dir(niche=args.niche, theme=theme, day=day)
    ep.mkdir(parents=True, exist_ok=True)
    out = ep / "index.html"
    cache = ep / "cache"
    cache.mkdir(parents=True, exist_ok=True)

    print("[4/4] render ->", ep)
    path = render_html(
        name=name,
        code=code,
        daily=daily,
        fundamentals=fundamentals,
        valuation=valuation,
        snap=snap,
        out_path=out,
    )
    daily.to_csv(cache / "daily.csv", index=False)
    fundamentals.to_csv(cache / "fundamentals.csv", index=False)
    valuation.to_csv(cache / "valuation.csv", index=False)

    meta = {
        "niche": args.niche,
        "theme": theme,
        "date": day.isoformat(),
        "code": code,
        "name": name,
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "html": "index.html",
        "format": "9:16-ppt-deck",
        "data_tool": "tools/stock-data",
    }
    (ep / "meta.json").write_text(
        json.dumps(meta, ensure_ascii=False, indent=2) + chr(10),
        encoding="utf-8",
    )

    print("DONE", path)
    print("Open in browser:", path.resolve().as_uri())


if __name__ == "__main__":
    main()

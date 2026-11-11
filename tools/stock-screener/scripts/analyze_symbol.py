#!/usr/bin/env python3
"""单股或多股估值：PE、PB、股息率、历史分位。写出普通横版网页，不生成录屏 HTML。

用法：
  python scripts/analyze_symbol.py 600519
  python scripts/analyze_symbol.py 贵州茅台
  python scripts/analyze_symbol.py 00700 09988 01810
  python scripts/analyze_symbol.py --title 513330_top10 --heading "恒生互联网ETF前十 PE" 00700 09988
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

import pandas as pd

SRC = Path(__file__).resolve().parents[1] / "src"
sys.path.insert(0, str(SRC))

from data_path import ensure_stock_data_on_path  # noqa: E402

ensure_stock_data_on_path()

from analysis import (  # noqa: E402
    build_fundamental_panel,
    build_valuation_series,
    current_snapshot,
    percentile,
)
from cache_io import repo_root  # noqa: E402
from codes import hk_code5, is_hk, load_security_names, resolve_code  # noqa: E402
from valuation_page import write_valuation_group_page, write_valuation_page  # noqa: E402
from fundamentals import fetch_dividends  # noqa: E402
from market import fetch_daily  # noqa: E402
from market_panel import load_market_panels  # noqa: E402
from store import dividend_code_path, read_frame  # noqa: E402


def _num(v, nd=2):
    if v is None:
        return None
    return round(float(v), nd)


def _slug(title: str | None, folder_codes: list[str]) -> str:
    if title:
        slug = re.sub(r"[^\w\u4e00-\u9fff]+", "_", title, flags=re.UNICODE).strip("_")
        return slug[:80] or "group"
    if len(folder_codes) <= 4:
        return "-".join(folder_codes)
    return f"{folder_codes[0]}_etc{len(folder_codes)}"


def _cached_dividends(code: str):
    if is_hk(code):
        return None
    cached = read_frame(dividend_code_path(code))
    if cached is None or cached.empty:
        return None
    cached["report_date"] = pd.to_datetime(cached["report_date"])
    cached["ex_date"] = pd.to_datetime(cached["ex_date"])
    return cached


def _display_name(code: str, resolved: str, names: dict[str, str] | None) -> str:
    folder = hk_code5(code) if is_hk(code) else str(code)
    if resolved and resolved not in {code, folder, str(code).lstrip("0")}:
        return resolved
    if names:
        return names.get(str(code)) or names.get(folder) or resolved or folder
    return resolved or folder


def _analyze(query: str, *, panels=None, names=None, fetch_div: bool = True) -> tuple[str, str, object, dict]:
    import pandas as pd

    code, name = resolve_code(query)
    name = _display_name(code, name, names)
    start = "2013-01-01" if is_hk(code) else "2015-01-01"
    key = hk_code5(code) if is_hk(code) else str(code)
    panel = None
    if panels and not is_hk(code):
        panel = panels.get(str(code).zfill(6))
    if panel is None or (hasattr(panel, "empty") and panel.empty):
        panel = build_fundamental_panel(code)
    daily = fetch_daily(code, start_date=start, adjust="bfq")
    if fetch_div:
        dividends = fetch_dividends(code)
    else:
        dividends = _cached_dividends(code)
    if dividends is None:
        dividends = pd.DataFrame()
    series = build_valuation_series(panel, daily, dividends)
    snap = current_snapshot(panel, daily, dividends)
    asof = snap.get("asof")
    report = snap.get("report_date")
    out = {
        "code": code,
        "name": name,
        "asof": None if asof is None else str(asof)[:10],
        "price": _num(snap.get("price"), 2),
        "pe": _num(snap.get("pe"), 2),
        "pb": _num(snap.get("pb"), 2),
        "div_yield_pct": _num(snap.get("div_yield_pct"), 2),
        "pe_percentile": _num(percentile(series["pe"], snap.get("pe")) if not series.empty else None, 1),
        "pb_percentile": _num(percentile(series["pb"], snap.get("pb")) if not series.empty else None, 1),
        "div_percentile": _num(
            percentile(series["div_yield_pct"], snap.get("div_yield_pct")) if not series.empty else None,
            1,
        ),
        "report_date": None if report is None else str(report)[:10],
        "price_adjust": "unadjusted" if is_hk(code) else "bfq",
        "dividend_source": None if is_hk(code) else "eastmoney_report_period",
        "market": snap.get("market") or ("hk" if is_hk(code) else "a"),
        "currency_price": "HKD" if is_hk(code) else "CNY",
        "currency_financials": "CNY",
        "fx": "HKDCNYC" if is_hk(code) else None,
        "fx_cny_per_hkd": _num(snap.get("fx_cny_per_hkd"), 4) if is_hk(code) else None,
        "price_cny": _num(snap.get("price_cny"), 2) if is_hk(code) else None,
    }
    return code, name, series, out


def _write_single(name: str, code: str, series, summary: dict) -> Path:
    day = summary.get("asof") or "na"
    folder_code = hk_code5(code) if is_hk(code) else code
    folder = repo_root() / "cache" / f"pe_{folder_code}_{day}"
    return write_valuation_page(name, folder_code, series, summary, folder)


def main() -> int:
    ap = argparse.ArgumentParser(description="单股或多股 PE/PB 分析页（不是录屏 HTML）")
    ap.add_argument("symbols", nargs="*", help="名称或代码，多只时写出一张总览页")
    ap.add_argument("--symbols-file", default=None, help="每行一个代码或名称，可与位置参数一起用")
    ap.add_argument("--title", default=None, help="多股总览页目录名（cache/pe_<title>_<行情日>/）")
    ap.add_argument("--heading", default=None, help="多股总览页标题，默认用 --title")
    ap.add_argument("--lead", default=None, help="总览页导语前额外说明，例如持仓来源")
    ap.add_argument("--weights", default=None, help="与股票顺序对应的权重，逗号分隔，例如 15.09,14.92")
    ap.add_argument("--workers", type=int, default=1)
    args = ap.parse_args()

    symbols = list(args.symbols)
    if args.symbols_file:
        text = Path(args.symbols_file).read_text(encoding="utf-8")
        symbols.extend([ln.strip() for ln in text.splitlines() if ln.strip() and not ln.strip().startswith("#")])
    if not symbols:
        print("错误: 请提供股票代码或 --symbols-file", file=sys.stderr)
        return 2

    weights = None
    if args.weights:
        weights = [float(x) for x in args.weights.split(",") if x.strip() != ""]
        if len(weights) != len(symbols):
            print("错误: --weights 个数必须与股票只数相同", file=sys.stderr)
            return 2

    group = len(symbols) > 1 or args.title is not None
    fetch_div = len(symbols) <= 20
    names = load_security_names()
    panels = None
    if any(not is_hk(s) for s in symbols):
        try:
            panels = load_market_panels()
            print(f"market panels={len(panels)}", flush=True)
        except Exception as exc:
            print(f"market panels unavailable: {exc}", flush=True)
            panels = None

    def one(i: int, query: str):
        code, name, series, summary = _analyze(
            query, panels=panels, names=names, fetch_div=fetch_div
        )
        page = None if group else _write_single(name, code, series, summary)
        item = {
            "name": name,
            "code": hk_code5(code) if is_hk(code) else code,
            "series": series,
            "summary": summary,
        }
        if weights is not None:
            item["weight"] = weights[i]
        return i, item, page, summary

    results_slots: list = [None] * len(symbols)
    workers = max(1, int(args.workers))
    if workers == 1 or len(symbols) == 1:
        jobs = [one(i, q) for i, q in enumerate(symbols)]
    else:
        from concurrent.futures import ThreadPoolExecutor, as_completed
        jobs = []
        with ThreadPoolExecutor(max_workers=workers) as pool:
            futs = {pool.submit(one, i, q): i for i, q in enumerate(symbols)}
            done = 0
            for fut in as_completed(futs):
                rec = fut.result()
                jobs.append(rec)
                done += 1
                if done % 20 == 0 or done == len(symbols):
                    print(f"{done}/{len(symbols)} last={rec[1].get('code')} {rec[1].get('name')}", flush=True)
        jobs.sort(key=lambda r: r[0])

    results = []
    for i, item, page, summary in jobs:
        results.append(item)
        if not group:
            print(json.dumps(summary, ensure_ascii=False, indent=2))
            print(page, file=sys.stderr)

    if not group:
        return 0

    asofs = [r["summary"].get("asof") for r in results if r["summary"].get("asof")]
    day = max(asofs) if asofs else "na"
    folder_codes = [r["code"] for r in results]
    slug = _slug(args.title, folder_codes)
    heading = args.heading or args.title or f"{len(results)}只股票 PE"
    folder = repo_root() / "cache" / f"pe_{slug}_{day}"
    page = write_valuation_group_page(
        slug,
        results,
        folder,
        lead=args.lead,
        heading=heading,
    )
    print(page, file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

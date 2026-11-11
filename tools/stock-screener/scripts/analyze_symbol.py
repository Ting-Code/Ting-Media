#!/usr/bin/env python3
"""单股估值：PE、PB、股息率、历史分位。写出普通横版网页，不生成录屏 HTML。

用法：
  python scripts/analyze_symbol.py 600519
  python scripts/analyze_symbol.py 贵州茅台
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

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
from codes import hk_code5, is_hk, resolve_code  # noqa: E402
from valuation_page import write_valuation_page  # noqa: E402
from fundamentals import fetch_dividends  # noqa: E402
from market import fetch_daily  # noqa: E402


def _num(v, nd=2):
    if v is None:
        return None
    return round(float(v), nd)


def main() -> int:
    if len(sys.argv) < 2 or sys.argv[1] in ("-h", "--help"):
        print("用法: python scripts/analyze_symbol.py <名称或代码>", file=sys.stderr)
        return 2
    code, name = resolve_code(sys.argv[1])
    start = "2013-01-01" if is_hk(code) else "2015-01-01"
    panel = build_fundamental_panel(code)
    daily = fetch_daily(code, start_date=start, adjust="bfq")
    dividends = fetch_dividends(code)
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
    day = out["asof"] or "na"
    folder_code = hk_code5(code) if is_hk(code) else code
    page_code = folder_code
    folder = repo_root() / "cache" / f"pe_{folder_code}_{day}"
    page = write_valuation_page(name, page_code, series, out, folder)
    print(json.dumps(out, ensure_ascii=False, indent=2))
    print(page, file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

#!/usr/bin/env python3
"""全 A 股息率。最近四个已结束报告期的已实施现金 / 最新不复权收盘价。

用法：
  python scripts/div_yield.py
  python scripts/div_yield.py --top 50
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import pandas as pd

SRC = Path(__file__).resolve().parents[1] / "src"
sys.path.insert(0, str(SRC))

from data_path import ensure_stock_data_on_path  # noqa: E402

ensure_stock_data_on_path()

from analysis import a_share_dividend_yield, completed_quarter_ends  # noqa: E402
from cache_io import repo_root  # noqa: E402
from codes import load_security_names  # noqa: E402
from fundamentals import fetch_period_cash_dividends  # noqa: E402
from market import fetch_a_share_last_close  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description="全 A 股息率")
    parser.add_argument("--top", type=int, default=20, help="终端打印前 N 名，默认 20")
    args = parser.parse_args()

    prices = fetch_a_share_last_close()
    if prices.empty:
        print("没有读到日线收盘价", file=sys.stderr)
        return 1
    asof = pd.Timestamp(prices["asof"].mode().iloc[0])
    quarters = completed_quarter_ends(asof, 4)
    frames = []
    names: dict[str, str] = {}
    for quarter in quarters:
        part = fetch_period_cash_dividends(quarter.strftime("%Y%m%d"))
        if part.empty:
            continue
        frames.append(part)
        for code, name in zip(part["code"], part["name"]):
            if name and code not in names:
                names[code] = str(name)
    dividends = (
        pd.concat(frames, ignore_index=True)
        if frames
        else pd.DataFrame(columns=["code", "name", "report_date", "cash_per_share", "ex_date", "status"])
    )
    table = a_share_dividend_yield(prices, dividends)
    local_names = load_security_names()
    table.insert(1, "name", table["code"].map(lambda code: local_names.get(code) or names.get(code) or ""))

    day = asof.strftime("%Y-%m-%d")
    out = repo_root() / "cache" / f"div_yield_{day}"
    out.mkdir(parents=True, exist_ok=True)
    csv_path = out / "yield.csv"
    table.to_csv(csv_path, index=False, encoding="utf-8-sig", float_format="%.6f")
    qtext = "、".join(q.strftime("%Y-%m-%d") for q in quarters)
    (out / "source.txt").write_text(
        "\n".join(
            [
                "股息率 = 最近四个已结束报告期的已实施每股现金合计 / 最新不复权收盘价",
                "",
                "分子：东方财富分红送配，按定期报告期。字段「现金分红-现金分红比例」是每 10 股税前派现，每股 = 该数 / 10。",
                "只保留方案进度为实施、且除权除息日不晚于该股最新行情日的记录。这张表不收录特别分红。",
                f"四个报告期按全市场行情日 {day} 对齐：{qtext}。某一季没有实施分红记 0。",
                "",
                "分母：本机通达信 vipdoc 日线的不复权收盘价。",
                "名称：本机通达信 hq_cache 证券简称。",
                "",
            ]
        ),
        encoding="utf-8",
    )

    payers = table[table["dps"] > 0]
    print(f"行情日 {day}  全 A {len(table)}  有派息 {len(payers)}")
    if not payers.empty:
        y = payers["div_yield_pct"]
        print(
            f"有派息中位数 {y.median():.2f}%  前10%从 {y.quantile(0.9):.2f}% 起  "
            f">=3% {int((y >= 3).sum())}  >=5% {int((y >= 5).sum())}"
        )
    show = table.head(max(args.top, 0))
    if not show.empty:
        view = show[["code", "name", "close", "dps", "div_yield_pct"]].copy()
        view["div_yield_pct"] = view["div_yield_pct"].map(lambda v: None if pd.isna(v) else round(float(v), 2))
        print(view.to_string(index=False))
    print(csv_path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

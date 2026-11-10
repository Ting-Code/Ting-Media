#!/usr/bin/env python3
"""头部 ETF 持有规模占板块总市值，并写成静态网页。

用法：
  python scripts/etf_market_share.py
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pandas as pd

SRC = Path(__file__).resolve().parents[1] / "src"
sys.path.insert(0, str(SRC))

from data_path import ensure_stock_data_on_path  # noqa: E402

ensure_stock_data_on_path()

from cache_io import repo_root  # noqa: E402
from etf_page import write_page  # noqa: E402
from etf_share import build_etf_market_share  # noqa: E402


def main() -> int:
    groups = build_etf_market_share()
    asof = pd.Timestamp(groups[0]["asof"])
    day = asof.strftime("%Y-%m-%d")
    out = repo_root() / "cache" / f"etf_market_share_{day}"
    out.mkdir(parents=True, exist_ok=True)
    for stale in ("chart.png", "daily.csv"):
        path = out / stale
        if path.exists():
            path.unlink()

    weekly = pd.concat([g["weekly"] for g in groups], ignore_index=True)
    members = pd.DataFrame([row for g in groups for row in g["members"]])
    weekly.to_csv(out / "weekly.csv", index=False, encoding="utf-8-sig", float_format="%.6f")
    members.to_csv(out / "members.csv", index=False, encoding="utf-8-sig")
    page = out / "index.html"
    write_page(groups, page)

    meta = {"asof": day, "note": "持有规模占板块总市值，不是成交额", "groups": []}
    print(f"行情日 {day}")
    for group in groups:
        last = group["weekly"].iloc[-1]
        names = "、".join(f"{row['code']} {row['name']}" for row in group["members"])
        meta["groups"].append(
            {
                "id": group["id"],
                "label": group["label"],
                "market": group["market_name"],
                "index": group["index"],
                "etf_count": len(group["members"]),
                "last_week_share_pct": round(float(last["share_pct"]), 4),
                "last_aum_yi": round(float(last["aum"]) / 1e8, 2),
                "last_cap_yi": round(float(last["market_cap"]) / 1e8, 2),
                "flow": group["flow"]["text"],
            }
        )
        print(
            f"{group['label']}  {len(group['members'])} 只  {names}"
            f"  最新周 {last['share_pct']:.2f}%"
            f"（持有 {last['aum'] / 1e8:.0f} 亿 / {group['market_name']} {last['market_cap'] / 1e8:.0f} 亿）"
        )
        print(f"  {group['flow']['text']}")
        heads = "、".join(f"{row['code']}" for row in group["members"])
        print(f"  当周头部 {heads}")
        if group["id"] == "csi300":
            counter = [point for point in group["anomaly"] if point["kind"] == "counter"]
            last = counter[-1]
            print(
                f"  逆势同步申购 {len(counter)} 周，最近 {last['date']}"
                f" 净申购 {last['total']:+.0f} 亿份，指数 {last['ret']:+.1f}%"
            )
    (out / "meta.json").write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")
    (out / "source.txt").write_text(
        "\n".join(
            [
                "头部宽基 ETF 持有规模占对应板块总市值。不是成交额。",
                "",
                "名单：简称包含「沪深300ETF」「科创50ETF」或「创业板ETF」。每个周按当周持有规模重选。",
                "留下达到本组最大那只 10% 以上的，最多 4 只。增强、价值、成长、红利、行业主题不在简称里，不会进入候选。",
                "持有规模 = 基金份额 × 当日收盘价。份额来自上交所、深交所。",
                "收盘价来自本机通达信。基金日线按三位小数存储，这里除以 10 还原成元，当作净值的近似。",
                "分母是交易所公布的市价总值。沪深300用全A（沪主板A+科创板+深主板A+创业板），科创50用科创板，创业板用创业板。",
                "不含 B 股和北交所。周序列用当周最后一个交易日，不是日占比的平均。",
                "第三张图是当周头部的周净申购：本周末份额减去上周末。新上市的整周份额不计入。",
                "K 线：沪深300 sh000300，科创50 sh000688，创业板指 sz399006。用本机通达信。",
                "",
            ]
        ),
        encoding="utf-8",
    )
    print(page)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

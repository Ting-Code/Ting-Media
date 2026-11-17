# -*- coding: utf-8 -*-
"""沪深300 / 科创50 / 创业板：乐咕 PE/PB + 通达信官方点位，按季度对齐。"""
from __future__ import annotations

from pathlib import Path

import pandas as pd

from cache_io import repo_root
from data_path import ensure_stock_data_on_path

ensure_stock_data_on_path()

from market import fetch_index_daily  # noqa: E402

GROUPS = (
    {
        "id": "csi300",
        "title": "沪深300估值",
        "index": "sh000300",
        "index_name": "沪深300",
        "kind": "index",
        "symbol": "沪深300",
        "pe_label": "乐咕沪深300滚动市盈率",
        "pb_label": "乐咕沪深300滚动市净率",
        "script": (
            "这一页看沪深300的历史估值和点位。\n"
            "红线是乐咕滚动市盈率，蓝线是滚动市净率，绿线是沪深300点位。三条轴各自拉满，不是同一刻度。\n"
            "只比较位置，不给操作建议。数据仅供参考。"
        ),
    },
    {
        "id": "star50",
        "title": "科创50估值",
        "index": "sh000688",
        "index_name": "科创50",
        "kind": "market",
        "symbol": "科创版",
        "pe_label": "乐咕科创板市盈率",
        "pb_label": "乐咕科创板市净率",
        "script": (
            "这一页看科创50点位，和乐咕科创板的市盈率、市净率。\n"
            "PE/PB 是科创板整体，不是按科创50成分再加权。三条轴各自拉满。\n"
            "只比较位置，不给操作建议。数据仅供参考。"
        ),
    },
    {
        "id": "chinext",
        "title": "创业板估值",
        "index": "sz399006",
        "index_name": "创业板指",
        "kind": "index",
        "symbol": "创业板50",
        "pe_label": "乐咕创业板50滚动市盈率",
        "pb_label": "乐咕创业板50滚动市净率",
        "script": (
            "这一页看创业板指点位，和乐咕创业板50的滚动市盈率、市净率。\n"
            "点位是创业板指，PE/PB 是创业板50，口径不一样。三条轴各自拉满。\n"
            "只比较位置，不给操作建议。数据仅供参考。"
        ),
    },
)


def _cache_dir(asof: pd.Timestamp) -> Path:
    path = repo_root() / "cache" / ("etf_board_valuation_%s" % asof.strftime("%Y-%m-%d"))
    path.mkdir(parents=True, exist_ok=True)
    return path


def _on_or_before(frame: pd.DataFrame, day: pd.Timestamp, column: str):
    sub = frame[frame["date"] <= day]
    if sub.empty:
        return None
    value = sub.iloc[-1][column]
    if pd.isna(value):
        return None
    return float(value)


def _quarter_marks(index_daily: pd.DataFrame, asof: pd.Timestamp) -> list[tuple[pd.Timestamp, pd.Timestamp, bool]]:
    first = pd.Timestamp(index_daily["date"].iloc[0]).normalize()
    asof = pd.Timestamp(asof).normalize()
    marks = []
    cursor = pd.Timestamp(first.year, 3, 31)
    while cursor < first:
        cursor = (cursor + pd.offsets.QuarterEnd(1)).normalize()
    current_end = pd.Timestamp(asof).to_period("Q").end_time.normalize()
    while cursor <= current_end:
        if cursor <= asof:
            marks.append((cursor, cursor, False))
        else:
            marks.append((cursor, asof, True))
            break
        cursor = (cursor + pd.offsets.QuarterEnd(1)).normalize()
    return marks


def _fetch_index_pe_pb(symbol: str) -> tuple[pd.DataFrame, pd.DataFrame]:
    import akshare as ak

    pe = ak.stock_index_pe_lg(symbol=symbol)
    pb = ak.stock_index_pb_lg(symbol=symbol)
    pe = pe.rename(columns={"日期": "date", "滚动市盈率": "pe"})
    pb = pb.rename(columns={"日期": "date", "市净率": "pb"})
    pe["date"] = pd.to_datetime(pe["date"]).dt.normalize()
    pb["date"] = pd.to_datetime(pb["date"]).dt.normalize()
    return pe[["date", "pe"]], pb[["date", "pb"]]


def _fetch_market_pe_pb(symbol: str) -> tuple[pd.DataFrame, pd.DataFrame]:
    import akshare as ak

    pe = ak.stock_market_pe_lg(symbol=symbol)
    pb = ak.stock_market_pb_lg(symbol=symbol)
    pe_col = "市盈率" if "市盈率" in pe.columns else "平均市盈率"
    pe = pe.rename(columns={"日期": "date", pe_col: "pe"})
    pb = pb.rename(columns={"日期": "date", "市净率": "pb"})
    pe["date"] = pd.to_datetime(pe["date"]).dt.normalize()
    pb["date"] = pd.to_datetime(pb["date"]).dt.normalize()
    return pe[["date", "pe"]], pb[["date", "pb"]]


def build_board_valuations(asof: str | pd.Timestamp) -> list[dict]:
    """返回三组估值页：口播、图表点（季度 PE/PB/点位）。"""
    asof = pd.Timestamp(asof).normalize()
    cache = _cache_dir(asof)
    pages = []
    for spec in GROUPS:
        index_daily = fetch_index_daily(spec["index"], start_date="2000-01-01")
        index_daily = index_daily.copy()
        index_daily["date"] = pd.to_datetime(index_daily["date"]).dt.normalize()
        index_daily = index_daily[index_daily["date"] <= asof]
        if index_daily.empty:
            raise RuntimeError("通达信没有 %s 日线" % spec["index_name"])
        if spec["kind"] == "index":
            pe_frame, pb_frame = _fetch_index_pe_pb(spec["symbol"])
        else:
            pe_frame, pb_frame = _fetch_market_pe_pb(spec["symbol"])
        pe_frame = pe_frame[pe_frame["date"] <= asof]
        pb_frame = pb_frame[pb_frame["date"] <= asof]
        rows = []
        for quarter_end, anchor, incomplete in _quarter_marks(index_daily, asof):
            rows.append(
                {
                    "date": anchor.strftime("%Y-%m-%d"),
                    "quarter_end": quarter_end.strftime("%Y-%m-%d"),
                    "price": _on_or_before(index_daily, anchor, "close"),
                    "pe": _on_or_before(pe_frame, anchor, "pe"),
                    "pb": _on_or_before(pb_frame, anchor, "pb"),
                    "incomplete": incomplete,
                }
            )
        rows = [row for row in rows if any(row[key] is not None for key in ("pe", "pb", "price"))]
        if not rows:
            raise RuntimeError("没有 %s 估值点" % spec["title"])
        frame = pd.DataFrame(rows)
        frame.to_csv(cache / ("%s_valuation.csv" % spec["id"]), index=False)
        last = next(row for row in reversed(rows) if row["pe"] is not None)
        pages.append(
            {
                "title": spec["title"],
                "tag": spec["index_name"],
                "script": spec["script"],
                "chart": {
                    "kind": "val",
                    "index": spec["index_name"],
                    "rightName": "",
                    "rightKey": "pe",
                    "rightKind": "pe",
                    "peNow": last["pe"],
                    "peLabel": spec["pe_label"],
                    "pbLabel": spec["pb_label"],
                    "points": rows,
                },
            }
        )
    return pages

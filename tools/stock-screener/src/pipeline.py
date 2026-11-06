"""Screener pipeline: universe -> enrich -> filters -> rank."""

from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Any

import filters  # noqa: F401 — register plugins
from indicators import enrich_row
from rank import rank_rows
from registry import get_filter
from data_path import ensure_stock_data_on_path
from universe import build_universe

ensure_stock_data_on_path()
from tdx_day import read_day_tail  # noqa: E402


def _apply_filters(row: dict[str, Any], filter_specs: list[dict[str, Any]]) -> bool:
    for spec in filter_specs:
        if spec.get("enabled", True) is False:
            continue
        fid = spec["id"]
        params = spec.get("params") or {}
        fn = get_filter(fid)
        if not fn(row, params):
            return False
    return True


def _process_one(item: dict[str, Any], max_bars: int, filter_specs: list[dict[str, Any]]) -> dict[str, Any] | None:
    df = read_day_tail(Path(item["path"]), max_bars=max_bars)
    if df.empty:
        return None
    feats = enrich_row(df)
    if not feats:
        return None
    row = {**item, **feats, "_bars": df}
    if not _apply_filters(row, filter_specs):
        return None
    row.pop("_bars", None)
    return row


def run_pipeline(cfg: dict[str, Any], workers: int = 8) -> tuple[Any, dict[str, Any]]:
    tdx_cfg = cfg.get("tdx") or {}
    vipdoc = tdx_cfg.get("vipdoc") or "D:/app/tdx/vipdoc"
    max_bars = int(tdx_cfg.get("max_bars", 120))
    uni_cfg = cfg.get("universe") or {}
    filter_specs = cfg.get("filters") or []
    rank_cfg = cfg.get("rank") or {}
    out_cfg = cfg.get("output") or {}

    universe = build_universe(vipdoc, uni_cfg)
    # preload spot once if market_cap filter used (avoid thundering herd)
    if any((f or {}).get("id") == "market_cap" for f in filter_specs):
        from spot import load_market_cap_map

        load_market_cap_map()
    hits: list[dict[str, Any]] = []
    errors = 0

    with ThreadPoolExecutor(max_workers=max(1, workers)) as ex:
        futs = [
            ex.submit(_process_one, item, max_bars, filter_specs) for item in universe
        ]
        for fut in as_completed(futs):
            try:
                row = fut.result()
            except Exception:
                errors += 1
                continue
            if row is not None:
                hits.append(row)

    by = rank_cfg.get("by") or ["amount_yi"]
    ascending = rank_cfg.get("ascending") or [False]
    df = rank_rows(hits, by=by, ascending=ascending)
    top = out_cfg.get("top")
    if top is not None and not df.empty:
        df = df.head(int(top)).copy()

    # trim columns for csv
    drop_cols = [c for c in ["path", "_bars"] if c in df.columns]
    if drop_cols:
        df = df.drop(columns=drop_cols)

    meta = {
        "config_name": cfg.get("name"),
        "vipdoc": str(vipdoc),
        "universe_size": len(universe),
        "hit_size_before_top": len(hits),
        "hit_size": int(len(df)),
        "errors": errors,
        "filters": filter_specs,
        "rank": rank_cfg,
        "note": "tech screener; fundamentals via analysis.py when needed",
    }
    if not df.empty and "date" in df.columns:
        meta["asof"] = str(df["date"].mode().iloc[0]) if len(df) else None
    return df, meta

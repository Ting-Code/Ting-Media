"""Build stock universe from Tongdaxin day files + optional ST names."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from data_path import ensure_stock_data_on_path

ensure_stock_data_on_path()
from tdx_day import classify_board, is_st_name, list_day_files, load_name_map  # noqa: E402


def build_universe(vipdoc: str | Path, uni_cfg: dict[str, Any]) -> list[dict[str, Any]]:
    boards = set(uni_cfg.get("boards") or ["main", "chinext", "star", "bse"])
    exclude_index = bool(uni_cfg.get("exclude_index", True))
    exclude_st = bool(uni_cfg.get("exclude_st", True))

    names = load_name_map() if exclude_st else {}
    items: list[dict[str, Any]] = []
    for market, code6, path in list_day_files(vipdoc):
        board = classify_board(market, code6)
        if board is None:
            if exclude_index:
                continue
            board = "other"
        if board not in boards:
            continue
        name = names.get(code6, "")
        if exclude_st and name and is_st_name(name):
            continue
        items.append(
            {
                "market": market,
                "code": code6,
                "symbol": f"{market}{code6}",
                "name": name,
                "board": board,
                "path": str(path),
            }
        )
    return items

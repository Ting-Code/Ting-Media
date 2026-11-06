"""Write screener outputs under repo cache/."""

from __future__ import annotations

import json
from datetime import date
from pathlib import Path
from typing import Any

import pandas as pd


def repo_root() -> Path:
    # tools/stock-screener/src/cache_io.py -> repo root
    return Path(__file__).resolve().parents[3]


def write_run(
    config_name: str,
    hits: pd.DataFrame,
    meta: dict[str, Any],
    asof: str | None = None,
) -> Path:
    day = asof or date.today().isoformat()
    out = repo_root() / "cache" / f"screener_{config_name}_{day}"
    out.mkdir(parents=True, exist_ok=True)
    hits_path = out / "hits.csv"
    meta_path = out / "meta.json"
    hits.to_csv(hits_path, index=False, encoding="utf-8-sig")
    meta_path.write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")
    return out

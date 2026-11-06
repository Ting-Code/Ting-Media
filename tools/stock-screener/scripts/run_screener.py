#!/usr/bin/env python3
"""CLI: run technical A-share screener from YAML config."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
sys.path.insert(0, str(SRC))

from cache_io import write_run  # noqa: E402
from pipeline import run_pipeline  # noqa: E402
from registry import known_filters  # noqa: E402


def main() -> int:
    ap = argparse.ArgumentParser(description="A-share technical screener (Tongdaxin day bars)")
    ap.add_argument("--config", required=True, help="path to YAML config")
    ap.add_argument("--vipdoc", default=None, help="override tdx.vipdoc")
    ap.add_argument("--workers", type=int, default=8)
    ap.add_argument("--list-filters", action="store_true")
    args = ap.parse_args()

    # ensure filters registered before list
    import filters  # noqa: F401

    if args.list_filters:
        print("\n".join(known_filters()))
        return 0

    cfg_path = Path(args.config)
    if not cfg_path.is_file():
        cfg_path = ROOT / args.config
    cfg = yaml.safe_load(cfg_path.read_text(encoding="utf-8"))
    if args.vipdoc:
        cfg.setdefault("tdx", {})["vipdoc"] = args.vipdoc

    print(f"config={cfg.get('name')} filters={[f.get('id') for f in cfg.get('filters') or []]}")
    df, meta = run_pipeline(cfg, workers=args.workers)
    asof = meta.get("asof")
    out = write_run(cfg.get("name") or "run", df, {**meta, "config_file": str(cfg_path)}, asof=asof)
    print(f"universe={meta['universe_size']} hits={meta['hit_size']} errors={meta['errors']}")
    print(f"wrote {out}")
    if not df.empty:
        cols = [c for c in ["code", "name", "board", "close", "pct_chg_5d", "amount_yi", "date"] if c in df.columns]
        print(df[cols].head(15).to_string(index=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

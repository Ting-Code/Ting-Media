"""Put stock-data + stock-screener src on sys.path."""
from __future__ import annotations

import sys
from pathlib import Path


def ensure_tool_srcs_on_path() -> None:
    tools_dir = Path(__file__).resolve().parents[2]  # .../tools
    for name in ("stock-data", "stock-screener"):
        s = str(tools_dir / name / "src")
        if s not in sys.path:
            sys.path.insert(0, s)


# backward-compat alias
def ensure_stock_data_on_path() -> Path:
    ensure_tool_srcs_on_path()
    return Path(__file__).resolve().parents[2] / "stock-data" / "src"

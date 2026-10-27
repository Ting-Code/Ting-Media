"""Put tools/stock-data/src on sys.path."""
from __future__ import annotations
import sys
from pathlib import Path

def ensure_stock_data_on_path() -> Path:
    tools_dir = Path(__file__).resolve().parents[2]  # .../tools
    data_src = tools_dir / "stock-data" / "src"
    s = str(data_src)
    if s not in sys.path:
        sys.path.insert(0, s)
    return data_src

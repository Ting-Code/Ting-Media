"""Rank filtered rows."""

from __future__ import annotations

from typing import Any

import pandas as pd


def rank_rows(rows: list[dict[str, Any]], by: list[str], ascending: list[bool]) -> pd.DataFrame:
    if not rows:
        return pd.DataFrame()
    df = pd.DataFrame(rows)
    cols = [c for c in by if c in df.columns]
    if not cols:
        return df
    asc = ascending[: len(cols)]
    while len(asc) < len(cols):
        asc.append(False)
    return df.sort_values(by=cols, ascending=asc, na_position="last").reset_index(drop=True)

"""复权：通达信 lday(不复权) + gbbq 权息本地计算。"""

from __future__ import annotations

import pandas as pd


def _event_factors(bfq: pd.DataFrame, xdxr: pd.DataFrame) -> list[tuple[pd.Timestamp, float]]:
    """Each ex-date factor = 除权参考价 / 昨收 (10股口径)."""
    if xdxr is None or xdxr.empty:
        return []
    priced = bfq.set_index("date").sort_index() if "date" in bfq.columns else bfq.sort_index()
    factors: list[tuple[pd.Timestamp, float]] = []
    for _, row in xdxr.iterrows():
        dt = pd.Timestamp(row["date"]).normalize()
        prev = priced[priced.index < dt]
        if prev.empty:
            continue
        pc = float(prev["close"].iloc[-1])
        if pc <= 0:
            continue
        fh = float(row.get("fenhong") or 0.0)
        pg = float(row.get("peigu") or 0.0)
        pj = float(row.get("peigujia") or 0.0)
        sg = float(row.get("songzhuangu") or 0.0)
        ref = (pc * 10.0 - fh + pg * pj) / (10.0 + pg + sg)
        factors.append((dt, ref / pc))
    return factors


def apply_adjust(bfq: pd.DataFrame, xdxr: pd.DataFrame, how: str = "qfq") -> pd.DataFrame:
    """
    how: qfq 前复权 | hfq 后复权 | none/bfq 不复权
    输入需含 date, open, high, low, close；volume/amount 原样保留。
    """
    how = (how or "none").lower()
    out = bfq.copy()
    if how in ("none", "bfq", "1", ""):
        return out.reset_index(drop=True)

    factors = _event_factors(out, xdxr)
    if not factors:
        return out.reset_index(drop=True)

    dates = pd.to_datetime(out["date"]).reset_index(drop=True)
    mult = pd.Series(1.0, index=out.index)

    if how in ("qfq", "2", "forward"):
        # 严格早于除权日的 K 线乘上该次因子（累乘）
        for dt, f in factors:
            mult.loc[dates < dt] *= f
    elif how in ("hfq", "3", "backward"):
        # 除权日及之后乘上 1/factor 的累乘（等价后复权）
        for dt, f in factors:
            if f == 0:
                continue
            mult.loc[dates >= dt] *= 1.0 / f
    else:
        raise ValueError(f"未知复权方式: {how}")

    for col in ("open", "high", "low", "close"):
        if col in out.columns:
            out[col] = out[col] * mult.values
    return out.reset_index(drop=True)

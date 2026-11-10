"""Tongdaxin vipdoc daily bars (.day, 32 bytes/record, 不复权)."""

from __future__ import annotations

import struct
from pathlib import Path

import pandas as pd

from codes import to_exchange
from paths import tdx_root, tdx_vipdoc

RECORD = struct.Struct("<IIIIIfII")
REC_SIZE = 32
MARKET_DIRS = ("sh", "sz", "bj")


def _market_code(code: str) -> tuple[str, str]:
    digits = "".join(ch for ch in code if ch.isdigit())[-6:]
    bs = to_exchange(digits)
    return bs.split(".")[0], digits


def day_file_path(code: str, vipdoc: Path | None = None) -> Path:
    root = vipdoc or tdx_vipdoc()
    if root is None:
        raise FileNotFoundError("未找到通达信 vipdoc，请设置 TDX_DIR / TDX_VIPDOC")
    market, digits = _market_code(code)
    path = root / market / "lday" / f"{market}{digits}.day"
    if not path.is_file():
        raise FileNotFoundError(f"无日线文件: {path}")
    return path


def _rows_from_raw(raw: bytes) -> pd.DataFrame:
    if len(raw) < REC_SIZE or len(raw) % REC_SIZE:
        return pd.DataFrame(columns=["date", "open", "high", "low", "close", "volume", "amount"])
    rows = []
    for date_i, o, h, l, c, amount, volume, _ in RECORD.iter_unpack(raw):
        rows.append(
            (
                date_i,
                o / 100.0,
                h / 100.0,
                l / 100.0,
                c / 100.0,
                float(volume),
                float(amount),
            )
        )
    df = pd.DataFrame(rows, columns=["date_i", "open", "high", "low", "close", "volume", "amount"])
    df["date"] = pd.to_datetime(df["date_i"].astype(str), format="%Y%m%d", errors="coerce")
    return df.dropna(subset=["date", "close"]).drop(columns=["date_i"]).reset_index(drop=True)


def read_day_file(path: Path) -> pd.DataFrame:
    return _rows_from_raw(Path(path).read_bytes()).sort_values("date").reset_index(drop=True)


def read_day_tail(path: Path, max_bars: int = 120) -> pd.DataFrame:
    """Last max_bars bars — for screener hot path."""
    p = Path(path)
    size = p.stat().st_size
    if size < REC_SIZE or size % REC_SIZE:
        return pd.DataFrame()
    n = size // REC_SIZE
    take = min(n, max_bars)
    with p.open("rb") as f:
        f.seek((n - take) * REC_SIZE)
        raw = f.read(take * REC_SIZE)
    return _rows_from_raw(raw)


def fetch_tdx_daily(
    code: str,
    start_date: str | None = None,
    end_date: str | None = None,
    vipdoc: Path | None = None,
) -> pd.DataFrame:
    df = read_day_file(day_file_path(code, vipdoc=vipdoc))
    if start_date:
        df = df[df["date"] >= pd.Timestamp(start_date)]
    if end_date:
        df = df[df["date"] <= pd.Timestamp(end_date)]
    return df.reset_index(drop=True)


def classify_board(market: str, code6: str) -> str | None:
    """Board id or None if index / non-stock."""
    if market == "sh":
        if code6.startswith(("000", "880", "90")):
            return None
        if code6.startswith(("688", "689")):
            return "star"
        if code6.startswith(("60", "68")):
            return "main"
        return None
    if market == "sz":
        if code6.startswith("399"):
            return None
        if code6.startswith(("300", "301")):
            return "chinext"
        if code6.startswith(("000", "001", "002", "003")):
            return "main"
        return None
    if market == "bj":
        if code6.startswith(("8", "4", "92")):
            return "bse"
        return None
    return None


def list_a_share_codes(vipdoc: str | Path | None = None) -> list[str]:
    """A 股代码（沪深京日线里能归到板块的），不含指数。"""
    return [code for market, code, _ in list_day_files(vipdoc) if classify_board(market, code)]


def list_day_files(vipdoc: str | Path | None = None) -> list[tuple[str, str, Path]]:
    root = Path(vipdoc) if vipdoc else tdx_vipdoc()
    if root is None:
        raise FileNotFoundError("未找到通达信 vipdoc")
    out: list[tuple[str, str, Path]] = []
    for m in MARKET_DIRS:
        d = root / m / "lday"
        if not d.is_dir():
            continue
        for p in d.glob(f"{m}*.day"):
            stem = p.stem
            if len(stem) < 8:
                continue
            code6 = stem[2:8]
            if code6.isdigit():
                out.append((m, code6, p))
    return out


def load_name_map() -> dict[str, str]:
    try:
        import akshare as ak

        raw = ak.stock_info_a_code_name()
    except Exception:
        return {}
    if raw is None or raw.empty:
        return {}
    cols = {str(c).lower(): c for c in raw.columns}
    code_col = cols.get("code") or cols.get("证券代码") or raw.columns[0]
    name_col = cols.get("name") or cols.get("证券简称") or raw.columns[1]
    out: dict[str, str] = {}
    for _, row in raw.iterrows():
        code = "".join(ch for ch in str(row[code_col]) if ch.isdigit()).zfill(6)[-6:]
        out[code] = str(row[name_col]).strip()
    return out


def is_st_name(name: str) -> bool:
    n = name.upper().replace(" ", "")
    return "ST" in n or n.startswith("*") or "退" in name


def load_security_names() -> dict[str, str]:
    """通达信本地证券简称。读 hq_cache 的 shs/szs/bjs.tnf，不走网络。"""
    root = tdx_root()
    if root is None:
        return {}
    out: dict[str, str] = {}
    rec = 360
    for filename in ("shs.tnf", "szs.tnf", "bjs.tnf"):
        path = root / "T0002" / "hq_cache" / filename
        if not path.is_file():
            continue
        raw = path.read_bytes()
        body = raw[50:] if len(raw) > 50 else raw
        n = len(body) // rec
        for i in range(n):
            chunk = body[i * rec : (i + 1) * rec]
            code = chunk[:6].decode("ascii", "ignore")
            if not code.isdigit():
                continue
            name = chunk[31:].split(b"\x00", 1)[0].decode("gbk", "ignore")
            name = "".join(name.split())
            if name:
                out[code] = name
    return out


def read_day_dates_amount(path: Path):
    """只取日期和成交额。日期是 YYYYMMDD int64，成交额是元（float64）。"""
    import numpy as np

    raw = Path(path).read_bytes()
    empty_d = np.empty(0, dtype=np.int64)
    empty_a = np.empty(0, dtype=np.float64)
    if len(raw) < REC_SIZE or len(raw) % REC_SIZE:
        return empty_d, empty_a
    n = len(raw) // REC_SIZE
    dtype = np.dtype(
        [
            ("date", "<u4"),
            ("open", "<u4"),
            ("high", "<u4"),
            ("low", "<u4"),
            ("close", "<u4"),
            ("amount", "<f4"),
            ("volume", "<u4"),
            ("pad", "<u4"),
        ]
    )
    arr = np.frombuffer(raw, dtype=dtype, count=n)
    return arr["date"].astype(np.int64), arr["amount"].astype(np.float64)

"""Tongdaxin vipdoc daily bars (.day, 32 bytes/record, 不复权)."""

from __future__ import annotations

import struct
from pathlib import Path

import pandas as pd

from codes import hk_code5, is_hk, to_exchange
from paths import tdx_root, tdx_vipdoc

RECORD = struct.Struct("<IIIIIfII")
REC_SIZE = 32
MARKET_DIRS = ("sh", "sz", "bj")
HK_DAY_RECORD = struct.Struct("<IfffffII")
HK_MARKET_DIR = "ds"
HK_FILE_PREFIX = "31#"


def _market_code(code: str) -> tuple[str, str]:
    digits = "".join(ch for ch in code if ch.isdigit())[-6:]
    bs = to_exchange(digits)
    return bs.split(".")[0], digits


def day_file_path(code: str, vipdoc: Path | None = None) -> Path:
    if is_hk(code):
        return hk_day_file_path(code, vipdoc=vipdoc)
    root = vipdoc or tdx_vipdoc()
    if root is None:
        raise FileNotFoundError("未找到通达信 vipdoc，请设置 TDX_DIR / TDX_VIPDOC")
    market, digits = _market_code(code)
    path = root / market / "lday" / f"{market}{digits}.day"
    if not path.is_file():
        raise FileNotFoundError(f"无日线文件: {path}")
    return path




def hk_day_file_path(code: str, vipdoc: Path | None = None) -> Path:
    root = vipdoc or tdx_vipdoc()
    if root is None:
        raise FileNotFoundError("未找到通达信 vipdoc，请设置 TDX_DIR / TDX_VIPDOC")
    code5 = hk_code5(code)
    path = root / HK_MARKET_DIR / "lday" / f"{HK_FILE_PREFIX}{code5}.day"
    if not path.is_file():
        raise FileNotFoundError(f"无港股日线文件: {path}")
    return path


def _rows_from_raw_hk(raw: bytes) -> pd.DataFrame:
    if len(raw) < REC_SIZE or len(raw) % REC_SIZE:
        return pd.DataFrame(columns=["date", "open", "high", "low", "close", "volume", "amount"])
    rows = []
    for date_i, o, h, l, c, amount, volume, _ in HK_DAY_RECORD.iter_unpack(raw):
        rows.append((date_i, float(o), float(h), float(l), float(c), float(volume), float(amount)))
    df = pd.DataFrame(rows, columns=["date_i", "open", "high", "low", "close", "volume", "amount"])
    df["date"] = pd.to_datetime(df["date_i"].astype(str), format="%Y%m%d", errors="coerce")
    return df.dropna(subset=["date", "close"]).drop(columns=["date_i"]).reset_index(drop=True)


def read_hk_day_file(path: Path) -> pd.DataFrame:
    return _rows_from_raw_hk(Path(path).read_bytes()).sort_values("date").reset_index(drop=True)


def load_hk_security_names() -> dict[str, str]:
    """港股代码 -> 简称。优先扫 ds_stk.dat，再用 tdxhkag.cfg 覆盖。"""
    root = tdx_root()
    if root is None:
        return {}
    cache = root / "T0002" / "hq_cache"
    out: dict[str, str] = {}

    stk = cache / "ds_stk.dat"
    if stk.is_file():
        raw = stk.read_bytes()
        i = 0
        n = len(raw)
        while i < n - 25:
            token = raw[i : i + 5]
            if token.isdigit() and raw[i + 5 : i + 8] == b"\x00\x00\x00":
                code = token.decode("ascii")
                name_raw = raw[i + 20 : i + 40].split(b"\x00", 1)[0]
                try:
                    name = name_raw.decode("gbk").strip()
                except UnicodeDecodeError:
                    name = ""
                if name and all(ch.isprintable() for ch in name):
                    out[f"{code}.HK"] = name
                i += 20
            else:
                i += 1

    cfg = cache / "tdxhkag.cfg"
    if cfg.is_file():
        for line in cfg.read_text(encoding="gbk", errors="ignore").splitlines():
            parts = line.split("|")
            if len(parts) < 2:
                continue
            digits = "".join(ch for ch in parts[0] if ch.isdigit())
            name = parts[1].strip()
            if len(digits) <= 5 and name:
                out[f"{digits.zfill(5)}.HK"] = name
    return out


def drop_incomplete_hk_session(
    daily: pd.DataFrame,
    *,
    now: pd.Timestamp | None = None,
    close_hour: int = 16,
    close_minute: int = 10,
) -> pd.DataFrame:
    """港股当日未收盘前，去掉最后一根可能未完成的日线。"""
    if daily is None or daily.empty:
        return daily
    df = daily.sort_values("date").reset_index(drop=True)
    last = pd.Timestamp(df["date"].iloc[-1]).normalize()
    try:
        from zoneinfo import ZoneInfo
        tz = ZoneInfo("Asia/Hong_Kong")
    except Exception:
        tz = None
    if now is None:
        now = pd.Timestamp.now(tz=tz) if tz else pd.Timestamp.now()
    else:
        now = pd.Timestamp(now)
        if tz is not None and now.tzinfo is None:
            now = now.tz_localize(tz)
    local = now.tz_convert(tz) if tz is not None and now.tzinfo is not None else now
    today = pd.Timestamp(local.date())
    cutoff = local.replace(hour=close_hour, minute=close_minute, second=0, microsecond=0) if tz else local
    if last == today and local < cutoff:
        return df.iloc[:-1].reset_index(drop=True)
    return df

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
    path = day_file_path(code, vipdoc=vipdoc)
    df = read_hk_day_file(path) if is_hk(code) else read_day_file(path)
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

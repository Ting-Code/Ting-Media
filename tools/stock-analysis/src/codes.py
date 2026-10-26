"""Stock code helpers and name map for first-version single-stock flow."""

from __future__ import annotations

# Common aliases for demos / AI prompts. Prefer 6-digit code when unsure.
NAME_TO_CODE = {
    "宁德时代": "300750",
    "catl": "300750",
    "贵州茅台": "600519",
    "茅台": "600519",
    "五粮液": "000858",
    "招商银行": "600036",
    "平安银行": "000001",
    "中国平安": "601318",
    "比亚迪": "002594",
    "隆基绿能": "601012",
    "中芯国际": "688981",
    "药明康德": "603259",
}


def to_baostock(code: str) -> str:
    digits = "".join(ch for ch in code if ch.isdigit())
    if len(digits) != 6:
        raise ValueError(f"无效股票代码: {code}")
    if digits.startswith(("5", "6", "9")):
        return f"sh.{digits}"
    if digits.startswith(("4", "8")):
        return f"bj.{digits}"
    return f"sz.{digits}"


def _lookup_akshare_name(name: str) -> tuple[str, str] | None:
    """Best-effort name -> code via AkShare. Returns None on failure."""
    try:
        import akshare as ak
    except Exception:
        return None
    try:
        df = ak.stock_info_a_code_name()
    except Exception:
        return None
    if df is None or df.empty:
        return None
    cols = {str(c).lower(): c for c in df.columns}
    code_col = cols.get("code") or cols.get("证券代码")
    name_col = cols.get("name") or cols.get("证券简称")
    if code_col is None or name_col is None:
        # fallback positional
        code_col, name_col = df.columns[0], df.columns[1]
    hit = df[df[name_col].astype(str).str.strip() == name]
    if hit.empty:
        hit = df[df[name_col].astype(str).str.contains(name, regex=False)]
    if hit.empty:
        return None
    code = "".join(ch for ch in str(hit.iloc[0][code_col]) if ch.isdigit()).zfill(6)[-6:]
    disp = str(hit.iloc[0][name_col]).strip()
    return code, disp


def resolve_code(query: str) -> tuple[str, str]:
    """Return (6-digit code, display name)."""
    q = query.strip()
    if not q:
        raise ValueError("股票名称或代码不能为空")

    key = q.lower()
    if key in NAME_TO_CODE:
        return NAME_TO_CODE[key], q
    if q in NAME_TO_CODE:
        return NAME_TO_CODE[q], q

    digits = "".join(ch for ch in q if ch.isdigit())
    if len(digits) == 6 and digits.isdigit():
        return digits, q

    found = _lookup_akshare_name(q)
    if found:
        return found

    raise ValueError(
        f"无法识别股票: {query}。"
        "请改用 6 位代码（如 300750），或在 src/codes.py 的 NAME_TO_CODE 中补充名称映射。"
    )

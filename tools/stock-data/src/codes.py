"""Stock code helpers and name map for first-version single-stock flow."""

from __future__ import annotations

# Common aliases for demos / AI prompts. Prefer 6-digit code when unsure.
# 港股用 00700.HK，不要把 5 位代码左侧补成 6 位 A 股。
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
    "腾讯控股": "00700.HK",
    "腾讯": "00700.HK",
}


def is_hk(code: str) -> bool:
    """是否为已规范化的港股代码（00700.HK）或带 .HK 后缀的输入。"""
    s = str(code).strip().upper()
    return s.endswith(".HK")


def hk_code5(code: str) -> str:
    s = str(code).strip().upper()
    if s.endswith(".HK"):
        s = s[:-3]
    digits = "".join(ch for ch in s if ch.isdigit())
    if not digits or len(digits) > 5:
        raise ValueError(f"无效港股代码: {code}")
    return digits.zfill(5)


def hk_symbol(code: str) -> str:
    return f"{hk_code5(code)}.HK"


def to_exchange(code: str) -> str:
    if is_hk(code):
        return f"hk.{hk_code5(code)}"
    digits = "".join(ch for ch in code if ch.isdigit())
    if len(digits) != 6:
        raise ValueError(f"无效代码: {code}")
    if digits.startswith("92"):
        return f"bj.{digits}"
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


def _lookup_local_name(name: str) -> tuple[str, str] | None:
    """通达信本地简称。只在唯一命中时返回。"""
    try:
        names = load_security_names()
    except Exception:
        return None
    exact = [(code, label) for code, label in names.items() if label == name]
    if len(exact) == 1:
        return exact[0]
    return None


def _lookup_hk_local_name(name: str) -> tuple[str, str] | None:
    try:
        from tdx_day import load_hk_security_names
        names = load_hk_security_names()
    except Exception:
        return None
    exact = [(code, label) for code, label in names.items() if label == name]
    if len(exact) == 1:
        return exact[0]
    return None


def load_security_names() -> dict[str, str]:
    """通达信本地证券简称，code -> name。"""
    from tdx_day import load_security_names as _load

    return _load()


def _looks_like_bare_hk_code(query: str, digits: str) -> bool:
    compact = query.strip().upper().replace(" ", "")
    return compact == digits and len(digits) == 5


def resolve_code(query: str) -> tuple[str, str]:
    """Return (code, display name). A 股为 6 位数字，港股为 00700.HK。"""
    q = query.strip()
    if not q:
        raise ValueError("名称或代码不能为空")

    key = q.lower()
    if key in NAME_TO_CODE:
        code = NAME_TO_CODE[key]
        return code, q
    if q in NAME_TO_CODE:
        code = NAME_TO_CODE[q]
        return code, q

    if q.upper().endswith(".HK"):
        symbol = hk_symbol(q)
        return symbol, _hk_display_name(symbol, q)

    digits = "".join(ch for ch in q if ch.isdigit())
    if len(digits) == 6 and digits.isdigit() and not q.upper().endswith(".HK"):
        return digits, q
    if _looks_like_bare_hk_code(q, digits):
        symbol = hk_symbol(digits)
        return symbol, _hk_display_name(symbol, q)

    found = _lookup_local_name(q)
    if found:
        return found

    found = _lookup_hk_local_name(q)
    if found:
        return found

    found = _lookup_akshare_name(q)
    if found:
        return found

    raise ValueError(
        f"无法识别: {query}。"
        "请改用 6 位 A 股代码（如 300750），或港股 00700 / 00700.HK，"
        "或在 src/codes.py 的 NAME_TO_CODE 中补充名称映射。"
    )


def _hk_display_name(symbol: str, fallback: str) -> str:
    try:
        from tdx_day import load_hk_security_names
        name = load_hk_security_names().get(symbol)
        if name:
            return name
    except Exception:
        pass
    return fallback

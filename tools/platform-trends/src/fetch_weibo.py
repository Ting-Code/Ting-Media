"""Weibo hot-search topics."""
from __future__ import annotations

from urllib.parse import quote

from httputil import get_json
from normalize import HotItem

HOT_SEARCH = "https://weibo.com/ajax/side/hotSearch"
HOT_BAND = "https://weibo.com/ajax/statuses/hot_band"
HEADERS = {"Referer": "https://weibo.com"}


def fetch_weibo() -> list[HotItem]:
    try:
        return _from_hot_search()
    except Exception:
        return _from_hot_band()


def _from_hot_search() -> list[HotItem]:
    payload = get_json(HOT_SEARCH, headers=HEADERS)
    if not payload.get("ok"):
        raise RuntimeError(f"weibo hotSearch ok={payload.get('ok')}")
    rows = (payload.get("data") or {}).get("realtime") or []
    if not rows:
        raise RuntimeError("weibo hotSearch empty")
    return [_topic(row, i) for i, row in enumerate(rows, start=1) if _title(row)]


def _from_hot_band() -> list[HotItem]:
    payload = get_json(HOT_BAND, headers=HEADERS)
    if not payload.get("ok"):
        raise RuntimeError(f"weibo hot_band ok={payload.get('ok')}")
    rows = (payload.get("data") or {}).get("band_list") or []
    if not rows:
        raise RuntimeError("weibo hot_band empty")
    return [_topic(row, i) for i, row in enumerate(rows, start=1) if _title(row)]


def _title(row: dict) -> str:
    return str(row.get("word") or row.get("note") or "").strip()


def _topic(row: dict, fallback_rank: int) -> HotItem:
    title = _title(row)
    heat = _float(row.get("num") if row.get("num") is not None else row.get("raw_hot"))
    niche = str(row.get("category") or "").strip() or "未标注"
    rank = row.get("realpos")
    try:
        rank = int(rank) if rank is not None else fallback_rank
    except (TypeError, ValueError):
        rank = fallback_rank
    return HotItem(
        kind="topic",
        platform="weibo",
        title=title,
        rank=rank,
        heat=heat,
        niche=niche,
        url=f"https://s.weibo.com/weibo?q={quote(title)}",
        extra={"label": row.get("label_name") or row.get("icon_desc") or ""},
    )


def _float(value) -> float | None:
    if value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None

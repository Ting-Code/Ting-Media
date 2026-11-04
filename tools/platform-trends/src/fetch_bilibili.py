"""Bilibili popular + ranking boards (works + partition niche)."""
from __future__ import annotations

from httputil import get_json
from normalize import HotItem

POPULAR = "https://api.bilibili.com/x/web-interface/popular"
RANKING = "https://api.bilibili.com/x/web-interface/ranking/v2"
HEADERS = {"Referer": "https://www.bilibili.com"}


def fetch_bilibili(*, popular_ps: int = 50, ranking_limit: int = 50) -> list[HotItem]:
    popular = _popular(popular_ps)
    ranking = _ranking(ranking_limit)
    by_key: dict[str, HotItem] = {}
    ordered: list[HotItem] = []
    for item in ranking + popular:
        key = str((item.extra or {}).get("bvid") or item.title)
        if key in by_key:
            continue
        by_key[key] = item
        ordered.append(item)
    for i, item in enumerate(ordered, start=1):
        item.rank = i
    return ordered


def _popular(ps: int) -> list[HotItem]:
    payload = get_json(POPULAR, headers=HEADERS, params={"ps": ps, "pn": 1})
    if payload.get("code") != 0:
        raise RuntimeError(
            f"bilibili popular code={payload.get('code')} {payload.get('message')}"
        )
    return [_work(row, source="popular") for row in payload.get("data", {}).get("list", [])]


def _ranking(limit: int) -> list[HotItem]:
    payload = get_json(RANKING, headers=HEADERS, params={"rid": 0, "type": "all"})
    if payload.get("code") != 0:
        raise RuntimeError(
            f"bilibili ranking code={payload.get('code')} {payload.get('message')}"
        )
    rows = payload.get("data", {}).get("list", [])[:limit]
    return [_work(row, source="ranking") for row in rows]


def _work(row: dict, *, source: str) -> HotItem:
    stat = row.get("stat") or {}
    owner = row.get("owner") or {}
    bvid = row.get("bvid") or ""
    aid = row.get("aid")
    url = f"https://www.bilibili.com/video/{bvid}" if bvid else ""
    heat = _float(stat.get("view"))
    return HotItem(
        kind="work",
        platform="bilibili",
        title=str(row.get("title") or "").strip() or "未命名",
        heat=heat,
        niche=str(row.get("tname") or "").strip() or "未标注",
        url=url,
        author=str(owner.get("name") or "").strip(),
        extra={
            "source": source,
            "bvid": bvid,
            "aid": aid,
            "like": stat.get("like"),
            "coin": stat.get("coin"),
            "share": stat.get("share"),
            "reply": stat.get("reply"),
        },
    )


def _float(value) -> float | None:
    if value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None

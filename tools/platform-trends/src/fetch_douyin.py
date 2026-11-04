"""Douyin hot-word billboard."""
from __future__ import annotations

from urllib.parse import quote

from httputil import get_json
from normalize import HotItem

URL = "https://www.iesdouyin.com/web/api/v2/hotsearch/billboard/word/"
HEADERS = {"Referer": "https://www.douyin.com/"}


def fetch_douyin() -> list[HotItem]:
    payload = get_json(URL, headers=HEADERS)
    code = payload.get("status_code")
    rows = payload.get("word_list") or []
    if code not in (0, None) and not rows:
        raise RuntimeError(f"douyin status_code={code}")
    if not rows:
        raise RuntimeError("douyin word_list empty")
    items: list[HotItem] = []
    for i, row in enumerate(rows, start=1):
        title = str(row.get("word") or "").strip()
        if not title:
            continue
        heat = row.get("hot_value")
        try:
            heat = float(heat) if heat is not None else None
        except (TypeError, ValueError):
            heat = None
        items.append(
            HotItem(
                kind="topic",
                platform="douyin",
                title=title,
                rank=i,
                heat=heat,
                niche="未标注",
                url=f"https://www.douyin.com/search/{quote(title)}",
                extra={"label": row.get("label")},
            )
        )
    return items

"""Aggregate niches and cross-platform topic overlaps."""
from __future__ import annotations

import re
from collections import defaultdict
from dataclasses import dataclass, field
from typing import Any

from normalize import HotItem

_PUNCT = re.compile(r"[\s#＃@【】\[\]()（）·\-_|｜/\.,，。!！?？:：;；\"'“”‘’]+")


@dataclass
class FetchResult:
    platform: str
    items: list[HotItem] = field(default_factory=list)
    error: str | None = None


@dataclass
class TrendReport:
    results: list[FetchResult]
    bilibili_niches: list[dict[str, Any]]
    weibo_niches: list[dict[str, Any]]
    overlaps: list[dict[str, Any]]
    summary: dict[str, Any]


def analyze(results: list[FetchResult]) -> TrendReport:
    by_plat = {r.platform: r for r in results}
    bili = by_plat.get("bilibili")
    weibo = by_plat.get("weibo")
    douyin = by_plat.get("douyin")

    bili_niches = _bilibili_niches(bili.items if bili and not bili.error else [])
    weibo_niches = _count_niches(weibo.items if weibo and not weibo.error else [])
    overlaps = _overlaps(
        [r for r in results if not r.error and r.items]
    )
    summary = {
        "platforms": {
            r.platform: {
                "ok": r.error is None,
                "count": len(r.items),
                "error": r.error,
            }
            for r in results
        },
        "ok_count": sum(1 for r in results if r.error is None),
        "fail_count": sum(1 for r in results if r.error is not None),
        "total_items": sum(len(r.items) for r in results),
        "top_bili_niche": bili_niches[0]["niche"] if bili_niches else None,
        "overlap_count": len(overlaps),
    }
    return TrendReport(
        results=results,
        bilibili_niches=bili_niches,
        weibo_niches=weibo_niches,
        overlaps=overlaps,
        summary=summary,
    )


def _bilibili_niches(items: list[HotItem]) -> list[dict[str, Any]]:
    buckets: dict[str, dict[str, Any]] = {}
    for item in items:
        niche = item.niche or "未标注"
        bucket = buckets.setdefault(
            niche,
            {"niche": niche, "works": 0, "views": 0.0, "likes": 0.0, "samples": []},
        )
        bucket["works"] += 1
        if item.heat is not None:
            bucket["views"] += item.heat
        like = (item.extra or {}).get("like")
        try:
            if like is not None:
                bucket["likes"] += float(like)
        except (TypeError, ValueError):
            pass
        if len(bucket["samples"]) < 3:
            bucket["samples"].append(item.title)
    rows = list(buckets.values())
    rows.sort(key=lambda r: (r["works"], r["views"]), reverse=True)
    return rows


def _count_niches(items: list[HotItem]) -> list[dict[str, Any]]:
    counts: dict[str, int] = defaultdict(int)
    for item in items:
        niche = item.niche or "未标注"
        if niche == "未标注":
            continue
        counts[niche] += 1
    rows = [{"niche": k, "topics": v} for k, v in counts.items()]
    rows.sort(key=lambda r: r["topics"], reverse=True)
    return rows


def _overlaps(results: list[FetchResult]) -> list[dict[str, Any]]:
    # Compare topic-like titles across platforms; include Bilibili works too.
    pools: dict[str, list[tuple[str, HotItem]]] = {}
    for result in results:
        pools[result.platform] = [(norm_title(it.title), it) for it in result.items]
    platforms = list(pools.keys())
    found: list[dict[str, Any]] = []
    seen: set[tuple[str, ...]] = set()
    for i, left in enumerate(platforms):
        for right in platforms[i + 1 :]:
            for n1, a in pools[left]:
                if len(n1) < 2:
                    continue
                for n2, b in pools[right]:
                    if len(n2) < 2:
                        continue
                    if not titles_overlap(n1, n2):
                        continue
                    key = tuple(sorted((left, right, n1, n2)))
                    if key in seen:
                        continue
                    seen.add(key)
                    found.append(
                        {
                            "platforms": [left, right],
                            "titles": {left: a.title, right: b.title},
                            "ranks": {left: a.rank, right: b.rank},
                        }
                    )
    found.sort(
        key=lambda row: sum(
            (row["ranks"].get(p) or 999) for p in row["platforms"]
        )
    )
    return found[:30]


def norm_title(title: str) -> str:
    text = _PUNCT.sub("", str(title).casefold())
    return text


def titles_overlap(a: str, b: str) -> bool:
    if a == b:
        return True
    if len(a) >= 4 and (a in b or b in a):
        return True
    # Character Jaccard for short Chinese titles
    sa, sb = set(a), set(b)
    if not sa or not sb:
        return False
    inter = len(sa & sb)
    union = len(sa | sb)
    if union == 0:
        return False
    jaccard = inter / union
    if jaccard >= 0.72 and inter >= 3:
        return True
    # shared contiguous 3-gram
    if len(a) >= 3 and len(b) >= 3:
        grams = {a[i : i + 3] for i in range(len(a) - 2)}
        for i in range(len(b) - 2):
            if b[i : i + 3] in grams:
                return True
    return False

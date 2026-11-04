"""Canonical hot-item shape across platforms."""
from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any, Literal

Kind = Literal["work", "topic"]
Platform = Literal["bilibili", "weibo", "douyin"]


@dataclass
class HotItem:
    kind: Kind
    platform: Platform
    title: str
    rank: int | None = None
    heat: float | None = None
    niche: str = "未标注"
    url: str = ""
    author: str = ""
    extra: dict[str, Any] | None = None

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        if not data.get("extra"):
            data.pop("extra", None)
        return data

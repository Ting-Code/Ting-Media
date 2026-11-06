# -*- coding: utf-8 -*-
"""Platform rules for Douyin / Bilibili Toy / Xiaohongshu offline HTML."""
from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path
from typing import Any

SPEC_PATH = Path(__file__).with_name("platform_specs.json")
PLATFORMS = ("douyin", "bilibili", "xhs")


@lru_cache(maxsize=1)
def load_specs() -> dict[str, Any]:
    return json.loads(SPEC_PATH.read_text(encoding="utf-8"))


def get_spec(platform: str) -> dict[str, Any]:
    key = platform.strip().lower()
    aliases = {
        "dy": "douyin",
        "抖音": "douyin",
        "bili": "bilibili",
        "b站": "bilibili",
        "toy": "bilibili",
        "red": "xhs",
        "xiaohongshu": "xhs",
        "小红书": "xhs",
    }
    key = aliases.get(key, key)
    specs = load_specs()
    if key not in specs:
        raise KeyError(f"unknown platform: {platform!r}; choose from {', '.join(PLATFORMS)}")
    return {"id": key, **specs[key]}


def common_constraints() -> dict[str, Any]:
    """Intersection that can ship to all three platforms."""
    return {
        "entry": "index.html",
        "allow_inline_script": False,
        "allow_inline_event_handlers": False,
        "allow_network": False,
        "allow_external_cdn": False,
        "allow_external_nav": False,
        "allow_eval": False,
        "allow_iframe": False,
        "prefer_multi_file": True,
        "zip_max_mb": 8,
        "entry_html_max_mb": 1,
        "notes": [
            "三端交集：外置 JS/CSS、无网络、无 eval/iframe、入口 index.html",
            "zip 按抖音 8MB 控；入口 HTML 按 B 站 1MB 控",
        ],
    }

"""Filter registry."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

FilterFn = Callable[[dict[str, Any], dict[str, Any]], bool]

_FILTERS: dict[str, FilterFn] = {}


def register(filter_id: str):
    def deco(fn: FilterFn):
        _FILTERS[filter_id] = fn
        return fn

    return deco


def get_filter(filter_id: str) -> FilterFn:
    if filter_id not in _FILTERS:
        raise KeyError(f"unknown filter: {filter_id}")
    return _FILTERS[filter_id]


def known_filters() -> list[str]:
    return sorted(_FILTERS)

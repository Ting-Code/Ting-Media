"""Shared HTTP helpers: UA, retry, soft rate limit."""
from __future__ import annotations

import time
from typing import Any

import requests

DEFAULT_UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/120.0.0.0 Safari/537.36"
)
_LAST_AT = 0.0
_MIN_GAP = 0.35


def get_json(
    url: str,
    *,
    headers: dict[str, str] | None = None,
    params: dict[str, Any] | None = None,
    timeout: float = 12.0,
    retries: int = 3,
) -> Any:
    global _LAST_AT
    hdrs = {"User-Agent": DEFAULT_UA, "Accept": "application/json,text/plain,*/*"}
    if headers:
        hdrs.update(headers)
    last_error: Exception | None = None
    for attempt in range(retries):
        wait = _MIN_GAP - (time.monotonic() - _LAST_AT)
        if wait > 0:
            time.sleep(wait)
        try:
            resp = requests.get(url, headers=hdrs, params=params, timeout=timeout)
            _LAST_AT = time.monotonic()
            resp.raise_for_status()
            return resp.json()
        except Exception as exc:  # noqa: BLE001
            last_error = exc
            time.sleep(0.6 * (attempt + 1))
    assert last_error is not None
    raise last_error

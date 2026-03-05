"""Global RPM throttle and retry-on-429 for Nvidia NIM free tier."""

from __future__ import annotations

import asyncio
import time
from typing import Any

import httpx


class Throttle:
    """Global request throttle to stay under RPM limit."""

    def __init__(self, rpm: int = 35):
        self._interval = 60.0 / rpm  # ~1.7s between requests
        self._lock = asyncio.Lock()
        self._last = 0.0

    async def wait(self) -> None:
        async with self._lock:
            now = time.monotonic()
            wait_time = self._interval - (now - self._last)
            if wait_time > 0:
                await asyncio.sleep(wait_time)
            self._last = time.monotonic()


_throttle = Throttle()


async def throttled_request(
    client: httpx.AsyncClient,
    method: str,
    url: str,
    **kwargs: Any,
) -> httpx.Response:
    """Make a throttled request with retry-on-429."""
    await _throttle.wait()
    resp = await client.request(method, url, **kwargs)

    if resp.status_code == 429:
        retry_after = float(resp.headers.get("retry-after", "5"))
        await asyncio.sleep(retry_after)
        await _throttle.wait()
        resp = await client.request(method, url, **kwargs)

    return resp


def get_throttle() -> Throttle:
    """Return the global throttle instance."""
    return _throttle

"""Async SSE stream parser for chat completion streaming responses."""

from __future__ import annotations

import json
from typing import AsyncIterator

import httpx


async def parse_sse_stream(response: httpx.Response) -> AsyncIterator[dict | str]:
    """Parse an SSE stream, yielding parsed JSON dicts or "[DONE]".

    Each SSE event has the form:
        data: {"id": ..., ...}
    or:
        data: [DONE]
    """
    buffer = ""
    async for chunk in response.aiter_text():
        buffer += chunk
        while "\n" in buffer:
            line, buffer = buffer.split("\n", 1)
            line = line.strip()
            if not line:
                continue
            if line.startswith("data: "):
                payload = line[6:]
                if payload == "[DONE]":
                    yield "[DONE]"
                else:
                    try:
                        yield json.loads(payload)
                    except json.JSONDecodeError:
                        continue
    # Handle any remaining data in buffer
    remaining = buffer.strip()
    if remaining.startswith("data: "):
        payload = remaining[6:]
        if payload == "[DONE]":
            yield "[DONE]"
        else:
            try:
                yield json.loads(payload)
            except json.JSONDecodeError:
                pass

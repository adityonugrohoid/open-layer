"""Open Layer client — unified async interface for chat completions."""

from __future__ import annotations

import json
from typing import Any, AsyncIterator

import httpx

from open_layer.adapter import Adapter
from open_layer.types import (
    ChatCompletionRequest,
    ChatCompletionResponse,
    StreamChunk,
)


class _PassthroughAdapter:
    """Default adapter that passes payloads through unchanged (spec-native provider)."""

    @property
    def provider_name(self) -> str:
        return "passthrough"

    def translate_request(self, payload: dict[str, Any]) -> dict[str, Any]:
        return payload

    def translate_response(self, data: dict[str, Any]) -> dict[str, Any]:
        return data

    def translate_stream_chunk(self, data: dict[str, Any]) -> dict[str, Any]:
        return data


class OpenLayerClient:
    """Async client for Open Layer-compliant chat completions.

    Usage:
        client = OpenLayerClient(base_url="https://...", api_key="...", adapter=NvidiaAdapter())
        response = await client.chat(request)

        async for chunk in client.stream(request):
            print(chunk.choices[0].delta.content)
    """

    def __init__(
        self,
        base_url: str,
        api_key: str,
        adapter: Adapter | None = None,
        timeout: float = 120.0,
    ):
        self._adapter: Adapter = adapter or _PassthroughAdapter()
        self._http = httpx.AsyncClient(
            base_url=base_url.rstrip("/"),
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            },
            timeout=httpx.Timeout(timeout, connect=10.0),
        )

    async def chat(self, request: ChatCompletionRequest) -> ChatCompletionResponse:
        """Send a non-streaming chat completion request."""
        payload = self._adapter.translate_request(request.to_dict())
        payload.pop("stream", None)

        resp = await self._http.post("/chat/completions", json=payload)
        resp.raise_for_status()

        data = self._adapter.translate_response(resp.json())
        return ChatCompletionResponse.from_dict(data)

    async def stream(self, request: ChatCompletionRequest) -> AsyncIterator[StreamChunk]:
        """Send a streaming chat completion request, yielding chunks."""
        payload = self._adapter.translate_request(request.to_dict())
        payload["stream"] = True
        if request.stream_options is None:
            payload.setdefault("stream_options", {"include_usage": True})

        async with self._http.stream("POST", "/chat/completions", json=payload) as resp:
            resp.raise_for_status()
            buffer = ""
            async for text in resp.aiter_text():
                buffer += text
                while "\n" in buffer:
                    line, buffer = buffer.split("\n", 1)
                    line = line.strip()
                    if not line or not line.startswith("data: "):
                        continue
                    data_str = line[6:]
                    if data_str == "[DONE]":
                        return
                    try:
                        raw = json.loads(data_str)
                    except json.JSONDecodeError:
                        continue
                    translated = self._adapter.translate_stream_chunk(raw)
                    yield StreamChunk.from_dict(translated)

    async def close(self) -> None:
        await self._http.aclose()

    async def __aenter__(self) -> OpenLayerClient:
        return self

    async def __aexit__(self, *args: Any) -> None:
        await self.close()

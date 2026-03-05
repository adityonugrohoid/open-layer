"""Suite-level fixtures: httpx client, common request helpers."""

from __future__ import annotations

from typing import Any

import httpx
import pytest
import pytest_asyncio

from tests.conftest import ProviderConfig


@pytest_asyncio.fixture
async def client(provider_config: ProviderConfig) -> httpx.AsyncClient:
    async with httpx.AsyncClient(
        base_url=provider_config.base_url,
        headers={
            "Authorization": f"Bearer {provider_config.api_key}",
            "Content-Type": "application/json",
        },
        timeout=httpx.Timeout(60.0, connect=10.0),
    ) as c:
        yield c


@pytest.fixture
def chat_payload(provider_config: ProviderConfig) -> dict[str, Any]:
    """Minimal chat completion payload."""
    return {
        "model": provider_config.model,
        "messages": [{"role": "user", "content": "Say hi."}],
        "max_tokens": 10,
    }


@pytest.fixture
def thinking_payload(provider_config: ProviderConfig) -> dict[str, Any]:
    """Chat payload with thinking enabled, using the thinking model."""
    return {
        "model": provider_config.thinking_model,
        "messages": [{"role": "user", "content": "What is 2+2?"}],
        "max_tokens": 1024,
        "thinking": {"enabled": True},
    }


@pytest.fixture
def stream_payload(provider_config: ProviderConfig) -> dict[str, Any]:
    """Streaming chat completion payload."""
    return {
        "model": provider_config.model,
        "messages": [{"role": "user", "content": "Say hi."}],
        "max_tokens": 30,
        "stream": True,
        "stream_options": {"include_usage": True},
    }


@pytest.fixture
def thinking_stream_payload(provider_config: ProviderConfig) -> dict[str, Any]:
    """Streaming payload with thinking enabled."""
    return {
        "model": provider_config.thinking_model,
        "messages": [{"role": "user", "content": "What is 2+2?"}],
        "max_tokens": 1024,
        "stream": True,
        "stream_options": {"include_usage": True},
        "thinking": {"enabled": True},
    }

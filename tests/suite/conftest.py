"""Suite-level fixtures: throttled httpx client, common request helpers."""

from __future__ import annotations

import os
from typing import Any

import httpx
import pytest
import pytest_asyncio

from tests.models import ModelConfig, NVIDIA_BASE_URL, NVIDIA_ENV_KEY
from tests.suite.helpers.throttle import get_throttle


@pytest_asyncio.fixture
async def client() -> httpx.AsyncClient:
    api_key = os.environ.get(NVIDIA_ENV_KEY, "")
    if not api_key:
        pytest.skip(f"Missing {NVIDIA_ENV_KEY} environment variable")
    async with httpx.AsyncClient(
        base_url=NVIDIA_BASE_URL,
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        },
        timeout=httpx.Timeout(120.0, connect=10.0),
    ) as c:
        yield c


@pytest.fixture
def chat_payload(model_config: ModelConfig) -> dict[str, Any]:
    """Minimal chat completion payload."""
    return {
        "model": model_config.id,
        "messages": [{"role": "user", "content": "Say hi."}],
        "max_tokens": 10,
    }


@pytest.fixture
def thinking_payload(model_config: ModelConfig) -> dict[str, Any]:
    """Chat payload for thinking models — no thinking request param (Nvidia uses <think> tags inherently)."""
    return {
        "model": model_config.id,
        "messages": [{"role": "user", "content": "What is 2+2?"}],
        "max_tokens": 1024,
    }


@pytest.fixture
def stream_payload(model_config: ModelConfig) -> dict[str, Any]:
    """Streaming chat completion payload."""
    return {
        "model": model_config.id,
        "messages": [{"role": "user", "content": "Say hi."}],
        "max_tokens": 30,
        "stream": True,
        "stream_options": {"include_usage": True},
    }


@pytest.fixture
def thinking_stream_payload(model_config: ModelConfig) -> dict[str, Any]:
    """Streaming payload for thinking models — no thinking param."""
    return {
        "model": model_config.id,
        "messages": [{"role": "user", "content": "What is 2+2?"}],
        "max_tokens": 1024,
        "stream": True,
        "stream_options": {"include_usage": True},
    }

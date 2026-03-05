"""Level 1 + Level 2 conformance tests: usage token reporting."""

from __future__ import annotations

from typing import Any

import httpx
import pytest

from tests.conftest import ProviderConfig, require_thinking
from tests.suite.helpers.sse import parse_sse_stream
from tests.suite.helpers.schema import validate


# --- Helpers ---

async def get_response(client: httpx.AsyncClient, payload: dict[str, Any]) -> dict:
    resp = await client.post("/chat/completions", json=payload)
    assert resp.status_code == 200, f"Expected 200, got {resp.status_code}: {resp.text}"
    return resp.json()


async def get_stream_usage(client: httpx.AsyncClient, payload: dict[str, Any]) -> dict | None:
    payload = {**payload, "stream": True, "stream_options": {"include_usage": True}}
    async with client.stream("POST", "/chat/completions", json=payload) as resp:
        resp.raise_for_status()
        last_usage = None
        async for event in parse_sse_stream(resp):
            if isinstance(event, dict) and event.get("usage") is not None:
                last_usage = event["usage"]
    return last_usage


# --- Level 1 Tests ---

@pytest.mark.level1
async def test_usage_present_in_response(client: httpx.AsyncClient, chat_payload: dict) -> None:
    data = await get_response(client, chat_payload)
    assert "usage" in data, "Response missing 'usage' field"


@pytest.mark.level1
async def test_usage_has_required_fields(client: httpx.AsyncClient, chat_payload: dict) -> None:
    data = await get_response(client, chat_payload)
    usage = data["usage"]
    for field in ("prompt_tokens", "completion_tokens", "total_tokens"):
        assert field in usage, f"usage missing required field: {field}"


@pytest.mark.level1
async def test_usage_fields_are_integers(client: httpx.AsyncClient, chat_payload: dict) -> None:
    data = await get_response(client, chat_payload)
    usage = data["usage"]
    for field in ("prompt_tokens", "completion_tokens", "total_tokens"):
        val = usage[field]
        assert isinstance(val, int) and val >= 0, f"usage.{field} should be non-negative int, got {val!r}"


@pytest.mark.level1
async def test_total_tokens_equals_sum(client: httpx.AsyncClient, chat_payload: dict) -> None:
    data = await get_response(client, chat_payload)
    usage = data["usage"]
    expected = usage["prompt_tokens"] + usage["completion_tokens"]
    assert usage["total_tokens"] == expected, (
        f"total_tokens ({usage['total_tokens']}) != prompt ({usage['prompt_tokens']}) + completion ({usage['completion_tokens']})"
    )


@pytest.mark.level1
async def test_usage_schema_valid(client: httpx.AsyncClient, chat_payload: dict) -> None:
    data = await get_response(client, chat_payload)
    errors = validate(data["usage"], "usage")
    assert not errors, f"Usage schema validation errors: {errors}"


@pytest.mark.level1
async def test_streaming_usage_present(client: httpx.AsyncClient, chat_payload: dict) -> None:
    usage = await get_stream_usage(client, chat_payload)
    assert usage is not None, "No usage in streaming response with include_usage=true"


# --- Level 2 Tests ---

@pytest.mark.level2
async def test_thinking_has_reasoning_tokens(
    client: httpx.AsyncClient, thinking_payload: dict, provider_config: ProviderConfig
) -> None:
    require_thinking(provider_config)
    data = await get_response(client, thinking_payload)
    usage = data["usage"]
    details = usage.get("completion_tokens_details", {})
    if details:
        assert "reasoning_tokens" in details, "completion_tokens_details missing reasoning_tokens"


@pytest.mark.level2
async def test_reasoning_tokens_lte_completion_tokens(
    client: httpx.AsyncClient, thinking_payload: dict, provider_config: ProviderConfig
) -> None:
    require_thinking(provider_config)
    data = await get_response(client, thinking_payload)
    usage = data["usage"]
    details = usage.get("completion_tokens_details", {})
    if details and "reasoning_tokens" in details:
        assert details["reasoning_tokens"] <= usage["completion_tokens"], (
            f"reasoning_tokens ({details['reasoning_tokens']}) > completion_tokens ({usage['completion_tokens']})"
        )


@pytest.mark.level2
async def test_no_thinking_still_has_reasoning_tokens_zero(
    client: httpx.AsyncClient, chat_payload: dict, provider_config: ProviderConfig
) -> None:
    require_thinking(provider_config)
    # Use the thinking model but without enabling thinking
    payload = {**chat_payload, "model": provider_config.thinking_model}
    data = await get_response(client, payload)
    usage = data["usage"]
    details = usage.get("completion_tokens_details", {})
    if details and "reasoning_tokens" in details:
        assert details["reasoning_tokens"] == 0, (
            f"reasoning_tokens should be 0 without thinking enabled, got {details['reasoning_tokens']}"
        )

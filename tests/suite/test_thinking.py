"""Level 2 conformance tests: thinking/reasoning token support."""

from __future__ import annotations

from typing import Any

import httpx
import pytest

from tests.models import ModelConfig
from tests.conftest import require_thinking, require_budget
from tests.suite.helpers.schema import validate
from tests.suite.helpers.throttle import get_throttle

pytestmark = pytest.mark.level2


# --- Helpers ---

async def post_chat(client: httpx.AsyncClient, payload: dict[str, Any]) -> httpx.Response:
    await get_throttle().wait()
    return await client.post("/chat/completions", json=payload)


# --- Tests ---

async def test_thinking_request_accepted(
    client: httpx.AsyncClient, thinking_payload: dict, model_config: ModelConfig
) -> None:
    require_thinking(model_config)
    resp = await post_chat(client, thinking_payload)
    assert resp.status_code == 200, f"Thinking request rejected: {resp.text}"


@pytest.mark.xfail(reason="Nvidia uses <think> tags in content, not message.thinking.content")
async def test_thinking_enabled_returns_thinking_content(
    client: httpx.AsyncClient, thinking_payload: dict, model_config: ModelConfig
) -> None:
    require_thinking(model_config)
    resp = await post_chat(client, thinking_payload)
    assert resp.status_code == 200
    msg = resp.json()["choices"][0]["message"]
    assert "thinking" in msg, "Response message missing 'thinking' field when thinking enabled"
    assert "content" in msg["thinking"], "thinking object missing 'content' field"


@pytest.mark.xfail(reason="Nvidia uses <think> tags in content, not message.thinking.content")
async def test_thinking_content_is_string(
    client: httpx.AsyncClient, thinking_payload: dict, model_config: ModelConfig
) -> None:
    require_thinking(model_config)
    resp = await post_chat(client, thinking_payload)
    assert resp.status_code == 200
    thinking = resp.json()["choices"][0]["message"]["thinking"]
    assert isinstance(thinking["content"], str), f"thinking.content should be string, got {type(thinking['content'])}"


@pytest.mark.xfail(reason="Nvidia uses <think> tags in content, not message.thinking.content")
async def test_thinking_content_nonempty(
    client: httpx.AsyncClient, thinking_payload: dict, model_config: ModelConfig
) -> None:
    require_thinking(model_config)
    resp = await post_chat(client, thinking_payload)
    assert resp.status_code == 200
    thinking = resp.json()["choices"][0]["message"]["thinking"]
    assert len(thinking["content"]) > 0, "thinking.content should be non-empty"


async def test_thinking_disabled_no_thinking_field(
    client: httpx.AsyncClient, model_config: ModelConfig
) -> None:
    require_thinking(model_config)
    payload = {
        "model": model_config.id,
        "messages": [{"role": "user", "content": "Say hi."}],
        "max_tokens": 10,
    }
    resp = await post_chat(client, payload)
    assert resp.status_code == 200
    msg = resp.json()["choices"][0]["message"]
    thinking = msg.get("thinking")
    # When not explicitly requested, thinking should be absent or have empty/null content
    if thinking is not None:
        assert not thinking.get("content"), "thinking.content should be empty when disabled"


async def test_no_thinking_object_no_thinking_field(
    client: httpx.AsyncClient, model_config: ModelConfig
) -> None:
    require_thinking(model_config)
    payload = {
        "model": model_config.id,
        "messages": [{"role": "user", "content": "Say hi."}],
        "max_tokens": 10,
    }
    resp = await post_chat(client, payload)
    assert resp.status_code == 200
    msg = resp.json()["choices"][0]["message"]
    thinking = msg.get("thinking")
    if thinking is not None:
        assert not thinking.get("content"), "thinking.content should be empty when thinking not requested"


async def test_budget_tokens_accepted(
    client: httpx.AsyncClient, model_config: ModelConfig
) -> None:
    require_thinking(model_config)
    require_budget(model_config)
    payload = {
        "model": model_config.id,
        "messages": [{"role": "user", "content": "What is 2+2?"}],
        "max_tokens": 1024,
        "thinking": {"enabled": True, "budget_tokens": 512},
    }
    resp = await post_chat(client, payload)
    assert resp.status_code == 200, f"budget_tokens rejected: {resp.text}"


@pytest.mark.xfail(reason="Nvidia uses <think> tags in content, not message.thinking.content")
async def test_thinking_response_schema_valid(
    client: httpx.AsyncClient, thinking_payload: dict, model_config: ModelConfig
) -> None:
    require_thinking(model_config)
    resp = await post_chat(client, thinking_payload)
    assert resp.status_code == 200
    errors = validate(resp.json(), "chat-completion-response")
    assert not errors, f"Schema validation errors: {errors}"


async def test_thinking_multiturn_strip_thinking(
    client: httpx.AsyncClient, model_config: ModelConfig
) -> None:
    """Multi-turn with a previous thinking response should work.

    Per spec, thinking content from prior turns should be handled gracefully.
    """
    require_thinking(model_config)
    payload = {
        "model": model_config.id,
        "messages": [
            {"role": "user", "content": "What is 2+2?"},
            {"role": "assistant", "content": "4"},
            {"role": "user", "content": "And 3+3?"},
        ],
        "max_tokens": 1024,
    }
    resp = await post_chat(client, payload)
    assert resp.status_code == 200, f"Multi-turn with thinking failed: {resp.text}"

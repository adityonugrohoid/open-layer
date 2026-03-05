"""Level 1 conformance tests: POST /v1/chat/completions (non-streaming)."""

from __future__ import annotations

import time
from typing import Any

import httpx
import pytest

from tests.models import ModelConfig
from tests.suite.helpers.schema import validate
from tests.suite.helpers.throttle import get_throttle

pytestmark = pytest.mark.level1


# --- Helpers ---

async def post_chat(client: httpx.AsyncClient, payload: dict[str, Any]) -> httpx.Response:
    await get_throttle().wait()
    return await client.post("/chat/completions", json=payload)


# --- Tests ---

async def test_endpoint_accepts_post(client: httpx.AsyncClient, chat_payload: dict) -> None:
    resp = await post_chat(client, chat_payload)
    assert resp.status_code == 200, f"Expected 200, got {resp.status_code}: {resp.text}"


async def test_response_schema_valid(client: httpx.AsyncClient, chat_payload: dict) -> None:
    resp = await post_chat(client, chat_payload)
    assert resp.status_code == 200
    errors = validate(resp.json(), "chat-completion-response")
    assert not errors, f"Schema validation errors: {errors}"


async def test_response_has_required_fields(client: httpx.AsyncClient, chat_payload: dict) -> None:
    resp = await post_chat(client, chat_payload)
    data = resp.json()
    for field in ("id", "object", "created", "model", "choices", "usage"):
        assert field in data, f"Missing required field: {field}"


async def test_object_is_chat_completion(client: httpx.AsyncClient, chat_payload: dict) -> None:
    resp = await post_chat(client, chat_payload)
    assert resp.json()["object"] == "chat.completion"


async def test_id_is_string(client: httpx.AsyncClient, chat_payload: dict) -> None:
    resp = await post_chat(client, chat_payload)
    id_val = resp.json()["id"]
    assert isinstance(id_val, str) and len(id_val) > 0, f"id should be non-empty string, got {id_val!r}"


async def test_created_is_unix_timestamp(client: httpx.AsyncClient, chat_payload: dict) -> None:
    resp = await post_chat(client, chat_payload)
    created = resp.json()["created"]
    assert isinstance(created, int), f"created should be int, got {type(created)}"
    now = int(time.time())
    assert now - 300 <= created <= now + 60, f"created {created} not a reasonable timestamp (now={now})"


async def test_model_is_string(client: httpx.AsyncClient, chat_payload: dict) -> None:
    resp = await post_chat(client, chat_payload)
    model = resp.json()["model"]
    assert isinstance(model, str) and len(model) > 0, f"model should be non-empty string, got {model!r}"


async def test_choices_has_message(client: httpx.AsyncClient, chat_payload: dict) -> None:
    resp = await post_chat(client, chat_payload)
    choices = resp.json()["choices"]
    assert len(choices) >= 1, "choices should have at least one item"
    msg = choices[0]["message"]
    assert msg["role"] == "assistant", f"Expected role 'assistant', got {msg['role']!r}"


async def test_finish_reason_is_standard(client: httpx.AsyncClient, chat_payload: dict) -> None:
    resp = await post_chat(client, chat_payload)
    reason = resp.json()["choices"][0]["finish_reason"]
    assert reason in {"stop", "length", "tool_calls"}, f"Unexpected finish_reason: {reason!r}"


async def test_finish_reason_stop(client: httpx.AsyncClient, chat_payload: dict) -> None:
    payload = {**chat_payload, "max_tokens": 100}
    resp = await post_chat(client, payload)
    reason = resp.json()["choices"][0]["finish_reason"]
    assert reason == "stop", f"Expected 'stop', got {reason!r}"


async def test_finish_reason_length(client: httpx.AsyncClient, model_config: ModelConfig) -> None:
    payload = {
        "model": model_config.id,
        "messages": [{"role": "user", "content": "Write a very long essay about the history of mathematics."}],
        "max_tokens": 5,
    }
    resp = await post_chat(client, payload)
    reason = resp.json()["choices"][0]["finish_reason"]
    assert reason == "length", f"Expected 'length' with max_tokens=5, got {reason!r}"


async def test_system_role_supported(client: httpx.AsyncClient, model_config: ModelConfig) -> None:
    payload = {
        "model": model_config.id,
        "messages": [
            {"role": "system", "content": "You are a helpful assistant."},
            {"role": "user", "content": "Say hi."},
        ],
        "max_tokens": 10,
    }
    resp = await post_chat(client, payload)
    assert resp.status_code == 200, f"System role not accepted: {resp.text}"


async def test_user_role_supported(client: httpx.AsyncClient, chat_payload: dict) -> None:
    resp = await post_chat(client, chat_payload)
    assert resp.status_code == 200


async def test_assistant_role_in_multiturn(client: httpx.AsyncClient, model_config: ModelConfig) -> None:
    payload = {
        "model": model_config.id,
        "messages": [
            {"role": "user", "content": "Say hi."},
            {"role": "assistant", "content": "Hi!"},
            {"role": "user", "content": "Say bye."},
        ],
        "max_tokens": 10,
    }
    resp = await post_chat(client, payload)
    assert resp.status_code == 200, f"Multi-turn with assistant role failed: {resp.text}"


async def test_temperature_parameter(client: httpx.AsyncClient, chat_payload: dict) -> None:
    payload = {**chat_payload, "temperature": 0.1}
    resp = await post_chat(client, payload)
    assert resp.status_code == 200, f"temperature=0.1 rejected: {resp.text}"


async def test_top_p_parameter(client: httpx.AsyncClient, chat_payload: dict) -> None:
    payload = {**chat_payload, "top_p": 0.9}
    resp = await post_chat(client, payload)
    assert resp.status_code == 200, f"top_p=0.9 rejected: {resp.text}"


async def test_max_tokens_parameter(client: httpx.AsyncClient, model_config: ModelConfig) -> None:
    payload = {
        "model": model_config.id,
        "messages": [{"role": "user", "content": "Write a long story."}],
        "max_tokens": 10,
    }
    resp = await post_chat(client, payload)
    assert resp.status_code == 200
    content = resp.json()["choices"][0]["message"]["content"]
    assert content is not None, "content should not be None"


async def test_stop_parameter_string(client: httpx.AsyncClient, chat_payload: dict) -> None:
    payload = {**chat_payload, "stop": "."}
    resp = await post_chat(client, payload)
    assert resp.status_code == 200, f"stop='.' rejected: {resp.text}"


async def test_stop_parameter_array(client: httpx.AsyncClient, chat_payload: dict) -> None:
    payload = {**chat_payload, "stop": [".", "!"]}
    resp = await post_chat(client, payload)
    assert resp.status_code == 200, f"stop=['.', '!'] rejected: {resp.text}"


async def test_unknown_fields_accepted(client: httpx.AsyncClient, chat_payload: dict) -> None:
    payload = {**chat_payload, "x_test_field": "hello"}
    resp = await post_chat(client, payload)
    # Should not return an error — unknown fields are allowed per spec
    assert resp.status_code == 200, f"Unknown field rejected: {resp.text}"


async def test_message_content_is_string_or_null(client: httpx.AsyncClient, chat_payload: dict) -> None:
    resp = await post_chat(client, chat_payload)
    content = resp.json()["choices"][0]["message"]["content"]
    assert content is None or isinstance(content, str), f"content should be string or null, got {type(content)}"

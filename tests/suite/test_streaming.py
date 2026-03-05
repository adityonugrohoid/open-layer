"""Level 1 + Level 2 conformance tests: streaming chat completions (SSE)."""

from __future__ import annotations

from typing import Any

import httpx
import pytest

from tests.conftest import ProviderConfig, require_thinking
from tests.suite.helpers.sse import parse_sse_stream
from tests.suite.helpers.schema import validate


# --- Helpers ---

async def collect_stream(client: httpx.AsyncClient, payload: dict[str, Any]) -> tuple[list[dict], bool]:
    """Send a streaming request and collect all chunks + whether [DONE] was received."""
    chunks: list[dict] = []
    got_done = False
    async with client.stream("POST", "/chat/completions", json=payload) as resp:
        resp.raise_for_status()
        async for event in parse_sse_stream(resp):
            if event == "[DONE]":
                got_done = True
            else:
                chunks.append(event)
    return chunks, got_done


# --- Level 1 Tests ---

@pytest.mark.level1
async def test_stream_returns_sse(client: httpx.AsyncClient, stream_payload: dict) -> None:
    async with client.stream("POST", "/chat/completions", json=stream_payload) as resp:
        content_type = resp.headers.get("content-type", "")
        assert "text/event-stream" in content_type, f"Expected text/event-stream, got {content_type}"


@pytest.mark.level1
async def test_stream_events_prefixed_with_data(client: httpx.AsyncClient, stream_payload: dict) -> None:
    async with client.stream("POST", "/chat/completions", json=stream_payload) as resp:
        found_data_line = False
        async for chunk in resp.aiter_text():
            for line in chunk.split("\n"):
                line = line.strip()
                if not line:
                    continue
                if line.startswith("data: "):
                    found_data_line = True
                    break
            if found_data_line:
                break
        assert found_data_line, "No SSE lines starting with 'data: ' found"


@pytest.mark.level1
async def test_stream_terminates_with_done(client: httpx.AsyncClient, stream_payload: dict) -> None:
    _, got_done = await collect_stream(client, stream_payload)
    assert got_done, "Stream did not terminate with [DONE]"


@pytest.mark.level1
async def test_chunk_has_required_fields(client: httpx.AsyncClient, stream_payload: dict) -> None:
    chunks, _ = await collect_stream(client, stream_payload)
    assert len(chunks) > 0, "No chunks received"
    first = chunks[0]
    for field in ("id", "object", "created", "model", "choices"):
        assert field in first, f"Chunk missing required field: {field}"


@pytest.mark.level1
async def test_chunk_object_is_chunk(client: httpx.AsyncClient, stream_payload: dict) -> None:
    chunks, _ = await collect_stream(client, stream_payload)
    assert len(chunks) > 0
    assert chunks[0]["object"] == "chat.completion.chunk"


@pytest.mark.level1
async def test_chunk_ids_consistent(client: httpx.AsyncClient, stream_payload: dict) -> None:
    chunks, _ = await collect_stream(client, stream_payload)
    assert len(chunks) > 0
    stream_id = chunks[0]["id"]
    for i, chunk in enumerate(chunks):
        assert chunk["id"] == stream_id, f"Chunk {i} has id {chunk['id']!r}, expected {stream_id!r}"


@pytest.mark.level1
async def test_first_chunk_has_role(client: httpx.AsyncClient, stream_payload: dict) -> None:
    chunks, _ = await collect_stream(client, stream_payload)
    # Find the first chunk with non-empty choices
    for chunk in chunks:
        if chunk.get("choices"):
            delta = chunk["choices"][0].get("delta", {})
            assert delta.get("role") == "assistant", f"First delta should have role='assistant', got {delta}"
            return
    pytest.fail("No chunks with choices found")


@pytest.mark.level1
async def test_final_chunk_has_finish_reason(client: httpx.AsyncClient, stream_payload: dict) -> None:
    chunks, _ = await collect_stream(client, stream_payload)
    # Find the last chunk with non-empty choices
    for chunk in reversed(chunks):
        choices = chunk.get("choices", [])
        if choices:
            reason = choices[0].get("finish_reason")
            assert reason is not None, "Final chunk with choices should have a finish_reason"
            assert reason in {"stop", "length", "tool_calls"}, f"Unexpected finish_reason: {reason!r}"
            return
    pytest.fail("No chunks with choices found")


@pytest.mark.level1
async def test_stream_usage_with_include_usage(client: httpx.AsyncClient, stream_payload: dict) -> None:
    chunks, _ = await collect_stream(client, stream_payload)
    usage_chunks = [c for c in chunks if c.get("usage") is not None]
    assert len(usage_chunks) >= 1, "No usage chunk found with stream_options.include_usage=true"


@pytest.mark.level1
async def test_usage_chunk_has_empty_choices(client: httpx.AsyncClient, stream_payload: dict) -> None:
    chunks, _ = await collect_stream(client, stream_payload)
    usage_chunks = [c for c in chunks if c.get("usage") is not None]
    if not usage_chunks:
        pytest.skip("No usage chunk in stream")
    for uc in usage_chunks:
        choices = uc.get("choices", [])
        # Usage chunk should have empty choices or no choices
        assert len(choices) == 0, f"Usage chunk should have empty choices, got {len(choices)}"


@pytest.mark.level1
async def test_stream_content_accumulates(client: httpx.AsyncClient, stream_payload: dict) -> None:
    chunks, _ = await collect_stream(client, stream_payload)
    content_parts = []
    for chunk in chunks:
        for choice in chunk.get("choices", []):
            delta = choice.get("delta", {})
            if "content" in delta and delta["content"]:
                content_parts.append(delta["content"])
    full_content = "".join(content_parts)
    assert len(full_content) > 0, "Accumulated stream content is empty"


# --- Level 2 Tests ---

@pytest.mark.level2
async def test_stream_thinking_uses_delta_thinking_content(
    client: httpx.AsyncClient, thinking_stream_payload: dict, provider_config: ProviderConfig
) -> None:
    require_thinking(provider_config)
    chunks, _ = await collect_stream(client, thinking_stream_payload)
    thinking_deltas = []
    for chunk in chunks:
        for choice in chunk.get("choices", []):
            delta = choice.get("delta", {})
            if "thinking" in delta and delta["thinking"].get("content"):
                thinking_deltas.append(delta["thinking"]["content"])
    assert len(thinking_deltas) > 0, "No thinking deltas found in stream"


@pytest.mark.level2
async def test_stream_thinking_content_no_overlap(
    client: httpx.AsyncClient, thinking_stream_payload: dict, provider_config: ProviderConfig
) -> None:
    """Thinking deltas and content deltas MUST NOT overlap in the same chunk."""
    require_thinking(provider_config)
    chunks, _ = await collect_stream(client, thinking_stream_payload)
    for i, chunk in enumerate(chunks):
        for choice in chunk.get("choices", []):
            delta = choice.get("delta", {})
            has_thinking = "thinking" in delta and delta["thinking"].get("content")
            has_content = "content" in delta and delta["content"]
            assert not (has_thinking and has_content), (
                f"Chunk {i}: thinking and content overlap in same delta"
            )


@pytest.mark.level2
async def test_stream_thinking_usage_has_reasoning_tokens(
    client: httpx.AsyncClient, thinking_stream_payload: dict, provider_config: ProviderConfig
) -> None:
    require_thinking(provider_config)
    chunks, _ = await collect_stream(client, thinking_stream_payload)
    usage_chunks = [c for c in chunks if c.get("usage") is not None]
    if not usage_chunks:
        pytest.skip("No usage chunk in stream")
    usage = usage_chunks[-1]["usage"]
    details = usage.get("completion_tokens_details", {})
    if details:
        assert "reasoning_tokens" in details, "completion_tokens_details missing reasoning_tokens"
        assert isinstance(details["reasoning_tokens"], int), "reasoning_tokens should be int"

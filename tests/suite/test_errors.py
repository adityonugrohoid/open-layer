"""Level 1 conformance tests: error response format and status codes."""

from __future__ import annotations

from typing import Any

import httpx
import pytest

from tests.conftest import ProviderConfig
from tests.suite.helpers.schema import validate

pytestmark = pytest.mark.level1

STANDARD_ERROR_TYPES = {
    "invalid_request_error",
    "authentication_error",
    "permission_error",
    "not_found_error",
    "rate_limit_error",
    "server_error",
    "overloaded_error",
}

STATUS_TO_TYPE = {
    400: {"invalid_request_error"},
    401: {"authentication_error"},
    403: {"permission_error"},
    404: {"not_found_error"},
    429: {"rate_limit_error"},
    500: {"server_error"},
    503: {"overloaded_error", "server_error"},
}


# --- Helpers ---

async def post_chat(client: httpx.AsyncClient, payload: dict[str, Any]) -> httpx.Response:
    return await client.post("/chat/completions", json=payload)


# --- Tests ---

async def test_invalid_model_returns_error(
    client: httpx.AsyncClient, provider_config: ProviderConfig
) -> None:
    payload = {
        "model": "nonexistent-model-xyz-999",
        "messages": [{"role": "user", "content": "Hi."}],
        "max_tokens": 5,
    }
    resp = await post_chat(client, payload)
    assert resp.status_code >= 400, f"Expected error status, got {resp.status_code}"


async def test_error_has_type_and_message(
    client: httpx.AsyncClient, provider_config: ProviderConfig
) -> None:
    payload = {
        "model": "nonexistent-model-xyz-999",
        "messages": [{"role": "user", "content": "Hi."}],
        "max_tokens": 5,
    }
    resp = await post_chat(client, payload)
    assert resp.status_code >= 400
    data = resp.json()
    assert "error" in data, f"Error response missing 'error' field: {data}"
    error = data["error"]
    assert "type" in error, f"error object missing 'type': {error}"
    assert "message" in error, f"error object missing 'message': {error}"


async def test_error_type_is_standard(
    client: httpx.AsyncClient, provider_config: ProviderConfig
) -> None:
    payload = {
        "model": "nonexistent-model-xyz-999",
        "messages": [{"role": "user", "content": "Hi."}],
        "max_tokens": 5,
    }
    resp = await post_chat(client, payload)
    assert resp.status_code >= 400
    data = resp.json()
    error_type = data.get("error", {}).get("type")
    assert error_type in STANDARD_ERROR_TYPES, (
        f"error.type {error_type!r} not in standard set: {STANDARD_ERROR_TYPES}"
    )


async def test_error_schema_valid(
    client: httpx.AsyncClient, provider_config: ProviderConfig
) -> None:
    payload = {
        "model": "nonexistent-model-xyz-999",
        "messages": [{"role": "user", "content": "Hi."}],
        "max_tokens": 5,
    }
    resp = await post_chat(client, payload)
    assert resp.status_code >= 400
    errors = validate(resp.json(), "error")
    assert not errors, f"Error schema validation errors: {errors}"


async def test_invalid_model_returns_404_or_400(
    client: httpx.AsyncClient, provider_config: ProviderConfig
) -> None:
    payload = {
        "model": "nonexistent-model-xyz-999",
        "messages": [{"role": "user", "content": "Hi."}],
        "max_tokens": 5,
    }
    resp = await post_chat(client, payload)
    assert resp.status_code in {400, 404}, (
        f"Expected 400 or 404 for invalid model, got {resp.status_code}"
    )


async def test_missing_messages_returns_400(
    client: httpx.AsyncClient, provider_config: ProviderConfig
) -> None:
    payload = {"model": provider_config.model}
    resp = await post_chat(client, payload)
    assert resp.status_code == 400, f"Expected 400 for missing messages, got {resp.status_code}"


async def test_auth_error_returns_401(provider_config: ProviderConfig) -> None:
    async with httpx.AsyncClient(
        base_url=provider_config.base_url,
        headers={
            "Authorization": "Bearer invalid-key-xxx",
            "Content-Type": "application/json",
        },
        timeout=httpx.Timeout(30.0, connect=10.0),
    ) as bad_client:
        payload = {
            "model": provider_config.model,
            "messages": [{"role": "user", "content": "Hi."}],
            "max_tokens": 5,
        }
        resp = await bad_client.post("/chat/completions", json=payload)
        assert resp.status_code == 401, f"Expected 401 for bad auth, got {resp.status_code}"


async def test_error_type_matches_status_code(
    client: httpx.AsyncClient, provider_config: ProviderConfig
) -> None:
    payload = {
        "model": "nonexistent-model-xyz-999",
        "messages": [{"role": "user", "content": "Hi."}],
        "max_tokens": 5,
    }
    resp = await post_chat(client, payload)
    status = resp.status_code
    assert status >= 400
    data = resp.json()
    error_type = data.get("error", {}).get("type")
    expected_types = STATUS_TO_TYPE.get(status)
    if expected_types:
        assert error_type in expected_types, (
            f"Status {status} should have error.type in {expected_types}, got {error_type!r}"
        )

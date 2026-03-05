"""Level 1 conformance tests: GET /v1/capabilities (RECOMMENDED, skip on 404)."""

from __future__ import annotations

import httpx
import pytest

from tests.suite.helpers.schema import validate
from tests.suite.helpers.throttle import get_throttle

pytestmark = pytest.mark.level1


# --- Helpers ---

async def get_capabilities(client: httpx.AsyncClient) -> dict | None:
    await get_throttle().wait()
    resp = await client.get("/capabilities")
    if resp.status_code == 404:
        return None
    resp.raise_for_status()
    return resp.json()


# --- Tests (run once, not per-model) ---

async def test_capabilities_endpoint_exists(client: httpx.AsyncClient) -> None:
    await get_throttle().wait()
    resp = await client.get("/capabilities")
    if resp.status_code == 404:
        pytest.skip("Capabilities endpoint not implemented (404)")
    assert resp.status_code == 200, f"Expected 200, got {resp.status_code}: {resp.text}"


async def test_capabilities_has_required_fields(client: httpx.AsyncClient) -> None:
    data = await get_capabilities(client)
    if data is None:
        pytest.skip("Capabilities endpoint not implemented")
    for field in ("spec_version", "conformance_level", "features"):
        assert field in data, f"Missing required field: {field}"


async def test_capabilities_schema_valid(client: httpx.AsyncClient) -> None:
    data = await get_capabilities(client)
    if data is None:
        pytest.skip("Capabilities endpoint not implemented")
    errors = validate(data, "capabilities")
    assert not errors, f"Schema validation errors: {errors}"


async def test_spec_version_is_string(client: httpx.AsyncClient) -> None:
    data = await get_capabilities(client)
    if data is None:
        pytest.skip("Capabilities endpoint not implemented")
    assert isinstance(data["spec_version"], str), f"spec_version should be string, got {type(data['spec_version'])}"
    assert len(data["spec_version"]) > 0, "spec_version should be non-empty"


async def test_conformance_level_gte_one(client: httpx.AsyncClient) -> None:
    data = await get_capabilities(client)
    if data is None:
        pytest.skip("Capabilities endpoint not implemented")
    level = data["conformance_level"]
    assert isinstance(level, int) and level >= 1, f"conformance_level should be int >= 1, got {level!r}"

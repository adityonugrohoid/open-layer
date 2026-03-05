"""JSON Schema validator with $ref resolution across all spec schemas."""

from __future__ import annotations

import json
from pathlib import Path

from jsonschema import Draft202012Validator
from referencing import Registry, Resource


SCHEMA_DIR = Path(__file__).resolve().parent.parent.parent.parent / "spec" / "v0.1" / "schema"

_registry: Registry | None = None
_validators: dict[str, Draft202012Validator] = {}


def _build_registry() -> Registry:
    global _registry
    if _registry is not None:
        return _registry

    resources: list[tuple[str, Resource]] = []
    for schema_file in SCHEMA_DIR.glob("*.json"):
        schema = json.loads(schema_file.read_text())
        uri = schema.get("$id", f"file://{schema_file}")
        resource = Resource.from_contents(schema)
        resources.append((uri, resource))

    _registry = Registry().with_resources(resources)
    return _registry


def get_validator(schema_name: str) -> Draft202012Validator:
    """Get a validator for a named schema (e.g. 'chat-completion-response')."""
    if schema_name in _validators:
        return _validators[schema_name]

    schema_file = SCHEMA_DIR / f"{schema_name}.json"
    schema = json.loads(schema_file.read_text())
    registry = _build_registry()

    validator = Draft202012Validator(schema, registry=registry)
    _validators[schema_name] = validator
    return validator


def validate(data: dict, schema_name: str) -> list[str]:
    """Validate data against a schema. Returns list of error messages (empty = valid)."""
    validator = get_validator(schema_name)
    errors = list(validator.iter_errors(data))
    return [f"{e.json_path}: {e.message}" for e in errors]

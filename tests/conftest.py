"""Root conftest: CLI options, model loading, and parameterization."""

from __future__ import annotations

import os
from pathlib import Path

import pytest
from dotenv import load_dotenv

from tests.models import ModelConfig, MODELS, MODELS_BY_ID

# Load .env from project root
load_dotenv(Path(__file__).resolve().parent.parent / ".env")

# Default smoke subset for fast iteration (5 diverse models)
SMOKE_MODELS: list[str] = [
    "meta/llama-3.3-70b-instruct",
    "google/gemma-3-27b-it",
    "mistralai/mistral-small-3.1-24b-instruct-2503",
    "deepseek-ai/deepseek-r1-distill-qwen-14b",
    "microsoft/phi-4-mini-flash-reasoning",
]


def _resolve_models(config: pytest.Config) -> list[ModelConfig]:
    """Resolve CLI flags into a list of ModelConfig."""
    model_filters: list[str] | None = config.getoption("model")
    tag_filters: list[str] | None = config.getoption("tag")
    use_all: bool = config.getoption("all_models")

    if use_all:
        return list(MODELS)

    if model_filters:
        result = []
        for filt in model_filters:
            matches = [m for m in MODELS if filt in m.id]
            if not matches:
                pytest.exit(f"No models matching --model {filt!r}", returncode=1)
            result.extend(matches)
        # Deduplicate while preserving order
        seen: set[str] = set()
        deduped = []
        for m in result:
            if m.id not in seen:
                seen.add(m.id)
                deduped.append(m)
        return deduped

    if tag_filters:
        result = []
        for m in MODELS:
            if any(tag in m.tags for tag in tag_filters):
                result.append(m)
        if not result:
            pytest.exit(f"No models matching --tag {tag_filters}", returncode=1)
        return result

    # Default: smoke subset
    return [MODELS_BY_ID[mid] for mid in SMOKE_MODELS if mid in MODELS_BY_ID]


def pytest_addoption(parser: pytest.Parser) -> None:
    parser.addoption(
        "--model",
        action="append",
        default=None,
        help="Model ID substring filter (can be repeated). Default: smoke subset.",
    )
    parser.addoption(
        "--tag",
        action="append",
        default=None,
        help="Tag filter (can be repeated, e.g. --tag thinking). Default: smoke subset.",
    )
    parser.addoption(
        "--all",
        action="store_true",
        default=False,
        dest="all_models",
        help="Run against all 52 models.",
    )


def pytest_generate_tests(metafunc: pytest.Metafunc) -> None:
    if "model_config" in metafunc.fixturenames:
        models = _resolve_models(metafunc.config)
        if not models:
            pytest.skip("No models available")
        metafunc.parametrize(
            "model_config",
            models,
            ids=[m.short_id for m in models],
        )


def require_thinking(model_config: ModelConfig) -> None:
    """Skip the test if the model is not a thinking model."""
    if not model_config.is_thinking:
        pytest.skip(f"{model_config.short_id} is not a thinking model")


def require_budget(model_config: ModelConfig) -> None:
    """Skip the test — Nvidia has no budget control."""
    pytest.skip("Nvidia NIM does not support budget_tokens")

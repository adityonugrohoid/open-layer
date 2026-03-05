"""Root conftest: CLI options, provider loading, and parameterization."""

from __future__ import annotations

import os
from pathlib import Path
from dataclasses import dataclass

import pytest
import tomli
from dotenv import load_dotenv


# Load .env from project root
load_dotenv(Path(__file__).resolve().parent.parent / ".env")

PROVIDERS_PATH = Path(__file__).resolve().parent / "providers.toml"


@dataclass
class ProviderConfig:
    name: str
    base_url: str
    api_key: str
    model: str
    thinking_model: str
    supports_thinking: bool
    supports_budget: bool


def load_providers(names: list[str] | None = None) -> list[ProviderConfig]:
    with open(PROVIDERS_PATH, "rb") as f:
        data = tomli.load(f)

    providers = []
    for name, cfg in data.items():
        if names and name not in names:
            continue
        api_key = os.environ.get(cfg["env_key"], "")
        if not api_key:
            continue
        providers.append(
            ProviderConfig(
                name=name,
                base_url=cfg["base_url"].rstrip("/"),
                api_key=api_key,
                model=cfg["model"],
                thinking_model=cfg.get("thinking_model", ""),
                supports_thinking=cfg.get("supports_thinking", False),
                supports_budget=cfg.get("supports_budget", False),
            )
        )
    return providers


def pytest_addoption(parser: pytest.Parser) -> None:
    parser.addoption(
        "--provider",
        action="append",
        default=None,
        help="Provider name(s) to test (can be repeated). Default: all with keys.",
    )


def pytest_generate_tests(metafunc: pytest.Metafunc) -> None:
    if "provider_config" in metafunc.fixturenames:
        names = metafunc.config.getoption("provider")
        providers = load_providers(names)
        if not providers:
            pytest.skip("No providers available (missing API keys or --provider filter)")
        metafunc.parametrize(
            "provider_config",
            providers,
            ids=[p.name for p in providers],
        )


def require_thinking(provider_config: ProviderConfig) -> None:
    """Skip the test if the provider doesn't support thinking."""
    if not provider_config.supports_thinking or not provider_config.thinking_model:
        pytest.skip(f"{provider_config.name} does not support thinking")


def require_budget(provider_config: ProviderConfig) -> None:
    """Skip the test if the provider doesn't support budget control."""
    if not provider_config.supports_budget:
        pytest.skip(f"{provider_config.name} does not support budget_tokens")

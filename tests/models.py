"""Model registry for Nvidia NIM conformance testing.

Last probed: 2026-03-05. Models verified against live Nvidia NIM API.
"""

from __future__ import annotations

from dataclasses import dataclass

NVIDIA_BASE_URL = "https://integrate.api.nvidia.com/v1"
NVIDIA_ENV_KEY = "NVIDIA_API_KEY"


@dataclass(frozen=True)
class ModelConfig:
    id: str
    tags: frozenset[str]

    @property
    def is_thinking(self) -> bool:
        return "thinking" in self.tags

    @property
    def short_id(self) -> str:
        return self.id.split("/")[-1] if "/" in self.id else self.id


def _infer_tags(model_id: str) -> frozenset[str]:
    """Infer tags from the model ID string."""
    lower = model_id.lower()
    tags: set[str] = set()

    # Thinking/reasoning models
    if any(kw in lower for kw in ("r1", "qwq", "reasoning", "thinking")):
        tags.add("thinking")

    # Family tags
    families = {
        "llama": "llama",
        "gemma": "gemma",
        "mistral": "mistral",
        "mixtral": "mistral",
        "qwen": "qwen",
        "phi": "phi",
        "deepseek": "deepseek",
        "nemotron": "nemotron",
        "solar": "solar",
        "jamba": "jamba",
        "glm": "glm",
    }
    for keyword, family in families.items():
        if keyword in lower:
            tags.add(family)

    return frozenset(tags)


def _model(model_id: str) -> ModelConfig:
    return ModelConfig(id=model_id, tags=_infer_tags(model_id))


# 30 confirmed-working Nvidia NIM models (live probe 2026-03-05)
MODELS: list[ModelConfig] = [
    # Llama family (7)
    _model("meta/llama-3.3-70b-instruct"),
    _model("meta/llama-3.1-405b-instruct"),
    _model("meta/llama-3.1-70b-instruct"),
    _model("meta/llama-3.1-8b-instruct"),
    _model("meta/llama-3.2-1b-instruct"),
    _model("meta/llama-3.2-3b-instruct"),
    _model("meta/llama-3.2-90b-vision-instruct"),
    # Gemma family (7)
    _model("google/gemma-3-27b-it"),
    _model("google/gemma-3-12b-it"),
    _model("google/gemma-3-4b-it"),
    _model("google/gemma-3-1b-it"),
    _model("google/gemma-2-27b-it"),
    _model("google/gemma-2-9b-it"),
    _model("google/gemma-2-2b-it"),
    # Mistral family (3)
    _model("mistralai/mistral-small-3.1-24b-instruct-2503"),
    _model("mistralai/mixtral-8x22b-instruct-v0.1"),
    _model("mistralai/mixtral-8x7b-instruct-v0.1"),
    # DeepSeek thinking (2)
    _model("deepseek-ai/deepseek-r1-distill-qwen-14b"),
    _model("deepseek-ai/deepseek-r1-distill-llama-8b"),
    # Qwen family (1)
    _model("qwen/qwen2.5-coder-32b-instruct"),
    # Phi family (5)
    _model("microsoft/phi-4-mini-flash-reasoning"),
    _model("microsoft/phi-4-multimodal-instruct"),
    _model("microsoft/phi-3.5-mini-instruct"),
    _model("microsoft/phi-3-medium-128k-instruct"),
    _model("microsoft/phi-3-mini-128k-instruct"),
    # Nemotron (2)
    _model("nvidia/llama-3.1-nemotron-ultra-253b-v1"),
    _model("nvidia/nemotron-mini-4b-instruct"),
    # Others (3)
    _model("upstage/solar-10.7b-instruct"),
    _model("ai21labs/jamba-1.5-mini-instruct"),
    _model("thudm/chatglm3-6b"),
]

MODELS_BY_ID: dict[str, ModelConfig] = {m.id: m for m in MODELS}
THINKING_MODELS: list[ModelConfig] = [m for m in MODELS if m.is_thinking]
CHAT_MODELS: list[ModelConfig] = [m for m in MODELS if not m.is_thinking]

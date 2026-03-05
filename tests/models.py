"""Model registry for Nvidia NIM conformance testing."""

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
        "qwen": "qwen",
        "phi": "phi",
        "deepseek": "deepseek",
        "nemotron": "nemotron",
        "kimi": "kimi",
        "codestral": "mistral",
        "granite": "granite",
        "c4ai": "c4ai",
        "command": "c4ai",
        "palmyra": "palmyra",
        "solar": "solar",
        "jamba": "jamba",
        "arctic": "arctic",
        "starcoder": "starcoder",
        "yi-": "yi",
        "glm": "glm",
        "intern": "intern",
        "athene": "athene",
        "fugaku": "fugaku",
        "mamba": "mamba",
        "nv-": "nvidia",
        "nvidia/": "nvidia",
    }
    for keyword, family in families.items():
        if keyword in lower:
            tags.add(family)

    return frozenset(tags)


def _model(model_id: str) -> ModelConfig:
    return ModelConfig(id=model_id, tags=_infer_tags(model_id))


# 52 confirmed-working Nvidia NIM models (from live probe)
MODELS: list[ModelConfig] = [
    # Llama family
    _model("meta/llama-3.3-70b-instruct"),
    _model("meta/llama-3.1-405b-instruct"),
    _model("meta/llama-3.1-70b-instruct"),
    _model("meta/llama-3.1-8b-instruct"),
    _model("meta/llama-3.2-1b-instruct"),
    _model("meta/llama-3.2-3b-instruct"),
    _model("meta/llama-3.2-90b-vision-instruct"),
    _model("nvidia/llama-3.1-nemotron-70b-instruct"),
    _model("nvidia/llama-3.1-nemotron-ultra-253b-v1"),
    _model("nvidia/llama-3.3-nemotron-super-49b-v1"),
    # Gemma family
    _model("google/gemma-3-27b-it"),
    _model("google/gemma-3-12b-it"),
    _model("google/gemma-3-4b-it"),
    _model("google/gemma-3-1b-it"),
    _model("google/gemma-2-27b-it"),
    _model("google/gemma-2-9b-it"),
    _model("google/gemma-2-2b-it"),
    # Mistral family
    _model("mistralai/mistral-small-3.1-24b-instruct-2503"),
    _model("mistralai/mistral-large-2-instruct"),
    _model("mistralai/mixtral-8x22b-instruct-v0.1"),
    _model("mistralai/mixtral-8x7b-instruct-v0.1"),
    _model("mistralai/mistral-7b-instruct-v0.3"),
    _model("mistralai/codestral-22b-instruct-v0.1"),
    # DeepSeek family
    _model("deepseek-ai/deepseek-r1-distill-qwen-14b"),
    _model("deepseek-ai/deepseek-r1-distill-qwen-32b"),
    _model("deepseek-ai/deepseek-r1-distill-llama-8b"),
    _model("deepseek-ai/deepseek-r1-distill-llama-70b"),
    _model("deepseek-ai/deepseek-r1"),
    # Qwen family
    _model("qwen/qwen2.5-72b-instruct"),
    _model("qwen/qwen2.5-32b-instruct"),
    _model("qwen/qwen2.5-14b-instruct"),
    _model("qwen/qwen2.5-7b-instruct"),
    _model("qwen/qwen2.5-coder-32b-instruct"),
    _model("qwen/qwq-32b"),
    # Phi family
    _model("microsoft/phi-4-mini-flash-reasoning"),
    _model("microsoft/phi-4-multimodal-instruct"),
    _model("microsoft/phi-3.5-mini-instruct"),
    _model("microsoft/phi-3-medium-128k-instruct"),
    _model("microsoft/phi-3-mini-128k-instruct"),
    # Nemotron / Nvidia
    _model("nvidia/nemotron-mini-4b-instruct"),
    # Granite
    _model("ibm/granite-3.1-8b-instruct"),
    _model("ibm/granite-3.1-2b-instruct"),
    # Others
    _model("writer/palmyra-fin-70b-32k"),
    _model("upstage/solar-10.7b-instruct"),
    _model("ai21labs/jamba-1.5-mini-instruct"),
    _model("snowflake/arctic"),
    _model("01-ai/yi-large"),
    _model("thudm/chatglm3-6b"),
    _model("internlm/internlm2_5-7b-chat"),
    _model("athene/athene-v2-agent"),
    _model("nvidia/nv-mistralai-mistral-nemo-12b-instruct"),
    _model("nvidia/usdcode-llama3.1-70b-instruct"),
]

MODELS_BY_ID: dict[str, ModelConfig] = {m.id: m for m in MODELS}
THINKING_MODELS: list[ModelConfig] = [m for m in MODELS if m.is_thinking]
CHAT_MODELS: list[ModelConfig] = [m for m in MODELS if not m.is_thinking]

<div align="center">

# Open Layer

[![License: Apache 2.0](https://img.shields.io/badge/License-Apache%202.0-blue.svg)](LICENSE)
[![Spec Version](https://img.shields.io/badge/spec-v0.1--draft-orange.svg)](spec/)

**A universal open standard for LLM inference I/O — standardizing how applications talk to language models.**

[Why Open Layer?](#why) | [The Spec](#the-specification) | [Conformance Tests](#conformance-tests) | [SDK](#reference-sdk) | [Roadmap](#roadmap)

</div>

---

## Why?

MCP standardized how models talk to **tools**. Nothing standardizes how apps talk to **models**.

Every open model provider claims "OpenAI-compatible" — but only for the basics. The moment you use thinking tokens, streaming, tool calling, or caching, everything diverges:

| Feature | Provider A | Provider B | Provider C |
|---------|-----------|-----------|-----------|
| Thinking tokens | `reasoning_content` | `thinking_blocks` | `thinkingConfig` |
| Streaming deltas | `choices[0].delta` | `content_block_delta` | `candidates[0].content` |
| Cache reporting | `usage.cache_hit_tokens` | not reported | `cachedContentTokenCount` |
| Tool schemas | OpenAI-style | similar but different | `functionDeclarations` |

**Open Layer** is a spec — not a proxy, not a library — that defines the canonical request/response contract for LLM inference. Providers conform natively. Apps code to it once.

```
Without Open Layer:  [App] -> [LiteLLM/OpenRouter translates] -> [Provider]
With Open Layer:     [App] -> [Provider speaks the spec natively]
```

## The Specification

The spec defines a standard contract for:

| Section | What It Standardizes |
|---------|---------------------|
| **Messages** | Roles, content format, multi-turn structure |
| **Thinking** | Budget control, visibility, response format for reasoning tokens |
| **Streaming** | SSE event types, delta shapes, chunk boundaries |
| **Usage Reporting** | `{prompt_tokens, completion_tokens, reasoning_tokens, cached_tokens}` |
| **Model Capabilities** | `GET /v1/capabilities` endpoint |
| **Errors** | Standard error types, retry semantics, rate limit headers |

**Spec format:** Markdown prose + JSON Schema definitions, versioned in git.

See [`spec/v0.1/`](spec/v0.1/) for the full specification.

## Conformance Tests

A model-agnostic test harness that validates any OpenAI-compatible endpoint against the spec. Currently tests 30 models on Nvidia NIM across 10 model families.

```bash
cd tests && source ../.venv/bin/activate

# Default: smoke subset (5 diverse models)
python -m pytest suite/ -v

# Single model
python -m pytest suite/ -v --model llama-3.3-70b

# Thinking models only
python -m pytest suite/ -v --tag thinking

# All 30 models
python -m pytest suite/ -v --all
```

### Conformance Results (2026-03-05)

Tested 12 models across 10 families on Nvidia NIM:

| Model | Family | L1 Core | L2 Thinking | Non-conformances |
|-------|--------|---------|-------------|------------------|
| llama-3.3-70b-instruct | Llama | PASS | N/A | - |
| gemma-3-27b-it | Gemma | PASS | N/A | - |
| mistral-small-3.1-24b | Mistral | PASS | N/A | - |
| deepseek-r1-distill-qwen-14b | DeepSeek | PASS | partial | rejects unknown fields, usage chunk has choices |
| phi-4-mini-flash-reasoning | Phi | partial | partial | finish_reason=length on short prompts |
| nemotron-ultra-253b-v1 | Nemotron | partial | N/A | content=null on max_tokens |
| nemotron-mini-4b-instruct | Nemotron | partial | N/A | rejects unknown fields, usage chunk has choices |
| qwen2.5-coder-32b | Qwen | partial | N/A | rejects unknown fields, usage chunk has choices |
| deepseek-r1-distill-llama-8b | DeepSeek | partial | partial | rejects unknown fields, usage chunk has choices |
| solar-10.7b-instruct | Solar | partial | N/A | usage chunk has choices |
| jamba-1.5-mini-instruct | Jamba | PASS | N/A | - |
| chatglm3-6b | GLM | PASS | N/A | - |

**Key findings:**
- `test_unknown_fields_accepted` — 4/12 models reject unknown request fields (API gateway behavior)
- `test_usage_chunk_has_empty_choices` — 5/12 models include non-empty choices in usage chunk
- Thinking models use `<think>` tags in content instead of `message.thinking.content`
- Nvidia returns plain text (not JSON) for invalid model errors

**Conformance levels:**
- **Level 1: Core** — Messages, streaming, usage reporting, errors
- **Level 2: Thinking** — Level 1 + reasoning/thinking token support
- **Level 3: Agentic** — Level 2 + tool calling, structured output, caching (v0.2)

## Reference SDK

Python SDK with typed dataclasses and provider adapters.

```python
import asyncio
from open_layer import OpenLayerClient, ChatCompletionRequest, Message
from adapters.nvidia import NvidiaAdapter

async def main():
    async with OpenLayerClient(
        base_url="https://integrate.api.nvidia.com/v1",
        api_key="...",
        adapter=NvidiaAdapter(),
    ) as client:
        # Non-streaming
        response = await client.chat(ChatCompletionRequest(
            model="meta/llama-3.3-70b-instruct",
            messages=[Message(role="user", content="Explain quantum computing")],
            max_tokens=100,
        ))
        print(response.choices[0].message.content)

        # Streaming
        request = ChatCompletionRequest(
            model="meta/llama-3.3-70b-instruct",
            messages=[Message(role="user", content="Say hi")],
            max_tokens=10,
            stream=True,
        )
        async for chunk in client.stream(request):
            for choice in chunk.choices:
                if choice.delta.content:
                    print(choice.delta.content, end="")

asyncio.run(main())
```

### Adapters

Adapters translate between provider-native APIs and the Open Layer spec:

| Adapter | Provider | Thinking Translation | Usage Normalization |
|---------|----------|---------------------|-------------------|
| `NvidiaAdapter` | Nvidia NIM | `<think>` tags -> `message.thinking` | top-level `reasoning_tokens` -> `completion_tokens_details` |
| `DeepSeekAdapter` | DeepSeek | `reasoning_content` -> `message.thinking` | passthrough |
| `GroqAdapter` | Groq | `reasoning` -> `message.thinking` | `budget_tokens` -> `reasoning_effort` |

## Project Structure

```
open-layer/
├── spec/v0.1/              # The specification (Markdown + JSON Schema)
├── tests/                   # Conformance test suite
│   ├── suite/               #   Test cases (66 tests per model)
│   ├── models.py            #   30-model registry with tag system
│   ├── results/             #   Saved conformance test outputs
│   └── runner/              #   CLI test runner
├── sdks/python/             # Python SDK (open_layer)
│   └── open_layer/          #   Client, types, adapter protocol
├── adapters/                # Provider-specific adapters
│   ├── nvidia/              #   Nvidia NIM
│   ├── deepseek/            #   DeepSeek
│   └── groq/                #   Groq
├── scripts/                 # Validation and utility scripts
└── docs/                    # Provider fragmentation research
```

## Roadmap

- [x] **v0.1 Spec** — Messages, thinking tokens, streaming, usage reporting, errors, capabilities
- [x] **Conformance tests** — 66 tests, 30 models, 10 families, CLI runner with --model/--tag/--all
- [x] **Python SDK** — Async client with typed dataclasses and adapter protocol
- [x] **Adapters** — Nvidia, DeepSeek, Groq
- [ ] **v0.2** — Tool calling, structured output, caching
- [ ] **TypeScript SDK** — `@open-layer/sdk` (npm)
- [ ] **v0.3** — Multimodal input, governance model

## How It Differs

| | Open Layer | LiteLLM | OpenRouter | OpenAI Compat |
|---|---|---|---|---|
| **Type** | Spec (document) | Library (code) | Service (cloud) | Informal convention |
| **Translation** | None — providers conform | Runtime proxy | Cloud proxy | Each provider interprets |
| **Thinking tokens** | First-class standard | Runtime normalization | Runtime normalization | Not covered |
| **Lock-in** | None | LiteLLM abstractions | OpenRouter routing | OpenAI's changelog |

## License

[Apache License 2.0](LICENSE)

## Author

**Adityo Nugroho** ([@adityonugrohoid](https://github.com/adityonugrohoid))

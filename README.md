<div align="center">

# Open Layer

[![License: Apache 2.0](https://img.shields.io/badge/License-Apache%202.0-blue.svg)](LICENSE)
[![Spec Version](https://img.shields.io/badge/spec-v0.1--PoC-orange.svg)](spec/)
[![Status](https://img.shields.io/badge/status-v0.1%20PoC%20complete-green.svg)]()

**A proof-of-concept specification for standardizing LLM inference I/O across providers.**

[Motivation](#motivation) | [What Was Explored](#what-was-explored) | [Key Findings](#key-findings) | [A/B Demo](#ab-demo) | [SDK](#reference-sdk)

</div>

---

## Motivation

Every open model provider claims "OpenAI-compatible" APIs, but conformance breaks down beyond basic chat completions. This project explored what a formal standard would look like by:

1. **Writing a spec** — defining the canonical request/response contract for messages, thinking tokens, streaming, usage reporting, errors, and capabilities
2. **Testing it** — running conformance tests against 12 models across 10 families on Nvidia NIM
3. **Building adapters** — normalizing non-conformant responses to prove the spec works in practice

### The Fragmentation Problem

| Feature | Nvidia NIM | DeepSeek | Groq |
|---------|-----------|----------|------|
| Thinking tokens | `<think>` tags in content | `reasoning_content` field | `reasoning` field |
| Null usage fields | `prompt_tokens_details: null` | omitted | omitted |
| Non-spec fields | 8+ per response (`logprobs`, `stop_reason`, `service_tier`...) | 2-3 | 1-2 |

## What Was Explored

### Specification (`spec/v0.1/`)

Markdown prose + JSON Schema definitions covering 6 areas:

| Section | What It Standardizes |
|---------|---------------------|
| **Messages** | Roles, content format, multi-turn structure |
| **Thinking** | Budget control, visibility, response format for reasoning tokens |
| **Streaming** | SSE event types, delta shapes, chunk boundaries |
| **Usage** | `{prompt_tokens, completion_tokens, reasoning_tokens, cached_tokens}` |
| **Capabilities** | `GET /v1/capabilities` endpoint |
| **Errors** | Standard error types, retry semantics, rate limit headers |

### Conformance Tests (`tests/`)

66 tests per model, 30-model registry with tag-based parameterization:

```bash
cd tests && source ../.venv/bin/activate
python -m pytest suite/ -v              # smoke (5 models)
python -m pytest suite/ -v --tag thinking  # thinking models only
python -m pytest suite/ -v --all        # all 30 models
```

### Provider Adapters (`adapters/`)

| Adapter | Thinking Translation | Usage Normalization |
|---------|---------------------|-------------------|
| `NvidiaAdapter` | `<think>` tags + `reasoning_content` -> `message.thinking` | null cleanup, `reasoning_tokens` relocation |
| `DeepSeekAdapter` | `reasoning_content` -> `message.thinking` | passthrough |
| `GroqAdapter` | `reasoning` -> `message.thinking` | `budget_tokens` -> `reasoning_effort` |

### A/B Demo (`scripts/`, `docs/`)

Visual proof of what adapters fix — HTML report with side-by-side raw vs normalized JSON, diff-highlighted per model.

```bash
# Terminal demo (single model)
python scripts/ab_demo.py

# Full HTML report (all 12 models)
python scripts/ab_report.py
# Then open docs/ab-report.html
```

## Key Findings

Tested 12 models across 10 families on Nvidia NIM (2026-03-05):

| Finding | Impact |
|---------|--------|
| 4/12 models reject unknown request fields | API gateway behavior, not model-level |
| 5/12 models include non-empty choices in streaming usage chunk | Breaks clients expecting empty choices on usage-only chunks |
| Thinking models use 3 different patterns for reasoning output | No interoperability without adapters |
| Nvidia returns plain text (not JSON) for invalid model errors | Breaks typed error handling |
| **12/12 models PASS after adapter normalization** | Adapters work as a bridge |

### Conformance Results

| Model | Core | Thinking | Notes |
|-------|------|----------|-------|
| llama-3.3-70b-instruct | PASS | N/A | - |
| gemma-3-27b-it | PASS | N/A | - |
| mistral-small-3.1-24b | PASS | N/A | - |
| deepseek-r1-distill-qwen-14b | PASS | PASS | `<think>` tags extracted |
| phi-4-mini-flash-reasoning | PASS | PASS | `<think>` tags extracted |
| nemotron-ultra-253b-v1 | PASS | PASS | `reasoning_content` extracted |
| nemotron-mini-4b-instruct | PASS | N/A | - |
| qwen2.5-coder-32b | PASS | N/A | - |
| deepseek-r1-distill-llama-8b | PASS | PASS | `<think>` tags extracted |
| solar-10.7b-instruct | PASS | N/A | - |
| jamba-1.5-mini-instruct | PASS | N/A | - |
| chatglm3-6b | PASS | N/A | - |

## Reference SDK

```python
from open_layer import OpenLayerClient, ChatCompletionRequest, Message
from adapters.nvidia import NvidiaAdapter

async with OpenLayerClient(
    base_url="https://integrate.api.nvidia.com/v1",
    api_key="...",
    adapter=NvidiaAdapter(),
) as client:
    response = await client.chat(ChatCompletionRequest(
        model="deepseek-ai/deepseek-r1-distill-llama-8b",
        messages=[Message(role="user", content="Explain quantum computing")],
    ))
    # Thinking extracted into message.thinking.content
    # Content is clean answer only
    print(response.choices[0].message.content)
    print(response.choices[0].message.thinking.content)
```

## Project Structure

```
open-layer/
├── spec/v0.1/              # Specification (Markdown + JSON Schema)
├── tests/                   # Conformance test suite (66 tests/model)
│   ├── suite/               #   Test cases
│   ├── models.py            #   30-model registry
│   └── results/             #   Saved outputs
├── sdks/python/open_layer/  # Python SDK (async client, typed dataclasses)
├── adapters/                # Provider adapters (Nvidia, DeepSeek, Groq)
├── scripts/
│   ├── ab_demo.py           #   Terminal A/B demo (rich)
│   ├── ab_report.py         #   HTML report generator
│   └── validate_sdk.py      #   SDK validation across 12 models
└── docs/
    ├── ab-report.html       #   Generated conformance report
    └── provider-fragmentation.md
```

## Status

**v0.1 PoC — Complete.** This project explored LLM API standardization as a proof of concept. The spec, conformance tests, SDK, and adapters demonstrate the problem space and validate that normalization is feasible.

Not actively developed beyond v0.1. The conformance report and adapter patterns serve as reference material for understanding provider fragmentation in the LLM API ecosystem.

## License

[Apache License 2.0](LICENSE)

## Author

**Adityo Nugroho** ([@adityonugrohoid](https://github.com/adityonugrohoid))
</div>

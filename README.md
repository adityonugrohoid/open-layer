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
Without Open Layer:  [App] → [LiteLLM/OpenRouter translates] → [Provider]
With Open Layer:     [App] → [Provider speaks the spec natively]
```

## The Specification

The spec defines a standard contract for:

| Section | What It Standardizes |
|---------|---------------------|
| **Messages** | Roles, content blocks (text, image, audio), multi-turn format |
| **Thinking** | Budget control, visibility, response format for reasoning tokens |
| **Streaming** | SSE event types, delta shapes, chunk boundaries |
| **Tool Calling** | Tool schema, choice modes, parallel calls, result format |
| **Structured Output** | JSON Schema constraints, guaranteed parseable responses |
| **Caching** | Cache control hints, hit/miss reporting |
| **Usage Reporting** | `{input_tokens, output_tokens, thinking_tokens, cached_tokens}` |
| **Model Capabilities** | `{supports: ["thinking", "vision", "tools", ...]}` |
| **Errors** | Standard error codes, retry semantics, rate limit headers |

**Spec format:** Markdown prose + JSON Schema definitions, versioned in git.

See [`spec/`](spec/) for the full specification.

## Conformance Tests

A provider-agnostic test harness that validates any endpoint against the spec:

```bash
open-layer validate --provider https://api.example.com/v1 --key $API_KEY

# ✓ messages.basic         PASS
# ✓ thinking.budget        PASS
# ✗ thinking.streaming     FAIL — missing thinking.delta events
# ✓ tools.basic            PASS
# ✓ usage_reporting        PASS
#
# Score: 4/5 — Level 1 Conformant
```

**Conformance levels:**
- **Level 1: Core** — Messages, streaming, usage reporting, errors
- **Level 2: Thinking** — Level 1 + reasoning/thinking token support
- **Level 3: Agentic** — Level 2 + tool calling, structured output, caching

## Reference SDK

Thin client that speaks the spec. No translation magic, no fallback routing.

```python
from open_layer import Client

client = Client(base_url="https://api.provider.com/v1", api_key="...")

response = client.chat.create(
    model="llama-3.3-70b",
    messages=[{"role": "user", "content": "Explain quantum computing"}],
    thinking={"budget_tokens": 4096, "visible": True},
)

print(response.content)               # main response
print(response.thinking_blocks)       # reasoning trace
print(response.usage.thinking_tokens) # standard field
```

## Target Providers

Open Layer targets open model providers first:

- **Groq** — Llama, Qwen, Kimi K2 (fastest inference)
- **DeepSeek** — V3.2, R1 (best price-performance)
- **Alibaba Qwen** — Qwen3.5-Plus, Qwen-Turbo (most aggressive pricing)
- **Mistral** — Small, Nemo (1B free tokens/month)
- **Cerebras** — Llama (speed-competitive)
- **Together.ai** — Llama 4 Scout, DeepSeek
- **Cloudflare Workers AI** — Edge deployment

Frontier models (OpenAI, Anthropic) are welcome but not required. The open ecosystem defines the standard.

## Project Structure

```
open-layer/
├── spec/                    # The specification (Markdown + JSON Schema)
│   └── v0.1/
├── tests/                   # Conformance test suite
│   ├── suite/               #   Test cases
│   └── runner/              #   CLI test runner
├── sdks/
│   ├── python/              #   open-layer (PyPI)
│   └── typescript/          #   @open-layer/sdk (npm)
├── adapters/                # Temporary shims for existing providers
│   ├── groq/
│   ├── deepseek/
│   └── alibaba-qwen/
└── docs/                    # Guides and comparisons
```

## Roadmap

- [ ] **v0.1** — Messages, thinking tokens, streaming, usage reporting spec
- [ ] Conformance test suite (CLI runner)
- [ ] Python reference SDK
- [ ] Adapters for Groq, DeepSeek, Alibaba Qwen
- [ ] **v0.2** — Tool calling, structured output, caching, TypeScript SDK
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

# Open Layer

## Overview
Open Layer is a universal open standard (specification) for LLM inference I/O — standardizing how applications communicate with language model providers. It's the model I/O counterpart to MCP (which standardizes tool access).

## Tech Stack
- **Spec:** Markdown + JSON Schema draft-2020-12 (versioned in git)
- **Conformance tests:** Python (pytest)
- **Reference SDK:** Python (PyPI: `open-layer`)
- **Adapters:** Python (FastAPI/Starlette thin proxy)
- **Docs site:** MkDocs or Docusaurus (GitHub Pages)
- **CI:** GitHub Actions

## Architecture
```
[Application] → Open Layer SDK → [Conformant Provider API]
                                   ├── Groq
                                   ├── DeepSeek
                                   ├── Alibaba Qwen
                                   ├── Mistral
                                   └── Cerebras
```
No central proxy. The spec IS the interop layer. Providers conform natively.
Adapters exist as temporary bootstrap shims until native adoption.

## Project Structure
```
open-layer/
├── spec/v0.1/          # The specification (Markdown + JSON Schema)
│   ├── messages.md     # Core request/response, roles, finish reasons
│   ├── thinking.md     # Thinking tokens: enable, budget, response, multi-turn
│   ├── streaming.md    # SSE format, delta shapes, phase sequencing
│   ├── usage.md        # Token counting, reasoning breakdown, cache reporting
│   ├── capabilities.md # GET /v1/capabilities discovery endpoint
│   ├── errors.md       # Error types, HTTP codes, rate limits, stream errors
│   └── schema/         # 8 JSON Schema files (draft-2020-12)
├── tests/              # Conformance test suite
├── sdks/python/        # Reference SDK
├── adapters/           # Provider adapter shims
│   ├── groq/
│   ├── deepseek/
│   └── alibaba-qwen/
└── docs/
    └── provider-fragmentation.md  # Provider research (source of truth)
```

## v0.1 Status
- [x] Spec: all 6 sections + 8 JSON schemas (Draft)
- [ ] Conformance test suite (pytest CLI runner)
- [ ] Python reference SDK
- [ ] Adapters: Groq, DeepSeek, Alibaba Qwen

## Key Spec Decisions
- **Thinking request:** `thinking.enabled` (bool) + `thinking.budget_tokens` (int, optional)
- **Thinking response:** `message.thinking.content` (always a string, never array)
- **Streaming thinking:** `delta.thinking.content` — phases MUST NOT overlap
- **Usage:** `completion_tokens_details.reasoning_tokens` + `prompt_tokens_details.cached_tokens`
- **Capabilities:** `GET /v1/capabilities` — new endpoint, synthesized by adapters
- **Errors:** 7 standard types, `retry-after` REQUIRED on 429
- **Conformance levels:** L1 Core, L2 Thinking, L3 Agentic (deferred to v0.2)
- **Versioning:** `0.1-draft` for now, date-based (YYYY-MM-DD) at 1.0

## Provider Mapping (quick ref)
| Feature | Groq | DeepSeek | Qwen | Mistral |
|---------|------|----------|------|---------|
| Thinking field | `reasoning` | `reasoning_content` | `reasoning_content` | typed content blocks |
| Budget param | `reasoning_effort` | N/A (max_tokens) | `thinking_budget` | N/A |
| Cache reporting | — | `prompt_cache_hit_tokens` (top-level) | `prompt_tokens_details.cached_tokens` | — |
| Reasoning usage | — | `completion_tokens_details.reasoning_tokens` | `completion_tokens_details.reasoning_tokens` | — |
| Input thinking | OK | MUST strip (400 error) | OK | OK |

## Key Patterns
- Spec-first development: spec → tests → SDK → adapters
- Adapters are temporary — goal is native provider adoption
- JSON Schema for request/response validation
- Provider-specific fields allowed with `x-` prefix
- RFC 2119 language in spec (MUST/SHOULD/MAY)

## Commands
```bash
# All commands run from ~/projects/open-layer/

# Run conformance tests (once implemented)
cd tests && python -m pytest suite/ -v

# Validate a provider
python -m open_layer validate --provider <url> --key <key>

# Validate JSON schemas
python3 -c "import json, glob; [print(f'OK: {f}') for f in sorted(glob.glob('spec/v0.1/schema/*.json')) if json.load(open(f))]"
```

## Important Notes
- This is a SPEC project, not a service or library
- Target open model providers first (Groq, DeepSeek, Alibaba, Mistral)
- Frontier models (OpenAI, Anthropic) welcome but not required
- Apache 2.0 licensed
- Concept doc: ~/projects/brainstorming/concepts/open-layer.md
- Provider research: docs/provider-fragmentation.md (single source of truth for mappings)

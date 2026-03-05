# Open Layer

## Overview
Open Layer is a universal open standard (specification) for LLM inference I/O — standardizing how applications communicate with language model providers. It's the model I/O counterpart to MCP (which standardizes tool access).

## Tech Stack
- **Spec:** Markdown + JSON Schema draft-2020-12 (versioned in git)
- **Conformance tests:** Python (pytest, pytest-asyncio, httpx)
- **Reference SDK:** Python async (httpx, dataclasses)
- **Adapters:** Python (Nvidia, DeepSeek, Groq)

## Project Structure
```
open-layer/
├── spec/v0.1/              # Specification (6 sections + 8 JSON schemas)
├── tests/                   # Conformance test suite
│   ├── models.py            #   30-model registry (ModelConfig dataclass)
│   ├── conftest.py          #   CLI: --model/--tag/--all parameterization
│   ├── suite/               #   66 tests per model (6 test files)
│   │   ├── helpers/
│   │   │   ├── throttle.py  #   35 RPM asyncio.Lock throttle
│   │   │   ├── schema.py    #   JSON Schema validator
│   │   │   └── sse.py       #   SSE stream parser
│   │   └── test_*.py        #   messages, streaming, usage, thinking, capabilities, errors
│   ├── results/             #   Saved conformance outputs
│   └── runner/cli.py        #   pytest wrapper
├── sdks/python/open_layer/  # Python SDK
│   ├── client.py            #   Async client (chat + stream)
│   ├── types.py             #   Typed dataclasses for all spec types
│   └── adapter.py           #   Adapter protocol
├── adapters/                # Provider adapters
│   ├── nvidia/              #   <think> tag extraction, usage normalization
│   ├── deepseek/            #   reasoning_content mapping, input stripping
│   └── groq/                #   reasoning field mapping, budget→effort
├── scripts/
│   ├── ab_demo.py            #   A/B demo: raw API vs adapter-normalized output
│   └── validate_sdk.py      #   SDK+adapter validation against 12 models
└── docs/
    └── provider-fragmentation.md
```

## v0.1 Status — PoC COMPLETE
- [x] Spec: 6 sections + 8 JSON schemas (Draft)
- [x] Conformance tests: 66 tests/model, 30-model registry, CLI filters
- [x] Python SDK: async client, typed dataclasses, adapter protocol
- [x] Adapters: Nvidia, DeepSeek, Groq
- [x] Conformance results: 12 models, 10 families tested

## Commands
```bash
# All commands from ~/projects/open-layer/
source .venv/bin/activate

# Conformance tests
cd tests && python -m pytest suite/ -v                    # smoke (5 models)
cd tests && python -m pytest suite/ -v --model llama-3.3  # single model
cd tests && python -m pytest suite/ -v --tag thinking     # thinking models
cd tests && python -m pytest suite/ -v --all              # all 30 models

# SDK validation
python scripts/validate_sdk.py

# A/B demo (raw vs adapter-normalized)
python scripts/ab_demo.py

# Validate JSON schemas
python3 -c "import json, glob; [print(f'OK: {f}') for f in sorted(glob.glob('spec/v0.1/schema/*.json')) if json.load(open(f))]"
```

## Key Conformance Findings
- 4/12 models reject unknown fields (Nvidia gateway, not model-level)
- 5/12 models include non-empty choices in streaming usage chunk
- Thinking models use `<think>` tags, not `message.thinking.content`
- Nvidia returns plain text (not JSON) for invalid model errors
- SDK+adapter: 12/12 models PASS after adapter normalization

## Key Patterns
- Spec-first: spec → tests → SDK → adapters
- Adapters are temporary — goal is native provider adoption
- 35 RPM throttle for Nvidia free tier (asyncio.Lock in throttle.py)
- xfail for known provider deviations (tests stay spec-correct)
- ModelConfig with tag-based parameterization (not provider-based)

## A/B Demo
- `scripts/ab_demo.py` — rich-powered side-by-side comparison of raw Nvidia API vs adapter-normalized output
- Shows: thinking extraction (<think> tags → message.thinking.content), usage normalization, non-spec field detection
- Tries deepseek-r1-distill-qwen-14b first, falls back to deepseek-r1-distill-llama-8b
- Run: `python scripts/ab_demo.py`

# Open Layer

## Overview
Open Layer is a universal open standard (specification) for LLM inference I/O — standardizing how applications communicate with language model providers. It's the model I/O counterpart to MCP (which standardizes tool access).

## Tech Stack
- **Spec:** Markdown + JSON Schema (versioned in git)
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
├── tests/              # Conformance test suite
├── sdks/python/        # Reference SDK
├── adapters/           # Provider adapter shims
└── docs/               # Guides and comparisons
```

## Key Patterns
- Spec-first development: write the spec, then implement tests, then SDK
- Conformance levels: Level 1 (Core), Level 2 (Thinking), Level 3 (Agentic)
- Adapters are temporary — goal is native provider adoption
- JSON Schema for request/response validation

## Commands
```bash
# Run conformance tests (once implemented)
cd tests && python -m pytest suite/ -v

# Validate a provider
python -m open_layer validate --provider <url> --key <key>
```

## Important Notes
- This is a SPEC project, not a service or library
- Target open model providers first (Groq, DeepSeek, Alibaba, Mistral)
- Frontier models (OpenAI, Anthropic) welcome but not required
- Apache 2.0 licensed
- Concept doc: ~/projects/brainstorming/concepts/open-layer.md

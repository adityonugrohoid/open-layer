# Open Layer — Roadmap

## v0.1 — Foundation (Complete)
**Goal:** Ship the core spec + conformance suite, validate against real providers.

- [x] Messages spec (text-only)
- [x] Thinking/reasoning token spec
- [x] Streaming spec (SSE event format)
- [x] Usage reporting spec (input/output/thinking/cached tokens)
- [x] Model capabilities declaration spec
- [x] Error contract spec
- [x] Conformance test suite (66 tests/model, 30-model registry, CLI runner)
- [x] Python reference SDK (async client, typed dataclasses, adapter protocol)
- [x] Adapters: Nvidia (3 thinking patterns), DeepSeek, Groq
- [x] A/B conformance report (HTML, 12 models tested)

**Outcome:** Proved that provider APIs diverge significantly beyond basic chat, and that adapter-based normalization is feasible. 12/12 models PASS through adapters.

---

*v0.1 PoC is the final delivered version. The areas below remain as reference for what a full standard would require.*

## v0.2 — Agentic (Not started)
- Tool calling spec
- Structured output spec
- Cache control hints spec
- TypeScript SDK
- Additional adapters (Mistral, Cerebras, Together.ai)

## v0.3 — Multimodal (Not started)
- Multimodal input/output spec
- Embedding spec
- Provider conformance dashboard

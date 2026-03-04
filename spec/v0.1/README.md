# Open Layer Specification v0.1 (Draft)

> **Status:** Draft — not yet stable. Breaking changes expected.

This directory contains the Open Layer v0.1 specification.

## Sections

| Section | File | Status |
|---------|------|--------|
| Messages | [`messages.md`](messages.md) | Draft |
| Thinking/Reasoning | [`thinking.md`](thinking.md) | Draft |
| Streaming | [`streaming.md`](streaming.md) | Draft |
| Usage Reporting | [`usage.md`](usage.md) | Draft |
| Model Capabilities | [`capabilities.md`](capabilities.md) | Draft |
| Error Contract | [`errors.md`](errors.md) | Draft |
| JSON Schemas | [`schema/`](schema/) | Draft |

## Design Principles

1. **Spec, not implementation** — Define the contract, not how to build it
2. **Open models first** — Target providers who benefit from interoperability
3. **Conformance levels** — Allow incremental adoption (Core → Thinking → Agentic)
4. **Extension-friendly** — Allow `x-` prefixed fields for provider-specific features
5. **JSON Schema validated** — Every request/response shape has a machine-readable schema

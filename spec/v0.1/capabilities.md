# Model Capabilities

> **Status:** Draft
> **Conformance Level:** Level 1 (Core)
> **Schema:** [`schema/capabilities.json`](schema/capabilities.json)

## Overview

This section defines the capabilities discovery endpoint. Clients use this endpoint to determine which Open Layer features a provider supports, what conformance level it claims, and which models are available with their per-model feature overrides.

The key words "MUST", "MUST NOT", "REQUIRED", "SHALL", "SHALL NOT", "SHOULD", "SHOULD NOT", "RECOMMENDED", "MAY", and "OPTIONAL" in this document are to be interpreted as described in [RFC 2119](https://www.rfc-editor.org/rfc/rfc2119).

## Request Format

### Endpoint

```
GET /v1/capabilities
```

No request body. Authentication MUST use the same mechanism as chat completions (typically `Authorization: Bearer <api-key>`).

## Response Format

### Response Body

```json
{
  "spec_version": "0.1-draft",
  "conformance_level": 2,
  "features": {
    "thinking": {
      "supported": true,
      "budget_control": true
    },
    "streaming": {
      "supported": true,
      "usage_in_stream": true
    }
  },
  "models": [
    {
      "id": "deepseek-reasoner",
      "features": {
        "thinking": {
          "supported": true,
          "budget_control": false
        }
      }
    },
    {
      "id": "deepseek-chat",
      "features": {
        "thinking": {
          "supported": false
        }
      }
    }
  ]
}
```

### Field Reference

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `spec_version` | string | REQUIRED | The Open Layer spec version. Format: `"0.1-draft"` for pre-1.0, `"YYYY-MM-DD"` at 1.0+. |
| `conformance_level` | integer | REQUIRED | The highest conformance level this provider supports. `1` = Core, `2` = Thinking, `3` = Agentic (v0.2). |
| `features` | object | REQUIRED | Provider-wide feature support. See [Features Object](#features-object). |
| `models` | array of [Model](#model-object) | OPTIONAL | List of available models with per-model feature overrides. |

### Features Object

The features object reports provider-wide defaults. Per-model overrides in the `models` array take precedence.

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `features.thinking` | object | OPTIONAL | Thinking feature support. |
| `features.thinking.supported` | boolean | REQUIRED (if present) | Whether the provider supports thinking tokens. |
| `features.thinking.budget_control` | boolean | OPTIONAL | Whether `budget_tokens` is respected. Default: `false`. |
| `features.streaming` | object | OPTIONAL | Streaming feature support. |
| `features.streaming.supported` | boolean | REQUIRED (if present) | Whether the provider supports streaming. |
| `features.streaming.usage_in_stream` | boolean | OPTIONAL | Whether `stream_options.include_usage` is supported. Default: `false`. |

### Model Object

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `id` | string | REQUIRED | Model identifier (same value used in `model` request field). |
| `features` | object | OPTIONAL | Per-model feature overrides. Same structure as the top-level `features` object. |

Per-model features override provider-wide features. If a feature is not listed in the model's `features`, the provider-wide default applies.

## Conformance Requirements

### Level 1 (Core) — RECOMMENDED

1. Providers SHOULD implement `GET /v1/capabilities`.
2. If implemented, the response MUST include `spec_version`, `conformance_level`, and `features`.
3. `spec_version` MUST be a valid Open Layer version string.
4. `conformance_level` MUST be an integer ≥ 1.
5. The `models` array is OPTIONAL but RECOMMENDED for providers with heterogeneous model capabilities.

### Notes on Adoption

The capabilities endpoint is RECOMMENDED, not REQUIRED, at Level 1. Providers that do not implement it SHOULD document their supported features out-of-band. Clients SHOULD gracefully handle a 404 response and fall back to manual configuration.

## Provider Mapping

No provider currently implements a `/v1/capabilities` endpoint. This is a new endpoint introduced by Open Layer. Adapters MUST synthesize this response based on known provider capabilities.

### Synthesized Capabilities

| Provider | `conformance_level` | `thinking.supported` | `thinking.budget_control` | `streaming.supported` | `streaming.usage_in_stream` |
|----------|--------------------|-----------------------|--------------------------|----------------------|----------------------------|
| Groq | 2 | `true` (select models) | `true` (via `reasoning_effort`) | `true` | `true` |
| DeepSeek | 2 | `true` (deepseek-reasoner) | `false` | `true` | `true` |
| Nvidia | 2 | `true` (R1-distill, DeepSeek V3.x, QwQ, Nemotron reasoning models) | `false` | `true` | `true` |
| Mistral | 2 | `true` (Magistral models) | `false` | `true` | `true` (automatic) |

### Per-Model Overrides

Adapters SHOULD populate the `models` array. Example for Nvidia:

```json
{
  "models": [
    {
      "id": "deepseek-ai/deepseek-r1-distill-qwen-14b",
      "features": {
        "thinking": {"supported": true, "budget_control": false}
      }
    },
    {
      "id": "meta/llama-3.3-70b-instruct",
      "features": {
        "thinking": {"supported": false}
      }
    }
  ]
}
```

## Examples

### Example 1: Level 2 provider with thinking

```json
{
  "spec_version": "0.1-draft",
  "conformance_level": 2,
  "features": {
    "thinking": {
      "supported": true,
      "budget_control": true
    },
    "streaming": {
      "supported": true,
      "usage_in_stream": true
    }
  },
  "models": [
    {
      "id": "deepseek-ai/deepseek-v3.1",
      "features": {
        "thinking": {"supported": true, "budget_control": false}
      }
    },
    {
      "id": "meta/llama-3.3-70b-instruct",
      "features": {
        "thinking": {"supported": false}
      }
    }
  ]
}
```

### Example 2: Level 1 provider (no thinking)

```json
{
  "spec_version": "0.1-draft",
  "conformance_level": 1,
  "features": {
    "streaming": {
      "supported": true,
      "usage_in_stream": true
    }
  }
}
```

### Example 3: Client handling 404

When a provider does not implement the capabilities endpoint:

```
GET /v1/capabilities HTTP/1.1
Authorization: Bearer sk-...

HTTP/1.1 404 Not Found
```

Clients SHOULD fall back to manual configuration and SHOULD NOT treat this as a fatal error.

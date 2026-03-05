# Usage Reporting

> **Status:** Draft
> **Conformance Level:** Level 1 (Core) for base fields, Level 2 (Thinking) for reasoning breakdown
> **Schema:** [`schema/usage.json`](schema/usage.json)

## Overview

This section defines how providers report token usage. Open Layer standardizes the three base fields all providers already support, plus optional detailed breakdowns for reasoning tokens and cache hits.

The key words "MUST", "MUST NOT", "REQUIRED", "SHALL", "SHALL NOT", "SHOULD", "SHOULD NOT", "RECOMMENDED", "MAY", and "OPTIONAL" in this document are to be interpreted as described in [RFC 2119](https://www.rfc-editor.org/rfc/rfc2119).

## Response Format

The `usage` object appears in every non-streaming response and in the final streaming chunk (when `stream_options.include_usage` is `true`).

### Canonical Shape

```json
{
  "usage": {
    "prompt_tokens": 50,
    "completion_tokens": 100,
    "total_tokens": 150,
    "prompt_tokens_details": {
      "cached_tokens": 0
    },
    "completion_tokens_details": {
      "reasoning_tokens": 38
    }
  }
}
```

### Field Reference

#### Base Fields (Level 1)

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `prompt_tokens` | integer | REQUIRED | Number of tokens in the prompt (input). |
| `completion_tokens` | integer | REQUIRED | Number of tokens in the completion (output). Includes reasoning tokens if thinking is enabled. |
| `total_tokens` | integer | REQUIRED | Sum of `prompt_tokens` and `completion_tokens`. |

#### Prompt Details (Level 1, OPTIONAL)

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `prompt_tokens_details` | object | OPTIONAL | Breakdown of prompt token usage. |
| `prompt_tokens_details.cached_tokens` | integer | OPTIONAL | Number of prompt tokens served from cache. |

#### Completion Details (Level 2)

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `completion_tokens_details` | object | CONDITIONAL | Breakdown of completion token usage. REQUIRED at Level 2 when thinking is enabled. |
| `completion_tokens_details.reasoning_tokens` | integer | CONDITIONAL | Number of tokens used for thinking/reasoning. REQUIRED at Level 2 when thinking is enabled. |

### Invariants

- `total_tokens` MUST equal `prompt_tokens + completion_tokens`.
- When thinking is enabled, `reasoning_tokens` MUST be less than or equal to `completion_tokens`.
- `cached_tokens` MUST be less than or equal to `prompt_tokens`.

## Conformance Requirements

### Level 1 (Core) — REQUIRED

1. Providers MUST include `usage` in every non-streaming response.
2. Providers MUST include `prompt_tokens`, `completion_tokens`, and `total_tokens`.
3. `total_tokens` MUST equal `prompt_tokens + completion_tokens`.
4. When streaming with `include_usage: true`, providers MUST include `usage` in the final chunk.
5. Providers SHOULD include `prompt_tokens_details.cached_tokens` when cache reporting is available.

### Level 2 (Thinking) — Additional requirements

6. When thinking is enabled, providers MUST include `completion_tokens_details.reasoning_tokens`.
7. `reasoning_tokens` MUST reflect the number of tokens consumed by thinking, not just the visible output.
8. Providers that do not support reasoning token breakdown MUST still include `completion_tokens_details.reasoning_tokens: 0` when thinking is enabled.

## Provider Mapping

### Base Fields

All four providers return the standard three fields with no translation needed:

| Standard | Groq | DeepSeek | Nvidia | Mistral |
|----------|------|----------|------|---------|
| `prompt_tokens` | ✅ | ✅ | ✅ | ✅ |
| `completion_tokens` | ✅ | ✅ | ✅ | ✅ |
| `total_tokens` | ✅ | ✅ | ✅ | ✅ |

### Reasoning Token Breakdown

| Standard | Groq | DeepSeek | Nvidia | Mistral |
|----------|------|----------|------|---------|
| `completion_tokens_details.reasoning_tokens` | Not reported (set to `0`) | `completion_tokens_details.reasoning_tokens` | `usage.reasoning_tokens` (top-level, not nested) | Not reported (set to `0`) |

### Cache Reporting

| Standard | Groq | DeepSeek | Nvidia | Mistral |
|----------|------|----------|------|---------|
| `prompt_tokens_details.cached_tokens` | Not reported | `prompt_cache_hit_tokens` (top-level) | `prompt_tokens_details` (null when no cache data) | Not reported |

### Adapter Notes

- **Groq:** Includes unique timing fields (`queue_time`, `prompt_time`, `completion_time`, `total_time`). Adapters SHOULD pass these through as provider-specific extensions but MUST NOT rely on them in the standard usage object. Reasoning tokens are reported only in the Responses API (`output_tokens_details.reasoning_tokens`), not in chat completions.
- **DeepSeek:** Reports cache at the top level (`prompt_cache_hit_tokens`, `prompt_cache_miss_tokens`) rather than nested in `prompt_tokens_details`. Adapters MUST map `prompt_cache_hit_tokens` → `prompt_tokens_details.cached_tokens`.
- **Nvidia:** Reports `reasoning_tokens` at the top level of the `usage` object (not nested in `completion_tokens_details`). Adapters MUST move this into `completion_tokens_details.reasoning_tokens`. `prompt_tokens_details` is returned as `null` when no cache data is available — adapters SHOULD omit it rather than passing `null`.
- **Mistral:** The simplest reporting — no reasoning breakdown, no cache reporting. Adapters MUST set `reasoning_tokens: 0` when thinking is enabled and omit `prompt_tokens_details` when cache data is not available.

### Provider Extension Fields

Providers MAY include additional fields beyond the standard ones. Adapters SHOULD preserve these as-is:

| Provider | Extra Fields | Type |
|----------|-------------|------|
| Groq | `queue_time`, `prompt_time`, `completion_time`, `total_time` | Timing (seconds) |
| DeepSeek | `prompt_cache_hit_tokens`, `prompt_cache_miss_tokens` | Token counts |
| Nvidia | `reasoning_tokens` (top-level), `metadata` | Token count, metadata object |

## Examples

### Example 1: Basic usage (Level 1)

```json
{
  "usage": {
    "prompt_tokens": 25,
    "completion_tokens": 42,
    "total_tokens": 67
  }
}
```

### Example 2: Usage with thinking (Level 2)

```json
{
  "usage": {
    "prompt_tokens": 18,
    "completion_tokens": 156,
    "total_tokens": 174,
    "completion_tokens_details": {
      "reasoning_tokens": 120
    }
  }
}
```

### Example 3: Usage with cache hit

```json
{
  "usage": {
    "prompt_tokens": 1024,
    "completion_tokens": 50,
    "total_tokens": 1074,
    "prompt_tokens_details": {
      "cached_tokens": 896
    }
  }
}
```

### Example 4: Full usage with thinking and cache

```json
{
  "usage": {
    "prompt_tokens": 2048,
    "completion_tokens": 300,
    "total_tokens": 2348,
    "prompt_tokens_details": {
      "cached_tokens": 1792
    },
    "completion_tokens_details": {
      "reasoning_tokens": 200
    }
  }
}
```

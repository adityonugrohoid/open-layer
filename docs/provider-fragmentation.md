# Provider API Fragmentation Research

**Last Updated:** 2026-03-05
**Sources:** Public API documentation (no API keys required)

This document maps the exact I/O divergence across open model providers. This is the evidence base for why Open Layer needs to exist.

---

## Providers Researched

| Provider | Docs URL | API Style |
|----------|----------|-----------|
| **Groq** | https://console.groq.com/docs | OpenAI-compatible (`/openai/v1/`) |
| **DeepSeek** | https://api-docs.deepseek.com/ | OpenAI-compatible (`/chat/completions`) |
| **Alibaba Qwen** | https://www.alibabacloud.com/help/en/model-studio/ | OpenAI-compatible (`/compatible-mode/v1/`) + DashScope native |
| **Mistral** | https://docs.mistral.ai/ | OpenAI-compatible (`/v1/chat/completions`) |

All claim "OpenAI-compatible." All diverge on modern features.

---

## 1. Thinking / Reasoning Tokens

The biggest area of fragmentation. Every provider handles this differently.

### How to Enable Thinking

| Provider | Method | Example |
|----------|--------|---------|
| **Groq** | `reasoning_format` param + `reasoning_effort` | `"reasoning_format": "parsed", "reasoning_effort": "high"` |
| **DeepSeek** | `thinking` object param OR model name | `"thinking": {"type": "enabled"}` or `model: "deepseek-reasoner"` |
| **Alibaba Qwen** | `enable_thinking` + `thinking_budget` (via `extra_body`) | `"enable_thinking": true, "thinking_budget": 5000` |
| **Mistral** | `prompt_mode` param + Magistral model family | `"prompt_mode": "reasoning"` with `model: "magistral-medium-latest"` |

### Budget / Effort Control

| Provider | Parameter | Values |
|----------|-----------|--------|
| **Groq** | `reasoning_effort` | `"none"`, `"default"`, `"low"`, `"medium"`, `"high"` |
| **DeepSeek** | None | Capped by `max_tokens` (default 32K, max 64K) |
| **Alibaba Qwen** | `thinking_budget` | Integer (max tokens for reasoning) |
| **Mistral** | None | No budget control available |

### Response Format (Non-Streaming)

#### Groq
```json
{
  "choices": [{
    "message": {
      "role": "assistant",
      "content": "The answer is 42.",
      "reasoning": "Let me think step by step..."
    }
  }]
}
```
- Field name: **`reasoning`** (unique to Groq)
- Type: string

#### DeepSeek
```json
{
  "choices": [{
    "message": {
      "role": "assistant",
      "content": "The answer is 42.",
      "reasoning_content": "Let me think step by step..."
    }
  }]
}
```
- Field name: **`reasoning_content`**
- Type: string
- **CRITICAL:** Do NOT send `reasoning_content` back in multi-turn messages — causes 400 error

#### Alibaba Qwen
```json
{
  "choices": [{
    "message": {
      "role": "assistant",
      "content": "The answer is 42.",
      "reasoning_content": "Let me think step by step..."
    }
  }]
}
```
- Field name: **`reasoning_content`** (same as DeepSeek)
- Type: string

#### Mistral (Magistral models)
```json
{
  "choices": [{
    "message": {
      "role": "assistant",
      "content": [
        {
          "type": "thinking",
          "thinking": [
            {"type": "text", "text": "Let me think step by step..."}
          ]
        },
        {
          "type": "text",
          "text": "The answer is 42."
        }
      ]
    }
  }]
}
```
- Field name: **`content`** becomes an array of typed blocks
- `content` is no longer a string — it's `Array<{type: "thinking" | "text", ...}>`
- Most divergent approach of all providers

### Groq Alternative: Raw Mode
Groq also supports `reasoning_format: "raw"` which inlines thinking in content:
```json
{
  "message": {
    "content": "<think>Let me think step by step...</think>The answer is 42."
  }
}
```

---

## 2. Streaming

### SSE Format — All Providers

All use `data:` prefixed SSE lines, terminated by `data: [DONE]`. Basic chunk shape is consistent:

```
data: {"id":"...","object":"chat.completion.chunk","choices":[{"index":0,"delta":{...},"finish_reason":null}]}
```

### Thinking Token Streaming — The Divergence

#### Groq
```
data: {"choices":[{"delta":{"reasoning":"Let me think..."}}]}
data: {"choices":[{"delta":{"reasoning":" step by step"}}]}
data: {"choices":[{"delta":{"content":"The answer"}}]}
data: {"choices":[{"delta":{"content":" is 42."}}]}
```
- Uses `delta.reasoning` field

#### DeepSeek
```
data: {"choices":[{"delta":{"reasoning_content":"Let me think..."}}]}
data: {"choices":[{"delta":{"reasoning_content":" step by step"}}]}
data: {"choices":[{"delta":{"content":"The answer"}}]}
data: {"choices":[{"delta":{"content":" is 42."}}]}
```
- Uses `delta.reasoning_content` field
- Reasoning and content phases do NOT overlap

#### Alibaba Qwen
```
data: {"choices":[{"delta":{"reasoning_content":"Let me think...","content":null}}]}
data: {"choices":[{"delta":{"reasoning_content":" step by step","content":null}}]}
data: {"choices":[{"delta":{"reasoning_content":null,"content":"The answer"}}]}
data: {"choices":[{"delta":{"reasoning_content":null,"content":" is 42."}}]}
```
- Uses `delta.reasoning_content` (same field name as DeepSeek)
- **But** explicitly sends `null` for the inactive field in each chunk (DeepSeek omits it)

#### Mistral
```
data: {"choices":[{"delta":{"content":[{"type":"thinking","thinking":[{"type":"text","text":"Let me think..."}]}]}}]}
data: {"choices":[{"delta":{"content":[{"type":"text","text":"The answer is 42."}]}}]}
```
- Content blocks streamed as typed arrays (most complex parsing)

### Usage in Streaming

| Provider | How to Get Usage | Where It Appears |
|----------|-----------------|------------------|
| **Groq** | `stream_options: {"include_usage": true}` | Final chunk before `[DONE]` |
| **DeepSeek** | `stream_options: {"include_usage": true}` | Final chunk before `[DONE]` |
| **Alibaba Qwen** | `stream_options: {"include_usage": true}` | Final chunk (empty choices array) |
| **Mistral** | Automatic | Final chunk with `finish_reason` |

---

## 3. Tool Calling

The most consistent area — all providers follow OpenAI's pattern closely.

### Tool Definition Schema — Identical Across All 4

```json
{
  "type": "function",
  "function": {
    "name": "get_weather",
    "description": "Get weather for a location",
    "parameters": {
      "type": "object",
      "properties": {
        "location": {"type": "string", "description": "City name"}
      },
      "required": ["location"]
    }
  }
}
```

### tool_choice Options

| Value | Groq | DeepSeek | Qwen | Mistral |
|-------|------|----------|------|---------|
| `"none"` | Yes | Yes | Yes | Yes |
| `"auto"` | Yes | Yes | Yes | Yes (default) |
| `"required"` | Yes | Yes | Yes | `"any"` or `"required"` |
| Specific function | Yes | Yes | Yes | Yes |

Mistral uses `"any"` as an alias for `"required"` — minor divergence.

### Response Shape — Consistent

All return the same structure:
```json
{
  "message": {
    "role": "assistant",
    "content": null,
    "tool_calls": [{
      "id": "call_abc123",
      "type": "function",
      "function": {
        "name": "get_weather",
        "arguments": "{\"location\": \"Paris\"}"
      }
    }]
  },
  "finish_reason": "tool_calls"
}
```

### Tool Result Message — Consistent

```json
{
  "role": "tool",
  "tool_call_id": "call_abc123",
  "content": "{\"temperature\": 22}"
}
```

Mistral also includes `"name": "get_weather"` in tool messages.

### Parallel Tool Calls

| Provider | Default | Parameter |
|----------|---------|-----------|
| **Groq** | Enabled | `parallel_tool_calls: true/false` |
| **DeepSeek** | Supported | No explicit param |
| **Alibaba Qwen** | **Not supported with streaming** | N/A |
| **Mistral** | Supported | `parallel_tool_calls: true/false` |

### Strict Mode

| Provider | Supported | How |
|----------|-----------|-----|
| **Groq** | No | — |
| **DeepSeek** | Yes (Beta) | `"strict": true` on function, requires `additionalProperties: false` |
| **Alibaba Qwen** | No | — |
| **Mistral** | No | — |

---

## 4. Usage Reporting

### Standard Fields

All providers return at minimum:
```json
{
  "prompt_tokens": 50,
  "completion_tokens": 100,
  "total_tokens": 150
}
```

### Extended Fields — Where They Diverge

#### Groq
```json
{
  "usage": {
    "prompt_tokens": 18,
    "completion_tokens": 556,
    "total_tokens": 574,
    "queue_time": 0.037,
    "prompt_time": 0.0007,
    "completion_time": 0.463,
    "total_time": 0.464
  }
}
```
- **Unique:** Timing fields (`queue_time`, `prompt_time`, `completion_time`, `total_time`)
- Reasoning tokens: via Responses API only (`output_tokens_details.reasoning_tokens`)

#### DeepSeek
```json
{
  "usage": {
    "prompt_tokens": 156,
    "completion_tokens": 48,
    "total_tokens": 204,
    "prompt_cache_hit_tokens": 128,
    "prompt_cache_miss_tokens": 28,
    "completion_tokens_details": {
      "reasoning_tokens": 38
    }
  }
}
```
- **Unique:** Top-level `prompt_cache_hit_tokens` and `prompt_cache_miss_tokens`
- Reasoning tokens in `completion_tokens_details.reasoning_tokens`

#### Alibaba Qwen
```json
{
  "usage": {
    "prompt_tokens": 3019,
    "completion_tokens": 288,
    "total_tokens": 3307,
    "prompt_tokens_details": {
      "cached_tokens": 2048,
      "text_tokens": 971,
      "image_tokens": 0,
      "video_tokens": 0,
      "audio_tokens": null
    },
    "completion_tokens_details": {
      "text_tokens": 100,
      "reasoning_tokens": 188,
      "audio_tokens": null
    }
  }
}
```
- **Most granular:** Breaks down by modality (text, image, video, audio)
- Cache via `prompt_tokens_details.cached_tokens`
- Reasoning via `completion_tokens_details.reasoning_tokens`

#### Mistral
```json
{
  "usage": {
    "prompt_tokens": 11,
    "completion_tokens": 268,
    "total_tokens": 279
  }
}
```
- **Simplest:** No breakdown for reasoning tokens, no cache reporting
- Thinking tokens rolled into `completion_tokens` with no separation

---

## 5. Cache Semantics

| Provider | Cache Type | Control Param | Reporting |
|----------|-----------|---------------|-----------|
| **Groq** | Unknown | None documented | `cached_tokens` in Responses API |
| **DeepSeek** | Automatic prefix caching | None (always on, min 64 tokens) | `prompt_cache_hit_tokens`, `prompt_cache_miss_tokens` |
| **Alibaba Qwen** | Explicit caching | Via cache creation API | `prompt_tokens_details.cached_tokens` |
| **Mistral** | None documented | N/A | N/A |

### DeepSeek Cache Details
- Always enabled, no opt-in
- Prefix-based: matches from the start of messages
- Minimum cacheable unit: 64 tokens
- Cache hit tokens priced at ~1/10th of miss tokens
- TTL: automatic cleanup, hours to days of inactivity

---

## 6. Message Format

### Supported Roles

| Role | Groq | DeepSeek | Qwen | Mistral |
|------|------|----------|------|---------|
| `system` | Yes | Yes | Yes | Yes |
| `user` | Yes | Yes | Yes | Yes |
| `assistant` | Yes | Yes | Yes | Yes |
| `tool` | Yes | Yes | Yes | Yes |

Consistent across all providers.

### System Prompt Handling

All support `system` as a standard role in the messages array. No provider requires it as a separate parameter (unlike Anthropic's Claude API which uses a top-level `system` field).

### Content Types

| Provider | String content | Array content (multimodal) |
|----------|---------------|---------------------------|
| **Groq** | Yes | Yes (OpenAI format) |
| **DeepSeek** | Yes | Yes (OpenAI format) |
| **Alibaba Qwen** | Yes | Yes (OpenAI format in compat mode, different in DashScope native) |
| **Mistral** | Yes | Yes (OpenAI format) — BUT reasoning models return array of typed blocks |

### Groq-Specific Extras
- `x_groq` object in response with internal request ID
- `service_tier` field: `"auto"`, `"on_demand"`, `"flex"`, `"performance"`
- Temperature `0` silently converted to `1e-8`
- `N` must be `1`

### DeepSeek-Specific Extras
- `assistant.prefix` field (Beta) for response prefilling
- `reasoning_content` in response but MUST NOT be sent back in input
- `finish_reason: "insufficient_system_resource"` (unique error state)

### Alibaba Qwen-Specific Extras
- DashScope native format wraps messages in `input.messages` with params in `parameters`
- `enable_search` and `search_options` for web search
- Native format includes usage in every streaming chunk by default

### Mistral-Specific Extras
- `safe_prompt` boolean for safety guardrails
- `metadata` object for session tracking
- `random_seed` for deterministic outputs

---

## 7. Structured Output

| Provider | Method | Parameter |
|----------|--------|-----------|
| **Groq** | JSON mode | `response_format: {"type": "json_object"}` |
| **DeepSeek** | JSON mode | `response_format: {"type": "json_object"}` |
| **Alibaba Qwen** | JSON mode | `response_format: {"type": "json_object"}` |
| **Mistral** | JSON mode | `response_format: {"type": "json_object"}` |

JSON Schema constrained output support varies and is less documented.

---

## 8. Error Handling

### HTTP Status Codes (All Providers)
- `400` — Bad request / invalid parameters
- `401` — Invalid API key
- `429` — Rate limited
- `500` — Server error

### Rate Limit Headers

| Provider | Headers |
|----------|---------|
| **Groq** | `x-ratelimit-limit-*`, `x-ratelimit-remaining-*`, `x-ratelimit-reset-*` |
| **DeepSeek** | Standard `Retry-After` |
| **Alibaba Qwen** | Varies by endpoint |
| **Mistral** | Standard rate limit headers |

### Unique Error States
- **DeepSeek:** `finish_reason: "insufficient_system_resource"` — server overloaded
- **Groq:** `finish_reason` limited to `"stop"`, `"length"`, `"tool_calls"`

---

## Summary: Fragmentation Heat Map

| Feature | Consistency | Notes |
|---------|-------------|-------|
| **Messages format** | HIGH | All use OpenAI-style messages array |
| **Tool calling** | HIGH | Nearly identical schemas and response shapes |
| **Structured output** | HIGH | All support `json_object` mode |
| **Basic streaming** | HIGH | All use SSE with `data:` prefix and `[DONE]` |
| **Usage (basic)** | HIGH | All return `prompt_tokens`, `completion_tokens`, `total_tokens` |
| **Thinking enable param** | **LOW** | 4 providers, 4 different params |
| **Thinking response format** | **LOW** | 3 different field names, 1 uses typed content blocks |
| **Thinking budget control** | **LOW** | All different (effort levels vs token count vs none) |
| **Thinking streaming** | **LOW** | 3 different delta field names, 1 uses content block arrays |
| **Usage (reasoning breakdown)** | **MEDIUM** | 3 of 4 report it, but in different nested structures |
| **Usage (cache reporting)** | **LOW** | All different: top-level fields vs nested vs none |
| **Cache control** | **LOW** | Ranges from automatic (DeepSeek) to explicit (Qwen) to none (Mistral) |

**Conclusion:** The basics (messages, tools, JSON mode) are already ~90% standardized thanks to OpenAI's gravity. The modern features (thinking, caching, detailed usage) are where Open Layer adds the most value. This is exactly the right gap to target.

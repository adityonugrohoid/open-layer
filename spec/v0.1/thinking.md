# Thinking

> **Status:** Draft
> **Conformance Level:** Level 2 (Thinking)
> **Schema:** [`schema/thinking.json`](schema/thinking.json)

## Overview

This section defines how clients enable, control, and consume thinking (reasoning) tokens. Thinking tokens expose a model's internal chain-of-thought, improving transparency and debuggability for complex tasks.

Open Layer normalizes the four divergent provider approaches into a single canonical format using a `thinking` object on both request and response.

The key words "MUST", "MUST NOT", "REQUIRED", "SHALL", "SHALL NOT", "SHOULD", "SHOULD NOT", "RECOMMENDED", "MAY", and "OPTIONAL" in this document are to be interpreted as described in [RFC 2119](https://www.rfc-editor.org/rfc/rfc2119).

## Request Format

To enable thinking, include a `thinking` object in the chat completion request:

```json
{
  "model": "deepseek-reasoner",
  "messages": [
    {"role": "user", "content": "What is 25 * 37?"}
  ],
  "thinking": {
    "enabled": true,
    "budget_tokens": 4096
  }
}
```

### Field Reference

| Field | Type | Required | Default | Description |
|-------|------|----------|---------|-------------|
| `thinking.enabled` | boolean | REQUIRED | — | Whether to enable thinking/reasoning output. |
| `thinking.budget_tokens` | integer | OPTIONAL | Provider-defined | Maximum tokens the model may use for thinking. Providers that do not support budget control MUST accept and ignore this field. |

### Behavior

- When `thinking.enabled` is `true`, the model SHOULD produce thinking content before its final answer.
- When `thinking.enabled` is `false` or the `thinking` object is omitted, the model MUST NOT include a `thinking` field in the response.
- `budget_tokens` is a hint, not a hard limit. Providers SHOULD respect it as closely as possible but MAY exceed or underuse the budget.
- If a provider does not support thinking at all, it MUST return an error (see [Errors](errors.md)) with type `"invalid_request_error"` and a message indicating thinking is not supported for the requested model.

## Response Format

When thinking is enabled, the assistant message includes a `thinking` object:

```json
{
  "choices": [
    {
      "index": 0,
      "message": {
        "role": "assistant",
        "content": "25 * 37 = 925.",
        "thinking": {
          "content": "Let me calculate 25 * 37 step by step.\n25 * 37 = 25 * 30 + 25 * 7 = 750 + 175 = 925."
        }
      },
      "finish_reason": "stop"
    }
  ]
}
```

### Field Reference

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `thinking.content` | string | REQUIRED | The model's thinking/reasoning text. |

### Design Rationale

- **`thinking.content` is always a string** — This preserves compatibility with clients that expect `content` to be a simple string. Mistral's block-array format MUST be flattened to a single string by adapters.
- **Field name `thinking`** — The name `thinking` was chosen to avoid the `reasoning` vs `reasoning_content` split across providers. It is a new canonical name that maps cleanly to all providers.

## Streaming Format

When streaming with thinking enabled, thinking content arrives as `delta.thinking.content` before the main `delta.content`. See [Streaming](streaming.md) for full details.

```
data: {"choices":[{"delta":{"role":"assistant"}}]}
data: {"choices":[{"delta":{"thinking":{"content":"Let me calculate..."}}}]}
data: {"choices":[{"delta":{"thinking":{"content":" 25 * 37"}}}]}
data: {"choices":[{"delta":{"content":"25 * 37 = 925."}}]}
data: {"choices":[{"delta":{},"finish_reason":"stop"}]}
```

### Phase Sequencing

1. **Role delta** — First chunk establishes `role: "assistant"`.
2. **Thinking phase** — Zero or more chunks with `delta.thinking.content`.
3. **Content phase** — Zero or more chunks with `delta.content`.
4. **Finish** — Final chunk with `finish_reason`.

Thinking and content phases MUST NOT overlap. Once the first `delta.content` chunk is emitted, no further `delta.thinking.content` chunks may follow.

## Multi-Turn Rules

### Sending Thinking Back in Conversation

When replaying an assistant message that included thinking in a multi-turn conversation:

1. Providers SHOULD accept the `thinking` field on assistant messages in input.
2. If a provider does not support thinking in input messages, it MUST accept and silently ignore the `thinking` field (not return an error).
3. Clients SHOULD strip the `thinking` field from assistant messages before sending them as input, as some providers (notably DeepSeek) return errors when `reasoning_content` is included in input.

**Recommendation:** Adapters SHOULD strip `thinking` from input assistant messages by default, unless the provider is known to accept it.

## Conformance Requirements

### Level 2 (Thinking) — REQUIRED (in addition to Level 1)

1. Providers MUST accept the `thinking` request object as defined above.
2. When `thinking.enabled` is `true`, the response MUST include `thinking.content` on the assistant message.
3. `thinking.content` MUST be a string (not an array, not an object).
4. In streaming mode, thinking deltas MUST use the `delta.thinking.content` field.
5. Thinking and content phases MUST NOT overlap in streaming.
6. Providers that support budget control MUST accept `budget_tokens` and map it to their native parameter.
7. Providers that do not support budget control MUST accept and ignore `budget_tokens` without error.
8. Providers MUST report reasoning token usage in `completion_tokens_details.reasoning_tokens`. See [Usage](usage.md).
9. Providers MUST NOT include `thinking` in the response when thinking is not enabled.

## Provider Mapping

### Enable Parameter

| Standard | Groq | DeepSeek | Nvidia | Mistral |
|----------|------|----------|--------|---------|
| `thinking.enabled: true` | `reasoning_format: "parsed"` | `thinking: {"type": "enabled"}` | Use reasoning model (e.g. `deepseek-ai/deepseek-r1-distill-*`) or `chat_template_kwargs: {"enable_thinking": true}` | `prompt_mode: "reasoning"` |
| `thinking.enabled: false` | `reasoning_format: "none"` (or omit) | Omit `thinking` param | Use non-reasoning model or omit `chat_template_kwargs` | Omit `prompt_mode` |

### Budget Parameter

| Standard | Groq | DeepSeek | Nvidia | Mistral |
|----------|------|----------|--------|---------|
| `thinking.budget_tokens: N` | `reasoning_effort` (map to `"low"`, `"medium"`, `"high"`) | Not supported (uses `max_tokens`) | Not supported (ignore) | Not supported (ignore) |

**Budget mapping for Groq:** Since Groq uses effort levels rather than token counts, adapters SHOULD map `budget_tokens` as follows:

| `budget_tokens` | `reasoning_effort` |
|-----------------|-------------------|
| ≤ 1024 | `"low"` |
| 1025–8192 | `"medium"` |
| > 8192 | `"high"` |

These thresholds are recommendations. Adapters MAY use different mappings.

### Response Field

| Standard | Groq | DeepSeek | Nvidia | Mistral |
|----------|------|----------|--------|---------|
| `message.thinking.content` | `message.reasoning` | `message.reasoning_content` | `message.reasoning_content` (or `<think>` tags in `content` for R1-distill models) | `message.content[].thinking[].text` (flattened) |

### Streaming Delta Field

| Standard | Groq | DeepSeek | Nvidia | Mistral |
|----------|------|----------|--------|---------|
| `delta.thinking.content` | `delta.reasoning` | `delta.reasoning_content` | `delta.reasoning_content` | `delta.content[].thinking[].text` (flattened) |

### Adapter Notes

- **Mistral:** The most complex mapping. Mistral returns `content` as an array of typed blocks. Adapters MUST:
  1. Extract text from all blocks with `"type": "thinking"` and concatenate into `thinking.content`.
  2. Extract text from all blocks with `"type": "text"` and concatenate into `content`.
- **DeepSeek:** Adapters MUST strip `reasoning_content` from input assistant messages to avoid 400 errors.
- **Nvidia:** Two response patterns exist:
  1. Models like `deepseek-ai/deepseek-v3.1` return `reasoning_content` as a separate field (same as DeepSeek native).
  2. R1-distill models embed thinking in `<think>...</think>` tags within `content`. Adapters MUST parse these tags, extract the thinking text into `thinking.content`, and strip the tags from `content`.
  3. Non-reasoning models return `reasoning_content: null` and `reasoning: null` — adapters MUST strip these null fields.

## Examples

### Example 1: Basic thinking request

**Request:**
```json
{
  "model": "deepseek-reasoner",
  "messages": [
    {"role": "user", "content": "What is the sum of the first 100 positive integers?"}
  ],
  "thinking": {
    "enabled": true,
    "budget_tokens": 2048
  }
}
```

**Response:**
```json
{
  "id": "chatcmpl-think-001",
  "object": "chat.completion",
  "created": 1709000000,
  "model": "deepseek-reasoner",
  "choices": [
    {
      "index": 0,
      "message": {
        "role": "assistant",
        "content": "The sum of the first 100 positive integers is 5050.",
        "thinking": {
          "content": "I need to find 1 + 2 + 3 + ... + 100.\nUsing the formula n(n+1)/2:\n100 * 101 / 2 = 10100 / 2 = 5050."
        }
      },
      "finish_reason": "stop"
    }
  ],
  "usage": {
    "prompt_tokens": 18,
    "completion_tokens": 45,
    "total_tokens": 63,
    "completion_tokens_details": {
      "reasoning_tokens": 32
    }
  }
}
```

### Example 2: Thinking disabled (no thinking in response)

**Request:**
```json
{
  "model": "llama-3.3-70b",
  "messages": [
    {"role": "user", "content": "Hello!"}
  ]
}
```

**Response:**
```json
{
  "id": "chatcmpl-no-think-001",
  "object": "chat.completion",
  "created": 1709000100,
  "model": "llama-3.3-70b",
  "choices": [
    {
      "index": 0,
      "message": {
        "role": "assistant",
        "content": "Hello! How can I help you today?"
      },
      "finish_reason": "stop"
    }
  ],
  "usage": {
    "prompt_tokens": 8,
    "completion_tokens": 9,
    "total_tokens": 17
  }
}
```

### Example 3: Multi-turn with thinking (stripping thinking from input)

**Request (second turn — thinking stripped from first assistant message):**
```json
{
  "model": "deepseek-reasoner",
  "messages": [
    {"role": "user", "content": "What is 25 * 37?"},
    {"role": "assistant", "content": "25 * 37 = 925."},
    {"role": "user", "content": "Now divide that by 5."}
  ],
  "thinking": {
    "enabled": true
  }
}
```

**Response:**
```json
{
  "id": "chatcmpl-think-002",
  "object": "chat.completion",
  "created": 1709000200,
  "model": "deepseek-reasoner",
  "choices": [
    {
      "index": 0,
      "message": {
        "role": "assistant",
        "content": "925 / 5 = 185.",
        "thinking": {
          "content": "The previous result was 925. Now I need to divide by 5.\n925 / 5 = 185."
        }
      },
      "finish_reason": "stop"
    }
  ],
  "usage": {
    "prompt_tokens": 35,
    "completion_tokens": 28,
    "total_tokens": 63,
    "completion_tokens_details": {
      "reasoning_tokens": 18
    }
  }
}
```

# Messages

> **Status:** Draft
> **Conformance Level:** Level 1 (Core)
> **Schema:** [`schema/message.json`](schema/message.json), [`schema/chat-completion-request.json`](schema/chat-completion-request.json), [`schema/chat-completion-response.json`](schema/chat-completion-response.json)

## Overview

This section defines the core request and response contract for chat completions. An Open Layer conformant provider MUST accept requests and produce responses matching the formats defined here.

The key words "MUST", "MUST NOT", "REQUIRED", "SHALL", "SHALL NOT", "SHOULD", "SHOULD NOT", "RECOMMENDED", "MAY", and "OPTIONAL" in this document are to be interpreted as described in [RFC 2119](https://www.rfc-editor.org/rfc/rfc2119).

## Request Format

### Endpoint

```
POST /v1/chat/completions
```

### Request Body

```json
{
  "model": "llama-3.3-70b",
  "messages": [
    {"role": "system", "content": "You are a helpful assistant."},
    {"role": "user", "content": "What is the capital of France?"}
  ],
  "temperature": 0.7,
  "top_p": 1.0,
  "max_tokens": 256,
  "stop": ["\n\n"],
  "stream": false
}
```

### Field Reference

| Field | Type | Required | Default | Description |
|-------|------|----------|---------|-------------|
| `model` | string | REQUIRED | — | Model identifier. Provider-specific (e.g. `"llama-3.3-70b"`, `"deepseek-chat"`). |
| `messages` | array of [Message](#message-object) | REQUIRED | — | Conversation history. MUST contain at least one message. |
| `temperature` | number | OPTIONAL | Provider-defined | Sampling temperature. Range: `0.0` to `2.0`. |
| `top_p` | number | OPTIONAL | Provider-defined | Nucleus sampling threshold. Range: `0.0` to `1.0`. |
| `max_tokens` | integer | OPTIONAL | Provider-defined | Maximum tokens to generate in the completion. |
| `stop` | string \| string[] | OPTIONAL | `null` | Up to 4 sequences where the model stops generating. |
| `stream` | boolean | OPTIONAL | `false` | If `true`, response is streamed as SSE events. See [Streaming](streaming.md). |
| `n` | integer | OPTIONAL | `1` | Number of completions to generate. Providers MAY restrict this to `1`. |

### Message Object

A message represents a single turn in the conversation.

```json
{
  "role": "user",
  "content": "Hello, world!"
}
```

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `role` | string | REQUIRED | One of: `"system"`, `"user"`, `"assistant"`, `"tool"`. |
| `content` | string \| null | REQUIRED | The text content of the message. MUST be a string or `null`. |
| `name` | string | OPTIONAL | An optional name for the participant. |

#### Roles

- **`system`** — Sets behavior and context for the model. Providers MUST support `system` as a role within the `messages` array (not as a separate top-level field).
- **`user`** — A message from the human user.
- **`assistant`** — A message from the model. Used in multi-turn conversations to represent previous model outputs.
- **`tool`** — A tool result message. See the tool calling specification (Level 3, deferred to v0.2).

#### Assistant Message Extensions

Assistant messages in responses MAY include additional fields defined in other spec sections:

- `thinking` — Thinking/reasoning content. See [Thinking](thinking.md).

These extension fields MUST NOT appear on `system`, `user`, or `tool` messages.

## Response Format

### Response Body

```json
{
  "id": "chatcmpl-abc123",
  "object": "chat.completion",
  "created": 1709000000,
  "model": "llama-3.3-70b",
  "choices": [
    {
      "index": 0,
      "message": {
        "role": "assistant",
        "content": "The capital of France is Paris."
      },
      "finish_reason": "stop"
    }
  ],
  "usage": {
    "prompt_tokens": 25,
    "completion_tokens": 8,
    "total_tokens": 33
  }
}
```

### Field Reference

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `id` | string | REQUIRED | Unique identifier for the completion. |
| `object` | string | REQUIRED | Always `"chat.completion"`. |
| `created` | integer | REQUIRED | Unix timestamp (seconds) when the completion was created. |
| `model` | string | REQUIRED | The model that generated the completion. |
| `choices` | array of [Choice](#choice-object) | REQUIRED | List of completion choices. |
| `usage` | [Usage](usage.md) | REQUIRED | Token usage statistics. See [Usage](usage.md). |

### Choice Object

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `index` | integer | REQUIRED | Index of the choice in the `choices` array. |
| `message` | [Message](#message-object) | REQUIRED | The generated message. Role MUST be `"assistant"`. |
| `finish_reason` | string | REQUIRED | Why the model stopped generating. See [Finish Reasons](#finish-reasons). |

### Finish Reasons

| Value | Description |
|-------|-------------|
| `"stop"` | Model reached a natural stopping point or a `stop` sequence. |
| `"length"` | Model hit `max_tokens` limit. |
| `"tool_calls"` | Model is requesting a tool call (Level 3). |

Providers MUST return one of the above values. Provider-specific finish reasons (e.g. `"insufficient_system_resource"`) SHOULD be mapped to the closest standard value or to `"stop"` with an accompanying error in the response.

## Conformance Requirements

### Level 1 (Core) — REQUIRED

1. Providers MUST accept `POST /v1/chat/completions` with the request body defined above.
2. Providers MUST support all four roles: `system`, `user`, `assistant`, `tool`.
3. Providers MUST return responses matching the response body schema.
4. Providers MUST include `id`, `object`, `created`, `model`, `choices`, and `usage` in every non-streaming response.
5. Providers MUST return `finish_reason` as one of the standard values defined above.
6. Providers MUST support `temperature`, `top_p`, `max_tokens`, `stop`, and `stream` parameters.
7. Providers SHOULD accept and ignore unknown fields in the request body (forward compatibility).
8. Providers MAY include additional fields prefixed with `x-` in the response.

## Provider Mapping

### Request Parameters

All four target providers accept the standard request format with no translation needed:

| Parameter | Groq | DeepSeek | Nvidia | Mistral |
|-----------|------|----------|------|---------|
| `model` | ✅ | ✅ | ✅ | ✅ |
| `messages` | ✅ | ✅ | ✅ | ✅ |
| `temperature` | ✅ | ✅ | ✅ | ✅ |
| `top_p` | ✅ | ✅ | ✅ | ✅ |
| `max_tokens` | ✅ | ✅ | ✅ | ✅ |
| `stop` | ✅ | ✅ | ✅ | ✅ |
| `stream` | ✅ | ✅ | ✅ | ✅ |

Note: The four target providers are **Groq**, **DeepSeek**, **Nvidia** (NIM API), and **Mistral**.

### Response Fields

| Field | Groq | DeepSeek | Nvidia | Mistral |
|-------|------|----------|------|---------|
| `id` | ✅ | ✅ | ✅ | ✅ |
| `object` | ✅ | ✅ | ✅ | ✅ |
| `created` | ✅ | ✅ | ✅ | ✅ |
| `model` | ✅ | ✅ | ✅ | ✅ |
| `choices` | ✅ | ✅ | ✅ | ✅ |
| `usage` | ✅ | ✅ | ✅ | ✅ |
| `finish_reason` | `stop`, `length`, `tool_calls` | `stop`, `length`, `tool_calls`, `insufficient_system_resource` | `stop`, `length`, `tool_calls` | `stop`, `length`, `tool_calls` |

Note: Nvidia includes `reasoning` and `reasoning_content` fields on all messages (set to `null` for non-reasoning models). Adapters SHOULD strip these `null` fields.

### Provider-Specific Extensions

| Provider | Extra Fields | Handling |
|----------|-------------|----------|
| Groq | `x_groq` (internal request ID), `system_fingerprint` | Pass through as-is |
| DeepSeek | `system_fingerprint` | Pass through as-is |
| Nvidia | `reasoning`, `reasoning_content`, `refusal`, `annotations` (all null for non-reasoning), `metadata` | Strip null fields |
| Mistral | — | — |

## Examples

### Example 1: Simple completion

**Request:**
```json
{
  "model": "llama-3.3-70b",
  "messages": [
    {"role": "user", "content": "Say hello in French."}
  ],
  "max_tokens": 50
}
```

**Response:**
```json
{
  "id": "chatcmpl-abc123",
  "object": "chat.completion",
  "created": 1709000000,
  "model": "llama-3.3-70b",
  "choices": [
    {
      "index": 0,
      "message": {
        "role": "assistant",
        "content": "Bonjour !"
      },
      "finish_reason": "stop"
    }
  ],
  "usage": {
    "prompt_tokens": 12,
    "completion_tokens": 4,
    "total_tokens": 16
  }
}
```

### Example 2: Multi-turn conversation with system prompt

**Request:**
```json
{
  "model": "deepseek-chat",
  "messages": [
    {"role": "system", "content": "You are a concise assistant. Reply in one sentence."},
    {"role": "user", "content": "What is photosynthesis?"},
    {"role": "assistant", "content": "Photosynthesis is the process by which plants convert sunlight into energy."},
    {"role": "user", "content": "What pigment is responsible?"}
  ],
  "temperature": 0.3,
  "max_tokens": 100
}
```

**Response:**
```json
{
  "id": "chatcmpl-def456",
  "object": "chat.completion",
  "created": 1709000100,
  "model": "deepseek-chat",
  "choices": [
    {
      "index": 0,
      "message": {
        "role": "assistant",
        "content": "Chlorophyll is the primary pigment responsible for photosynthesis."
      },
      "finish_reason": "stop"
    }
  ],
  "usage": {
    "prompt_tokens": 52,
    "completion_tokens": 11,
    "total_tokens": 63
  }
}
```

### Example 3: Max tokens reached

**Request:**
```json
{
  "model": "meta/llama-3.3-70b-instruct",
  "messages": [
    {"role": "user", "content": "Write a long essay about the history of computing."}
  ],
  "max_tokens": 10
}
```

**Response:**
```json
{
  "id": "chatcmpl-ghi789",
  "object": "chat.completion",
  "created": 1709000200,
  "model": "meta/llama-3.3-70b-instruct",
  "choices": [
    {
      "index": 0,
      "message": {
        "role": "assistant",
        "content": "The history of computing begins with early mechanical"
      },
      "finish_reason": "length"
    }
  ],
  "usage": {
    "prompt_tokens": 14,
    "completion_tokens": 10,
    "total_tokens": 24
  }
}
```

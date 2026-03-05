# Streaming

> **Status:** Draft
> **Conformance Level:** Level 1 (Core)
> **Schema:** [`schema/chat-completion-chunk.json`](schema/chat-completion-chunk.json)

## Overview

This section defines the streaming response format for chat completions. When `stream: true` is set in the request, the response is delivered as a sequence of Server-Sent Events (SSE), each containing a JSON chunk with incremental content.

The key words "MUST", "MUST NOT", "REQUIRED", "SHALL", "SHALL NOT", "SHOULD", "SHOULD NOT", "RECOMMENDED", "MAY", and "OPTIONAL" in this document are to be interpreted as described in [RFC 2119](https://www.rfc-editor.org/rfc/rfc2119).

## Request Format

To enable streaming, set `stream: true` in the chat completion request:

```json
{
  "model": "llama-3.3-70b",
  "messages": [
    {"role": "user", "content": "Hello!"}
  ],
  "stream": true,
  "stream_options": {
    "include_usage": true
  }
}
```

### Stream Options

| Field | Type | Required | Default | Description |
|-------|------|----------|---------|-------------|
| `stream_options.include_usage` | boolean | OPTIONAL | `false` | If `true`, include usage statistics in the final chunk before `[DONE]`. |

## Response Format

### Transport

- Content-Type: `text/event-stream`
- Each event is prefixed with `data: ` followed by a JSON object.
- The stream terminates with `data: [DONE]`.
- Lines are separated by `\n\n` (double newline).

### Chunk Structure

Each SSE event contains a chat completion chunk:

```json
{
  "id": "chatcmpl-abc123",
  "object": "chat.completion.chunk",
  "created": 1709000000,
  "model": "llama-3.3-70b",
  "choices": [
    {
      "index": 0,
      "delta": {
        "content": "Hello"
      },
      "finish_reason": null
    }
  ]
}
```

### Field Reference

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `id` | string | REQUIRED | Unique identifier for the completion. Same across all chunks. |
| `object` | string | REQUIRED | Always `"chat.completion.chunk"`. |
| `created` | integer | REQUIRED | Unix timestamp (seconds). Same across all chunks. |
| `model` | string | REQUIRED | The model that generated the completion. |
| `choices` | array of [Chunk Choice](#chunk-choice) | REQUIRED | Incremental choices. |
| `usage` | [Usage](usage.md) | CONDITIONAL | Token usage. Present only when `stream_options.include_usage` is `true`, in the final chunk before `[DONE]`. |

### Chunk Choice

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `index` | integer | REQUIRED | Index of the choice. |
| `delta` | [Delta](#delta-object) | REQUIRED | Incremental content for this chunk. |
| `finish_reason` | string \| null | REQUIRED | `null` until the final chunk, then one of: `"stop"`, `"length"`, `"tool_calls"`. |

### Delta Object

The delta contains only the fields that changed in this chunk. All fields are optional.

| Field | Type | Description |
|-------|------|-------------|
| `role` | string | The role. Only present in the first chunk. |
| `content` | string | Incremental text content. |
| `thinking` | object | Incremental thinking content. See [Thinking](thinking.md). |
| `thinking.content` | string | Incremental thinking text. |

## Phase Sequencing

Streaming chunks MUST follow this order:

```
┌─────────────┐    ┌──────────────────┐    ┌───────────────┐    ┌────────┐    ┌─────────┐
│ Role Delta  │ →  │ Thinking Phase   │ →  │ Content Phase │ →  │ Finish │ →  │ Usage   │
│ (1 chunk)   │    │ (0+ chunks)      │    │ (0+ chunks)   │    │(1 chunk│    │(0-1     │
│             │    │ Level 2 only     │    │               │    │        │    │ chunk)  │
└─────────────┘    └──────────────────┘    └───────────────┘    └────────┘    └─────────┘
```

1. **Role delta** — First chunk MUST contain `delta.role: "assistant"`. Content MAY be empty.
2. **Thinking phase** (Level 2 only) — Zero or more chunks with `delta.thinking.content`. Only present when thinking is enabled.
3. **Content phase** — Zero or more chunks with `delta.content`.
4. **Finish chunk** — One chunk with `finish_reason` set and an empty `delta: {}`.
5. **Usage chunk** (optional) — If `include_usage` is `true`, one final chunk with `usage` and an empty `choices` array.
6. **Terminator** — `data: [DONE]`

### Phase Rules

- Thinking and content phases MUST NOT overlap. Once `delta.content` appears, `delta.thinking.content` MUST NOT appear again.
- The finish chunk MUST have an empty delta (`{}` or `{}`).
- The usage chunk (if present) MUST have an empty `choices` array.

## Complete Stream Example

### Without Thinking

```
data: {"id":"chatcmpl-abc123","object":"chat.completion.chunk","created":1709000000,"model":"llama-3.3-70b","choices":[{"index":0,"delta":{"role":"assistant","content":""},"finish_reason":null}]}

data: {"id":"chatcmpl-abc123","object":"chat.completion.chunk","created":1709000000,"model":"llama-3.3-70b","choices":[{"index":0,"delta":{"content":"Hello"},"finish_reason":null}]}

data: {"id":"chatcmpl-abc123","object":"chat.completion.chunk","created":1709000000,"model":"llama-3.3-70b","choices":[{"index":0,"delta":{"content":"!"},"finish_reason":null}]}

data: {"id":"chatcmpl-abc123","object":"chat.completion.chunk","created":1709000000,"model":"llama-3.3-70b","choices":[{"index":0,"delta":{},"finish_reason":"stop"}]}

data: {"id":"chatcmpl-abc123","object":"chat.completion.chunk","created":1709000000,"model":"llama-3.3-70b","choices":[],"usage":{"prompt_tokens":8,"completion_tokens":2,"total_tokens":10}}

data: [DONE]
```

### With Thinking (Level 2)

```
data: {"id":"chatcmpl-think-001","object":"chat.completion.chunk","created":1709000000,"model":"deepseek-reasoner","choices":[{"index":0,"delta":{"role":"assistant"},"finish_reason":null}]}

data: {"id":"chatcmpl-think-001","object":"chat.completion.chunk","created":1709000000,"model":"deepseek-reasoner","choices":[{"index":0,"delta":{"thinking":{"content":"Let me think"}},"finish_reason":null}]}

data: {"id":"chatcmpl-think-001","object":"chat.completion.chunk","created":1709000000,"model":"deepseek-reasoner","choices":[{"index":0,"delta":{"thinking":{"content":" step by step..."}},"finish_reason":null}]}

data: {"id":"chatcmpl-think-001","object":"chat.completion.chunk","created":1709000000,"model":"deepseek-reasoner","choices":[{"index":0,"delta":{"content":"The answer"}},"finish_reason":null}]}

data: {"id":"chatcmpl-think-001","object":"chat.completion.chunk","created":1709000000,"model":"deepseek-reasoner","choices":[{"index":0,"delta":{"content":" is 42."}},"finish_reason":null}]}

data: {"id":"chatcmpl-think-001","object":"chat.completion.chunk","created":1709000000,"model":"deepseek-reasoner","choices":[{"index":0,"delta":{},"finish_reason":"stop"}]}

data: {"id":"chatcmpl-think-001","object":"chat.completion.chunk","created":1709000000,"model":"deepseek-reasoner","choices":[],"usage":{"prompt_tokens":15,"completion_tokens":20,"total_tokens":35,"completion_tokens_details":{"reasoning_tokens":12}}}

data: [DONE]
```

## Error Handling in Streams

If an error occurs mid-stream, the provider MUST:

1. Send an error event as a regular `data:` line with the [Error](errors.md) schema.
2. Terminate the stream (no `[DONE]` after an error).

```
data: {"id":"chatcmpl-abc123","object":"chat.completion.chunk","created":1709000000,"model":"llama-3.3-70b","choices":[{"index":0,"delta":{"content":"Partial response"},"finish_reason":null}]}

data: {"error":{"type":"server_error","message":"Internal server error during generation."}}

```

See [Errors](errors.md) for the full error schema.

## Conformance Requirements

### Level 1 (Core) — REQUIRED

1. Providers MUST support `stream: true` in the request.
2. Streaming responses MUST use `text/event-stream` content type.
3. Each event MUST be prefixed with `data: ` and followed by `\n\n`.
4. The stream MUST terminate with `data: [DONE]\n\n`.
5. Each chunk MUST include `id`, `object`, `created`, `model`, and `choices`.
6. `object` MUST be `"chat.completion.chunk"`.
7. The first chunk MUST include `delta.role`.
8. The final content chunk MUST include `finish_reason`.
9. Providers MUST support `stream_options.include_usage`.
10. When `include_usage` is `true`, the usage chunk MUST appear before `[DONE]` with an empty `choices` array.

### Level 2 (Thinking) — Additional requirements

11. Thinking deltas MUST use `delta.thinking.content`.
12. Thinking and content phases MUST NOT overlap.
13. When thinking is enabled, reasoning tokens MUST be reported in the usage chunk.

## Provider Mapping

### Streaming Delta Fields

| Standard | Groq | DeepSeek | Nvidia | Mistral |
|----------|------|----------|------|---------|
| `delta.content` | `delta.content` | `delta.content` | `delta.content` | `delta.content` (string) or `delta.content[]` (blocks) |
| `delta.thinking.content` | `delta.reasoning` | `delta.reasoning_content` | `delta.reasoning_content` | `delta.content[].thinking[].text` |

### Usage in Streaming

| Standard | Groq | DeepSeek | Nvidia | Mistral |
|----------|------|----------|------|---------|
| `stream_options.include_usage: true` | ✅ | ✅ | ✅ | Automatic (always included) |
| Usage in separate final chunk | ✅ | ✅ | ✅ | In chunk with `finish_reason` |

### Adapter Notes

- **Mistral:** For non-reasoning models, `delta.content` is a string (no translation needed). For Magistral (reasoning) models, `delta.content` is an array of typed blocks. Adapters MUST flatten these blocks into `delta.content` (string) and `delta.thinking.content` (string).
- **Mistral:** Usage is automatic — adapters SHOULD still accept `stream_options.include_usage` but MAY ignore it since Mistral always includes usage.
- **Nvidia:** Uses `reasoning_content` in deltas (same field name as DeepSeek). R1-distill models may embed thinking in `<think>` tags within `content` — adapters MUST parse and separate these.
- **DeepSeek:** Reasoning and content phases never overlap — matches the Open Layer spec naturally.

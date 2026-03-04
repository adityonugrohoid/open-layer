# Errors

> **Status:** Draft
> **Conformance Level:** Level 1 (Core)
> **Schema:** [`schema/error.json`](schema/error.json)

## Overview

This section defines the standard error response format, HTTP status codes, rate limit headers, and error handling in streaming responses. Open Layer normalizes error shapes across providers into a single canonical format.

The key words "MUST", "MUST NOT", "REQUIRED", "SHALL", "SHALL NOT", "SHOULD", "SHOULD NOT", "RECOMMENDED", "MAY", and "OPTIONAL" in this document are to be interpreted as described in [RFC 2119](https://www.rfc-editor.org/rfc/rfc2119).

## Response Format

All errors MUST be returned as a JSON object with a top-level `error` field:

```json
{
  "error": {
    "type": "invalid_request_error",
    "message": "The 'model' field is required.",
    "code": "missing_required_field",
    "param": "model"
  }
}
```

### Field Reference

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `error` | object | REQUIRED | The error object. |
| `error.type` | string | REQUIRED | Error category. One of the [standard types](#error-types). |
| `error.message` | string | REQUIRED | Human-readable error description. |
| `error.code` | string | OPTIONAL | Machine-readable error code for programmatic handling. |
| `error.param` | string | OPTIONAL | The request parameter that caused the error. |

## Error Types

| Type | HTTP Status | Description |
|------|-------------|-------------|
| `invalid_request_error` | 400 | The request is malformed, missing required fields, or has invalid parameter values. |
| `authentication_error` | 401 | The API key is invalid, expired, or missing. |
| `permission_error` | 403 | The API key does not have permission to access the requested resource. |
| `not_found_error` | 404 | The requested model or endpoint does not exist. |
| `rate_limit_error` | 429 | Too many requests. The client should retry after the period indicated by rate limit headers. |
| `server_error` | 500 | An unexpected internal error. The provider should investigate. |
| `overloaded_error` | 503 | The provider is temporarily overloaded. The client should retry with backoff. |

### Mapping Provider-Specific Errors

Providers MAY have unique error states that do not map directly to the standard types. Adapters MUST map these to the closest standard type:

| Provider-Specific | Maps To | Rationale |
|-------------------|---------|-----------|
| DeepSeek `finish_reason: "insufficient_system_resource"` | `overloaded_error` (503) | Server cannot complete the request due to resource constraints. |

## HTTP Status Codes

Providers MUST use the HTTP status codes specified in the [Error Types](#error-types) table. The relationship between `error.type` and HTTP status code MUST be consistent — the same `error.type` MUST always correspond to the same HTTP status code.

### Success Codes

| Status | Usage |
|--------|-------|
| 200 | Successful completion (non-streaming and streaming). |

## Rate Limit Headers

Providers SHOULD include rate limit information in response headers. Open Layer defines the following standard headers:

| Header | Type | Required | Description |
|--------|------|----------|-------------|
| `x-ratelimit-limit-requests` | integer | RECOMMENDED | Maximum requests per time window. |
| `x-ratelimit-limit-tokens` | integer | RECOMMENDED | Maximum tokens per time window. |
| `x-ratelimit-remaining-requests` | integer | RECOMMENDED | Remaining requests in current window. |
| `x-ratelimit-remaining-tokens` | integer | RECOMMENDED | Remaining tokens in current window. |
| `x-ratelimit-reset-requests` | string | RECOMMENDED | Time until request limit resets (duration string, e.g. `"1s"`, `"6m30s"`). |
| `x-ratelimit-reset-tokens` | string | RECOMMENDED | Time until token limit resets (duration string). |
| `retry-after` | integer | RECOMMENDED | Seconds to wait before retrying (on 429 responses). |

### Rate Limit Header Notes

- Rate limit headers SHOULD be included on all responses (not just 429 errors) to allow proactive client throttling.
- The `retry-after` header MUST be included on 429 responses.
- Providers MAY include additional rate limit headers with the `x-ratelimit-` prefix.

## Streaming Errors

If an error occurs during a streaming response, the provider MUST:

1. Send an error event as a `data:` line containing the standard error JSON.
2. Terminate the stream immediately (no `data: [DONE]` after an error).

```
data: {"id":"chatcmpl-abc123","object":"chat.completion.chunk","created":1709000000,"model":"llama-3.3-70b","choices":[{"index":0,"delta":{"content":"Partial"},"finish_reason":null}]}

data: {"error":{"type":"server_error","message":"Internal error during generation."}}

```

### Client Handling

Clients MUST:

1. Check each SSE event for the presence of an `error` field.
2. If an error event is received, treat the stream as terminated.
3. Not wait for `[DONE]` after receiving a stream error.

## Conformance Requirements

### Level 1 (Core) — REQUIRED

1. All error responses MUST use the standard error format with `error.type` and `error.message`.
2. `error.type` MUST be one of the standard types defined above.
3. HTTP status codes MUST match the specified type-to-status mapping.
4. 429 responses MUST include a `retry-after` header.
5. Streaming errors MUST use the standard error format in a `data:` event.
6. Streaming errors MUST terminate the stream without a `[DONE]` event.
7. Providers SHOULD include rate limit headers on all responses.
8. Providers SHOULD use the standard `x-ratelimit-*` header names.

## Provider Mapping

### Error Response Format

All four providers return errors as a JSON object with an `error` field, but the internal structure varies:

| Standard | Groq | DeepSeek | Qwen | Mistral |
|----------|------|----------|------|---------|
| `error.type` | `error.type` | `error.type` | `error.code` (string) | `error.type` |
| `error.message` | `error.message` | `error.message` | `error.message` | `error.message` |
| `error.code` | `error.code` | — | — | — |
| `error.param` | `error.param` | — | `error.param` | — |

### Rate Limit Headers

| Standard | Groq | DeepSeek | Qwen | Mistral |
|----------|------|----------|------|---------|
| `x-ratelimit-limit-requests` | ✅ | — | Varies | ✅ |
| `x-ratelimit-remaining-requests` | ✅ | — | Varies | ✅ |
| `x-ratelimit-reset-requests` | ✅ | — | Varies | ✅ |
| `retry-after` | ✅ | ✅ | Varies | ✅ |

### Adapter Notes

- **Groq:** Error format closely matches Open Layer standard. Minimal translation needed.
- **DeepSeek:** Maps `finish_reason: "insufficient_system_resource"` to `overloaded_error` (503). Error response format matches standard.
- **Qwen:** Uses `error.code` as a string where Open Layer uses `error.type`. Adapters MUST map Qwen's `error.code` values to the standard `error.type` values.
- **Mistral:** Error format closely matches Open Layer standard. Minimal translation needed.

## Examples

### Example 1: Invalid request (missing model)

**HTTP Response:** `400 Bad Request`

```json
{
  "error": {
    "type": "invalid_request_error",
    "message": "The 'model' field is required.",
    "code": "missing_required_field",
    "param": "model"
  }
}
```

### Example 2: Rate limited

**HTTP Response:** `429 Too Many Requests`

**Headers:**
```
retry-after: 2
x-ratelimit-limit-requests: 100
x-ratelimit-remaining-requests: 0
x-ratelimit-reset-requests: 2s
```

```json
{
  "error": {
    "type": "rate_limit_error",
    "message": "Rate limit exceeded. Please retry after 2 seconds."
  }
}
```

### Example 3: Authentication failure

**HTTP Response:** `401 Unauthorized`

```json
{
  "error": {
    "type": "authentication_error",
    "message": "Invalid API key provided."
  }
}
```

### Example 4: Model not found

**HTTP Response:** `404 Not Found`

```json
{
  "error": {
    "type": "not_found_error",
    "message": "Model 'nonexistent-model' not found.",
    "param": "model"
  }
}
```

### Example 5: Server overloaded

**HTTP Response:** `503 Service Unavailable`

```json
{
  "error": {
    "type": "overloaded_error",
    "message": "The server is currently overloaded. Please retry with exponential backoff."
  }
}
```

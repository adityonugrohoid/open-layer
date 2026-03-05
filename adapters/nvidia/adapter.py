"""Nvidia NIM adapter — translates between Open Layer spec and Nvidia API.

Key deviations handled:
- Thinking: Nvidia R1-distill models use <think>...</think> tags in content,
  not a separate message.thinking.content field. This adapter extracts them.
- Usage: Nvidia puts reasoning_tokens at top-level usage (not in completion_tokens_details).
- prompt_tokens_details: Often null instead of omitted.
- No thinking request param: Nvidia models think inherently, no {thinking: {enabled: true}}.
"""

from __future__ import annotations

import re
from typing import Any

THINK_TAG_RE = re.compile(r"<think>(.*?)</think>", re.DOTALL)


class NvidiaAdapter:
    @property
    def provider_name(self) -> str:
        return "nvidia"

    def translate_request(self, payload: dict[str, Any]) -> dict[str, Any]:
        # Strip thinking request param — Nvidia doesn't support it
        payload.pop("thinking", None)
        return payload

    def translate_response(self, data: dict[str, Any]) -> dict[str, Any]:
        # Normalize usage
        usage = data.get("usage", {})
        self._normalize_usage(usage)

        # Extract <think> tags from content into message.thinking
        for choice in data.get("choices", []):
            msg = choice.get("message", {})
            self._extract_thinking(msg)

        return data

    def translate_stream_chunk(self, data: dict[str, Any]) -> dict[str, Any]:
        # Normalize usage if present
        usage = data.get("usage")
        if usage is not None:
            self._normalize_usage(usage)
        return data

    def _normalize_usage(self, usage: dict[str, Any]) -> None:
        # Move top-level reasoning_tokens into completion_tokens_details
        reasoning = usage.pop("reasoning_tokens", None)
        if reasoning is not None:
            details = usage.get("completion_tokens_details") or {}
            details["reasoning_tokens"] = reasoning
            usage["completion_tokens_details"] = details

        # Normalize null details to empty dicts (or omit)
        if usage.get("prompt_tokens_details") is None:
            usage.pop("prompt_tokens_details", None)
        if usage.get("completion_tokens_details") is None:
            usage.pop("completion_tokens_details", None)

    def _extract_thinking(self, msg: dict[str, Any]) -> None:
        content = msg.get("content")
        if not content or not isinstance(content, str):
            return

        match = THINK_TAG_RE.search(content)
        if match:
            thinking_text = match.group(1).strip()
            # Remove <think> tags from content
            clean_content = THINK_TAG_RE.sub("", content).strip()
            msg["content"] = clean_content
            msg["thinking"] = {"content": thinking_text}

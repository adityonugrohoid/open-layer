"""DeepSeek adapter — translates between Open Layer spec and DeepSeek API.

Key deviations handled:
- Thinking: DeepSeek uses reasoning_content field instead of message.thinking.content.
- Input: reasoning_content MUST be stripped from input messages (DeepSeek errors on it).
- No budget control: budget_tokens is accepted and ignored.
"""

from __future__ import annotations

from typing import Any


class DeepSeekAdapter:
    @property
    def provider_name(self) -> str:
        return "deepseek"

    def translate_request(self, payload: dict[str, Any]) -> dict[str, Any]:
        # Strip thinking from input messages (DeepSeek rejects it)
        for msg in payload.get("messages", []):
            msg.pop("thinking", None)

        # DeepSeek doesn't support thinking request param
        payload.pop("thinking", None)

        return payload

    def translate_response(self, data: dict[str, Any]) -> dict[str, Any]:
        for choice in data.get("choices", []):
            msg = choice.get("message", {})
            self._translate_thinking(msg)
        return data

    def translate_stream_chunk(self, data: dict[str, Any]) -> dict[str, Any]:
        for choice in data.get("choices", []):
            delta = choice.get("delta", {})
            self._translate_thinking(delta)
        return data

    def _translate_thinking(self, msg: dict[str, Any]) -> None:
        reasoning = msg.pop("reasoning_content", None)
        if reasoning and isinstance(reasoning, str):
            msg["thinking"] = {"content": reasoning}

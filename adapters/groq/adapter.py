"""Groq adapter — translates between Open Layer spec and Groq API.

Key deviations handled:
- Thinking: Groq uses a reasoning field instead of message.thinking.content.
- Budget: Groq supports reasoning_effort for budget control (maps from budget_tokens).
"""

from __future__ import annotations

from typing import Any


class GroqAdapter:
    @property
    def provider_name(self) -> str:
        return "groq"

    def translate_request(self, payload: dict[str, Any]) -> dict[str, Any]:
        # Map thinking.budget_tokens to reasoning_effort
        thinking = payload.pop("thinking", None)
        if thinking and thinking.get("enabled"):
            budget = thinking.get("budget_tokens")
            if budget is not None:
                payload["reasoning_effort"] = self._budget_to_effort(budget)

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
        reasoning = msg.pop("reasoning", None)
        if reasoning and isinstance(reasoning, str):
            msg["thinking"] = {"content": reasoning}

    def _budget_to_effort(self, budget_tokens: int) -> str:
        if budget_tokens <= 1024:
            return "low"
        elif budget_tokens <= 4096:
            return "medium"
        else:
            return "high"

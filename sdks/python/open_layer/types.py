"""Open Layer spec v0.1 data types."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class Message:
    role: str
    content: str | None
    name: str | None = None
    thinking: ThinkingResponse | None = None

    def to_dict(self) -> dict[str, Any]:
        d: dict[str, Any] = {"role": self.role, "content": self.content}
        if self.name is not None:
            d["name"] = self.name
        if self.thinking is not None:
            d["thinking"] = self.thinking.to_dict()
        return d

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Message:
        thinking = None
        if "thinking" in data and data["thinking"] is not None:
            thinking = ThinkingResponse.from_dict(data["thinking"])
        return cls(
            role=data["role"],
            content=data.get("content"),
            name=data.get("name"),
            thinking=thinking,
        )


@dataclass
class ThinkingRequest:
    enabled: bool
    budget_tokens: int | None = None

    def to_dict(self) -> dict[str, Any]:
        d: dict[str, Any] = {"enabled": self.enabled}
        if self.budget_tokens is not None:
            d["budget_tokens"] = self.budget_tokens
        return d


@dataclass
class ThinkingResponse:
    content: str

    def to_dict(self) -> dict[str, Any]:
        return {"content": self.content}

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> ThinkingResponse:
        return cls(content=data["content"])


@dataclass
class Usage:
    prompt_tokens: int
    completion_tokens: int
    total_tokens: int
    prompt_tokens_details: dict[str, Any] | None = None
    completion_tokens_details: dict[str, Any] | None = None

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Usage:
        return cls(
            prompt_tokens=data["prompt_tokens"],
            completion_tokens=data["completion_tokens"],
            total_tokens=data["total_tokens"],
            prompt_tokens_details=data.get("prompt_tokens_details"),
            completion_tokens_details=data.get("completion_tokens_details"),
        )


@dataclass
class Choice:
    index: int
    message: Message
    finish_reason: str

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Choice:
        return cls(
            index=data["index"],
            message=Message.from_dict(data["message"]),
            finish_reason=data["finish_reason"],
        )


@dataclass
class ChatCompletionRequest:
    model: str
    messages: list[Message]
    temperature: float | None = None
    top_p: float | None = None
    max_tokens: int | None = None
    stop: str | list[str] | None = None
    stream: bool = False
    n: int = 1
    thinking: ThinkingRequest | None = None
    stream_options: dict[str, Any] | None = None

    def to_dict(self) -> dict[str, Any]:
        d: dict[str, Any] = {
            "model": self.model,
            "messages": [m.to_dict() for m in self.messages],
        }
        if self.temperature is not None:
            d["temperature"] = self.temperature
        if self.top_p is not None:
            d["top_p"] = self.top_p
        if self.max_tokens is not None:
            d["max_tokens"] = self.max_tokens
        if self.stop is not None:
            d["stop"] = self.stop
        if self.stream:
            d["stream"] = True
        if self.n != 1:
            d["n"] = self.n
        if self.thinking is not None:
            d["thinking"] = self.thinking.to_dict()
        if self.stream_options is not None:
            d["stream_options"] = self.stream_options
        return d


@dataclass
class ChatCompletionResponse:
    id: str
    object: str
    created: int
    model: str
    choices: list[Choice]
    usage: Usage

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> ChatCompletionResponse:
        return cls(
            id=data["id"],
            object=data["object"],
            created=data["created"],
            model=data["model"],
            choices=[Choice.from_dict(c) for c in data["choices"]],
            usage=Usage.from_dict(data["usage"]),
        )


@dataclass
class StreamDelta:
    role: str | None = None
    content: str | None = None
    thinking: ThinkingResponse | None = None

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> StreamDelta:
        thinking = None
        if "thinking" in data and data["thinking"] is not None:
            t = data["thinking"]
            if t.get("content"):
                thinking = ThinkingResponse(content=t["content"])
        return cls(
            role=data.get("role"),
            content=data.get("content"),
            thinking=thinking,
        )


@dataclass
class StreamChoice:
    index: int
    delta: StreamDelta
    finish_reason: str | None = None

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> StreamChoice:
        return cls(
            index=data["index"],
            delta=StreamDelta.from_dict(data.get("delta", {})),
            finish_reason=data.get("finish_reason"),
        )


@dataclass
class StreamChunk:
    id: str
    object: str
    created: int
    model: str
    choices: list[StreamChoice]
    usage: Usage | None = None

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> StreamChunk:
        usage = None
        if data.get("usage") is not None:
            usage = Usage.from_dict(data["usage"])
        return cls(
            id=data["id"],
            object=data["object"],
            created=data["created"],
            model=data["model"],
            choices=[StreamChoice.from_dict(c) for c in data.get("choices", [])],
            usage=usage,
        )

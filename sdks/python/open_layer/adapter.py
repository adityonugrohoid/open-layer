"""Adapter protocol — defines the interface adapters must implement."""

from __future__ import annotations

from typing import Any, AsyncIterator, Protocol

from open_layer.types import ChatCompletionResponse, StreamChunk


class Adapter(Protocol):
    """Protocol for provider adapters.

    An adapter translates between the Open Layer spec and a provider's native API.
    """

    @property
    def provider_name(self) -> str:
        """Human-readable provider name."""
        ...

    def translate_request(self, payload: dict[str, Any]) -> dict[str, Any]:
        """Transform an Open Layer request payload into provider-native format.

        The input is already a dict (from ChatCompletionRequest.to_dict()).
        The output should be the dict to POST to the provider's chat/completions endpoint.
        """
        ...

    def translate_response(self, data: dict[str, Any]) -> dict[str, Any]:
        """Transform a provider-native response into Open Layer format.

        The input is the raw JSON response from the provider.
        The output should conform to the Open Layer chat-completion-response schema.
        """
        ...

    def translate_stream_chunk(self, data: dict[str, Any]) -> dict[str, Any]:
        """Transform a provider-native streaming chunk into Open Layer format."""
        ...

"""Validate SDK + Nvidia adapter against live API.

Runs a quick chat completion (non-streaming + streaming) through the SDK
for a set of models and reports conformance.

Usage:
    cd ~/projects/open-layer
    source .venv/bin/activate
    python scripts/validate_sdk.py
"""

from __future__ import annotations

import asyncio
import os
import sys
import time

# Add SDK and adapters to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "sdks", "python"))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from dotenv import load_dotenv

from open_layer import OpenLayerClient, ChatCompletionRequest, Message
from adapters.nvidia.adapter import NvidiaAdapter

load_dotenv(os.path.join(os.path.dirname(__file__), "..", ".env"))

NVIDIA_API_KEY = os.environ["NVIDIA_API_KEY"]
NVIDIA_BASE_URL = "https://integrate.api.nvidia.com/v1"

# Same 12 models as conformance test (smoke 5 + extra 7)
MODELS = [
    # Smoke 5
    "meta/llama-3.3-70b-instruct",
    "google/gemma-3-27b-it",
    "mistralai/mistral-small-3.1-24b-instruct-2503",
    "deepseek-ai/deepseek-r1-distill-qwen-14b",
    "microsoft/phi-4-mini-flash-reasoning",
    # Extra 7
    "nvidia/llama-3.1-nemotron-ultra-253b-v1",
    "nvidia/nemotron-mini-4b-instruct",
    "qwen/qwen2.5-coder-32b-instruct",
    "deepseek-ai/deepseek-r1-distill-llama-8b",
    "upstage/solar-10.7b-instruct",
    "ai21labs/jamba-1.5-mini-instruct",
    "thudm/chatglm3-6b",
]

THINKING_KEYWORDS = ("r1", "qwq", "reasoning", "thinking")


def is_thinking_model(model_id: str) -> bool:
    return any(kw in model_id.lower() for kw in THINKING_KEYWORDS)


async def test_model(client: OpenLayerClient, model_id: str) -> dict:
    """Test a single model with non-streaming and streaming, return result dict."""
    result = {"model": model_id, "chat": None, "stream": None, "thinking": None}
    short = model_id.split("/")[-1]

    # Non-streaming chat
    try:
        req = ChatCompletionRequest(
            model=model_id,
            messages=[Message(role="user", content="Say hi.")],
            max_tokens=10,
        )
        resp = await client.chat(req)
        assert resp.object == "chat.completion"
        assert len(resp.choices) >= 1
        assert resp.choices[0].message.role == "assistant"
        assert resp.usage.total_tokens > 0
        result["chat"] = "PASS"
    except Exception as e:
        result["chat"] = f"FAIL: {e}"

    await asyncio.sleep(2)  # throttle

    # Streaming
    try:
        req = ChatCompletionRequest(
            model=model_id,
            messages=[Message(role="user", content="Say hi.")],
            max_tokens=10,
            stream=True,
        )
        chunks = []
        async for chunk in client.stream(req):
            chunks.append(chunk)
        assert len(chunks) > 0
        assert chunks[0].object == "chat.completion.chunk"
        content_parts = []
        for c in chunks:
            for ch in c.choices:
                if ch.delta.content:
                    content_parts.append(ch.delta.content)
        assert len(content_parts) > 0
        result["stream"] = "PASS"
    except Exception as e:
        result["stream"] = f"FAIL: {e}"

    await asyncio.sleep(2)  # throttle

    # Thinking extraction (for thinking models)
    if is_thinking_model(model_id):
        try:
            req = ChatCompletionRequest(
                model=model_id,
                messages=[Message(role="user", content="What is 2+2?")],
                max_tokens=1024,
            )
            resp = await client.chat(req)
            msg = resp.choices[0].message
            # After adapter translation, thinking should be extracted from <think> tags
            if msg.thinking and msg.thinking.content:
                result["thinking"] = "PASS (extracted)"
            elif msg.content and "<think>" in msg.content:
                result["thinking"] = "WARN: <think> tags not extracted"
            else:
                result["thinking"] = "PASS (no thinking in response)"
        except Exception as e:
            result["thinking"] = f"FAIL: {e}"
    else:
        result["thinking"] = "N/A"

    await asyncio.sleep(2)  # throttle

    return result


async def main() -> None:
    adapter = NvidiaAdapter()
    async with OpenLayerClient(
        base_url=NVIDIA_BASE_URL,
        api_key=NVIDIA_API_KEY,
        adapter=adapter,
    ) as client:
        print(f"{'Model':<50} {'Chat':<10} {'Stream':<10} {'Thinking':<30}")
        print("-" * 100)

        for model_id in MODELS:
            result = await test_model(client, model_id)
            short = model_id.split("/")[-1]
            print(
                f"{short:<50} "
                f"{result['chat']:<10} "
                f"{result['stream']:<10} "
                f"{result['thinking']:<30}"
            )


if __name__ == "__main__":
    asyncio.run(main())

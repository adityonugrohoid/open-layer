"""A/B Demo: Raw Nvidia API vs Open Layer SDK + Adapter.

Shows side-by-side comparison of raw provider responses (messy, non-conformant)
vs adapter-normalized output (clean, spec-compliant).

Usage:
    cd ~/projects/open-layer
    source .venv/bin/activate
    python scripts/ab_demo.py
"""

from __future__ import annotations

import asyncio
import copy
import json
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "sdks", "python"))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import httpx
from dotenv import load_dotenv
from rich.console import Console
from rich.panel import Panel
from rich.syntax import Syntax
from rich.table import Table

from adapters.nvidia.adapter import NvidiaAdapter

load_dotenv(os.path.join(os.path.dirname(__file__), "..", ".env"))

NVIDIA_API_KEY = os.environ["NVIDIA_API_KEY"]
BASE_URL = "https://integrate.api.nvidia.com/v1"
PROMPT = "What is 25 * 37? Think step by step."

# Thinking models to try in order (first available wins)
THINKING_MODELS = [
    "nvidia/llama-3.1-nemotron-ultra-253b-v1",
    "deepseek-ai/deepseek-r1-distill-qwen-14b",
    "deepseek-ai/deepseek-r1-distill-llama-8b",
]


async def call_raw_api(model: str) -> dict:
    """Direct httpx call — what you get without Open Layer."""
    async with httpx.AsyncClient(timeout=120.0) as client:
        resp = await client.post(
            f"{BASE_URL}/chat/completions",
            headers={
                "Authorization": f"Bearer {NVIDIA_API_KEY}",
                "Content-Type": "application/json",
            },
            json={
                "model": model,
                "messages": [{"role": "user", "content": PROMPT}],
                "max_tokens": 1024,
            },
        )
        resp.raise_for_status()
        return resp.json()


def normalize_with_adapter(raw: dict) -> dict:
    """Run raw response through NvidiaAdapter.translate_response."""
    data = copy.deepcopy(raw)
    adapter = NvidiaAdapter()
    return adapter.translate_response(data)


def fmt_json(obj: object, max_str_len: int = 200) -> str:
    """Pretty-print JSON, truncating long strings for readability."""

    def truncate(o: object) -> object:
        if isinstance(o, str) and len(o) > max_str_len:
            return o[:max_str_len] + f"... ({len(o)} chars)"
        if isinstance(o, dict):
            return {k: truncate(v) for k, v in o.items()}
        if isinstance(o, list):
            return [truncate(v) for v in o]
        return o

    return json.dumps(truncate(obj), indent=2)


def side_by_side(
    console: Console,
    raw_title: str,
    raw_json: object,
    norm_title: str,
    norm_json: object,
) -> None:
    """Print two JSON panels side by side (red=raw, green=normalized)."""
    raw_panel = Panel(
        Syntax(fmt_json(raw_json), "json", theme="monokai", word_wrap=True),
        title=f"[bold red]{raw_title}[/]",
        border_style="red",
        width=58,
    )
    norm_panel = Panel(
        Syntax(fmt_json(norm_json), "json", theme="monokai", word_wrap=True),
        title=f"[bold green]{norm_title}[/]",
        border_style="green",
        width=58,
    )
    console.print(raw_panel, norm_panel, justify="center")


def display_comparison(console: Console, model: str, raw: dict, normalized: dict) -> None:
    """Display rich panels comparing raw vs normalized responses."""
    raw_msg = raw["choices"][0]["message"]
    raw_content = raw_msg.get("content", "")
    raw_reasoning = raw_msg.get("reasoning_content")
    norm_msg = normalized["choices"][0]["message"]
    raw_usage = raw.get("usage", {})
    has_think_tags = "<think>" in raw_content
    has_reasoning_content = bool(raw_reasoning)
    has_thinking = has_think_tags or has_reasoning_content
    has_reasoning_tokens = "reasoning_tokens" in raw_usage
    has_null_prompt_details = (
        "prompt_tokens_details" in raw_usage
        and raw_usage["prompt_tokens_details"] is None
    )

    # Title
    console.print()
    console.rule("[bold cyan]Open Layer A/B Demo: Raw API vs Adapter-Normalized Output[/]")
    console.print()
    console.print(f"  [bold]Model:[/]  {model}")
    console.print(f"  [bold]Prompt:[/] {PROMPT}")
    console.print()

    # --- Panel 1: Thinking Content Extraction ---
    console.rule("[bold yellow]1. Thinking Content Extraction[/]")
    console.print()

    if has_reasoning_content:
        # reasoning_content field pattern (nemotron-ultra style)
        raw_display = {
            "message.content": raw_content[:200],
            "message.reasoning_content": raw_reasoning[:200] + "...",
            "message.thinking": None,
        }
        norm_display = {
            "message.content": (norm_msg.get("content") or "")[:200],
            "message.reasoning_content": "REMOVED",
            "message.thinking.content": raw_reasoning[:200] + "...",
        }
    elif has_think_tags:
        # <think> tag pattern (R1-distill style)
        think_end = raw_content.find("</think>")
        if think_end != -1:
            think_text = raw_content[7:think_end].strip()
            answer_text = raw_content[think_end + 8:].strip()
        else:
            think_text = raw_content[7:].strip()
            answer_text = ""

        raw_display = {
            "message.content": f"<think>{think_text[:120]}...</think> {answer_text[:80]}...",
            "message.thinking": None,
        }
        norm_display = {
            "message.content": (norm_msg.get("content") or "")[:200],
            "message.thinking.content": think_text[:200] + "...",
        }
    else:
        raw_display = {
            "message.content": raw_content[:200],
            "message.thinking": None,
        }
        norm_display = {
            "message.content": (norm_msg.get("content") or "")[:200],
            "message.thinking": None,
        }

    side_by_side(console, "Raw Nvidia Response", raw_display, "Adapter-Normalized", norm_display)
    console.print()

    if has_reasoning_content:
        console.print(
            "  [yellow]>[/] Raw: [red]message.reasoning_content[/] (non-spec field)"
        )
        console.print(
            "  [yellow]>[/] Normalized: moved to [green]message.thinking.content[/], "
            "reasoning_content removed"
        )
        console.print()
    elif has_think_tags:
        console.print(
            "  [yellow]>[/] Raw: [red]<think>...</think>[/] mixed into message.content"
        )
        console.print(
            "  [yellow]>[/] Normalized: extracted into [green]message.thinking.content[/], "
            "content is clean answer only"
        )
        console.print()

    # --- Panel 2: Usage Normalization ---
    console.rule("[bold yellow]2. Usage Normalization[/]")
    console.print()

    norm_usage = normalized.get("usage", {})
    side_by_side(console, "Raw Usage", raw_usage, "Normalized Usage", norm_usage)
    console.print()

    if has_reasoning_tokens:
        console.print(
            "  [yellow]>[/] [red]usage.reasoning_tokens[/] (top-level, non-spec) "
            "-> [green]usage.completion_tokens_details.reasoning_tokens[/]"
        )
    if has_null_prompt_details:
        console.print(
            "  [yellow]>[/] [red]prompt_tokens_details: null[/] -> [green]omitted[/] (clean)"
        )
    if not has_reasoning_tokens and not has_null_prompt_details:
        console.print("  [dim]No usage normalization needed for this response[/]")
    console.print()

    # --- Panel 3: Full Response Structure ---
    console.rule("[bold yellow]3. Full Response Structure[/]")
    console.print()

    side_by_side(console, "Raw Response (full)", raw, "Normalized Response (full)", normalized)
    console.print()

    # Provider-specific fields present in raw
    extra_fields = [k for k in raw if k not in ("id", "object", "created", "model", "choices", "usage")]
    choice_extras = [
        k for k in raw["choices"][0]
        if k not in ("index", "message", "finish_reason")
    ]
    if extra_fields or choice_extras:
        console.print("  [yellow]>[/] Non-spec fields in raw response:")
        for f in extra_fields:
            console.print(f"    [red]  {f}: {raw[f]}[/]")
        for f in choice_extras:
            console.print(f"    [red]  choices[0].{f}: {raw['choices'][0][f]}[/]")
        console.print()

    # --- Summary Table ---
    console.rule("[bold yellow]Summary of Transformations[/]")
    console.print()

    table = Table(show_header=True, header_style="bold")
    table.add_column("Transformation", style="cyan")
    table.add_column("Before (Raw)", style="red")
    table.add_column("After (Normalized)", style="green")

    if has_reasoning_content:
        table.add_row(
            "Thinking extraction",
            "message.reasoning_content (non-spec)",
            "message.thinking.content",
        )
        table.add_row(
            "Field cleanup",
            "reasoning_content on message",
            "Field removed",
        )
    elif has_think_tags:
        table.add_row(
            "Thinking extraction",
            "<think>...</think> in content",
            "message.thinking.content",
        )
        table.add_row(
            "Content cleaning",
            "Mixed thinking + answer",
            "Clean answer only",
        )

    if has_reasoning_tokens:
        table.add_row(
            "Reasoning tokens",
            "usage.reasoning_tokens (top-level)",
            "usage.completion_tokens_details.reasoning_tokens",
        )

    if has_null_prompt_details:
        table.add_row(
            "Null details cleanup",
            "prompt_tokens_details: null",
            "Field omitted",
        )

    if extra_fields or choice_extras:
        extras = extra_fields + [f"choices[].{f}" for f in choice_extras]
        table.add_row(
            "Non-spec fields",
            ", ".join(extras),
            "Preserved (adapter passthrough)",
        )

    console.print(table)
    console.print()
    console.rule("[bold cyan]Demo complete[/]")
    console.print()


async def main() -> None:
    console = Console(width=120)
    console.print()

    # Try thinking models in order until one responds
    model = None
    raw = None
    for candidate in THINKING_MODELS:
        short = candidate.split("/")[-1]
        console.print(f"[bold]Trying {short}...[/] ", end="")
        try:
            raw = await call_raw_api(candidate)
            model = candidate
            console.print("[green]OK[/]")
            break
        except httpx.HTTPStatusError as e:
            console.print(f"[red]{e.response.status_code}[/] (skipping)")

    if raw is None:
        console.print("[bold red]All models unavailable. Try again later.[/]")
        return

    normalized = normalize_with_adapter(raw)
    display_comparison(console, model, raw, normalized)


if __name__ == "__main__":
    asyncio.run(main())

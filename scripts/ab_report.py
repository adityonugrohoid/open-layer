"""Generate HTML A/B conformance report for all 12 tested models.

Calls each model on Nvidia NIM, captures raw vs adapter-normalized responses,
and generates a self-contained HTML report with side-by-side diff highlighting.

Usage:
    cd ~/projects/open-layer
    source .venv/bin/activate
    python scripts/ab_report.py
    # Opens docs/ab-report.html
"""

from __future__ import annotations

import asyncio
import copy
import html
import json
import os
import sys
from datetime import datetime, timezone
from typing import Any

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "sdks", "python"))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import httpx
from dotenv import load_dotenv

from adapters.nvidia.adapter import NvidiaAdapter

load_dotenv(os.path.join(os.path.dirname(__file__), "..", ".env"))

NVIDIA_API_KEY = os.environ["NVIDIA_API_KEY"]
BASE_URL = "https://integrate.api.nvidia.com/v1"
PROMPT = "What is 25 * 37? Think step by step."
THROTTLE_DELAY = 2.0  # seconds between calls (35 RPM free tier)

MODELS = [
    "meta/llama-3.3-70b-instruct",
    "google/gemma-3-27b-it",
    "mistralai/mistral-small-3.1-24b-instruct-2503",
    "deepseek-ai/deepseek-r1-distill-qwen-14b",
    "microsoft/phi-4-mini-flash-reasoning",
    "nvidia/llama-3.1-nemotron-ultra-253b-v1",
    "nvidia/nemotron-mini-4b-instruct",
    "qwen/qwen2.5-coder-32b-instruct",
    "deepseek-ai/deepseek-r1-distill-llama-8b",
    "upstage/solar-10.7b-instruct",
    "ai21labs/jamba-1.5-mini-instruct",
    "thudm/chatglm3-6b",
]

# Spec-defined fields at each level
SPEC_RESPONSE_KEYS = {"id", "object", "created", "model", "choices", "usage"}
SPEC_CHOICE_KEYS = {"index", "message", "finish_reason"}
SPEC_MESSAGE_KEYS = {"role", "content", "name", "thinking"}
SPEC_USAGE_KEYS = {
    "prompt_tokens", "completion_tokens", "total_tokens",
    "prompt_tokens_details", "completion_tokens_details",
}


# ---------------------------------------------------------------------------
# Data collection
# ---------------------------------------------------------------------------

async def call_model(client: httpx.AsyncClient, model: str) -> dict:
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


async def collect_all() -> list[dict]:
    """Call all models, return list of result dicts."""
    adapter = NvidiaAdapter()
    results: list[dict] = []

    async with httpx.AsyncClient(timeout=180.0) as client:
        for i, model in enumerate(MODELS):
            short = model.split("/")[-1]
            print(f"  [{i+1}/{len(MODELS)}] {short}...", end=" ", flush=True)
            try:
                raw = await call_model(client, model)
                normalized = adapter.translate_response(copy.deepcopy(raw))
                deviations = compute_deviations(raw, normalized)
                results.append({
                    "model": model,
                    "short": short,
                    "status": "ok",
                    "raw": raw,
                    "normalized": normalized,
                    "deviations": deviations,
                })
                print("OK")
            except Exception as e:
                results.append({
                    "model": model,
                    "short": short,
                    "status": "error",
                    "error": str(e),
                    "raw": None,
                    "normalized": None,
                    "deviations": [],
                })
                print(f"FAIL ({e})")

            if i < len(MODELS) - 1:
                await asyncio.sleep(THROTTLE_DELAY)

    return results


# ---------------------------------------------------------------------------
# Deviation detection
# ---------------------------------------------------------------------------

def compute_deviations(raw: dict, normalized: dict) -> list[dict]:
    """Compare raw vs normalized, return list of deviation dicts."""
    devs: list[dict] = []
    raw_msg = raw["choices"][0]["message"]
    norm_msg = normalized["choices"][0]["message"]
    raw_usage = raw.get("usage", {})
    norm_usage = normalized.get("usage", {})

    # 1. Thinking: <think> tags in content
    raw_content = raw_msg.get("content", "")
    if "<think>" in raw_content:
        devs.append({
            "type": "thinking_tags",
            "label": "&lt;think&gt; tags in content",
            "desc": "Thinking mixed into message.content instead of message.thinking.content",
            "raw_path": "choices[0].message.content",
            "norm_fix": "Extracted to message.thinking.content, content cleaned",
        })

    # 2. Thinking: reasoning_content field
    if raw_msg.get("reasoning_content"):
        devs.append({
            "type": "reasoning_content",
            "label": "reasoning_content field",
            "desc": "Non-spec message.reasoning_content instead of message.thinking.content",
            "raw_path": "choices[0].message.reasoning_content",
            "norm_fix": "Moved to message.thinking.content, field removed",
        })

    # 3. Usage: prompt_tokens_details null
    if "prompt_tokens_details" in raw_usage and raw_usage["prompt_tokens_details"] is None:
        devs.append({
            "type": "null_field",
            "label": "prompt_tokens_details: null",
            "desc": "Null value instead of omitting the field",
            "raw_path": "usage.prompt_tokens_details",
            "norm_fix": "Field omitted",
        })

    # 4. Usage: reasoning_tokens at top level
    if "reasoning_tokens" in raw_usage:
        devs.append({
            "type": "usage_reasoning",
            "label": "usage.reasoning_tokens (top-level)",
            "desc": "reasoning_tokens at top-level usage instead of completion_tokens_details",
            "raw_path": "usage.reasoning_tokens",
            "norm_fix": "Moved to usage.completion_tokens_details.reasoning_tokens",
        })

    # 5. Non-spec fields at response level
    for key in raw:
        if key not in SPEC_RESPONSE_KEYS:
            devs.append({
                "type": "extra_field",
                "label": f"Non-spec field: {key}",
                "desc": f"Provider-specific field \"{key}\" at response level",
                "raw_path": key,
                "norm_fix": "Passed through (adapter preserves unknown fields)",
            })

    # 6. Non-spec fields at choice level
    for key in raw["choices"][0]:
        if key not in SPEC_CHOICE_KEYS:
            devs.append({
                "type": "extra_field",
                "label": f"Non-spec field: choices[].{key}",
                "desc": f"Provider-specific field \"{key}\" at choice level",
                "raw_path": f"choices[0].{key}",
                "norm_fix": "Passed through",
            })

    # 7. Non-spec fields at message level
    for key in raw_msg:
        if key not in SPEC_MESSAGE_KEYS:
            # reasoning_content already handled above
            if key == "reasoning_content":
                continue
            devs.append({
                "type": "extra_field",
                "label": f"Non-spec field: message.{key}",
                "desc": f"Provider-specific field \"{key}\" at message level",
                "raw_path": f"choices[0].message.{key}",
                "norm_fix": "Passed through",
            })

    return devs


# ---------------------------------------------------------------------------
# JSON rendering with diff highlights
# ---------------------------------------------------------------------------

def truncate_strings(obj: Any, max_len: int = 150) -> Any:
    if isinstance(obj, str) and len(obj) > max_len:
        return obj[:max_len] + f"... ({len(obj)} chars)"
    if isinstance(obj, dict):
        return {k: truncate_strings(v, max_len) for k, v in obj.items()}
    if isinstance(obj, list):
        return [truncate_strings(v, max_len) for v in obj]
    return obj


def json_to_html(
    obj: Any,
    highlight_paths: dict[str, str],
    path: str = "",
    indent: int = 0,
) -> str:
    """Render JSON as HTML with path-based highlighting.

    highlight_paths: {dotted_path: css_class} e.g. {"usage.prompt_tokens_details": "removed"}
    """
    pad = "  " * indent
    css = highlight_paths.get(path, "")
    open_tag = f'<span class="hl-{css}">' if css else ""
    close_tag = "</span>" if css else ""

    if obj is None:
        return f"{open_tag}<span class='json-null'>null</span>{close_tag}"
    if isinstance(obj, bool):
        return f"{open_tag}<span class='json-bool'>{str(obj).lower()}</span>{close_tag}"
    if isinstance(obj, (int, float)):
        return f"{open_tag}<span class='json-num'>{obj}</span>{close_tag}"
    if isinstance(obj, str):
        escaped = html.escape(json.dumps(obj))
        return f"{open_tag}<span class='json-str'>{escaped}</span>{close_tag}"
    if isinstance(obj, list):
        if not obj:
            return f"{open_tag}[]{close_tag}"
        items = []
        for i, v in enumerate(obj):
            child_path = f"{path}.{i}" if path else str(i)
            rendered = json_to_html(v, highlight_paths, child_path, indent + 1)
            items.append(f"\n{pad}  {rendered}")
        return f"{open_tag}[{',' .join(items)}\n{pad}]{close_tag}"
    if isinstance(obj, dict):
        if not obj:
            return f"{open_tag}{{}}{close_tag}"
        entries = []
        for k, v in obj.items():
            child_path = f"{path}.{k}" if path else k
            key_css = highlight_paths.get(child_path, "")
            key_open = f'<span class="hl-{key_css}">' if key_css else ""
            key_close = "</span>" if key_css else ""
            rendered_val = json_to_html(v, highlight_paths, child_path, indent + 1)
            key_html = f"<span class='json-key'>\"{html.escape(k)}\"</span>"
            entries.append(f"\n{pad}  {key_open}{key_html}: {rendered_val}{key_close}")
        return f"{{{','.join(entries)}\n{pad}}}"
    return html.escape(str(obj))


def build_highlight_paths(raw: dict, deviations: list[dict]) -> tuple[dict, dict]:
    """Build highlight path dicts for raw and normalized panels."""
    raw_hl: dict[str, str] = {}
    norm_hl: dict[str, str] = {}

    for dev in deviations:
        rp = dev["raw_path"]
        if dev["type"] == "thinking_tags":
            raw_hl[f"choices.0.message.content"] = "removed"
            norm_hl["choices.0.message.content"] = "added"
            norm_hl["choices.0.message.thinking"] = "added"
            norm_hl["choices.0.message.thinking.content"] = "added"
        elif dev["type"] == "reasoning_content":
            raw_hl["choices.0.message.reasoning_content"] = "removed"
            norm_hl["choices.0.message.thinking"] = "added"
            norm_hl["choices.0.message.thinking.content"] = "added"
        elif dev["type"] == "null_field":
            raw_hl[rp.replace("[0]", ".0")] = "removed"
        elif dev["type"] == "usage_reasoning":
            raw_hl["usage.reasoning_tokens"] = "removed"
            norm_hl["usage.completion_tokens_details"] = "added"
            norm_hl["usage.completion_tokens_details.reasoning_tokens"] = "added"
        elif dev["type"] == "extra_field":
            raw_hl[rp.replace("[0]", ".0")] = "extra"

    return raw_hl, norm_hl


# ---------------------------------------------------------------------------
# HTML generation
# ---------------------------------------------------------------------------

def deviation_badge(dev: dict) -> str:
    badge_colors = {
        "thinking_tags": ("#dc3545", "THINKING"),
        "reasoning_content": ("#dc3545", "THINKING"),
        "null_field": ("#fd7e14", "NULL"),
        "usage_reasoning": ("#6f42c1", "USAGE"),
        "extra_field": ("#6c757d", "EXTRA"),
    }
    color, label = badge_colors.get(dev["type"], ("#6c757d", "OTHER"))
    return (
        f'<span class="badge" style="background:{color}">{label}</span> '
        f'{dev["label"]}'
    )


def model_card_html(result: dict) -> str:
    if result["status"] == "error":
        return f"""
        <div class="model-card error">
          <div class="model-header">
            <h3>{html.escape(result['short'])}</h3>
            <span class="status-badge error">ERROR</span>
          </div>
          <p class="error-msg">{html.escape(result['error'][:200])}</p>
        </div>"""

    raw = result["raw"]
    normalized = result["normalized"]
    deviations = result["deviations"]
    raw_hl, norm_hl = build_highlight_paths(raw, deviations)

    raw_display = truncate_strings(raw)
    norm_display = truncate_strings(normalized)

    raw_json_html = json_to_html(raw_display, raw_hl)
    norm_json_html = json_to_html(norm_display, norm_hl)

    # Categorize deviations
    adapter_fixed = [d for d in deviations if d["type"] not in ("extra_field",)]
    extra_fields = [d for d in deviations if d["type"] == "extra_field"]

    fixed_count = len(adapter_fixed)
    extra_count = len(extra_fields)
    total = len(deviations)

    # Deviation list HTML
    dev_items = ""
    for d in deviations:
        badge = deviation_badge(d)
        fix_class = "fix-applied" if d["type"] not in ("extra_field",) else "fix-passthrough"
        arrow = "&#8594;" if d["type"] not in ("extra_field",) else ""
        fix_text = d["norm_fix"] if d["type"] not in ("extra_field",) else d["norm_fix"]
        dev_items += f"""
            <div class="dev-item {fix_class}">
              <div class="dev-label">{badge}</div>
              <div class="dev-arrow">{arrow}</div>
              <div class="dev-fix">{html.escape(fix_text)}</div>
            </div>"""

    return f"""
    <div class="model-card" id="{html.escape(result['short'])}">
      <div class="model-header">
        <h3>{html.escape(result['model'])}</h3>
        <div class="header-badges">
          <span class="status-badge ok">OK</span>
          <span class="count-badge fixed">{fixed_count} fixed</span>
          <span class="count-badge extra">{extra_count} extra fields</span>
        </div>
      </div>

      <div class="deviations">
        <h4>Deviations Found ({total})</h4>
        {dev_items}
      </div>

      <div class="panels">
        <div class="panel raw">
          <div class="panel-label">Raw Nvidia Response</div>
          <pre><code>{raw_json_html}</code></pre>
        </div>
        <div class="panel normalized">
          <div class="panel-label">Adapter-Normalized</div>
          <pre><code>{norm_json_html}</code></pre>
        </div>
      </div>
    </div>"""


def generate_html(results: list[dict]) -> str:
    ok_count = sum(1 for r in results if r["status"] == "ok")
    err_count = sum(1 for r in results if r["status"] == "error")
    all_devs = []
    for r in results:
        if r["deviations"]:
            all_devs.extend(r["deviations"])
    fixed_total = sum(1 for d in all_devs if d["type"] not in ("extra_field",))
    extra_total = sum(1 for d in all_devs if d["type"] == "extra_field")

    # Summary table rows
    summary_rows = ""
    for r in results:
        if r["status"] == "error":
            summary_rows += f"""
            <tr class="summary-error">
              <td>{html.escape(r['short'])}</td>
              <td><span class="status-badge error">ERROR</span></td>
              <td>-</td><td>-</td><td>-</td>
            </tr>"""
            continue

        devs = r["deviations"]
        fixed = [d for d in devs if d["type"] not in ("extra_field",)]
        extras = [d for d in devs if d["type"] == "extra_field"]
        types = set()
        for d in fixed:
            if d["type"] in ("thinking_tags", "reasoning_content"):
                types.add("thinking")
            elif d["type"] == "null_field":
                types.add("null cleanup")
            elif d["type"] == "usage_reasoning":
                types.add("usage")
        type_str = ", ".join(sorted(types)) if types else "-"

        summary_rows += f"""
            <tr>
              <td><a href="#{html.escape(r['short'])}">{html.escape(r['short'])}</a></td>
              <td><span class="status-badge ok">OK</span></td>
              <td>{len(fixed)}</td>
              <td>{len(extras)}</td>
              <td>{type_str}</td>
            </tr>"""

    # Model cards
    cards = "\n".join(model_card_html(r) for r in results)
    now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Open Layer v0.1 — Adapter Conformance Report</title>
<style>
  :root {{
    --bg: #0d1117;
    --surface: #161b22;
    --border: #30363d;
    --text: #e6edf3;
    --text-dim: #8b949e;
    --red: #f85149;
    --red-bg: rgba(248,81,73,0.15);
    --green: #3fb950;
    --green-bg: rgba(63,185,80,0.15);
    --orange: #d29922;
    --orange-bg: rgba(210,153,34,0.15);
    --purple: #bc8cff;
    --blue: #58a6ff;
  }}

  * {{ margin: 0; padding: 0; box-sizing: border-box; }}

  body {{
    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Helvetica, Arial, sans-serif;
    background: var(--bg);
    color: var(--text);
    line-height: 1.5;
  }}

  .container {{ max-width: 1400px; margin: 0 auto; padding: 24px; }}

  header {{
    border-bottom: 1px solid var(--border);
    padding-bottom: 24px;
    margin-bottom: 32px;
  }}
  header h1 {{
    font-size: 28px;
    font-weight: 600;
    margin-bottom: 8px;
  }}
  header p {{ color: var(--text-dim); font-size: 14px; }}

  /* Stats row */
  .stats {{
    display: flex;
    gap: 16px;
    margin-bottom: 32px;
    flex-wrap: wrap;
  }}
  .stat-card {{
    background: var(--surface);
    border: 1px solid var(--border);
    border-radius: 8px;
    padding: 16px 24px;
    flex: 1;
    min-width: 140px;
  }}
  .stat-card .stat-value {{
    font-size: 32px;
    font-weight: 700;
  }}
  .stat-card .stat-label {{
    font-size: 12px;
    color: var(--text-dim);
    text-transform: uppercase;
    letter-spacing: 0.5px;
  }}
  .stat-card.green .stat-value {{ color: var(--green); }}
  .stat-card.red .stat-value {{ color: var(--red); }}
  .stat-card.orange .stat-value {{ color: var(--orange); }}
  .stat-card.purple .stat-value {{ color: var(--purple); }}

  /* Summary table */
  .summary-section {{ margin-bottom: 40px; }}
  .summary-section h2 {{
    font-size: 20px;
    margin-bottom: 16px;
    padding-bottom: 8px;
    border-bottom: 1px solid var(--border);
  }}
  table {{
    width: 100%;
    border-collapse: collapse;
    background: var(--surface);
    border-radius: 8px;
    overflow: hidden;
  }}
  th, td {{
    padding: 10px 16px;
    text-align: left;
    border-bottom: 1px solid var(--border);
    font-size: 14px;
  }}
  th {{
    background: rgba(255,255,255,0.05);
    font-weight: 600;
    font-size: 12px;
    text-transform: uppercase;
    letter-spacing: 0.5px;
    color: var(--text-dim);
  }}
  td a {{ color: var(--blue); text-decoration: none; }}
  td a:hover {{ text-decoration: underline; }}
  .summary-error td {{ opacity: 0.5; }}

  /* Badges */
  .badge {{
    display: inline-block;
    font-size: 10px;
    font-weight: 700;
    padding: 2px 8px;
    border-radius: 10px;
    color: #fff;
    text-transform: uppercase;
    letter-spacing: 0.5px;
    vertical-align: middle;
  }}
  .status-badge {{
    display: inline-block;
    font-size: 11px;
    font-weight: 600;
    padding: 2px 10px;
    border-radius: 10px;
  }}
  .status-badge.ok {{ background: rgba(63,185,80,0.2); color: var(--green); }}
  .status-badge.error {{ background: rgba(248,81,73,0.2); color: var(--red); }}
  .count-badge {{
    display: inline-block;
    font-size: 11px;
    padding: 2px 10px;
    border-radius: 10px;
    margin-left: 6px;
  }}
  .count-badge.fixed {{ background: rgba(63,185,80,0.2); color: var(--green); }}
  .count-badge.extra {{ background: rgba(139,148,158,0.2); color: var(--text-dim); }}

  /* Model cards */
  .model-card {{
    background: var(--surface);
    border: 1px solid var(--border);
    border-radius: 12px;
    margin-bottom: 24px;
    overflow: hidden;
  }}
  .model-card.error {{
    opacity: 0.6;
  }}
  .model-header {{
    display: flex;
    justify-content: space-between;
    align-items: center;
    padding: 16px 20px;
    border-bottom: 1px solid var(--border);
    flex-wrap: wrap;
    gap: 8px;
  }}
  .model-header h3 {{
    font-size: 16px;
    font-weight: 600;
    font-family: 'SF Mono', 'Fira Code', monospace;
  }}
  .header-badges {{ display: flex; align-items: center; }}
  .error-msg {{
    padding: 16px 20px;
    color: var(--red);
    font-family: monospace;
    font-size: 13px;
  }}

  /* Deviations */
  .deviations {{
    padding: 16px 20px;
    border-bottom: 1px solid var(--border);
  }}
  .deviations h4 {{
    font-size: 13px;
    color: var(--text-dim);
    text-transform: uppercase;
    letter-spacing: 0.5px;
    margin-bottom: 10px;
  }}
  .dev-item {{
    display: flex;
    align-items: center;
    gap: 12px;
    padding: 6px 0;
    font-size: 13px;
  }}
  .dev-label {{ flex: 0 0 auto; min-width: 280px; }}
  .dev-arrow {{ color: var(--text-dim); flex: 0 0 20px; text-align: center; }}
  .dev-fix {{ color: var(--text-dim); }}
  .dev-item.fix-applied .dev-fix {{ color: var(--green); }}

  /* Side-by-side panels */
  .panels {{
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: 0;
  }}
  .panel {{
    overflow-x: auto;
  }}
  .panel-label {{
    font-size: 11px;
    font-weight: 700;
    text-transform: uppercase;
    letter-spacing: 1px;
    padding: 10px 16px;
    border-bottom: 1px solid var(--border);
  }}
  .panel.raw .panel-label {{
    color: var(--red);
    background: var(--red-bg);
  }}
  .panel.normalized .panel-label {{
    color: var(--green);
    background: var(--green-bg);
  }}
  .panel.raw {{
    border-right: 1px solid var(--border);
  }}
  .panel pre {{
    margin: 0;
    padding: 16px;
    font-family: 'SF Mono', 'Fira Code', 'Cascadia Code', monospace;
    font-size: 12px;
    line-height: 1.6;
    overflow-x: auto;
    white-space: pre;
  }}
  .panel pre code {{
    font-family: inherit;
  }}

  /* JSON syntax */
  .json-key {{ color: var(--blue); }}
  .json-str {{ color: #a5d6ff; }}
  .json-num {{ color: #79c0ff; }}
  .json-null {{ color: var(--text-dim); font-style: italic; }}
  .json-bool {{ color: var(--orange); }}

  /* Diff highlights */
  .hl-removed {{
    background: var(--red-bg);
    border-left: 3px solid var(--red);
    padding-left: 4px;
    display: inline;
  }}
  .hl-added {{
    background: var(--green-bg);
    border-left: 3px solid var(--green);
    padding-left: 4px;
    display: inline;
  }}
  .hl-extra {{
    background: rgba(139,148,158,0.1);
    border-left: 3px solid var(--text-dim);
    padding-left: 4px;
    display: inline;
  }}

  /* Footer */
  footer {{
    margin-top: 40px;
    padding-top: 20px;
    border-top: 1px solid var(--border);
    color: var(--text-dim);
    font-size: 13px;
    text-align: center;
  }}

  /* Responsive */
  @media (max-width: 900px) {{
    .panels {{ grid-template-columns: 1fr; }}
    .panel.raw {{ border-right: none; border-bottom: 1px solid var(--border); }}
    .dev-item {{ flex-wrap: wrap; }}
    .dev-label {{ min-width: auto; }}
  }}
</style>
</head>
<body>
<div class="container">

<header>
  <h1>Open Layer v0.1 &mdash; Adapter Conformance Report</h1>
  <p>
    Raw Nvidia NIM API responses vs. NvidiaAdapter-normalized output &middot;
    {len(MODELS)} models &middot; Generated {now}
  </p>
  <p>Prompt: <code>{html.escape(PROMPT)}</code></p>
</header>

<div class="stats">
  <div class="stat-card green">
    <div class="stat-value">{ok_count}</div>
    <div class="stat-label">Models OK</div>
  </div>
  <div class="stat-card red">
    <div class="stat-value">{err_count}</div>
    <div class="stat-label">Errors</div>
  </div>
  <div class="stat-card orange">
    <div class="stat-value">{fixed_total}</div>
    <div class="stat-label">Deviations Fixed</div>
  </div>
  <div class="stat-card purple">
    <div class="stat-value">{extra_total}</div>
    <div class="stat-label">Extra Fields Detected</div>
  </div>
</div>

<div class="summary-section">
  <h2>Summary</h2>
  <table>
    <thead>
      <tr>
        <th>Model</th>
        <th>Status</th>
        <th>Fixed</th>
        <th>Extra Fields</th>
        <th>Deviation Types</th>
      </tr>
    </thead>
    <tbody>
      {summary_rows}
    </tbody>
  </table>
</div>

<h2 style="margin-bottom:20px;font-size:20px;padding-bottom:8px;border-bottom:1px solid var(--border)">
  Per-Model Details
</h2>

{cards}

<footer>
  Open Layer v0.1 &middot; Adapter: NvidiaAdapter &middot; Provider: Nvidia NIM &middot;
  <a href="https://github.com/adityonugrohoid/open-layer" style="color:var(--blue)">GitHub</a>
</footer>

</div>
</body>
</html>"""


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

async def main() -> None:
    print("Collecting responses from 12 models...")
    results = await collect_all()

    print("\nGenerating HTML report...")
    html_content = generate_html(results)

    out_dir = os.path.join(os.path.dirname(__file__), "..", "docs")
    os.makedirs(out_dir, exist_ok=True)
    out_path = os.path.join(out_dir, "ab-report.html")
    with open(out_path, "w") as f:
        f.write(html_content)

    abs_path = os.path.abspath(out_path)
    print(f"\nReport saved to: {abs_path}")
    print(f"Open in browser: file://{abs_path}")


if __name__ == "__main__":
    asyncio.run(main())

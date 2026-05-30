#!/usr/bin/env python3
"""
Restaurant location viability agent.

Usage:
    python agent.py <input.md>     # parse → score → LLM → writes report.md
    python agent.py --mock         # parse + score sample_input.md, print signals, no API call
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
from pathlib import Path

from scoring import compute_signals
from prompts import SYSTEM_PROMPT


# ── Unicode normalisation ─────────────────────────────────────────────────────

def _normalize_str(s: str) -> str:
    return (
        s.replace(" ", " ")   # narrow no-break space → regular space
         .replace("ç", "ç")   # already ç, but round-trip safe
         .replace("’", "'")   # right single quotation mark
         .replace("‘", "'")   # left single quotation mark
    )


def _normalize_obj(obj):
    """Recursively normalize unicode in parsed JSON structures."""
    if isinstance(obj, str):
        return _normalize_str(obj)
    if isinstance(obj, dict):
        return {k: _normalize_obj(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_normalize_obj(item) for item in obj]
    return obj


# ── Markdown parsing ──────────────────────────────────────────────────────────

def _extract_json_blocks(md_text: str) -> list:
    """Return all successfully parsed objects/arrays from ```json … ``` fences."""
    blocks = []
    for m in re.finditer(r"```json\s*([\s\S]*?)\s*```", md_text, re.IGNORECASE):
        try:
            blocks.append(json.loads(m.group(1)))
        except json.JSONDecodeError:
            pass  # skip malformed blocks
    return blocks


def _identify_blocks(blocks: list) -> tuple[dict | None, list | None, list | None]:
    """
    Heuristically identify user_request, traffic_data, competitors from parsed blocks.
    Identification is by structure, not position — order in the file does not matter.
    """
    user_request = traffic_data = competitors = None

    for block in blocks:
        if isinstance(block, dict):
            # User request: has address + day_of_the_week keys
            if "address" in block and "day_of_the_week" in block:
                user_request = block
        elif isinstance(block, list) and block and isinstance(block[0], dict):
            first = block[0]
            if "hour" in first or "speed_summary" in first:
                traffic_data = block
            elif any(k in first for k in ("title", "totalScore", "reviewsCount")):
                competitors = block

    return user_request, traffic_data, competitors


def _load_and_parse(md_path: Path) -> tuple[dict, list, list]:
    """
    Read the markdown file, extract JSON blocks, normalise unicode,
    and return (user_request, traffic_data, competitors).
    Raises ValueError if the user-request block is missing.
    """
    md_text = md_path.read_text(encoding="utf-8")
    raw_blocks = _extract_json_blocks(md_text)
    blocks = [_normalize_obj(b) for b in raw_blocks]

    user_request, traffic_data, competitors = _identify_blocks(blocks)

    if user_request is None:
        raise ValueError(
            f"No user-request block found in {md_path}. "
            "Expected a JSON object with 'address' and 'day_of_the_week' keys."
        )

    return user_request, traffic_data or [], competitors or []


# ── LLM call (isolated — swap provider here) ─────────────────────────────────

def call_llm(system_prompt: str, user_message: str) -> str:
    """
    Call the Anthropic API with the given prompts and return the assistant text.
    Swap provider by replacing this function's body only.
    """
    try:
        import anthropic
    except ImportError:
        sys.exit("anthropic package not installed. Run: pip install anthropic")

    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        sys.exit("ANTHROPIC_API_KEY environment variable is not set.")

    client = anthropic.Anthropic(api_key=api_key)
    response = client.messages.create(
        model="claude-sonnet-4-5",
        max_tokens=4096,
        system=system_prompt,
        messages=[{"role": "user", "content": user_message}],
    )
    return response.content[0].text


# ── Public entry point ────────────────────────────────────────────────────────

def generate_report(input_md_path: str) -> str:
    """
    Full pipeline: parse → compute signals → LLM → write report.
    Returns the path to the written report.md.
    """
    md_path = Path(input_md_path)
    user_request, traffic_data, competitors = _load_and_parse(md_path)

    signals = compute_signals(user_request, traffic_data, competitors)

    user_message = json.dumps(
        {"user_request": user_request, "signals": signals},
        indent=2,
        ensure_ascii=False,
    )

    report_md = call_llm(SYSTEM_PROMPT, user_message)

    output_path = md_path.parent / "report.md"
    output_path.write_text(report_md, encoding="utf-8")
    return str(output_path)


# ── CLI ───────────────────────────────────────────────────────────────────────

def main() -> None:
    parser = argparse.ArgumentParser(
        description="Restaurant location viability agent",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "Examples:\n"
            "  python agent.py sample_input.md       # full run\n"
            "  python agent.py --mock                # scoring only, no API call\n"
        ),
    )
    parser.add_argument("input", nargs="?", help="Path to input markdown file")
    parser.add_argument(
        "--mock",
        action="store_true",
        help="Parse + score sample_input.md without calling the API; prints signals as JSON",
    )
    args = parser.parse_args()

    if args.mock:
        sample = Path(__file__).parent / "sample_input.md"
        if not sample.exists():
            sys.exit(f"sample_input.md not found at {sample}")
        user_request, traffic_data, competitors = _load_and_parse(sample)
        signals = compute_signals(user_request, traffic_data, competitors)
        print(json.dumps(signals, indent=2, ensure_ascii=False))
        return

    if not args.input:
        parser.error("Provide an input .md file path, or use --mock")

    output_path = generate_report(args.input)
    print(f"Report written to: {output_path}")


if __name__ == "__main__":
    main()

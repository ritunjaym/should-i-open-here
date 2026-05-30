#!/usr/bin/env python3
"""
Restaurant location viability agent.

Usage:
    python agent.py <input.json> --address ADDR --day DAY --open HH:MM --close HH:MM --search TERM
    python agent.py --mock      # score sample_input.json with demo args, no API call
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


# ── Traffic timestamp parsing ─────────────────────────────────────────────────

def _parse_traffic_timestamp(ts: str) -> int | None:
    """
    Parse a datetime string like '2026-05-30 11:00 AM PDT' → integer hour (0–23).
    Also handles '2026-05-30 13:00 PDT' (24h) and bare 'HH:MM AM/PM'.
    """
    s = ts.strip()
    # 24-hour: 'YYYY-MM-DD HH:MM ...' where HH >= 10 (no AM/PM needed)
    m = re.search(r"\b(\d{2}):(\d{2})\b(?!\s*[AP]M)", s, re.IGNORECASE)
    if m and int(m.group(1)) >= 10:   # avoid matching 10:00 AM as 24h
        pass  # fall through to AM/PM check first
    # AM/PM form: '11:00 AM', '1:00 PM', '12:30 AM'
    m = re.search(r"(\d{1,2}):(\d{2})\s*(AM|PM)", s, re.IGNORECASE)
    if m:
        h = int(m.group(1))
        period = m.group(3).upper()
        if period == "PM" and h != 12:
            h += 12
        elif period == "AM" and h == 12:
            h = 0
        return h
    # 24-hour fallback: 'YYYY-MM-DD HH:MM'
    m = re.search(r"\b(\d{2}):(\d{2})\b", s)
    if m:
        return int(m.group(1))
    return None


def _normalize_traffic(aggregated_traffic: dict) -> list:
    """
    Convert the aggregated_traffic dict ('2026-05-30 11:00 AM PDT' → {…counts…})
    into the list-of-{hour, speed_summary} form that scoring.py expects.
    Duplicate hours are last-write-wins.
    """
    by_hour: dict[int, dict] = {}
    for ts, summary in aggregated_traffic.items():
        if not isinstance(summary, dict):
            continue
        hour = _parse_traffic_timestamp(str(ts))
        if hour is not None:
            by_hour[hour] = summary
    return [{"hour": h, "speed_summary": s} for h, s in sorted(by_hour.items())]


# ── JSON file parsing ─────────────────────────────────────────────────────────

def _load_and_parse(
    json_path: Path, user_request: dict
) -> tuple[dict, list, list]:
    """
    Read the JSON input file, extract google_maps_places and aggregated_traffic,
    normalise unicode, and return (user_request, traffic_data, competitors).
    """
    raw = json.loads(json_path.read_text(encoding="utf-8"))
    data = _normalize_obj(raw)

    competitors = data.get("google_maps_places", [])
    if not isinstance(competitors, list):
        competitors = []

    traffic_raw = data.get("aggregated_traffic", {})
    if not isinstance(traffic_raw, dict):
        traffic_raw = {}
    traffic_data = _normalize_traffic(traffic_raw)

    return user_request, traffic_data, competitors


def _build_user_request(args: argparse.Namespace) -> dict:
    return {
        "address": args.address,
        "day_of_the_week": args.day,
        "opening_time": args.open,
        "closing_time": args.close,
        "search_term": args.search,
    }


# ── LLM call (isolated — swap provider here) ─────────────────────────────────

def call_llm(system_prompt: str, user_message: str) -> str:
    """
    Call the Anthropic API and return the assistant text.
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

def generate_report(json_path: str, user_request: dict) -> str:
    """
    Full pipeline: parse JSON → compute signals → LLM → write report.md.
    Returns the path to the written report.
    """
    path = Path(json_path)
    ur, traffic_data, competitors = _load_and_parse(path, user_request)

    signals = compute_signals(ur, traffic_data, competitors)

    user_message = json.dumps(
        {"user_request": ur, "signals": signals},
        indent=2,
        ensure_ascii=False,
    )

    report_md = call_llm(SYSTEM_PROMPT, user_message)

    output_path = path.parent / "report.md"
    output_path.write_text(report_md, encoding="utf-8")
    return str(output_path)


# ── CLI ───────────────────────────────────────────────────────────────────────

_MOCK_DEFAULTS = {
    "address": "411 15th Ave E, Seattle, WA 98112",
    "day": "Saturday",
    "open": "11:00",
    "close": "23:00",
    "search": "vegan restaurant",
}


def _add_location_args(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--address", help="Street address of the candidate location")
    parser.add_argument("--day",     help="Day of the week (e.g. Saturday)")
    parser.add_argument("--open",    dest="open",  help="Opening time in HH:MM (24h)")
    parser.add_argument("--close",   dest="close", help="Closing time in HH:MM (24h)")
    parser.add_argument("--search",  help='Search term (e.g. "vegan restaurant")')


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Restaurant location viability agent",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "Examples:\n"
            '  python agent.py real_input.json --address "411 15th Ave E, Seattle, WA 98112" \\\n'
            "    --day Saturday --open 11:00 --close 23:00 --search \"vegan restaurant\"\n"
            "  python agent.py --mock\n"
        ),
    )
    parser.add_argument("input", nargs="?", help="Path to input JSON file")
    parser.add_argument(
        "--mock",
        action="store_true",
        help=(
            "Parse + score sample_input.json with demo location args; "
            "prints signals as JSON without calling the API"
        ),
    )
    _add_location_args(parser)
    args = parser.parse_args()

    if args.mock:
        sample = Path(__file__).parent / "sample_input.json"
        if not sample.exists():
            sys.exit(f"sample_input.json not found at {sample}")
        # Fill unset args with mock defaults
        for field, default in _MOCK_DEFAULTS.items():
            if getattr(args, field, None) is None:
                setattr(args, field, default)
        user_request = _build_user_request(args)
        _, traffic_data, competitors = _load_and_parse(sample, user_request)
        signals = compute_signals(user_request, traffic_data, competitors)
        print(json.dumps(signals, indent=2, ensure_ascii=False))
        return

    if not args.input:
        parser.error("Provide an input JSON file path, or use --mock")

    missing = [f"--{f}" for f in ("address", "day", "open", "close", "search")
               if not getattr(args, f.replace("-", "_"), None)]
    if missing:
        parser.error(f"The following args are required: {', '.join(missing)}")

    user_request = _build_user_request(args)
    output_path = generate_report(args.input, user_request)
    print(f"Report written to: {output_path}")


if __name__ == "__main__":
    main()

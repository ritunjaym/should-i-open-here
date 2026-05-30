"""
Bridge between Person C's backend and Person B's agent.

Person B's agent expects a markdown file with three JSON fences.
This module converts the scraper dict → temp markdown file → calls agent → returns report.
"""
import json
import sys
import os
import tempfile
from pathlib import Path

# Person B's agent lives one level up
sys.path.insert(0, str(Path(__file__).parent.parent))
from agent import call_llm, _load_and_parse, compute_signals
from prompts import SYSTEM_PROMPT
from scoring import compute_signals


async def generate(scrape_data: dict) -> str:
    """
    Convert scraper dict to Person B's markdown format,
    run through their scoring + LLM pipeline, return report markdown.
    """
    import asyncio
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(None, _generate_sync, scrape_data)


def _generate_sync(scrape_data: dict) -> str:
    # Build the markdown input Person B's agent expects
    user_request = {
        "address": scrape_data.get("location", ""),
        "day_of_the_week": scrape_data.get("day_of_week", "Saturday"),
        "opening_time": scrape_data.get("opening_time", "09:00"),
        "closing_time": scrape_data.get("closing_time", "22:00"),
        "search_term": scrape_data.get("business_type", ""),
    }

    # Convert competitors to Person B's schema
    competitors = [
        {
            "title": c.get("name", "Unknown"),
            "totalScore": c.get("rating", 0),
            "reviewsCount": c.get("review_count", 0),
            "categories": [scrape_data.get("business_type", "")],
            "openingHours": [],
            "rank": i + 1,
        }
        for i, c in enumerate(scrape_data.get("competitors", []))
    ]

    # Use real hourly traffic if available (from scraper_real), else fall back to proxy
    if scrape_data.get("hourly_traffic"):
        traffic_data = scrape_data["hourly_traffic"]
    else:
        traffic_map = {"low": 20, "moderate": 40, "high": 65, "very high": 85}
        free_flow = traffic_map.get(scrape_data.get("foot_traffic", "moderate"), 40)
        traffic_data = [
            {"hour": h, "speed_summary": {"Free Flow": free_flow, "Slow Traffic": 100 - free_flow}}
            for h in range(9, 23)
        ]

    # Write to temp markdown file and call Person B's pipeline
    md_content = f"""# Location Analysis Input

## User Request

```json
{json.dumps(user_request, indent=2)}
```

## Hourly Traffic Data

```json
{json.dumps(traffic_data, indent=2)}
```

## Competitors

```json
{json.dumps(competitors, indent=2)}
```
"""

    with tempfile.NamedTemporaryFile(
        mode="w", suffix=".md", delete=False, encoding="utf-8"
    ) as f:
        f.write(md_content)
        tmp_path = f.name

    try:
        user_req, traffic, comps = _load_and_parse(Path(tmp_path))
        signals = compute_signals(user_req, traffic, comps)
        user_message = json.dumps(
            {"user_request": user_req, "signals": signals},
            indent=2,
            ensure_ascii=False,
        )
        return call_llm(SYSTEM_PROMPT, user_message)
    finally:
        os.unlink(tmp_path)

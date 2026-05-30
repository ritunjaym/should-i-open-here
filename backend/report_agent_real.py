"""
Bridge between Person C's backend and Person B's updated agent.

New agent.py interface (as of latest commit):
  generate_report(json_path: str, user_request: dict) -> str  # returns path to report.md

Input JSON must match Apify's output format:
  {
    "google_maps_places": [ {title, totalScore, reviewsCount, categories, openingHours, ...} ],
    "aggregated_traffic":  { "<timestamp>": {Free Flow, Slow Traffic, ...}, ... }
  }
"""
from __future__ import annotations

import asyncio
import json
import os
import sys
import tempfile
from datetime import datetime
from pathlib import Path
# Parse .env directly and inject into os.environ before importing agent
_env_path = Path(__file__).parent / ".env"
if _env_path.exists():
    for _line in _env_path.read_text(encoding="utf-8").splitlines():
        _line = _line.strip()
        if _line and not _line.startswith("#") and "=" in _line:
            _k, _v = _line.split("=", 1)
            os.environ[_k.strip()] = _v.strip()

# Person B's agent lives one level up from backend/
sys.path.insert(0, str(Path(__file__).parent.parent))
from agent import generate_report as _agent_generate_report  # noqa: E402


async def generate(scrape_data: dict) -> str:
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(None, _generate_sync, scrape_data)


def _generate_sync(scrape_data: dict) -> str:
    user_request = {
        "address":        scrape_data.get("location", ""),
        "day_of_the_week": scrape_data.get("day_of_week", "Saturday"),
        "opening_time":   scrape_data.get("opening_time", "09:00"),
        "closing_time":   scrape_data.get("closing_time", "22:00"),
        "search_term":    scrape_data.get("business_type", ""),
    }

    # ── Build google_maps_places in Apify schema ──────────────────────────────
    # scraper_real returns the full Apify places list under "raw_places";
    # scraper mock returns competitors in the simplified schema — handle both.
    raw_places = scrape_data.get("raw_places")
    if raw_places:
        google_maps_places = raw_places
    else:
        google_maps_places = [
            {
                "rank":         i + 1,
                "title":        c.get("name", "Unknown"),
                "address":      "",
                "totalScore":   c.get("rating", 0.0),
                "reviewsCount": c.get("review_count", 0),
                "categories":   c.get("categories") or [scrape_data.get("business_type", "")],
                "openingHours": c.get("openingHours") or [],
            }
            for i, c in enumerate(scrape_data.get("competitors", []))
        ]

    # ── Build aggregated_traffic in Apify schema ──────────────────────────────
    # scraper_real stores real hourly traffic under "hourly_traffic";
    # convert list[{hour, speed_summary}] → {"YYYY-MM-DD HH:MM AM/PM": {…}}
    aggregated_traffic: dict = {}
    today = datetime.now().strftime("%Y-%m-%d")

    hourly = scrape_data.get("hourly_traffic") or []
    if hourly:
        for entry in hourly:
            h = entry.get("hour", 0)
            period = "AM" if h < 12 else "PM"
            display_h = h if h <= 12 else h - 12
            display_h = display_h or 12
            ts = f"{today} {display_h:02d}:00 {period}"
            aggregated_traffic[ts] = entry.get("speed_summary", {})
    else:
        # Fall back: synthesise from the foot_traffic string
        traffic_map = {"low": 20, "moderate": 40, "high": 65, "very high": 85}
        free_flow = traffic_map.get(scrape_data.get("foot_traffic", "moderate"), 40)
        for h in range(9, 23):
            period = "AM" if h < 12 else "PM"
            display_h = h if h <= 12 else h - 12
            display_h = display_h or 12
            ts = f"{today} {display_h:02d}:00 {period}"
            aggregated_traffic[ts] = {
                "Free Flow": free_flow,
                "Slow Traffic": 100 - free_flow,
            }

    apify_json = {
        "google_maps_places": google_maps_places,
        "aggregated_traffic": aggregated_traffic,
    }

    # ── Write temp JSON file and call agent.generate_report ──────────────────
    with tempfile.NamedTemporaryFile(
        mode="w", suffix=".json", delete=False, encoding="utf-8"
    ) as f:
        json.dump(apify_json, f, indent=2, ensure_ascii=False)
        tmp_path = f.name

    try:
        report_path = _agent_generate_report(tmp_path, user_request)
        return Path(report_path).read_text(encoding="utf-8")
    finally:
        os.unlink(tmp_path)

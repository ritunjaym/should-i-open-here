"""
Real scraper — wraps Person A's apify_extraction.py logic as an async callable.

Converts Apify + geopy output → shared schema expected by scraper.py:
{
  "location": str,
  "business_type": str,
  "lat": float | None,
  "lng": float | None,
  "competitors": [{"name", "distance_m", "rating", "review_count"}],
  "foot_traffic": "low" | "moderate" | "high" | "very high",
  "nearby_pois": [str],
  "hourly_traffic": [{"hour": int, "speed_summary": {...}}],  # passthrough for agent
}
"""
from __future__ import annotations

import asyncio
import os
import sys
from datetime import datetime, time, timedelta
from pathlib import Path
from typing import Optional

from apify_client import ApifyClient
from geopy.geocoders import Nominatim
from timezonefinder import TimezoneFinder
import pytz

# Person B's agent lives one level up from backend/
sys.path.insert(0, str(Path(__file__).parent.parent))

GOOGLE_MAPS_ACTOR = "nwua9Gu5YrADL7ZDj"
TRAFFIC_ACTOR = "qlLfzCYcQfFM9S5n1"

MAPS_KEYS = ["title", "address", "totalScore", "categories", "reviewsCount", "openingHours", "rank"]


def _classify_foot_traffic(hourly: list[dict]) -> str:
    """Convert real hourly traffic data to a foot_traffic string."""
    if not hourly:
        return "moderate"
    busyness_values = []
    for entry in hourly:
        s = entry.get("speed_summary", {})
        busy = s.get("Slow Traffic", 0) + s.get("Moderate Congestion", 0) + s.get("Heavy Congestion", 0)
        total = busy + s.get("Free Flow", 0)
        busyness_values.append(busy / total if total else 0)
    avg = sum(busyness_values) / len(busyness_values)
    if avg >= 0.6:
        return "very high"
    if avg >= 0.4:
        return "high"
    if avg >= 0.2:
        return "moderate"
    return "low"


def _scrape_sync(
    location: str,
    business_type: str,
    lat: Optional[float],
    lng: Optional[float],
    opening_time: str = "09:00",
    closing_time: str = "22:00",
) -> dict:
    api_key = os.environ["APIFY_API_KEY"]
    client = ApifyClient(api_key)

    # ── Google Maps competitors ───────────────────────────────────────────────
    run = client.actor(GOOGLE_MAPS_ACTOR).call(run_input={
        "searchStringsArray": [business_type],
        "locationQuery": location,
        "maxCrawledPlacesPerSearch": 10,
        "skipClosedPlaces": True,
        "reviewsStartDate": "2024-01-01",
    })

    raw_places = [item for item in client.dataset(run["defaultDatasetId"]).iterate_items()]
    filtered_places = [{k: item.get(k) for k in MAPS_KEYS} for item in raw_places]

    competitors = [
        {
            "name": p.get("title", "Unknown"),
            "distance_m": 0,        # Apify doesn't return distance directly
            "rating": p.get("totalScore") or 0.0,
            "review_count": p.get("reviewsCount") or 0,
        }
        for p in filtered_places
    ]

    nearby_pois = list({
        cat
        for p in filtered_places
        for cat in (p.get("categories") or [])
        if cat.lower() != business_type.lower()
    })[:10]

    # ── Geocode if not provided ───────────────────────────────────────────────
    if lat is None or lng is None:
        geolocator = Nominatim(user_agent="should_i_open_here")
        geo = geolocator.geocode(location)
        if geo:
            lat, lng = geo.latitude, geo.longitude

    # ── Hourly traffic ────────────────────────────────────────────────────────
    hourly_traffic: list[dict] = []

    if lat is not None and lng is not None:
        tf = TimezoneFinder()
        tz_name = tf.timezone_at(lng=lng, lat=lat) or "UTC"
        local_tz = pytz.timezone(tz_name)

        now_utc = datetime.now(pytz.utc)
        days_since_sunday = (now_utc.weekday() + 1) % 7
        sunday_start_utc = (now_utc - timedelta(days=days_since_sunday)).replace(
            hour=0, minute=0, second=0, microsecond=0
        )

        start_hour = int(opening_time.split(":")[0])
        end_hour = int(closing_time.split(":")[0])

        for hour in range(start_hour, end_hour + 1):
            naive_dt = datetime.combine(datetime.now().date(), time(hour=hour % 24))
            local_dt = local_tz.localize(naive_dt)
            utc_dt = local_dt.astimezone(pytz.utc)
            delta_seconds = int((utc_dt - sunday_start_utc).total_seconds())

            traffic_run = client.actor(TRAFFIC_ACTOR).call(run_input={
                "lat": str(lat),
                "lon": str(lng),
                "zoom": 17,
                "radius": 2,
                "seconds": delta_seconds,
            })

            speed_summaries = [
                item["metadata"]["speed_summary"]
                for item in client.dataset(traffic_run["defaultDatasetId"]).iterate_items()
                if "speed_summary" in item.get("metadata", {})
            ]

            merged: dict = {}
            for s in speed_summaries:
                for k, v in s.items():
                    merged[k] = merged.get(k, 0) + v

            hourly_traffic.append({"hour": hour, "speed_summary": merged})

    return {
        "location": location,
        "business_type": business_type,
        "lat": lat,
        "lng": lng,
        "competitors": competitors,
        "foot_traffic": _classify_foot_traffic(hourly_traffic),
        "nearby_pois": nearby_pois,
        "hourly_traffic": hourly_traffic,
    }


async def scrape(
    location: str,
    business_type: str,
    lat: Optional[float] = None,
    lng: Optional[float] = None,
    opening_time: str = "09:00",
    closing_time: str = "22:00",
) -> dict:
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(
        None, _scrape_sync, location, business_type, lat, lng, opening_time, closing_time
    )

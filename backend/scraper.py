"""
Person A's scraper interface.
The real implementation lives in scraper_real.py (Person A's code).
Until that lands, USE_MOCK=True returns deterministic fake data.
"""
import os
import asyncio
from typing import Optional

USE_MOCK = os.getenv("USE_MOCK_SCRAPER", "true").lower() == "true"

# ── Shared schema ──────────────────────────────────────────────────────────────
# This is the contract between Person A and Person C.
# Person A must return a dict that matches this shape.
#
# {
#   "location": str,
#   "business_type": str,
#   "competitors": [
#       {"name": str, "distance_m": int, "rating": float, "review_count": int}
#   ],
#   "foot_traffic": "low" | "moderate" | "high" | "very high",
#   "nearby_pois": [str],          # optional enrichment
#   "lat": float | None,
#   "lng": float | None,
# }


async def scrape_location(
    location: str,
    business_type: str,
    lat: Optional[float] = None,
    lng: Optional[float] = None,
) -> dict:
    if USE_MOCK:
        return _mock_scrape(location, business_type, lat, lng)

    # swap in Person A's real implementation
    from scraper_real import scrape as real_scrape  # noqa: PLC0415
    return await real_scrape(location, business_type, lat, lng)


def _mock_scrape(location, business_type, lat, lng) -> dict:
    return {
        "location": location,
        "business_type": business_type,
        "lat": lat,
        "lng": lng,
        "competitors": [
            {"name": "Starbucks", "distance_m": 200, "rating": 4.2, "review_count": 1840},
            {"name": "Café Ladro", "distance_m": 450, "rating": 4.5, "review_count": 320},
            {"name": "Victrola Coffee", "distance_m": 600, "rating": 4.7, "review_count": 980},
        ],
        "foot_traffic": "high",
        "nearby_pois": ["Seattle Central Library", "Pike Place Market", "Westlake Center"],
    }

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
    day_of_week: Optional[str] = None,
    opening_time: Optional[str] = None,
    closing_time: Optional[str] = None,
) -> dict:
    if USE_MOCK:
        data = _mock_scrape(location, business_type, lat, lng)
        # Stash optional fields so report_agent_real can use them
        if day_of_week:
            data["day_of_week"] = day_of_week
        if opening_time:
            data["opening_time"] = opening_time
        if closing_time:
            data["closing_time"] = closing_time
        return data

    from scraper_real import scrape as real_scrape  # noqa: PLC0415
    return await real_scrape(
        location, business_type, lat, lng,
        opening_time=opening_time or "09:00",
        closing_time=closing_time or "22:00",
    )


_CITY_POIS = {
    "seattle":       ["Pike Place Market", "Seattle Central Library", "Westlake Center"],
    "new york":      ["Times Square", "Central Park", "Grand Central Terminal"],
    "nyc":           ["Times Square", "Central Park", "Grand Central Terminal"],
    "atlanta":       ["Centennial Olympic Park", "Ponce City Market", "The BeltLine"],
    "san francisco": ["Union Square", "Fisherman's Wharf", "Ferry Building"],
    "austin":        ["Sixth Street", "Barton Springs", "South Congress Ave"],
    "chicago":       ["Millennium Park", "Navy Pier", "The Loop"],
    "los angeles":   ["Venice Beach", "Griffith Observatory", "Grand Central Market"],
    "miami":         ["South Beach", "Wynwood Walls", "Brickell City Centre"],
    "denver":        ["16th Street Mall", "RiNo Art District", "Union Station"],
    "boston":        ["Faneuil Hall", "Newbury Street", "Boston Common"],
    "nashville":     ["Broadway", "Gulch", "12 South"],
    "portland":      ["Powell's Books", "Pearl District", "Saturday Market"],
}

_COMPETITOR_TEMPLATES = {
    "coffee":        [("Blue Bottle Coffee", 4.4, 890), ("Stumptown Coffee", 4.6, 1240), ("Intelligentsia", 4.3, 540), ("Victrola Coffee", 4.7, 980)],
    "pizza":         [("Serious Pie", 4.5, 1820), ("Via Tribunali", 4.3, 760), ("Pagliacci Pizza", 4.2, 2100), ("Bizzarro Italian Café", 4.4, 430)],
    "burger":        [("Dick's Drive-In", 4.4, 3200), ("Lil Woody's", 4.5, 880), ("Uneeda Burger", 4.3, 640), ("Katsu Burger", 4.6, 1100)],
    "sushi":         [("Shiro's Sushi", 4.7, 1560), ("Japonessa", 4.3, 2400), ("Umi Sake House", 4.4, 1800), ("Taneda", 4.8, 320)],
    "ramen":         [("Tsukushinbo", 4.5, 940), ("Yoroshiku", 4.4, 760), ("Samurai Noodle", 4.2, 1300), ("Kamonegi", 4.7, 580)],
    "arabic":        [("Mamnoon", 4.6, 1200), ("Shawarma Press", 4.3, 870), ("Arabica Café", 4.4, 510), ("Falafel King", 4.1, 690)],
    "middle eastern":[("Mamnoon", 4.6, 1200), ("Shawarma Press", 4.3, 870), ("Arabica Café", 4.4, 510), ("Falafel King", 4.1, 690)],
    "mediterranean": [("Lola", 4.5, 1340), ("Mamnoon", 4.6, 1200), ("Olympia Pizza", 4.2, 980), ("Plaka Estiatorio", 4.4, 560)],
    "mexican":       [("Mezcaleria Oaxaca", 4.5, 1100), ("La Carta de Oaxaca", 4.4, 890), ("Fogón Cocina", 4.3, 730), ("Rancho Bravo", 4.1, 1500)],
    "thai":          [("Pestle Rock", 4.6, 920), ("Thai Ginger", 4.2, 1700), ("Isarn Thai", 4.5, 640), ("Noodle Boat", 4.3, 870)],
    "indian":        [("Poppy", 4.5, 1080), ("Roti Cuisine", 4.4, 760), ("Spice Waala", 4.6, 540), ("Nirmal's", 4.3, 890)],
    "vegan":         [("Plum Bistro", 4.6, 1400), ("Café Flora", 4.5, 2100), ("Wayward Vegan Café", 4.4, 980), ("No Bones Beach Club", 4.3, 1200)],
    "gym":           [("24 Hour Fitness", 3.8, 540), ("LA Fitness", 3.9, 720), ("CrossFit Seattle", 4.5, 380), ("Orangetheory Fitness", 4.4, 660)],
    "bar":           [("Canon", 4.7, 1800), ("Tavern Law", 4.5, 1200), ("Knee High Stocking Co", 4.4, 890), ("Rob Roy", 4.6, 1100)],
    "bakery":        [("Grand Central Bakery", 4.5, 1300), ("Macrina Bakery", 4.6, 1800), ("Fuji Bakery", 4.7, 760), ("Tall Grass Bakery", 4.4, 540)],
}

_HOURS_TEMPLATES = [
    [{"day": d, "hours": "11 AM to 9 PM"} for d in ["Monday","Tuesday","Wednesday","Thursday","Friday","Saturday","Sunday"]],
    [{"day": d, "hours": "9 AM to 10 PM"} for d in ["Monday","Tuesday","Wednesday","Thursday","Friday","Saturday","Sunday"]],
    [{"day": d, "hours": "10 AM to 8 PM"} for d in ["Monday","Tuesday","Wednesday"]] +
    [{"day": d, "hours": "10 AM to 10 PM"} for d in ["Thursday","Friday","Saturday"]] +
    [{"day": "Sunday", "hours": "Closed"}],
    [{"day": "Monday", "hours": "Closed"}] +
    [{"day": d, "hours": "5 PM to 11 PM"} for d in ["Tuesday","Wednesday","Thursday"]] +
    [{"day": d, "hours": "12 PM to 11 PM"} for d in ["Friday","Saturday","Sunday"]],
]


def _match_template(business_type: str) -> list:
    bt = business_type.lower()
    for key, competitors in _COMPETITOR_TEMPLATES.items():
        if key in bt:
            return competitors
    # Generic fallback: derive from business_type name
    return [
        (f"{business_type.title()} Place A", 4.3, 780),
        (f"{business_type.title()} Place B", 4.1, 430),
        (f"{business_type.title()} Place C", 4.5, 1100),
        (f"{business_type.title()} Place D", 3.9, 290),
    ]


def _city_pois(location: str) -> list:
    loc = location.lower()
    for key, pois in _CITY_POIS.items():
        if key in loc:
            return pois
    return ["City Center", "Main Street", "Local Park"]


def _mock_scrape(location, business_type, lat, lng) -> dict:
    import hashlib
    seed = int(hashlib.md5(f"{location}{business_type}".encode()).hexdigest()[:4], 16)

    templates = _match_template(business_type)
    competitors = []
    for i, (name, rating, reviews) in enumerate(templates):
        distance = 150 + (seed % 5 + i) * 120
        competitors.append({
            "name": name,
            "distance_m": distance,
            "rating": rating,
            "review_count": reviews,
            "categories": [business_type],
            "openingHours": _HOURS_TEMPLATES[(seed + i) % len(_HOURS_TEMPLATES)],
        })

    traffics = ["moderate", "high", "high", "very high"]
    foot_traffic = traffics[seed % len(traffics)]

    return {
        "location": location,
        "business_type": business_type,
        "lat": lat,
        "lng": lng,
        "competitors": competitors,
        "foot_traffic": foot_traffic,
        "nearby_pois": _city_pois(location),
        "hourly_traffic": [
            {
                "hour": h,
                "speed_summary": {
                    "Free Flow": max(10, 50 - (seed % 20) - abs(h - 14) * 2),
                    "Slow Traffic": 20 + (seed % 10),
                    "Moderate Congestion": 15 + abs(h - 13),
                    "Heavy Congestion": max(0, 10 - abs(h - 12)),
                }
            }
            for h in range(9, 22)
        ],
    }

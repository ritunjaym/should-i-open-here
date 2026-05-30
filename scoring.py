"""
Deterministic signal and score computation for restaurant viability analysis.
No LLM calls; all output is passed as JSON into the LLM prompt.

Viability Score Formula (0–10):
    score = 10 × (
        WEIGHT_DEMAND       × demand_component       +   # avg review count → market size proxy
        WEIGHT_COMPETITION  × competition_component  +   # fewer direct competitors → more room
        WEIGHT_INCUMBENT    × incumbent_component    +   # fewer strong incumbents → less entrenched
        WEIGHT_ACTIVITY     × activity_component     +   # peak in-window activity → walk-by opportunity
        WEIGHT_ACCESSIBILITY× accessibility_component    # free-flow fraction → easier ingress
    )
Each component is normalized [0, 1] before weighting.
"""

from __future__ import annotations

import re
from typing import Optional

# ── Traffic activity weights ──────────────────────────────────────────────────
# Heavier congestion class → more surrounding activity (denser/busier area).
# Free flow → easy vehicle access but lower surrounding density.
FREE_FLOW_WEIGHT = 1
SLOW_TRAFFIC_WEIGHT = 2
MODERATE_CONGESTION_WEIGHT = 3
HEAVY_CONGESTION_WEIGHT = 4

# Weight applied to the counter-programming bonus when scoring candidate hours.
COUNTER_PROGRAMMING_WEIGHT = 0.5

# Minimum span length (hours) for a recommended operating window.
MIN_RECOMMENDED_HOURS = 4

# ── Strong-incumbent thresholds ───────────────────────────────────────────────
STRONG_INCUMBENT_MIN_RATING = 4.5
STRONG_INCUMBENT_MIN_REVIEWS = 100

# ── Normalization ceilings ────────────────────────────────────────────────────
DEMAND_REVIEW_CEILING = 500   # avg reviews ≥ this → full demand score
MAX_DIRECT_COMPETITORS = 8    # direct competitors ≥ this → zero competition score
MAX_STRONG_INCUMBENTS = 5     # strong incumbents ≥ this → zero incumbent score

# ── Viability score weights (must sum to 1.0) ─────────────────────────────────
WEIGHT_DEMAND = 0.25
WEIGHT_COMPETITION = 0.30
WEIGHT_INCUMBENT = 0.20
WEIGHT_ACTIVITY = 0.15
WEIGHT_ACCESSIBILITY = 0.10

# ── Internal lookup tables ────────────────────────────────────────────────────
_CONGESTION_KEY_MAP: dict[str, str] = {
    "free flow": "Free Flow",
    "freeflow": "Free Flow",
    "free_flow": "Free Flow",
    "slow traffic": "Slow Traffic",
    "slowtraffic": "Slow Traffic",
    "slow_traffic": "Slow Traffic",
    "moderate congestion": "Moderate Congestion",
    "moderate_congestion": "Moderate Congestion",
    "moderatecongestion": "Moderate Congestion",
    "heavy congestion": "Heavy Congestion",
    "heavy_congestion": "Heavy Congestion",
    "heavycongestion": "Heavy Congestion",
}

_CONGESTION_WEIGHTS: dict[str, int] = {
    "Free Flow": FREE_FLOW_WEIGHT,
    "Slow Traffic": SLOW_TRAFFIC_WEIGHT,
    "Moderate Congestion": MODERATE_CONGESTION_WEIGHT,
    "Heavy Congestion": HEAVY_CONGESTION_WEIGHT,
}

# Words that do not identify a food-type category.
_GENERIC_TERMS = {
    "restaurant", "bar", "joint", "place", "food", "eatery", "kitchen",
    "house", "grill", "cafe", "shop", "diner", "bistro", "spot", "cuisine",
}


# ── Hour parsing ──────────────────────────────────────────────────────────────

def _parse_hour_int(val) -> Optional[int]:
    """Parse an hour value from int, float, 'HH:MM', 'H AM/PM', or plain digit string."""
    if isinstance(val, (int, float)):
        return int(val)
    s = str(val).strip()
    m = re.match(r"^(\d{1,2}):(\d{2})$", s)
    if m:
        return int(m.group(1))
    m = re.match(r"^(\d{1,2})(?::(\d{2}))?\s*(AM|PM)$", s, re.IGNORECASE)
    if m:
        h = int(m.group(1))
        if m.group(3).upper() == "PM" and h != 12:
            h += 12
        elif m.group(3).upper() == "AM" and h == 12:
            h = 0
        return h
    m = re.match(r"^(\d{1,2})$", s)
    if m:
        return int(m.group(1))
    return None


def _parse_hour_12(time_str: str) -> Optional[int]:
    """
    Parse a time string → integer hour (0–23).
    Handles: '11 AM', '10 PM', '8:30 AM', '3 PM', and ambiguous '4:30' (no AM/PM).
    Ambiguous hours 1–6 without an AM/PM marker are treated as PM (restaurant heuristic).
    """
    s = time_str.strip()
    m = re.match(r"(\d{1,2})(?::(\d{2}))?\s*(AM|PM)", s, re.IGNORECASE)
    if m:
        h = int(m.group(1))
        if m.group(3).upper() == "PM" and h != 12:
            h += 12
        elif m.group(3).upper() == "AM" and h == 12:
            h = 0
        return h
    # No AM/PM marker — bare hour or H:MM (e.g. the second segment of a split range).
    m = re.match(r"^(\d{1,2})(?::(\d{2}))?$", s)
    if m:
        h = int(m.group(1))
        if 0 < h < 7:   # '4:30', '5' → almost certainly afternoon in a restaurant context
            h += 12
        return h
    return None


def _parse_opening_hours_for_day(
    opening_hours: list, day: str
) -> list[tuple[int, int]]:
    """
    Return a list of (open_h, close_h) tuples for the given day.
    Handles: single range, comma-split ranges ('11:30 AM to 3 PM, 4:30 to 9 PM'),
    'Closed', and missing entries.  Returns [] if closed or no data found.
    """
    if not opening_hours:
        return []
    day_lower = day.lower()
    for entry in opening_hours:
        if not isinstance(entry, dict):
            continue
        if str(entry.get("day", "")).lower() != day_lower:
            continue
        hours_str = str(entry.get("hours", "")).strip()
        if not hours_str or "closed" in hours_str.lower():
            return []
        ranges: list[tuple[int, int]] = []
        for segment in hours_str.split(","):
            # Handle "11 AM to 9 PM" (sample data) AND "11 AM–9 PM" / "11 AM - 9 PM" (Apify)
            parts = re.split(r"\s+to\s+|[–—]\s*|\s+-\s+", segment.strip(), maxsplit=1, flags=re.IGNORECASE)
            if len(parts) != 2:
                continue
            open_h = _parse_hour_12(parts[0].strip())
            close_h = _parse_hour_12(parts[1].strip())
            if open_h is not None and close_h is not None:
                ranges.append((open_h, close_h))
        return ranges
    return []


def _is_open_at_hour(ranges: list[tuple[int, int]], h: int) -> bool:
    """True if hour h falls within any of the (open_h, close_h) ranges (cross-midnight safe)."""
    for open_h, close_h in ranges:
        effective_close = close_h if close_h > open_h else close_h + 24
        if open_h <= h < effective_close:
            return True
    return False


def _format_ranges(ranges: list[tuple[int, int]]) -> str:
    """Format a list of hour ranges as a human-readable string, e.g. '11:00–15:00, 16:30–21:00'."""
    parts = []
    for open_h, close_h in ranges:
        display_close = close_h if close_h > open_h else close_h + 24
        parts.append(f"{open_h:02d}:00–{display_close:02d}:00")
    return ", ".join(parts) if parts else "Unknown"


# ── Traffic helpers ───────────────────────────────────────────────────────────

def _normalize_speed_summary(raw: dict) -> dict:
    """Normalize speed_summary keys to canonical form (e.g. 'free_flow' → 'Free Flow')."""
    result: dict[str, float] = {}
    for k, v in raw.items():
        canonical = _CONGESTION_KEY_MAP.get(k.lower().strip(), k)
        result[canonical] = float(v)
    return result


def _activity_score(speed_summary: dict) -> float:
    """
    Derive a 0–1 activity score from a normalized speed_summary.
    Weighted average congestion level, where higher congestion → more surrounding activity.
    raw ∈ [1, 4] → normalized to [0, 1].
    """
    total = sum(speed_summary.values())
    if total == 0:
        return 0.0
    weighted = sum(
        speed_summary.get(cls, 0.0) * w for cls, w in _CONGESTION_WEIGHTS.items()
    )
    raw = weighted / total  # ∈ [1, 4]
    return (raw - 1) / 3   # normalized ∈ [0, 1]


# ── Category matching ─────────────────────────────────────────────────────────

def _extract_core_category(search_term: str) -> str:
    """Return the food-type keyword from a search term (first non-generic word)."""
    for word in search_term.lower().split():
        if word not in _GENERIC_TERMS:
            return word
    words = search_term.lower().split()
    return words[0] if words else ""


def _is_direct_competitor(categories: list, core: str) -> bool:
    """True if core appears in the first two category labels."""
    return any(core in str(c).lower() for c in categories[:2])


def _is_adjacent_competitor(categories: list, core: str) -> bool:
    """True if core appears in category labels beyond the first two."""
    return any(core in str(c).lower() for c in categories[2:])


# ── Recommended-hours algorithm ───────────────────────────────────────────────

def _find_recommended_hours(
    available_hours: dict[int, float],
    competitor_open_fraction: dict[int, float],
    window_hours: list[int],
) -> tuple[Optional[int], Optional[int], str]:
    """
    Find the contiguous span within window_hours that maximises
        combined_score = activity_score + COUNTER_PROGRAMMING_WEIGHT × (1 − competitor_open_fraction)
    over all spans of length ≥ MIN_RECOMMENDED_HOURS.

    Returns (recommended_open_hour, recommended_close_hour_exclusive, rationale_string).
    """
    if not available_hours or not window_hours:
        return None, None, "Insufficient traffic data to make a recommendation."

    combined: dict[int, float] = {
        h: available_hours.get(h, 0.0)
        + COUNTER_PROGRAMMING_WEIGHT * (1.0 - competitor_open_fraction.get(h, 0.0))
        for h in window_hours
    }

    best_avg = -1.0
    best_start = window_hours[0]
    best_end_excl = window_hours[-1] + 1

    n = len(window_hours)
    for i in range(n):
        for j in range(i + MIN_RECOMMENDED_HOURS, n + 1):
            span = window_hours[i:j]
            avg = sum(combined[h] for h in span) / len(span)
            if avg > best_avg:
                best_avg = avg
                best_start = span[0]
                best_end_excl = span[-1] + 1

    counter_hours = [
        h for h in range(best_start, best_end_excl)
        if competitor_open_fraction.get(h, 0.0) < 0.5
    ]

    rationale = (
        f"Span {best_start:02d}:00–{best_end_excl:02d}:00 achieves the highest mean "
        f"combined score ({best_avg:.3f}) across activity and counter-programming signals."
    )
    if counter_hours:
        hrs = ", ".join(f"{h:02d}:00" for h in counter_hours)
        rationale += (
            f" Counter-programming opportunity: fewer than half of nearby competitors "
            f"are open at {hrs}."
        )

    return best_start, best_end_excl, rationale


# ── Main entry point ──────────────────────────────────────────────────────────

def compute_signals(
    user_request: dict, traffic_data: list, competitors: list
) -> dict:
    """
    Compute all deterministic signals and the viability score.
    Returns a JSON-serialisable dict to pass directly to the LLM.
    """
    day = str(user_request.get("day_of_the_week", ""))
    opening_str = str(user_request.get("opening_time", "00:00"))
    closing_str = str(user_request.get("closing_time", "23:00"))
    search_term = str(user_request.get("search_term", ""))

    try:
        window_open = int(opening_str.split(":")[0])
    except (ValueError, AttributeError):
        window_open = 0
    try:
        window_close = int(closing_str.split(":")[0])
    except (ValueError, AttributeError):
        window_close = 23

    # ── Category analysis ─────────────────────────────────────────────────────
    core = _extract_core_category(search_term)
    direct_count = 0
    adjacent_count = 0
    for comp in competitors:
        cats = comp.get("categories", [])
        if _is_direct_competitor(cats, core):
            direct_count += 1
        elif _is_adjacent_competitor(cats, core):
            adjacent_count += 1

    # ── Ratings / reviews ─────────────────────────────────────────────────────
    ratings = [c["totalScore"] for c in competitors if c.get("totalScore") is not None]
    reviews = [c["reviewsCount"] for c in competitors if c.get("reviewsCount") is not None]
    avg_rating = round(sum(ratings) / len(ratings), 2) if ratings else None
    avg_review_count = round(sum(reviews) / len(reviews)) if reviews else 0

    strong_incumbents = [
        c for c in competitors
        if (c.get("totalScore") or 0) >= STRONG_INCUMBENT_MIN_RATING
        and (c.get("reviewsCount") or 0) >= STRONG_INCUMBENT_MIN_REVIEWS
    ]
    strong_incumbent_count = len(strong_incumbents)

    # ── Per-hour activity scores ──────────────────────────────────────────────
    hourly_scores: dict[int, float] = {}
    for entry in traffic_data:
        hour = _parse_hour_int(entry.get("hour"))
        if hour is None:
            continue
        raw_summary = entry.get("speed_summary", {})
        if not isinstance(raw_summary, dict):
            continue
        hourly_scores[hour] = _activity_score(_normalize_speed_summary(raw_summary))

    window_hours = list(range(window_open, window_close))
    available_hours = {h: hourly_scores[h] for h in window_hours if h in hourly_scores}

    # ── Traffic coverage ──────────────────────────────────────────────────────
    covered_hours = sorted(available_hours.keys())
    if covered_hours and set(covered_hours) == set(window_hours):
        traffic_coverage_note = None
    elif covered_hours:
        traffic_coverage_note = (
            f"Traffic data covers {covered_hours[0]:02d}:00–{covered_hours[-1] + 1:02d}:00 only. "
            f"Hours {covered_hours[-1] + 1:02d}:00–{window_close:02d}:00 have no traffic data; "
            f"activity scores and hour recommendations reflect only the covered range."
        )
    else:
        traffic_coverage_note = (
            "No traffic data falls within the stated operating window. "
            "Activity scores and hour recommendations are unavailable."
        )

    # ── Competitor open/close distribution ────────────────────────────────────
    competitor_hours_that_day: list[dict] = []
    open_at_hour: dict[int, int] = {h: 0 for h in window_hours}

    for comp in competitors:
        ranges = _parse_opening_hours_for_day(comp.get("openingHours", []), day)
        competitor_hours_that_day.append({
            "name": comp.get("title", "Unknown"),
            "hours_today": _format_ranges(ranges) if ranges else "Closed / unknown",
        })
        for h in window_hours:
            if _is_open_at_hour(ranges, h):
                open_at_hour[h] += 1

    total_comps = len(competitors) or 1
    competitor_open_fraction: dict[int, float] = {
        h: round(n / total_comps, 2) for h, n in open_at_hour.items()
    }

    ranked_hours = [h for h, _ in sorted(available_hours.items(), key=lambda x: -x[1])]

    # ── Recommended hours (constrained to traffic-covered hours only) ─────────
    rec_open, rec_close, rec_rationale = _find_recommended_hours(
        available_hours, competitor_open_fraction, covered_hours   # ← covered_hours, not window_hours
    )

    # ── Accessibility note ────────────────────────────────────────────────────
    all_summaries = [
        _normalize_speed_summary(e["speed_summary"])
        for e in traffic_data
        if isinstance(e.get("speed_summary"), dict)
    ]
    day_total = sum(sum(s.values()) for s in all_summaries)
    day_free_flow = sum(s.get("Free Flow", 0.0) for s in all_summaries)
    free_flow_fraction = round(day_free_flow / day_total, 3) if day_total else 0.5

    if free_flow_fraction >= 0.70:
        accessibility_note = (
            "Free-flow dominant: road access is easy, though lower congestion may "
            "also indicate lower surrounding activity density."
        )
    elif free_flow_fraction >= 0.40:
        accessibility_note = (
            "Mixed conditions: moderate access friction alongside reasonable surrounding activity."
        )
    else:
        accessibility_note = (
            "Congestion-heavy: high surrounding activity is implied, "
            "but vehicle access friction is significant."
        )

    # ── Viability score ───────────────────────────────────────────────────────
    demand_c = min(1.0, avg_review_count / DEMAND_REVIEW_CEILING)
    competition_c = max(0.0, 1.0 - direct_count / MAX_DIRECT_COMPETITORS)
    incumbent_c = max(0.0, 1.0 - strong_incumbent_count / MAX_STRONG_INCUMBENTS)
    activity_c = max(available_hours.values()) if available_hours else 0.0
    accessibility_c = free_flow_fraction

    viability_score = round(
        10.0 * (
            WEIGHT_DEMAND * demand_c
            + WEIGHT_COMPETITION * competition_c
            + WEIGHT_INCUMBENT * incumbent_c
            + WEIGHT_ACTIVITY * activity_c
            + WEIGHT_ACCESSIBILITY * accessibility_c
        ),
        1,
    )

    return {
        "direct_competitor_count": direct_count,
        "adjacent_competitor_count": adjacent_count,
        "avg_competitor_rating": avg_rating,
        "avg_review_count": int(avg_review_count),
        "strong_incumbent_count": strong_incumbent_count,
        "strong_incumbent_threshold": {
            "min_rating": STRONG_INCUMBENT_MIN_RATING,
            "min_reviews": STRONG_INCUMBENT_MIN_REVIEWS,
        },
        "traffic_covered_hours": covered_hours,
        "traffic_coverage_note": traffic_coverage_note,
        "hourly_activity_scores": {
            str(h): round(s, 4) for h, s in sorted(available_hours.items())
        },
        "hours_ranked_best_to_worst": ranked_hours,
        "recommended_open_hour": rec_open,
        "recommended_close_hour": rec_close,
        "recommendation_rationale": rec_rationale,
        "competitor_open_fraction_by_hour": {
            str(h): v for h, v in competitor_open_fraction.items()
        },
        "competitor_hours_that_day": competitor_hours_that_day,
        "accessibility_note": accessibility_note,
        "free_flow_fraction": free_flow_fraction,
        "viability_score": viability_score,
        "score_components": {
            "demand": round(demand_c, 4),
            "competition": round(competition_c, 4),
            "incumbent": round(incumbent_c, 4),
            "activity": round(activity_c, 4),
            "accessibility": round(accessibility_c, 4),
        },
        "score_weights": {
            "demand": WEIGHT_DEMAND,
            "competition": WEIGHT_COMPETITION,
            "incumbent": WEIGHT_INCUMBENT,
            "activity": WEIGHT_ACTIVITY,
            "accessibility": WEIGHT_ACCESSIBILITY,
        },
    }

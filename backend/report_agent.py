"""
Person B's report generator interface.
Real implementation: report_agent_real.py (Person B's code).
Until that lands, USE_MOCK=True returns a canned markdown report.
"""
import os
import asyncio

USE_MOCK = os.getenv("USE_MOCK_AGENT", "true").lower() == "true"

PROMPT_TEMPLATE = """You are a business location analyst. Write a concise, structured report on whether the following location is good for opening a {business_type}.

Location data:
{data_json}

Write the report in markdown with these sections:
## Executive Summary
(2-3 sentences, clear go/no-go recommendation)

## Competitor Landscape
(who's nearby, how saturated is the market)

## Foot Traffic Analysis
(what the traffic level means for this business type)

## Opportunity & Risk
(what's the opening, what's the threat)

## Verdict
Score: X/10 — one sentence rationale.

Be direct and opinionated. No filler."""


async def generate_report(scrape_data: dict) -> str:
    if USE_MOCK:
        return _mock_report(scrape_data)

    from report_agent_real import generate as real_generate  # noqa: PLC0415
    return await real_generate(scrape_data)


def _mock_report(data: dict) -> str:
    loc = data.get("location", "Unknown location")
    biz = data.get("business_type", "business")
    competitors = data.get("competitors", [])
    traffic = data.get("foot_traffic", "unknown")
    n = len(competitors)

    return f"""# Location Analysis: {biz.title()} at {loc}

## Executive Summary
This location shows **strong foot traffic** but faces **significant competition** with {n} established players within 600 m. Proceed only with a clear differentiation strategy — quality alone will not be enough.

## Competitor Landscape
{n} direct competitors identified nearby:
{chr(10).join(f"- **{c['name']}** — {c['distance_m']} m away, rated {c['rating']}⭐ ({c.get('review_count', '?')} reviews)" for c in competitors)}

Market saturation is **high**. The closest competitor is only {min(c['distance_m'] for c in competitors) if competitors else 'N/A'} m away.

## Foot Traffic Analysis
Foot traffic is rated **{traffic}**. For a {biz}, this is {'excellent — customers are already in the area and willing to spend.' if traffic in ('high', 'very high') else 'acceptable but may require active marketing to convert passersby.'}

## Opportunity & Risk
**Opportunity:** High foot traffic from nearby landmarks creates natural discovery. A differentiated concept (e.g., specialty roast, unique atmosphere) can carve share from commoditized chains.

**Risk:** Three well-reviewed competitors within walking distance means price-sensitive customers have easy alternatives. Customer acquisition cost will be elevated.

## Verdict
**Score: 6/10** — Viable location if you have a strong brand differentiator, but expect a tough first 6 months against entrenched players.
"""

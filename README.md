# should-i-open-here

Restaurant location viability agent — parses a teammate's structured Markdown input, computes deterministic signals, and calls Claude to produce a Markdown viability report.

## Run

```bash
ANTHROPIC_API_KEY=your_key python agent.py sample_input.md
```

Test parsing and scoring without calling the API:

```bash
python agent.py --mock
```

## Input format

A `.md` file with three ` ```json ``` ` code fences:
1. **User request** — `address`, `day_of_the_week`, `opening_time`, `closing_time` (24h `HH:MM`), `search_term`
2. **Hourly traffic** — array of `{hour, speed_summary}` objects, one per hour
3. **Competitors** — array of place objects with `title`, `totalScore`, `reviewsCount`, `categories`, `openingHours`, `rank`

## Output

`report.md` written alongside the input file. Compatible with standard Markdown renderers (Box, GitHub, etc.) — pipe tables only, no ASCII box-drawing characters.

## Requirements

```
pip install anthropic
```

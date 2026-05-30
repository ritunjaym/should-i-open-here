<<<<<<< HEAD
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
=======
# Should I Open Here?

AI-powered business location analyzer. Enter an address + business type → get a Box-saved report on competitors, foot traffic, and whether you should open there.

## Repo Structure

```
/
├── schema.json          ← shared data contract (read this first!)
├── backend/             ← Person C: FastAPI + Box integration
├── scraper/             ← Person A: Apify Google Maps scraper
└── frontend/            ← Person D: UI
```

## Quickstart (backend)

```bash
cd backend
pip install -r requirements.txt
cp .env.example .env     # add Box credentials
uvicorn main:app --reload
```

## Integration

See `schema.json` for the shared JSON schema all parts agree on.

- **Scraper → Backend**: Person A drops `scraper_real.py` in `backend/`, set `USE_MOCK_SCRAPER=false`
- **Agent → Backend**: Person B drops `report_agent_real.py` in `backend/`, set `USE_MOCK_AGENT=false`
- **Backend → Frontend**: POST `/analyze` returns `{ box_link, report_preview }`
>>>>>>> 5a9b89512dccd1ca29be07543725afbbd2f71722

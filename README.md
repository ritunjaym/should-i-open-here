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

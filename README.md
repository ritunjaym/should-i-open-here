# Should I Open Here?

AI-powered business location analyzer. Enter an address + business type → get a Box-saved report on competitors, foot traffic, and whether you should open there.

## Repo Structure

```
/
├── schema.json          ← shared data contract (read this first!)
├── agent.py             ← Person B: AI report writer (Claude-powered)
├── prompts.py           ← Person B: system prompt for the analyst
├── scoring.py           ← Person B: deterministic signal scoring
├── sample_input.md      ← Person B: sample input format
├── backend/             ← Person C: FastAPI + Box integration
└── frontend/            ← Person D: UI (coming)
```

## Quickstart

### Run the agent standalone (Person B)
```bash
ANTHROPIC_API_KEY=your_key python agent.py sample_input.md
# or test without API call:
python agent.py --mock
```

### Run the backend (Person C)
```bash
cd backend
pip install -r requirements.txt
cp .env.example .env     # add Box credentials + Anthropic key
uvicorn main:app --reload
# API at http://localhost:8000  |  Docs at http://localhost:8000/docs
```

## Integration

See `schema.json` for the shared JSON schema all parts agree on.

- **Scraper → Backend**: Person A drops `scraper_real.py` in `backend/`, set `USE_MOCK_SCRAPER=false`
- **Agent → Backend**: Person B drops `report_agent_real.py` in `backend/`, set `USE_MOCK_AGENT=false`
- **Backend → Frontend**: POST `/analyze` returns `{ box_link, report_preview }`

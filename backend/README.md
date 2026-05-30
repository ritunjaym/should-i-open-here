# Backend — Person C (Madan)

FastAPI backend that chains: **scrape → AI report → Box upload → return link**

## Setup

```bash
cd backend
python -m venv venv
venv\Scripts\activate        # Windows
pip install -r requirements.txt
cp .env.example .env         # fill in your Box credentials
```

## Run

```bash
uvicorn main:app --reload
# or
python main.py
```

API is at `http://localhost:8000`  
Swagger docs at `http://localhost:8000/docs`

## Box Developer Token

1. Go to https://app.box.com/developers/console
2. Create a new app → Custom App → User Authentication (OAuth 2.0)
3. Under "Configuration" tab → copy Client ID + Secret
4. Scroll to "Developer Token" → Generate Token (valid 1 hour, enough for the hackathon)
5. Paste all three into `.env`

## Environment Variables

| Variable | Description |
|---|---|
| `BOX_CLIENT_ID` | From Box developer console |
| `BOX_CLIENT_SECRET` | From Box developer console |
| `BOX_DEVELOPER_TOKEN` | Generated token (1-hour TTL) |
| `USE_MOCK_SCRAPER` | `true` = use fake data, `false` = call Person A's module |
| `USE_MOCK_AGENT` | `true` = use canned report, `false` = call Person B's module |

## Plugging in Person A / Person B

- **Person A**: drop `scraper_real.py` into this folder with an async `scrape(location, business_type, lat, lng) -> dict` function, then set `USE_MOCK_SCRAPER=false`
- **Person B**: drop `report_agent_real.py` into this folder with an async `generate(scrape_data: dict) -> str` function, then set `USE_MOCK_AGENT=false`

## API

### POST /analyze

```json
{
  "location": "123 Main St, Seattle",
  "business_type": "coffee shop",
  "lat": 47.6062,
  "lng": -122.3321
}
```

Response:
```json
{
  "box_link": "https://app.box.com/s/...",
  "report_preview": "# Location Analysis...",
  "location": "123 Main St, Seattle",
  "business_type": "coffee shop"
}
```

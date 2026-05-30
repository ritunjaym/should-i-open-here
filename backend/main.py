from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional
import uvicorn
from pathlib import Path
from dotenv import load_dotenv
load_dotenv(Path(__file__).parent / ".env")

from scraper import scrape_location
from report_agent import generate_report
from box_client import upload_report_to_box

app = FastAPI(title="Should I Open Here?", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


class AnalyzeRequest(BaseModel):
    location: str          # "123 Main St, Seattle" or "47.6062,-122.3321"
    business_type: str     # "coffee shop", "gym", "restaurant", etc.
    lat: Optional[float] = None
    lng: Optional[float] = None
    day_of_week: Optional[str] = None      # e.g. "Monday"
    opening_time: Optional[str] = None     # e.g. "09:00"
    closing_time: Optional[str] = None     # e.g. "17:00"


class AnalyzeResponse(BaseModel):
    box_link: str
    report_preview: str    # first ~300 chars so the frontend can show a teaser
    location: str
    business_type: str


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/analyze", response_model=AnalyzeResponse)
async def analyze(req: AnalyzeRequest):
    # Step 1: scrape competitor + traffic data
    try:
        scrape_data = await scrape_location(
            location=req.location,
            business_type=req.business_type,
            lat=req.lat,
            lng=req.lng,
            day_of_week=req.day_of_week,
            opening_time=req.opening_time,
            closing_time=req.closing_time,
        )
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Scraper error: {e}")

    # Step 2: generate markdown report via AI agent
    try:
        report_md = await generate_report(scrape_data)
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Report agent error: {e}")

    # Step 3: save report to Box, get shareable link
    try:
        box_link = await upload_report_to_box(
            report_md=report_md,
            location=req.location,
            business_type=req.business_type,
        )
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Box upload error: {e}")

    return AnalyzeResponse(
        box_link=box_link,
        report_preview=report_md,
        location=req.location,
        business_type=req.business_type,
    )


if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)

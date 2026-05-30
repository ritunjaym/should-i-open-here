"""
Box integration — uses Box REST API directly (no boxsdk) to avoid OAuth2
refresh issues with Developer Tokens.

Requires env vars:
  BOX_DEVELOPER_TOKEN   # from app.box.com/developers/console (expires 1hr)

Folder structure in Box:
  Should I Open Here/
    └── Reports/
          └── <slug>_<timestamp>.md
"""
import os
import io
import re
import asyncio
from datetime import datetime, timezone

import requests

BASE = "https://api.box.com/2.0"
UPLOAD_BASE = "https://upload.box.com/api/2.0"
BOX_FOLDER_NAME = "Should I Open Here"
REPORTS_SUBFOLDER = "Reports"


def _headers() -> dict:
    token = os.environ.get("BOX_DEVELOPER_TOKEN", "").strip()
    if not token or token.startswith("PASTE_"):
        raise ValueError(
            "BOX_DEVELOPER_TOKEN not set in .env — "
            "go to app.box.com/developers/console → your app → Configuration → Generate Developer Token"
        )
    return {"Authorization": f"Bearer {token}"}


def _get_or_create_folder(parent_id: str, name: str) -> str:
    """Return folder ID, creating it if it doesn't exist."""
    # list parent folder
    r = requests.get(
        f"{BASE}/folders/{parent_id}/items",
        params={"fields": "id,name,type", "limit": 1000},
        headers=_headers(),
    )
    r.raise_for_status()
    for item in r.json().get("entries", []):
        if item["type"] == "folder" and item["name"] == name:
            return item["id"]

    # create it
    r = requests.post(
        f"{BASE}/folders",
        json={"name": name, "parent": {"id": parent_id}},
        headers=_headers(),
    )
    r.raise_for_status()
    return r.json()["id"]


def _safe_filename(location: str, business_type: str) -> str:
    slug = re.sub(r"[^\w\s-]", "", f"{location} {business_type}").strip()
    slug = re.sub(r"\s+", "_", slug)[:60]
    ts = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    return f"{slug}_{ts}.md"


def _upload_sync(report_md: str, location: str, business_type: str) -> str:
    # ensure folder hierarchy
    parent_id = _get_or_create_folder("0", BOX_FOLDER_NAME)
    reports_id = _get_or_create_folder(parent_id, REPORTS_SUBFOLDER)

    filename = _safe_filename(location, business_type)
    file_content = report_md.encode("utf-8")

    # upload file
    r = requests.post(
        f"{UPLOAD_BASE}/files/content",
        headers=_headers(),
        data={"attributes": f'{{"name":"{filename}","parent":{{"id":"{reports_id}"}}}}'},
        files={"file": (filename, io.BytesIO(file_content), "text/markdown")},
    )
    r.raise_for_status()
    file_id = r.json()["entries"][0]["id"]

    # create shared link (open = no login required)
    r = requests.put(
        f"{BASE}/files/{file_id}",
        json={"shared_link": {"access": "open"}},
        headers={**_headers(), "Content-Type": "application/json"},
        params={"fields": "shared_link"},
    )
    r.raise_for_status()
    return r.json()["shared_link"]["url"]


async def upload_report_to_box(
    report_md: str,
    location: str,
    business_type: str,
) -> str:
    """Upload markdown report to Box and return a shareable link URL."""
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(
        None, _upload_sync, report_md, location, business_type
    )

"""
Box integration using Client Credentials Grant (CCG).
No developer token needed — uses client_id + client_secret + enterprise_id.

Required env vars:
  BOX_CLIENT_ID
  BOX_CLIENT_SECRET
  BOX_ENTERPRISE_ID   # found in Box developer console under your app

Folder structure created in Box:
  Should I Open Here/
    └── Reports/
          └── <slug>_<timestamp>.md
"""
import os
import io
import re
import asyncio
from datetime import datetime, timezone
from pathlib import Path

import requests

BASE        = "https://api.box.com/2.0"
UPLOAD_BASE = "https://upload.box.com/api/2.0"
TOKEN_URL   = "https://api.box.com/oauth2/token"
BOX_FOLDER_NAME    = "Should I Open Here"
REPORTS_SUBFOLDER  = "Reports"

# Load .env the same way other modules do
_env_file = Path(__file__).parent / ".env"
if _env_file.exists():
    for _line in _env_file.read_text(encoding="utf-8").splitlines():
        _line = _line.strip()
        if _line and not _line.startswith("#") and "=" in _line:
            _k, _v = _line.split("=", 1)
            os.environ[_k.strip()] = _v.strip()


def _get_ccg_token() -> str:
    """Obtain a Box access token via Client Credentials Grant."""
    client_id     = os.environ.get("BOX_CLIENT_ID", "").strip()
    client_secret = os.environ.get("BOX_CLIENT_SECRET", "").strip()
    enterprise_id = os.environ.get("BOX_ENTERPRISE_ID", "").strip()

    missing = [k for k, v in [
        ("BOX_CLIENT_ID", client_id),
        ("BOX_CLIENT_SECRET", client_secret),
        ("BOX_ENTERPRISE_ID", enterprise_id),
    ] if not v]
    if missing:
        raise ValueError(f"Missing Box env vars: {', '.join(missing)}")

    r = requests.post(TOKEN_URL, data={
        "grant_type":      "client_credentials",
        "client_id":       client_id,
        "client_secret":   client_secret,
        "box_subject_type": "enterprise",
        "box_subject_id":  enterprise_id,
    })
    r.raise_for_status()
    return r.json()["access_token"]


def _headers() -> dict:
    return {"Authorization": f"Bearer {_get_ccg_token()}"}


def _get_or_create_folder(parent_id: str, name: str, headers: dict) -> str:
    r = requests.get(
        f"{BASE}/folders/{parent_id}/items",
        params={"fields": "id,name,type", "limit": 1000},
        headers=headers,
    )
    r.raise_for_status()
    for item in r.json().get("entries", []):
        if item["type"] == "folder" and item["name"] == name:
            return item["id"]

    r = requests.post(
        f"{BASE}/folders",
        json={"name": name, "parent": {"id": parent_id}},
        headers=headers,
    )
    r.raise_for_status()
    return r.json()["id"]


def _safe_filename(location: str, business_type: str) -> str:
    slug = re.sub(r"[^\w\s-]", "", f"{location} {business_type}").strip()
    slug = re.sub(r"\s+", "_", slug)[:60]
    ts = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    return f"{slug}_{ts}.md"


def _upload_sync(report_md: str, location: str, business_type: str) -> str:
    headers = _headers()   # single token for the whole upload

    parent_id  = _get_or_create_folder("0", BOX_FOLDER_NAME, headers)
    reports_id = _get_or_create_folder(parent_id, REPORTS_SUBFOLDER, headers)

    filename     = _safe_filename(location, business_type)
    file_content = report_md.encode("utf-8")

    r = requests.post(
        f"{UPLOAD_BASE}/files/content",
        headers=headers,
        data={"attributes": f'{{"name":"{filename}","parent":{{"id":"{reports_id}"}}}}'},
        files={"file": (filename, io.BytesIO(file_content), "text/markdown")},
    )
    r.raise_for_status()
    file_id = r.json()["entries"][0]["id"]

    r = requests.put(
        f"{BASE}/files/{file_id}",
        json={"shared_link": {"access": "open"}},
        headers={**headers, "Content-Type": "application/json"},
        params={"fields": "shared_link"},
    )
    r.raise_for_status()
    return r.json()["shared_link"]["url"]


async def upload_report_to_box(report_md: str, location: str, business_type: str) -> str:
    """Upload report to Box via CCG auth. Returns shareable link or 'no-box-token'."""
    if not all([
        os.environ.get("BOX_CLIENT_ID"),
        os.environ.get("BOX_CLIENT_SECRET"),
        os.environ.get("BOX_ENTERPRISE_ID"),
    ]):
        return "no-box-token"

    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(None, _upload_sync, report_md, location, business_type)

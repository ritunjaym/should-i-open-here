"""
Box integration using OAuth 2.0 access + refresh tokens.

Run box_auth_setup.py ONCE to populate BOX_ACCESS_TOKEN and BOX_REFRESH_TOKEN in .env.
Tokens are auto-refreshed on expiry.

Required env vars (set automatically by box_auth_setup.py):
  BOX_CLIENT_ID
  BOX_CLIENT_SECRET
  BOX_ACCESS_TOKEN
  BOX_REFRESH_TOKEN
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
ENV_FILE    = Path(__file__).parent / ".env"

BOX_FOLDER_NAME   = "Should I Open Here"
REPORTS_SUBFOLDER = "Reports"

# Load .env
if ENV_FILE.exists():
    for _line in ENV_FILE.read_text(encoding="utf-8").splitlines():
        _line = _line.strip()
        if _line and not _line.startswith("#") and "=" in _line:
            _k, _v = _line.split("=", 1)
            os.environ[_k.strip()] = _v.strip()


def _refresh_tokens() -> str:
    """Use refresh token to get a new access token; persists both back to .env."""
    r = requests.post(TOKEN_URL, data={
        "grant_type":    "refresh_token",
        "refresh_token": os.environ.get("BOX_REFRESH_TOKEN", ""),
        "client_id":     os.environ.get("BOX_CLIENT_ID", ""),
        "client_secret": os.environ.get("BOX_CLIENT_SECRET", ""),
    })
    r.raise_for_status()
    tokens = r.json()
    new_access  = tokens["access_token"]
    new_refresh = tokens["refresh_token"]

    # Persist updated tokens to .env
    os.environ["BOX_ACCESS_TOKEN"]  = new_access
    os.environ["BOX_REFRESH_TOKEN"] = new_refresh
    _update_env("BOX_ACCESS_TOKEN",  new_access)
    _update_env("BOX_REFRESH_TOKEN", new_refresh)
    return new_access


def _update_env(key: str, value: str):
    if not ENV_FILE.exists():
        return
    lines = ENV_FILE.read_text(encoding="utf-8").splitlines()
    updated = False
    for i, line in enumerate(lines):
        if line.startswith(f"{key}="):
            lines[i] = f"{key}={value}"
            updated = True
            break
    if not updated:
        lines.append(f"{key}={value}")
    ENV_FILE.write_text("\n".join(lines) + "\n", encoding="utf-8")


def _get_token() -> str:
    return os.environ.get("BOX_ACCESS_TOKEN", "")


def _headers(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


def _api_get(url, token, **kwargs):
    """GET with one automatic token refresh on 401."""
    r = requests.get(url, headers=_headers(token), **kwargs)
    if r.status_code == 401:
        token = _refresh_tokens()
        r = requests.get(url, headers=_headers(token), **kwargs)
    r.raise_for_status()
    return r, token


def _api_post(url, token, **kwargs):
    r = requests.post(url, headers=_headers(token), **kwargs)
    if r.status_code == 401:
        token = _refresh_tokens()
        r = requests.post(url, headers=_headers(token), **kwargs)
    r.raise_for_status()
    return r, token


def _api_put(url, token, **kwargs):
    r = requests.put(url, headers=_headers(token), **kwargs)
    if r.status_code == 401:
        token = _refresh_tokens()
        r = requests.put(url, headers=_headers(token), **kwargs)
    r.raise_for_status()
    return r, token


def _get_or_create_folder(parent_id: str, name: str, token: str) -> tuple[str, str]:
    r, token = _api_get(
        f"{BASE}/folders/{parent_id}/items", token,
        params={"fields": "id,name,type", "limit": 1000},
    )
    for item in r.json().get("entries", []):
        if item["type"] == "folder" and item["name"] == name:
            return item["id"], token

    r, token = _api_post(
        f"{BASE}/folders", token,
        json={"name": name, "parent": {"id": parent_id}},
    )
    return r.json()["id"], token


def _safe_filename(location: str, business_type: str) -> str:
    slug = re.sub(r"[^\w\s-]", "", f"{location} {business_type}").strip()
    slug = re.sub(r"\s+", "_", slug)[:60]
    ts = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    return f"{slug}_{ts}.md"


def _upload_sync(report_md: str, location: str, business_type: str) -> str:
    token = _get_token()

    parent_id,  token = _get_or_create_folder("0", BOX_FOLDER_NAME, token)
    reports_id, token = _get_or_create_folder(parent_id, REPORTS_SUBFOLDER, token)

    filename     = _safe_filename(location, business_type)
    file_content = report_md.encode("utf-8")

    r, token = _api_post(
        f"{UPLOAD_BASE}/files/content", token,
        data={"attributes": f'{{"name":"{filename}","parent":{{"id":"{reports_id}"}}}}'},
        files={"file": (filename, io.BytesIO(file_content), "text/markdown")},
    )
    file_id = r.json()["entries"][0]["id"]

    r, _ = _api_put(
        f"{BASE}/files/{file_id}", token,
        json={"shared_link": {"access": "open"}},
        params={"fields": "shared_link"},
    )
    return r.json()["shared_link"]["url"]


async def upload_report_to_box(report_md: str, location: str, business_type: str) -> str:
    """Upload report to Box and return a shareable link. Returns 'no-box-token' if not configured."""
    if not os.environ.get("BOX_ACCESS_TOKEN") or not os.environ.get("BOX_REFRESH_TOKEN"):
        return "no-box-token"

    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(None, _upload_sync, report_md, location, business_type)

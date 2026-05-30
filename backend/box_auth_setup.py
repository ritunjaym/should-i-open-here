#!/usr/bin/env python3
"""
Run this ONCE to authorize your Box app and save tokens to .env.
Usage: python box_auth_setup.py
"""
import os, json, webbrowser, urllib.parse, secrets
from http.server import HTTPServer, BaseHTTPRequestHandler
from pathlib import Path
import requests

REDIRECT_URI = "http://localhost:8080/callback"
ENV_FILE = Path(__file__).parent / ".env"

# Load existing .env
env_vals = {}
if ENV_FILE.exists():
    for line in ENV_FILE.read_text().splitlines():
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            k, v = line.split("=", 1)
            env_vals[k.strip()] = v.strip()

CLIENT_ID     = env_vals.get("BOX_CLIENT_ID", "")
CLIENT_SECRET = env_vals.get("BOX_CLIENT_SECRET", "")

if not CLIENT_ID or not CLIENT_SECRET:
    print("BOX_CLIENT_ID / BOX_CLIENT_SECRET not found in .env")
    exit(1)

state = secrets.token_hex(8)
auth_url = (
    f"https://account.box.com/api/oauth2/authorize"
    f"?response_type=code&client_id={CLIENT_ID}"
    f"&redirect_uri={urllib.parse.quote(REDIRECT_URI)}&state={state}"
)

captured = {}

class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        qs = urllib.parse.parse_qs(urllib.parse.urlparse(self.path).query)
        captured["code"]  = qs.get("code",  [""])[0]
        captured["state"] = qs.get("state", [""])[0]
        self.send_response(200)
        self.send_header("Content-Type", "text/html")
        self.end_headers()
        self.wfile.write(b"<h2>Box authorized! You can close this tab.</h2>")
    def log_message(self, *a): pass

print("\nOpening Box authorization in your browser...")
print("If it doesn't open, visit:\n", auth_url, "\n")
webbrowser.open(auth_url)

server = HTTPServer(("localhost", 8080), Handler)
server.handle_request()   # blocks until one request comes in

code = captured.get("code", "")
if not code:
    print("No authorization code received. Did you approve the app?")
    exit(1)

# Exchange code for tokens
r = requests.post("https://api.box.com/oauth2/token", data={
    "grant_type":    "authorization_code",
    "code":          code,
    "client_id":     CLIENT_ID,
    "client_secret": CLIENT_SECRET,
    "redirect_uri":  REDIRECT_URI,
})
r.raise_for_status()
tokens = r.json()
access_token  = tokens["access_token"]
refresh_token = tokens["refresh_token"]

# Write tokens back to .env
env_vals["BOX_ACCESS_TOKEN"]  = access_token
env_vals["BOX_REFRESH_TOKEN"] = refresh_token

lines = []
for k, v in env_vals.items():
    lines.append(f"{k}={v}")
ENV_FILE.write_text("\n".join(lines) + "\n")

print("Tokens saved to .env")
print("Access token:", access_token[:20], "...")
print("Box is ready to use!")

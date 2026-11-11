#!/usr/bin/env python3
"""
JARVIS local server — pure stdlib HTTP + optional Obsidian bridge.
Run: python backend/server.py   (from project root)
"""

from __future__ import annotations

import json
import mimetypes
import sys
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlparse

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from backend.obsidian_client import ObsidianClient
from backend.orchestrator import Orchestrator

CONFIG_PATH = ROOT / "config" / "settings.json"
EXAMPLE_PATH = ROOT / "config" / "settings.example.json"
FRONTEND = ROOT / "frontend"


def load_settings() -> dict:
    path = CONFIG_PATH if CONFIG_PATH.exists() else EXAMPLE_PATH
    # utf-8-sig strips Windows BOM from PowerShell Set-Content
    with open(path, encoding="utf-8-sig") as f:
        return json.load(f)


SETTINGS = load_settings()
OBSIDIAN = ObsidianClient(SETTINGS.get("obsidian", {}))
ORCH = Orchestrator(OBSIDIAN, SETTINGS)


class Handler(BaseHTTPRequestHandler):
    server_version = "JARVIS/0.1"

    def log_message(self, fmt, *args):
        sys.stderr.write("[JARVIS] " + (fmt % args) + "\n")

    def _cors(self):
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")

    def do_OPTIONS(self):
        self.send_response(204)
        self._cors()
        self.end_headers()

    def do_GET(self):
        path = urlparse(self.path).path
        if path == "/api/health":
            return self._json(200, {"ok": True, "name": "JARVIS", "version": "0.1"})
        if path == "/api/obsidian/status":
            return self._json(200, OBSIDIAN.status())
        if path in ("/", "/index.html"):
            return self._file(FRONTEND / "index.html")
        rel = path.lstrip("/")
        candidate = (FRONTEND / rel).resolve()
        if str(candidate).startswith(str(FRONTEND.resolve())) and candidate.is_file():
            return self._file(candidate)
        self._json(404, {"error": "not found"})

    def do_POST(self):
        parsed = urlparse(self.path)
        length = int(self.headers.get("Content-Length") or 0)
        raw = self.rfile.read(length) if length else b"{}"
        try:
            body = json.loads(raw.decode("utf-8") or "{}")
        except json.JSONDecodeError:
            return self._json(400, {"error": "invalid json"})
        if parsed.path == "/api/chat":
            msg = body.get("message") or body.get("text") or ""
            return self._json(200, ORCH.handle(msg))
        if parsed.path == "/api/obsidian/read":
            try:
                return self._json(200, {"ok": True, "content": OBSIDIAN.read_note(body.get("path", ""))})
            except Exception as e:
                return self._json(400, {"ok": False, "error": str(e)})
        if parsed.path == "/api/obsidian/write":
            try:
                r = OBSIDIAN.write_note(body.get("path", ""), body.get("content", ""), append=bool(body.get("append")))
                return self._json(200, r)
            except Exception as e:
                return self._json(400, {"ok": False, "error": str(e)})
        if parsed.path == "/api/obsidian/search":
            try:
                return self._json(200, {"ok": True, "results": OBSIDIAN.search(body.get("query", ""))})
            except Exception as e:
                return self._json(400, {"ok": False, "error": str(e)})
        self._json(404, {"error": "not found"})

    def _json(self, code: int, data: dict):
        payload = json.dumps(data, ensure_ascii=False).encode("utf-8")
        self.send_response(code)
        self._cors()
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(payload)))
        self.end_headers()
        self.wfile.write(payload)

    def _file(self, path: Path):
        data = path.read_bytes()
        ctype = mimetypes.guess_type(str(path))[0] or "application/octet-stream"
        self.send_response(200)
        self._cors()
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)


def main():
    host = SETTINGS.get("server", {}).get("host", "127.0.0.1")
    port = int(SETTINGS.get("server", {}).get("port", 8765))
    if not CONFIG_PATH.exists():
        print(f"[JARVIS] Using example config. Copy to {CONFIG_PATH} and set API key.")
    httpd = ThreadingHTTPServer((host, port), Handler)
    print(f"[JARVIS] http://{host}:{port}")
    print(f"[JARVIS] Obsidian mode: {SETTINGS.get('obsidian', {}).get('mode')}")
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\n[JARVIS] shutdown")


if __name__ == "__main__":
    main()

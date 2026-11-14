#!/usr/bin/env python3
"""JARVIS local-first HTTP server. Run from the repository root with start.bat."""
from __future__ import annotations

import json
import mimetypes
import re
import sys
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, unquote, urlparse

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from backend.obsidian_client import ObsidianClient
from backend.orchestrator import Orchestrator
from backend.storage import Store

CONFIG_PATH = ROOT / "config" / "settings.json"
EXAMPLE_PATH = ROOT / "config" / "settings.example.json"
FRONTEND = ROOT / "frontend"
DATA_PATH = ROOT / "data" / "jarvis.db"


def load_settings() -> dict:
    path = CONFIG_PATH if CONFIG_PATH.exists() else EXAMPLE_PATH
    with path.open(encoding="utf-8-sig") as stream:
        return json.load(stream)


SETTINGS = load_settings()
# Resolve a relative vault path against the repository, not the shell's current directory.
obsidian_settings = SETTINGS.setdefault("obsidian", {})
filesystem_settings = obsidian_settings.setdefault("filesystem", {})
vault_path = str(filesystem_settings.get("vault_path") or "").strip()
if vault_path and not Path(vault_path).is_absolute():
    filesystem_settings["vault_path"] = str((ROOT / vault_path).resolve())
OBSIDIAN = ObsidianClient(obsidian_settings)
STORE = Store(DATA_PATH)
ORCH = Orchestrator(OBSIDIAN, SETTINGS, STORE)
MAX_BODY = 1_000_000


class Handler(BaseHTTPRequestHandler):
    server_version = "JARVIS/0.3"

    def log_message(self, fmt, *args):
        sys.stderr.write("[JARVIS] " + (fmt % args) + "\n")

    def _host_allowed(self) -> bool:
        host = (self.headers.get("Host") or "").lower()
        port = int(SETTINGS.get("server", {}).get("port", 8765))
        return host in {f"127.0.0.1:{port}", f"localhost:{port}", "127.0.0.1", "localhost"}

    def _json(self, code: int, data):
        payload = json.dumps(data, ensure_ascii=False).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(payload)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(payload)

    def _read_body(self):
        try:
            length = int(self.headers.get("Content-Length") or 0)
        except ValueError:
            raise ValueError("Invalid Content-Length")
        if length < 0 or length > MAX_BODY:
            raise ValueError("Request body too large")
        raw = self.rfile.read(length) if length else b"{}"
        return json.loads(raw.decode("utf-8-sig"))

    def _file(self, path: Path):
        data = path.read_bytes()
        ctype = mimetypes.guess_type(str(path))[0] or "application/octet-stream"
        if ctype.startswith("text/") or ctype in ("application/javascript", "application/json"):
            ctype += "; charset=utf-8"
        self.send_response(200)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(data)))
        self.send_header("X-Content-Type-Options", "nosniff")
        self.end_headers()
        self.wfile.write(data)

    def do_OPTIONS(self):
        if not self._host_allowed():
            return self._json(403, {"error": "invalid host"})
        self.send_response(204)
        self.end_headers()

    def do_GET(self):
        if not self._host_allowed():
            return self._json(403, {"error": "invalid host"})
        parsed = urlparse(self.path)
        path = parsed.path
        if path == "/api/health":
            return self._json(200, {"ok": True, "name": "JARVIS", "version": "0.3"})
        if path == "/api/obsidian/status":
            return self._json(200, OBSIDIAN.status())
        if path == "/api/llm/status":
            return self._json(200, ORCH.llm_status())
        if path == "/api/tasks":
            return self._json(200, STORE.list_tasks())
        if path == "/api/memory":
            query = parse_qs(parsed.query).get("q", [""])[0][:200]
            return self._json(200, STORE.list_memories(query))
        if path == "/api/audit":
            with STORE.connection() as con:
                rows = con.execute(
                    "SELECT event,details,created_at FROM audit_log ORDER BY created_at DESC LIMIT 100"
                ).fetchall()
            return self._json(200, [dict(row) for row in rows])
        if path in ("/", "/index.html"):
            return self._file(FRONTEND / "index.html")
        if path.startswith("/static/"):
            relative = path[len("/static/"):]
            if relative not in {"app.js", "style.css"}:
                return self._json(404, {"error": "not found"})
            return self._file(FRONTEND / relative)
        return self._json(404, {"error": "not found"})

    def do_POST(self):
        if not self._host_allowed():
            return self._json(403, {"error": "invalid host"})
        parsed = urlparse(self.path)
        try:
            body = self._read_body()
        except (ValueError, UnicodeDecodeError, json.JSONDecodeError) as exc:
            return self._json(400, {"ok": False, "error": str(exc)})

        if not isinstance(body, dict):
            return self._json(400, {"ok": False, "error": "JSON object required"})
        if parsed.path == "/api/chat":
            message = str(body.get("message") or body.get("text") or "")[:12000]
            return self._json(200, ORCH.handle(message))
        if parsed.path == "/api/tasks":
            try:
                item = STORE.add_task(str(body.get("title") or ""), str(body.get("details") or "")[:4000])
                return self._json(201, item)
            except ValueError as exc:
                return self._json(400, {"error": str(exc)})
        if parsed.path == "/api/memory":
            try:
                item = STORE.add_memory(str(body.get("content") or ""), str(body.get("tags") or "")[:500])
                return self._json(201, item)
            except ValueError as exc:
                return self._json(400, {"error": str(exc)})
        if parsed.path == "/api/obsidian/read":
            try:
                content = OBSIDIAN.read_note(str(body.get("path") or ""))
                return self._json(200, {"ok": True, "content": content})
            except Exception as exc:
                return self._json(400, {"ok": False, "error": str(exc)})
        if parsed.path == "/api/obsidian/write":
            try:
                result = OBSIDIAN.write_note(
                    str(body.get("path") or ""),
                    str(body.get("content") or ""),
                    append=bool(body.get("append")),
                )
                return self._json(200, result)
            except Exception as exc:
                return self._json(400, {"ok": False, "error": str(exc)})
        if parsed.path == "/api/obsidian/search":
            try:
                results = OBSIDIAN.search(str(body.get("query") or "")[:200])
                return self._json(200, {"ok": True, "results": results})
            except Exception as exc:
                return self._json(400, {"ok": False, "error": str(exc)})
        return self._json(404, {"error": "not found"})

    def do_PATCH(self):
        if not self._host_allowed():
            return self._json(403, {"error": "invalid host"})
        match = re.fullmatch(r"/api/tasks/([0-9a-fA-F-]{36})", urlparse(self.path).path)
        if not match:
            return self._json(404, {"error": "not found"})
        item = STORE.toggle_task(match.group(1))
        if item is None:
            return self._json(404, {"error": "task not found"})
        return self._json(200, item)

    def do_DELETE(self):
        if not self._host_allowed():
            return self._json(403, {"error": "invalid host"})
        match = re.fullmatch(r"/api/tasks/([0-9a-fA-F-]{36})", urlparse(self.path).path)
        if not match:
            return self._json(404, {"error": "not found"})
        if not STORE.delete_task(match.group(1)):
            return self._json(404, {"error": "task not found"})
        return self._json(200, {"deleted": True})


def main():
    host = str(SETTINGS.get("server", {}).get("host", "127.0.0.1"))
    port = int(SETTINGS.get("server", {}).get("port", 8765))
    if host not in {"127.0.0.1", "localhost"}:
        raise SystemExit("[JARVIS] Refusing non-local bind. Use 127.0.0.1 or localhost.")
    if not 1 <= port <= 65535:
        raise SystemExit("[JARVIS] Invalid port in config.")
    httpd = ThreadingHTTPServer((host, port), Handler)
    print(f"[JARVIS] http://{host}:{port}")
    print(f"[JARVIS] Database: {DATA_PATH}")
    print(f"[JARVIS] Obsidian mode: {SETTINGS.get('obsidian', {}).get('mode', 'rest')}")
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\n[JARVIS] Shutting down.")
    finally:
        httpd.server_close()


if __name__ == "__main__":
    main()

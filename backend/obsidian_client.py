"""Obsidian bridge for JARVIS: Local REST API or filesystem."""
from __future__ import annotations
import json, ssl, urllib.parse, urllib.request
from pathlib import Path
from typing import Any, Optional

class ObsidianClient:
    def __init__(self, config: dict):
        self.mode = config.get("mode", "rest")
        self.rest = config.get("rest", {})
        self.fs = config.get("filesystem", {})
        self._vault: Optional[Path] = None
        if self.mode == "filesystem":
            path = self.fs.get("vault_path") or ""
            self._vault = Path(path).expanduser() if path else None

    def status(self) -> dict[str, Any]:
        if self.mode == "rest":
            if not self.rest.get("api_key") or self.rest.get("api_key") == "PASTE_YOUR_LOCAL_REST_API_KEY_HERE":
                return {"ok": False, "connected": False, "configured": False, "mode": "rest", "error": "Local REST API key is not configured"}
            try:
                data = self._rest_get("/")
                return {"ok": True, "connected": True, "configured": True, "mode": "rest", "detail": data}
            except Exception as e:
                return {"ok": False, "connected": False, "configured": True, "mode": "rest", "error": str(e)[:240]}
        if self._vault and self._vault.is_dir():
            return {"ok": True, "mode": "filesystem", "vault": str(self._vault)}
        return {"ok": False, "mode": "filesystem", "error": "vault_path missing or not a directory"}

    def list_files(self, path: str = "") -> list[str]:
        if self.mode == "rest":
            raw = self._rest_get(f"/vault/{self._enc(path)}" if path else "/vault/")
            if isinstance(raw, dict) and "files" in raw:
                return raw["files"]
            if isinstance(raw, list):
                return raw
            return [str(raw)]
        return self._fs_list(path)

    def read_note(self, path: str) -> str:
        if self.mode == "rest":
            return self._rest_get_text(f"/vault/{self._enc(path)}")
        return self._fs_read(path)

    def write_note(self, path: str, content: str, append: bool = False) -> dict:
        if self.mode == "rest":
            method = "POST" if append else "PUT"
            self._rest_request(method, f"/vault/{self._enc(path)}", body=content, content_type="text/markdown")
            return {"ok": True, "path": path, "append": append}
        return self._fs_write(path, content, append)

    def search(self, query: str) -> list[dict]:
        if self.mode == "rest":
            try:
                raw = self._rest_request("POST", "/search/simple/", body=json.dumps({"query": query}), content_type="application/json")
                if isinstance(raw, list):
                    return raw
                if isinstance(raw, dict) and "results" in raw:
                    return raw["results"]
                return [{"raw": raw}]
            except Exception:
                return self._fs_search(query) if self._vault else []
        return self._fs_search(query)

    def _headers(self, content_type: Optional[str] = None) -> dict:
        h = {"Authorization": f"Bearer {self.rest.get('api_key', '')}"}
        if content_type:
            h["Content-Type"] = content_type
        return h

    def _url(self, path: str) -> str:
        base = self.rest.get("base_url", "https://127.0.0.1:27124").rstrip("/")
        if not path.startswith("/"):
            path = "/" + path
        return base + path

    def _ctx(self) -> Optional[ssl.SSLContext]:
        if self.rest.get("verify_ssl", False):
            return None
        ctx = ssl.create_default_context()
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE
        return ctx

    def _rest_request(self, method: str, path: str, body: Optional[str] = None, content_type: Optional[str] = None) -> Any:
        data = body.encode("utf-8") if body is not None else None
        req = urllib.request.Request(self._url(path), data=data, headers=self._headers(content_type), method=method)
        with urllib.request.urlopen(req, context=self._ctx(), timeout=15) as resp:
            raw = resp.read().decode("utf-8", errors="replace")
            if not raw:
                return {}
            try:
                return json.loads(raw)
            except json.JSONDecodeError:
                return raw

    def _rest_get(self, path: str) -> Any:
        return self._rest_request("GET", path)

    def _rest_get_text(self, path: str) -> str:
        req = urllib.request.Request(self._url(path), headers=self._headers(), method="GET")
        with urllib.request.urlopen(req, context=self._ctx(), timeout=15) as resp:
            return resp.read().decode("utf-8", errors="replace")

    @staticmethod
    def _enc(path: str) -> str:
        parts = path.replace("\\", "/").strip("/").split("/")
        return "/".join(urllib.parse.quote(p) for p in parts if p)

    def _safe_path(self, rel: str) -> Path:
        if not self._vault:
            raise RuntimeError("vault_path not configured")
        normalized = str(rel or "").replace("\\", "/").strip("/")
        if not normalized or any(part in ("", ".", "..") for part in normalized.split("/")):
            raise ValueError("A safe relative vault path is required")
        root = self._vault.resolve()
        target = (root / normalized).resolve()
        if not target.is_relative_to(root):
            raise PermissionError("path escapes vault")
        return target

    def _fs_list(self, path: str) -> list[str]:
        root = self._safe_path(path) if path else self._vault
        assert root is not None
        if not root.exists():
            return []
        out = []
        for p in sorted(root.rglob("*.md")):
            out.append(str(p.relative_to(self._vault)).replace("\\", "/"))
        return out[:500]

    def _fs_read(self, path: str) -> str:
        return self._safe_path(path).read_text(encoding="utf-8")

    def _fs_write(self, path: str, content: str, append: bool) -> dict:
        target = self._safe_path(path)
        target.parent.mkdir(parents=True, exist_ok=True)
        if append and target.exists():
            with target.open("a", encoding="utf-8") as f:
                f.write(content)
        else:
            target.write_text(content, encoding="utf-8")
        return {"ok": True, "path": path, "append": append}

    def _fs_search(self, query: str) -> list[dict]:
        if not self._vault:
            return []
        q = query.lower()
        hits = []
        for p in self._vault.rglob("*.md"):
            try:
                text = p.read_text(encoding="utf-8", errors="ignore")
            except Exception:
                continue
            if q in text.lower() or q in str(p).lower():
                hits.append({"path": str(p.relative_to(self._vault)).replace("\\", "/"), "snippet": text[:200].replace("\n", " ")})
            if len(hits) >= 30:
                break
        return hits

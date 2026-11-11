"""High-level agent router."""
from __future__ import annotations
from typing import Any

class AgentRouter:
    def __init__(self, orchestrator, settings: dict, voice=None):
        self.orch = orchestrator
        self.settings = settings
        self.voice = voice

    def run(self, text: str, source: str = "text") -> dict[str, Any]:
        result = self.orch.handle((text or "").strip())
        result["source"] = source
        return result

    def plan(self, text: str) -> dict[str, Any]:
        t = (text or "").lower()
        if any(w in t for w in ("погод", "weather")):
            return {"agent": "tools.weather"}
        if any(w in t for w in ("задач", "task", "todo")):
            return {"agent": "tools.tasks"}
        if any(w in t for w in ("замет", "прочитай", "запиши", "найди")):
            return {"agent": "obsidian"}
        if any(w in t for w in ("почт", "email")):
            return {"agent": "email", "status": "planned"}
        if any(w in t for w in ("соцсет", "telegram", "twitter")):
            return {"agent": "social", "status": "planned"}
        return {"agent": "fallback"}

from __future__ import annotations
from datetime import datetime
from typing import Any

def time_tool(**kwargs) -> dict[str, Any]:
    return {"ok": True, "reply": f"Сейчас: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}", "tool": "time"}

def help_catalog(**kwargs) -> dict[str, Any]:
    text = (
        "**JARVIS — команды**\n"
        "• статус — Obsidian / система\n"
        "• список заметок / найди … / прочитай path.md\n"
        "• запиши в path.md: текст | добавь в path.md: текст\n"
        "• погода [город]\n"
        "• задачи | добавь задачу …\n"
        "• время\n"
        "• помощь\n\n"
        "**Голос:** нажми микрофон один раз, затем говори «Джарвис, …».\\n"
        "**LLM:** свободный диалог через локальную Ollama-модель.\\n"
        "**Ограничения:** письма, календарь и произвольные команды Windows пока не выполняются."
    )
    return {"ok": True, "reply": text, "tool": "help"}

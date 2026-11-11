"""Tasks in Obsidian JARVIS/Tasks.md"""
from __future__ import annotations
from datetime import datetime
from typing import Any

def tasks_tool(action: str = "list", text: str = "", obsidian=None, path: str = "JARVIS/Tasks.md", **kwargs) -> dict[str, Any]:
    if obsidian is None:
        return {"ok": False, "reply": "Obsidian не подключён.", "tool": "tasks"}
    action = (action or "list").lower()
    if action in ("list", "show", "список"):
        try:
            content = obsidian.read_note(path)
        except Exception:
            content = "# Tasks\n\n"
            try:
                obsidian.write_note(path, content, append=False)
            except Exception as e:
                return {"ok": False, "reply": f"Нет доступа к {path}: {e}", "tool": "tasks"}
        lines = [ln for ln in content.splitlines() if ln.strip().startswith("- [")]
        if not lines:
            return {"ok": True, "reply": "Список задач пуст. Скажи: добавь задачу …", "tool": "tasks"}
        return {"ok": True, "reply": "Задачи:\n" + "\n".join(lines[:50]), "tool": "tasks"}
    if action in ("add", "create", "добавь", "новая"):
        item = (text or "").strip()
        if not item:
            return {"ok": False, "reply": "Укажи текст задачи.", "tool": "tasks"}
        stamp = datetime.now().strftime("%Y-%m-%d")
        line = f"- [ ] {item} ({stamp})\n"
        try:
            try:
                obsidian.read_note(path)
            except Exception:
                obsidian.write_note(path, "# Tasks\n\n", append=False)
            obsidian.write_note(path, line, append=True)
            return {"ok": True, "reply": f"Задача добавлена → {path}\n{line.strip()}", "tool": "tasks"}
        except Exception as e:
            return {"ok": False, "reply": f"Не записал задачу: {e}", "tool": "tasks"}
    return {"ok": False, "reply": f"Неизвестное действие: {action}", "tool": "tasks"}

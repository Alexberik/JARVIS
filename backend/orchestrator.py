"""Simple command orchestrator for JARVIS MVP."""
from __future__ import annotations
import re
from datetime import datetime
from typing import Any
from .obsidian_client import ObsidianClient

class Orchestrator:
    def __init__(self, obsidian: ObsidianClient, settings: dict):
        self.obsidian = obsidian
        self.settings = settings
        self.handlers = [
            (re.compile(r"(статус|status|ping|подключ)", re.I), self._status),
            (re.compile(r"(список|list).*(замет|note|файл|file|vault)", re.I), self._list_notes),
            (re.compile(r"(найди|поиск|search|ищи)\s+(.+)", re.I), self._search),
            (re.compile(r"(прочитай|read|открой|open)\s+(.+)", re.I), self._read),
            (re.compile(r"(запиши|write|создай заметку|create note)\s+([^\n]+)", re.I), self._write_hint),
            (re.compile(r"(время|time|дата|date)", re.I), self._time),
            (re.compile(r"(помощь|help|команды|commands)", re.I), self._help),
        ]

    def handle(self, text: str) -> dict[str, Any]:
        text = (text or "").strip()
        if not text:
            return {"reply": "Слушаю. Скажи «помощь» для списка команд.", "tool": None}
        m_write = re.match(r"(?:запиши|write|сохрани)\s+(?:в\s+)?([^\s:]+\.md)\s*[:\-]\s*(.+)", text, re.I | re.S)
        if m_write:
            return self._write(m_write.group(1).strip(), m_write.group(2).strip())
        m_append = re.match(r"(?:добавь|append)\s+(?:в\s+)?([^\s:]+\.md)\s*[:\-]\s*(.+)", text, re.I | re.S)
        if m_append:
            return self._write(m_append.group(1).strip(), m_append.group(2).strip(), append=True)
        for pattern, fn in self.handlers:
            m = pattern.search(text)
            if m:
                return fn(m, text)
        return {"reply": "Пока режим команд (без LLM). Примеры: статус, список заметок, найди проект, прочитай Inbox.md, запиши в JARVIS/Log.md: текст, помощь.", "tool": None}

    def _status(self, m, text):
        st = self.obsidian.status()
        if st.get("ok"):
            reply = f"Obsidian подключён (режим: {st.get('mode')})."
            if st.get("vault"):
                reply += f" Vault: {st['vault']}"
        else:
            reply = f"Obsidian недоступен: {st.get('error', 'unknown')}. Проверь Local REST API / vault_path."
        return {"reply": reply, "tool": "obsidian.status", "data": st}

    def _list_notes(self, m, text):
        try:
            files = self.obsidian.list_files()
            preview = files[:40]
            more = len(files) - len(preview)
            lines = "\n".join(f"• {f}" for f in preview)
            if more > 0:
                lines += f"\n… и ещё {more}"
            return {"reply": f"Заметки в vault ({len(files)}):\n{lines}", "tool": "obsidian.list", "data": files}
        except Exception as e:
            return {"reply": f"Не удалось получить список: {e}", "tool": "obsidian.list", "error": str(e)}

    def _search(self, m, text):
        query = m.group(2).strip() if m.lastindex and m.lastindex >= 2 else text
        query = re.sub(r"^(в\s+obsidian|в\s+заметках)\s*", "", query, flags=re.I)
        try:
            hits = self.obsidian.search(query)
            if not hits:
                return {"reply": f"По запросу «{query}» ничего не найдено.", "tool": "obsidian.search", "data": []}
            lines = []
            for h in hits[:15]:
                if isinstance(h, dict):
                    path = h.get("path") or h.get("filename") or str(h)
                    snip = h.get("snippet") or h.get("content") or ""
                    lines.append(f"• {path}" + (f" — {snip[:80]}…" if snip else ""))
                else:
                    lines.append(f"• {h}")
            return {"reply": f"Найдено ({len(hits)}):\n" + "\n".join(lines), "tool": "obsidian.search", "data": hits}
        except Exception as e:
            return {"reply": f"Ошибка поиска: {e}", "tool": "obsidian.search", "error": str(e)}

    def _read(self, m, text):
        path = m.group(2).strip().strip("\"'").replace("заметку ", "").replace("note ", "")
        try:
            content = self.obsidian.read_note(path)
            preview = content if len(content) < 2500 else content[:2500] + "\n…[обрезано]"
            return {"reply": f"**{path}**\n\n{preview}", "tool": "obsidian.read", "data": {"path": path}}
        except Exception as e:
            return {"reply": f"Не прочитал «{path}»: {e}", "tool": "obsidian.read", "error": str(e)}

    def _write_hint(self, m, text):
        return {"reply": "Формат:\nзапиши в Folder/note.md: текст\nили\nдобавь в Inbox.md: ещё строка", "tool": None}

    def _write(self, path, content, append=False):
        try:
            self.obsidian.write_note(path, content if not append else "\n" + content, append=append)
            action = "дополнено" if append else "записано"
            return {"reply": f"Готово: {action} → {path}", "tool": "obsidian.write", "data": {"path": path}}
        except Exception as e:
            return {"reply": f"Ошибка записи: {e}", "tool": "obsidian.write", "error": str(e)}

    def _time(self, m, text):
        return {"reply": f"Сейчас: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}", "tool": "system.time"}

    def _help(self, m, text):
        return {"reply": "**Команды JARVIS (MVP)**\n• статус\n• список заметок\n• найди <запрос>\n• прочитай <path.md>\n• запиши в path.md: текст\n• добавь в path.md: текст\n• время", "tool": "help"}

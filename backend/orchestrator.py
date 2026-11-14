"""
JARVIS orchestrator — rule-based routing + tools.
Later: free-form via Ollama when no rule matches.
"""
from __future__ import annotations

import json
import re
import urllib.error
import urllib.request
from typing import Any, Callable

from .obsidian_client import ObsidianClient
from .tools.weather import weather_tool
from .tools.tasks import tasks_tool
from .tools.system_info import time_tool, help_catalog


class Orchestrator:
    def __init__(self, obsidian: ObsidianClient, settings: dict, store=None):
        self.obsidian = obsidian
        self.settings = settings
        self.store = store
        notes = (settings.get("obsidian") or {}).get("notes") or {}
        self.tasks_path = notes.get("tasks") or "Tasks.md"
        self.handlers: list[tuple[re.Pattern, Callable]] = [
            (re.compile(r"(статус|status|ping|подключ)", re.I), self._status),
            (re.compile(r"(список|list).*(замет|note|файл|file|vault)", re.I), self._list_notes),
            (re.compile(r"(найди|поиск|search|ищи)\s+(.+)", re.I), self._search),
            (re.compile(r"(прочитай|read|открой|open)\s+(.+)", re.I), self._read),
            (re.compile(r"(запиши|write|создай заметку)\s+([^\n]+)", re.I), self._write_hint),
            (re.compile(r"(погод\w*|weather)(?:\s+(.+))?", re.I), self._weather),
            (re.compile(r"(добавь задачу|создай задачу|поставь задачу|новая задача|task add)\s+(.+)", re.I), self._task_add),
            (re.compile(r"(задачи|tasks|todo|список задач)", re.I), self._task_list),
            (re.compile(r"(время|time|дата|date)", re.I), self._time),
            (re.compile(r"(помощь|help|команды|commands)", re.I), self._help),
        ]

    def handle(self, text: str) -> dict[str, Any]:
        text = (text or "").strip()
        if not text:
            return {"reply": "Слушаю. Скажи «помощь» для списка команд.", "tool": None}

        m_write = re.match(
            r"(?:запиши|write|сохрани)\s+(?:в\s+)?([^\s:]+\.md)\s*[:\-]\s*(.+)",
            text,
            re.I | re.S,
        )
        if m_write:
            return self._write(m_write.group(1).strip(), m_write.group(2).strip())

        m_append = re.match(
            r"(?:добавь|append)\s+(?:в\s+)?([^\s:]+\.md)\s*[:\-]\s*(.+)",
            text,
            re.I | re.S,
        )
        if m_append:
            return self._write(m_append.group(1).strip(), m_append.group(2).strip(), append=True)

        for pattern, fn in self.handlers:
            m = pattern.search(text)
            if m:
                return fn(m, text)

        llm_result = self._ask_llm(text)
        if llm_result:
            return llm_result
        return {
            "reply": (
                "Команда не распознана, а локальная LLM недоступна.\n"
                "Примеры: статус, погода, задачи, добавь задачу …, "
                "найди …, запиши в Log.md: текст, помощь."
            ),
            "tool": None,
        }

    def _ask_llm(self, user_text: str) -> dict[str, Any] | None:
        cfg = self.settings.get("llm") or {}
        provider = str(cfg.get("provider") or "none").lower()
        if provider != "ollama":
            return None
        base = str(cfg.get("ollama_base") or "http://127.0.0.1:11434").rstrip("/")
        model = str(cfg.get("model") or "llama3.2")
        timeout = max(5, min(int(cfg.get("timeout_seconds") or 45), 120))
        payload = {
            "model": model,
            "stream": False,
            "messages": [
                {
                    "role": "system",
                    "content": (
                        "Ты JARVIS, персональный голосовой помощник. Отвечай по-русски, "
                        "кратко и естественно. Ты работаешь локально на компьютере пользователя. "
                        "Не утверждай, что выполнил действие, если оно не было выполнено "
                        "инструментом. Не выдумывай доступ к файлам, почте, календарю или интернету. "
                        "Для задач, заметок и поиска используй только доступные команды JARVIS; "
                        "если пользователь просит недоступное действие, честно объясни ограничение. "
                        "Никогда не проси присылать пароли, API-ключи или секреты в чат."
                    ),
                },
                {"role": "user", "content": user_text[:12000]},
            ],
            "options": {"temperature": 0.4},
        }
        request = urllib.request.Request(
            base + "/api/chat",
            data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        try:
            with urllib.request.urlopen(request, timeout=timeout) as response:
                data = json.loads(response.read().decode("utf-8"))
            answer = str((data.get("message") or {}).get("content") or "").strip()
            if not answer:
                return None
            if self.store is not None:
                self.store.audit("llm.reply", f"model={model}; chars={len(answer)}")
            return {"reply": answer, "tool": "llm.chat", "model": model}
        except (urllib.error.URLError, TimeoutError, ValueError, KeyError) as exc:
            if self.store is not None:
                self.store.audit("llm.unavailable", str(exc)[:300])
            return {
                "reply": (
                    f"Локальная модель {model} сейчас недоступна. "
                    "Проверь, запущен ли Ollama и загружена ли модель."
                ),
                "tool": "llm.chat",
                "error": str(exc)[:300],
            }

    def llm_status(self) -> dict[str, Any]:
        cfg = self.settings.get("llm") or {}
        provider = str(cfg.get("provider") or "none").lower()
        model = str(cfg.get("model") or "llama3.2")
        if provider != "ollama":
            return {"ok": False, "provider": provider, "model": model, "reason": "provider_not_configured"}
        base = str(cfg.get("ollama_base") or "http://127.0.0.1:11434").rstrip("/")
        try:
            request = urllib.request.Request(base + "/api/tags", method="GET")
            with urllib.request.urlopen(request, timeout=2) as response:
                data = json.loads(response.read().decode("utf-8"))
            names = [str(item.get("name") or "") for item in data.get("models", [])]
            installed = any(name == model or name.startswith(model + ":") for name in names)
            return {
                "ok": installed, "provider": provider, "model": model,
                "installed_models": names[:30],
                "reason": "ready" if installed else "model_not_downloaded",
            }
        except Exception as exc:
            return {"ok": False, "provider": provider, "model": model, "reason": str(exc)[:200]}

    def _status(self, m, text):
        st = self.obsidian.status()
        voice = (self.settings.get("voice") or {}).get("enabled")
        llm = (self.settings.get("llm") or {}).get("provider")
        if st.get("ok"):
            reply = f"Obsidian подключён (режим: {st.get('mode')})."
            if st.get("vault"):
                reply += f" Vault: {st['vault']}"
        else:
            reply = f"Obsidian недоступен: {st.get('error', 'unknown')}."
        reply += f"\nLLM: {llm or 'none'} | Voice: {'on' if voice else 'off'}"
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

    def _weather(self, m, text):
        city = ""
        if m.lastindex and m.lastindex >= 2 and m.group(2):
            city = m.group(2).strip()
            city = re.sub(r"^(в|во)\s+", "", city, flags=re.I)
        if not city:
            city = ((self.settings.get("tools") or {}).get("weather") or {}).get("default_city") or "Tbilisi"
        return weather_tool(city=city)

    def _task_list(self, m, text):
        if self.store is not None:
            items = self.store.list_tasks()
            if not items:
                return {"reply": "Список задач пуст. Скажи: добавь задачу …", "tool": "tasks.list", "data": []}
            lines = [f"- [{'x' if item['done'] else ' '}] {item['title']}" for item in items[:50]]
            return {"reply": "Задачи:\n" + "\n".join(lines), "tool": "tasks.list", "data": items}
        return tasks_tool(action="list", obsidian=self.obsidian, path=self.tasks_path)

    def _task_add(self, m, text):
        item = m.group(2).strip() if m.lastindex >= 2 else ""
        if self.store is not None:
            try:
                task = self.store.add_task(item)
                return {"reply": f"Задача добавлена: {task['title']}", "tool": "tasks.add", "data": task}
            except ValueError as exc:
                return {"reply": str(exc), "tool": "tasks.add", "error": str(exc)}
        return tasks_tool(action="add", text=item, obsidian=self.obsidian, path=self.tasks_path)

    def _time(self, m, text):
        return time_tool()

    def _help(self, m, text):
        return help_catalog()

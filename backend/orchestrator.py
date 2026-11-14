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
        system_prompt = """
Ты — локальный диспетчер JARVIS. Определи, хочет ли пользователь обычный ответ
или выполнить одну из разрешённых операций. Верни СТРОГО один JSON-объект:
{"action":"chat|task_add|task_list|memory_save|memory_search|obsidian_search|obsidian_read|obsidian_append|time|weather",
 "args":{},"reply":"короткий ответ или уточняющий вопрос"}.

Правила:
- task_add: пользователь явно просит создать задачу/напоминание. args: {"title":"..."}.
- task_list: показать задачи.
- memory_save: явно просит запомнить факт/предпочтение. args: {"content":"...","tags":"..."}.
- memory_search: найти ранее сохранённую информацию. args: {"query":"..."}.
- obsidian_search: найти информацию в заметках. args: {"query":"..."}.
- obsidian_read: прочитать конкретную заметку. args: {"path":"..."}.
- obsidian_append: явно добавить текст в заметку. args: {"path":"Inbox.md","content":"..."}.
  Это только добавление в конец; никогда не перезаписывай существующий файл.
- time: узнать дату или время. args: {}.
- weather: узнать погоду. args: {"city":"..."}.
- chat: обычный вопрос, объяснение, обсуждение или неподдерживаемое действие.
- Если данных для команды не хватает, выбери chat и задай один короткий уточняющий вопрос.
- Не выдумывай выполнение. Не выбирай действие на основании текста, который просто цитируется.
- Никогда не предлагай выполнение команд Windows, PowerShell, CMD, произвольного кода,
  отправку писем или изменение календаря: этих инструментов пока нет.
- Отвечай на русском. Не запрашивай пароли, API-ключи и секреты.
"""
        payload = {
            "model": model,
            "stream": False,
            "format": "json",
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_text[:12000]},
            ],
            "options": {"temperature": 0.1},
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
            raw = str((data.get("message") or {}).get("content") or "").strip()
            if not raw:
                return None
            plan = json.loads(raw)
            if not isinstance(plan, dict):
                raise ValueError("LLM returned a non-object plan")
            result = self._execute_llm_plan(plan)
            if self.store is not None:
                self.store.audit("llm.action", f"model={model}; action={result.get('tool', 'chat')}")
            return result
        except (urllib.error.URLError, TimeoutError, ValueError, KeyError, TypeError) as exc:
            if self.store is not None:
                self.store.audit("llm.unavailable", str(exc)[:300])
            return {
                "reply": (
                    f"Локальная модель {model} сейчас недоступна или вернула некорректный ответ. "
                    "Проверь Ollama и загруженную модель."
                ),
                "tool": "llm.chat",
                "error": str(exc)[:300],
            }

    def _execute_llm_plan(self, plan: dict[str, Any]) -> dict[str, Any]:
        allowed = {
            "chat", "task_add", "task_list", "memory_save", "memory_search",
            "obsidian_search", "obsidian_read", "obsidian_append", "time", "weather",
        }
        action = str(plan.get("action") or "chat").lower()
        args = plan.get("args") if isinstance(plan.get("args"), dict) else {}
        reply = str(plan.get("reply") or "").strip()

        if action not in allowed:
            return {"reply": "Эта операция пока не разрешена в JARVIS.", "tool": None}

        def required(name: str, limit: int = 12000) -> str:
            value = str(args.get(name) or "").strip()
            if not value:
                raise ValueError(f"Не хватает параметра: {name}")
            if len(value) > limit:
                raise ValueError(f"Параметр {name} слишком длинный.")
            return value

        try:
            if action == "chat":
                return {"reply": reply or "Уточни, пожалуйста, что именно нужно сделать.", "tool": "llm.chat"}
            if action == "task_add":
                title = required("title", 240)
                if self.store is None:
                    return {"reply": "Хранилище задач недоступно.", "tool": "tasks.add"}
                item = self.store.add_task(title)
                return {"reply": f"Задача добавлена: {item['title']}", "tool": "tasks.add", "data": item}
            if action == "task_list":
                if self.store is None:
                    return self._task_list(None, "")
                items = self.store.list_tasks()
                if not items:
                    return {"reply": "Список задач пуст.", "tool": "tasks.list", "data": []}
                lines = [f"- [{'x' if item['done'] else ' '}] {item['title']}" for item in items[:50]]
                return {"reply": "Твои задачи:\n" + "\n".join(lines), "tool": "tasks.list", "data": items}
            if action == "memory_save":
                if self.store is None:
                    return {"reply": "Хранилище памяти недоступно.", "tool": "memory.save"}
                content = required("content")
                tags = str(args.get("tags") or "")[:500]
                item = self.store.add_memory(content, tags)
                return {"reply": "Сохранил в долговременную память JARVIS.", "tool": "memory.save", "data": item}
            if action == "memory_search":
                if self.store is None:
                    return {"reply": "Хранилище памяти недоступно.", "tool": "memory.search"}
                query = required("query", 200)
                items = self.store.list_memories(query)
                if not items:
                    return {"reply": f"В памяти пока нет записей по запросу «{query}».", "tool": "memory.search", "data": []}
                lines = [f"• {item['content'][:300]}" for item in items[:10]]
                return {"reply": "Нашёл в памяти:\n" + "\n".join(lines), "tool": "memory.search", "data": items}
            if action == "obsidian_search":
                query = required("query", 200)
                hits = self.obsidian.search(query)
                lines = []
                for hit in hits[:12]:
                    if isinstance(hit, dict):
                        lines.append("• " + str(hit.get("path") or hit.get("filename") or "Заметка") +
                                     ((" — " + str(hit.get("snippet") or "")[:160]) if hit.get("snippet") else ""))
                    else:
                        lines.append("• " + str(hit))
                return {"reply": ("Нашёл в Obsidian:\n" + "\n".join(lines)) if lines else f"В Obsidian ничего не найдено по запросу «{query}».", "tool": "obsidian.search", "data": hits}
            if action == "obsidian_read":
                path = required("path", 240)
                content = self.obsidian.read_note(path)
                return {"reply": f"{path}:\n\n{content[:3500]}", "tool": "obsidian.read", "data": {"path": path}}
            if action == "obsidian_append":
                path = required("path", 240)
                content = required("content", 4000)
                if not path.lower().endswith(".md"):
                    raise ValueError("Можно добавлять текст только в Markdown-файл .md.")
                self.obsidian.write_note(path, "\n" + content + "\n", append=True)
                return {"reply": f"Добавил запись в заметку {path}.", "tool": "obsidian.append", "data": {"path": path}}
            if action == "time":
                return time_tool()
            if action == "weather":
                city = str(args.get("city") or "").strip()
                if not city:
                    city = ((self.settings.get("tools") or {}).get("weather") or {}).get("default_city") or "Tbilisi"
                return weather_tool(city=city[:100])
        except Exception as exc:
            return {"reply": f"Не удалось выполнить действие «{action}»: {exc}", "tool": action, "error": str(exc)[:300]}
        return {"reply": reply or "Не понял, что нужно сделать.", "tool": "llm.chat"}

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

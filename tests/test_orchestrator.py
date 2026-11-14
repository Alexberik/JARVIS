from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from backend.orchestrator import Orchestrator
from backend.storage import Store


class FakeObsidian:
    def __init__(self):
        self.notes = {"Inbox.md": "# Inbox\n"}
        self.appended = []

    def search(self, query):
        return [{"path": "Inbox.md", "snippet": f"match: {query}"}]

    def read_note(self, path):
        if path not in self.notes:
            raise FileNotFoundError(path)
        return self.notes[path]

    def write_note(self, path, content, append=False):
        if append:
            self.notes[path] = self.notes.get(path, "") + content
        else:
            self.notes[path] = content
        self.appended.append((path, content, append))
        return {"ok": True}


class LLMPlanTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.store = Store(Path(self.tmp.name) / "jarvis-test.db")
        self.obsidian = FakeObsidian()
        self.orch = Orchestrator(
            self.obsidian,
            {
                "llm": {"provider": "ollama", "model": "llama3.2"},
                "tools": {"weather": {"default_city": "Tbilisi"}},
            },
            self.store,
        )

    def tearDown(self):
        self.tmp.cleanup()

    def test_task_add_executes_and_persists(self):
        result = self.orch._execute_llm_plan({
            "action": "task_add", "args": {"title": "Позвонить поставщику"}
        })
        self.assertEqual(result["tool"], "tasks.add")
        self.assertEqual(self.store.list_tasks()[0]["title"], "Позвонить поставщику")

    def test_memory_save_persists(self):
        result = self.orch._execute_llm_plan({
            "action": "memory_save",
            "args": {"content": "Предпочитаю русский язык", "tags": "preferences"},
        })
        self.assertEqual(result["tool"], "memory.save")
        self.assertEqual(self.store.list_memories()[0]["content"], "Предпочитаю русский язык")

    def test_memory_search_returns_matching_entry(self):
        self.store.add_memory("Рабочий проект JARVIS", "project")
        result = self.orch._execute_llm_plan({
            "action": "memory_search", "args": {"query": "JARVIS"}
        })
        self.assertIn("Рабочий проект JARVIS", result["reply"])

    def test_obsidian_append_only(self):
        result = self.orch._execute_llm_plan({
            "action": "obsidian_append",
            "args": {"path": "Inbox.md", "content": "Позвонить поставщику"},
        })
        self.assertEqual(result["tool"], "obsidian.append")
        self.assertTrue(self.obsidian.notes["Inbox.md"].endswith("Позвонить поставщику\n"))
        self.assertTrue(self.obsidian.appended[-1][2])

    def test_obsidian_append_rejects_non_markdown(self):
        result = self.orch._execute_llm_plan({
            "action": "obsidian_append",
            "args": {"path": "notes.txt", "content": "text"},
        })
        self.assertIn("только в Markdown", result["reply"])
        self.assertEqual(self.obsidian.appended, [])

    def test_unknown_action_is_not_executed(self):
        result = self.orch._execute_llm_plan({
            "action": "run_powershell", "args": {"command": "Remove-Item *"}
        })
        self.assertIsNone(result["tool"])
        self.assertEqual(self.obsidian.appended, [])

    def test_chat_does_not_claim_execution(self):
        result = self.orch._execute_llm_plan({
            "action": "chat", "args": {}, "reply": "Я могу объяснить, как это сделать."
        })
        self.assertEqual(result["tool"], "llm.chat")
        self.assertIn("объяснить", result["reply"])


if __name__ == "__main__":
    unittest.main()

"""Small SQLite store for JARVIS tasks, memories, and audit events."""
from __future__ import annotations

import sqlite3
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


class Store:
    def __init__(self, path: Path):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.initialize()

    def connect(self) -> sqlite3.Connection:
        con = sqlite3.connect(self.path, timeout=10)
        con.row_factory = sqlite3.Row
        con.execute("PRAGMA foreign_keys=ON")
        return con

    def initialize(self) -> None:
        with self.connect() as con:
            con.execute("PRAGMA journal_mode=WAL")
            con.executescript("""
                CREATE TABLE IF NOT EXISTS tasks (
                    id TEXT PRIMARY KEY,
                    title TEXT NOT NULL,
                    details TEXT NOT NULL DEFAULT '',
                    done INTEGER NOT NULL DEFAULT 0,
                    created_at TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS memories (
                    id TEXT PRIMARY KEY,
                    content TEXT NOT NULL,
                    tags TEXT NOT NULL DEFAULT '',
                    created_at TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS audit_log (
                    id TEXT PRIMARY KEY,
                    event TEXT NOT NULL,
                    details TEXT NOT NULL DEFAULT '',
                    created_at TEXT NOT NULL
                );
            """)

    @staticmethod
    def now() -> str:
        return datetime.now(timezone.utc).isoformat()

    def audit(self, event: str, details: str = "") -> None:
        with self.connect() as con:
            con.execute(
                "INSERT INTO audit_log(id,event,details,created_at) VALUES(?,?,?,?)",
                (str(uuid.uuid4()), event, details[:1000], self.now()),
            )

    def list_tasks(self) -> list[dict[str, Any]]:
        with self.connect() as con:
            rows = con.execute(
                "SELECT id,title,details,done,created_at FROM tasks ORDER BY created_at DESC"
            ).fetchall()
        return [dict(row) for row in rows]

    def add_task(self, title: str, details: str = "") -> dict[str, Any]:
        title = title.strip()
        if not title:
            raise ValueError("Task title is required")
        if len(title) > 240 or len(details) > 4000:
            raise ValueError("Task title/details exceed the allowed length")
        item = {
            "id": str(uuid.uuid4()), "title": title, "details": details,
            "done": 0, "created_at": self.now(),
        }
        with self.connect() as con:
            con.execute(
                "INSERT INTO tasks(id,title,details,done,created_at) VALUES(?,?,?,?,?)",
                (item["id"], item["title"], item["details"], item["done"], item["created_at"]),
            )
        self.audit("task.created", title)
        return item

    def toggle_task(self, task_id: str) -> dict[str, Any] | None:
        with self.connect() as con:
            row = con.execute("SELECT done FROM tasks WHERE id=?", (task_id,)).fetchone()
            if row is None:
                return None
            done = 0 if row["done"] else 1
            con.execute("UPDATE tasks SET done=? WHERE id=?", (done, task_id))
        self.audit("task.toggled", task_id)
        return {"id": task_id, "done": done}

    def delete_task(self, task_id: str) -> bool:
        with self.connect() as con:
            cur = con.execute("DELETE FROM tasks WHERE id=?", (task_id,))
        if cur.rowcount:
            self.audit("task.deleted", task_id)
            return True
        return False

    def list_memories(self, query: str = "") -> list[dict[str, Any]]:
        with self.connect() as con:
            if query:
                pattern = f"%{query}%"
                rows = con.execute(
                    "SELECT id,content,tags,created_at FROM memories "
                    "WHERE content LIKE ? OR tags LIKE ? ORDER BY created_at DESC LIMIT 200",
                    (pattern, pattern),
                ).fetchall()
            else:
                rows = con.execute(
                    "SELECT id,content,tags,created_at FROM memories "
                    "ORDER BY created_at DESC LIMIT 200"
                ).fetchall()
        return [dict(row) for row in rows]

    def add_memory(self, content: str, tags: str = "") -> dict[str, Any]:
        content = content.strip()
        if not content:
            raise ValueError("Memory content is required")
        if len(content) > 12000 or len(tags) > 500:
            raise ValueError("Memory content/tags exceed the allowed length")
        item = {"id": str(uuid.uuid4()), "content": content, "tags": tags, "created_at": self.now()}
        with self.connect() as con:
            con.execute(
                "INSERT INTO memories(id,content,tags,created_at) VALUES(?,?,?,?)",
                (item["id"], item["content"], item["tags"], item["created_at"]),
            )
        self.audit("memory.saved", item["id"])
        return item

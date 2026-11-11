from __future__ import annotations

import os
import sqlite3
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import httpx
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

ROOT = Path(__file__).resolve().parent.parent
load_dotenv(ROOT / ".env")
DB_PATH = Path(os.getenv("DATABASE_PATH", "data/jarvis.db"))
if not DB_PATH.is_absolute():
    DB_PATH = ROOT / DB_PATH
DB_PATH.parent.mkdir(parents=True, exist_ok=True)

app = FastAPI(title="JARVIS AI", version="0.2.0")
app.mount("/static", StaticFiles(directory=ROOT / "frontend"), name="static")


def now() -> str:
    return datetime.now(timezone.utc).isoformat()


def db() -> sqlite3.Connection:
    con = sqlite3.connect(DB_PATH)
    con.row_factory = sqlite3.Row
    return con


def init_db() -> None:
    with db() as con:
        con.execute("""CREATE TABLE IF NOT EXISTS tasks (
            id TEXT PRIMARY KEY, title TEXT NOT NULL, details TEXT NOT NULL DEFAULT '',
            done INTEGER NOT NULL DEFAULT 0, created_at TEXT NOT NULL)""")
        con.execute("""CREATE TABLE IF NOT EXISTS memories (
            id TEXT PRIMARY KEY, content TEXT NOT NULL, tags TEXT NOT NULL DEFAULT '',
            created_at TEXT NOT NULL)""")
        con.execute("""CREATE TABLE IF NOT EXISTS audit_log (
            id TEXT PRIMARY KEY, event TEXT NOT NULL, details TEXT NOT NULL,
            created_at TEXT NOT NULL)""")


init_db()


def audit(event: str, details: str = "") -> None:
    with db() as con:
        con.execute("INSERT INTO audit_log(id,event,details,created_at) VALUES(?,?,?,?)",
                    (str(uuid.uuid4()), event, details[:4000], now()))


class TaskIn(BaseModel):
    title: str = Field(min_length=1, max_length=240)
    details: str = Field(default="", max_length=4000)


class MemoryIn(BaseModel):
    content: str = Field(min_length=1, max_length=12000)
    tags: str = Field(default="", max_length=500)


class ChatIn(BaseModel):
    message: str = Field(min_length=1, max_length=12000)


class ObsidianNoteIn(BaseModel):
    path: str = Field(min_length=1, max_length=240)
    content: str = Field(min_length=1, max_length=30000)


@app.get("/")
def home():
    return FileResponse(ROOT / "frontend" / "index.html")


@app.get("/api/health")
def health():
    return {"status": "ok", "app": "JARVIS AI", "version": "0.2.0", "time": now()}


@app.get("/api/tasks")
def list_tasks():
    with db() as con:
        rows = con.execute("SELECT * FROM tasks ORDER BY created_at DESC").fetchall()
    return [dict(r) for r in rows]


@app.post("/api/tasks")
def create_task(item: TaskIn):
    task_id = str(uuid.uuid4())
    with db() as con:
        con.execute("INSERT INTO tasks(id,title,details,created_at) VALUES(?,?,?,?)",
                    (task_id, item.title, item.details, now()))
    audit("task.created", item.title)
    return {"id": task_id, **item.model_dump(), "done": 0}


@app.patch("/api/tasks/{task_id}")
def toggle_task(task_id: str):
    with db() as con:
        row = con.execute("SELECT done FROM tasks WHERE id=?", (task_id,)).fetchone()
        if not row:
            raise HTTPException(404, "Task not found")
        new_value = 0 if row["done"] else 1
        con.execute("UPDATE tasks SET done=? WHERE id=?", (new_value, task_id))
    audit("task.toggled", task_id)
    return {"id": task_id, "done": new_value}


@app.delete("/api/tasks/{task_id}")
def delete_task(task_id: str):
    with db() as con:
        cur = con.execute("DELETE FROM tasks WHERE id=?", (task_id,))
        if cur.rowcount == 0:
            raise HTTPException(404, "Task not found")
    audit("task.deleted", task_id)
    return {"deleted": True}


@app.get("/api/memory")
def list_memory(q: str = ""):
    with db() as con:
        if q:
            rows = con.execute(
                "SELECT * FROM memories WHERE content LIKE ? OR tags LIKE ? ORDER BY created_at DESC",
                (f"%{q}%", f"%{q}%")).fetchall()
        else:
            rows = con.execute("SELECT * FROM memories ORDER BY created_at DESC LIMIT 100").fetchall()
    return [dict(r) for r in rows]


@app.post("/api/memory")
def save_memory(item: MemoryIn):
    memory_id = str(uuid.uuid4())
    created = now()
    with db() as con:
        con.execute("INSERT INTO memories(id,content,tags,created_at) VALUES(?,?,?,?)",
                    (memory_id, item.content, item.tags, created))
    audit("memory.saved", memory_id)
    return {"id": memory_id, **item.model_dump(), "created_at": created}


def obsidian_configured() -> bool:
    return bool(os.getenv("OBSIDIAN_API_KEY"))


def obsidian_client() -> httpx.AsyncClient:
    return httpx.AsyncClient(
        base_url=os.getenv("OBSIDIAN_BASE_URL", "https://127.0.0.1:27124").rstrip("/"),
        headers={"Authorization": f"Bearer {os.getenv('OBSIDIAN_API_KEY', '')}"},
        verify=os.getenv("OBSIDIAN_VERIFY_TLS", "false").lower() == "true",
        timeout=15.0,
    )


@app.get("/api/obsidian/status")
async def obsidian_status():
    if not obsidian_configured():
        return {"configured": False, "connected": False,
                "message": "Configure the Obsidian Local REST API values in local .env"}
    try:
        async with obsidian_client() as client:
            response = await client.get("/")
        return {"configured": True, "connected": response.is_success,
                "status_code": response.status_code}
    except Exception as exc:
        return {"configured": True, "connected": False, "message": str(exc)[:240]}


@app.get("/api/obsidian/search")
async def obsidian_search(q: str):
    if not obsidian_configured():
        raise HTTPException(503, "Obsidian Local REST API is not configured")
    async with obsidian_client() as client:
        response = await client.post("/search/simple/", json={"query": q})
    if not response.is_success:
        raise HTTPException(response.status_code, response.text[:500])
    return response.json()


@app.post("/api/obsidian/note")
async def create_obsidian_note(item: ObsidianNoteIn):
    if not obsidian_configured():
        raise HTTPException(503, "Obsidian Local REST API is not configured")
    relative = Path(item.path.replace("\\", "/"))
    if relative.is_absolute() or any(part in ("..", "") for part in relative.parts):
        raise HTTPException(400, "Invalid note path")
    safe_path = relative.as_posix().lstrip("/")
    async with obsidian_client() as client:
        response = await client.put(f"/vault/{safe_path}", content=item.content,
                                    headers={"Content-Type": "text/markdown"})
    if not response.is_success:
        raise HTTPException(response.status_code, response.text[:500])
    audit("obsidian.note_created", safe_path)
    return {"created": True, "path": safe_path}


@app.get("/api/audit")
def list_audit():
    with db() as con:
        rows = con.execute("SELECT * FROM audit_log ORDER BY created_at DESC LIMIT 100").fetchall()
    return [dict(r) for r in rows]


@app.post("/api/chat")
async def chat(item: ChatIn):
    key = os.getenv("OPENAI_API_KEY")
    if not key:
        return {"configured": False,
                "reply": "GPT API is not configured. Add OPENAI_API_KEY to your local .env file."}
    base = os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1").rstrip("/")
    model = os.getenv("OPENAI_MODEL", "gpt-4.1-mini")
    payload: dict[str, Any] = {
        "model": model,
        "messages": [
            {"role": "system", "content": "You are JARVIS, a concise personal assistant. Never claim to have performed an external action unless a connected tool confirms it. Ask for approval before sensitive actions. You cannot execute tools that are not explicitly connected."},
            {"role": "user", "content": item.message},
        ],
    }
    async with httpx.AsyncClient(timeout=60) as client:
        response = await client.post(f"{base}/chat/completions", json=payload,
                                     headers={"Authorization": f"Bearer {key}"})
    if not response.is_success:
        raise HTTPException(response.status_code, response.text[:500])
    data = response.json()
    reply = data["choices"][0]["message"]["content"]
    audit("chat.completed", item.message[:300])
    return {"configured": True, "reply": reply}

# JARVIS architecture

## Current runtime
- Windows launcher: `start.bat`.
- Local HTTP server: `backend/server.py` (Python standard library).
- Browser cockpit: `frontend/`.
- SQLite store: `backend/storage.py` → `data/jarvis.db` (tasks, memory entries, audit events).
- Obsidian adapter: `backend/obsidian_client.py` (Local REST API or filesystem mode).
- Rule-based command router: `backend/orchestrator.py`.

## Data boundaries
- SQLite tasks are the single source for tasks shown in the cockpit and handled by chat commands.
- SQLite memory entries are local operational memory for the cockpit.
- Markdown files under `JARVIS/` are the human-readable knowledge base, project notes, inbox, log, and curated memory.
- Obsidian API credentials remain in ignored `config/settings.json`.
- Personal vault settings and root-level personal folders are not committed.

## Local API
- Binds only to `127.0.0.1` or `localhost`.
- Rejects unexpected Host headers.
- Serves only the known frontend assets.
- No permissive cross-origin access is enabled.
- Request bodies are limited to 1 MB.
- Note paths are validated to prevent traversal outside the vault.

## Planned adapters
OpenAI-compatible LLM, Gmail/Google Calendar OAuth, MCP, n8n, sherpa-onnx, Piper, browser automation, and desktop automation are not part of the current working baseline. Add each behind an explicit permission policy and test before marking it connected.

## Permission boundaries
- Local task and memory operations are available in the local cockpit.
- Obsidian note read/search/write is available only after configuring the local plugin key.
- Email sending, calendar writes, social publishing, purchases, financial actions, shell execution, desktop control, and remote access are not enabled in this baseline.

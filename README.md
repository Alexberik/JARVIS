# JARVIS AI

Local-first personal assistant for Windows: browser cockpit, Obsidian bridge, rule-based command router, and a modular foundation for voice and future AI integrations.

## Current working entry point

Use the included Windows launcher:

```powershell
.`start.bat
```

Then open http://127.0.0.1:8765.

The launcher starts `backend/server.py` (Python standard library; no pip packages are required for this entry point). Keep the server window open while using JARVIS.

## Connect Obsidian

1. Open Obsidian Desktop and keep your vault open.
2. In Obsidian, open Settings → Community plugins → Browse.
3. Install and enable **Local REST API**.
4. Open Settings → Local REST API and copy the API key shown there.
5. In the repository, copy the example settings file:

```powershell
Copy-Item config\settings.example.json config\settings.json
notepad config\settings.json
```

6. In `config/settings.json`, keep `obsidian.mode` set to `rest`, set `obsidian.rest.base_url` to the exact local URL shown by the plugin (normally `https://127.0.0.1:27124`), and paste the key into `obsidian.rest.api_key`.
7. Save the file and restart JARVIS.

**Never send the API key in chat, notes, screenshots, or GitHub.** The local `config/settings.json` is now ignored by Git. Do not expose the Obsidian API or JARVIS server to the public internet.

## Current capabilities and limits

- Browser cockpit with dark graphite/cyan styling.
- Local Obsidian status, note read/write, and search through the Local REST API bridge.
- Rule-based commands for status, notes, weather, tasks, and time.
- Browser speech input where supported.
- Voice engines (sherpa-onnx and Piper) are scaffolding only; model files and runtime wiring are not yet complete.
- Gmail, Google Calendar, social publishing, unrestricted desktop control, and a full MCP client are not connected in this baseline.
- The current `start.bat` runtime does not yet use GPT/Ollama for free-form chat. The separate FastAPI `backend/main.py` entry point is an experimental alternative and is not the recommended launcher yet.

## Project layout

- `backend/server.py` — current local HTTP server and frontend asset routing.
- `backend/obsidian_client.py` — Obsidian REST/filesystem adapter.
- `backend/orchestrator.py` — rule-based command router.
- `backend/tools/` — local tools.
- `backend/voice/` — voice pipeline scaffold.
- `frontend/` — browser interface, styles, and JavaScript.
- `config/settings.example.json` — safe configuration template.
- `config/settings.json` — local configuration; do not commit.
- `obsidian-vault/` and `docs/obsidian/` — project documentation notes.

## Security

- Bind local services to `127.0.0.1`.
- Never commit API keys, OAuth tokens, private notes, databases, or logs.
- External side effects must require explicit approval.
- Shell execution, public remote access, financial actions, and destructive file operations remain disabled until separately secured and tested.

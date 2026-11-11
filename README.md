# JARVIS AI

Local-first personal assistant with a hybrid Windows runtime, browser cockpit, voice input/output, SQLite memory, and Obsidian knowledge base.

## Current baseline
- FastAPI backend and browser UI foundation
- Local SQLite tasks and memory
- Optional Obsidian Local REST API adapter
- Optional OpenAI-compatible chat adapter
- Browser speech support where available
- Integration roadmap and security policy

## Windows setup
1. Install Python 3.11+.
2. Open PowerShell in this repository.
3. Run:

```powershell
py -3.11 -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r backend\requirements.txt
Copy-Item .env.example .env
uvicorn backend.main:app --reload --host 127.0.0.1 --port 8000
```

Open http://127.0.0.1:8000. Keep the host on 127.0.0.1; do not expose this development server to the internet.

## Obsidian
Install and enable the Local REST API community plugin. Copy the plugin's displayed local URL and API key into your local .env file. Never commit .env or put API keys in notes. The obsidian-vault folder contains the JARVIS project knowledge base.

## Planned modules
Google OAuth (Gmail/Calendar), MCP tools, sherpa-onnx offline speech recognition, Piper offline speech synthesis, n8n workflows, isolated browser automation, and approval-gated desktop automation.

## Safety
No unrestricted shell execution. Unknown MCP tools are denied. Email sending, calendar writes, social publishing, financial actions, and destructive operations require explicit approval. Browser/desktop automation and remote access remain disabled until their security controls are implemented and tested.

See SECURITY.md, docs/ARCHITECTURE.md, and docs/ROADMAP.md.

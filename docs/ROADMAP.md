# Roadmap

## Milestone 0 — Foundation
- [x] Create repository and project structure
- [x] Define local-first hybrid architecture
- [x] Define Obsidian vault layout
- [ ] Validate backend and UI on the user's Windows machine
- [ ] Configure local Obsidian Local REST API

## Milestone 1 — Assistant core
- [ ] Complete chat orchestration and provider abstraction
- [ ] Tasks, reminders, and recurring jobs
- [ ] Searchable memory with sources and timestamps
- [ ] Obsidian sync with conflict handling
- [ ] Audit log and action approval inbox

## Milestone 2 — Voice
- [ ] Browser voice UX
- [ ] Optional sherpa-onnx offline speech recognition
- [ ] Optional Piper offline speech synthesis
- [ ] Wake-word and push-to-talk modes

## Milestone 3 — Productivity integrations
- [ ] Google OAuth
- [ ] Gmail read/search; sending only after approval
- [ ] Google Calendar read/create; writes after approval
- [ ] n8n workflow adapter
- [ ] MCP client with per-tool allow-list

## Milestone 4 — Controlled automation
- [ ] Browser-use isolated browser profile
- [ ] PyAutoGUI adapter with exact-action approval tokens
- [ ] Per-action audit records
- [ ] No unrestricted terminal or arbitrary code execution

## Milestone 5 — Remote access
- [ ] Authentication and session management
- [ ] CSRF, origin controls, rate limiting
- [ ] TLS and private tunnel
- [ ] Device approval and revocation
- [ ] Security review before enabling remote access

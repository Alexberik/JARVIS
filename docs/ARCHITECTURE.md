# JARVIS architecture

## Deployment
- Local Windows runtime: database, local integrations, Obsidian, optional offline voice and desktop adapters.
- Browser cockpit: chat, tasks, memory, approvals, and system status.
- Cloud AI provider: optional; send only the data required by the user's request.
- Remote access: deferred until authentication, TLS, CSRF protection, origin restrictions, rate limits, and audit logging exist.

## Layers
1. Interface: browser cockpit and voice input/output.
2. Orchestrator: resolves intent, selects tools, checks permissions, verifies outcomes.
3. Policy engine: deny-by-default tool registry and action-specific approvals.
4. Adapters: Obsidian, OpenAI-compatible APIs, Google Workspace, MCP, n8n, browser and desktop automation.
5. Storage: SQLite operational state and Markdown knowledge in Obsidian.

## Memory
- Working state: active conversation and pending approvals.
- Operational memory: tasks, reminders, tool runs, metadata in SQLite.
- Knowledge memory: Markdown notes in the Obsidian vault.
- Secrets: separate from all memory stores.

## Voice
Initial browser speech APIs where supported; sherpa-onnx is the offline ASR candidate and Piper is the offline TTS candidate. Voice models are installed separately and are never committed to Git.

## Automation boundaries
PyAutoGUI and browser-use are optional adapters, not the orchestration core. They require isolated contexts, narrow allow-lists, and fresh approvals for sensitive actions. No unrestricted terminal execution.

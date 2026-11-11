# Architecture

## Local machine
- Windows runtime
- FastAPI service
- SQLite database
- Obsidian vault
- Optional local speech engines

## AI and tools
- OpenAI-compatible model provider
- MCP tool adapters
- Google Workspace OAuth adapters
- n8n workflows
- Isolated browser automation
- Optional desktop automation

## Permission tiers
- Automatic: local read-only operations, task capture, note drafts.
- Confirm: email sending, calendar writes, social publishing, external form submissions.
- Disabled until separately secured: shell execution, financial actions, trading, public remote access, destructive filesystem actions.

## Data flow
User command → intent parser → policy check → tool adapter → result verification → audit record → response.

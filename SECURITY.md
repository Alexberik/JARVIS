# Security policy

## Defaults
- Bind the development server to 127.0.0.1 only.
- Never commit .env, API keys, OAuth tokens, vault secrets, databases, or personal logs.
- Do not expose the local API or Obsidian Local REST API to the public internet.
- Unknown MCP servers and tools are deny-by-default.
- Browser and desktop automation are disabled until isolated and reviewed.
- No unrestricted shell execution.

## Approval requirements
An approval must be bound to the exact action and parameters, expire, and be consumed once. A generic approved flag is not sufficient. Approval for one app, recipient, file, URL, or operation must not authorize another.

## External side effects
Email sending, calendar writes, social publishing, purchases, trading, and destructive file operations require explicit approval and an audit record.

## Secrets
Store secrets only in local .env or an OS secret store. Never paste keys into issues, commits, screenshots, or chat. Rotate any secret that is accidentally exposed.

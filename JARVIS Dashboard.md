# JARVIS Dashboard

Welcome to your JARVIS workspace.

## Project notes
- [[obsidian-vault/00 - JARVIS Home]]
- [[obsidian-vault/01 - Project Overview]]
- [[obsidian-vault/02 - Architecture]]
- [[obsidian-vault/03 - Integrations]]
- [[obsidian-vault/04 - Commands and Workflows]]
- [[obsidian-vault/05 - Decisions Log]]
- [[obsidian-vault/06 - Security Rules]]
- [[obsidian-vault/07 - Setup on Windows]]

## Local setup checklist
- [ ] Clone or safely sync this repository to `C:\Users\Admin\JARVIS`.
- [ ] Open that folder as an Obsidian vault.
- [ ] Install Obsidian Local REST API community plugin.
- [ ] Put the plugin URL and API key into the local `.env` file only.
- [ ] Start the FastAPI service on `127.0.0.1`.
- [ ] Confirm the Obsidian status in the JARVIS web cockpit.

**Security:** Never commit `.env`, API keys, OAuth tokens, databases, or private notes that you do not want in this GitHub repository.

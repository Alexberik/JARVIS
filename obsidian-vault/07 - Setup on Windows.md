# Setup on Windows

## Repository and runtime

Repository: `C:\Users\Admin\JARVIS`

Start the local JARVIS service from PowerShell in the repository root:

```powershell
.\start.bat
```

Open the web cockpit at http://127.0.0.1:8765.

## Open the correct Obsidian vault

The active JARVIS vault is the nested folder:

`C:\Users\Admin\JARVIS\JARVIS`

In Obsidian choose **Open another vault → Open folder as vault** and select that exact folder. The note `00 - Home.md` is the dashboard and navigation page.

Do not open the repository root or the legacy `obsidian-vault` documentation folder as the active knowledge vault. The repository root contains application code; `obsidian-vault` contains project documentation.

## Connect JARVIS to Obsidian

The default integration uses filesystem mode and does not require a community plugin. In the repository root, create the local settings file if it does not exist:

```powershell
if (!(Test-Path config\settings.json)) {
  Copy-Item config\settings.example.json config\settings.json
}
notepad config\settings.json
```

The Obsidian section should contain:

```json
"mode": "filesystem",
"filesystem": { "vault_path": "JARVIS" }
```

Save the file and restart JARVIS. The dashboard should report Obsidian as connected.

## Privacy

Keep `config/settings.json`, `.obsidian/`, the SQLite database, API keys, and OAuth tokens local. Never commit secrets or expose the local JARVIS server to the public internet.

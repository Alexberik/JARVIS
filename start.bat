@echo off
chcp 65001 >nul
cd /d "%~dp0"
echo [JARVIS] Starting on http://127.0.0.1:8765
echo [JARVIS] Keep Obsidian open with Local REST API enabled.
python backend\server.py
pause

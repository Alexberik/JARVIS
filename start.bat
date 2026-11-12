@echo off
setlocal
chcp 65001 >nul
cd /d "%~dp0"

echo.
echo  JARVIS AI - LOCAL STARTUP
echo  ========================
echo  Project: %CD%
echo  URL: http://127.0.0.1:8765
echo.

where py >nul 2>&1
if %errorlevel%==0 (
    py -3 -c "import sys; sys.exit(0 if sys.version_info >= (3,10) else 1)"
    if errorlevel 1 (
        echo [ERROR] Python 3.10 or newer is required.
        pause
        exit /b 1
    )
    py -3 backend\server.py
) else (
    python -c "import sys; sys.exit(0 if sys.version_info >= (3,10) else 1)"
    if errorlevel 1 (
        echo [ERROR] Python 3.10 or newer is required. Install Python and enable PATH.
        pause
        exit /b 1
    )
    python backend\server.py
)

if errorlevel 1 echo [JARVIS] Server stopped with an error.
pause
endlocal

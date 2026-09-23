@echo off
REM ============================================================
REM  OWNLY one-click launcher — LOCAL MODE, NO DOCKER NEEDED
REM  Starts the API at http://localhost:8000 and opens the docs.
REM  First run creates the Python environment automatically.
REM ============================================================

set BACKEND=%~dp0backend

if not exist "%BACKEND%\.venv\Scripts\python.exe" (
    echo [OWNLY] First run — creating Python environment (about 1 minute)...
    python -m venv "%BACKEND%\.venv"
    "%BACKEND%\.venv\Scripts\python.exe" -m pip install -q --upgrade pip
    "%BACKEND%\.venv\Scripts\python.exe" -m pip install -q -r "%BACKEND%\requirements-local.txt"
)

echo [OWNLY] Starting OWNLY on http://localhost:8000
echo         Close this window (or Ctrl+C) to stop the server.
echo.
start "" http://localhost:8000/docs
"%BACKEND%\.venv\Scripts\python.exe" "%BACKEND%\run_local.py"
pause
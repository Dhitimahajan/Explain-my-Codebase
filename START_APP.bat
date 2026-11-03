@echo off
title Explain My Codebase Server
cd /d "%~dp0"
echo =====================================================================
echo   ?? EXPLAIN MY CODEBASE - AI Architecture Visualizer & Copilot
echo =====================================================================
echo.
echo Starting backend server on http://127.0.0.1:8000 ...
echo Please keep this window open while using the application!
echo.
if exist ".venv\Scripts\python.exe" (
    ".venv\Scripts\python.exe" run.py
) else (
    python run.py
)
pause

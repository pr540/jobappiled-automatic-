@echo off
title JobBot — Retry Failed Jobs
cd /d "e:\your projects\jobappiled-automatic-"

echo ============================================================
echo   JOBBOT — RETRY FAILED / ERROR JOBS
echo   Resets error jobs to pending then re-applies
echo ============================================================
echo.

call .venv\Scripts\activate.bat

:: Kill stale Chrome
taskkill /F /IM chromedriver.exe >nul 2>&1
taskkill /F /IM chrome.exe >nul 2>&1
timeout /t 2 /nobreak >nul

:: Run apply-only with retry-errors flag
python run_daily.py --apply-only --retry-errors --limit 150

echo.
echo Done! Check http://localhost:5000 for results.
pause

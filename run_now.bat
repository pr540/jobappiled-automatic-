@echo off
title JobBot — Full Daily Run
cd /d "e:\your projects\jobappiled-automatic-"

echo ============================================================
echo   JOBBOT DAILY RUN  —  %date% %time%
echo   Search + ATS Score + Apply + Outreach
echo   Dashboard: http://localhost:5000
echo ============================================================
echo.

:: Create logs folder if missing
if not exist logs mkdir logs

:: Activate virtualenv
call .venv\Scripts\activate.bat

:: Kill stale Chrome before starting
echo [STEP 0] Cleaning up stale Chrome processes...
taskkill /F /IM chromedriver.exe >nul 2>&1
taskkill /F /IM chrome.exe >nul 2>&1
timeout /t 2 /nobreak >nul

:: Run full daily pipeline (search -> score -> apply -> outreach)
echo [STEP 1] Starting full daily run...
echo Output is saved to logs\daily_run.log
echo.
python run_daily.py --limit 150 2>&1 | tee logs\daily_run.log

echo.
echo ============================================================
echo   DONE! Check results at http://localhost:5000
echo   Full log: logs\daily_run.log
echo ============================================================
pause

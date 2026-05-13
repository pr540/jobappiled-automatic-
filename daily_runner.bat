@echo off
:: ============================================================
:: JobBot Daily Runner — called by Windows Task Scheduler at 9 AM
:: Steps: Cleanup -> Search -> ATS Score -> Apply -> Outreach -> Report
:: ============================================================
cd /d "e:\your projects\jobappiled-automatic-"

:: Create logs folder if missing
if not exist logs mkdir logs

echo [%date% %time%] JobBot daily run starting... >> logs\daily_run.log

:: Kill stale Chrome before starting
taskkill /F /IM chromedriver.exe >nul 2>&1
taskkill /F /IM chrome.exe >nul 2>&1
timeout /t 3 /nobreak >nul

:: Activate virtualenv
call .venv\Scripts\activate.bat

:: Full daily run: search new jobs + retry any errors from yesterday + apply + outreach
python run_daily.py --limit 150 --retry-errors >> logs\daily_run.log 2>&1

echo [%date% %time%] Daily run complete. >> logs\daily_run.log

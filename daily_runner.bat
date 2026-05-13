@echo off
:: ============================================================
:: JobBot Daily Runner — called by Windows Task Scheduler
:: ============================================================
cd /d "e:\your projects\jobappiled-automatic-"

echo [%date% %time%] Starting JobBot daily run...

:: Activate virtualenv and run
call .venv\Scripts\activate.bat
python run_daily.py --limit 150 >> logs\daily_run.log 2>&1

echo [%date% %time%] Daily run complete.

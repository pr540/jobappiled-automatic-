@echo off
title JobBot — Continuous Loop (LinkedIn + Naukri + Indeed)
cd /d "e:\your projects\jobappiled-automatic-"

echo ============================================================
echo   JOBBOT CONTINUOUS LOOP
echo   Platforms : LinkedIn  Naukri  Indeed
echo   Interval  : every 2 hours
echo   Started   : %date% %time%
echo   Log       : logs\loop_run.log
echo   Dashboard : http://localhost:5000
echo   Press Ctrl+C to stop cleanly.
echo ============================================================
echo.

if not exist logs mkdir logs

call .venv\Scripts\activate.bat

python run_loop.py --platforms linkedin naukri indeed --interval 120 --limit 150

echo.
echo ============================================================
echo   Loop ended.  Check logs\loop_run.log for details.
echo ============================================================
pause

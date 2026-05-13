@echo off
title JobBot Dashboard
cd /d "e:\your projects\jobappiled-automatic-"

echo ==========================================
echo   JOBBOT STARTING...
echo   Dashboard: http://localhost:5000
echo   Close this window to stop.
echo ==========================================

call .venv\Scripts\activate.bat
python app.py

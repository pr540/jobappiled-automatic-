@echo off
title JobBot — Install / First-Time Setup
cd /d "e:\your projects\jobappiled-automatic-"

echo ============================================================
echo   JOBBOT FIRST-TIME SETUP
echo ============================================================
echo.

:: Check Python
python --version 2>nul || (
    echo [ERROR] Python not found. Install Python 3.10+ from python.org
    pause
    exit /b 1
)

:: Create virtualenv if not exists
if not exist .venv (
    echo [1/4] Creating virtual environment...
    python -m venv .venv
) else (
    echo [1/4] Virtual environment already exists.
)

:: Activate
call .venv\Scripts\activate.bat

:: Install setuptools first (required for Python 3.12+)
echo [2/4] Installing setuptools...
pip install -q setuptools wheel

:: Install all requirements
echo [3/4] Installing requirements...
pip install -r requirements.txt

:: Create required folders
echo [4/4] Creating folders...
if not exist data mkdir data
if not exist data\browser_profiles mkdir data\browser_profiles
if not exist logs mkdir logs
if not exist instance mkdir instance

echo.
echo ============================================================
echo   SETUP COMPLETE!
echo.
echo   NEXT STEPS:
echo   1. Copy your resume to:  data\resume.pdf
echo   2. Run platform login:   .venv\Scripts\python setup_login.py
echo   3. Schedule automation:  Right-click setup_autostart.bat
echo                            then "Run as Administrator"
echo   4. Start dashboard:      Double-click start.bat
echo      View at:              http://localhost:5000
echo ============================================================
pause

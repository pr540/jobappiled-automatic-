@echo off
echo ================================================
echo   JOB BOT PLAYWRIGHT - FIRST TIME SETUP
echo ================================================
echo.

where node >nul 2>nul
if %errorlevel% neq 0 (
    echo [ERROR] Node.js not found. Install from https://nodejs.org
    pause
    exit /b 1
)

echo [1/3] Installing npm packages...
npm install
if %errorlevel% neq 0 ( echo npm install failed && pause && exit /b 1 )

echo.
echo [2/3] Installing Chromium browser...
npx playwright install chromium
if %errorlevel% neq 0 ( echo Browser install failed && pause && exit /b 1 )

echo.
echo [3/3] Setting up Google logins (opens browser)...
node auth_setup.js

echo.
echo ================================================
echo   Setup complete! Now run: run_jobs.bat
echo ================================================
pause

@echo off
:: Run as Administrator — adds JobBot to Windows startup
:: So the dashboard auto-starts every time you boot your PC

set STARTUP_DIR=%APPDATA%\Microsoft\Windows\Start Menu\Programs\Startup
set SCRIPT_DIR=e:\your projects\jobappiled-automatic-

echo Creating JobBot startup shortcut...

:: Create a VBScript to make the shortcut silently
echo Set oWS = WScript.CreateObject("WScript.Shell") > "%TEMP%\mkshortcut.vbs"
echo sLinkFile = "%STARTUP_DIR%\JobBot.lnk" >> "%TEMP%\mkshortcut.vbs"
echo Set oLink = oWS.CreateShortcut(sLinkFile) >> "%TEMP%\mkshortcut.vbs"
echo oLink.TargetPath = "%SCRIPT_DIR%\start.bat" >> "%TEMP%\mkshortcut.vbs"
echo oLink.WorkingDirectory = "%SCRIPT_DIR%" >> "%TEMP%\mkshortcut.vbs"
echo oLink.Description = "JobBot Auto Apply Dashboard" >> "%TEMP%\mkshortcut.vbs"
echo oLink.WindowStyle = 1 >> "%TEMP%\mkshortcut.vbs"
echo oLink.Save >> "%TEMP%\mkshortcut.vbs"
cscript /nologo "%TEMP%\mkshortcut.vbs"
del "%TEMP%\mkshortcut.vbs"

echo.
echo [OK] JobBot will now auto-start on every Windows login.
echo [OK] Dashboard will be at: http://localhost:5000
echo.
echo Also registering daily Task Scheduler job at 09:00 AM...

schtasks /delete /tn "JobBotDailyApply" /f >nul 2>&1
schtasks /create /tn "JobBotDailyApply" /tr "\"%SCRIPT_DIR%\daily_runner.bat\"" /sc DAILY /st 09:00 /ru "%USERNAME%" /rl HIGHEST /f

if %errorlevel% equ 0 (
    echo [OK] Daily auto-apply scheduled for 09:00 AM every day.
) else (
    echo [WARN] Task Scheduler setup failed - run as Administrator.
)

echo.
echo Setup complete! Restart your PC and JobBot will start automatically.
pause

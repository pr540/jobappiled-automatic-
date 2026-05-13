@echo off
:: ============================================================
:: Registers JobBot as a daily Windows Task Scheduler task
:: Run this ONCE as Administrator
:: ============================================================
echo Setting up JobBot as a daily scheduled task...

:: Delete old task if exists
schtasks /delete /tn "JobBotDailyApply" /f >nul 2>&1

:: Create task: every day at 09:00 AM
schtasks /create ^
  /tn "JobBotDailyApply" ^
  /tr "\"e:\your projects\jobappiled-automatic-\daily_runner.bat\"" ^
  /sc DAILY ^
  /st 09:00 ^
  /ru "%USERNAME%" ^
  /rl HIGHEST ^
  /f

if %errorlevel% equ 0 (
    echo.
    echo SUCCESS! Task "JobBotDailyApply" created.
    echo Runs every day at 09:00 AM automatically.
    echo.
    echo To view:    schtasks /query /tn "JobBotDailyApply"
    echo To run now: schtasks /run /tn "JobBotDailyApply"
    echo To delete:  schtasks /delete /tn "JobBotDailyApply" /f
) else (
    echo.
    echo ERROR: Run this .bat file as Administrator ^(right-click ^> Run as administrator^)
)
pause

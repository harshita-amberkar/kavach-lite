@echo off
cd /d "%~dp0"
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0tools\start_kavach.ps1"
if errorlevel 1 (
    echo.
    echo KAVACH startup failed. Check data\server-error.log.
    pause
    exit /b 1
)
echo.
echo KAVACH is running.
pause

@echo off
REM Kill the old/stuck backend on port 8000 (needs Administrator)
net session >nul 2>&1
if %errorLevel% neq 0 (
    echo.
    echo  [ERROR] RIGHT-CLICK this file and choose "Run as administrator"
    echo.
    pause
    exit /b 1
)
echo Killing all listeners on ports 8000, 8001, and 9203...
for %%p in (8000 8001 9203) do (
    for /f "tokens=5" %%a in ('netstat -ano ^| findstr ":%%p " ^| findstr "LISTENING"') do (
        echo   taskkill PID %%a ^(port %%p^)
        taskkill /PID %%a /F /T
    )
)
echo.
echo Done. Ports 8000, 8001, and 9203 are now free.
echo Next: run run_servers.bat (starts backend :8000, bridge :8001, frontend :3001, and VoiceTut Sarah :9203)
pause

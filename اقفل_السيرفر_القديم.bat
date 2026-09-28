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
echo Killing all listeners on port 8000...
for /f "tokens=5" %%a in ('netstat -ano ^| findstr ":8000 " ^| findstr "LISTENING"') do (
    echo   taskkill PID %%a
    taskkill /PID %%a /F /T
)
echo.
echo Done. Port 8000 is now free.
echo Next: run run_servers.bat (it will start everything with the new Leda voice)
pause

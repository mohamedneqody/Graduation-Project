@echo off
color 0a
title AI-COS OCR Server (Port 9202)

:check_port
netstat -ano | findstr ":9202 " | findstr "LISTENING" >nul 2>&1
if %errorlevel%==0 (
    echo [%time%] Port 9202 is already in use. Waiting 30s...
    timeout /t 30 /nobreak >nul
    goto check_port
)

:start_server
echo [%time%] Starting OCR Server on port 9202...
cd /d "D:\Graduation Project\upload"
call "D:\Graduation Project\venv\Scripts\activate.bat"
python ocr_api_server.py

echo [%time%] OCR Server stopped. Restarting in 3 seconds...
timeout /t 3 /nobreak >nul
goto start_server

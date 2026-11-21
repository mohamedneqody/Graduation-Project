@echo off
setlocal
chcp 65001 >nul
title AI-COS - Run All Servers
if "%~1"=="" (
    echo [0] Cleaning up any existing server instances before full launch...
    call "%~dp0stop_servers.bat"
    color 0a
)
echo.
echo ===================================================
echo   AI-COS -- Starting ALL services
echo   Backend -^> Frontend -^> Worker -^> OCR -^> Ollama -^> Bridge -^> VoiceTut
echo   This takes about 2-3 minutes (OCR models must load). PLEASE WAIT...
echo ===================================================
echo.
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0AI-COS-Pharmacy\scripts\start-local.ps1" -Mode all %*
set "AI_COS_START_EXIT=%errorlevel%"
echo.
echo ===================================================
echo   Final status (LISTENING = running)
echo ===================================================
powershell.exe -NoProfile -Command "$m=@{8000='Backend API';8001='Bridge 8001';3001='Frontend';9202='OCR';9203='VoiceTut TTS';11434='Ollama';6379='Redis';5678='n8n'}; foreach($p in 8000,8001,3001,9202,9203,11434,6379,5678){ $up=[bool](Get-NetTCPConnection -State Listen -LocalPort $p -ErrorAction SilentlyContinue); '{0,-6} {1,-14} {2}' -f $p,$m[$p],$(if($up){'LISTENING  [OK]'}else{'DOWN       [X]'}) }"
echo.
if not "%AI_COS_START_EXIT%"=="0" (
    color 0c
    echo [!] Startup reported errors. See logs in: %~dp0AI-COS-Pharmacy\logs\local-startup
) else (
    echo Open: http://localhost:3001
)
if "%~1"=="" pause
exit /b %AI_COS_START_EXIT%

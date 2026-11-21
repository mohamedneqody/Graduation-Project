@echo off
setlocal
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0AI-COS-Pharmacy\scripts\start-local.ps1" -Mode backend %*
set "AI_COS_START_EXIT=%errorlevel%"
if "%~1"=="" pause
exit /b %AI_COS_START_EXIT%

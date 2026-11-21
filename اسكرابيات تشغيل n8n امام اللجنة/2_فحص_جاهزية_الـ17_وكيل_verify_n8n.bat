@echo off
chcp 65001 >nul
echo ============================================================================
echo   AI-COS - Live Audit of All 17 n8n Workflows and 15 Webhooks
echo ============================================================================
powershell -NoProfile -ExecutionPolicy Bypass -File "D:\Graduation Project\AI-COS-Pharmacy\scripts\verify-n8n-workflows.ps1" -RequireBackend
echo.
pause

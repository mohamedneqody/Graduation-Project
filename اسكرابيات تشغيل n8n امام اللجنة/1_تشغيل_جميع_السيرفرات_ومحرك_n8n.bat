@echo off
chcp 65001 >nul
echo ============================================================================
echo   AI-COS - Starting n8n Docker + All Local Servers (Backend, Frontend, OCR)
echo ============================================================================
docker start n8n n8n-runners 2>nul
call "D:\Graduation Project\run_servers.bat"
pause

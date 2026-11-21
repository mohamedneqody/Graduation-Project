@echo off
chcp 65001 >nul
echo ============================================================================
echo   AI-COS - Execute All 17 Workflows and Hybrid Agents (Pharmacy Full Suite)
echo ============================================================================
"D:\Graduation Project\venv\Scripts\python.exe" "%~dp0run_all_n8n_agents.py"
echo.
pause

@echo off
chcp 65001 >nul
echo ============================================================================
echo   AI-COS - Multi-Vertical Proof: Run Same 5 Agents on Car Showroom
echo ============================================================================
"D:\Graduation Project\venv\Scripts\python.exe" "%~dp0prove_multi_vertical_n8n_agents.py"
echo.
pause

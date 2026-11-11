@echo off
title Supabase Maintenance Connection
"%~dp0venv\Scripts\python.exe" "%~dp0AI-COS-Pharmacy\backend\scripts\configure_cloud_maintenance.py"
if errorlevel 1 echo Setup did not finish successfully.
pause

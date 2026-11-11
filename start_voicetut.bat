@echo off
title VoiceTut-TTS Sarah Service (Port 9203)
echo ========================================================
echo   Starting VoiceTut-TTS (Sarah Egyptian Voice)
echo   Python Env: D:\voicetut_env\Scripts\python.exe
echo   Port: 9203
echo ========================================================
cd /d "D:\Graduation Project\AI-COS-Pharmacy\backend"
"D:\voicetut_env\Scripts\python.exe" voicetut_service.py
pause

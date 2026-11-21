@echo off
chcp 65001 >nul
title VoiceTut-TTS Sarah Service (Port 9203)
echo ========================================================
echo   Starting VoiceTut-TTS (Sarah Egyptian Voice)
echo   Python Env: D:\voicetut_env\Scripts\python.exe
echo   Port: 9203
echo ========================================================
set HF_HOME=D:\huggingface_cache
set TRANSFORMERS_CACHE=D:\huggingface_cache
set TORCH_HOME=D:\huggingface_cache
set HF_HUB_OFFLINE=1
set TRANSFORMERS_OFFLINE=1
set HF_HUB_DISABLE_TELEMETRY=1
set PYTHONUNBUFFERED=1
set VOICETUT_LADY_DIR=C:\انشلء محتوي وياب\lady
cd /d "D:\Graduation Project\AI-COS-Pharmacy\backend"
"D:\voicetut_env\Scripts\python.exe" voicetut_service.py
if "%~1"=="" pause

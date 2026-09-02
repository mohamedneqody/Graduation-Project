@echo off
echo Activating Python virtual environment...
call "D:\Graduation Project\venv\Scripts\activate.bat"
if errorlevel 1 (
    echo ERROR: Could not activate venv!
    echo Make sure venv exists at: D:\Graduation Project\venv
    pause
    exit /b 1
)

echo Starting FastAPI Backend on http://localhost:8000 ...
cd /d "D:\Graduation Project\AI-COS-Pharmacy\backend"
uvicorn app.main:app --reload --host 127.0.0.1 --port 8000

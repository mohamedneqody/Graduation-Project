@echo off
echo Activating Python virtual environment...
call "D:\Graduation Project\venv\Scripts\activate.bat"
if errorlevel 1 (
    echo ERROR: Could not activate venv!
    pause
    exit /b 1
)

echo Checking Redis (docker container ai-cos-redis)...
docker start ai-cos-redis >nul 2>&1

echo Starting Celery Worker on Redis localhost:6379 ...
cd /d "D:\Graduation Project\AI-COS-Pharmacy\backend"
celery -A app.worker.celery_app worker --loglevel=info --pool=solo

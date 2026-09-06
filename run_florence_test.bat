@echo off
chcp 65001 >nul
cd /d "d:\Graduation Project"
if "%~1"=="" (
    echo [INFO] No image dropped. Running default sample...
    "venv\Scripts\python.exe" "test_florence.py"
) else (
    echo [INFO] Processing: %1
    "venv\Scripts\python.exe" "test_florence.py" "%~1"
)
pause

@echo off
color 0c
echo ===================================================
echo   AI-COS Pharmacy -- Stopping All Servers
echo ===================================================
echo.

echo [1] Freeing port 8000 (Backend)...
for /f "tokens=5" %%a in ('netstat -ano ^| findstr ":8000 " ^| findstr "LISTENING"') do (
    echo     Killing PID %%a
    taskkill /PID %%a /F >nul 2>&1
)

echo [2] Freeing port 3000 (Frontend)...
for /f "tokens=5" %%a in ('netstat -ano ^| findstr ":3000 " ^| findstr "LISTENING"') do (
    echo     Killing PID %%a
    taskkill /PID %%a /F >nul 2>&1
)

echo [3] Freeing port 9202 (OCR Server)...
for /f "tokens=5" %%a in ('netstat -ano ^| findstr ":9202 " ^| findstr "LISTENING"') do (
    echo     Killing PID %%a
    taskkill /PID %%a /F >nul 2>&1
)

echo [4] Stopping Celery / Python workers...
taskkill /IM celery.exe /F >nul 2>&1

echo.
echo All ports cleared.
echo ===================================================
timeout /t 2 /nobreak >nul

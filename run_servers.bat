@echo off
color 0a
echo ===================================================
echo   AI-COS Pharmacy -- Starting Servers
echo ===================================================
echo.

echo [0] Clearing occupied ports (avoiding WinError 10013)...
for /f "tokens=5" %%a in ('netstat -ano ^| findstr ":8000 " ^| findstr "LISTENING" 2^>nul') do (
    echo     Freeing port 8000 -- PID %%a
    taskkill /PID %%a /F >nul 2>&1
)
for /f "tokens=5" %%a in ('netstat -ano ^| findstr ":3000 " ^| findstr "LISTENING" 2^>nul') do (
    echo     Freeing port 3000 -- PID %%a
    taskkill /PID %%a /F >nul 2>&1
)
for /f "tokens=5" %%a in ('netstat -ano ^| findstr ":9202 " ^| findstr "LISTENING" 2^>nul') do (
    echo     Freeing port 9202 -- PID %%a
    taskkill /PID %%a /F >nul 2>&1
)
echo     Done.
echo.

echo [1] Starting Redis (docker) + Celery Worker...
docker start ai-cos-redis 2>nul
start "Celery Worker" cmd /k "D:\Graduation Project\start_worker.bat"

echo [2] Starting FastAPI Backend on port 8000...
start "Backend - FastAPI :8000" cmd /k "D:\Graduation Project\start_backend.bat"

echo [3] Starting AI OCR Vision Server on port 9202...
start "AI OCR Vision Server :9202" cmd /k "D:\Graduation Project\start_ocr.bat"

echo.
echo [*] Waiting for Backend to be ready (up to 15s)...
set /a tries=0
:wait_loop
timeout /t 2 /nobreak >nul
curl -s -o nul -w "%%{http_code}" http://127.0.0.1:8000/api/v1/customers/health 2>nul | findstr "200" >nul
if %errorlevel%==0 (
    echo     Backend is ready!
    goto backend_ready
)
set /a tries+=1
if %tries% lss 7 goto wait_loop
echo     Backend still starting -- continuing anyway...
:backend_ready
echo.

echo [4] Starting Next.js Frontend on port 3000...
start "Frontend - Next.js :3000" cmd /k "D:\Graduation Project\start_frontend.bat"

echo.
echo ===================================================
echo   Servers are starting in separate windows!
echo.
echo   Frontend   : http://localhost:3000
echo   Backend    : http://localhost:8000
echo   OCR Server : http://localhost:9202
echo   API Docs   : http://localhost:8000/docs
echo ===================================================
echo.
pause

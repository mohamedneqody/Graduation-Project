@echo off
color 0a
echo ===================================================
echo   AI-COS Pharmacy -- Starting Servers
echo ===================================================
echo.

echo [0] Clearing previous server windows and occupied ports...
taskkill /FI "WINDOWTITLE eq Backend - FastAPI*" /F /T >nul 2>&1
taskkill /FI "WINDOWTITLE eq Frontend - Next.js*" /F /T >nul 2>&1
taskkill /FI "WINDOWTITLE eq AI OCR Vision Server*" /F /T >nul 2>&1
taskkill /FI "WINDOWTITLE eq Celery Worker*" /F /T >nul 2>&1

for /f "tokens=5" %%a in ('netstat -ano ^| findstr ":8000 " ^| findstr "LISTENING" 2^>nul') do (
    echo     Freeing port 8000 -- PID %%a
    taskkill /PID %%a /F /T >nul 2>&1
)
for /f "tokens=5" %%a in ('netstat -ano ^| findstr ":3000 " ^| findstr "LISTENING" 2^>nul') do (
    echo     Freeing port 3000 -- PID %%a
    taskkill /PID %%a /F /T >nul 2>&1
)
for /f "tokens=5" %%a in ('netstat -ano ^| findstr ":9202 " ^| findstr "LISTENING" 2^>nul') do (
    echo     Freeing port 9202 -- PID %%a
    taskkill /PID %%a /F /T >nul 2>&1
)
echo     Done.
echo.

echo [1] Starting Redis (docker) + Celery Worker...
docker start ai-cos-redis >nul 2>&1
start "Celery Worker" /D "D:\Graduation Project" cmd /k call start_worker.bat

echo [1.5] Checking Ollama AI Service...
curl -s http://127.0.0.1:11434/api/tags >nul 2>&1
if %errorlevel% neq 0 (
    echo     Starting Ollama AI Service...
    start "Ollama AI Engine" "D:\Ollama\ollama.exe" serve
)

echo [2] Starting FastAPI Backend on port 8000 (BERT Embeddings + RAG + Catalog)...
start "Backend - FastAPI :8000 (BERT + RAG)" /D "D:\Graduation Project" cmd /k call start_backend.bat

echo [3] Starting AI OCR Vision Server on port 9202...
start "AI OCR Vision Server :9202" /D "D:\Graduation Project" cmd /k call start_ocr.bat

echo.
echo [*] Waiting for Backend and AI Models to be ready (up to 15s)...
set /a tries=0
:wait_loop
ping 127.0.0.1 -n 3 >nul
curl -s http://127.0.0.1:8000/health 2>nul | findstr "ok" >nul
if %errorlevel%==0 (
    echo     Backend and BERT Model are ready!
    goto backend_ready
)
set /a tries+=1
if %tries% lss 7 goto wait_loop
echo     Backend still starting -- continuing anyway...
:backend_ready
echo.

echo [4] Starting Next.js Frontend on port 3000...
start "Frontend - Next.js :3000" /D "D:\Graduation Project" cmd /k call start_frontend.bat

echo.
echo ===================================================
echo   All 5 AI-COS Pharmacy Services are Live!
echo.
echo   Frontend       : http://localhost:3000
echo   Backend + BERT : http://localhost:8000
echo   Ollama AI Engine: http://localhost:11434 (100%% GPU)
echo   OCR Server     : http://localhost:9202
echo   API Swagger UI : http://localhost:8000/docs
echo ===================================================
echo.
echo Press any key to close this summary window (servers will remain running)...
pause >nul

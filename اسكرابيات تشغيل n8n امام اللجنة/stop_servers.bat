@echo off
color 0c
echo ===================================================
echo   AI-COS -- Stopping All Servers
echo ===================================================
echo.

echo [1] Freeing port 8000 / 8001 (Backend / Bridge)...
for /f "tokens=5" %%a in ('netstat -ano ^| findstr ":8000 " ^| findstr "LISTENING"') do (
    echo     Killing PID %%a
    taskkill /PID %%a /F /T >nul 2>&1
)
for /f "tokens=5" %%a in ('netstat -ano ^| findstr ":8001 " ^| findstr "LISTENING"') do (
    echo     Killing PID %%a
    taskkill /PID %%a /F /T >nul 2>&1
)

echo [2] Freeing port 3000 / 3001 (Frontend)...
for /f "tokens=5" %%a in ('netstat -ano ^| findstr ":3000 " ^| findstr "LISTENING"') do (
    echo     Killing PID %%a
    taskkill /PID %%a /F /T >nul 2>&1
)
for /f "tokens=5" %%a in ('netstat -ano ^| findstr ":3001 " ^| findstr "LISTENING"') do (
    echo     Killing PID %%a
    taskkill /PID %%a /F /T >nul 2>&1
)

echo [2b] Stopping batch loop launchers ^(OCR / VoiceTut / Worker^)...
powershell -NoProfile -Command "Get-CimInstance Win32_Process -ErrorAction SilentlyContinue | Where-Object { $_.Name -eq 'cmd.exe' -and $_.CommandLine -match 'start_(ocr|worker|voicetut|backend|frontend)\.bat' } | ForEach-Object { Stop-Process -Id $_.ProcessId -Force -ErrorAction SilentlyContinue }" >nul 2>&1

echo [3] Freeing port 9202 / 9203 (OCR / VoiceTut-TTS Servers)...
for /f "tokens=5" %%a in ('netstat -ano ^| findstr ":9202 " ^| findstr "LISTENING"') do (
    echo     Killing PID %%a
    taskkill /PID %%a /F /T >nul 2>&1
)
for /f "tokens=5" %%a in ('netstat -ano ^| findstr ":9203 " ^| findstr "LISTENING"') do (
    echo     Killing PID %%a
    taskkill /PID %%a /F /T >nul 2>&1
)

echo [4] Stopping Celery / Python workers...
taskkill /IM celery.exe /F /T >nul 2>&1
powershell -NoProfile -Command "Get-CimInstance Win32_Process -ErrorAction SilentlyContinue | Where-Object { $_.Name -match '^(python|celery)' -and $_.CommandLine -like '*app.worker.celery_app*' } | ForEach-Object { Stop-Process -Id $_.ProcessId -Force -ErrorAction SilentlyContinue }" >nul 2>&1

echo.
echo All ports cleared.
echo ===================================================
timeout /t 2 /nobreak >nul 2>&1 || ping -n 3 127.0.0.1 >nul

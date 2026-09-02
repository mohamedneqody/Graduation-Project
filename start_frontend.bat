@echo off
cd /d "D:\Graduation Project\AI-COS-Pharmacy\frontend"

echo Checking Next.js installation...
if not exist "node_modules\.bin\next.cmd" (
    echo next.js not found - running npm install...
    npm install
    if errorlevel 1 (
        echo ERROR: npm install failed!
        pause
        exit /b 1
    )
)

echo Starting Next.js Frontend on http://localhost:3000 ...
npm run dev

@echo off
REM ============================================================
REM  Install Arabic (Egypt) TTS voice - Microsoft Hoda (female)
REM  For the AI-COS Pharmacy chatbot speaker feature
REM ============================================================

REM Admin check
net session >nul 2>&1
if %errorLevel% neq 0 (
    echo.
    echo  [ERROR] This file needs Administrator rights.
    echo  RIGHT-CLICK this file and choose "Run as administrator"
    echo.
    pause
    exit /b 1
)

echo.
echo Installing Arabic (Egypt) Speech voice - Microsoft Hoda (female)...
echo Downloading from Windows Update (~30 MB). Please wait 1-2 minutes...
echo.

powershell -Command "try { Add-WindowsCapability -Online -Name 'Language.Speech~~~ar-EG~0.0.1.0' -ErrorAction Stop; Write-Host 'RESULT: INSTALLED OK' } catch { Write-Host ('RESULT: ' + $_.Exception.Message) }"

echo.
echo Verifying installation state...
powershell -Command "$c = Get-WindowsCapability -Online -Name 'Language.Speech~~~ar-EG~0.0.1.0'; Write-Host ('State: ' + $c.State)"

echo.
echo ==================================================
echo  NEXT STEPS (very important):
echo  1. If State = Installed : perfect
echo  2. Close ALL Chrome and Edge windows
echo  3. Reopen the browser and go to localhost:3000
echo  4. Open the chat and press the speaker button
echo     - You will hear Microsoft Hoda (female Arabic voice)
echo ==================================================
pause

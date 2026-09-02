# AI-COS OCR Server Keep-Alive Script
# Run this in a PowerShell window - it will keep the OCR server alive permanently
$python = "D:\Graduation Project\venv\Scripts\python.exe"
$server = "D:\Graduation Project\upload\ocr_api_server.py"
$workdir = "D:\Graduation Project\upload"
$env:PYTHONPATH = "D:\Graduation Project\AI-COS-Pharmacy\backend"

Write-Host "=== AI-COS OCR Server Manager ===" -ForegroundColor Cyan
Write-Host "This window keeps the OCR server alive. DO NOT CLOSE this window." -ForegroundColor Yellow
Write-Host ""

while ($true) {
    # Check if port 9202 is already in use
    $inUse = Get-NetTCPConnection -LocalPort 9202 -State Listen -ErrorAction SilentlyContinue
    if ($inUse) {
        Write-Host "[$(Get-Date -Format 'HH:mm:ss')] OCR Server is already running on port 9202. Checking every 30s..." -ForegroundColor Green
        Start-Sleep -Seconds 30
        continue
    }
    
    Write-Host "[$(Get-Date -Format 'HH:mm:ss')] Starting OCR Server..." -ForegroundColor Cyan
    
    $proc = Start-Process -FilePath $python `
        -ArgumentList $server `
        -WorkingDirectory $workdir `
        -PassThru `
        -NoNewWindow
    
    Write-Host "[$(Get-Date -Format 'HH:mm:ss')] OCR Server started (PID: $($proc.Id))" -ForegroundColor Green
    
    # Wait for server to come up
    $ready = $false
    for ($i = 0; $i -lt 30; $i++) {
        Start-Sleep -Seconds 1
        $check = Get-NetTCPConnection -LocalPort 9202 -State Listen -ErrorAction SilentlyContinue
        if ($check) { $ready = $true; break }
    }
    
    if ($ready) {
        Write-Host "[$(Get-Date -Format 'HH:mm:ss')] OCR Server is READY on port 9202!" -ForegroundColor Green
    } else {
        Write-Host "[$(Get-Date -Format 'HH:mm:ss')] WARNING: Server may not have started properly" -ForegroundColor Red
    }
    
    # Wait for the process to exit, then restart
    $proc.WaitForExit()
    Write-Host "[$(Get-Date -Format 'HH:mm:ss')] OCR Server stopped (exit code: $($proc.ExitCode)). Restarting in 3s..." -ForegroundColor Yellow
    Start-Sleep -Seconds 3
}

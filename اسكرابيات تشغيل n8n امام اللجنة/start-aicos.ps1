# ═══════════════════════════════════════════════════════════════
#  Cura AI Pharmacy (صيدلية كيورا الذكية) — Professional System Launcher
#  يتحقق من توفر المنافذ قبل التشغيل، ومن استجابة HTTP بعده
# ═══════════════════════════════════════════════════════════════
param([switch]$CheckOnly, [switch]$ReadOnly)

$ErrorActionPreference = 'Stop'
$Root = Split-Path -Parent $PSScriptRoot
$WorkspaceRoot = Split-Path -Parent $Root
$BackendPort = if ($ReadOnly) { 8001 } else { 8000 }
$BackendApp = if ($ReadOnly) { 'scripts.integration_smoke_server:app' } else { 'app.main:app' }
$BackendBind = if ($ReadOnly) { '127.0.0.1' } else { '0.0.0.0' }
if ($ReadOnly) {
    Write-Host 'وضع الفحص للقراءة فقط: الكتابة والإرسال والمهام الخلفية معطلة.' -ForegroundColor Yellow
}

Write-Host ''
Write-Host ('═' * 60) -ForegroundColor Cyan
Write-Host '  صيدلية كيورا الذكية (Cura AI Pharmacy) — تشغيل المنظومة الاحترافي' -ForegroundColor Cyan
Write-Host "  Backend :$BackendPort (FastAPI)  +  Frontend :3001 (Next.js)" -ForegroundColor Cyan
Write-Host ('═' * 60) -ForegroundColor Cyan
Write-Host ''

# ── [0/4] التحقق من توفر المنافذ قبل بدء أي خدمة ──
Write-Host "[0/4] التحقق من توفر المنافذ $BackendPort و 3001..." -ForegroundColor Yellow
try {
    $occupiedPorts = @(Get-NetTCPConnection -State Listen -ErrorAction Stop |
        Where-Object { $_.LocalPort -in $BackendPort, 3001 } |
        Select-Object LocalPort, OwningProcess -Unique)
} catch {
    Write-Error "تعذر التحقق من المنافذ؛ لم يبدأ التشغيل. $($_.Exception.Message)" -ErrorAction Continue
    exit 1
}
if ($occupiedPorts.Count -gt 0) {
    foreach ($listener in $occupiedPorts) {
        Write-Error "المنفذ $($listener.LocalPort) مستخدم بواسطة PID $($listener.OwningProcess)؛ التشغيل متوقف. أغلق الخدمة المالكة بنفسك إذا أردت استخدام هذا المنفذ." -ErrorAction Continue
    }
    exit 1
}
Write-Host '      المنفذان متاحان ✓' -ForegroundColor Green
if ($CheckOnly) {
    Write-Host '      اكتمل فحص المنافذ فقط؛ لم يبدأ أي خادم.' -ForegroundColor Green
    exit 0
}

# ── [1/4] تشغيل الباك إند ──
Write-Host "[1/4] تشغيل الباك إند (FastAPI :$BackendPort)..." -ForegroundColor Yellow
$VenvPy = Join-Path $WorkspaceRoot 'venv\Scripts\python.exe'
if (Test-Path $VenvPy) {
    Start-Process -WindowStyle Hidden -WorkingDirectory "$Root\backend" -FilePath $VenvPy `
        -ArgumentList '-m','uvicorn',$BackendApp,'--host',$BackendBind,'--port',"$BackendPort",'--no-server-header','--reload','--reload-delay','2'
} else {
    Start-Process -WindowStyle Hidden -WorkingDirectory "$Root\backend" -FilePath 'py' `
        -ArgumentList '-3.12','-m','uvicorn',$BackendApp,'--host',$BackendBind,'--port',"$BackendPort",'--no-server-header','--reload','--reload-delay','2'
}

# ── [2/4] فحص استجابة HTTP للباك إند ──
Write-Host '[2/4] انتظار استجابة HTTP من الباك إند...' -ForegroundColor Yellow
$tries = 0; $ok = $false; $backendStatus = $null
while ($tries -lt 20) {
    $tries++
    Start-Sleep -Seconds 3
    try {
        $r = Invoke-WebRequest -Uri "http://127.0.0.1:$BackendPort/health" `
             -Method GET -TimeoutSec 3 -UseBasicParsing -ErrorAction Stop
        if ($r.StatusCode -eq 200 -and ($r.Content | ConvertFrom-Json).service -eq 'aicos-pharmacy-backend') { $backendStatus = 200; $ok = $true; break }
    } catch {
        $code = $null
        if ($_.Exception.Response) { $code = [int]$_.Exception.Response.StatusCode }
        # A response from an unrelated service does not establish AI-COS readiness.
    }
}
if (-not $ok) {
    Write-Host '      ✗ لم يُؤكد فحص HTTP استجابة الباك إند خلال المحاولات المتاحة. راجع إعدادات الخادم.' -ForegroundColor Red
    Read-Host 'اضغط Enter للخروج'
    exit 1
}
Write-Host "      الباك إند يستجيب عبر HTTP ($backendStatus) ✓ — بعد $tries محاولة" -ForegroundColor Green

# ── [3/4] تشغيل الفرونت إند ──
Write-Host '[3/4] تشغيل الواجهة (Next.js :3001)...' -ForegroundColor Yellow
$savedInternalUrl = $env:INTERNAL_API_URL
$savedNodeOptions = $env:NODE_OPTIONS
$savedRayonThreads = $env:RAYON_NUM_THREADS
$savedTokioThreads = $env:TOKIO_WORKER_THREADS
try {
    $env:INTERNAL_API_URL = "http://127.0.0.1:$BackendPort"
    if (-not $env:NODE_OPTIONS) { $env:NODE_OPTIONS = '--max-old-space-size=1536' }
    if (-not $env:RAYON_NUM_THREADS) { $env:RAYON_NUM_THREADS = '2' }
    if (-not $env:TOKIO_WORKER_THREADS) { $env:TOKIO_WORKER_THREADS = '2' }
    Start-Process -WindowStyle Hidden -WorkingDirectory "$Root\frontend" -FilePath 'cmd.exe' `
        -ArgumentList '/c','npm run dev'
} finally {
    $env:INTERNAL_API_URL = $savedInternalUrl
    $env:NODE_OPTIONS = $savedNodeOptions
    $env:RAYON_NUM_THREADS = $savedRayonThreads
    $env:TOKIO_WORKER_THREADS = $savedTokioThreads
}

# ── [4/4] فحص صحة الواجهة ──
Write-Host '[4/4] انتظار إقلاع الواجهة والتحقق من صحة...' -ForegroundColor Yellow
$tries = 0; $ok = $false
while ($tries -lt 20) {
    $tries++
    Start-Sleep -Seconds 3
    try {
        $r = Invoke-WebRequest -Uri 'http://127.0.0.1:3001/login' `
             -Method GET -TimeoutSec 4 -UseBasicParsing -ErrorAction Stop
        if ($r.StatusCode -eq 200) { $ok = $true; break }
    } catch { }
}
if (-not $ok) {
    Write-Host '      ✗ فشل إقلاع الواجهة بعد 60 ثانية!' -ForegroundColor Red
    Read-Host 'اضغط Enter للخروج'
    exit 1
}
Write-Host "      الواجهة تستجيب (200) ✓ — بعد $tries محاولة" -ForegroundColor Green

# ── [5] التأكد من تشغيل خادم قراءة الروشتات (OCR :9202) ──
$OcrBat = Join-Path $WorkspaceRoot 'start_ocr.bat'
$ocrListening = @(Get-NetTCPConnection -State Listen -ErrorAction SilentlyContinue | Where-Object LocalPort -eq 9202)
if (-not $ocrListening.Count -and (Test-Path $OcrBat)) {
    Write-Host '[5/5] تشغيل محرك قراءة الروشتات (TrOCR + Florence-2 :9202)...' -ForegroundColor Yellow
    Start-Process -WindowStyle Hidden -WorkingDirectory $WorkspaceRoot -FilePath 'cmd.exe' -ArgumentList '/d','/s','/c',"`"$OcrBat`""
}

Write-Host ''
Write-Host ('═' * 60) -ForegroundColor Green
Write-Host '  ✅ اكتمل فحص استجابة HTTP للخدمتين:' -ForegroundColor Green
Write-Host "     • الباك إند :$BackendPort — HTTP $backendStatus ✓" -ForegroundColor Green
Write-Host '     • الواجهة  :3001 — تستجيب ✓' -ForegroundColor Green
Write-Host ''
Write-Host '  افتح المتصفح على:  http://localhost:3001' -ForegroundColor White
Write-Host ('═' * 60) -ForegroundColor Green

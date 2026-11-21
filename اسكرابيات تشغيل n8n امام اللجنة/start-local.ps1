[CmdletBinding()]
param(
    [ValidateSet('all', 'backend', 'frontend')][string]$Mode = 'all',
    [switch]$CoreOnly,
    [switch]$CheckOnly,
    [ValidateRange(1, 300)][int]$WaitSeconds = 120
)

$RepositoryRoot = Split-Path -Parent $PSScriptRoot
$WorkspaceRoot = Split-Path -Parent $RepositoryRoot

function Get-LocalServicePlan([string]$SelectedMode, [bool]$OnlyCore) {
    $python = Join-Path $WorkspaceRoot 'venv\Scripts\python.exe'
    $plan = @()
    if ($SelectedMode -in @('all', 'backend')) {
        $plan += [pscustomobject]@{
            Name='backend'; Port=8000; File=$python
            Arguments='-m uvicorn app.main:app --host 0.0.0.0 --port 8000 --no-server-header --reload --reload-delay 2'
            Directory=(Join-Path $RepositoryRoot 'backend'); Health='http://127.0.0.1:8000/health'
        }
    }
    if ($SelectedMode -in @('all', 'frontend')) {
        $plan += [pscustomobject]@{
            Name='frontend'; Port=3001; File=(Get-Command node.exe -ErrorAction Stop).Source
            Arguments='node_modules/next/dist/bin/next dev --port 3001'
            Directory=(Join-Path $RepositoryRoot 'frontend'); Health='http://127.0.0.1:3001/login'
        }
    }
    if ($SelectedMode -eq 'all' -and !$OnlyCore) {
        foreach ($name in @('worker', 'ocr')) {
            $batch = Join-Path $WorkspaceRoot ('start_' + $name + '.bat')
            $port = if ($name -eq 'ocr') { 9202 } else { $null }
            $plan += [pscustomobject]@{
                Name=$name; Port=$port
                File=$env:ComSpec; Arguments=('/d /s /c ""{0}""' -f $batch)
                Directory=$WorkspaceRoot; Health=$null; RequiredFile=$batch
            }
        }
    }
    return $plan
}

function Test-LocalSetup($Plan, [string]$SelectedMode, [bool]$OnlyCore) {
    $issues = [System.Collections.Generic.List[string]]::new()
    foreach ($service in $Plan) {
        if (!(Test-Path -LiteralPath $service.File -PathType Leaf)) { $issues.Add("Missing executable for $($service.Name)") }
        if (!(Test-Path -LiteralPath $service.Directory -PathType Container)) { $issues.Add("Missing directory for $($service.Name)") }
        if ($service.PSObject.Properties['RequiredFile'] -and !(Test-Path -LiteralPath $service.RequiredFile -PathType Leaf)) {
            $issues.Add("Missing launcher for $($service.Name)")
        }
        if ($service.Port) {
            $listeners = @(Get-NetTCPConnection -State Listen -ErrorAction SilentlyContinue | Where-Object LocalPort -eq $service.Port)
            if ($listeners.Count) {
                $issues.Add("Port $($service.Port) for $($service.Name) is already occupied.")
            }
        }
    }
    if ($SelectedMode -in @('all', 'frontend')) {
        $frontend = Join-Path $RepositoryRoot 'frontend'
        if (!(Test-Path -LiteralPath (Join-Path $frontend 'node_modules\next\dist\bin\next'))) {
            $issues.Add('Frontend dependencies missing. Run npm ci in the frontend directory first.')
        } else {
            $node = (Get-Command node.exe -ErrorAction Stop).Source
            $output = & $node (Join-Path $PSScriptRoot 'check-local-origins.cjs')
            if ($LASTEXITCODE -ne 0) {
                try { $result = $output | ConvertFrom-Json; foreach ($issue in $result.errors) { $issues.Add([string]$issue) } }
                catch { $issues.Add('Could not validate local frontend origins') }
            }
        }
    }
    if ($SelectedMode -eq 'all' -and !$OnlyCore) {
        if (!(Get-Command docker.exe -ErrorAction SilentlyContinue)) { $issues.Add('Docker is required for optional services. Use -CoreOnly for the web application.') }
        if (!(Test-Path -LiteralPath 'D:\Ollama\ollama.exe') -and !(Get-Command ollama.exe -ErrorAction SilentlyContinue)) {
            $issues.Add('Ollama executable not found. Use -CoreOnly for the web application.')
        }
    }
    return [pscustomobject]@{Ok=($issues.Count -eq 0); Issues=@($issues.ToArray()); Services=@($Plan | Select-Object Name, Port)}
}

function Start-LocalProcess($Service, [string]$LogDirectory) {
    if ($Service.Name -eq 'frontend') {
        if (-not $env:NODE_OPTIONS) { $env:NODE_OPTIONS = '--max-old-space-size=1536' }
        if (-not $env:RAYON_NUM_THREADS) { $env:RAYON_NUM_THREADS = '2' }
        if (-not $env:TOKIO_WORKER_THREADS) { $env:TOKIO_WORKER_THREADS = '2' }
    }
    $stamp = Get-Date -Format 'yyyyMMdd-HHmmss-fff'
    $options = @{
        FilePath=$Service.File; ArgumentList=$Service.Arguments; WorkingDirectory=$Service.Directory
        WindowStyle='Hidden'; PassThru=$true
        RedirectStandardOutput=(Join-Path $LogDirectory ($Service.Name + '-' + $stamp + '.out.log'))
        RedirectStandardError=(Join-Path $LogDirectory ($Service.Name + '-' + $stamp + '.err.log'))
    }
    $process = Start-Process @options
    Write-Host ("Started {0}, PID {1}. Logs: {2}" -f $Service.Name, $process.Id, $LogDirectory)
    return $process
}

function Wait-LocalHttp($Service, $Process, [int]$Seconds) {
    $deadline = [DateTime]::UtcNow.AddSeconds($Seconds)
    do {
        $Process.Refresh()
        if ($Process.HasExited) { throw "$($Service.Name) exited before HTTP liveness was confirmed. Check its log." }
        try {
            $response = Invoke-WebRequest -Uri $Service.Health -UseBasicParsing -TimeoutSec 3 -MaximumRedirection 0
            if ($response.StatusCode -eq 200) {
                if ($Service.Name -eq 'backend') {
                    $body = $response.Content | ConvertFrom-Json
                    if ($body.service -eq 'aicos-pharmacy-backend' -and $body.status -eq 'ok') { return }
                } else { return }
            }
        } catch { }
        if ([DateTime]::UtcNow -ge $deadline) { break }
        Start-Sleep -Milliseconds 500
    } while ($true)
    throw "$($Service.Name) HTTP liveness timed out. Startup is incomplete; check the logs."
}

function Invoke-LocalStartup([string]$SelectedMode, [bool]$OnlyCore, [bool]$InspectOnly, [int]$Seconds) {
    $plan = @(Get-LocalServicePlan $SelectedMode $OnlyCore)
    $check = Test-LocalSetup $plan $SelectedMode $OnlyCore
    if ($InspectOnly) { $check | ConvertTo-Json -Depth 4; return [bool]$check.Ok }
    if (!$check.Ok) { throw ($check.Issues -join [Environment]::NewLine) }
    $logs = Join-Path $RepositoryRoot 'logs\local-startup'
    New-Item -ItemType Directory -Path $logs -Force | Out-Null
    foreach ($service in @($plan | Where-Object Name -in @('backend', 'frontend'))) {
        $process = Start-LocalProcess $service $logs
        Wait-LocalHttp $service $process $Seconds
        Write-Host "$($service.Name): HTTP liveness confirmed on port $($service.Port)."
    }
    if ($SelectedMode -eq 'all' -and !$OnlyCore) {
        foreach ($service in @($plan | Where-Object Name -in @('ocr', 'worker'))) {
            $existingPort = if ($service.Port) { @(Get-NetTCPConnection -State Listen -ErrorAction SilentlyContinue | Where-Object LocalPort -eq $service.Port) } else { @() }
            if (!$existingPort.Count) {
                Start-LocalProcess $service $logs | Out-Null
            }
            if ($service.Name -eq 'ocr') {
                Write-Host 'Waiting for Local OCR Vision Engine (port 9202) to finish loading models...'
                $ocrDeadline = [DateTime]::UtcNow.AddSeconds(75)
                $ocrReady = $false
                while ([DateTime]::UtcNow -lt $ocrDeadline) {
                    try {
                        $ocrResp = Invoke-WebRequest -Uri 'http://127.0.0.1:9202/health' -UseBasicParsing -TimeoutSec 3
                        if ($ocrResp.StatusCode -eq 200) { $ocrReady = $true; break }
                    } catch { }
                    Start-Sleep -Seconds 2
                }
                if ($ocrReady) {
                    Write-Host 'ocr: HTTP liveness confirmed on port 9202.'
                } else {
                    Write-Warning 'ocr: Still warming up in background on port 9202.'
                }
            }
        }
        foreach ($container in @('ai-cos-redis', 'n8n')) {
            try {
                & docker.exe start $container 2>$null | Out-Null
            } catch {
                Write-Warning "Could not start Docker container $container; continuing."
            }
        }
        $ollamaListening = @(Get-NetTCPConnection -State Listen -ErrorAction SilentlyContinue | Where-Object LocalPort -eq 11434)
        if (!$ollamaListening.Count) {
            $ollama = if (Test-Path -LiteralPath 'D:\Ollama\ollama.exe') { 'D:\Ollama\ollama.exe' } else { (Get-Command ollama.exe -ErrorAction SilentlyContinue).Source }
            if ($ollama) {
                Start-LocalProcess ([pscustomobject]@{Name='ollama'; File=$ollama; Arguments='serve'; Directory=$WorkspaceRoot}) $logs | Out-Null
            }
        }
        $python = Join-Path $WorkspaceRoot 'venv\Scripts\python.exe'
        $bridgeScript = Join-Path $RepositoryRoot 'scripts\port_8001_bridge.py'
        if ((Test-Path -LiteralPath $bridgeScript) -and !(Get-NetTCPConnection -State Listen -ErrorAction SilentlyContinue | Where-Object LocalPort -eq 8001)) {
            Start-LocalProcess ([pscustomobject]@{Name='bridge_8001'; File=$python; Arguments=('"{0}"' -f $bridgeScript); Directory=$RepositoryRoot}) $logs | Out-Null
        }
        $voicetutBat = Join-Path $WorkspaceRoot 'start_voicetut.bat'
        if ((Test-Path -LiteralPath $voicetutBat) -and !(Get-NetTCPConnection -State Listen -ErrorAction SilentlyContinue | Where-Object LocalPort -eq 9203)) {
            Start-LocalProcess ([pscustomobject]@{Name='voicetut'; File=$env:ComSpec; Arguments=('/d /s /c ""{0}""' -f $voicetutBat); Directory=$WorkspaceRoot}) $logs | Out-Null
        }
        Write-Host 'Optional services were requested; their model/worker/workflow readiness has not been verified.'
    }
    Write-Host 'Local startup finished. HTTP liveness does not certify database, AI, OCR or n8n workflow readiness.'
    return $true
}

# Dot-sourcing exposes functions for isolated tests without starting services.
if ($MyInvocation.InvocationName -ne '.') {
    $ErrorActionPreference = 'Stop'
    try {
        $success = Invoke-LocalStartup $Mode ([bool]$CoreOnly) ([bool]$CheckOnly) $WaitSeconds
        if ($CheckOnly) {
            $success | Where-Object { $_ -isnot [bool] } | Write-Output
            if (!($success | Where-Object { $_ -is [bool] } | Select-Object -Last 1)) { exit 1 }
        }
        exit 0
    } catch {
        Write-Error -Message ($_.Exception.Message + ' No existing process was stopped. Any services already started remain running.') -ErrorAction Continue
        exit 1
    }
}

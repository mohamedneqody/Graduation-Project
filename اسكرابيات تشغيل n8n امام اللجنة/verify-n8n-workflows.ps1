# ===========================================================================
# Cura AI Pharmacy (AI-COS) - Automated Verification for all 17 n8n Workflows
# Checks n8n Engine (:5678), all 17 AI-COS Workflows in SQLite (published,
# tagged, zero :8001, health-guarded schedules), all 15 Production Webhooks
# (non-mutating 403 auth-gate check), and FastAPI Backend (:8000) when UP.
# ===========================================================================

param(
    [switch]$RequireBackend
)

$ErrorActionPreference = 'Continue'
$failures = 0

function Read-InternalServiceKey {
    $envPath = "D:\Graduation Project\AI-COS-Pharmacy\backend\.env"
    if (Test-Path $envPath) {
        foreach ($line in [System.IO.File]::ReadAllLines($envPath)) {
            if ($line -match '^\s*INTERNAL_SERVICE_KEY\s*=\s*(.+?)\s*$') {
                return $Matches[1].Trim('"', "'", ' ')
            }
        }
    }
    if ($env:INTERNAL_SERVICE_KEY) { return $env:INTERNAL_SERVICE_KEY }
    return ""
}

$token = Read-InternalServiceKey

Write-Host ""
Write-Host "=======================================================================" -ForegroundColor Cyan
Write-Host "   Cura AI Pharmacy (AI-COS) - n8n 17 Workflows & Webhooks Live Audit" -ForegroundColor Cyan
Write-Host "=======================================================================" -ForegroundColor Cyan
Write-Host ""

# ---------------------------------------------------------------------------
# 1. Core Services (:5678 n8n & :8000 FastAPI Backend)
# ---------------------------------------------------------------------------
Write-Host "[1/3] Core Service Health" -ForegroundColor Yellow

$n8nHealthCode = curl.exe -s --max-time 5 -o NUL -w "%{http_code}" "http://127.0.0.1:5678/healthz"
if ($n8nHealthCode -eq "200") {
    Write-Host "  [PASS - HTTP $n8nHealthCode] n8n Engine (:5678/healthz)" -ForegroundColor Green
} else {
    Write-Host "  [FAIL - HTTP $n8nHealthCode] n8n Engine (:5678/healthz)" -ForegroundColor Red
    $failures++
}

$backendHealthRaw = curl.exe -s --max-time 5 -w "__HTTP__:%{http_code}" "http://127.0.0.1:8000/health"
$backendHttpCode = "000"
$backendBody = ""
if ($backendHealthRaw -match '(?s)^(.*)__HTTP__:(\d+)$') {
    $backendBody = $Matches[1].Trim()
    $backendHttpCode = $Matches[2]
}

$backendUp = $false
if ($backendHttpCode -eq "200" -and $backendBody -match '"service"\s*:\s*"aicos-pharmacy-backend"') {
    $backendUp = $true
    Write-Host "  [PASS - HTTP 200] FastAPI Backend (:8000/health - aicos-pharmacy-backend)" -ForegroundColor Green
} elseif ($backendHttpCode -eq "200") {
    Write-Host "  [WARN - HTTP 200] Port :8000 responded with unexpected service: $backendBody" -ForegroundColor DarkYellow
    if ($RequireBackend) { $failures++ }
} else {
    Write-Host "  [WARN - OFFLINE (HTTP $backendHttpCode)] FastAPI Backend (:8000/health) - start backend via run_servers.bat to test internal routes" -ForegroundColor DarkYellow
    if ($RequireBackend) { $failures++ }
}

if ($backendUp) {
    if (-not $token) {
        Write-Host "  [FAIL] INTERNAL_SERVICE_KEY not found in backend\.env or environment" -ForegroundColor Red
        $failures++
    } else {
        $internalChecks = @(
            @{ Name = "Governance SLA Overdue (/internal/governance/review-overdue?hours=24)"; Url = "http://127.0.0.1:8000/internal/governance/review-overdue?hours=24" },
            @{ Name = "Governance Pending Queue (/internal/governance/pending?limit=10)"; Url = "http://127.0.0.1:8000/internal/governance/pending?limit=10" },
            @{ Name = "Weekly Executive Digest (/api/v1/business-value/internal/weekly-digest)"; Url = "http://127.0.0.1:8000/api/v1/business-value/internal/weekly-digest" },
            @{ Name = "Decision Lab Health (/internal/decision-lab/health)"; Url = "http://127.0.0.1:8000/internal/decision-lab/health" }
        )
        foreach ($ic in $internalChecks) {
            $code = curl.exe -s --max-time 8 -o NUL -w "%{http_code}" $ic.Url -H "X-Internal-Token: $token"
            if ($code -eq "200") {
                Write-Host "  [PASS - HTTP $code] $($ic.Name)" -ForegroundColor Green
            } else {
                Write-Host "  [FAIL - HTTP $code] $($ic.Name)" -ForegroundColor Red
                $failures++
            }
        }
    }
}

Write-Host ""
Write-Host "[2/3] n8n SQLite Workflow Parity, Tags & Health Guards (17 Active AI-COS Workflows)" -ForegroundColor Yellow

$nodeAuditScript = @'
const { DatabaseSync } = require('node:sqlite');
const db = new DatabaseSync('/home/node/.n8n/database.sqlite', { readOnly: true });

const expectedIds = [
  '81yGYG75B34myKyX',
  'AIcosDecisionLab26',
  'AIcosDiscount002',
  'AIcosEmgAlertFIX03',
  'AIcosSummary0003',
  'AIcosWormAlert002',
  'AIcosWormAnchor01',
  'IdmwV5STp1lMMV9u',
  'JHc6K01OQn1iPNT7',
  'YLX90juWgWUxaHHE',
  'fsCIHwHnZPCl9VSW',
  'h6V0iABymaF3COv7',
  'ofhk7M9PfQzHx0BV',
  'qrv7DBmlhfYp63X9',
  's1S68Kb87OmgB5tz',
  'tBAAF1jT2jP9dJiD',
  'zWNggcB1fRoc7VJN'
];

let bad = 0;
for (const id of expectedIds) {
  const wf = db.prepare(`
    SELECT w.id, w.name, w.active, w.isArchived, w.activeVersionId, w.versionId, w.nodes, w.connections,
           GROUP_CONCAT(t.id, ',') AS tagIds
    FROM workflow_entity w
    LEFT JOIN workflows_tags wt ON wt.workflowId = w.id
    LEFT JOIN tag_entity t ON t.id = wt.tagId
    WHERE w.id = ?
    GROUP BY w.id
  `).get(id);

  if (!wf) {
    console.log(`FAIL|${id}|MISSING|not found in workflow_entity`);
    bad++;
    continue;
  }

  const pub = db.prepare('SELECT nodes, connections FROM workflow_history WHERE workflowId = ? AND versionId = ?').get(id, wf.activeVersionId || '');
  const draftNodes = JSON.parse(wf.nodes || '[]');
  const draftConn = JSON.parse(wf.connections || '{}');
  const pubNodes = pub ? JSON.parse(pub.nodes || '[]') : [];
  const pubConn = pub ? JSON.parse(pub.connections || '{}') : {};

  const activeOk = wf.active === 1 && wf.isArchived === 0;
  const verOk = Boolean(wf.activeVersionId) && wf.activeVersionId === wf.versionId;
  const nodesOk = JSON.stringify(draftNodes) === JSON.stringify(pubNodes);
  const connOk = JSON.stringify(draftConn) === JSON.stringify(pubConn);
  const no8001 = !(wf.nodes || '').includes(':8001') && !(pub?.nodes || '').includes(':8001');
  const tagOk = String(wf.tagIds || '').split(',').includes('zTQQM5OPihN02AOR');

  const hasSched = pubNodes.some(n => !n.disabled && n.type === 'n8n-nodes-base.scheduleTrigger');
  const hits8000 = JSON.stringify(pubNodes).includes('host.docker.internal:8000');
  const hasStdGuard = (
    pubNodes.some(n => n.name === 'Check Backend Health') &&
    pubNodes.some(n => n.name === 'Is Backend Online?') &&
    pubNodes.some(n => n.name === 'Skipped - Backend Offline')
  );
  const hasDecisionLabGuard = (
    pubNodes.some(n => n.name === 'Check Decision Lab availability') &&
    pubNodes.some(n => n.name === 'Backend and schema ready') &&
    pubNodes.some(n => n.name === 'Skipped - backend unavailable or not ready')
  );
  const guardOk = !(hasSched && hits8000) || hasStdGuard || hasDecisionLabGuard;

  const ok = activeOk && verOk && nodesOk && connOk && no8001 && tagOk && guardOk;
  if (!ok) bad++;
  const flags = `active=${wf.active},ver=${verOk},nodes=${nodesOk},conn=${connOk},no8001=${no8001},tag=${tagOk},guard=${guardOk}`;
  console.log(`${ok ? 'PASS' : 'FAIL'}|${id}|${wf.name}|${flags}`);
}
process.exit(bad > 0 ? 1 : 0);
'@

$auditLines = $nodeAuditScript | docker exec -i n8n node 2>&1
$auditExit = $LASTEXITCODE
foreach ($line in $auditLines) {
    $parts = "$line" -split '\|', 4
    if ($parts.Count -eq 4) {
        if ($parts[0] -eq 'PASS') {
            Write-Host "  [PASS] $($parts[1]) - $($parts[2]) ($($parts[3]))" -ForegroundColor Green
        } else {
            Write-Host "  [FAIL] $($parts[1]) - $($parts[2]) ($($parts[3]))" -ForegroundColor Red
        }
    } else {
        Write-Host "  $line" -ForegroundColor Gray
    }
}
if ($auditExit -ne 0) { $failures++ }

Write-Host ""
Write-Host "[3/3] Live Production Webhook Registration & Auth Gate (15 Endpoints)" -ForegroundColor Yellow

$webhookPaths = @(
    "evaluate_due",
    "send_reminder",
    "send_discount_offer",
    "weekly_summary",
    "order-notification",
    "low-stock",
    "inventory-alert",
    "emergency-alert",
    "worm-alert",
    "worm-anchor",
    "aicos-analytics",
    "aicos-customer-success",
    "aicos-finance-clv",
    "aicos-patient-health",
    "aicos-support"
)

foreach ($path in $webhookPaths) {
    $url = "http://127.0.0.1:5678/webhook/$path"
    $raw = curl.exe -s --max-time 5 -X POST -H "Content-Type: application/json" -d "{}" -w "__HTTP__:%{http_code}" $url
    $code = "000"
    $body = ""
    if ($raw -match '(?s)^(.*)__HTTP__:(\d+)$') {
        $body = $Matches[1].Trim()
        $code = $Matches[2]
    }
    if ($code -eq "403" -and $body -match 'Authorization data is wrong') {
        Write-Host "  [PASS - HTTP 403 Auth-Gated] /webhook/$path" -ForegroundColor Green
    } else {
        Write-Host "  [FAIL - HTTP $code] /webhook/$path -> $body" -ForegroundColor Red
        $failures++
    }
}

Write-Host ""
Write-Host "=======================================================================" -ForegroundColor Cyan
if ($failures -eq 0) {
    Write-Host "   OVERALL RESULT: PASS (17/17 workflows verified, 15/15 webhooks live)" -ForegroundColor Green
} else {
    Write-Host "   OVERALL RESULT: FAIL ($failures failure(s) detected)" -ForegroundColor Red
}
Write-Host "=======================================================================" -ForegroundColor Cyan
Write-Host ""

exit $failures

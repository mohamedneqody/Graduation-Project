$attempt = 0
while ($attempt -lt 4) {
  $listeners = Get-NetTCPConnection -LocalPort 8000 -State Listen -ErrorAction SilentlyContinue | Select-Object -ExpandProperty OwningProcess -Unique
  if (-not $listeners) { Write-Output "PORT CLEAR"; break }
  foreach ($p in $listeners) {
    Write-Output ("Killing tree PID=" + $p)
    taskkill /PID $p /F /T 2>&1 | Out-Null
  }
  Start-Sleep -Seconds 2
  $attempt++
}
$final = Get-NetTCPConnection -LocalPort 8000 -State Listen -ErrorAction SilentlyContinue
if ($final) { Write-Output "STILL LISTENING" } else { Write-Output "PORT CLEAR FINAL" }

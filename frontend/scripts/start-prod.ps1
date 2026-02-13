# Start frontend production server reliably (clears .next, builds, frees port)
param(
  [int]$Port = 3011
)

$ErrorActionPreference = 'Stop'

function Kill-Port([int]$p) {
  $lines = netstat -ano | Select-String -Pattern ":$p\s+" | ForEach-Object { $_.Line }
  foreach ($ln in $lines) {
    if ($ln -match 'LISTENING\s+(\d+)$') {
      $procId = [int]$Matches[1]
      try {
        taskkill /F /PID $procId | Out-Null
        Write-Host "Killed PID $procId on port $p"
      } catch {
        Write-Host ("Failed to kill PID {0} on port {1}: {2}" -f $procId, $p, $_.Exception.Message)
      }
    }
  }
}

$root = Split-Path -Parent $PSScriptRoot
Set-Location $root

Kill-Port $Port

if (Test-Path .next) {
  Remove-Item -Recurse -Force .next
}

npm run build

$env:PORT = "$Port"
npm run start

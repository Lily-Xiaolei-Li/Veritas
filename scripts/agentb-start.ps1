param(
  [switch]$NoWatchdog
)

. "$PSScriptRoot\agentb-lib.ps1"

Write-Log "Agent-B start (stable dev mode)"

# Prevent multiple watchdog windows fighting over ports
$existing = Load-Lock
if ($existing -and (Is-Process-Alive $existing)) {
  Write-Log "Another stable watchdog is already running (PID $existing). Closing it now..."
  try { Stop-Process -Id $existing -Force -ErrorAction Stop } catch { }
  Start-Sleep -Seconds 1
}
Clear-Lock
Save-Lock $PID


# Ensure ports are free (prevents EADDRINUSE / WinError 10048)
# Frontend sometimes probes ports; clear a small range to avoid EADDRINUSE.
3011..3025 | ForEach-Object { Stop-Process-OnPort $_ }
Stop-Process-OnPort 8001

# Wait a moment for ports to actually release (TIME_WAIT / lingering listeners)
3011..3025 | ForEach-Object {
  if (!(Wait-PortFree $_ 8 250)) {
    $p = (Get-ProcessOnPort $_ | Select-Object -First 1)
    Write-Log "Port $_ is still in use (PID $p). Start may fail until it is released."
  }
}
if (!(Wait-PortFree 8001 8 250)) {
  $p = (Get-ProcessOnPort 8001 | Select-Object -First 1)
  Write-Log "Port 8001 is still in use (PID $p). Start may fail until it is released."
}

# Clean stale/corrupted Next build cache (prevents missing chunk/module errors)
try {
  $nextDir = Join-Path (Join-Path (Project-Root) 'frontend') '.next'
  if (Test-Path $nextDir) {
    Remove-Item -Recurse -Force $nextDir -ErrorAction SilentlyContinue
    Write-Log "Cleared frontend .next cache"
  }
} catch {
  # ignore
}


# Start backend if needed
$backendPid = Load-Pid 'backend'
if (!(Is-Process-Alive $backendPid) -or !(Http-Ok 'http://localhost:8001/health')) {
  try { Stop-ByPid 'backend' } catch { }
  Stop-Process-OnPort 8001
  Start-Backend
} else {
  Write-Log "Backend already running (PID $backendPid)"
}

Write-Log "Waiting for backend to become ready..."
if (!(Wait-HttpOk 'http://localhost:8001/health' 120 2)) {
  Write-Log "Backend still not ready after 120s. Check .run\\backend.err.log and .run\\backend.out.log"
}

# Start frontend if needed
$frontendPid = Load-Pid 'frontend'
if (!(Is-Process-Alive $frontendPid) -or !(Http-Ok 'http://localhost:3011/')) {
  try { Stop-ByPid 'frontend' } catch { }
  3011..3025 | ForEach-Object { Stop-Process-OnPort $_ }
  if (!(Wait-PortFree 3011 12 250)) {
    $p = (Get-ProcessOnPort 3011 | Select-Object -First 1)
    Write-Log "Port 3011 is still in use (PID $p). Trying to start anyway..."
  }
  Start-Frontend
} else {
  Write-Log "Frontend already running (PID $frontendPid)"
}

Write-Log "Waiting for frontend to become ready..."
if (!(Wait-HttpOk 'http://localhost:3011/' 180 3)) {
  Write-Log "Frontend still not ready after 180s. Check .run\\frontend.err.log and .run\\frontend.out.log"
}

if ($NoWatchdog) {
  Write-Log "NoWatchdog set; leaving processes running."
  exit 0
}

Write-Log "Watchdog running. Close this window OR run agentb-stop.ps1 to stop."
Write-Log "Tip: first boot can take ~30-90 seconds; watchdog will wait before restarting."

$graceBackendSec = 90
$graceFrontendSec = 120

while ($true) {
  Start-Sleep -Seconds 10
  $now = [DateTimeOffset]::UtcNow.ToUnixTimeSeconds()

  # Backend
  $backendPid = Load-Pid 'backend'
  $backendStarted = Load-Started 'backend'
  $backendInGrace = $backendStarted -and (($now - $backendStarted) -lt $graceBackendSec)
  $backendHealthy = (Is-Process-Alive $backendPid) -and (Http-Ok 'http://localhost:8001/health')

  if (!$backendHealthy -and !$backendInGrace) {
    Write-Log "Backend not healthy; restarting..."
    try { Stop-ByPid 'backend' } catch { }
    Stop-Process-OnPort 8001
    Start-Backend
  }

  # Frontend
  $frontendPid = Load-Pid 'frontend'
  $frontendStarted = Load-Started 'frontend'
  $frontendInGrace = $frontendStarted -and (($now - $frontendStarted) -lt $graceFrontendSec)

  # For frontend, only require process alive during grace; after grace require HTTP
  $frontendHealthy = (Is-Process-Alive $frontendPid) -and ($frontendInGrace -or (Http-Ok 'http://localhost:3011/'))

  if (!$frontendHealthy -and !$frontendInGrace) {
    Write-Log "Frontend not healthy; restarting..."
    try { Stop-ByPid 'frontend' } catch { }
    Stop-Process-OnPort 3011
    Start-Frontend
  }
}

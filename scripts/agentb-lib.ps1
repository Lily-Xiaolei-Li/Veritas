# Shared helpers for Agent-B scripts

$ErrorActionPreference = 'Stop'

function Write-Log([string]$msg) {
  $ts = Get-Date -Format 'yyyy-MM-dd HH:mm:ss'
  Write-Host "[$ts] $msg"
}

function Project-Root {
  return (Resolve-Path (Join-Path $PSScriptRoot '..')).Path
}

function Pid-Dir {
  $dir = Join-Path (Project-Root) '.run'
  if (!(Test-Path $dir)) { New-Item -ItemType Directory -Path $dir | Out-Null }
  return $dir
}

function Lock-File {
  return (Join-Path (Pid-Dir) 'watchdog.lock')
}

function Save-Lock([int]$procId) {
  Set-Content -Path (Lock-File) -Value $procId -Encoding ascii
}

function Load-Lock {
  $f = Lock-File
  if (!(Test-Path $f)) { return $null }
  $raw = (Get-Content $f -ErrorAction SilentlyContinue | Select-Object -First 1)
  if (!$raw) { return $null }
  try { return [int]$raw } catch { return $null }
}

function Clear-Lock {
  $f = Lock-File
  if (Test-Path $f) { Remove-Item -Force $f }
}

function Pid-File([string]$name) {
  return (Join-Path (Pid-Dir) "$name.pid")
}

function Started-File([string]$name) {
  return (Join-Path (Pid-Dir) "$name.started")
}

function Save-Started([string]$name) {
  Set-Content -Path (Started-File $name) -Value ([DateTimeOffset]::UtcNow.ToUnixTimeSeconds()) -Encoding ascii
}

function Load-Started([string]$name) {
  $f = Started-File $name
  if (!(Test-Path $f)) { return $null }
  $raw = (Get-Content $f -ErrorAction SilentlyContinue | Select-Object -First 1)
  if (!$raw) { return $null }
  try { return [int64]$raw } catch { return $null }
}

function Clear-Started([string]$name) {
  $f = Started-File $name
  if (Test-Path $f) { Remove-Item -Force $f }
}

function Save-Pid([string]$name, [int]$procId) {
  Set-Content -Path (Pid-File $name) -Value $procId -Encoding ascii
}

function Load-Pid([string]$name) {
  $f = Pid-File $name
  if (!(Test-Path $f)) { return $null }
  $raw = (Get-Content $f -ErrorAction SilentlyContinue | Select-Object -First 1)
  if (!$raw) { return $null }
  try { return [int]$raw } catch { return $null }
}

function Clear-Pid([string]$name) {
  $f = Pid-File $name
  if (Test-Path $f) { Remove-Item -Force $f }
}

function Is-Process-Alive([int]$procId) {
  if (!$procId) { return $false }
  try {
    $p = Get-Process -Id $procId -ErrorAction Stop
    return $true
  } catch {
    return $false
  }
}

function Http-Ok([string]$url) {
  try {
    $r = Invoke-WebRequest -UseBasicParsing -TimeoutSec 3 -Uri $url
    return ($r.StatusCode -ge 200 -and $r.StatusCode -lt 300)
  } catch {
    return $false
  }
}

function Wait-HttpOk([string]$url, [int]$timeoutSec, [int]$pollSec = 2) {
  $deadline = (Get-Date).AddSeconds($timeoutSec)
  while ((Get-Date) -lt $deadline) {
    if (Http-Ok $url) { return $true }
    Start-Sleep -Seconds $pollSec
  }
  return $false
}

function Get-ProcessOnPort([int]$port) {
  try {
    $conns = Get-NetTCPConnection -LocalPort $port -ErrorAction Stop | Select-Object -Unique OwningProcess
    return ($conns | ForEach-Object { $_.OwningProcess } | Where-Object { $_ -and $_ -ne 0 } | Select-Object -Unique)
  } catch {
    return @()
  }
}

function Stop-Process-OnPort([int]$port) {
  $pids = @(Get-ProcessOnPort $port)
  foreach ($p in $pids) {
    Write-Log "Stopping process on port $port (PID $p)..."
    try { Stop-Process -Id $p -Force -ErrorAction Stop } catch { }
  }
}

function Wait-PortFree([int]$port, [int]$timeoutSec = 15, [int]$pollMs = 250) {
  $deadline = (Get-Date).AddSeconds($timeoutSec)
  while ((Get-Date) -lt $deadline) {
    $pids = @(Get-ProcessOnPort $port)
    if ($pids.Count -eq 0) { return $true }
    Start-Sleep -Milliseconds $pollMs
  }
  return $false
}

function Start-Backend {
  $root = Project-Root
  $backend = Join-Path $root 'backend'
  $python = Join-Path $backend 'venv\Scripts\python.exe'
  if (!(Test-Path $python)) { throw "Backend venv python not found: $python" }

  $outLog = Join-Path (Pid-Dir) 'backend.out.log'
  $errLog = Join-Path (Pid-Dir) 'backend.err.log'
  Write-Log "Starting backend (uvicorn on :8001)..."
  Write-Log "Backend log: $outLog"

  $args = @('-m','uvicorn','app.main:app','--host','127.0.0.1','--port','8001')
  $p = Start-Process -FilePath $python -WorkingDirectory $backend -PassThru -WindowStyle Hidden `
    -ArgumentList $args -RedirectStandardOutput $outLog -RedirectStandardError $errLog

  Save-Pid 'backend' $p.Id
  Save-Started 'backend'
  Start-Sleep -Milliseconds 200
  Write-Log "Backend PID: $($p.Id)"
}

function Start-Frontend {
  $root = Project-Root
  $frontend = Join-Path $root 'frontend'

  $outLog = Join-Path (Pid-Dir) 'frontend.out.log'
  $errLog = Join-Path (Pid-Dir) 'frontend.err.log'
  Write-Log "Starting frontend (Next dev on :3011)..."
  Write-Log "Frontend log: $outLog"

  # Use cmd.exe so npm.cmd resolves reliably
  # Note: removed -H 127.0.0.1 because it conflicts with IPv6 listeners on Windows
  $p = Start-Process -FilePath 'cmd.exe' -WorkingDirectory $frontend -PassThru -WindowStyle Hidden `
    -ArgumentList @('/c','npm','run','dev','--','-p','3011') -RedirectStandardOutput $outLog -RedirectStandardError $errLog

  Save-Pid 'frontend' $p.Id
  Save-Started 'frontend'
  Start-Sleep -Milliseconds 200
  Write-Log "Frontend PID: $($p.Id)"
}

function Stop-ByPid([string]$name) {
  $procId = Load-Pid $name
  if (!$procId) {
    Write-Log "${name}: no pid file"
    return
  }
  if (Is-Process-Alive $procId) {
    Write-Log "Stopping $name (PID $procId)..."
    try { Stop-Process -Id $procId -Force -ErrorAction Stop } catch { }
  }
  Clear-Pid $name
  Clear-Started $name
}

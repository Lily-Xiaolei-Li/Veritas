# Agent-B Port Cleanup Script
# Also kills any existing Agent-B cmd windows

# First, kill cmd windows with Agent-B titles
Write-Host "  Closing Agent-B windows..."
Get-Process -Name cmd -ErrorAction SilentlyContinue | Where-Object {
    $_.MainWindowTitle -match "Agent-B"
} | ForEach-Object {
    Write-Host "    Closing window: $($_.MainWindowTitle)"
    Stop-Process -Id $_.Id -Force -ErrorAction SilentlyContinue
}

# Kill all python processes (uvicorn backends)
Write-Host "  Stopping Python processes..."
Get-Process -Name python -ErrorAction SilentlyContinue | ForEach-Object {
    Write-Host "    Killing python PID $($_.Id)"
    Stop-Process -Id $_.Id -Force -ErrorAction SilentlyContinue
}

# Kill node processes on our ports (but not all node - Clawdbot uses node!)
$ports = @(3000, 3001, 3002, 3003, 3004, 3005, 3006, 3007, 3008, 3009, 3010)
foreach ($port in $ports) {
    $conns = Get-NetTCPConnection -LocalPort $port -State Listen -ErrorAction SilentlyContinue
    if ($conns) {
        foreach ($conn in $conns) {
            Write-Host "    Killing PID $($conn.OwningProcess) on port $port"
            Stop-Process -Id $conn.OwningProcess -Force -ErrorAction SilentlyContinue
        }
    }
}

# Wait for cleanup
Start-Sleep -Seconds 2
Write-Host "  Cleanup complete"

. "$PSScriptRoot\agentb-lib.ps1"

Write-Log "Stopping Agent-B..."

# Stop tracked processes first
Stop-ByPid 'frontend'
Stop-ByPid 'backend'

# Also stop anything still listening on the ports (covers stale runs / missing pid files)
3011..3025 | ForEach-Object { Stop-Process-OnPort $_ }
Stop-Process-OnPort 8001

Clear-Lock
Write-Log "Stopped."
<# Agent-B Research 一键启动脚本 #>

Write-Host "🚀 Starting Agent-B Research..." -ForegroundColor Cyan

# 确保 PostgreSQL 在运行
$pgService = Get-Service -Name "postgresql-x64-16" -ErrorAction SilentlyContinue
if ($pgService.Status -ne "Running") {
    Write-Host "Starting PostgreSQL..." -ForegroundColor Yellow
    net start postgresql-x64-16
}

# 用 PM2 启动前端和后端
Set-Location $PSScriptRoot
pm2 delete all 2>$null
pm2 start ecosystem.config.js

Write-Host ""
Write-Host "✅ Agent-B Research started!" -ForegroundColor Green
Write-Host ""
Write-Host "Frontend: http://localhost:3000" -ForegroundColor White
Write-Host "Backend:  http://localhost:8001" -ForegroundColor White
Write-Host ""
Write-Host "Commands:" -ForegroundColor Gray
Write-Host "  pm2 status     - 查看状态"
Write-Host "  pm2 logs       - 查看日志"
Write-Host "  pm2 restart all - 重启全部"
Write-Host "  pm2 stop all   - 停止全部"

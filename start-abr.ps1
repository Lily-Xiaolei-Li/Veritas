# Agent-B-Research Startup Script
# Starts backend + frontend via PM2, then opens browser

Write-Host "Starting Agent-B-Research..." -ForegroundColor Cyan

# Resurrect PM2 processes (backend + frontend)
pm2 resurrect

# Wait for services to start (frontend needs time to compile)
Write-Host "Waiting 15 seconds for services to initialize..." -ForegroundColor Yellow
Start-Sleep -Seconds 15

Write-Host "Opening browser..." -ForegroundColor Green
Start-Process "http://localhost:3001"

Write-Host "Done!" -ForegroundColor Green

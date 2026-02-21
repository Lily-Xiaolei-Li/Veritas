# Veritas Test Runner
Write-Host "=== Veritas Integration Tests ===" -ForegroundColor Cyan

Write-Host "`n[1/3] Testing Veritas Core..." -ForegroundColor Yellow
cd veritas-core/backend
python -m pytest tests/ -v --tb=short
cd ../..

Write-Host "`n[2/3] Testing Scholarly Hollows..." -ForegroundColor Yellow  
cd scholarly-hollows
python -m pytest tests/ -v --tb=short
cd ..

Write-Host "`n[3/3] Testing Gnosiplexio..." -ForegroundColor Yellow
cd gnosiplexio
python -m pytest tests/ -v --tb=short
cd ..

Write-Host "`n=== Tests Complete ===" -ForegroundColor Green

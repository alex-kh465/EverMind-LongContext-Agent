# LongContext Agent - Complete Project Startup Script
# Starts both backend and frontend servers

param(
    [switch]$BackendOnly,
    [switch]$FrontendOnly,
    [switch]$Help
)

if ($Help) {
    Write-Host "LongContext Agent Startup Script" -ForegroundColor Cyan
    Write-Host "====================================" -ForegroundColor Cyan
    Write-Host ""
    Write-Host "Usage:"
    Write-Host "  .\start-project.ps1              # Start both frontend and backend"
    Write-Host "  .\start-project.ps1 -BackendOnly  # Start only backend"
    Write-Host "  .\start-project.ps1 -FrontendOnly # Start only frontend"
    Write-Host "  .\start-project.ps1 -Help         # Show this help"
    Write-Host ""
    Write-Host "URLs:"
    Write-Host "  Frontend: http://localhost:5173"
    Write-Host "  Backend:  http://localhost:8000"
    Write-Host "  API Docs: http://localhost:8000/docs"
    Write-Host ""
    exit
}

Write-Host "🚀 LongContext Agent - Full Stack Startup" -ForegroundColor Cyan
Write-Host "==========================================" -ForegroundColor Cyan
Write-Host ""

Write-Host "✅ Both servers will start in separate windows" -ForegroundColor Green
Write-Host "🌐 Frontend: http://localhost:5173" -ForegroundColor Yellow
Write-Host "📊 Backend: http://localhost:8000" -ForegroundColor Yellow
Write-Host "📖 API Docs: http://localhost:8000/docs" -ForegroundColor Yellow
Write-Host ""

# Start backend
Write-Host "Starting Backend..." -ForegroundColor Cyan
Start-Process powershell -ArgumentList "-NoExit", "-Command", "cd '$PWD\backend'; .\activate.ps1; python start.py"

# Wait for backend to start
Start-Sleep -Seconds 2

# Start frontend
Write-Host "Starting Frontend..." -ForegroundColor Cyan
Start-Process powershell -ArgumentList "-NoExit", "-Command", "cd '$PWD\frontend'; .\start-dev.ps1"

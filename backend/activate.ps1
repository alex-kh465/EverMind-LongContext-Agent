# LongContext Agent Backend - Virtual Environment Activation Script
# Run this script to activate the Python virtual environment

Write-Host "🚀 LongContext Agent Backend Environment" -ForegroundColor Cyan
Write-Host "=========================================" -ForegroundColor Cyan

# Check if virtual environment exists
if (Test-Path ".\venv\Scripts\Activate.ps1") {
    Write-Host "✅ Activating virtual environment..." -ForegroundColor Green
    .\venv\Scripts\Activate.ps1
    
    Write-Host ""
    Write-Host "🐍 Python:" (python --version) -ForegroundColor Yellow
    Write-Host "📦 Installed packages:" (pip list | Measure-Object -Line).Lines "packages" -ForegroundColor Yellow
    
    Write-Host ""
    Write-Host "📋 Available commands:" -ForegroundColor Magenta
    Write-Host "  python start.py        - Start the backend server" -ForegroundColor White
    Write-Host "  python -m main         - Run main application" -ForegroundColor White
    Write-Host "  pip install -r requirements.txt - Install/update dependencies" -ForegroundColor White
    Write-Host "  deactivate             - Exit virtual environment" -ForegroundColor White
    
} else {
    Write-Host "❌ Virtual environment not found!" -ForegroundColor Red
    Write-Host "Run: python -m venv venv" -ForegroundColor Yellow
}

Write-Host ""

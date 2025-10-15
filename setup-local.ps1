# LongContext Agent - Local Setup Script for Windows
# Run this script to set up the development environment

Write-Host "LongContext Agent - Local Setup" -ForegroundColor Green
Write-Host "Setting up development environment..." -ForegroundColor Yellow

# Check prerequisites
Write-Host "`nChecking prerequisites..." -ForegroundColor Cyan

# Check Python
try {
    $pythonVersion = python --version 2>&1
    Write-Host "Python found: $pythonVersion" -ForegroundColor Green
}
catch {
    Write-Host "Python not found. Please install Python 3.9+!" -ForegroundColor Red
    exit 1
}

# Check Node.js
try {
    $nodeVersion = node --version 2>&1
    Write-Host "Node.js found: $nodeVersion" -ForegroundColor Green
}
catch {
    Write-Host "Node.js not found. Please install Node.js 18+!" -ForegroundColor Red
    exit 1
}
# Setup Backend
Write-Host "`nSetting up Backend..." -ForegroundColor Cyan
Set-Location backend

# Create virtual environment if it doesn't exist
if (-not (Test-Path "venv")) {
    Write-Host "Creating virtual environment..." -ForegroundColor Yellow
    python -m venv venv
}

# Activate virtual environment
Write-Host "Activating virtual environment..." -ForegroundColor Yellow
& ".\venv\Scripts\Activate.ps1"

# Install dependencies
Write-Host "Installing Python dependencies..." -ForegroundColor Yellow
pip install -r requirements.txt

# Create environment file if it doesn't exist
if (-not (Test-Path ".env")) {
    Write-Host "Creating backend environment file..." -ForegroundColor Yellow
    Copy-Item ".env.local" ".env"
    Write-Host "Please edit backend/.env and add your OPENAI_API_KEY!" -ForegroundColor Red
}

# Setup Frontend
Write-Host "`nSetting up Frontend..." -ForegroundColor Cyan
Set-Location ../frontend

# Install dependencies
Write-Host "Installing Node.js dependencies..." -ForegroundColor Yellow
npm install

# Create environment file if it doesn't exist
if (-not (Test-Path ".env")) {
    Write-Host "Creating frontend environment file..." -ForegroundColor Yellow
    Copy-Item ".env.local" ".env" -ErrorAction SilentlyContinue
    if (-not (Test-Path ".env")) {
        $envContent = @"
VITE_API_URL=http://localhost:8000
VITE_APP_TITLE=LongContext Agent
"@
        $envContent | Out-File -FilePath ".env" -Encoding UTF8
    }
}

Set-Location ..

Write-Host "`nSetup completed!" -ForegroundColor Green
Write-Host "`nNext Steps:" -ForegroundColor Cyan
Write-Host "1. Edit backend/.env and add your OPENAI_API_KEY" -ForegroundColor Yellow
Write-Host "2. Start the backend: cd backend; uvicorn main:app --reload" -ForegroundColor Yellow
Write-Host "3. Start the frontend: cd frontend; npm run dev" -ForegroundColor Yellow
Write-Host "4. Open http://localhost:5173 in your browser" -ForegroundColor Yellow

Write-Host "`nFor deployment, see DEPLOYMENT_GUIDE.md" -ForegroundColor Cyan

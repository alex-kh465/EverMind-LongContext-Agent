# LongContext Agent Frontend - Development Server
# Run this script to start the React development server

Write-Host "🚀 LongContext Agent Frontend" -ForegroundColor Cyan
Write-Host "==============================" -ForegroundColor Cyan

# Check if node_modules exists
if (Test-Path ".\node_modules") {
    Write-Host "✅ Dependencies found" -ForegroundColor Green
} else {
    Write-Host "📦 Installing dependencies..." -ForegroundColor Yellow
    npm install
}

Write-Host ""
Write-Host "🌐 Starting development server..." -ForegroundColor Green
Write-Host "📡 API URL: http://localhost:8000" -ForegroundColor Yellow
Write-Host "🖥️  Frontend URL: http://localhost:5173" -ForegroundColor Yellow
Write-Host ""
Write-Host "💡 Make sure the backend is running on port 8000" -ForegroundColor Magenta
Write-Host ""

# Start the development server
npm run dev

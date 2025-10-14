# LongContext Agent - Database Setup Checker
# Run this to verify your database configuration

Write-Host "🔍 LongContext Agent Database Checker" -ForegroundColor Cyan
Write-Host "=====================================" -ForegroundColor Cyan
Write-Host ""

# Check if we're in the right location
if (-not (Test-Path "backend\database.py")) {
    Write-Host "❌ Please run this from the project root directory" -ForegroundColor Red
    Write-Host "💡 You should see both 'backend' and 'frontend' folders here" -ForegroundColor Yellow
    exit 1
}

Write-Host "✅ Project structure looks good" -ForegroundColor Green

# Check backend environment
Write-Host ""
Write-Host "🔧 Backend Environment:" -ForegroundColor Magenta

if (Test-Path "backend\.env") {
    Write-Host "✅ Environment file exists" -ForegroundColor Green
    
    # Check for OpenAI key
    $env_content = Get-Content "backend\.env" -Raw
    if ($env_content -match "OPENAI_API_KEY=sk-") {
        Write-Host "✅ OpenAI API key configured" -ForegroundColor Green
    } else {
        Write-Host "❌ OpenAI API key missing or invalid" -ForegroundColor Red
        Write-Host "💡 Edit backend\.env and add: OPENAI_API_KEY=sk-your-key-here" -ForegroundColor Yellow
    }
} else {
    Write-Host "❌ Environment file missing" -ForegroundColor Red
    Write-Host "💡 Copy backend\.env.example to backend\.env" -ForegroundColor Yellow
}

# Check database files
Write-Host ""
Write-Host "🗄️ Database Status:" -ForegroundColor Magenta

if (Test-Path "backend\memory.db") {
    $size = (Get-Item "backend\memory.db").Length
    Write-Host "✅ SQLite database exists ($size bytes)" -ForegroundColor Green
} else {
    Write-Host "❓ SQLite database not found (will be created on first run)" -ForegroundColor Yellow
}

if (Test-Path "backend\vector_db") {
    Write-Host "✅ Vector database directory exists" -ForegroundColor Green
} else {
    Write-Host "❓ Vector database not found (will be created on first run)" -ForegroundColor Yellow
}

# Check virtual environment
Write-Host ""
Write-Host "🐍 Python Environment:" -ForegroundColor Magenta

if (Test-Path "backend\venv") {
    Write-Host "✅ Virtual environment exists" -ForegroundColor Green
    
    # Check if activated
    if ($env:VIRTUAL_ENV -like "*longcontext-agent*") {
        Write-Host "✅ Virtual environment is active" -ForegroundColor Green
    } else {
        Write-Host "❓ Virtual environment not active" -ForegroundColor Yellow
        Write-Host "💡 Run: backend\activate.ps1" -ForegroundColor Yellow
    }
} else {
    Write-Host "❌ Virtual environment missing" -ForegroundColor Red
    Write-Host "💡 Run: cd backend && python -m venv venv" -ForegroundColor Yellow
}

# Provide next steps
Write-Host ""
Write-Host "🚀 Next Steps:" -ForegroundColor Cyan
Write-Host "1. Make sure you have configured your OpenAI API key in backend\.env" -ForegroundColor White
Write-Host "2. Start the backend: cd backend && .\activate.ps1 && python start.py" -ForegroundColor White
Write-Host "3. Start the frontend: cd frontend && npm run dev" -ForegroundColor White
Write-Host "4. Visit: http://localhost:5173 (frontend) and http://localhost:8000 (backend)" -ForegroundColor White

Write-Host ""
Write-Host "📋 Database Details:" -ForegroundColor Cyan
Write-Host "• Type: Hybrid (SQLite + ChromaDB)" -ForegroundColor White
Write-Host "• SQLite: Structured data (sessions, messages, metrics)" -ForegroundColor White  
Write-Host "• ChromaDB: Vector embeddings for semantic search" -ForegroundColor White
Write-Host "• Auto-setup: Databases created automatically on first backend start" -ForegroundColor White

Write-Host ""
Write-Host "🔍 For detailed inspection, run: cd backend && python inspect_db.py" -ForegroundColor Gray

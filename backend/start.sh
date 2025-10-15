#!/bin/bash

# Set Python path to include all necessary directories
export PYTHONPATH="/app:/app/shared:/app/backend:/app/tools"

# Initialize database if needed
cd /app/backend
python -c "
import asyncio
import sys
import os

# Add all paths
sys.path.insert(0, '/app')
sys.path.insert(0, '/app/shared')
sys.path.insert(0, '/app/backend')
sys.path.insert(0, '/app/tools')

try:
    from database import DatabaseManager
    
    async def init_db():
        db = DatabaseManager()
        await db.initialize()
        print('Database initialized successfully')
    
    asyncio.run(init_db())
except Exception as e:
    print(f'Database initialization error: {e}')
    print('Continuing with startup...')
"

# Start the FastAPI application from backend directory
cd /app/backend
exec uvicorn main:app --host 0.0.0.0 --port ${PORT:-8000} --workers 1

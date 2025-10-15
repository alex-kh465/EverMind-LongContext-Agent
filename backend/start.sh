#!/bin/bash

# Initialize database if needed
python -c "
import asyncio
import sys
import os
sys.path.append('.')

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

# Start the FastAPI application
exec uvicorn main:app --host 0.0.0.0 --port ${PORT:-8000} --workers 1
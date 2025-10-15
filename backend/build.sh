#!/usr/bin/env bash
# Render build script for LongContext Agent Backend

set -o errexit  # exit on error

echo "Installing Python dependencies..."
pip install --upgrade pip
pip install -r requirements.txt

echo "Creating necessary directories..."
mkdir -p data logs

echo "Setting up database..."
python -c "
import asyncio
import sys
import os
sys.path.append('.')
from database import DatabaseManager

async def setup_db():
    db = DatabaseManager()
    await db.initialize()
    print('Database initialized successfully')

if __name__ == '__main__':
    asyncio.run(setup_db())
"

echo "Build completed successfully!"
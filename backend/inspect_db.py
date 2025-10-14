#!/usr/bin/env python3
"""
Database Inspection Script for LongContext Agent
Run this to verify your database setup and explore the data
"""

import os
import sys
import sqlite3
import json
from datetime import datetime
from pathlib import Path

def inspect_sqlite():
    """Inspect SQLite database"""
    db_path = "memory.db"
    
    if not os.path.exists(db_path):
        print(f"❌ SQLite database not found at: {db_path}")
        print("💡 Run the backend server first to create the database")
        return False
    
    print(f"✅ SQLite database found: {db_path}")
    print(f"📏 Database size: {os.path.getsize(db_path)} bytes")
    
    try:
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        # Get all tables
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = [row[0] for row in cursor.fetchall()]
        
        print(f"📋 Tables found: {len(tables)}")
        
        for table in tables:
            # Get row count for each table
            cursor.execute(f"SELECT COUNT(*) FROM {table}")
            count = cursor.fetchone()[0]
            print(f"  📊 {table}: {count} records")
            
            # Show recent records if any exist
            if count > 0:
                cursor.execute(f"SELECT * FROM {table} ORDER BY rowid DESC LIMIT 3")
                records = cursor.fetchall()
                print(f"    📝 Recent records:")
                for i, record in enumerate(records):
                    record_dict = dict(record)
                    # Truncate long content
                    for key, value in record_dict.items():
                        if isinstance(value, str) and len(value) > 50:
                            record_dict[key] = value[:47] + "..."
                    print(f"      {i+1}. {record_dict}")
        
        conn.close()
        return True
        
    except Exception as e:
        print(f"❌ Error inspecting SQLite: {e}")
        return False

def inspect_chromadb():
    """Inspect ChromaDB vector database"""
    vector_db_path = "vector_db"
    
    if not os.path.exists(vector_db_path):
        print(f"❌ ChromaDB directory not found at: {vector_db_path}")
        print("💡 Run the backend server first to create the vector database")
        return False
    
    print(f"✅ ChromaDB directory found: {vector_db_path}")
    
    # Calculate directory size
    total_size = sum(f.stat().st_size for f in Path(vector_db_path).rglob('*') if f.is_file())
    print(f"📏 Vector DB size: {total_size} bytes")
    
    try:
        # Try to connect to ChromaDB
        import chromadb
        from chromadb.config import Settings
        
        client = chromadb.PersistentClient(
            path=vector_db_path,
            settings=Settings(anonymized_telemetry=False)
        )
        
        collections = client.list_collections()
        print(f"📋 Collections found: {len(collections)}")
        
        for collection in collections:
            count = collection.count()
            print(f"  🔍 {collection.name}: {count} vectors")
            
            if count > 0:
                # Get a sample of documents
                result = collection.get(limit=3)
                if result['documents']:
                    print(f"    📝 Sample documents:")
                    for i, doc in enumerate(result['documents']):
                        truncated = doc[:47] + "..." if len(doc) > 50 else doc
                        metadata = result['metadatas'][i] if result['metadatas'] else {}
                        print(f"      {i+1}. {truncated} | {metadata}")
        
        return True
        
    except ImportError:
        print("❌ ChromaDB not available (chromadb package not installed)")
        return False
    except Exception as e:
        print(f"❌ Error inspecting ChromaDB: {e}")
        return False

def check_environment():
    """Check environment configuration"""
    print("\n🔧 Environment Configuration:")
    
    env_file = ".env"
    if os.path.exists(env_file):
        print(f"✅ Environment file found: {env_file}")
        with open(env_file, 'r') as f:
            lines = f.readlines()
        
        # Check for key configurations
        has_openai_key = False
        has_db_config = False
        
        for line in lines:
            line = line.strip()
            if line.startswith('OPENAI_API_KEY=') and len(line) > 20:
                has_openai_key = True
                print("  ✅ OpenAI API key configured")
            elif line.startswith('DATABASE_URL='):
                has_db_config = True
                print(f"  ✅ Database URL: {line}")
        
        if not has_openai_key:
            print("  ❌ OpenAI API key not found or too short")
        if not has_db_config:
            print("  ❌ Database URL not configured")
    else:
        print(f"❌ Environment file not found: {env_file}")
        print("💡 Copy .env.example to .env and configure your settings")

def main():
    """Main inspection function"""
    print("🔍 LongContext Agent Database Inspector")
    print("=" * 50)
    
    # Check current directory
    if not os.path.exists("database.py"):
        print("❌ Not in backend directory!")
        print("💡 Navigate to the backend directory first:")
        print("   cd backend")
        sys.exit(1)
    
    # Check environment
    check_environment()
    
    # Inspect databases
    print("\n🗄️ Database Inspection:")
    print("-" * 30)
    
    sqlite_ok = inspect_sqlite()
    print()
    chromadb_ok = inspect_chromadb()
    
    # Summary
    print("\n📊 Summary:")
    print("-" * 20)
    
    if sqlite_ok and chromadb_ok:
        print("🎉 All databases are properly set up!")
        print("✅ Your LongContext Agent is ready to use")
    elif sqlite_ok:
        print("⚠️  SQLite is working, but ChromaDB needs attention")
        print("💡 Make sure you have chromadb installed: pip install chromadb")
    elif chromadb_ok:
        print("⚠️  ChromaDB is working, but SQLite needs attention")
        print("💡 Check if the backend has been started at least once")
    else:
        print("❌ Database setup needs attention")
        print("💡 Try running the backend server: python start.py")
    
    print(f"\n🕐 Inspection completed at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

if __name__ == "__main__":
    main()

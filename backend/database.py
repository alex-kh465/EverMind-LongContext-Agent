"""
Database manager for LongContext Agent.
Handles SQLite for structured data and ChromaDB for vector storage.
"""

import os
import sys
import json
import logging
import asyncio
import sqlite3
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime

import chromadb
import numpy as np
from chromadb.config import Settings
from chromadb.errors import NotFoundError

# Add shared directory to path
sys.path.append(os.path.join(os.path.dirname(__file__), "..", "shared"))
from models import Memory, ConversationSession, BaseMessage, MemoryType, MessageRole

logger = logging.getLogger(__name__)


class DatabaseManager:
    """Manages both SQLite and ChromaDB connections"""
    
    def __init__(self, db_path: str = "./memory.db", vector_db_path: str = "./vector_db"):
        self.db_path = db_path
        self.vector_db_path = vector_db_path
        self.connection: Optional[sqlite3.Connection] = None
        self.vector_client: Optional[chromadb.Client] = None
        self.vector_collection = None
        
    async def initialize(self):
        """Initialize both databases"""
        try:
            # Initialize SQLite
            await self._init_sqlite()
            
            # Initialize ChromaDB
            await self._init_chromadb()
            
            logger.info("Database initialization completed successfully")
            
        except Exception as e:
            logger.error(f"Database initialization failed: {e}")
            raise
    
    async def _init_sqlite(self):
        """Initialize SQLite database with schema"""
        self.connection = sqlite3.connect(
            self.db_path,
            isolation_level=None,  # Enable autocommit
            check_same_thread=False
        )
        self.connection.row_factory = sqlite3.Row
        
        # Create tables
        await asyncio.get_event_loop().run_in_executor(
            None, self._create_sqlite_tables
        )
        
        logger.info(f"SQLite database initialized at {self.db_path}")
    
    def _create_sqlite_tables(self):
        """Create SQLite tables"""
        cursor = self.connection.cursor()
        
        # Conversation sessions table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS sessions (
                id TEXT PRIMARY KEY,
                title TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                metadata TEXT DEFAULT '{}'
            )
        """)
        
        # Messages table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS messages (
                id TEXT PRIMARY KEY,
                session_id TEXT NOT NULL,
                role TEXT NOT NULL,
                content TEXT NOT NULL,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                metadata TEXT DEFAULT '{}',
                FOREIGN KEY (session_id) REFERENCES sessions (id) ON DELETE CASCADE
            )
        """)
        
        # Memories table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS memories (
                id TEXT PRIMARY KEY,
                session_id TEXT NOT NULL,
                memory_type TEXT NOT NULL,
                content TEXT NOT NULL,
                relevance_score REAL DEFAULT 0.0,
                compression_ratio REAL DEFAULT 1.0,
                token_count INTEGER DEFAULT 0,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                metadata TEXT DEFAULT '{}',
                FOREIGN KEY (session_id) REFERENCES sessions (id) ON DELETE CASCADE
            )
        """)
        
        # Performance metrics table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS metrics (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                metric_name TEXT NOT NULL,
                metric_value REAL NOT NULL,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                metadata TEXT DEFAULT '{}'
            )
        """)
        
        # Tool calls table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS tool_calls (
                id TEXT PRIMARY KEY,
                session_id TEXT NOT NULL,
                tool_type TEXT NOT NULL,
                parameters TEXT NOT NULL,
                result TEXT,
                execution_time_ms REAL DEFAULT 0.0,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (session_id) REFERENCES sessions (id) ON DELETE CASCADE
            )
        """)
        
        # Create indexes
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_messages_session ON messages(session_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_memories_session ON memories(session_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_memories_type ON memories(memory_type)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_memories_score ON memories(relevance_score)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_metrics_name ON metrics(metric_name)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_tool_calls_session ON tool_calls(session_id)")
        
        self.connection.commit()
        logger.info("SQLite tables created successfully")
    
    async def _init_chromadb(self):
        """Initialize ChromaDB for vector storage"""
        try:
            # Create client with persistent storage
            self.vector_client = chromadb.PersistentClient(
                path=self.vector_db_path,
                settings=Settings(
                    anonymized_telemetry=False,
                    allow_reset=True
                )
            )
            
            # Get or create collection
            try:
                self.vector_collection = self.vector_client.get_collection("memories")
                logger.info("Loaded existing vector collection")
            except (ValueError, NotFoundError, Exception) as e:
                # Collection doesn't exist, create it
                if ("does not exist" in str(e) or 
                    "Collection [memories] does not exists" in str(e) or
                    isinstance(e, NotFoundError)):
                    self.vector_collection = self.vector_client.create_collection(
                        name="memories",
                        metadata={"hnsw:space": "cosine"}
                    )
                    logger.info("Created new vector collection")
                else:
                    # Re-raise if it's a different error
                    raise
            
        except Exception as e:
            logger.error(f"ChromaDB initialization failed: {e}")
            # Fallback to in-memory client
            self.vector_client = chromadb.Client()
            self.vector_collection = self.vector_client.create_collection(
                name="memories",
                metadata={"hnsw:space": "cosine"}
            )
            logger.warning("Using in-memory vector database as fallback")
    
    # SQLite Operations
    async def execute_query(self, query: str, params: tuple = ()) -> List[sqlite3.Row]:
        """Execute SELECT query and return results"""
        def _execute():
            cursor = self.connection.cursor()
            cursor.execute(query, params)
            return cursor.fetchall()
        
        return await asyncio.get_event_loop().run_in_executor(None, _execute)
    
    async def execute_update(self, query: str, params: tuple = ()) -> int:
        """Execute INSERT/UPDATE/DELETE query and return affected rows"""
        def _execute():
            cursor = self.connection.cursor()
            cursor.execute(query, params)
            return cursor.rowcount
        
        return await asyncio.get_event_loop().run_in_executor(None, _execute)
    
    async def execute_many(self, query: str, params_list: List[tuple]) -> int:
        """Execute query with multiple parameter sets"""
        def _execute():
            cursor = self.connection.cursor()
            cursor.executemany(query, params_list)
            return cursor.rowcount
        
        return await asyncio.get_event_loop().run_in_executor(None, _execute)
    
    # Session Operations
    async def create_session(self, session: ConversationSession) -> bool:
        """Create a new conversation session"""
        try:
            await self.execute_update(
                "INSERT INTO sessions (id, title, created_at, updated_at, metadata) VALUES (?, ?, ?, ?, ?)",
                (
                    session.id,
                    session.title,
                    session.created_at,
                    session.updated_at,
                    json.dumps(session.metadata)
                )
            )
            logger.debug(f"Created session: {session.id}")
            return True
        except Exception as e:
            logger.error(f"Failed to create session: {e}")
            return False
    
    async def get_session(self, session_id: str) -> Optional[ConversationSession]:
        """Get session by ID"""
        try:
            rows = await self.execute_query(
                "SELECT * FROM sessions WHERE id = ?",
                (session_id,)
            )
            
            if not rows:
                return None
            
            row = rows[0]
            return ConversationSession(
                id=row["id"],
                title=row["title"],
                created_at=datetime.fromisoformat(row["created_at"]),
                updated_at=datetime.fromisoformat(row["updated_at"]),
                metadata=json.loads(row["metadata"])
            )
        except Exception as e:
            logger.error(f"Failed to get session: {e}")
            return None
    
    async def list_sessions(self, limit: int = 100) -> List[ConversationSession]:
        """List all sessions"""
        try:
            rows = await self.execute_query(
                "SELECT * FROM sessions ORDER BY updated_at DESC LIMIT ?",
                (limit,)
            )
            
            sessions = []
            for row in rows:
                session = ConversationSession(
                    id=row["id"],
                    title=row["title"],
                    created_at=datetime.fromisoformat(row["created_at"]),
                    updated_at=datetime.fromisoformat(row["updated_at"]),
                    metadata=json.loads(row["metadata"])
                )
                sessions.append(session)
            
            return sessions
        except Exception as e:
            logger.error(f"Failed to list sessions: {e}")
            return []
    
    async def delete_session(self, session_id: str) -> bool:
        """Delete session and all related data"""
        try:
            # Delete from vector store
            try:
                # Get all memory IDs for this session
                memory_rows = await self.execute_query(
                    "SELECT id FROM memories WHERE session_id = ?",
                    (session_id,)
                )
                memory_ids = [row["id"] for row in memory_rows]
                
                if memory_ids:
                    self.vector_collection.delete(ids=memory_ids)
            except Exception as e:
                logger.warning(f"Failed to delete vectors for session {session_id}: {e}")
            
            # Delete from SQLite (cascades to messages, memories, tool_calls)
            affected = await self.execute_update(
                "DELETE FROM sessions WHERE id = ?",
                (session_id,)
            )
            
            logger.info(f"Deleted session {session_id} (affected {affected} rows)")
            return affected > 0
            
        except Exception as e:
            logger.error(f"Failed to delete session: {e}")
            return False
    
    # Message Operations
    async def save_message(self, message: BaseMessage, session_id: str) -> bool:
        """Save a message"""
        try:
            await self.execute_update(
                "INSERT INTO messages (id, session_id, role, content, timestamp, metadata) VALUES (?, ?, ?, ?, ?, ?)",
                (
                    message.id,
                    session_id,
                    message.role.value,
                    message.content,
                    message.timestamp,
                    json.dumps(message.metadata)
                )
            )
            return True
        except Exception as e:
            logger.error(f"Failed to save message: {e}")
            return False
    
    async def get_session_messages(self, session_id: str, limit: int = 100) -> List[BaseMessage]:
        """Get messages for a session"""
        try:
            rows = await self.execute_query(
                "SELECT * FROM messages WHERE session_id = ? ORDER BY timestamp ASC LIMIT ?",
                (session_id, limit)
            )
            
            messages = []
            for row in rows:
                message = BaseMessage(
                    id=row["id"],
                    role=MessageRole(row["role"]),
                    content=row["content"],
                    timestamp=datetime.fromisoformat(row["timestamp"]),
                    metadata=json.loads(row["metadata"])
                )
                messages.append(message)
            
            return messages
        except Exception as e:
            logger.error(f"Failed to get messages: {e}")
            return []
    
    # Memory Operations
    async def save_memory(self, memory: Memory, embedding: Optional[List[float]] = None) -> bool:
        """Save a memory to both SQLite and vector store"""
        try:
            # Save to SQLite
            await self.execute_update(
                """INSERT INTO memories 
                   (id, session_id, memory_type, content, relevance_score, compression_ratio, token_count, timestamp, metadata) 
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    memory.id,
                    memory.session_id,
                    memory.memory_type.value,
                    memory.content,
                    memory.relevance_score,
                    memory.compression_ratio,
                    memory.token_count,
                    memory.timestamp,
                    json.dumps(memory.metadata)
                )
            )
            
            # Save to vector store if embedding is provided
            if embedding and self.vector_collection:
                self.vector_collection.add(
                    ids=[memory.id],
                    embeddings=[embedding],
                    documents=[memory.content],
                    metadatas=[{
                        "session_id": memory.session_id,
                        "memory_type": memory.memory_type.value,
                        "relevance_score": memory.relevance_score,
                        "timestamp": memory.timestamp.isoformat()
                    }]
                )
            
            logger.debug(f"Saved memory: {memory.id}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to save memory: {e}")
            return False
    
    async def search_memories_vector(self, query_embedding: List[float], limit: int = 10, session_id: Optional[str] = None) -> List[Dict[str, Any]]:
        """Search memories using vector similarity"""
        try:
            where_clause = {}
            if session_id:
                where_clause["session_id"] = session_id
            
            results = self.vector_collection.query(
                query_embeddings=[query_embedding],
                n_results=limit,
                where=where_clause if where_clause else None
            )
            
            # Format results
            memories = []
            if results["ids"] and results["ids"][0]:
                for i in range(len(results["ids"][0])):
                    memory = {
                        "id": results["ids"][0][i],
                        "content": results["documents"][0][i],
                        "distance": results["distances"][0][i] if results["distances"] else 0.0,
                        "metadata": results["metadatas"][0][i]
                    }
                    memories.append(memory)
            
            return memories
            
        except Exception as e:
            logger.error(f"Vector search failed: {e}")
            return []
    
    async def get_memories(self, session_id: Optional[str] = None, memory_types: Optional[List[MemoryType]] = None, limit: int = 10) -> List[Memory]:
        """Get memories with optional filters"""
        try:
            query = "SELECT * FROM memories WHERE 1=1"
            params = []
            
            if session_id:
                query += " AND session_id = ?"
                params.append(session_id)
            
            if memory_types:
                placeholders = ",".join("?" * len(memory_types))
                query += f" AND memory_type IN ({placeholders})"
                params.extend([mt.value for mt in memory_types])
            
            query += " ORDER BY timestamp DESC LIMIT ?"
            params.append(limit)
            
            rows = await self.execute_query(query, tuple(params))
            
            memories = []
            for row in rows:
                memory = Memory(
                    id=row["id"],
                    session_id=row["session_id"],
                    memory_type=MemoryType(row["memory_type"]),
                    content=row["content"],
                    relevance_score=row["relevance_score"],
                    compression_ratio=row["compression_ratio"],
                    token_count=row["token_count"],
                    timestamp=datetime.fromisoformat(row["timestamp"]),
                    metadata=json.loads(row["metadata"])
                )
                memories.append(memory)
            
            return memories
            
        except Exception as e:
            logger.error(f"Failed to get memories: {e}")
            return []
    
    # Metrics Operations
    async def save_metric(self, name: str, value: float, metadata: Dict[str, Any] = None) -> bool:
        """Save a performance metric"""
        try:
            await self.execute_update(
                "INSERT INTO metrics (metric_name, metric_value, metadata) VALUES (?, ?, ?)",
                (name, value, json.dumps(metadata or {}))
            )
            return True
        except Exception as e:
            logger.error(f"Failed to save metric: {e}")
            return False
    
    async def get_metrics(self, metric_name: Optional[str] = None, hours: int = 24) -> List[Dict[str, Any]]:
        """Get metrics for the specified time period"""
        try:
            query = "SELECT * FROM metrics WHERE datetime(timestamp) > datetime('now', '-{} hours')".format(hours)
            params = []
            
            if metric_name:
                query += " AND metric_name = ?"
                params.append(metric_name)
            
            query += " ORDER BY timestamp DESC"
            
            rows = await self.execute_query(query, tuple(params))
            
            metrics = []
            for row in rows:
                metric = {
                    "name": row["metric_name"],
                    "value": row["metric_value"],
                    "timestamp": row["timestamp"],
                    "metadata": json.loads(row["metadata"])
                }
                metrics.append(metric)
            
            return metrics
            
        except Exception as e:
            logger.error(f"Failed to get metrics: {e}")
            return []
    
    # Health Check
    async def health_check(self) -> bool:
        """Perform database health check"""
        try:
            # Check SQLite
            await self.execute_query("SELECT 1")
            
            # Check ChromaDB
            if self.vector_collection:
                self.vector_collection.count()
            
            return True
            
        except Exception as e:
            logger.error(f"Database health check failed: {e}")
            return False
    
    # Cleanup
    async def close(self):
        """Close database connections"""
        try:
            if self.connection:
                await asyncio.get_event_loop().run_in_executor(
                    None, self.connection.close
                )
            logger.info("Database connections closed")
        except Exception as e:
            logger.error(f"Error closing database: {e}")


# Dependency injection helper
_db_manager_instance: Optional[DatabaseManager] = None

def get_db_manager() -> DatabaseManager:
    """Get the singleton database manager instance"""
    global _db_manager_instance
    if _db_manager_instance is None:
        _db_manager_instance = DatabaseManager()
    return _db_manager_instance

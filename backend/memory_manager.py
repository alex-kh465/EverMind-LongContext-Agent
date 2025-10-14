"""
Memory Manager for LongContext Agent.
Handles context storage, summarization, and retrieval with performance metrics tracking.
"""

import os
import sys
import logging
import asyncio
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime, timedelta

# Add shared directory to path
sys.path.append(os.path.join(os.path.dirname(__file__), "..", "shared"))
from models import (
    Memory, ConversationSession, BaseMessage, MemoryType, MessageRole,
    PerformanceMetrics
)

from database import DatabaseManager
from utils import generate_id, calculate_token_count, safe_json_dumps, safe_json_loads

logger = logging.getLogger(__name__)


class MemoryManager:
    """Manages conversation memory with smart compression and retrieval"""
    
    def __init__(self, db_manager: DatabaseManager):
        self.db = db_manager
        self.retrieval_limit = int(os.getenv("RETRIEVAL_LIMIT", "10"))
        self.relevance_threshold = float(os.getenv("RELEVANCE_THRESHOLD", "0.7"))
        self.compression_threshold = int(os.getenv("COMPRESSION_THRESHOLD", "8000"))  # Tokens
        self.retriever = None  # Will be set by the agent if needed
        
    # Session Management
    async def create_session(self, title: str = "New Conversation") -> ConversationSession:
        """Create a new conversation session"""
        session_id = generate_id("session")
        
        session = ConversationSession(
            id=session_id,
            title=title,
            messages=[],
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
            metadata={}
        )
        
        success = await self.db.create_session(session)
        if not success:
            raise RuntimeError(f"Failed to create session {session_id}")
        
        logger.info(f"Created new session: {session_id}")
        return session
    
    async def get_session(self, session_id: str) -> Optional[ConversationSession]:
        """Get session by ID with messages"""
        session = await self.db.get_session(session_id)
        if session:
            # Load messages
            messages = await self.db.get_session_messages(session_id)
            session.messages = messages
        
        return session
    
    async def list_sessions(self) -> List[ConversationSession]:
        """List all sessions"""
        return await self.db.list_sessions()
    
    async def delete_session(self, session_id: str) -> bool:
        """Delete a session and all related data"""
        return await self.db.delete_session(session_id)
    
    async def update_session_title(self, session_id: str, title: str) -> bool:
        """Update session title"""
        try:
            await self.db.execute_update(
                "UPDATE sessions SET title = ?, updated_at = ? WHERE id = ?",
                (title, datetime.utcnow(), session_id)
            )
            return True
        except Exception as e:
            logger.error(f"Failed to update session title: {e}")
            return False
    
    # Message Management
    async def save_message(self, message: BaseMessage, session_id: str) -> bool:
        """Save a message and create memory if needed"""
        try:
            # Save the message
            success = await self.db.save_message(message, session_id)
            if not success:
                return False
            
            # Create memory for the message
            await self._create_message_memory(message, session_id)
            
            # Update session timestamp
            await self.db.execute_update(
                "UPDATE sessions SET updated_at = ? WHERE id = ?",
                (datetime.utcnow(), session_id)
            )
            
            # Check if compression is needed
            await self._check_compression_needed(session_id)
            
            logger.debug(f"Saved message: {message.id}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to save message: {e}")
            return False
    
    async def _create_message_memory(self, message: BaseMessage, session_id: str):
        """Create memory entry for a message"""
        memory_id = generate_id("memory")
        token_count = calculate_token_count(message.content)
        
        memory = Memory(
            id=memory_id,
            session_id=session_id,
            memory_type=MemoryType.CONVERSATION,
            content=message.content,
            relevance_score=1.0,  # New messages have max relevance
            compression_ratio=1.0,
            token_count=token_count,
            timestamp=message.timestamp,
            metadata={
                "message_id": message.id,
                "role": message.role.value,
                "original_message": True
            }
        )
        
        await self.db.save_memory(memory)
    
    # Memory Storage and Retrieval
    async def store_memory(self, session_id: str, content: str, memory_type: MemoryType, 
                          metadata: Dict[str, Any] = None, embedding: List[float] = None) -> Memory:
        """Store a memory with optional embedding"""
        memory_id = generate_id("memory")
        token_count = calculate_token_count(content)
        
        memory = Memory(
            id=memory_id,
            session_id=session_id,
            memory_type=memory_type,
            content=content,
            relevance_score=0.8,  # Default relevance
            compression_ratio=1.0,
            token_count=token_count,
            timestamp=datetime.utcnow(),
            metadata=metadata or {}
        )
        
        success = await self.db.save_memory(memory, embedding)
        if not success:
            raise RuntimeError(f"Failed to store memory {memory_id}")
        
        logger.debug(f"Stored memory: {memory_id} ({memory_type.value})")
        return memory
    
    async def search_memories(self, query: str, session_id: Optional[str] = None,
                            memory_types: List[MemoryType] = None, limit: int = None,
                            relevance_threshold: float = None) -> List[Memory]:
        """Search memories with hybrid approach (keyword + semantic)"""
        limit = limit or self.retrieval_limit
        relevance_threshold = relevance_threshold or self.relevance_threshold
        
        try:
            # Get memories from database
            memories = await self.db.get_memories(
                session_id=session_id,
                memory_types=memory_types,
                limit=limit * 2  # Get more to filter by relevance
            )
            
            # Simple keyword filtering for now
            # TODO: Implement semantic search with embeddings
            filtered_memories = []
            query_lower = query.lower()
            
            for memory in memories:
                # Check relevance score threshold
                if memory.relevance_score < relevance_threshold:
                    continue
                
                # Simple keyword matching
                if any(keyword in memory.content.lower() for keyword in query_lower.split()):
                    filtered_memories.append(memory)
                elif memory.relevance_score > 0.9:  # Include high-relevance memories
                    filtered_memories.append(memory)
            
            # Sort by relevance and timestamp
            filtered_memories.sort(
                key=lambda m: (m.relevance_score, m.timestamp),
                reverse=True
            )
            
            return filtered_memories[:limit]
            
        except Exception as e:
            logger.error(f"Failed to search memories: {e}")
            return []
    
    async def get_recent_context(self, session_id: str, max_tokens: int = 4000) -> Tuple[List[Memory], int]:
        """Get recent context that fits within token limit"""
        try:
            # Get recent memories in chronological order
            memories = await self.db.get_memories(
                session_id=session_id,
                limit=50  # Get more to select from
            )
            
            # Reverse to get chronological order (oldest first)
            memories.reverse()
            
            # Select memories that fit within token limit
            selected_memories = []
            current_tokens = 0
            
            for memory in memories:
                if current_tokens + memory.token_count <= max_tokens:
                    selected_memories.append(memory)
                    current_tokens += memory.token_count
                else:
                    break
            
            logger.debug(f"Selected {len(selected_memories)} memories ({current_tokens} tokens)")
            return selected_memories, current_tokens
            
        except Exception as e:
            logger.error(f"Failed to get recent context: {e}")
            return [], 0
    
    # Compression and Summarization
    async def _check_compression_needed(self, session_id: str):
        """Check if session needs memory compression"""
        try:
            # Count total tokens in session memories
            memories = await self.db.get_memories(session_id=session_id, limit=1000)
            total_tokens = sum(memory.token_count for memory in memories)
            
            if total_tokens > self.compression_threshold:
                logger.info(f"Session {session_id} needs compression ({total_tokens} tokens)")
                await self._compress_old_memories(session_id)
            
        except Exception as e:
            logger.error(f"Failed to check compression: {e}")
    
    async def _compress_old_memories(self, session_id: str):
        """Compress old memories to save space"""
        try:
            # Get memories older than 1 hour that aren't already summaries
            cutoff_time = datetime.utcnow() - timedelta(hours=1)
            
            query = """
                SELECT * FROM memories 
                WHERE session_id = ? 
                AND timestamp < ? 
                AND memory_type != 'summary'
                AND compression_ratio = 1.0
                ORDER BY timestamp ASC
                LIMIT 20
            """
            
            rows = await self.db.execute_query(query, (session_id, cutoff_time))
            
            if len(rows) < 5:  # Need at least 5 memories to compress
                return
            
            # Group memories for summarization
            memories_to_compress = []
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
                    metadata=safe_json_loads(row["metadata"], {})
                )
                memories_to_compress.append(memory)
            
            # Create summary (placeholder for now)
            # TODO: Implement actual GPT-4o-mini summarization
            combined_content = "\n".join([m.content for m in memories_to_compress])
            summary_content = f"Summary of {len(memories_to_compress)} messages: {combined_content[:200]}..."
            
            original_tokens = sum(m.token_count for m in memories_to_compress)
            summary_tokens = calculate_token_count(summary_content)
            compression_ratio = original_tokens / summary_tokens if summary_tokens > 0 else 1.0
            
            # Store summary
            summary_memory = Memory(
                id=generate_id("summary"),
                session_id=session_id,
                memory_type=MemoryType.SUMMARY,
                content=summary_content,
                relevance_score=0.7,
                compression_ratio=compression_ratio,
                token_count=summary_tokens,
                timestamp=datetime.utcnow(),
                metadata={
                    "compressed_memories": [m.id for m in memories_to_compress],
                    "original_tokens": original_tokens,
                    "compression_ratio": compression_ratio
                }
            )
            
            await self.db.save_memory(summary_memory)
            
            # Mark original memories as compressed (lower relevance)
            for memory in memories_to_compress:
                await self.db.execute_update(
                    "UPDATE memories SET relevance_score = relevance_score * 0.3 WHERE id = ?",
                    (memory.id,)
                )
            
            logger.info(f"Compressed {len(memories_to_compress)} memories into summary "
                       f"(ratio: {compression_ratio:.2f}x)")
            
            # Save compression metric
            await self.db.save_metric(
                "compression_ratio",
                compression_ratio,
                {"session_id": session_id, "memories_compressed": len(memories_to_compress)}
            )
            
        except Exception as e:
            logger.error(f"Failed to compress memories: {e}")
    
    # Performance Metrics
    async def get_performance_metrics(self) -> PerformanceMetrics:
        """Calculate and return performance metrics"""
        try:
            metrics = {}
            
            # Get recent metrics from database
            recent_metrics = await self.db.get_metrics(hours=24)
            
            # Calculate averages
            compression_ratios = [m["value"] for m in recent_metrics if m["name"] == "compression_ratio"]
            avg_compression_ratio = sum(compression_ratios) / len(compression_ratios) if compression_ratios else 1.0
            
            response_times = [m["value"] for m in recent_metrics if m["name"] == "response_time_ms"]
            avg_response_time = sum(response_times) / len(response_times) if response_times else 0.0
            
            # Get vector database size (more meaningful than SQLite rows)
            total_memories = await self.db.get_vector_db_size()
            
            # If vector DB is empty, fallback to SQLite count
            if total_memories == 0:
                total_memories_rows = await self.db.execute_query("SELECT COUNT(*) as count FROM memories")
                total_memories = total_memories_rows[0]["count"] if total_memories_rows else 0
            
            active_sessions_rows = await self.db.execute_query(
                "SELECT COUNT(*) as count FROM sessions WHERE updated_at > datetime('now', '-24 hours')"
            )
            active_sessions = active_sessions_rows[0]["count"] if active_sessions_rows else 0
            
            # Calculate memory growth rate (memories per day)
            yesterday = datetime.utcnow() - timedelta(days=1)
            growth_rows = await self.db.execute_query(
                "SELECT COUNT(*) as count FROM memories WHERE timestamp > ?",
                (yesterday,)
            )
            memory_growth_rate = growth_rows[0]["count"] if growth_rows else 0
            
            # Get vector database storage size
            vector_db_size_mb = await self.db.get_vector_db_storage_size_mb()
            
            # TODO: Calculate context retention accuracy and retrieval precision
            # These would require evaluation datasets or user feedback
            
            return PerformanceMetrics(
                context_retention_accuracy=0.85,  # Placeholder
                compression_ratio=avg_compression_ratio,
                retrieval_precision=0.80,  # Placeholder
                response_latency_ms=avg_response_time,
                memory_growth_rate=memory_growth_rate,
                total_memories=total_memories,
                active_sessions=active_sessions,
                vector_db_size_mb=vector_db_size_mb
            )
            
        except Exception as e:
            logger.error(f"Failed to calculate metrics: {e}")
            return PerformanceMetrics()
    
    async def record_metric(self, name: str, value: float, metadata: Dict[str, Any] = None):
        """Record a performance metric"""
        await self.db.save_metric(name, value, metadata)
    
    # Context Building
    async def build_context(self, session_id: str, query: str, max_tokens: int = 4000) -> Tuple[str, List[Memory]]:
        """Build context for LLM from relevant memories"""
        try:
            # Get relevant memories through search
            relevant_memories = await self.search_memories(
                query=query,
                session_id=session_id,
                limit=self.retrieval_limit
            )
            
            # Get recent context
            recent_memories, recent_tokens = await self.get_recent_context(
                session_id=session_id,
                max_tokens=max_tokens // 2  # Use half for recent context
            )
            
            # Combine and deduplicate
            all_memories = []
            seen_ids = set()
            
            # Add relevant memories first
            for memory in relevant_memories:
                if memory.id not in seen_ids:
                    all_memories.append(memory)
                    seen_ids.add(memory.id)
            
            # Add recent memories if space allows
            current_tokens = sum(m.token_count for m in all_memories)
            for memory in recent_memories:
                if memory.id not in seen_ids and current_tokens + memory.token_count <= max_tokens:
                    all_memories.append(memory)
                    seen_ids.add(memory.id)
                    current_tokens += memory.token_count
            
            # Sort by timestamp (chronological order)
            all_memories.sort(key=lambda m: m.timestamp)
            
            # Build context string
            context_parts = []
            for memory in all_memories:
                context_parts.append(f"[{memory.memory_type.value.upper()}] {memory.content}")
            
            context = "\n\n".join(context_parts)
            
            logger.debug(f"Built context: {len(all_memories)} memories, {current_tokens} tokens")
            
            return context, all_memories
            
        except Exception as e:
            logger.error(f"Failed to build context: {e}")
            return "", []
    
    # Maintenance
    async def cleanup_old_memories(self, days: int = 30):
        """Clean up old, low-relevance memories"""
        try:
            cutoff_date = datetime.utcnow() - timedelta(days=days)
            
            # Delete low-relevance memories older than cutoff
            affected = await self.db.execute_update(
                "DELETE FROM memories WHERE timestamp < ? AND relevance_score < 0.3",
                (cutoff_date,)
            )
            
            logger.info(f"Cleaned up {affected} old memories")
            
        except Exception as e:
            logger.error(f"Failed to cleanup memories: {e}")
    
    async def recompute_relevance_scores(self, session_id: str):
        """Recompute relevance scores for memories"""
        try:
            # Decay relevance scores for old memories
            await self.db.execute_update(
                """UPDATE memories 
                   SET relevance_score = relevance_score * 0.95 
                   WHERE session_id = ? 
                   AND timestamp < datetime('now', '-1 day')""",
                (session_id,)
            )
            
            logger.debug(f"Updated relevance scores for session {session_id}")
            
        except Exception as e:
            logger.error(f"Failed to update relevance scores: {e}")
    
    async def reset_system(self) -> bool:
        """Reset entire system by clearing all data and caches"""
        try:
            logger.warning("Resetting entire memory system...")
            
            # Reset database
            reset_success = await self.db.reset_system()
            
            if reset_success:
                # Clear any in-memory caches or state
                try:
                    if hasattr(self, 'retriever') and self.retriever:
                        self.retriever.reset_cache()
                        logger.info("Cleared retriever embedding cache")
                except Exception as e:
                    logger.warning(f"Could not clear retriever cache: {e}")
                
                logger.warning("Memory system reset completed successfully")
                return True
            else:
                logger.error("Database reset failed")
                return False
                
        except Exception as e:
            logger.error(f"Memory system reset failed: {e}")
            return False

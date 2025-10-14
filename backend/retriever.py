"""
Hybrid Retriever for LongContext Agent.
Combines semantic search (OpenAI embeddings + vector DB) with keyword search for optimal memory retrieval.
"""

import os
import sys
import logging
import asyncio
import numpy as np
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime

from openai import AsyncOpenAI

# Add shared directory to path
sys.path.append(os.path.join(os.path.dirname(__file__), "..", "shared"))
from models import Memory, MemoryType

from database import DatabaseManager
from utils import openai_rate_limiter, openai_circuit_breaker, calculate_token_count

logger = logging.getLogger(__name__)


class HybridRetriever:
    """Hybrid memory retrieval system combining semantic and keyword search"""
    
    def __init__(self, db_manager: DatabaseManager):
        self.db = db_manager
        self.openai_client = AsyncOpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        self.embedding_model = "text-embedding-3-small"  # Latest, efficient embedding model
        self.embedding_dimension = 1536
        
        # Search parameters
        self.semantic_weight = 0.7
        self.keyword_weight = 0.3
        self.relevance_decay_days = 7
    
    async def generate_embedding(self, text: str) -> Optional[List[float]]:
        """Generate embedding for text using OpenAI API"""
        try:
            # Check circuit breaker
            if not openai_circuit_breaker.can_execute():
                logger.warning("OpenAI circuit breaker is open, skipping embedding generation")
                return None
            
            # Rate limiting
            await openai_rate_limiter.wait_if_needed()
            
            # Generate embedding
            response = await self.openai_client.embeddings.create(
                model=self.embedding_model,
                input=text,
                encoding_format="float"
            )
            
            embedding = response.data[0].embedding
            
            # Record success
            openai_circuit_breaker.record_success()
            
            logger.debug(f"Generated embedding for text ({len(text)} chars)")
            return embedding
            
        except Exception as e:
            logger.error(f"Failed to generate embedding: {e}")
            openai_circuit_breaker.record_failure()
            return None
    
    async def batch_generate_embeddings(self, texts: List[str], batch_size: int = 10) -> List[Optional[List[float]]]:
        """Generate embeddings for multiple texts in batches"""
        results = []
        
        for i in range(0, len(texts), batch_size):
            batch = texts[i:i + batch_size]
            
            try:
                # Check circuit breaker
                if not openai_circuit_breaker.can_execute():
                    logger.warning("OpenAI circuit breaker is open, adding None embeddings")
                    results.extend([None] * len(batch))
                    continue
                
                # Rate limiting
                await openai_rate_limiter.wait_if_needed()
                
                # Generate batch embeddings
                response = await self.openai_client.embeddings.create(
                    model=self.embedding_model,
                    input=batch,
                    encoding_format="float"
                )
                
                # Extract embeddings
                batch_embeddings = [item.embedding for item in response.data]
                results.extend(batch_embeddings)
                
                # Record success
                openai_circuit_breaker.record_success()
                
                logger.debug(f"Generated {len(batch_embeddings)} embeddings")
                
            except Exception as e:
                logger.error(f"Failed to generate batch embeddings: {e}")
                openai_circuit_breaker.record_failure()
                results.extend([None] * len(batch))
        
        return results
    
    async def embed_and_store_memory(self, memory: Memory) -> bool:
        """Generate embedding for memory content and store it"""
        try:
            # Generate embedding
            embedding = await self.generate_embedding(memory.content)
            if not embedding:
                # Store without embedding
                return await self.db.save_memory(memory)
            
            # Store with embedding
            return await self.db.save_memory(memory, embedding)
            
        except Exception as e:
            logger.error(f"Failed to embed and store memory: {e}")
            return False
    
    def calculate_keyword_similarity(self, query: str, content: str) -> float:
        """Calculate keyword-based similarity between query and content"""
        query_words = set(query.lower().split())
        content_words = set(content.lower().split())
        
        if not query_words:
            return 0.0
        
        # Jaccard similarity
        intersection = query_words.intersection(content_words)
        union = query_words.union(content_words)
        
        jaccard = len(intersection) / len(union) if union else 0.0
        
        # Boost for exact phrase matches
        phrase_boost = 0.0
        if len(query.strip()) > 3 and query.lower() in content.lower():
            phrase_boost = 0.3
        
        return min(1.0, jaccard + phrase_boost)
    
    def calculate_temporal_decay(self, timestamp: datetime) -> float:
        """Calculate temporal decay factor for memory relevance"""
        now = datetime.utcnow()
        age_days = (now - timestamp).total_seconds() / 86400  # Convert to days
        
        # Exponential decay with half-life of relevance_decay_days
        decay_factor = 2 ** (-age_days / self.relevance_decay_days)
        return max(0.1, decay_factor)  # Minimum 10% relevance
    
    async def semantic_search(self, query: str, limit: int = 10, 
                            session_id: Optional[str] = None,
                            memory_types: Optional[List[MemoryType]] = None) -> List[Tuple[Memory, float]]:
        """Perform semantic search using vector similarity"""
        try:
            # Generate query embedding
            query_embedding = await self.generate_embedding(query)
            if not query_embedding:
                logger.warning("Failed to generate query embedding, falling back to keyword search")
                return []
            
            # Search vector database
            vector_results = await self.db.search_memories_vector(
                query_embedding=query_embedding,
                limit=limit * 2,  # Get more results for filtering
                session_id=session_id
            )
            
            # Convert to Memory objects and calculate scores
            memory_scores = []
            
            for result in vector_results:
                try:
                    # Get full memory data from SQLite
                    memory_rows = await self.db.execute_query(
                        "SELECT * FROM memories WHERE id = ?",
                        (result["id"],)
                    )
                    
                    if not memory_rows:
                        continue
                    
                    row = memory_rows[0]
                    memory = Memory(
                        id=row["id"],
                        session_id=row["session_id"],
                        memory_type=MemoryType(row["memory_type"]),
                        content=row["content"],
                        relevance_score=row["relevance_score"],
                        compression_ratio=row["compression_ratio"],
                        token_count=row["token_count"],
                        timestamp=datetime.fromisoformat(row["timestamp"]),
                        metadata={}  # Simplified for now
                    )
                    
                    # Filter by memory types if specified
                    if memory_types and memory.memory_type not in memory_types:
                        continue
                    
                    # Calculate semantic similarity score
                    # ChromaDB uses cosine distance, convert to similarity
                    distance = result.get("distance", 1.0)
                    semantic_score = 1.0 - distance  # Convert distance to similarity
                    
                    # Apply temporal decay
                    temporal_factor = self.calculate_temporal_decay(memory.timestamp)
                    
                    # Combine with stored relevance score
                    final_score = (
                        semantic_score * 0.6 +
                        memory.relevance_score * 0.3 +
                        temporal_factor * 0.1
                    )
                    
                    memory_scores.append((memory, final_score))
                    
                except Exception as e:
                    logger.error(f"Error processing semantic search result: {e}")
                    continue
            
            # Sort by score and limit results
            memory_scores.sort(key=lambda x: x[1], reverse=True)
            return memory_scores[:limit]
            
        except Exception as e:
            logger.error(f"Semantic search failed: {e}")
            return []
    
    async def keyword_search(self, query: str, limit: int = 10,
                           session_id: Optional[str] = None,
                           memory_types: Optional[List[MemoryType]] = None) -> List[Tuple[Memory, float]]:
        """Perform keyword-based search"""
        try:
            # Build SQL query
            sql_query = "SELECT * FROM memories WHERE 1=1"
            params = []
            
            if session_id:
                sql_query += " AND session_id = ?"
                params.append(session_id)
            
            if memory_types:
                placeholders = ",".join("?" * len(memory_types))
                sql_query += f" AND memory_type IN ({placeholders})"
                params.extend([mt.value for mt in memory_types])
            
            # Simple text search using LIKE
            query_terms = query.lower().split()
            if query_terms:
                like_conditions = []
                for term in query_terms:
                    like_conditions.append("LOWER(content) LIKE ?")
                    params.append(f"%{term}%")
                
                if like_conditions:
                    sql_query += f" AND ({' OR '.join(like_conditions)})"
            
            sql_query += " ORDER BY relevance_score DESC, timestamp DESC LIMIT ?"
            params.append(limit * 2)
            
            # Execute search
            rows = await self.db.execute_query(sql_query, tuple(params))
            
            # Convert to Memory objects and calculate keyword similarity scores
            memory_scores = []
            
            for row in rows:
                try:
                    memory = Memory(
                        id=row["id"],
                        session_id=row["session_id"],
                        memory_type=MemoryType(row["memory_type"]),
                        content=row["content"],
                        relevance_score=row["relevance_score"],
                        compression_ratio=row["compression_ratio"],
                        token_count=row["token_count"],
                        timestamp=datetime.fromisoformat(row["timestamp"]),
                        metadata={}
                    )
                    
                    # Calculate keyword similarity
                    keyword_score = self.calculate_keyword_similarity(query, memory.content)
                    
                    # Apply temporal decay
                    temporal_factor = self.calculate_temporal_decay(memory.timestamp)
                    
                    # Combine scores
                    final_score = (
                        keyword_score * 0.6 +
                        memory.relevance_score * 0.3 +
                        temporal_factor * 0.1
                    )
                    
                    if final_score > 0.1:  # Only include results with meaningful scores
                        memory_scores.append((memory, final_score))
                    
                except Exception as e:
                    logger.error(f"Error processing keyword search result: {e}")
                    continue
            
            # Sort by score and limit
            memory_scores.sort(key=lambda x: x[1], reverse=True)
            return memory_scores[:limit]
            
        except Exception as e:
            logger.error(f"Keyword search failed: {e}")
            return []
    
    async def hybrid_search(self, query: str, limit: int = 10,
                          session_id: Optional[str] = None,
                          memory_types: Optional[List[MemoryType]] = None,
                          min_relevance: float = 0.3) -> List[Memory]:
        """Perform hybrid search combining semantic and keyword approaches"""
        try:
            # Perform both searches concurrently
            semantic_task = asyncio.create_task(
                self.semantic_search(query, limit, session_id, memory_types)
            )
            keyword_task = asyncio.create_task(
                self.keyword_search(query, limit, session_id, memory_types)
            )
            
            semantic_results, keyword_results = await asyncio.gather(
                semantic_task, keyword_task, return_exceptions=True
            )
            
            # Handle exceptions
            if isinstance(semantic_results, Exception):
                logger.error(f"Semantic search failed: {semantic_results}")
                semantic_results = []
            
            if isinstance(keyword_results, Exception):
                logger.error(f"Keyword search failed: {keyword_results}")
                keyword_results = []
            
            # Combine results
            combined_scores = {}
            
            # Add semantic results
            for memory, score in semantic_results:
                combined_scores[memory.id] = {
                    "memory": memory,
                    "semantic_score": score,
                    "keyword_score": 0.0
                }
            
            # Add keyword results
            for memory, score in keyword_results:
                if memory.id in combined_scores:
                    combined_scores[memory.id]["keyword_score"] = score
                else:
                    combined_scores[memory.id] = {
                        "memory": memory,
                        "semantic_score": 0.0,
                        "keyword_score": score
                    }
            
            # Calculate final hybrid scores
            final_results = []
            
            for memory_data in combined_scores.values():
                memory = memory_data["memory"]
                semantic_score = memory_data["semantic_score"]
                keyword_score = memory_data["keyword_score"]
                
                # Weighted combination
                hybrid_score = (
                    semantic_score * self.semantic_weight +
                    keyword_score * self.keyword_weight
                )
                
                # Apply minimum relevance threshold
                if hybrid_score >= min_relevance:
                    final_results.append((memory, hybrid_score))
            
            # Sort by hybrid score and return top results
            final_results.sort(key=lambda x: x[1], reverse=True)
            
            # Extract memories
            retrieved_memories = [memory for memory, score in final_results[:limit]]
            
            logger.info(f"Hybrid search returned {len(retrieved_memories)} results "
                       f"(semantic: {len(semantic_results)}, keyword: {len(keyword_results)})")
            
            return retrieved_memories
            
        except Exception as e:
            logger.error(f"Hybrid search failed: {e}")
            return []
    
    async def retrieve_context(self, query: str, session_id: str, max_tokens: int = 4000) -> Tuple[List[Memory], str]:
        """Retrieve relevant context for a query within token limits"""
        try:
            # First, get recent conversation memories
            recent_memories = await self.db.get_memories(
                session_id=session_id,
                memory_types=[MemoryType.CONVERSATION],
                limit=20
            )
            
            # Perform hybrid search for relevant memories
            relevant_memories = await self.hybrid_search(
                query=query,
                session_id=session_id,
                limit=15
            )
            
            # Combine and deduplicate
            all_memories = {}
            
            # Add recent memories (higher priority)
            for memory in recent_memories[-10:]:  # Last 10 messages
                all_memories[memory.id] = memory
            
            # Add relevant memories
            for memory in relevant_memories:
                all_memories[memory.id] = memory
            
            # Sort by timestamp
            sorted_memories = sorted(all_memories.values(), key=lambda m: m.timestamp)
            
            # Select memories that fit within token limit
            selected_memories = []
            current_tokens = 0
            
            for memory in sorted_memories:
                if current_tokens + memory.token_count <= max_tokens:
                    selected_memories.append(memory)
                    current_tokens += memory.token_count
                else:
                    break
            
            # Build context string
            context_parts = []
            for memory in selected_memories:
                role_prefix = ""
                if "role" in memory.metadata:
                    role_prefix = f"[{memory.metadata['role'].upper()}] "
                
                context_parts.append(f"{role_prefix}{memory.content}")
            
            context = "\n\n".join(context_parts)
            
            logger.info(f"Retrieved context: {len(selected_memories)} memories, {current_tokens} tokens")
            
            return selected_memories, context
            
        except Exception as e:
            logger.error(f"Failed to retrieve context: {e}")
            return [], ""
    
    async def update_memory_embeddings(self, batch_size: int = 50):
        """Update embeddings for memories that don't have them"""
        try:
            # Find memories without embeddings
            memories_without_embeddings = []
            
            # Get memory IDs from vector collection
            try:
                vector_ids = set()
                if self.db.vector_collection:
                    # This is a simplified check - in practice, you'd query the collection
                    pass
            except Exception:
                vector_ids = set()
            
            # Get all memory IDs from SQL
            rows = await self.db.execute_query(
                "SELECT id, content FROM memories ORDER BY timestamp DESC LIMIT ?",
                (batch_size * 2,)
            )
            
            for row in rows:
                if row["id"] not in vector_ids:
                    memories_without_embeddings.append((row["id"], row["content"]))
            
            if not memories_without_embeddings:
                logger.info("All memories have embeddings")
                return
            
            # Process in batches
            for i in range(0, len(memories_without_embeddings), batch_size):
                batch = memories_without_embeddings[i:i + batch_size]
                
                # Extract texts and IDs
                texts = [item[1] for item in batch]
                memory_ids = [item[0] for item in batch]
                
                # Generate embeddings
                embeddings = await self.batch_generate_embeddings(texts)
                
                # Store embeddings
                for memory_id, embedding in zip(memory_ids, embeddings):
                    if embedding and self.db.vector_collection:
                        try:
                            # Get memory data
                            memory_rows = await self.db.execute_query(
                                "SELECT * FROM memories WHERE id = ?",
                                (memory_id,)
                            )
                            
                            if memory_rows:
                                row = memory_rows[0]
                                self.db.vector_collection.add(
                                    ids=[memory_id],
                                    embeddings=[embedding],
                                    documents=[row["content"]],
                                    metadatas=[{
                                        "session_id": row["session_id"],
                                        "memory_type": row["memory_type"],
                                        "timestamp": row["timestamp"]
                                    }]
                                )
                        except Exception as e:
                            logger.error(f"Failed to store embedding for {memory_id}: {e}")
                
                logger.info(f"Updated embeddings for {len(batch)} memories")
                
                # Small delay to avoid rate limits
                await asyncio.sleep(1)
            
        except Exception as e:
            logger.error(f"Failed to update memory embeddings: {e}")
    
    async def similarity_search(self, reference_memory: Memory, limit: int = 5) -> List[Memory]:
        """Find similar memories to a reference memory"""
        try:
            # Generate embedding for reference memory if not available
            embedding = None
            if reference_memory.embedding:
                embedding = reference_memory.embedding
            else:
                embedding = await self.generate_embedding(reference_memory.content)
            
            if not embedding:
                return []
            
            # Search for similar memories
            vector_results = await self.db.search_memories_vector(
                query_embedding=embedding,
                limit=limit + 1  # +1 to exclude the reference memory itself
            )
            
            # Convert to Memory objects
            similar_memories = []
            
            for result in vector_results:
                if result["id"] == reference_memory.id:
                    continue  # Skip the reference memory itself
                
                try:
                    memory_rows = await self.db.execute_query(
                        "SELECT * FROM memories WHERE id = ?",
                        (result["id"],)
                    )
                    
                    if memory_rows:
                        row = memory_rows[0]
                        memory = Memory(
                            id=row["id"],
                            session_id=row["session_id"],
                            memory_type=MemoryType(row["memory_type"]),
                            content=row["content"],
                            relevance_score=row["relevance_score"],
                            compression_ratio=row["compression_ratio"],
                            token_count=row["token_count"],
                            timestamp=datetime.fromisoformat(row["timestamp"]),
                            metadata={}
                        )
                        similar_memories.append(memory)
                        
                        if len(similar_memories) >= limit:
                            break
                            
                except Exception as e:
                    logger.error(f"Error processing similarity result: {e}")
                    continue
            
            return similar_memories
            
        except Exception as e:
            logger.error(f"Similarity search failed: {e}")
            return []

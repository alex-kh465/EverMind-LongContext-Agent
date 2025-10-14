"""
Context Summarizer for LongContext Agent.
Implements GPT-4o-mini powered summarization, compression strategies, and relevance scoring.
"""

import os
import sys
import logging
import asyncio
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime, timedelta

from openai import AsyncOpenAI

# Add shared directory to path
sys.path.append(os.path.join(os.path.dirname(__file__), "..", "shared"))
from models import Memory, MemoryType, MessageRole

from database import DatabaseManager
from utils import (
    generate_id, calculate_token_count, truncate_text,
    openai_rate_limiter, openai_circuit_breaker
)

logger = logging.getLogger(__name__)


class ContextSummarizer:
    """Advanced context summarization and compression system"""
    
    def __init__(self, db_manager: DatabaseManager):
        self.db = db_manager
        self.openai_client = AsyncOpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        self.summarization_model = os.getenv("OPENAI_SUMMARIZATION_MODEL", "gpt-4o-mini")
        
        # Compression parameters
        self.max_input_tokens = 16000  # Max tokens for summarization input
        self.target_compression_ratio = 3.0  # Aim for 3:1 compression
        self.min_memories_to_compress = 5
        self.max_memories_per_summary = 20
        
        # Quality parameters
        self.min_relevance_threshold = 0.3
        self.temporal_decay_factor = 0.95  # Daily decay
        
    async def generate_summary(self, memories: List[Memory], context: str = "", 
                             summary_type: str = "conversation") -> Optional[str]:
        """Generate a summary using GPT-4o-mini"""
        try:
            # Check circuit breaker
            if not openai_circuit_breaker.can_execute():
                logger.warning("OpenAI circuit breaker is open, skipping summarization")
                return None
            
            # Prepare content for summarization
            content_parts = []
            total_tokens = 0
            
            for memory in memories:
                memory_text = f"[{memory.timestamp.strftime('%H:%M')}] {memory.content}"
                memory_tokens = calculate_token_count(memory_text)
                
                if total_tokens + memory_tokens > self.max_input_tokens:
                    break
                
                content_parts.append(memory_text)
                total_tokens += memory_tokens
            
            if not content_parts:
                return None
            
            content_to_summarize = "\n".join(content_parts)
            
            # Create appropriate prompt based on summary type
            prompt = self._build_summarization_prompt(
                content_to_summarize, 
                summary_type, 
                context,
                len(memories)
            )
            
            # Rate limiting
            await openai_rate_limiter.wait_if_needed()
            
            # Generate summary
            response = await self.openai_client.chat.completions.create(
                model=self.summarization_model,
                messages=[
                    {"role": "system", "content": "You are an expert at creating concise, informative summaries that preserve key context and information."},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=min(2000, total_tokens // 2),  # Target 50% compression
                temperature=0.3,  # Lower temperature for consistency
            )
            
            summary = response.choices[0].message.content.strip()
            
            # Record success
            openai_circuit_breaker.record_success()
            
            # Calculate compression ratio
            original_tokens = total_tokens
            summary_tokens = calculate_token_count(summary)
            compression_ratio = original_tokens / summary_tokens if summary_tokens > 0 else 1.0
            
            logger.info(f"Generated summary: {original_tokens} -> {summary_tokens} tokens "
                       f"(ratio: {compression_ratio:.2f}x)")
            
            return summary
            
        except Exception as e:
            logger.error(f"Failed to generate summary: {e}")
            openai_circuit_breaker.record_failure()
            return None
    
    def _build_summarization_prompt(self, content: str, summary_type: str, 
                                  context: str, memory_count: int) -> str:
        """Build appropriate summarization prompt"""
        
        base_prompt = f"""Please create a concise summary of the following {summary_type} content. 
The summary should preserve key information, important details, and maintain context for future reference.

Content to summarize ({memory_count} items):
{content}

Requirements:
- Maintain chronological flow when relevant
- Preserve important facts, decisions, and outcomes
- Include key topics and themes discussed
- Keep the summary factual and objective
- Aim for {int(len(content.split()) * 0.3)} words or fewer

"""
        
        if context:
            base_prompt += f"\nAdditional context: {context}\n"
        
        if summary_type == "conversation":
            base_prompt += """
Focus on:
- Main topics discussed
- Decisions made or conclusions reached
- Questions asked and answers provided
- Any action items or follow-ups mentioned
"""
        elif summary_type == "tool_usage":
            base_prompt += """
Focus on:
- Tools used and their purposes
- Input parameters and outputs
- Success/failure status
- Any patterns or insights from tool usage
"""
        elif summary_type == "context":
            base_prompt += """
Focus on:
- Background information provided
- Context that might be relevant for future conversations
- Referenced documents, links, or external information
"""
        
        base_prompt += "\nSummary:"
        return base_prompt
    
    async def compress_memory_batch(self, session_id: str, cutoff_time: datetime) -> Optional[Memory]:
        """Compress a batch of old memories into a summary"""
        try:
            # Find memories to compress
            memories_to_compress = await self._find_compressible_memories(session_id, cutoff_time)
            
            if len(memories_to_compress) < self.min_memories_to_compress:
                logger.debug(f"Not enough memories to compress ({len(memories_to_compress)} < {self.min_memories_to_compress})")
                return None
            
            # Limit batch size
            if len(memories_to_compress) > self.max_memories_per_summary:
                memories_to_compress = memories_to_compress[:self.max_memories_per_summary]
            
            # Generate summary
            summary_content = await self.generate_summary(
                memories_to_compress,
                context=f"Conversation history from session {session_id}",
                summary_type="conversation"
            )
            
            if not summary_content:
                logger.error("Failed to generate summary content")
                return None
            
            # Calculate metrics
            original_tokens = sum(memory.token_count for memory in memories_to_compress)
            summary_tokens = calculate_token_count(summary_content)
            compression_ratio = original_tokens / summary_tokens if summary_tokens > 0 else 1.0
            
            # Create summary memory
            summary_memory = Memory(
                id=generate_id("summary"),
                session_id=session_id,
                memory_type=MemoryType.SUMMARY,
                content=summary_content,
                relevance_score=0.8,  # High relevance for summaries
                compression_ratio=compression_ratio,
                token_count=summary_tokens,
                timestamp=datetime.utcnow(),
                metadata={
                    "compressed_memory_ids": [m.id for m in memories_to_compress],
                    "original_tokens": original_tokens,
                    "compression_ratio": compression_ratio,
                    "compression_time": datetime.utcnow().isoformat(),
                    "memory_count": len(memories_to_compress),
                    "time_range": {
                        "start": memories_to_compress[0].timestamp.isoformat(),
                        "end": memories_to_compress[-1].timestamp.isoformat()
                    }
                }
            )
            
            # Store summary
            success = await self.db.save_memory(summary_memory)
            if not success:
                logger.error("Failed to store summary memory")
                return None
            
            # Update original memories (reduce relevance, don't delete)
            await self._mark_memories_compressed(memories_to_compress)
            
            # Record compression metrics
            await self.db.save_metric(
                "compression_ratio",
                compression_ratio,
                {
                    "session_id": session_id,
                    "memories_compressed": len(memories_to_compress),
                    "original_tokens": original_tokens,
                    "summary_tokens": summary_tokens
                }
            )
            
            logger.info(f"Compressed {len(memories_to_compress)} memories "
                       f"({original_tokens} -> {summary_tokens} tokens, "
                       f"ratio: {compression_ratio:.2f}x)")
            
            return summary_memory
            
        except Exception as e:
            logger.error(f"Failed to compress memory batch: {e}")
            return None
    
    async def _find_compressible_memories(self, session_id: str, cutoff_time: datetime) -> List[Memory]:
        """Find memories suitable for compression"""
        try:
            query = """
                SELECT * FROM memories 
                WHERE session_id = ? 
                AND timestamp < ? 
                AND memory_type != 'summary'
                AND relevance_score > ?
                ORDER BY timestamp ASC
            """
            
            rows = await self.db.execute_query(
                query, 
                (session_id, cutoff_time, self.min_relevance_threshold)
            )
            
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
                    metadata={}
                )
                memories.append(memory)
            
            return memories
            
        except Exception as e:
            logger.error(f"Failed to find compressible memories: {e}")
            return []
    
    async def _mark_memories_compressed(self, memories: List[Memory]):
        """Mark memories as compressed (reduce relevance but keep for reference)"""
        try:
            for memory in memories:
                # Reduce relevance significantly but don't delete
                new_relevance = memory.relevance_score * 0.2
                
                await self.db.execute_update(
                    """UPDATE memories 
                       SET relevance_score = ?, 
                           metadata = json_set(metadata, '$.compressed', 'true', '$.compression_time', ?)
                       WHERE id = ?""",
                    (new_relevance, datetime.utcnow().isoformat(), memory.id)
                )
            
        except Exception as e:
            logger.error(f"Failed to mark memories as compressed: {e}")
    
    async def adaptive_compression(self, session_id: str) -> List[Memory]:
        """Perform adaptive compression based on session state"""
        summaries_created = []
        
        try:
            # Get session memory statistics
            stats = await self._get_session_memory_stats(session_id)
            
            if stats["total_tokens"] < int(os.getenv("COMPRESSION_THRESHOLD", "8000")):
                logger.debug(f"Session {session_id} doesn't need compression "
                           f"({stats['total_tokens']} tokens)")
                return summaries_created
            
            # Determine compression strategy based on memory age distribution
            compression_times = await self._calculate_compression_points(stats)
            
            for cutoff_time in compression_times:
                summary = await self.compress_memory_batch(session_id, cutoff_time)
                if summary:
                    summaries_created.append(summary)
                
                # Small delay between compressions
                await asyncio.sleep(0.5)
            
            return summaries_created
            
        except Exception as e:
            logger.error(f"Adaptive compression failed: {e}")
            return summaries_created
    
    async def _get_session_memory_stats(self, session_id: str) -> Dict[str, Any]:
        """Get memory statistics for a session"""
        try:
            query = """
                SELECT 
                    COUNT(*) as total_memories,
                    SUM(token_count) as total_tokens,
                    AVG(relevance_score) as avg_relevance,
                    MIN(timestamp) as oldest_memory,
                    MAX(timestamp) as newest_memory,
                    SUM(CASE WHEN memory_type = 'summary' THEN 1 ELSE 0 END) as summary_count
                FROM memories 
                WHERE session_id = ?
            """
            
            rows = await self.db.execute_query(query, (session_id,))
            
            if rows:
                row = rows[0]
                return {
                    "total_memories": row["total_memories"] or 0,
                    "total_tokens": row["total_tokens"] or 0,
                    "avg_relevance": row["avg_relevance"] or 0.0,
                    "oldest_memory": row["oldest_memory"],
                    "newest_memory": row["newest_memory"],
                    "summary_count": row["summary_count"] or 0
                }
            
            return {"total_memories": 0, "total_tokens": 0, "avg_relevance": 0.0, 
                   "oldest_memory": None, "newest_memory": None, "summary_count": 0}
            
        except Exception as e:
            logger.error(f"Failed to get session memory stats: {e}")
            return {}
    
    async def _calculate_compression_points(self, stats: Dict[str, Any]) -> List[datetime]:
        """Calculate optimal compression time points"""
        compression_points = []
        
        try:
            if not stats.get("oldest_memory"):
                return compression_points
            
            oldest = datetime.fromisoformat(stats["oldest_memory"])
            newest = datetime.fromisoformat(stats["newest_memory"])
            
            # Calculate time spans for compression
            total_span = newest - oldest
            
            if total_span.total_seconds() < 3600:  # Less than 1 hour
                # Single compression point at 30 minutes ago
                compression_points.append(datetime.utcnow() - timedelta(minutes=30))
                
            elif total_span.total_seconds() < 86400:  # Less than 1 day
                # Multiple compression points
                compression_points.extend([
                    datetime.utcnow() - timedelta(hours=4),
                    datetime.utcnow() - timedelta(hours=1)
                ])
                
            else:  # More than 1 day
                # Daily compression points
                days_back = min(7, int(total_span.days) + 1)
                for day in range(1, days_back):
                    compression_points.append(
                        datetime.utcnow() - timedelta(days=day)
                    )
            
            # Filter points that have enough memories
            valid_points = []
            for point in compression_points:
                count_query = """
                    SELECT COUNT(*) as count FROM memories 
                    WHERE session_id = ? AND timestamp < ? AND memory_type != 'summary'
                """
                rows = await self.db.execute_query(count_query, (stats.get("session_id"), point))
                
                if rows and rows[0]["count"] >= self.min_memories_to_compress:
                    valid_points.append(point)
            
            return valid_points
            
        except Exception as e:
            logger.error(f"Failed to calculate compression points: {e}")
            return []
    
    async def enhance_memory_relevance(self, memory: Memory, query_context: str = "") -> float:
        """Use AI to enhance memory relevance scoring"""
        try:
            if not query_context:
                return memory.relevance_score
            
            # Check circuit breaker
            if not openai_circuit_breaker.can_execute():
                return memory.relevance_score
            
            prompt = f"""Rate the relevance of this memory to the current context on a scale of 0.0 to 1.0.

Memory content: {memory.content[:500]}
Current context: {query_context}

Consider:
- Topical relevance
- Temporal relevance (memory timestamp: {memory.timestamp})
- Information value for current context

Return only a number between 0.0 and 1.0."""
            
            # Rate limiting
            await openai_rate_limiter.wait_if_needed()
            
            response = await self.openai_client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": "You are an expert at evaluating information relevance. Respond with only a decimal number."},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=10,
                temperature=0.1
            )
            
            relevance_text = response.choices[0].message.content.strip()
            
            try:
                enhanced_relevance = float(relevance_text)
                enhanced_relevance = max(0.0, min(1.0, enhanced_relevance))  # Clamp to [0, 1]
                
                # Blend with existing relevance (70% AI, 30% original)
                final_relevance = 0.7 * enhanced_relevance + 0.3 * memory.relevance_score
                
                openai_circuit_breaker.record_success()
                return final_relevance
                
            except ValueError:
                logger.warning(f"Invalid relevance score from AI: {relevance_text}")
                return memory.relevance_score
            
        except Exception as e:
            logger.error(f"Failed to enhance memory relevance: {e}")
            openai_circuit_breaker.record_failure()
            return memory.relevance_score
    
    async def generate_contextual_tags(self, memory: Memory) -> List[str]:
        """Generate contextual tags for better memory organization"""
        try:
            # Check circuit breaker
            if not openai_circuit_breaker.can_execute():
                return []
            
            prompt = f"""Generate 3-5 relevant tags for this memory content. Tags should be single words or short phrases that capture key concepts, topics, or themes.

Memory content: {memory.content[:300]}

Return tags as a comma-separated list (e.g., "python, programming, debugging, error-handling")"""
            
            # Rate limiting
            await openai_rate_limiter.wait_if_needed()
            
            response = await self.openai_client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": "You are an expert at content analysis and tagging. Generate relevant, concise tags."},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=100,
                temperature=0.3
            )
            
            tags_text = response.choices[0].message.content.strip()
            tags = [tag.strip() for tag in tags_text.split(",")]
            
            # Clean and validate tags
            clean_tags = []
            for tag in tags:
                if tag and len(tag) > 1 and len(tag) < 30:
                    clean_tags.append(tag.lower())
            
            openai_circuit_breaker.record_success()
            return clean_tags[:5]  # Limit to 5 tags
            
        except Exception as e:
            logger.error(f"Failed to generate contextual tags: {e}")
            openai_circuit_breaker.record_failure()
            return []
    
    async def smart_memory_merge(self, similar_memories: List[Memory]) -> Optional[Memory]:
        """Intelligently merge similar memories to reduce redundancy"""
        if len(similar_memories) < 2:
            return None
        
        try:
            # Prepare content for merging
            contents = []
            for memory in similar_memories:
                contents.append(f"[{memory.timestamp.strftime('%H:%M')}] {memory.content}")
            
            combined_content = "\n".join(contents)
            
            prompt = f"""Merge these similar memory items into a single, comprehensive memory that preserves all important information while eliminating redundancy.

Memory items to merge:
{combined_content}

Requirements:
- Preserve all unique information
- Eliminate redundancy
- Maintain temporal context where relevant
- Keep the merged content concise but complete

Merged memory:"""
            
            # Rate limiting
            await openai_rate_limiter.wait_if_needed()
            
            response = await self.openai_client.chat.completions.create(
                model=self.summarization_model,
                messages=[
                    {"role": "system", "content": "You are an expert at merging and consolidating information while preserving key details."},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=1000,
                temperature=0.3
            )
            
            merged_content = response.choices[0].message.content.strip()
            
            # Calculate metrics
            original_tokens = sum(memory.token_count for memory in similar_memories)
            merged_tokens = calculate_token_count(merged_content)
            compression_ratio = original_tokens / merged_tokens if merged_tokens > 0 else 1.0
            
            # Create merged memory
            merged_memory = Memory(
                id=generate_id("merged"),
                session_id=similar_memories[0].session_id,
                memory_type=MemoryType.SUMMARY,  # Mark as summary type
                content=merged_content,
                relevance_score=max(m.relevance_score for m in similar_memories),
                compression_ratio=compression_ratio,
                token_count=merged_tokens,
                timestamp=datetime.utcnow(),
                metadata={
                    "merged_memory_ids": [m.id for m in similar_memories],
                    "merge_type": "similarity",
                    "original_tokens": original_tokens,
                    "compression_ratio": compression_ratio
                }
            )
            
            openai_circuit_breaker.record_success()
            return merged_memory
            
        except Exception as e:
            logger.error(f"Failed to merge memories: {e}")
            openai_circuit_breaker.record_failure()
            return None

"""
LongContext Agent - Main orchestration system.
Coordinates memory retrieval, context loading, tool usage, and OpenAI API calls for intelligent reasoning.
"""

import os
import sys
import logging
import asyncio
import time
from typing import List, Dict, Any, Optional, Tuple

from openai import AsyncOpenAI

# Add shared directory to path
sys.path.append(os.path.join(os.path.dirname(__file__), "..", "shared"))
from models import (
    ChatRequest, ChatResponse, BaseMessage, MessageRole, MemoryType,
    ToolCall, ToolType, ConversationSession
)

from memory_manager import MemoryManager
from retriever import HybridRetriever
from summarizer import ContextSummarizer
from utils import (
    generate_id, calculate_token_count, truncate_text,
    openai_rate_limiter, openai_circuit_breaker
)

logger = logging.getLogger(__name__)


class LongContextAgent:
    """Main agent that orchestrates all components for intelligent conversation"""
    
    def __init__(self, memory_manager: MemoryManager, retriever: HybridRetriever):
        self.memory_manager = memory_manager
        self.retriever = retriever
        self.summarizer = ContextSummarizer(memory_manager.db)
        
        # OpenAI client
        self.openai_client = AsyncOpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        self.model = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
        self.max_tokens = int(os.getenv("OPENAI_MAX_TOKENS", "2000"))
        self.temperature = float(os.getenv("OPENAI_TEMPERATURE", "0.7"))
        
        # Context management
        self.max_context_tokens = int(os.getenv("COMPRESSION_THRESHOLD", "8000"))
        self.system_prompt = self._build_system_prompt()
        
        # Tool management
        self.available_tools = {}
        self._register_built_in_tools()
    
    def _build_system_prompt(self) -> str:
        """Build the system prompt for the agent"""
        return """You are LongContext Agent, an advanced AI assistant with persistent memory capabilities.

Key features:
- You have access to conversation history and can remember past interactions
- You can use tools when needed to help answer questions or perform tasks
- You maintain context across long conversations through intelligent memory management
- You provide accurate, helpful, and contextual responses

Guidelines:
- Always consider the conversation context and history when responding
- Use tools when they would be helpful for answering questions or solving problems
- Be concise but comprehensive in your responses
- If you're unsure about something, say so rather than guessing
- Maintain a helpful and professional tone

Remember: Your responses are enhanced by your ability to retain and reference past conversation context."""
    
    def _register_built_in_tools(self):
        """Register built-in tools available to the agent"""
        # This will be expanded when we implement the tools framework
        # For now, placeholder for tool registration
        pass
    
    async def process_message(self, message: str, session_id: Optional[str] = None,
                            use_tools: bool = True, max_context_tokens: int = 4000) -> ChatResponse:
        """Process a user message and generate a response"""
        start_time = time.time()
        
        try:
            # Create or get session
            if not session_id:
                session = await self.memory_manager.create_session()
                session_id = session.id
                logger.info(f"Created new session: {session_id}")
            else:
                session = await self.memory_manager.get_session(session_id)
                if not session:
                    session = await self.memory_manager.create_session()
                    session_id = session.id
                    logger.warning(f"Session {session_id} not found, created new session")
            
            # Create user message
            user_message = BaseMessage(
                id=generate_id("msg"),
                role=MessageRole.USER,
                content=message,
                metadata={"session_id": session_id}
            )
            
            # Save user message
            await self.memory_manager.save_message(user_message, session_id)
            
            # Retrieve relevant context
            context_memories, context_string = await self.retriever.retrieve_context(
                query=message,
                session_id=session_id,
                max_tokens=max_context_tokens
            )
            
            logger.info(f"Retrieved {len(context_memories)} memories for context")
            
            # Check if tools should be used
            tool_calls = []
            if use_tools:
                tool_calls = await self._plan_and_execute_tools(message, context_string, session_id)
            
            # Generate response
            assistant_message = await self._generate_response(
                user_message=user_message,
                context=context_string,
                tool_calls=tool_calls,
                session_id=session_id
            )
            
            # Save assistant message
            await self.memory_manager.save_message(assistant_message, session_id)
            
            # Trigger compression if needed
            await self._trigger_adaptive_compression(session_id)
            
            # Calculate metrics
            response_time_ms = (time.time() - start_time) * 1000
            
            # Record performance metric
            await self.memory_manager.record_metric(
                "response_time_ms",
                response_time_ms,
                {"session_id": session_id, "message_tokens": calculate_token_count(message)}
            )
            
            # Build response
            response = ChatResponse(
                message=assistant_message,
                session_id=session_id,
                retrieved_memories=context_memories,
                tool_calls=tool_calls,
                metrics={
                    "response_time_ms": response_time_ms,
                    "context_tokens": sum(m.token_count for m in context_memories),
                    "tools_used": len(tool_calls),
                    "model_used": self.model
                }
            )
            
            logger.info(f"Processed message in {response_time_ms:.2f}ms")
            return response
            
        except Exception as e:
            logger.error(f"Failed to process message: {e}")
            
            # Create error response
            error_message = BaseMessage(
                id=generate_id("msg"),
                role=MessageRole.ASSISTANT,
                content="I apologize, but I encountered an error while processing your message. Please try again.",
                metadata={"error": str(e)}
            )
            
            return ChatResponse(
                message=error_message,
                session_id=session_id or "error",
                retrieved_memories=[],
                tool_calls=[],
                metrics={"error": True, "response_time_ms": (time.time() - start_time) * 1000}
            )
    
    async def _generate_response(self, user_message: BaseMessage, context: str,
                               tool_calls: List[ToolCall], session_id: str) -> BaseMessage:
        """Generate AI response using OpenAI API"""
        try:
            # Check circuit breaker
            if not openai_circuit_breaker.can_execute():
                logger.warning("OpenAI circuit breaker is open")
                return BaseMessage(
                    id=generate_id("msg"),
                    role=MessageRole.ASSISTANT,
                    content="I'm temporarily unable to process your request. Please try again in a moment.",
                    metadata={"circuit_breaker": "open"}
                )
            
            # Build conversation messages
            messages = [{"role": "system", "content": self.system_prompt}]
            
            # Add context if available
            if context:
                context_msg = f"Previous conversation context:\n{context}\n\nCurrent message:"
                messages.append({"role": "user", "content": context_msg})
            
            # Add current user message
            messages.append({"role": "user", "content": user_message.content})
            
            # Add tool results if any
            if tool_calls:
                tool_context = self._format_tool_results(tool_calls)
                messages.append({"role": "system", "content": f"Tool execution results:\n{tool_context}"})
            
            # Rate limiting
            await openai_rate_limiter.wait_if_needed()
            
            # Generate response
            response = await self.openai_client.chat.completions.create(
                model=self.model,
                messages=messages,
                max_tokens=self.max_tokens,
                temperature=self.temperature,
                stream=False
            )
            
            assistant_content = response.choices[0].message.content.strip()
            
            # Record success
            openai_circuit_breaker.record_success()
            
            # Create assistant message
            assistant_message = BaseMessage(
                id=generate_id("msg"),
                role=MessageRole.ASSISTANT,
                content=assistant_content,
                metadata={
                    "model": self.model,
                    "tokens_used": response.usage.total_tokens,
                    "session_id": session_id,
                    "context_length": len(context),
                    "tool_calls_count": len(tool_calls)
                }
            )
            
            return assistant_message
            
        except Exception as e:
            logger.error(f"Failed to generate response: {e}")
            openai_circuit_breaker.record_failure()
            
            return BaseMessage(
                id=generate_id("msg"),
                role=MessageRole.ASSISTANT,
                content="I apologize, but I'm having trouble generating a response right now. Please try rephrasing your question.",
                metadata={"error": str(e)}
            )
    
    def _format_tool_results(self, tool_calls: List[ToolCall]) -> str:
        """Format tool execution results for inclusion in context"""
        results = []
        for tool_call in tool_calls:
            result_text = f"Tool: {tool_call.tool_type.value}\n"
            result_text += f"Parameters: {tool_call.parameters}\n"
            result_text += f"Result: {tool_call.result}\n"
            if tool_call.execution_time_ms > 0:
                result_text += f"Execution time: {tool_call.execution_time_ms:.2f}ms"
            results.append(result_text)
        
        return "\n\n".join(results)
    
    async def _plan_and_execute_tools(self, message: str, context: str, session_id: str) -> List[ToolCall]:
        """Plan and execute tools based on the user message"""
        # This is a placeholder for tool planning and execution
        # In the full implementation, this would:
        # 1. Analyze the message to determine if tools are needed
        # 2. Select appropriate tools
        # 3. Execute tools with proper parameters
        # 4. Store tool results as memories
        
        tool_calls = []
        
        try:
            # Simple keyword-based tool detection for now
            message_lower = message.lower()
            
            # Calculator tool detection
            if any(word in message_lower for word in ["calculate", "compute", "math", "+", "-", "*", "/", "="]):
                tool_call = await self._execute_calculator_tool(message, session_id)
                if tool_call:
                    tool_calls.append(tool_call)
            
            # Web search tool detection (placeholder)
            if any(word in message_lower for word in ["search", "find", "look up", "what is", "who is"]):
                # Placeholder for web search tool
                pass
            
            return tool_calls
            
        except Exception as e:
            logger.error(f"Failed to plan and execute tools: {e}")
            return []
    
    async def _execute_calculator_tool(self, message: str, session_id: str) -> Optional[ToolCall]:
        """Execute calculator tool (simple math evaluation)"""
        try:
            # Extract mathematical expressions from the message
            # This is a simplified implementation
            import re
            
            # Look for mathematical expressions
            math_patterns = [
                r'(\d+(?:\.\d+)?\s*[+\-*/]\s*\d+(?:\.\d+)?)',
                r'(\d+\s*[+\-*/]\s*\d+)',
            ]
            
            expression = None
            for pattern in math_patterns:
                matches = re.findall(pattern, message)
                if matches:
                    expression = matches[0]
                    break
            
            if not expression:
                return None
            
            # Safely evaluate the expression
            try:
                # Only allow safe mathematical operations
                allowed_chars = set('0123456789+-*/.() ')
                if not all(c in allowed_chars for c in expression):
                    return None
                
                result = eval(expression)
                
                tool_call = ToolCall(
                    id=generate_id("tool"),
                    tool_type=ToolType.CALCULATOR,
                    parameters={"expression": expression},
                    result=str(result),
                    execution_time_ms=1.0  # Simple calculation
                )
                
                # Store tool result as memory
                await self.memory_manager.store_memory(
                    session_id=session_id,
                    content=f"Calculated: {expression} = {result}",
                    memory_type=MemoryType.TOOL_OUTPUT,
                    metadata={
                        "tool_type": "calculator",
                        "expression": expression,
                        "result": result
                    }
                )
                
                return tool_call
                
            except Exception:
                return None
                
        except Exception as e:
            logger.error(f"Calculator tool execution failed: {e}")
            return None
    
    async def _trigger_adaptive_compression(self, session_id: str):
        """Trigger adaptive compression if needed"""
        try:
            # Check if compression is needed
            stats = await self.summarizer._get_session_memory_stats(session_id)
            
            if stats.get("total_tokens", 0) > self.max_context_tokens:
                logger.info(f"Triggering adaptive compression for session {session_id}")
                
                # Run compression in background
                asyncio.create_task(self.summarizer.adaptive_compression(session_id))
                
        except Exception as e:
            logger.error(f"Failed to trigger adaptive compression: {e}")
    
    async def generate_session_title(self, session_id: str) -> str:
        """Generate a descriptive title for a conversation session"""
        try:
            # Get recent messages from the session
            session = await self.memory_manager.get_session(session_id)
            if not session or len(session.messages) < 2:
                return "New Conversation"
            
            # Get first few messages for title generation
            first_messages = session.messages[:5]
            conversation_start = "\n".join([
                f"{msg.role.value}: {msg.content[:100]}" 
                for msg in first_messages
            ])
            
            # Check circuit breaker
            if not openai_circuit_breaker.can_execute():
                return "Conversation"
            
            prompt = f"""Generate a short, descriptive title (3-6 words) for this conversation based on the opening messages:

{conversation_start}

The title should capture the main topic or theme. Respond with just the title, no quotes or extra text."""
            
            # Rate limiting
            await openai_rate_limiter.wait_if_needed()
            
            response = await self.openai_client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": "You are an expert at creating concise, descriptive conversation titles."},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=20,
                temperature=0.3
            )
            
            title = response.choices[0].message.content.strip().strip('"')
            
            # Validate and clean title
            if len(title) > 50:
                title = title[:50].rsplit(' ', 1)[0] + "..."
            
            # Update session title
            await self.memory_manager.update_session_title(session_id, title)
            
            openai_circuit_breaker.record_success()
            return title
            
        except Exception as e:
            logger.error(f"Failed to generate session title: {e}")
            openai_circuit_breaker.record_failure()
            return "Conversation"
    
    async def analyze_conversation_patterns(self, session_id: str) -> Dict[str, Any]:
        """Analyze conversation patterns and provide insights"""
        try:
            # Get session memories
            memories = await self.memory_manager.memory_manager.db.get_memories(
                session_id=session_id,
                limit=100
            )
            
            if not memories:
                return {"message": "Not enough conversation data for analysis"}
            
            # Basic statistics
            total_messages = len(memories)
            user_messages = sum(1 for m in memories if m.metadata.get("role") == "user")
            assistant_messages = total_messages - user_messages
            
            # Topic analysis (simplified)
            all_content = " ".join([m.content for m in memories])
            word_count = len(all_content.split())
            
            # Time span analysis
            if len(memories) > 1:
                time_span = memories[-1].timestamp - memories[0].timestamp
                conversation_duration_hours = time_span.total_seconds() / 3600
            else:
                conversation_duration_hours = 0
            
            # Compression analysis
            summaries = [m for m in memories if m.memory_type == MemoryType.SUMMARY]
            compression_events = len(summaries)
            
            analysis = {
                "total_messages": total_messages,
                "user_messages": user_messages,
                "assistant_messages": assistant_messages,
                "total_words": word_count,
                "conversation_duration_hours": round(conversation_duration_hours, 2),
                "compression_events": compression_events,
                "avg_message_length": word_count / total_messages if total_messages > 0 else 0,
                "session_health": "active" if conversation_duration_hours < 24 else "dormant"
            }
            
            return analysis
            
        except Exception as e:
            logger.error(f"Failed to analyze conversation patterns: {e}")
            return {"error": str(e)}
    
    async def suggest_follow_up_questions(self, session_id: str, last_message: str) -> List[str]:
        """Suggest relevant follow-up questions based on conversation context"""
        try:
            # Get recent context
            context_memories, context_string = await self.retriever.retrieve_context(
                query=last_message,
                session_id=session_id,
                max_tokens=2000
            )
            
            if not context_string:
                return []
            
            # Check circuit breaker
            if not openai_circuit_breaker.can_execute():
                return []
            
            prompt = f"""Based on this conversation context, suggest 3 relevant follow-up questions that the user might want to ask:

Recent conversation:
{context_string[-1000:]}  # Last 1000 chars

Last message: {last_message}

Generate 3 natural follow-up questions that would be helpful or interesting to explore further. Make them specific and relevant to the conversation topic."""
            
            # Rate limiting
            await openai_rate_limiter.wait_if_needed()
            
            response = await self.openai_client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": "You are an expert at understanding conversation flow and suggesting relevant follow-up questions."},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=200,
                temperature=0.7
            )
            
            suggestions_text = response.choices[0].message.content.strip()
            
            # Parse suggestions (assume they're numbered or bulleted)
            import re
            questions = re.findall(r'[1-3][.)]\s*(.+?)(?=\n[1-3][.)]|\n\n|\Z)', suggestions_text, re.DOTALL)
            
            if not questions:
                # Try splitting by lines
                lines = [line.strip() for line in suggestions_text.split('\n') if line.strip()]
                questions = [line for line in lines if '?' in line][:3]
            
            # Clean up questions
            clean_questions = []
            for q in questions:
                q = q.strip().strip('1234567890.-) ')
                if q and '?' in q:
                    clean_questions.append(q)
            
            openai_circuit_breaker.record_success()
            return clean_questions[:3]
            
        except Exception as e:
            logger.error(f"Failed to suggest follow-up questions: {e}")
            openai_circuit_breaker.record_failure()
            return []
    
    async def export_conversation(self, session_id: str, format: str = "text") -> str:
        """Export conversation in various formats"""
        try:
            session = await self.memory_manager.get_session(session_id)
            if not session:
                raise ValueError(f"Session {session_id} not found")
            
            messages = session.messages
            if not messages:
                return "No messages in this conversation."
            
            if format.lower() == "text":
                lines = []
                lines.append(f"Conversation: {session.title}")
                lines.append(f"Created: {session.created_at}")
                lines.append(f"Messages: {len(messages)}")
                lines.append("-" * 50)
                
                for msg in messages:
                    timestamp = msg.timestamp.strftime("%Y-%m-%d %H:%M:%S")
                    lines.append(f"[{timestamp}] {msg.role.value.upper()}: {msg.content}")
                
                return "\n".join(lines)
            
            elif format.lower() == "json":
                import json
                export_data = {
                    "session_id": session_id,
                    "title": session.title,
                    "created_at": session.created_at.isoformat(),
                    "updated_at": session.updated_at.isoformat(),
                    "messages": [
                        {
                            "id": msg.id,
                            "role": msg.role.value,
                            "content": msg.content,
                            "timestamp": msg.timestamp.isoformat(),
                            "metadata": msg.metadata
                        }
                        for msg in messages
                    ]
                }
                return json.dumps(export_data, indent=2)
            
            else:
                raise ValueError(f"Unsupported export format: {format}")
                
        except Exception as e:
            logger.error(f"Failed to export conversation: {e}")
            raise

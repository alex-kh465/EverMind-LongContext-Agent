"""
Shared data models and schemas for LongContext Agent.
These models are used across frontend and backend for consistent data structures.
"""

from datetime import datetime
from typing import List, Optional, Dict, Any, Union
from enum import Enum
from pydantic import BaseModel, Field


class MessageRole(str, Enum):
    """Message roles in conversation"""
    USER = "user"
    ASSISTANT = "assistant"
    SYSTEM = "system"
    TOOL = "tool"


class MemoryType(str, Enum):
    """Types of memory stored in the system"""
    CONVERSATION = "conversation"
    SUMMARY = "summary"
    TOOL_OUTPUT = "tool_output"
    CONTEXT = "context"


class ToolType(str, Enum):
    """Available tool types"""
    CALCULATOR = "calculator"
    WEB_SEARCH = "web_search"
    WIKIPEDIA = "wikipedia"


# Base Models
class BaseMessage(BaseModel):
    """Base message model"""
    id: str = Field(..., description="Unique message identifier")
    role: MessageRole = Field(..., description="Message role")
    content: str = Field(..., description="Message content")
    timestamp: datetime = Field(default_factory=datetime.utcnow, description="Message timestamp")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional metadata")


class Memory(BaseModel):
    """Memory storage model"""
    id: str = Field(..., description="Unique memory identifier")
    session_id: str = Field(..., description="Session identifier")
    memory_type: MemoryType = Field(..., description="Type of memory")
    content: str = Field(..., description="Memory content")
    embedding: Optional[List[float]] = Field(None, description="Vector embedding")
    relevance_score: float = Field(default=0.0, description="Relevance score")
    compression_ratio: float = Field(default=1.0, description="Compression ratio")
    token_count: int = Field(default=0, description="Token count")
    timestamp: datetime = Field(default_factory=datetime.utcnow, description="Creation timestamp")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional metadata")


class ToolCall(BaseModel):
    """Tool call model"""
    id: str = Field(..., description="Tool call identifier")
    tool_type: ToolType = Field(..., description="Type of tool")
    parameters: Dict[str, Any] = Field(..., description="Tool parameters")
    result: Optional[Any] = Field(None, description="Tool execution result")
    timestamp: datetime = Field(default_factory=datetime.utcnow, description="Execution timestamp")
    execution_time_ms: float = Field(default=0.0, description="Execution time in milliseconds")


class ConversationSession(BaseModel):
    """Conversation session model"""
    id: str = Field(..., description="Session identifier")
    title: str = Field(default="New Conversation", description="Session title")
    messages: List[BaseMessage] = Field(default_factory=list, description="Session messages")
    created_at: datetime = Field(default_factory=datetime.utcnow, description="Creation timestamp")
    updated_at: datetime = Field(default_factory=datetime.utcnow, description="Last update timestamp")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Session metadata")


# API Request/Response Models
class ChatRequest(BaseModel):
    """Chat API request model"""
    message: str = Field(..., description="User message")
    session_id: Optional[str] = Field(None, description="Session ID (creates new if None)")
    use_tools: bool = Field(default=True, description="Enable tool usage")
    max_context_tokens: int = Field(default=4000, description="Maximum context tokens")


class ChatResponse(BaseModel):
    """Chat API response model"""
    message: BaseMessage = Field(..., description="Assistant response")
    session_id: str = Field(..., description="Session identifier")
    retrieved_memories: List[Memory] = Field(default_factory=list, description="Retrieved memories")
    tool_calls: List[ToolCall] = Field(default_factory=list, description="Tool calls made")
    metrics: Dict[str, Any] = Field(default_factory=dict, description="Performance metrics")


class MemoryQuery(BaseModel):
    """Memory query model"""
    query: str = Field(..., description="Search query")
    session_id: Optional[str] = Field(None, description="Session filter")
    memory_types: List[MemoryType] = Field(default_factory=list, description="Memory type filters")
    limit: int = Field(default=10, description="Result limit")
    relevance_threshold: float = Field(default=0.7, description="Minimum relevance score")


class MemoryQueryResponse(BaseModel):
    """Memory query response model"""
    memories: List[Memory] = Field(..., description="Retrieved memories")
    total_count: int = Field(..., description="Total matching memories")
    query_time_ms: float = Field(..., description="Query execution time")


# Metrics Models
class PerformanceMetrics(BaseModel):
    """Performance metrics model"""
    context_retention_accuracy: float = Field(default=0.0, description="CRA metric")
    compression_ratio: float = Field(default=0.0, description="CR metric")
    retrieval_precision: float = Field(default=0.0, description="RP metric")
    response_latency_ms: float = Field(default=0.0, description="Response latency")
    memory_growth_rate: float = Field(default=0.0, description="Memory growth efficiency")
    total_memories: int = Field(default=0, description="Total stored memories")
    active_sessions: int = Field(default=0, description="Active sessions count")
    vector_db_size_mb: float = Field(default=0.0, description="Vector database storage size in MB")


class SystemHealth(BaseModel):
    """System health model"""
    status: str = Field(..., description="System status")
    database_connected: bool = Field(..., description="Database connection status")
    openai_api_available: bool = Field(..., description="OpenAI API availability")
    memory_usage_mb: float = Field(..., description="Memory usage in MB")
    cpu_usage_percent: float = Field(..., description="CPU usage percentage")
    uptime_seconds: float = Field(..., description="System uptime")


# Configuration Models
class AgentConfig(BaseModel):
    """Agent configuration model"""
    openai_model: str = Field(default="gpt-4o-mini", description="OpenAI model name")
    max_tokens: int = Field(default=2000, description="Maximum response tokens")
    temperature: float = Field(default=0.7, description="Response temperature")
    summarization_model: str = Field(default="gpt-4o-mini", description="Summarization model")
    compression_threshold: int = Field(default=8000, description="Token threshold for compression")
    retrieval_limit: int = Field(default=10, description="Maximum memories to retrieve")
    relevance_threshold: float = Field(default=0.7, description="Minimum relevance for retrieval")


class DatabaseConfig(BaseModel):
    """Database configuration model"""
    sqlite_path: str = Field(default="./memory.db", description="SQLite database path")
    vector_dimension: int = Field(default=1536, description="Vector embedding dimension")
    index_type: str = Field(default="cosine", description="Vector index type")
    batch_size: int = Field(default=100, description="Batch processing size")

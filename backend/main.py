"""
Main FastAPI application for LongContext Agent.
Provides RESTful API endpoints for chat, memory management, and agent orchestration.
"""

import os
import sys
import time
import logging
from contextlib import asynccontextmanager
from typing import Dict, Any

from fastapi import FastAPI, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from dotenv import load_dotenv

# Add shared directory to path
sys.path.append(os.path.join(os.path.dirname(__file__), "..", "shared"))

from models import (
    ChatRequest, ChatResponse, MemoryQuery, MemoryQueryResponse,
    PerformanceMetrics, SystemHealth, AgentConfig, DatabaseConfig
)

# Import backend modules
from database import DatabaseManager, get_db_manager
from memory_manager import MemoryManager
from agent import LongContextAgent
from retriever import HybridRetriever
from utils import setup_logging, health_check
from title_generator import should_update_title, generate_conversation_title

# Load environment variables
load_dotenv()

# Setup logging
setup_logging()
logger = logging.getLogger(__name__)

# Global variables
db_manager: DatabaseManager = None
memory_manager: MemoryManager = None
agent: LongContextAgent = None
app_start_time: float = time.time()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager"""
    global db_manager, memory_manager, agent
    
    logger.info("Starting LongContext Agent backend...")
    
    try:
        # Initialize database
        db_manager = DatabaseManager()
        await db_manager.initialize()
        
        # Initialize memory manager
        memory_manager = MemoryManager(db_manager)
        
        # Initialize agent
        retriever = HybridRetriever(db_manager)
        agent = LongContextAgent(memory_manager, retriever)
        
        logger.info("Backend initialized successfully")
        
        yield
        
    except Exception as e:
        logger.error(f"Failed to initialize backend: {e}")
        raise
    finally:
        # Cleanup
        if db_manager:
            await db_manager.close()
        logger.info("Backend shutdown complete")


# Create FastAPI app
app = FastAPI(
    title="LongContext Agent API",
    description="Production-grade agentic framework with resilient multi-turn memory system",
    version="1.0.0",
    lifespan=lifespan
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:5173", "https://*.vercel.app"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Dependency injection
async def get_agent() -> LongContextAgent:
    """Get the global agent instance"""
    if agent is None:
        raise HTTPException(status_code=503, detail="Agent not initialized")
    return agent


async def get_memory_manager() -> MemoryManager:
    """Get the global memory manager instance"""
    if memory_manager is None:
        raise HTTPException(status_code=503, detail="Memory manager not initialized")
    return memory_manager


async def _maybe_update_session_title(session_id: str, memory_mgr: MemoryManager):
    """Check if session title should be updated and generate new title if needed"""
    try:
        session = await memory_mgr.get_session(session_id)
        if not session or not session.messages:
            return
        
        message_count = len(session.messages)
        current_title = session.title
        
        # Check if we should generate a title
        if should_update_title(current_title, message_count):
            logger.info(f"Generating title for session {session_id} with {message_count} messages")
            
            # Generate new title based on conversation
            new_title = await generate_conversation_title(session.messages)
            
            # Update the session title
            success = await memory_mgr.update_session_title(session_id, new_title)
            if success:
                logger.info(f"Updated session {session_id} title to: '{new_title}'")
            else:
                logger.warning(f"Failed to update session {session_id} title")
                
    except Exception as e:
        logger.error(f"Error in title generation for session {session_id}: {e}")


# API Endpoints
@app.get("/")
async def root():
    """Root endpoint with API information"""
    return {
        "name": "LongContext Agent API",
        "version": "1.0.0",
        "status": "running",
        "uptime_seconds": time.time() - app_start_time,
        "endpoints": {
            "chat": "/chat",
            "memory": "/memory",
            "health": "/health",
            "metrics": "/metrics"
        }
    }


@app.post("/chat", response_model=ChatResponse)
async def chat(
    request: ChatRequest,
    agent_instance: LongContextAgent = Depends(get_agent)
):
    """Chat endpoint for conversation with the agent"""
    start_time = time.time()
    
    try:
        logger.info(f"Processing chat request: session_id={request.session_id}")
        
        # Process the chat request
        response = await agent_instance.process_message(
            message=request.message,
            session_id=request.session_id,
            use_tools=request.use_tools,
            max_context_tokens=request.max_context_tokens
        )
        
        # Add performance metrics
        response.metrics["response_time_ms"] = (time.time() - start_time) * 1000
        
        logger.info(f"Chat response generated in {response.metrics['response_time_ms']:.2f}ms")
        
        # Auto-generate title if needed  
        await _maybe_update_session_title(response.session_id, memory_manager)
        
        return response
        
    except Exception as e:
        logger.error(f"Error processing chat request: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/memory/search", response_model=MemoryQueryResponse)
async def search_memory(
    query: MemoryQuery,
    memory_mgr: MemoryManager = Depends(get_memory_manager)
):
    """Search memory store"""
    start_time = time.time()
    
    try:
        logger.info(f"Processing memory search: query='{query.query[:50]}...'")
        
        # Search memories
        memories = await memory_mgr.search_memories(
            query=query.query,
            session_id=query.session_id,
            memory_types=query.memory_types,
            limit=query.limit,
            relevance_threshold=query.relevance_threshold
        )
        
        query_time = (time.time() - start_time) * 1000
        
        response = MemoryQueryResponse(
            memories=memories,
            total_count=len(memories),
            query_time_ms=query_time
        )
        
        logger.info(f"Memory search completed in {query_time:.2f}ms, found {len(memories)} results")
        
        return response
        
    except Exception as e:
        logger.error(f"Error searching memory: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/memory/sessions")
async def list_sessions(
    memory_mgr: MemoryManager = Depends(get_memory_manager)
):
    """List all conversation sessions"""
    try:
        sessions = await memory_mgr.list_sessions()
        return {"sessions": sessions}
    except Exception as e:
        logger.error(f"Error listing sessions: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/memory/sessions")
async def create_session(
    request: Dict[str, Any],
    memory_mgr: MemoryManager = Depends(get_memory_manager)
):
    """Create a new conversation session"""
    try:
        title = request.get("title", "New Conversation")
        session = await memory_mgr.create_session(title)
        logger.info(f"Created new session: {session.id}")
        return session
    except Exception as e:
        logger.error(f"Error creating session: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/memory/sessions/{session_id}")
async def get_session(
    session_id: str,
    memory_mgr: MemoryManager = Depends(get_memory_manager)
):
    """Get a specific conversation session"""
    try:
        session = await memory_mgr.get_session(session_id)
        if not session:
            raise HTTPException(status_code=404, detail="Session not found")
        return session
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting session: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.patch("/memory/sessions/{session_id}")
async def update_session(
    session_id: str,
    request: Dict[str, Any],
    memory_mgr: MemoryManager = Depends(get_memory_manager)
):
    """Update a conversation session (mainly for title updates)"""
    try:
        success = await memory_mgr.update_session_title(session_id, request.get("title", ""))
        if not success:
            raise HTTPException(status_code=404, detail="Session not found")
        
        # Return updated session
        session = await memory_mgr.get_session(session_id)
        return session
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating session: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.delete("/memory/sessions/{session_id}")
async def delete_session(
    session_id: str,
    memory_mgr: MemoryManager = Depends(get_memory_manager)
):
    """Delete a conversation session and its memories"""
    try:
        success = await memory_mgr.delete_session(session_id)
        if success:
            return {"message": f"Session {session_id} deleted successfully"}
        else:
            raise HTTPException(status_code=404, detail="Session not found")
    except Exception as e:
        logger.error(f"Error deleting session: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/health", response_model=SystemHealth)
async def health():
    """System health check"""
    try:
        health_data = await health_check(db_manager)
        return health_data
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        return SystemHealth(
            status="unhealthy",
            database_connected=False,
            openai_api_available=False,
            memory_usage_mb=0.0,
            cpu_usage_percent=0.0,
            uptime_seconds=time.time() - app_start_time
        )


@app.get("/metrics", response_model=PerformanceMetrics)
async def get_metrics(
    memory_mgr: MemoryManager = Depends(get_memory_manager)
):
    """Get performance metrics"""
    try:
        metrics = await memory_mgr.get_performance_metrics()
        return metrics
    except Exception as e:
        logger.error(f"Error getting metrics: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/config")
async def get_config():
    """Get current agent configuration"""
    try:
        config = AgentConfig()
        db_config = DatabaseConfig()
        
        return {
            "agent": config.dict(),
            "database": db_config.dict()
        }
    except Exception as e:
        logger.error(f"Error getting config: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# Exception handlers
@app.exception_handler(Exception)
async def general_exception_handler(request, exc):
    """Handle unexpected exceptions"""
    logger.error(f"Unexpected error: {exc}")
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal server error"}
    )


if __name__ == "__main__":
    import uvicorn
    
    port = int(os.getenv("PORT", 8000))
    host = os.getenv("HOST", "0.0.0.0")
    
    uvicorn.run(
        "main:app",
        host=host,
        port=port,
        reload=True,
        log_level="info"
    )

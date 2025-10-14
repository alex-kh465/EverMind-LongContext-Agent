"""
Utility functions for LongContext Agent backend.
Includes logging setup, health checks, and common helper functions.
"""

import os
import sys
import time
import psutil
import logging
import asyncio
from typing import Dict, Any, Optional
from datetime import datetime

import httpx
from openai import AsyncOpenAI

# Add shared directory to path
sys.path.append(os.path.join(os.path.dirname(__file__), "..", "shared"))
from models import SystemHealth


def setup_logging(level: str = "INFO"):
    """Setup structured logging for the application"""
    
    # Configure logging format
    log_format = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    
    # Setup root logger
    logging.basicConfig(
        level=getattr(logging, level.upper()),
        format=log_format,
        handlers=[
            logging.StreamHandler(sys.stdout),
            logging.FileHandler("longcontext_agent.log")
        ]
    )
    
    # Configure specific loggers
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("chromadb").setLevel(logging.WARNING)
    logging.getLogger("openai").setLevel(logging.INFO)


async def health_check(db_manager=None) -> SystemHealth:
    """Perform comprehensive system health check"""
    
    # Check database connection
    database_connected = False
    if db_manager:
        try:
            await db_manager.health_check()
            database_connected = True
        except Exception as e:
            logging.error(f"Database health check failed: {e}")
    
    # Check OpenAI API availability
    openai_api_available = await check_openai_api()
    
    # Get system metrics
    process = psutil.Process()
    memory_usage_mb = process.memory_info().rss / 1024 / 1024
    cpu_usage_percent = process.cpu_percent()
    
    # Determine overall status
    status = "healthy" if database_connected and openai_api_available else "degraded"
    
    return SystemHealth(
        status=status,
        database_connected=database_connected,
        openai_api_available=openai_api_available,
        memory_usage_mb=memory_usage_mb,
        cpu_usage_percent=cpu_usage_percent,
        uptime_seconds=time.time() - psutil.boot_time()
    )


async def check_openai_api() -> bool:
    """Check if OpenAI API is available and accessible"""
    try:
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            return False
        
        client = AsyncOpenAI(api_key=api_key)
        
        # Try a simple API call with minimal cost
        response = await client.models.list()
        return len(response.data) > 0
        
    except Exception as e:
        logging.error(f"OpenAI API check failed: {e}")
        return False


def generate_id(prefix: str = "") -> str:
    """Generate a unique ID with optional prefix"""
    import uuid
    timestamp = int(time.time() * 1000)
    unique_id = str(uuid.uuid4()).replace("-", "")[:8]
    
    if prefix:
        return f"{prefix}_{timestamp}_{unique_id}"
    return f"{timestamp}_{unique_id}"


def calculate_token_count(text: str, model: str = "gpt-4o-mini") -> int:
    """Calculate approximate token count for given text"""
    try:
        import tiktoken
        
        # Get encoding for the model
        try:
            encoding = tiktoken.encoding_for_model(model)
        except KeyError:
            # Fallback to a common encoding
            encoding = tiktoken.get_encoding("cl100k_base")
        
        return len(encoding.encode(text))
        
    except ImportError:
        # Fallback: rough approximation (4 chars per token)
        return len(text) // 4


def truncate_text(text: str, max_tokens: int, model: str = "gpt-4o-mini") -> str:
    """Truncate text to fit within token limit"""
    current_tokens = calculate_token_count(text, model)
    
    if current_tokens <= max_tokens:
        return text
    
    # Calculate approximate character limit
    chars_per_token = len(text) / current_tokens
    max_chars = int(max_tokens * chars_per_token * 0.9)  # 90% safety margin
    
    if max_chars >= len(text):
        return text
    
    # Truncate at word boundary
    truncated = text[:max_chars]
    last_space = truncated.rfind(' ')
    
    if last_space > max_chars * 0.8:  # If we're close to the limit
        return truncated[:last_space] + "..."
    
    return truncated + "..."


async def batch_process(items: list, batch_size: int, process_func, *args, **kwargs):
    """Process items in batches asynchronously"""
    results = []
    
    for i in range(0, len(items), batch_size):
        batch = items[i:i + batch_size]
        
        # Process batch
        batch_tasks = []
        for item in batch:
            task = process_func(item, *args, **kwargs)
            batch_tasks.append(task)
        
        # Wait for batch completion
        batch_results = await asyncio.gather(*batch_tasks, return_exceptions=True)
        results.extend(batch_results)
    
    return results


def format_timestamp(timestamp: datetime) -> str:
    """Format timestamp for display"""
    if timestamp.date() == datetime.utcnow().date():
        return timestamp.strftime("%H:%M:%S")
    elif (datetime.utcnow() - timestamp).days < 7:
        return timestamp.strftime("%a %H:%M")
    else:
        return timestamp.strftime("%m/%d %H:%M")


def safe_json_loads(json_str: str, default=None):
    """Safely load JSON string with fallback"""
    try:
        import json
        return json.loads(json_str)
    except (json.JSONDecodeError, TypeError):
        return default or {}


def safe_json_dumps(obj: Any, default=None) -> str:
    """Safely dump object to JSON string with fallback"""
    try:
        import json
        return json.dumps(obj, default=str)
    except (TypeError, ValueError):
        return json.dumps(default or {})


class RateLimiter:
    """Simple rate limiter for API calls"""
    
    def __init__(self, max_calls: int, time_window: int):
        self.max_calls = max_calls
        self.time_window = time_window
        self.calls = []
    
    async def wait_if_needed(self):
        """Wait if rate limit would be exceeded"""
        now = time.time()
        
        # Remove old calls outside the time window
        self.calls = [call_time for call_time in self.calls if now - call_time < self.time_window]
        
        # Check if we're at the limit
        if len(self.calls) >= self.max_calls:
            sleep_time = self.time_window - (now - self.calls[0]) + 0.1
            if sleep_time > 0:
                await asyncio.sleep(sleep_time)
        
        # Record this call
        self.calls.append(now)


class CircuitBreaker:
    """Circuit breaker pattern for external service calls"""
    
    def __init__(self, failure_threshold: int = 5, recovery_timeout: int = 60):
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.failure_count = 0
        self.last_failure_time = None
        self.state = "CLOSED"  # CLOSED, OPEN, HALF_OPEN
    
    def can_execute(self) -> bool:
        """Check if operation can be executed"""
        if self.state == "CLOSED":
            return True
        
        if self.state == "OPEN":
            if time.time() - self.last_failure_time > self.recovery_timeout:
                self.state = "HALF_OPEN"
                return True
            return False
        
        if self.state == "HALF_OPEN":
            return True
        
        return False
    
    def record_success(self):
        """Record successful operation"""
        self.failure_count = 0
        self.state = "CLOSED"
    
    def record_failure(self):
        """Record failed operation"""
        self.failure_count += 1
        self.last_failure_time = time.time()
        
        if self.failure_count >= self.failure_threshold:
            self.state = "OPEN"


# Global instances
openai_rate_limiter = RateLimiter(max_calls=50, time_window=60)  # 50 calls per minute
openai_circuit_breaker = CircuitBreaker(failure_threshold=3, recovery_timeout=30)

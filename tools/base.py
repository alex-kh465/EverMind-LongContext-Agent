"""
Base tool interfaces and tool manager for LongContext Agent.
Provides extensible framework for integrating various tools and capabilities.
"""

import os
import sys
import json
import logging
import asyncio
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, List, Union
from datetime import datetime

# Add shared directory to path
sys.path.append(os.path.join(os.path.dirname(__file__), "..", "shared"))
from models import ToolCall, ToolType

logger = logging.getLogger(__name__)


class BaseTool(ABC):
    """Abstract base class for all tools"""
    
    def __init__(self, name: str, description: str, tool_type: ToolType):
        self.name = name
        self.description = description
        self.tool_type = tool_type
        self.enabled = True
    
    @abstractmethod
    async def execute(self, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """Execute the tool with given parameters"""
        pass
    
    @abstractmethod
    def validate_parameters(self, parameters: Dict[str, Any]) -> bool:
        """Validate tool parameters before execution"""
        pass
    
    def get_schema(self) -> Dict[str, Any]:
        """Return JSON schema for tool parameters"""
        return {
            "name": self.name,
            "description": self.description,
            "type": self.tool_type.value,
            "parameters": self._get_parameter_schema()
        }
    
    @abstractmethod
    def _get_parameter_schema(self) -> Dict[str, Any]:
        """Return parameter schema specific to this tool"""
        pass
    
    def is_enabled(self) -> bool:
        """Check if tool is enabled"""
        return self.enabled
    
    def enable(self):
        """Enable the tool"""
        self.enabled = True
    
    def disable(self):
        """Disable the tool"""
        self.enabled = False


class ToolExecutionResult:
    """Result of tool execution"""
    
    def __init__(self, success: bool, result: Any = None, error: str = None, 
                 execution_time_ms: float = 0.0, metadata: Dict[str, Any] = None):
        self.success = success
        self.result = result
        self.error = error
        self.execution_time_ms = execution_time_ms
        self.metadata = metadata or {}
        self.timestamp = datetime.utcnow()
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            "success": self.success,
            "result": self.result,
            "error": self.error,
            "execution_time_ms": self.execution_time_ms,
            "metadata": self.metadata,
            "timestamp": self.timestamp.isoformat()
        }


class ToolManager:
    """Manages registration and execution of tools"""
    
    def __init__(self):
        self.tools: Dict[str, BaseTool] = {}
        self.execution_history: List[ToolExecutionResult] = []
        self.max_history_size = 1000
    
    def register_tool(self, tool: BaseTool):
        """Register a new tool"""
        if tool.name in self.tools:
            logger.warning(f"Tool {tool.name} is already registered, overwriting")
        
        self.tools[tool.name] = tool
        logger.info(f"Registered tool: {tool.name} ({tool.tool_type.value})")
    
    def unregister_tool(self, tool_name: str):
        """Unregister a tool"""
        if tool_name in self.tools:
            del self.tools[tool_name]
            logger.info(f"Unregistered tool: {tool_name}")
        else:
            logger.warning(f"Tool {tool_name} not found for unregistration")
    
    def get_tool(self, tool_name: str) -> Optional[BaseTool]:
        """Get a tool by name"""
        return self.tools.get(tool_name)
    
    def list_tools(self, enabled_only: bool = True) -> List[Dict[str, Any]]:
        """List all registered tools"""
        tools_list = []
        
        for tool in self.tools.values():
            if enabled_only and not tool.is_enabled():
                continue
            
            tools_list.append(tool.get_schema())
        
        return tools_list
    
    async def execute_tool(self, tool_name: str, parameters: Dict[str, Any]) -> ToolExecutionResult:
        """Execute a tool with given parameters"""
        start_time = asyncio.get_event_loop().time()
        
        try:
            # Get tool
            tool = self.get_tool(tool_name)
            if not tool:
                return ToolExecutionResult(
                    success=False,
                    error=f"Tool {tool_name} not found"
                )
            
            # Check if tool is enabled
            if not tool.is_enabled():
                return ToolExecutionResult(
                    success=False,
                    error=f"Tool {tool_name} is disabled"
                )
            
            # Validate parameters
            if not tool.validate_parameters(parameters):
                return ToolExecutionResult(
                    success=False,
                    error=f"Invalid parameters for tool {tool_name}",
                    metadata={"parameters": parameters}
                )
            
            # Execute tool
            result = await tool.execute(parameters)
            execution_time_ms = (asyncio.get_event_loop().time() - start_time) * 1000
            
            execution_result = ToolExecutionResult(
                success=True,
                result=result,
                execution_time_ms=execution_time_ms,
                metadata={"tool_name": tool_name, "parameters": parameters}
            )
            
            # Add to history
            self._add_to_history(execution_result)
            
            logger.info(f"Successfully executed tool {tool_name} in {execution_time_ms:.2f}ms")
            return execution_result
            
        except Exception as e:
            execution_time_ms = (asyncio.get_event_loop().time() - start_time) * 1000
            
            execution_result = ToolExecutionResult(
                success=False,
                error=str(e),
                execution_time_ms=execution_time_ms,
                metadata={"tool_name": tool_name, "parameters": parameters}
            )
            
            self._add_to_history(execution_result)
            
            logger.error(f"Tool execution failed: {tool_name} - {e}")
            return execution_result
    
    def _add_to_history(self, result: ToolExecutionResult):
        """Add execution result to history"""
        self.execution_history.append(result)
        
        # Trim history if too large
        if len(self.execution_history) > self.max_history_size:
            self.execution_history = self.execution_history[-self.max_history_size:]
    
    def get_execution_history(self, limit: int = 50) -> List[Dict[str, Any]]:
        """Get recent execution history"""
        recent_history = self.execution_history[-limit:]
        return [result.to_dict() for result in recent_history]
    
    def get_tool_statistics(self) -> Dict[str, Any]:
        """Get tool usage statistics"""
        stats = {
            "total_tools": len(self.tools),
            "enabled_tools": sum(1 for tool in self.tools.values() if tool.is_enabled()),
            "total_executions": len(self.execution_history),
            "successful_executions": sum(1 for result in self.execution_history if result.success),
            "tool_usage": {},
            "average_execution_time_ms": 0.0
        }
        
        # Tool usage count
        for result in self.execution_history:
            tool_name = result.metadata.get("tool_name", "unknown")
            if tool_name not in stats["tool_usage"]:
                stats["tool_usage"][tool_name] = {"count": 0, "success_count": 0}
            
            stats["tool_usage"][tool_name]["count"] += 1
            if result.success:
                stats["tool_usage"][tool_name]["success_count"] += 1
        
        # Average execution time
        if self.execution_history:
            total_time = sum(result.execution_time_ms for result in self.execution_history)
            stats["average_execution_time_ms"] = total_time / len(self.execution_history)
        
        return stats
    
    async def plan_tool_usage(self, query: str, available_context: str = "") -> List[Dict[str, Any]]:
        """Plan which tools to use based on query analysis"""
        # This is a simplified implementation
        # In a production system, this could use ML/LLM to determine optimal tool usage
        
        planned_tools = []
        query_lower = query.lower()
        
        # Simple keyword-based planning
        for tool_name, tool in self.tools.items():
            if not tool.is_enabled():
                continue
            
            # Basic tool selection logic
            if tool.tool_type == ToolType.CALCULATOR:
                if any(keyword in query_lower for keyword in 
                      ["calculate", "compute", "math", "+", "-", "*", "/", "="]):
                    planned_tools.append({
                        "tool_name": tool_name,
                        "confidence": 0.8,
                        "reason": "Mathematical expressions detected"
                    })
            
            elif tool.tool_type == ToolType.WEB_SEARCH:
                if any(keyword in query_lower for keyword in 
                      ["search", "find", "look up", "what is", "who is", "when did"]):
                    planned_tools.append({
                        "tool_name": tool_name,
                        "confidence": 0.7,
                        "reason": "Information lookup request detected"
                    })
        
        # Sort by confidence
        planned_tools.sort(key=lambda x: x["confidence"], reverse=True)
        return planned_tools
    
    def create_tool_call(self, tool_name: str, parameters: Dict[str, Any], 
                        execution_result: ToolExecutionResult) -> ToolCall:
        """Create a ToolCall object from execution result"""
        tool = self.get_tool(tool_name)
        if not tool:
            raise ValueError(f"Tool {tool_name} not found")
        
        return ToolCall(
            id=f"tool_{int(datetime.utcnow().timestamp() * 1000)}",
            tool_type=tool.tool_type,
            parameters=parameters,
            result=execution_result.result if execution_result.success else execution_result.error,
            execution_time_ms=execution_result.execution_time_ms,
            timestamp=execution_result.timestamp
        )


# Global tool manager instance
_tool_manager_instance: Optional[ToolManager] = None

def get_tool_manager() -> ToolManager:
    """Get the global tool manager instance"""
    global _tool_manager_instance
    if _tool_manager_instance is None:
        _tool_manager_instance = ToolManager()
    return _tool_manager_instance

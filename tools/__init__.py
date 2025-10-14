"""
Tools package for LongContext Agent.
Provides extensible tool integration framework with built-in calculator, web search, and Wikipedia tools.
"""

from .base import BaseTool, ToolManager, ToolExecutionResult, get_tool_manager
from .calculator import CalculatorTool, StatisticsCalculator, register_calculator_tools
from .web_search import WebSearchTool, WikipediaTool, register_search_tools

__all__ = [
    # Base classes
    'BaseTool',
    'ToolManager', 
    'ToolExecutionResult',
    'get_tool_manager',
    
    # Calculator tools
    'CalculatorTool',
    'StatisticsCalculator',
    'register_calculator_tools',
    
    # Search tools
    'WebSearchTool',
    'WikipediaTool', 
    'register_search_tools',
    
    # Convenience functions
    'initialize_all_tools',
    'get_available_tools'
]


def initialize_all_tools():
    """Initialize and register all available tools"""
    tool_manager = get_tool_manager()
    
    # Register calculator tools
    register_calculator_tools()
    
    # Register search tools
    register_search_tools()
    
    return tool_manager


def get_available_tools():
    """Get list of all available tools with their schemas"""
    tool_manager = get_tool_manager()
    return tool_manager.list_tools()


# Auto-initialize tools when module is imported
_tool_manager = initialize_all_tools()

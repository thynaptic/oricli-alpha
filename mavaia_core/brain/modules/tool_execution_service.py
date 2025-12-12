"""
Tool Execution Service - Service for executing tools and formatting results
Mirrors Swift ToolExecutionService.swift functionality
"""

from typing import List, Optional
import time
from tool_calling_models import ToolCall, ToolResult
from tool_registry import tool_registry


class ToolExecutionService:
    """Service for executing tools and formatting results"""
    
    _instance: Optional["ToolExecutionService"] = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        if self._initialized:
            return
        self._initialized = True
    
    # MARK: - Tool Execution
    
    async def execute_tool(self, name: str, arguments: dict) -> ToolResult:
        """Execute a single tool"""
        start_time = time.time()
        
        try:
            result = await tool_registry.execute_tool(name, arguments)
            duration = time.time() - start_time
            return result
        except Exception as e:
            duration = time.time() - start_time
            raise
    
    async def execute_tools_parallel(self, tool_calls: List[ToolCall]) -> List[ToolResult]:
        """Execute multiple tools in parallel"""
        start_time = time.time()
        
        results = await tool_registry.execute_tools_parallel(tool_calls)
        
        duration = time.time() - start_time
        success_count = sum(1 for r in results if r.success)
        
        return results
    
    # MARK: - Result Formatting
    
    def format_tool_result(self, result: ToolResult, tool_name: str) -> str:
        """Format tool result for inclusion in conversation"""
        if result.success:
            formatted = result.content
            
            # Add metadata if available
            if result.metadata:
                metadata_str = ", ".join(f"{k}: {v}" for k, v in result.metadata.items())
                formatted += f"\n\n[Tool metadata: {metadata_str}]"
            
            return formatted
        else:
            return f"[Tool {tool_name} failed: {result.error or 'Unknown error'}]"
    
    def format_tool_results(
        self, results: List[ToolResult], tool_calls: List[ToolCall]
    ) -> List[str]:
        """Format multiple tool results"""
        formatted: List[str] = []
        
        for i, result in enumerate(results):
            tool_name = (
                tool_calls[i].function.name if i < len(tool_calls) else "unknown"
            )
            formatted.append(self.format_tool_result(result, tool_name))
        
        return formatted
    
    def create_tool_result_message(self, tool_name: str, content: str) -> dict:
        """Create tool result message for conversation history"""
        return {
            "role": "tool",
            "tool_name": tool_name,
            "content": content,
        }


# Global singleton instance
tool_execution_service = ToolExecutionService()


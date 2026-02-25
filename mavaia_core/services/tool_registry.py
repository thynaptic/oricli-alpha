from __future__ import annotations
"""
Tool Registry Service

Manages tool definitions and provides tool invocation capabilities
with support for programmatic tool calling from code execution.
"""

import json
import uuid
from typing import Dict, Any, Optional, List, Callable
from dataclasses import dataclass, field

from mavaia_core.exceptions import MavaiaError


class ToolRegistryError(MavaiaError):
    """Raised when tool registry operations fail."""
    pass


@dataclass
class ToolDefinition:
    """
    Internal tool definition dataclass.
    
    Attributes:
        name: Tool name (unique identifier)
        description: Tool description
        parameters: JSON Schema parameters definition
        allowed_callers: List of allowed callers: ["direct", "code_execution_20250825"]
        handler: Callable that executes the tool
        result_format: Result format: "json" or "native"
        defer_loading: If True, tool definition is deferred and will be loaded on-demand
    """
    name: str
    description: str
    parameters: Dict[str, Any]
    allowed_callers: List[str] = field(default_factory=lambda: ["direct"])
    handler: Optional[Callable] = None
    result_format: str = "json"
    defer_loading: bool = False
    
    def __post_init__(self):
        """Validate tool definition."""
        if not self.name:
            raise ValueError("Tool name cannot be empty")
        if not self.allowed_callers:
            raise ValueError("Tool must have at least one allowed caller")
        
        valid_callers = {"direct", "code_execution_20250825"}
        for caller in self.allowed_callers:
            if caller not in valid_callers:
                raise ValueError(
                    f"Invalid caller: {caller}. Must be one of {valid_callers}"
                )
        
        if self.result_format not in ("json", "native"):
            raise ValueError(f"result_format must be 'json' or 'native', got {self.result_format}")
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary (excluding handler)."""
        return {
            "name": self.name,
            "description": self.description,
            "parameters": self.parameters,
            "allowed_callers": self.allowed_callers,
            "result_format": self.result_format,
            "defer_loading": self.defer_loading,
        }


class ToolRegistry:
    """
    Registry for managing tools and their definitions.
    
    Supports both direct tool calling and programmatic tool calling
    from code execution contexts.
    """
    
    _instance: Optional["ToolRegistry"] = None
    _tools: Dict[str, ToolDefinition] = {}
    
    def __new__(cls):
        """Singleton pattern."""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    def register_tool(
        self,
        name: str,
        description: str,
        parameters: Dict[str, Any],
        handler: Optional[Callable] = None,
        allowed_callers: Optional[List[str]] = None,
        result_format: str = "json",
        defer_loading: bool = False,
    ) -> None:
        """
        Register a tool.
        
        Args:
            name: Tool name (must be unique)
            description: Tool description
            parameters: JSON Schema parameters definition
            handler: Callable that executes the tool (optional if defer_loading=True)
            allowed_callers: List of allowed callers (default: ["direct"])
            result_format: Result format: "json" or "native" (default: "json")
            defer_loading: If True, tool can be registered without handler for lazy loading
            
        Raises:
            ToolRegistryError: If tool registration fails
        """
        if name in self._tools:
            raise ToolRegistryError(f"Tool '{name}' is already registered")
        
        allowed_callers = allowed_callers or ["direct"]
        
        # Validate handler requirement
        if not defer_loading and handler is None:
            raise ToolRegistryError(f"Tool '{name}' requires a handler unless defer_loading=True")
        
        try:
            tool_def = ToolDefinition(
                name=name,
                description=description,
                parameters=parameters,
                allowed_callers=allowed_callers,
                handler=handler,
                result_format=result_format,
                defer_loading=defer_loading,
            )
            self._tools[name] = tool_def
        except Exception as e:
            raise ToolRegistryError(f"Failed to register tool '{name}': {str(e)}")
    
    def unregister_tool(self, name: str) -> None:
        """
        Unregister a tool.
        
        Args:
            name: Tool name
            
        Raises:
            ToolRegistryError: If tool is not registered
        """
        if name not in self._tools:
            raise ToolRegistryError(f"Tool '{name}' is not registered")
        del self._tools[name]
    
    def get_tool(self, name: str) -> Optional[ToolDefinition]:
        """
        Get tool definition by name.
        
        Args:
            name: Tool name
            
        Returns:
            ToolDefinition or None if not found
        """
        return self._tools.get(name)
    
    def list_tools(self, caller: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        List all registered tools.
        
        Args:
            caller: Optional caller to filter by (only return tools that allow this caller)
            
        Returns:
            List of tool definitions (as dictionaries)
        """
        tools = []
        for tool_def in self._tools.values():
            if caller is None or caller in tool_def.allowed_callers:
                tools.append(tool_def.to_dict())
        return tools
    
    def invoke_tool(
        self,
        tool_name: str,
        input_params: Dict[str, Any],
        caller: str = "direct",
    ) -> Any:
        """
        Invoke a tool.
        
        Args:
            tool_name: Tool name to invoke
            input_params: Tool input parameters
            caller: Caller type: "direct" or "code_execution_20250825"
            
        Returns:
            Tool result (formatted according to tool's result_format)
            
        Raises:
            ToolRegistryError: If tool invocation fails
        """
        tool_def = self._tools.get(tool_name)
        if not tool_def:
            raise ToolRegistryError(f"Tool '{tool_name}' is not registered")
        
        # Check if caller is allowed
        if caller not in tool_def.allowed_callers:
            raise ToolRegistryError(
                f"Tool '{tool_name}' does not allow caller '{caller}'. "
                f"Allowed callers: {tool_def.allowed_callers}"
            )
        
        # Validate handler exists
        if tool_def.handler is None:
            raise ToolRegistryError(f"Tool '{tool_name}' has no handler")
        
        # Invoke tool
        try:
            result = tool_def.handler(**input_params)
        except Exception as e:
            raise ToolRegistryError(f"Tool '{tool_name}' execution failed: {str(e)}")
        
        # Format result according to result_format
        if tool_def.result_format == "json":
            # Convert to JSON string
            try:
                if isinstance(result, (dict, list, str, int, float, bool, type(None))):
                    return json.dumps(result)
                else:
                    # Try to serialize
                    return json.dumps(str(result))
            except Exception:
                return json.dumps(str(result))
        else:
            # Native format - return as-is
            return result
    
    def can_call(self, tool_name: str, caller: str) -> bool:
        """
        Check if a caller can invoke a tool.
        
        Args:
            tool_name: Tool name
            caller: Caller type
            
        Returns:
            True if caller can invoke tool, False otherwise
        """
        tool_def = self._tools.get(tool_name)
        if not tool_def:
            return False
        return caller in tool_def.allowed_callers
    
    def register_deferred_tool(
        self,
        name: str,
        description: str,
        parameters: Dict[str, Any],
        allowed_callers: Optional[List[str]] = None,
        result_format: str = "json",
    ) -> None:
        """
        Register a deferred tool (without handler).
        
        Args:
            name: Tool name (must be unique)
            description: Tool description
            parameters: JSON Schema parameters definition
            allowed_callers: List of allowed callers (default: ["direct"])
            result_format: Result format: "json" or "native" (default: "json")
            
        Raises:
            ToolRegistryError: If tool registration fails
        """
        self.register_tool(
            name=name,
            description=description,
            parameters=parameters,
            handler=None,
            allowed_callers=allowed_callers,
            result_format=result_format,
            defer_loading=True,
        )
    
    def load_deferred_tool(
        self,
        name: str,
        handler: Callable,
    ) -> None:
        """
        Load/expand a deferred tool by registering its handler.
        
        Args:
            name: Tool name
            handler: Callable that executes the tool
            
        Raises:
            ToolRegistryError: If tool is not found or not deferred
        """
        tool_def = self._tools.get(name)
        if not tool_def:
            raise ToolRegistryError(f"Tool '{name}' is not registered")
        
        if not tool_def.defer_loading:
            raise ToolRegistryError(f"Tool '{name}' is not a deferred tool")
        
        # Update tool with handler and mark as loaded
        tool_def.handler = handler
        tool_def.defer_loading = False
    
    def list_deferred_tools(self) -> List[Dict[str, Any]]:
        """
        List all deferred tools (tools registered with defer_loading=True).
        
        Returns:
            List of deferred tool definitions (as dictionaries)
        """
        tools = []
        for tool_def in self._tools.values():
            if tool_def.defer_loading:
                tools.append(tool_def.to_dict())
        return tools
    
    def is_deferred(self, tool_name: str) -> bool:
        """
        Check if a tool is deferred.
        
        Args:
            tool_name: Tool name
            
        Returns:
            True if tool is deferred, False otherwise
        """
        tool_def = self._tools.get(tool_name)
        if not tool_def:
            return False
        return tool_def.defer_loading
    
    def clear(self) -> None:
        """Clear all registered tools (for testing)."""
        self._tools.clear()


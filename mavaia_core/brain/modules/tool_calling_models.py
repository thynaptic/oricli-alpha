"""
Tool Calling Models - Compatible with Ollama's tool calling format
Mirrors Swift ToolCalling.swift functionality
"""

from typing import Any, Dict, List, Optional
from dataclasses import dataclass, field
import time
import uuid

from mavaia_core.exceptions import InvalidParameterError


# MARK: - Tool Schema

@dataclass
class ToolProperty:
    """Tool property definition"""
    type: str  # "string", "number", "integer", "boolean", "array", "object"
    description: Optional[str] = None
    enum_values: Optional[List[str]] = None  # For enum types
    items: Optional["ToolProperty"] = None  # For array types
    properties: Optional[Dict[str, "ToolProperty"]] = None  # For object types

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization"""
        result: Dict[str, Any] = {"type": self.type}
        if self.description:
            result["description"] = self.description
        if self.enum_values:
            result["enum"] = self.enum_values
        if self.items:
            result["items"] = self.items.to_dict()
        if self.properties:
            result["properties"] = {k: v.to_dict() for k, v in self.properties.items()}
        return result


@dataclass
class ToolParameters:
    """Tool parameters definition"""
    type: str = "object"
    required: Optional[List[str]] = None
    properties: Dict[str, ToolProperty] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization"""
        result: Dict[str, Any] = {"type": self.type}
        if self.required:
            result["required"] = self.required
        result["properties"] = {k: v.to_dict() for k, v in self.properties.items()}
        return result


@dataclass
class ToolFunction:
    """Tool function definition"""
    name: str
    description: str
    parameters: ToolParameters

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization"""
        return {
            "name": self.name,
            "description": self.description,
            "parameters": self.parameters.to_dict(),
        }


@dataclass
class Tool:
    """Tool definition compatible with Ollama format"""
    type: str = "function"
    function: ToolFunction = field(default=None)

    def __post_init__(self):
        if self.function is None:
            raise InvalidParameterError("function", "None", "function is required")

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization"""
        return {
            "type": self.type,
            "function": self.function.to_dict(),
        }


# MARK: - Tool Call

@dataclass
class ToolCallFunction:
    """Tool call function"""
    name: str
    arguments: Dict[str, Any]

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization"""
        return {
            "name": self.name,
            "arguments": self.arguments,
        }


@dataclass
class ToolCall:
    """Tool call from model"""
    index: Optional[int] = None
    function: ToolCallFunction = field(default=None)

    def __post_init__(self):
        if self.function is None:
            raise InvalidParameterError("function", "None", "function is required")

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization"""
        result: Dict[str, Any] = {"function": self.function.to_dict()}
        if self.index is not None:
            result["index"] = self.index
        return result


# MARK: - Tool Result

@dataclass
class ToolResult:
    """Result from tool execution"""
    content: str
    metadata: Optional[Dict[str, Any]] = None
    success: bool = True
    error: Optional[str] = None
    tool_name: Optional[str] = None

    @classmethod
    def success_result(
        cls, content: str, tool_name: Optional[str] = None, metadata: Optional[Dict[str, Any]] = None
    ) -> "ToolResult":
        """Create a success result"""
        return cls(content=content, metadata=metadata, success=True, tool_name=tool_name)

    @classmethod
    def failure_result(cls, error: str, tool_name: Optional[str] = None) -> "ToolResult":
        """Create a failure result"""
        return cls(content="", metadata=None, success=False, error=error, tool_name=tool_name)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization"""
        result: Dict[str, Any] = {
            "content": self.content,
            "success": self.success,
        }
        if self.metadata:
            result["metadata"] = self.metadata
        if self.error:
            result["error"] = self.error
        if self.tool_name:
            result["tool_name"] = self.tool_name
        return result


# MARK: - Agent Loop Result

@dataclass
class AgentLoopResult:
    """Result from agent loop execution"""
    final_response: str
    tool_calls: List[ToolCall] = field(default_factory=list)
    tool_results: List[ToolResult] = field(default_factory=list)
    iterations: int = 0
    thinking: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization"""
        return {
            "final_response": self.final_response,
            "tool_calls": [tc.to_dict() for tc in self.tool_calls],
            "tool_results": [tr.to_dict() for tr in self.tool_results],
            "iterations": self.iterations,
            "thinking": self.thinking,
            "metadata": self.metadata,
        }


# MARK: - Tool Executor Type

from typing import Callable, Awaitable

ToolExecutor = Callable[[Dict[str, Any]], Awaitable[ToolResult]]


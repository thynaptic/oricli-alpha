"""
Programmatic Tool Calling Module

Enables code execution to call tools programmatically. Code can pause execution,
invoke tools, receive results, and continue execution.
"""

import uuid
import json
import re
import ast
from typing import Dict, Any, Optional, List

from mavaia_core.brain.base_module import BaseBrainModule, ModuleMetadata
from mavaia_core.exceptions import (
    ModuleInitializationError,
    ModuleOperationError,
    InvalidParameterError,
)

# Lazy imports to avoid timeout during module discovery
ToolRegistry = None
ToolRegistryError = None

def _lazy_import_tool_registry():
    """Lazy import ToolRegistry only when needed"""
    global ToolRegistry, ToolRegistryError
    if ToolRegistry is None:
        try:
            from mavaia_core.services.tool_registry import ToolRegistry as TR, ToolRegistryError as TRE
            ToolRegistry = TR
            ToolRegistryError = TRE
        except ImportError:
            # Tool registry is optional in some deployments.
            pass


class ProgrammaticToolCallingModule(BaseBrainModule):
    """
    Programmatic tool calling module.
    
    Enables code execution in sandboxes to call tools programmatically,
    reducing latency for multi-tool workflows.
    """
    
    CODE_EXECUTION_CALLER = "code_execution_20250825"
    
    def __init__(self):
        """Initialize programmatic tool calling module."""
        super().__init__()
        self._tool_registry = None
        self._code_execution_module = None
    
    def _ensure_tool_registry(self):
        """Lazy load tool registry only when needed"""
        _lazy_import_tool_registry()
        if ToolRegistry is None:
            raise ModuleInitializationError(
                module_name=self.metadata.name,
                reason="ToolRegistry is not available (import failed)",
            )
        if self._tool_registry is None:
            self._tool_registry = ToolRegistry()
    
    @property
    def metadata(self) -> ModuleMetadata:
        """Return module metadata."""
        return ModuleMetadata(
            name="programmatic_tool_calling",
            version="1.0.0",
            description="Programmatic tool calling from code execution contexts",
            operations=[
                "execute_with_tools",
                "register_tool",
                "list_tools",
                "invoke_tool",
            ],
            dependencies=[],
            enabled=True,
            model_required=False,
        )
    
    def initialize(self) -> bool:
        """Initialize the module."""
        try:
            # Get code execution module (lazy import to avoid circular dependency)
            from mavaia_core.brain.registry import ModuleRegistry
            code_exec_module = ModuleRegistry.get_module("code_execution")
            if code_exec_module:
                self._code_execution_module = code_exec_module
            return True
        except Exception:
            # Code execution module may not be available
            return True
    
    def execute(self, operation: str, params: Dict[str, Any]) -> Dict[str, Any]:
        """Execute a programmatic tool calling operation."""
        self._ensure_tool_registry()
        try:
            if operation == "execute_with_tools":
                return self._execute_with_tools(params)
            elif operation == "register_tool":
                return self._register_tool(params)
            elif operation == "list_tools":
                return self._list_tools(params)
            elif operation == "invoke_tool":
                return self._invoke_tool(params)
            else:
                raise InvalidParameterError(
                    "operation",
                    str(operation),
                    "Unknown operation for programmatic_tool_calling",
                )
        except (ToolRegistryError, InvalidParameterError) as e:
            raise ModuleOperationError(
                self.metadata.name,
                operation,
                str(e),
            )
        except Exception as e:
            raise ModuleOperationError(
                self.metadata.name,
                operation,
                f"Unexpected error: {str(e)}",
            )
    
    def _execute_with_tools(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute code with programmatic tool calling enabled.
        
        Args:
            code: Code to execute (Python or Node.js)
            language: Language ("python" or "node")
            session_id: Optional session ID
            tools: List of tool names available for calling
            resource_limits: Optional resource limits
            
        Returns:
            Execution result with tool calls and results
        """
        code = params.get("code", "")
        language = params.get("language", "python")
        session_id = params.get("session_id")
        tools = params.get("tools", [])
        resource_limits = params.get("resource_limits")
        
        if not code:
            raise InvalidParameterError("code", "", "Code cannot be empty")
        
        if language not in ("python", "node"):
            raise InvalidParameterError(
                "language", language, "Language must be 'python' or 'node'"
            )
        
        # Validate tools
        available_tools = []
        for tool_name in tools:
            tool_def = self._tool_registry.get_tool(tool_name)
            if not tool_def:
                raise InvalidParameterError(
                    "tools", tool_name, f"Tool '{tool_name}' is not registered"
                )
            # Check if tool allows programmatic calling
            if self.CODE_EXECUTION_CALLER not in tool_def.allowed_callers:
                raise InvalidParameterError(
                    "tools",
                    tool_name,
                    f"Tool '{tool_name}' does not allow programmatic calling",
                )
            available_tools.append(tool_name)
        
        if not self._code_execution_module:
            raise ModuleOperationError(
                self.metadata.name,
                "execute_with_tools",
                "Code execution module is not available",
            )
        
        # Inject tool calling helpers into code
        wrapped_code = self._wrap_code_with_tool_support(code, language, available_tools)
        
        # Execute code with tool calling support
        exec_params = {
            "code": wrapped_code,
            "language": language,
            "session_id": session_id,
            "resource_limits": resource_limits,
        }
        
        if language == "python":
            result = self._code_execution_module.execute("execute_python", exec_params)
        else:  # node
            result = self._code_execution_module.execute("execute_node", exec_params)
        
        # Parse tool calls from output
        tool_calls, tool_results, final_output = self._parse_tool_calls_from_output(
            result.get("stdout", ""), language
        )
        
        return {
            "session_id": result.get("session_id"),
            "success": result.get("success", False),
            "output": final_output,
            "tool_calls": tool_calls,
            "tool_results": tool_results,
            "stdout": result.get("stdout"),
            "stderr": result.get("stderr"),
            "execution_time": result.get("execution_time", 0.0),
        }
    
    def _wrap_code_with_tool_support(
        self, code: str, language: str, available_tools: List[str]
    ) -> str:
        """
        Wrap code with tool calling support.
        
        Creates a wrapper that intercepts tool calls and handles them.
        """
        if language == "python":
            return self._wrap_python_code(code, available_tools)
        else:  # node
            return self._wrap_node_code(code, available_tools)
    
    def _wrap_python_code(self, code: str, available_tools: List[str]) -> str:
        """Wrap Python code with tool calling support."""
        tools_json = json.dumps(available_tools)
        
        wrapper = f"""
# Tool calling support injected by programmatic_tool_calling module
import json
import sys

class ToolCallError(Exception):
    pass

# Tool registry (will be populated by wrapper)
_tool_results = {{}}

def mavaia_tools_invoke(tool_name, **kwargs):
    '''Invoke a tool programmatically'''
    # Serialize tool call
    tool_call_id = str(hash(str(tool_name) + str(kwargs) + str(sys.modules[__name__])))
    tool_call = {{
        "id": tool_call_id,
        "type": "tool_use",
        "name": tool_name,
        "input": kwargs,
        "caller": "code_execution_20250825"
    }}
    
    # Print tool call marker
    print(f"__MAVAIA_TOOL_USE__{{json.dumps(tool_call)}}__END_TOOL_USE__")
    sys.stdout.flush()
    
    # Wait for tool result (simulated by reading from special variable)
    # In real implementation, execution would pause here
    # For now, we'll read from a marker in output
    result_marker = f"__MAVAIA_TOOL_RESULT_{{{{tool_call_id}}}}__"
    
    # Try to get result (this is a simplified version)
    # Full implementation would pause execution and wait
    if tool_call_id in _tool_results:
        result = _tool_results[tool_call_id]
        if isinstance(result, str):
            try:
                return json.loads(result)
            except Exception:
                return result
        return result
    else:
        # Return placeholder (in real implementation, would block until result)
        return {{"status": "pending", "tool_call_id": tool_call_id}}

# Make available as mavaia.tools.invoke
class MavaiaTools:
    def invoke(self, tool_name, **kwargs):
        return mavaia_tools_invoke(tool_name, **kwargs)

class Mavaia:
    tools = MavaiaTools()

# User code
{code}
"""
        return wrapper
    
    def _wrap_node_code(self, code: str, available_tools: List[str]) -> str:
        """Wrap Node.js code with tool calling support."""
        tools_json = json.dumps(available_tools)
        
        wrapper = f"""
// Tool calling support injected by programmatic_tool_calling module
const crypto = require('crypto');

// Tool registry
const _toolResults = {{}};

function mavaiaToolsInvoke(toolName, kwargs) {{
    // Serialize tool call
    const toolCallId = crypto.createHash('md5').update(toolName + JSON.stringify(kwargs)).digest('hex');
    const toolCall = {{
        id: toolCallId,
        type: "tool_use",
        name: toolName,
        input: kwargs,
        caller: "code_execution_20250825"
    }};
    
    // Print tool call marker
    console.log(`__MAVAIA_TOOL_USE__${{JSON.stringify(toolCall)}}__END_TOOL_USE__`);
    
    // Try to get result
    if (_toolResults[toolCallId]) {{
        const result = _toolResults[toolCallId];
        try {{
            return JSON.parse(result);
        }} catch (e) {{
            return result;
        }}
    }} else {{
        return {{status: "pending", toolCallId: toolCallId}};
    }}
}}

// Make available as mavaia.tools.invoke
const mavaia = {{
    tools: {{
        invoke: mavaiaToolsInvoke
    }}
}};

// User code
{code}
"""
        return wrapper
    
    def _parse_tool_calls_from_output(
        self, output: str, language: str
    ) -> tuple[List[Dict[str, Any]], List[Dict[str, Any]], str]:
        """
        Parse tool calls and results from code execution output.
        
        Returns:
            Tuple of (tool_calls, tool_results, cleaned_output)
        """
        tool_calls = []
        tool_results = []
        cleaned_output = output
        
        # Extract tool use blocks
        tool_use_pattern = r"__MAVAIA_TOOL_USE__(.*?)__END_TOOL_USE__"
        matches = re.findall(tool_use_pattern, output, re.DOTALL)
        
        for match in matches:
            try:
                tool_call = json.loads(match.strip())
                tool_calls.append(tool_call)
                
                # Invoke tool
                tool_name = tool_call.get("name")
                tool_input = tool_call.get("input", {})
                tool_call_id = tool_call.get("id")
                
                try:
                    result = self._tool_registry.invoke_tool(
                        tool_name=tool_name,
                        input_params=tool_input,
                        caller=self.CODE_EXECUTION_CALLER,
                    )
                    
                    tool_result = {
                        "tool_use_id": tool_call_id,
                        "type": "tool_result",
                        "content": result,
                        "is_error": False,
                    }
                    tool_results.append(tool_result)
                    
                    # Inject result back into output (simplified - full implementation would resume execution)
                    # For now, we'll replace the tool call marker with result
                    result_marker = f"__MAVAIA_TOOL_RESULT_{tool_call_id}__"
                    cleaned_output = cleaned_output.replace(
                        f"__MAVAIA_TOOL_USE__{match}__END_TOOL_USE__",
                        result_marker,
                    )
                    
                except Exception as e:
                    tool_result = {
                        "tool_use_id": tool_call_id,
                        "type": "tool_result",
                        "content": str(e),
                        "is_error": True,
                    }
                    tool_results.append(tool_result)
            except Exception:
                # Skip invalid tool call JSON
                continue
        
        # Remove tool call markers from cleaned output
        cleaned_output = re.sub(tool_use_pattern, "", cleaned_output)
        
        return tool_calls, tool_results, cleaned_output.strip()
    
    def _register_tool(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Register a tool for programmatic calling."""
        name = params.get("name")
        description = params.get("description", "")
        parameters = params.get("parameters", {})
        allowed_callers = params.get("allowed_callers", ["direct"])
        result_format = params.get("result_format", "json")
        
        if not name:
            raise InvalidParameterError("name", "", "Tool name is required")
        
        # Handler would need to be provided as a module/operation reference
        # For now, we'll support registering tools that map to brain module operations
        handler_module = params.get("handler_module")
        handler_operation = params.get("handler_operation")
        
        if not handler_module or not handler_operation:
            raise InvalidParameterError(
                "handler_module/handler_operation",
                "",
                "Tool handler must specify module and operation",
            )
        
        # Get handler from module registry
        from mavaia_core.brain.registry import ModuleRegistry
        
        module = ModuleRegistry.get_module(handler_module)
        if not module:
            raise InvalidParameterError(
                "handler_module", handler_module, f"Module '{handler_module}' not found"
            )
        
        def tool_handler(**kwargs):
            return module.execute(handler_operation, kwargs)
        
        try:
            self._tool_registry.register_tool(
                name=name,
                description=description,
                parameters=parameters,
                handler=tool_handler,
                allowed_callers=allowed_callers,
                result_format=result_format,
            )
            return {"success": True, "tool_name": name}
        except Exception as e:
            raise ModuleOperationError(
                self.metadata.name, "register_tool", f"Failed to register tool: {str(e)}"
            )
    
    def _list_tools(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """List available tools."""
        caller = params.get("caller")
        
        tools = self._tool_registry.list_tools(caller=caller)
        
        return {
            "success": True,
            "tools": tools,
            "count": len(tools),
        }
    
    def _invoke_tool(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Invoke a tool directly (for testing/debugging)."""
        tool_name = params.get("tool_name")
        input_params = params.get("input", {})
        caller = params.get("caller", "direct")
        
        if not tool_name:
            raise InvalidParameterError("tool_name", "", "Tool name is required")
        
        try:
            result = self._tool_registry.invoke_tool(
                tool_name=tool_name,
                input_params=input_params,
                caller=caller,
            )
            
            return {
                "success": True,
                "result": result,
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
            }


from __future__ import annotations
"""
Tool Registry - Central registry for all available tools
Mirrors Swift ToolRegistry.swift functionality
"""

from typing import Any, Dict, List, Optional
import asyncio
try:
    from oricli_core.brain.modules.tool_calling_models import Tool, ToolCall, ToolResult, ToolExecutor
except ImportError:
    from tool_calling_models import Tool, ToolCall, ToolResult, ToolExecutor


class ToolRegistryError(Exception):
    """Tool registry errors"""
    pass


class ToolNotFoundError(ToolRegistryError):
    """Tool not found in registry"""
    def __init__(self, tool_name: str):
        self.tool_name = tool_name
        super().__init__(f"Tool '{tool_name}' not found in registry")


class ToolExecutionFailedError(ToolRegistryError):
    """Tool execution failed"""
    def __init__(self, tool_name: str, error: str):
        self.tool_name = tool_name
        self.error = error
        super().__init__(f"Tool '{tool_name}' execution failed: {error}")


class ToolRegistry:
    """Central registry for all available tools"""
    
    _instance: Optional["ToolRegistry"] = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        if self._initialized:
            return
        self._initialized = True
        self.tools: Dict[str, Tool] = {}
        self.executors: Dict[str, ToolExecutor] = {}
    
    # MARK: - Tool Registration
    
    def register_tool(self, tool: Tool, executor: ToolExecutor) -> None:
        """Register a tool with its executor"""
        tool_name = tool.function.name
        self.tools[tool_name] = tool
        self.executors[tool_name] = executor
    
    def register_tools(self, tools: List[tuple[Tool, ToolExecutor]]) -> None:
        """Register multiple tools at once"""
        for tool, executor in tools:
            self.register_tool(tool, executor)
    
    # MARK: - Tool Retrieval
    
    def get_tool(self, name: str) -> Optional[Tool]:
        """Get a tool by name"""
        return self.tools.get(name)
    
    def get_all_tools(self) -> List[Tool]:
        """Get all registered tools"""
        return list(self.tools.values())
    
    def get_tool_names(self) -> List[str]:
        """Get tool names"""
        return list(self.tools.keys())
    
    def has_tool(self, name: str) -> bool:
        """Check if a tool is registered"""
        return name in self.tools
    
    # MARK: - Tool Execution
    
    async def execute_tool(self, name: str, arguments: Dict[str, Any]) -> ToolResult:
        """Execute a tool by name with arguments"""
        if name not in self.executors:
            raise ToolNotFoundError(name)
        
        executor = self.executors[name]
        
        try:
            result = await executor(arguments)
            return result
        except Exception as e:
            raise ToolExecutionFailedError(name, str(e))
    
    async def execute_tools_parallel(self, tool_calls: List[ToolCall]) -> List[ToolResult]:
        """Execute multiple tools in parallel"""
        async def execute_with_index(index: int, tool_call: ToolCall) -> tuple[int, ToolResult]:
            try:
                result = await self.execute_tool(
                    tool_call.function.name,
                    tool_call.function.arguments
                )
                return (index, result)
            except Exception as e:
                return (index, ToolResult.failure_result(str(e), tool_call.function.name))
        
        tasks = [
            execute_with_index(i, tool_call)
            for i, tool_call in enumerate(tool_calls)
        ]
        
        results = await asyncio.gather(*tasks)
        
        # Sort by index to maintain order
        results.sort(key=lambda x: x[0])
        return [result for _, result in results]
    
    # MARK: - Tool Management
    
    def unregister_tool(self, name: str) -> None:
        """Unregister a tool"""
        self.tools.pop(name, None)
        self.executors.pop(name, None)
    
    def clear_all_tools(self) -> None:
        """Clear all tools"""
        self.tools.clear()
        self.executors.clear()
    
    def get_tool_count(self) -> int:
        """Get tool count"""
        return len(self.tools)


# Global singleton instance
tool_registry = ToolRegistry()


    def sync_with_module_registry(self) -> None:
        """
        Dynamically discover and register tools from the ModuleRegistry.
        This allows autonomously created tools (BaseBrainModules) to be used immediately.
        """
        try:
            from oricli_core.brain.registry import ModuleRegistry
            
            # Ensure ModuleRegistry has discovered all modules
            ModuleRegistry.discover_modules()
            
            # Find all modules that look like tools (have operations)
            for module_name, module in ModuleRegistry._modules.items():
                if module_name not in self.tools and hasattr(module, "metadata"):
                    meta = module.metadata
                    
                    # Create a Tool definition
                    tool_def = Tool(
                        name=meta.name,
                        description=meta.description,
                        parameters={
                            "type": "object",
                            "properties": {
                                "operation": {
                                    "type": "string",
                                    "description": f"The operation to perform. Supported: {', '.join(meta.operations)}",
                                    "enum": meta.operations
                                },
                                "params": {
                                    "type": "object",
                                    "description": "Parameters for the operation"
                                }
                            },
                            "required": ["operation"]
                        }
                    )
                    
                    # Create an executor that calls the module
                    async def make_executor(mod):
                        async def executor(args: Dict[str, Any]) -> ToolResult:
                            try:
                                op = args.get("operation")
                                params = args.get("params", {})
                                if not op:
                                    return ToolResult.failure_result("Missing 'operation' parameter", mod.metadata.name)
                                    
                                res = mod.execute(op, params)
                                return ToolResult.success_result(res)
                            except Exception as e:
                                return ToolResult.failure_result(str(e), mod.metadata.name)
                        return executor
                    
                    # Register it
                    # We need to run the async factory synchronously to get the coroutine function
                    import asyncio
                    loop = asyncio.get_event_loop()
                    if loop.is_running():
                        # If we're already in an event loop, we can't use run_until_complete easily here
                        # We'll just create the closure directly
                        def create_closure(mod):
                            async def executor(args: Dict[str, Any]) -> ToolResult:
                                try:
                                    op = args.get("operation")
                                    params = args.get("params", {})
                                    if not op:
                                        return ToolResult.failure_result("Missing 'operation' parameter", mod.metadata.name)
                                        
                                    res = mod.execute(op, params)
                                    return ToolResult.success_result(res)
                                except Exception as e:
                                    return ToolResult.failure_result(str(e), mod.metadata.name)
                            return executor
                            
                        self.register_tool(tool_def, create_closure(module))
                    else:
                        self.register_tool(tool_def, loop.run_until_complete(make_executor(module)))
                        
        except Exception as e:
            # Silently fail if we can't sync, to avoid breaking the registry
            pass

"""
Tool Calling Agent Service - Service for multi-turn tool calling (agent loop)
Converted from Swift ToolCallingAgentService.swift
"""

from typing import Any, Dict, List, Optional
import logging
import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent))

from mavaia_core.brain.base_module import BaseBrainModule, ModuleMetadata
from mavaia_core.exceptions import InvalidParameterError
from tool_calling_models import ToolCall, ToolCallFunction, ToolResult, AgentLoopResult

logger = logging.getLogger(__name__)

class ToolCallingAgentServiceModule(BaseBrainModule):
    """Service for multi-turn tool calling (agent loop)"""

    def __init__(self):
        self.cognitive_generator = None
        self.tool_execution = None
        self.tool_parser = None
        self.plan_service = None
        self._modules_loaded = False

    @property
    def metadata(self) -> ModuleMetadata:
        return ModuleMetadata(
            name="tool_calling_agent_service",
            version="1.0.0",
            description="Service for multi-turn tool calling (agent loop)",
            operations=[
                "execute_agent_loop",
                "execute_plan_based_loop",
                "execute_iterative_loop",
            ],
            dependencies=[],
            model_required=False,
        )

    def initialize(self) -> bool:
        """Initialize the module"""
        return True

    def _ensure_modules_loaded(self):
        """Lazy load dependent modules"""
        if self._modules_loaded:
            return

        try:
            from module_registry import ModuleRegistry

            self.cognitive_generator = ModuleRegistry.get_module("cognitive_generator")
            self.tool_execution = ModuleRegistry.get_module("tool_execution_service")
            self.tool_parser = ModuleRegistry.get_module("tool_call_parser")
            self.plan_service = ModuleRegistry.get_module("tool_calling_plan_service")

            self._modules_loaded = True
        except Exception as e:
            # Modules not available - will use fallback methods
            logger.debug(
                "Failed to load one or more tool calling dependencies",
                exc_info=True,
                extra={"module_name": "tool_calling_agent_service", "error_type": type(e).__name__},
            )

    def execute(self, operation: str, params: Dict[str, Any]) -> Dict[str, Any]:
        """Execute an operation"""
        self._ensure_modules_loaded()

        if operation == "execute_agent_loop":
            return self._execute_agent_loop(params)
        elif operation == "execute_plan_based_loop":
            return self._execute_plan_based_loop(params)
        elif operation == "execute_iterative_loop":
            return self._execute_iterative_loop(params)
        else:
            raise InvalidParameterError(
                parameter="operation",
                value=operation,
                reason="Unknown operation for tool_calling_agent_service",
            )

    def _execute_agent_loop(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Execute agent loop with tool calling (plan-based or iterative)"""
        query = params.get("query", "")
        tools = params.get("tools", [])
        use_planning = params.get("use_planning", True)

        should_plan = False
        if use_planning and self.plan_service:
            try:
                should_plan_result = self.plan_service.execute("should_create_plan", {
                    "query": query,
                    "available_tools": tools,
                })
                should_plan = should_plan_result.get("should_plan", False)
            except Exception as e:
                logger.debug(
                    "Plan service should_create_plan failed; continuing with iterative loop",
                    exc_info=True,
                    extra={"module_name": "tool_calling_agent_service", "error_type": type(e).__name__},
                )

        if should_plan:
            return self._execute_plan_based_loop(params)
        else:
            return self._execute_iterative_loop(params)

    def _execute_plan_based_loop(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Execute agent loop using plan-based approach"""
        query = params.get("query", "")
        tools = params.get("tools", [])
        system_prompt = params.get("system_prompt")
        conversation_history = params.get("conversation_history")

        if not self.plan_service:
            # Fall back to iterative execution if plan service not available
            return self._execute_iterative_loop(params)

        try:
            # Create plan
            plan_result = self.plan_service.execute("create_plan", {
                "query": query,
                "tools": tools,
                "conversation_history": conversation_history,
            })

            plan = plan_result.get("plan")
            if not plan or not plan.get("steps"):
                # Fall back to iterative execution if plan creation fails
                return self._execute_iterative_loop(params)

            # Validate plan
            validation = self.plan_service.execute("validate_plan", {
                "plan": plan,
                "tools": tools,
            })

            if not validation.get("is_valid", False):
                # Fall back to iterative execution if plan is invalid
                return self._execute_iterative_loop(params)

            # Execute plan
            execution_result = self.plan_service.execute("execute_plan", {
                "plan": plan,
                "tools": tools,
                "system_prompt": system_prompt,
                "conversation_history": conversation_history,
            })

            # Convert plan execution result to AgentLoopResult format
            steps = plan.get("steps", [])
            tool_calls = []
            for step in steps:
                tool_calls.append({
                    "index": None,
                    "function": {
                        "name": step.get("tool_name", ""),
                        "arguments": step.get("arguments", {}),
                    },
                })

            completed_steps = execution_result.get("completed_steps", [])
            step_results = execution_result.get("step_results", {})

            tool_results = []
            for step_id in completed_steps:
                if step_id in step_results:
                    tool_results.append(step_results[step_id])

            return {
                "success": True,
                "final_response": execution_result.get("final_response", ""),
                "tool_calls": tool_calls,
                "tool_results": tool_results,
                "iterations": len(completed_steps),
                "thinking": None,
                "metadata": {
                    "plan_id": plan.get("id"),
                    "completed_steps": len(completed_steps),
                    "failed_steps": len(execution_result.get("failed_steps", [])),
                    "skipped_steps": len(execution_result.get("skipped_steps", [])),
                    "adaptations": len(execution_result.get("adaptations", [])),
                    "total_time": execution_result.get("total_time", 0.0),
                },
            }
        except Exception as e:
            # Fall back to iterative execution if plan execution fails
            logger.debug(
                "Plan-based loop failed; falling back to iterative loop",
                exc_info=True,
                extra={"module_name": "tool_calling_agent_service", "error_type": type(e).__name__},
            )
            return self._execute_iterative_loop(params)

    def _execute_iterative_loop(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Execute agent loop using iterative approach (fallback for simple queries)"""
        query = params.get("query", "")
        tools = params.get("tools", [])
        system_prompt = params.get("system_prompt")
        conversation_history = params.get("conversation_history", [])
        max_iterations = params.get("max_iterations", 10)

        if not self.cognitive_generator:
            return {
                "success": False,
                "error": "Cognitive generator not available",
                "final_response": "",
                "tool_calls": [],
                "tool_results": [],
                "iterations": 0,
            }

        messages = conversation_history.copy() if conversation_history else []
        all_tool_calls = []
        all_tool_results = []
        iteration = 0

        # Build app context from system prompt
        app_context = system_prompt or "You are a helpful AI assistant with access to tools."

        # Add initial user query if not already in history
        if not messages or messages[-1].get("role") != "user":
            messages.append({"role": "user", "content": query})

        while iteration < max_iterations:
            # Build conversation context from messages
            conversation_context = [
                {"role": msg.get("role", "user"), "content": msg.get("content", "")}
                for msg in messages
            ]

            # Convert tools to Python format
            tools_python_format = []
            for tool in tools:
                tool_dict = {
                    "name": tool.get("function", {}).get("name", ""),
                    "description": tool.get("function", {}).get("description", ""),
                }

                # Convert parameters
                parameters = {}
                tool_params = tool.get("function", {}).get("parameters", {})
                properties = tool_params.get("properties", {})
                for key, property_info in properties.items():
                    param_info = {"type": property_info.get("type", "string")}
                    if "description" in property_info:
                        param_info["description"] = property_info["description"]
                    parameters[key] = param_info
                tool_dict["parameters"] = parameters
                tools_python_format.append(tool_dict)

            # Get tool calls from cognitive generator
            try:
                result = self.cognitive_generator.execute("generate_response_with_tools", {
                    "input": query,
                    "tools": tools_python_format,
                    "context": app_context,
                    "conversation_history": conversation_context,
                    "persona": "mavaia",
                })

                response_text = result.get("text", "")
                tool_calls_dict = result.get("tool_calls", [])

                # Convert tool calls to format
                tool_calls = []
                for tool_call_dict in tool_calls_dict:
                    if isinstance(tool_call_dict, dict):
                        name = tool_call_dict.get("name") or tool_call_dict.get("function", {}).get("name", "")
                        arguments = tool_call_dict.get("arguments") or tool_call_dict.get("function", {}).get("arguments", {})
                        tool_calls.append({
                            "index": tool_call_dict.get("index"),
                            "function": {
                                "name": name,
                                "arguments": arguments,
                            },
                        })
            except Exception as e:
                # If generation fails, break
                break

            # Add assistant message with response
            messages.append({"role": "assistant", "content": response_text})

            # If no tool calls, we're done
            if not tool_calls:
                break

            all_tool_calls.extend(tool_calls)

            # Execute tools
            if self.tool_execution:
                try:
                    tool_results = self.tool_execution.execute("execute_tools_parallel", {
                        "tool_calls": tool_calls,
                    })
                    all_tool_results.extend(tool_results.get("results", []))
                except Exception as e:
                    logger.debug(
                        "Tool execution failed; continuing without tool results",
                        exc_info=True,
                        extra={"module_name": "tool_calling_agent_service", "error_type": type(e).__name__},
                    )

            # Add tool results to conversation
            for result in all_tool_results[-len(tool_calls):]:
                messages.append({
                    "role": "tool",
                    "content": result.get("content", ""),
                })

            iteration += 1

        # Get final response
        final_response = ""
        for msg in reversed(messages):
            if msg.get("role") == "assistant":
                final_response = msg.get("content", "")
                break

        return {
            "success": True,
            "final_response": final_response,
            "tool_calls": all_tool_calls,
            "tool_results": all_tool_results,
            "iterations": iteration,
            "thinking": None,
            "metadata": {},
        }

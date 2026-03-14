from __future__ import annotations
"""
Agent Coordinator
Agent coordinator for lifecycle management and result aggregation
Converted from Swift AgentCoordinator.swift
"""


import logging
from typing import Any, Dict, List, Optional
import time

from oricli_core.brain.base_module import BaseBrainModule, ModuleMetadata
from oricli_core.brain.registry import ModuleRegistry
from oricli_core.exceptions import InvalidParameterError
from oricli_core.services.agent_profile_service import AgentProfile, get_agent_profile_service

logger = logging.getLogger(__name__)


class AgentType:
    """Agent type enumeration"""
    SEARCH = "search"
    RANKING = "ranking"
    SYNTHESIS = "synthesis"
    RESEARCH = "research"
    ANALYSIS = "analysis"
    ANSWER = "answer"


class AgentTask:
    """Agent task definition"""

    def __init__(
        self,
        task_id: str,
        agent_type: str,
        query: str,
        context: Dict[str, Any],
        dependencies: List[str] = None,
        priority: int = 0,
        agent_profile: Optional[str] = None,
    ):
        self.id = task_id
        self.agent_type = agent_type
        self.query = query
        self.context = context
        self.dependencies = dependencies or []
        self.priority = priority
        self.agent_profile = agent_profile

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "agent_type": self.agent_type,
            "query": self.query,
            "context": self.context,
            "dependencies": self.dependencies,
            "priority": self.priority,
            "agent_profile": self.agent_profile,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "AgentTask":
        return cls(
            task_id=data.get("id", ""),
            agent_type=data.get("agent_type", ""),
            query=data.get("query", ""),
            context=data.get("context", {}),
            dependencies=data.get("dependencies", []),
            priority=data.get("priority", 0),
            agent_profile=data.get("agent_profile"),
        )


class AgentResult:
    """Agent execution result"""

    def __init__(
        self,
        task_id: str,
        agent_type: str,
        success: bool,
        output: Any,
        error: Optional[str] = None,
    ):
        self.task_id = task_id
        self.agent_type = agent_type
        self.success = success
        self.output = output
        self.error = error

    def to_dict(self) -> Dict[str, Any]:
        return {
            "task_id": self.task_id,
            "agent_type": self.agent_type,
            "success": self.success,
            "output": self.output if isinstance(self.output, (str, dict, list)) else str(self.output),
            "error": self.error,
        }


class AgentCoordinatorModule(BaseBrainModule):
    """Agent coordinator for lifecycle management and result aggregation"""

    def __init__(self):
        super().__init__()
        self.agents: Dict[str, Any] = {}
        self.results: Dict[str, AgentResult] = {}
        self._modules_loaded = False

    @property
    def metadata(self) -> ModuleMetadata:
        return ModuleMetadata(
            name="agent_coordinator",
            version="1.0.1",
            description="Agent coordinator for lifecycle management and result aggregation",
            operations=[
                "execute_task",
                "execute_parallel",
                "get_result",
                "get_all_results",
                "spawn_agent",
                "status",
            ],
            dependencies=[],
            model_required=False,
        )

    def initialize(self) -> bool:
        """Initialize the module"""
        self._register_agents()
        return True

    def _register_agents(self):
        """Register all agents, including latent ones discovered on disk"""
        agent_types = [
            "search",
            "ranking",
            "synthesis",
            "research",
            "analysis",
            "answer",
            "reinforcement_learning",
            "research_reasoning",
            "query",
            "reranker",
            "retriever",
            "verifier",
        ]

        for agent_type in agent_types:
            try:
                agent = ModuleRegistry.get_module(f"{agent_type}_agent", auto_discover=True, wait_timeout=5.0)
                if agent:
                    self.agents[agent_type] = agent
                    logger.info(f"AgentCoordinator: Registered agent '{agent_type}'")
            except Exception as e:
                logger.debug(
                    f"AgentCoordinator: Optional agent '{agent_type}' unavailable",
                    exc_info=True,
                    extra={"module_name": "agent_coordinator", "dependency": f"{agent_type}_agent", "error_type": type(e).__name__},
                )

    def _extract_documents_from_results(self, previous_results: List[AgentResult]) -> List[Dict[str, Any]]:
        """Best-effort extraction of documents from prior agent outputs."""
        for r in reversed(previous_results):
            if r.agent_type not in {AgentType.SEARCH, AgentType.RANKING}:
                continue
            if isinstance(r.output, dict):
                docs = r.output.get("documents") or r.output.get("rankedDocuments") or r.output.get("ranked_documents")
                if isinstance(docs, list):
                    return docs
        return []

    def _extract_answer_from_results(self, previous_results: List[AgentResult]) -> str:
        """Best-effort extraction of answer text from prior outputs."""
        for r in reversed(previous_results):
            if r.agent_type not in {AgentType.SYNTHESIS, AgentType.ANSWER}:
                continue
            if isinstance(r.output, dict):
                ans = r.output.get("answer") or r.output.get("synthesis")
                if isinstance(ans, str):
                    return ans
        return ""

    def _normalize_agent_type(self, agent_type: Any) -> str:
        agent_type_str = agent_type
        if not isinstance(agent_type_str, str):
            if hasattr(agent_type_str, "value"):
                agent_type_str = agent_type_str.value
            else:
                agent_type_str = str(agent_type_str)
        if agent_type_str.endswith("_agent"):
            agent_type_str = agent_type_str[: -len("_agent")]
        return agent_type_str

    def _resolve_agent_profile(
        self,
        *,
        params: Dict[str, Any],
        task: AgentTask,
        agent_type: str,
    ) -> Optional[AgentProfile]:
        profile_name = params.get("agent_profile") or task.agent_profile or task.context.get("agent_profile")
        task_type = params.get("task_type") or task.context.get("task_type")
        return get_agent_profile_service().resolve_profile(
            profile_name=profile_name,
            task_type=task_type,
            agent_type=agent_type,
        )

    def _ensure_profile_allows(
        self,
        *,
        profile: Optional[AgentProfile],
        agent_type: str,
        operation: str,
    ) -> None:
        module_name = f"{agent_type}_agent"
        get_agent_profile_service().ensure_allowed(profile, module_name=module_name, operation=operation)

    def _build_profiled_params(
        self,
        params: Dict[str, Any],
        profile: Optional[AgentProfile],
    ) -> Dict[str, Any]:
        payload = dict(params)
        if profile is None:
            return payload
        payload["agent_profile"] = profile.name
        payload["profile_instructions"] = profile.system_instructions
        if profile.system_instructions and not payload.get("instructions"):
            payload["instructions"] = profile.system_instructions
        if profile.model_preference:
            payload["model"] = profile.model_preference
        return payload

    def _execute_agent(
        self,
        *,
        agent_type: str,
        agent: Any,
        task: AgentTask,
        context: Dict[str, Any],
        previous_results: List[AgentResult],
    ) -> Dict[str, Any]:
        """Dispatch to the correct agent operation based on agent_type."""
        query = task.query or ""
        profile: Optional[AgentProfile] = context.get("_resolved_agent_profile")

        if agent_type == AgentType.SEARCH:
            limit = context.get("limit", 10)
            sources = context.get("sources") or ["web", "memory"]
            return agent.execute(
                "search",
                self._build_profiled_params(
                    {"query": query, "limit": limit, "sources": sources},
                    profile,
                ),
            )

        documents = context.get("documents")
        if not isinstance(documents, list):
            documents = self._extract_documents_from_results(previous_results)

        if agent_type == AgentType.RANKING:
            return agent.execute(
                "rank",
                self._build_profiled_params(
                    {"query": query, "documents": documents},
                    profile,
                ),
            )

        if agent_type == AgentType.SYNTHESIS:
            return agent.execute(
                "synthesize",
                self._build_profiled_params(
                    {"query": query, "documents": documents, "persona": context.get("persona", "oricli")},
                    profile,
                ),
            )

        if agent_type == AgentType.RESEARCH:
            return agent.execute(
                "research",
                self._build_profiled_params(
                    {"query": query, "max_passes": context.get("max_passes", 3), "limit": context.get("limit", 10)},
                    profile,
                ),
            )

        if agent_type == AgentType.ANALYSIS:
            return agent.execute(
                "analyze",
                self._build_profiled_params(
                    {"query": query, "documents": documents},
                    profile,
                ),
            )

        if agent_type == AgentType.ANSWER:
            raw_answer = context.get("answer")
            if not isinstance(raw_answer, str) or not raw_answer:
                raw_answer = self._extract_answer_from_results(previous_results)
            return agent.execute(
                "format_answer",
                self._build_profiled_params(
                    {"query": query, "answer": raw_answer, "documents": documents},
                    profile,
                ),
            )

        raise InvalidParameterError("agent_type", agent_type, "Unknown agent_type for execution")

    def execute(self, operation: str, params: Dict[str, Any]) -> Dict[str, Any]:
        """Execute an operation"""
        if operation == "status":
            return self._get_status()

        if operation == "execute_task":
            return self._execute_task(params)
        elif operation == "execute_parallel":
            return self._execute_parallel(params)
        elif operation == "get_result":
            return self._get_result(params)
        elif operation == "get_all_results":
            return self._get_all_results()
        elif operation == "spawn_agent":
            return self._spawn_agent(params)
        else:
            return {"success": False, "error": f"Unknown operation: {operation}"}

    def _spawn_agent(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Spawn an ephemeral agent for a specific task."""
        agent_type = params.get("agent_type")
        instructions = params.get("instructions")
        
        if not agent_type:
            return {"success": False, "error": "agent_type required"}

        normalized_agent_type = self._normalize_agent_type(agent_type)
        profile = get_agent_profile_service().resolve_profile(
            profile_name=params.get("agent_profile"),
            task_type=params.get("task_type"),
            agent_type=normalized_agent_type,
        )

        resolved_instructions = instructions
        if profile and profile.system_instructions:
            resolved_instructions = (
                f"{profile.system_instructions}\n\n{instructions}".strip()
                if instructions
                else profile.system_instructions
            )
            
        # For now, we simulate spawning by returning a virtual agent ID
        # In a real implementation, this would create a new instance of BaseBrainModule
        agent_id = f"ephemeral_{agent_type}_{int(time.time())}"
        logger.info(f"AgentCoordinator: Spawned ephemeral agent '{agent_id}'")
        
        return {
            "success": True, 
            "agent_id": agent_id,
            "instructions": resolved_instructions,
            "agent_profile": profile.name if profile else None,
            "model": profile.model_preference if profile else None,
        }

    def _get_status(self) -> Dict[str, Any]:
        """Return module status"""
        return {
            "success": True,
            "status": "active",
            "version": self.metadata.version,
            "registered_agents_count": len(self.agents),
            "registered_agents": list(self.agents.keys()),
            "results_cache_size": len(self.results)
        }

    def _execute_task(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Execute a single task"""
        task_data = params.get("task", {})
        previous_results_data = params.get("previous_results", [])

        # Handle task_data - can be dict, AgentTask instance, or string
        if isinstance(task_data, dict):
            task = AgentTask.from_dict(task_data)
        elif isinstance(task_data, str):
            # String task - create a basic task
            task = AgentTask(
                task_id="test_task",
                agent_type=AgentType.SEARCH,
                query=task_data,
                context=params.get("context", {}),
                dependencies=[],
                priority=0,
            )
        elif hasattr(task_data, 'agent_type'):
            # Already an AgentTask instance
            task = task_data
        else:
            # Fallback: create minimal task
            task = AgentTask(
                task_id="test_task",
                agent_type=AgentType.SEARCH,
                query=str(task_data),
                context=params.get("context", {}),
                dependencies=[],
                priority=0,
            )
        
        previous_results = [
            AgentResult(
                task_id=r.get("task_id", ""),
                agent_type=r.get("agent_type", ""),
                success=r.get("success", False),
                output=r.get("output", ""),
                error=r.get("error"),
            )
            for r in previous_results_data
        ]

        agent_type_str = self._normalize_agent_type(task.agent_type)
        profile = self._resolve_agent_profile(params=params, task=task, agent_type=agent_type_str)
        operation_by_agent_type = {
            AgentType.SEARCH: "search",
            AgentType.RANKING: "rank",
            AgentType.SYNTHESIS: "synthesize",
            AgentType.RESEARCH: "research",
            AgentType.ANALYSIS: "analyze",
            AgentType.ANSWER: "format_answer",
        }
        requested_operation = operation_by_agent_type.get(agent_type_str)
        if requested_operation:
            try:
                self._ensure_profile_allows(
                    profile=profile,
                    agent_type=agent_type_str,
                    operation=requested_operation,
                )
            except Exception as e:
                result = AgentResult(
                    task_id=task.id,
                    agent_type=agent_type_str,
                    success=False,
                    output="",
                    error=str(e),
                )
                self.results[task.id] = result
                return {
                    "success": False,
                    "result": result.to_dict(),
                }
        
        agent = self.agents.get(agent_type_str)
        if not agent:
            result = AgentResult(
                task_id=task.id,
                agent_type=agent_type_str,
                success=False,
                output="",
                error=f"Agent not found: {agent_type_str}",
            )
            self.results[task.id] = result
            return {
                "success": False,
                "result": result.to_dict(),
            }

        # Build context with previous results
        context = task.context.copy()
        if previous_results:
            context["previous_results"] = [r.to_dict() for r in previous_results]
        if profile:
            context["_resolved_agent_profile"] = profile
            context["agent_profile"] = profile.name
            context["profile_instructions"] = profile.system_instructions
            if profile.model_preference:
                context["model"] = profile.model_preference

        # Execute with retries
        max_retries = 3
        last_error = None

        for attempt in range(max_retries + 1):
            try:
                result_data = self._execute_agent(
                    agent_type=agent_type_str,
                    agent=agent,
                    task=task,
                    context=context,
                    previous_results=previous_results,
                )

                result = AgentResult(
                    task_id=task.id,
                    agent_type=agent_type_str,
                    success=result_data.get("success", False),
                    output=result_data,
                    error=result_data.get("error"),
                )

                self.results[task.id] = result
                return {
                    "success": True,
                    "result": result.to_dict(),
                }
            except Exception as e:
                last_error = e
                if attempt < max_retries:
                    # Exponential backoff
                    time.sleep(2 ** attempt)

        # All retries failed
        result = AgentResult(
            task_id=task.id,
            agent_type=agent_type_str,
            success=False,
            output="",
            error=str(last_error) if last_error else "Unknown error",
        )

        self.results[task.id] = result
        return {
            "success": False,
            "result": result.to_dict(),
        }

    def _execute_parallel(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Execute tasks in parallel"""
        tasks_data = params.get("tasks", [])
        previous_results_data = params.get("previous_results", [])

        tasks = [
            AgentTask.from_dict(t) if isinstance(t, dict) else t
            for t in tasks_data
        ]

        # Execute tasks sequentially (simplified - would use threading in real implementation)
        results: List[AgentResult] = []
        for task in tasks:
            result_data = self._execute_task({
                "task": task.to_dict(),
                "previous_results": previous_results_data,
                "agent_profile": getattr(task, "agent_profile", None) or params.get("agent_profile"),
                "task_type": params.get("task_type"),
            })
            result = AgentResult(
                task_id=result_data["result"]["task_id"],
                agent_type=result_data["result"]["agent_type"],
                success=result_data["result"]["success"],
                output=result_data["result"]["output"],
                error=result_data["result"].get("error"),
            )
            results.append(result)

        return {
            "success": True,
            "result": {
                "results": [r.to_dict() for r in results],
                "count": len(results),
            },
        }

    def _get_result(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Get result for a task"""
        task_id = params.get("task_id")

        result = self.results.get(task_id)
        if not result:
            return {
                "success": False,
                "error": f"Result not found for task {task_id}",
            }

        return {
            "success": True,
            "result": result.to_dict(),
        }

    def _get_all_results(self) -> Dict[str, Any]:
        """Get all results"""
        return {
            "success": True,
            "result": {
                "results": [r.to_dict() for r in self.results.values()],
                "count": len(self.results),
            },
        }

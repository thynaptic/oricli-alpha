from __future__ import annotations
"""
Swarm Node Module
Manages individual node execution and peer review in collaborative swarm runs.
"""

from typing import Any, Dict, List, Optional

from oricli_core.brain.base_module import BaseBrainModule, ModuleMetadata
from oricli_core.brain.registry import ModuleRegistry
from oricli_core.exceptions import InvalidParameterError


class SwarmNodeModule(BaseBrainModule):
    """Module for managing individual swarm node execution."""

    def __init__(self) -> None:
        super().__init__()
        self.agent_coordinator = None

    @property
    def metadata(self) -> ModuleMetadata:
        return ModuleMetadata(
            name="swarm_node",
            version="1.1.0",
            description="Manages individual swarm node execution and collaborative peer review",
            operations=["status", "process_subtask", "review_peer_output"],
            dependencies=[],
            model_required=False,
        )

    def initialize(self) -> bool:
        return True

    def _ensure_agent_coordinator(self) -> None:
        if self.agent_coordinator is None:
            self.agent_coordinator = ModuleRegistry.get_module(
                "agent_coordinator",
                auto_discover=True,
                wait_timeout=1.0,
            )

    def execute(self, operation: str, params: Dict[str, Any]) -> Dict[str, Any]:
        if operation == "status":
            self._ensure_agent_coordinator()
            return {
                "success": True,
                "status": "active",
                "agent_coordinator_available": self.agent_coordinator is not None,
            }
        if operation == "process_subtask":
            return self._process_subtask(params)
        if operation == "review_peer_output":
            return self._review_peer_output(params)
        return {"success": False, "error": f"Unknown operation: {operation}"}

    def _extract_contribution(self, output: Any) -> str:
        if isinstance(output, str):
            return output.strip()
        if isinstance(output, dict):
            for key in ("answer", "synthesis", "text", "summary"):
                value = output.get(key)
                if isinstance(value, str) and value.strip():
                    return value.strip()
            documents = output.get("documents") or output.get("ranked_documents") or output.get("rankedDocuments")
            if isinstance(documents, list) and documents:
                titles = [
                    str(doc.get("title") or doc.get("name") or doc.get("id") or "document").strip()
                    for doc in documents
                    if isinstance(doc, dict)
                ]
                joined = ", ".join(title for title in titles if title)
                if joined:
                    return f"Documents considered: {joined}"
        return ""

    def _build_message(
        self,
        *,
        round_index: int,
        node_id: str,
        agent_type: str,
        content: str,
        message_kind: str,
        target_node_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        message = {
            "round": round_index,
            "node_id": node_id,
            "agent_type": agent_type,
            "kind": message_kind,
            "content": content,
        }
        if target_node_id:
            message["target_node_id"] = target_node_id
        return message

    def _process_subtask(self, params: Dict[str, Any]) -> Dict[str, Any]:
        self._ensure_agent_coordinator()
        if self.agent_coordinator is None:
            return {"success": False, "error": "agent_coordinator unavailable"}

        query = params.get("query") or params.get("input")
        agent_type = params.get("agent_type")
        if not query:
            raise InvalidParameterError("query", query, "query is required")
        if not agent_type:
            raise InvalidParameterError("agent_type", agent_type, "agent_type is required")

        round_index = int(params.get("round_index", 0))
        node_id = str(params.get("node_id") or f"{agent_type}_node_{round_index}")
        shared_state = dict(params.get("shared_state") or {})
        message_log = list(params.get("message_log") or [])
        context = dict(params.get("context") or {})
        context["collaborative"] = True
        context["shared_state"] = shared_state
        context["message_log"] = message_log
        context["node_id"] = node_id
        context["round_index"] = round_index

        task = {
            "id": params.get("task_id") or f"{node_id}_task",
            "agent_type": agent_type,
            "query": query,
            "context": context,
            "dependencies": params.get("dependencies", []),
            "priority": int(params.get("priority", 0)),
            "agent_profile": params.get("agent_profile"),
        }

        result = self.agent_coordinator.execute(
            "execute_task",
            {
                "task": task,
                "previous_results": params.get("previous_results", []),
                "agent_profile": params.get("agent_profile"),
                "task_type": params.get("task_type"),
            },
        )
        task_result = result.get("result", {})
        contribution = self._extract_contribution(task_result.get("output"))
        message = self._build_message(
            round_index=round_index,
            node_id=node_id,
            agent_type=str(agent_type),
            content=contribution or task_result.get("error", ""),
            message_kind="contribution",
        )

        return {
            "success": bool(result.get("success")),
            "node_id": node_id,
            "agent_type": str(agent_type),
            "task_result": task_result,
            "contribution": contribution,
            "message": message,
            "shared_state_delta": {"last_contribution": contribution, "last_contributor": node_id},
        }

    def _review_peer_output(self, params: Dict[str, Any]) -> Dict[str, Any]:
        reviewer_agent_type = str(params.get("reviewer_agent_type") or params.get("agent_type") or "reviewer")
        reviewer_node_id = str(params.get("reviewer_node_id") or params.get("node_id") or reviewer_agent_type)
        target = dict(params.get("target_contribution") or {})
        query = str(params.get("query") or "").strip()
        round_index = int(params.get("round_index", 0))

        target_node_id = str(target.get("node_id") or "unknown")
        contribution_text = str(target.get("contribution") or target.get("content") or "").strip()
        issues: List[str] = []

        if not contribution_text:
            issues.append("No contribution content was produced.")
        if target.get("success") is False:
            issues.append("Target node failed to produce a successful result.")
        if contribution_text and len(contribution_text) < 16:
            issues.append("Contribution is too short to support a strong final answer.")

        if query and contribution_text:
            query_terms = {term for term in query.lower().split() if len(term) > 3}
            if query_terms and not any(term in contribution_text.lower() for term in query_terms):
                issues.append("Contribution has weak lexical overlap with the requested query.")

        approval = not issues
        confidence = 0.85 if approval else 0.35
        summary = "Contribution approved for consensus." if approval else "; ".join(issues)

        review = {
            "reviewer_node_id": reviewer_node_id,
            "reviewer_agent_type": reviewer_agent_type,
            "target_node_id": target_node_id,
            "approval": approval,
            "issues": issues,
            "confidence": confidence,
            "summary": summary,
        }
        message = self._build_message(
            round_index=round_index,
            node_id=reviewer_node_id,
            agent_type=reviewer_agent_type,
            content=summary,
            message_kind="review",
            target_node_id=target_node_id,
        )
        return {"success": True, "review": review, "message": message}

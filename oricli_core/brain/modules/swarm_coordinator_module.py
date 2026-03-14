from __future__ import annotations
"""
Swarm Coordinator Module
Coordinates distributed intelligence across multiple nodes before producing a final answer.
"""

import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Any, Dict, List, Optional

from oricli_core.brain.base_module import BaseBrainModule, ModuleMetadata
from oricli_core.brain.registry import ModuleRegistry
from oricli_core.exceptions import InvalidParameterError
from oricli_core.services.swarm_blackboard_service import (
    SwarmBlackboardService,
    get_swarm_blackboard_service,
)


class SwarmCoordinatorModule(BaseBrainModule):
    """Module for coordinating collaborative swarm intelligence."""

    def __init__(self) -> None:
        super().__init__()
        self.swarm_node = None
        self.swarm_consensus = None
        self.blackboard_service: Optional[SwarmBlackboardService] = None
        self._modules_loaded = False

    @property
    def metadata(self) -> ModuleMetadata:
        return ModuleMetadata(
            name="swarm_coordinator",
            version="1.2.0",
            description="Coordinates distributed intelligence with shared state, persistence, peer review, and consensus",
            operations=["status", "coordinate_task", "gather_consensus"],
            dependencies=[],
            model_required=False,
        )

    def initialize(self) -> bool:
        return True

    def _ensure_modules_loaded(self) -> None:
        if self._modules_loaded:
            return
        self.swarm_node = ModuleRegistry.get_module("swarm_node", auto_discover=True, wait_timeout=1.0)
        self.swarm_consensus = ModuleRegistry.get_module("swarm_consensus", auto_discover=True, wait_timeout=1.0)
        if self.blackboard_service is None:
            self.blackboard_service = get_swarm_blackboard_service()
        self._modules_loaded = True

    def execute(self, operation: str, params: Dict[str, Any]) -> Dict[str, Any]:
        self._ensure_modules_loaded()
        if operation == "status":
            return {
                "success": True,
                "status": "active",
                "swarm_node_available": self.swarm_node is not None,
                "swarm_consensus_available": self.swarm_consensus is not None,
                "blackboard_persistence_available": self.blackboard_service is not None,
            }
        if operation == "coordinate_task":
            return self._coordinate_task(params)
        if operation == "gather_consensus":
            return self._gather_consensus(params)
        return {"success": False, "error": f"Unknown operation: {operation}"}

    def _normalize_participants(self, params: Dict[str, Any]) -> List[Dict[str, Any]]:
        participants = params.get("participants")
        if participants:
            normalized: List[Dict[str, Any]] = []
            for index, participant in enumerate(participants):
                if isinstance(participant, str):
                    normalized.append({"agent_type": participant, "node_id": f"{participant}_{index}"})
                elif isinstance(participant, dict):
                    data = dict(participant)
                    data.setdefault("node_id", f"{data.get('agent_type', 'agent')}_{index}")
                    normalized.append(data)
            return normalized

        agent_types = list(params.get("agent_types") or ["search", "synthesis", "answer"])
        return [{"agent_type": agent_type, "node_id": f"{agent_type}_{index}"} for index, agent_type in enumerate(agent_types)]

    def _merge_shared_state(
        self,
        shared_state: Dict[str, Any],
        delta: Dict[str, Any],
        *,
        lock: threading.Lock,
    ) -> None:
        with lock:
            for key, value in delta.items():
                existing = shared_state.get(key)
                if isinstance(existing, list) and isinstance(value, list):
                    existing.extend(value)
                elif isinstance(existing, dict) and isinstance(value, dict):
                    existing.update(value)
                else:
                    shared_state[key] = value

    def _initialize_blackboard(
        self,
        *,
        session_id: Optional[str],
        query: str,
        participants: List[Dict[str, Any]],
        params: Dict[str, Any],
    ) -> Dict[str, Any]:
        if self.blackboard_service is None:
            raise RuntimeError("swarm blackboard service unavailable")

        shared_state = dict(params.get("shared_state") or {})
        shared_state.setdefault("query", query)
        shared_state.setdefault("contributions", [])
        message_log = list(params.get("message_log") or [])

        if session_id:
            existing = self.blackboard_service.load_session(session_id)
            if existing is not None:
                return existing

        return self.blackboard_service.create_session(
            session_id=session_id,
            query=query,
            participants=participants,
            shared_state=shared_state,
            message_log=message_log,
            metadata={
                "agent_profile": params.get("agent_profile"),
                "task_type": params.get("task_type"),
            },
        )

    def _run_round_participant(
        self,
        *,
        participant: Dict[str, Any],
        round_index: int,
        query: str,
        params: Dict[str, Any],
        shared_state_snapshot: Dict[str, Any],
        message_log_snapshot: List[Dict[str, Any]],
        previous_results_snapshot: List[Dict[str, Any]],
    ) -> Dict[str, Any]:
        participant_context = dict(participant.get("context") or {})
        participant_context["shared_state"] = shared_state_snapshot
        participant_context["message_log"] = message_log_snapshot

        return self.swarm_node.execute(
            "process_subtask",
            {
                "node_id": participant["node_id"],
                "task_id": f"{participant['node_id']}_round_{round_index}",
                "agent_type": participant.get("agent_type"),
                "agent_profile": participant.get("agent_profile") or params.get("agent_profile"),
                "task_type": participant.get("task_type") or params.get("task_type"),
                "query": participant.get("query") or query,
                "context": participant_context,
                "shared_state": shared_state_snapshot,
                "message_log": message_log_snapshot,
                "previous_results": previous_results_snapshot,
                "round_index": round_index,
            },
        )

    def _coordinate_task(self, params: Dict[str, Any]) -> Dict[str, Any]:
        if self.swarm_node is None or self.swarm_consensus is None or self.blackboard_service is None:
            return {"success": False, "error": "swarm modules unavailable"}

        query = params.get("query") or params.get("input")
        if not query:
            raise InvalidParameterError("query", query, "query is required")

        participants = self._normalize_participants(params)
        round_limit = max(1, int(params.get("round_limit", 1)))
        peer_review = bool(params.get("peer_review", True))
        async_execution = bool(params.get("async_execution", False))
        session = self._initialize_blackboard(
            session_id=params.get("session_id"),
            query=query,
            participants=participants,
            params=params,
        )
        session_id = str(session["session_id"])
        shared_state = dict(session.get("shared_state") or {})
        shared_state.setdefault("query", query)
        shared_state.setdefault("contributions", [])
        message_log = list(session.get("message_log") or [])
        contributions: List[Dict[str, Any]] = list(session.get("contributions") or [])
        reviews: List[Dict[str, Any]] = list(session.get("reviews") or [])
        previous_results: List[Dict[str, Any]] = [
            contribution["task_result"]
            for contribution in contributions
            if isinstance(contribution, dict) and contribution.get("task_result")
        ]
        rounds: List[Dict[str, Any]] = []
        merge_lock = threading.Lock()

        for round_index in range(round_limit):
            round_entries: List[Dict[str, Any]] = []
            shared_state_snapshot = dict(shared_state)
            message_log_snapshot = list(message_log)
            previous_results_snapshot = list(previous_results)
            if async_execution and len(participants) > 1:
                max_workers = min(len(participants), int(params.get("max_workers", len(participants))))
                with ThreadPoolExecutor(max_workers=max_workers) as executor:
                    futures = [
                        executor.submit(
                            self._run_round_participant,
                            participant=participant,
                            round_index=round_index,
                            query=query,
                            params=params,
                            shared_state_snapshot=shared_state_snapshot,
                            message_log_snapshot=message_log_snapshot,
                            previous_results_snapshot=previous_results_snapshot,
                        )
                        for participant in participants
                    ]
                    for future in as_completed(futures):
                        round_entries.append(future.result())
            else:
                for participant in participants:
                    round_entries.append(
                        self._run_round_participant(
                            participant=participant,
                            round_index=round_index,
                            query=query,
                            params=params,
                            shared_state_snapshot=shared_state_snapshot,
                            message_log_snapshot=message_log_snapshot,
                            previous_results_snapshot=previous_results_snapshot,
                        )
                    )

            round_entries.sort(key=lambda entry: str(entry.get("node_id")))
            for node_result in round_entries:
                contributions.append(node_result)
                if node_result.get("task_result"):
                    previous_results.append(node_result["task_result"])
                if node_result.get("message"):
                    message_log.append(node_result["message"])
                shared_state["contributions"].append(
                    {
                        "node_id": node_result.get("node_id"),
                        "agent_type": node_result.get("agent_type"),
                        "contribution": node_result.get("contribution"),
                    }
                )
                delta = node_result.get("shared_state_delta")
                if isinstance(delta, dict):
                    self._merge_shared_state(shared_state, delta, lock=merge_lock)

            round_reviews: List[Dict[str, Any]] = []
            if peer_review and len(round_entries) > 1:
                for reviewer in round_entries:
                    for target in round_entries:
                        if reviewer.get("node_id") == target.get("node_id"):
                            continue
                        review_result = self.swarm_node.execute(
                            "review_peer_output",
                            {
                                "round_index": round_index,
                                "reviewer_node_id": reviewer.get("node_id"),
                                "reviewer_agent_type": reviewer.get("agent_type"),
                                "target_contribution": target,
                                "query": query,
                            },
                        )
                        if review_result.get("review"):
                            round_reviews.append(review_result["review"])
                            reviews.append(review_result["review"])
                        if review_result.get("message"):
                            message_log.append(review_result["message"])

            rounds.append(
                {
                    "round": round_index,
                    "contributions": round_entries,
                    "reviews": round_reviews,
                    "async_execution": async_execution,
                }
            )
            self.blackboard_service.save_round(
                session_id,
                round_data=rounds[-1],
                shared_state=shared_state,
                message_log=message_log,
                contributions=contributions,
                reviews=reviews,
            )

        consensus = self.swarm_consensus.execute(
            "evaluate_consensus",
            {
                "query": query,
                "contributions": contributions,
                "reviews": reviews,
                "shared_state": shared_state,
                "consensus_policy": params.get("consensus_policy", "weighted_vote"),
                "verifier_agent_types": params.get("verifier_agent_types"),
            },
        )
        self.blackboard_service.finalize_session(
            session_id,
            final_consensus=consensus,
            shared_state=shared_state,
            message_log=message_log,
            contributions=contributions,
            reviews=reviews,
        )
        return {
            "success": bool(consensus.get("success")),
            "session_id": session_id,
            "query": query,
            "answer": consensus.get("answer", ""),
            "consensus": consensus,
            "participants": participants,
            "message_log": message_log,
            "shared_state": shared_state,
            "contributions": contributions,
            "reviews": reviews,
            "rounds": rounds,
        }

    def _gather_consensus(self, params: Dict[str, Any]) -> Dict[str, Any]:
        if self.swarm_consensus is None:
            return {"success": False, "error": "swarm_consensus unavailable"}
        return self.swarm_consensus.execute("evaluate_consensus", params)

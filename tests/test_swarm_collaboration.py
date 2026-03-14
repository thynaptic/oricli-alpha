from __future__ import annotations

import threading
import time
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

from oricli_core.brain.modules.swarm_consensus_module import SwarmConsensusModule
from oricli_core.brain.modules.swarm_coordinator_module import SwarmCoordinatorModule
from oricli_core.brain.modules.swarm_node_module import SwarmNodeModule
from oricli_core.services.swarm_blackboard_service import SwarmBlackboardService


class FakeAgentCoordinator:
    def __init__(self):
        self.calls = []

    def execute(self, operation, params):
        self.calls.append((operation, params))
        task = params["task"]
        agent_type = task["agent_type"]
        query = task["query"]
        if agent_type == "search":
            output = {"documents": [{"title": "Spec"}, {"title": "Benchmark"}]}
        elif agent_type == "synthesis":
            output = {"synthesis": f"Synthesis for {query}"}
        else:
            output = {"answer": f"Answer for {query}"}
        return {
            "success": True,
            "result": {
                "task_id": task["id"],
                "agent_type": agent_type,
                "success": True,
                "output": output,
                "error": None,
            },
        }


def test_swarm_node_process_subtask_uses_shared_context():
    node = SwarmNodeModule()
    node.agent_coordinator = FakeAgentCoordinator()

    result = node.execute(
        "process_subtask",
        {
            "node_id": "search_1",
            "agent_type": "search",
            "query": "distributed reasoning",
            "shared_state": {"topic": "agents"},
            "message_log": [{"kind": "seed", "content": "start"}],
            "context": {"limit": 2},
            "agent_profile": "research_agent_profile",
        },
    )

    assert result["success"] is True
    assert result["node_id"] == "search_1"
    assert "Documents considered" in result["contribution"]
    sent_task = node.agent_coordinator.calls[0][1]["task"]
    assert sent_task["context"]["shared_state"]["topic"] == "agents"
    assert sent_task["agent_profile"] == "research_agent_profile"


def test_swarm_consensus_prefers_reviewed_contribution():
    consensus = SwarmConsensusModule()

    result = consensus.execute(
        "evaluate_consensus",
        {
            "contributions": [
                {"node_id": "a", "agent_type": "analysis", "success": True, "contribution": "Weak"},
                {"node_id": "b", "agent_type": "synthesis", "success": True, "contribution": "Much stronger final synthesis answer"},
            ],
            "reviews": [
                {"target_node_id": "a", "approval": False, "issues": ["too short"], "confidence": 0.8},
                {"target_node_id": "b", "approval": True, "issues": [], "confidence": 0.9},
            ],
        },
    )

    assert result["success"] is True
    assert result["selected_node_id"] == "b"
    assert "stronger final synthesis answer" in result["answer"]


def test_swarm_consensus_verifier_wins_policy():
    consensus = SwarmConsensusModule()

    result = consensus.execute(
        "evaluate_consensus",
        {
            "contributions": [
                {"node_id": "a", "agent_type": "analysis", "success": True, "contribution": "Long but disputed answer"},
                {"node_id": "b", "agent_type": "synthesis", "success": True, "contribution": "Verifier-backed answer"},
            ],
            "reviews": [
                {"target_node_id": "a", "approval": True, "issues": [], "confidence": 0.9, "reviewer_agent_type": "peer"},
                {"target_node_id": "b", "approval": True, "issues": [], "confidence": 0.6, "reviewer_agent_type": "verifier"},
            ],
            "consensus_policy": "verifier_wins",
            "verifier_agent_types": ["verifier"],
        },
    )

    assert result["success"] is True
    assert result["selected_node_id"] == "b"
    assert result["policy"] == "verifier_wins"
    assert result["conflicts_detected"] is False


class FakeSwarmNode:
    def __init__(self):
        self.calls = []

    def execute(self, operation, params):
        self.calls.append((operation, dict(params)))
        if operation == "process_subtask":
            contribution = f"{params['agent_type']} contribution for {params['query']}"
            return {
                "success": True,
                "node_id": params["node_id"],
                "agent_type": params["agent_type"],
                "contribution": contribution,
                "task_result": {
                    "task_id": params["task_id"],
                    "agent_type": params["agent_type"],
                    "success": True,
                    "output": {"answer": contribution},
                    "error": None,
                },
                "message": {"kind": "contribution", "node_id": params["node_id"], "content": contribution},
                "shared_state_delta": {"last_contributor": params["node_id"]},
            }
        if operation == "review_peer_output":
            target = params["target_contribution"]
            return {
                "success": True,
                "review": {
                    "reviewer_node_id": params["reviewer_node_id"],
                    "target_node_id": target["node_id"],
                    "approval": True,
                    "issues": [],
                    "confidence": 0.75,
                    "summary": "Looks good.",
                },
                "message": {"kind": "review", "node_id": params["reviewer_node_id"], "content": "Looks good."},
            }
        raise AssertionError(f"Unexpected operation: {operation}")


def test_swarm_coordinator_runs_collaborative_rounds(tmp_path):
    coordinator = SwarmCoordinatorModule()
    coordinator.swarm_node = FakeSwarmNode()
    coordinator.swarm_consensus = SwarmConsensusModule()
    coordinator.blackboard_service = SwarmBlackboardService(sessions_dir=tmp_path / "swarm_sessions")
    coordinator._modules_loaded = True

    result = coordinator.execute(
        "coordinate_task",
        {
            "query": "How do agents collaborate?",
            "participants": [
                {"agent_type": "analysis", "node_id": "analysis_1"},
                {"agent_type": "synthesis", "node_id": "synthesis_1"},
            ],
            "round_limit": 1,
            "peer_review": True,
        },
    )

    assert result["success"] is True
    assert result["session_id"]
    assert len(result["contributions"]) == 2
    assert len(result["reviews"]) == 2
    assert result["message_log"]
    assert result["shared_state"]["last_contributor"] in {"analysis_1", "synthesis_1"}
    assert "contribution for How do agents collaborate?" in result["answer"]


class FakeAsyncSwarmNode:
    def __init__(self):
        self._lock = threading.Lock()
        self.inflight = 0
        self.max_inflight = 0

    def execute(self, operation, params):
        if operation == "process_subtask":
            with self._lock:
                self.inflight += 1
                self.max_inflight = max(self.max_inflight, self.inflight)
            time.sleep(0.05)
            with self._lock:
                self.inflight -= 1
            contribution = f"{params['agent_type']} async contribution"
            return {
                "success": True,
                "node_id": params["node_id"],
                "agent_type": params["agent_type"],
                "contribution": contribution,
                "task_result": {
                    "task_id": params["task_id"],
                    "agent_type": params["agent_type"],
                    "success": True,
                    "output": {"answer": contribution},
                    "error": None,
                },
                "message": {"kind": "contribution", "node_id": params["node_id"], "content": contribution},
                "shared_state_delta": {"contributors": [params["node_id"]]},
            }
        if operation == "review_peer_output":
            target = params["target_contribution"]
            return {
                "success": True,
                "review": {
                    "reviewer_node_id": params["reviewer_node_id"],
                    "reviewer_agent_type": params.get("reviewer_agent_type"),
                    "target_node_id": target["node_id"],
                    "approval": True,
                    "issues": [],
                    "confidence": 0.5,
                    "summary": "ok",
                },
                "message": {"kind": "review", "node_id": params["reviewer_node_id"], "content": "ok"},
            }
        raise AssertionError(f"Unexpected operation: {operation}")


def test_swarm_coordinator_async_execution_and_persistence(tmp_path):
    sessions_dir = tmp_path / "swarm_sessions"
    blackboard = SwarmBlackboardService(sessions_dir=sessions_dir)
    fake_node = FakeAsyncSwarmNode()

    coordinator = SwarmCoordinatorModule()
    coordinator.swarm_node = fake_node
    coordinator.swarm_consensus = SwarmConsensusModule()
    coordinator.blackboard_service = blackboard
    coordinator._modules_loaded = True

    result = coordinator.execute(
        "coordinate_task",
        {
            "query": "async swarm test",
            "participants": [
                {"agent_type": "analysis", "node_id": "analysis_1"},
                {"agent_type": "synthesis", "node_id": "synthesis_1"},
                {"agent_type": "answer", "node_id": "answer_1"},
            ],
            "round_limit": 1,
            "peer_review": False,
            "async_execution": True,
        },
    )

    assert result["success"] is True
    assert fake_node.max_inflight >= 2
    persisted = blackboard.load_session(result["session_id"])
    assert persisted is not None
    assert persisted["status"] == "completed"
    assert len(persisted["contributions"]) == 3
    assert persisted["final_consensus"]["selected_node_id"]

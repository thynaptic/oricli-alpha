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


class FakeSkillManager:
    def __init__(self):
        self.calls = []
        self.skills = {
            "senior_python_dev": {
                "skill_name": "senior_python_dev",
                "description": "Expert Python software engineering and architecture design.",
                "triggers": ["python", "refactor", "architecture"],
                "requires_tools": ["python_codebase_search"],
                "mindset": "You think like a senior Python engineer.",
                "instructions": "Always preserve readability and add tests.",
            },
            "technical_writer": {
                "skill_name": "technical_writer",
                "description": "Expert technical documentation writing.",
                "triggers": ["document this", "readme", "tutorial"],
                "requires_tools": ["python_documentation_generator"],
                "mindset": "You optimize for clarity and audience empathy.",
                "instructions": "Use headings and copy-pasteable examples.",
            },
        }

    def execute(self, operation, params):
        self.calls.append((operation, dict(params)))
        if operation == "get_skill":
            skill = self.skills.get(params.get("skill_name"))
            if skill is None:
                return {"success": False, "error": "Skill not found"}
            return {"success": True, "skill": dict(skill)}
        if operation == "match_skills":
            query = str(params.get("query") or "").lower()
            matches = []
            for skill in self.skills.values():
                if any(trigger.lower() in query for trigger in skill["triggers"]):
                    matches.append(dict(skill))
            return {"success": True, "matches": matches}
        raise AssertionError(f"Unexpected operation: {operation}")


def test_swarm_node_process_subtask_uses_shared_context():
    node = SwarmNodeModule()
    node.agent_coordinator = FakeAgentCoordinator()
    node.skill_manager = FakeSkillManager()

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
            "skill_name": "technical_writer",
        },
    )

    assert result["success"] is True
    assert result["node_id"] == "search_1"
    assert "Documents considered" in result["contribution"]
    assert result["selected_skill"]["skill_name"] == "technical_writer"
    assert result["instruction_layers"]["skill_mindset"] == "You optimize for clarity and audience empathy."
    sent_task = node.agent_coordinator.calls[0][1]["task"]
    assert sent_task["context"]["shared_state"]["topic"] == "agents"
    assert sent_task["agent_profile"] == "research_agent_profile"
    assert sent_task["context"]["selected_skill"]["skill_name"] == "technical_writer"
    assert "Skill instructions (technical_writer)" in sent_task["context"]["instructions"]


def test_swarm_node_process_subtask_auto_matches_skill():
    node = SwarmNodeModule()
    node.agent_coordinator = FakeAgentCoordinator()
    node.skill_manager = FakeSkillManager()

    result = node.execute(
        "process_subtask",
        {
            "node_id": "analysis_1",
            "agent_type": "analysis",
            "query": "refactor this python architecture for better clarity",
            "agent_profile": "code_agent_profile",
        },
    )

    assert result["success"] is True
    assert result["selected_skill"]["skill_name"] == "senior_python_dev"
    assert result["selected_skill"]["match_strategy"] == "query_match"
    assert "python" in result["selected_skill"]["matched_triggers"]


def test_swarm_node_estimate_bid_returns_scored_bid():
    node = SwarmNodeModule()
    node.skill_manager = FakeSkillManager()

    baseline = node.execute(
        "estimate_bid",
        {
            "node_id": "analysis_1",
            "agent_type": "analysis",
            "query": "debug a benchmark failure",
            "task_type": "debug",
            "priority": 2,
        },
    )
    skilled = node.execute(
        "estimate_bid",
        {
            "node_id": "analysis_1",
            "agent_type": "analysis",
            "query": "debug and refactor this python benchmark failure",
            "task_type": "debug",
            "priority": 2,
            "skill_name": "senior_python_dev",
        },
    )

    assert baseline["success"] is True
    assert skilled["success"] is True
    assert skilled["bid"]["node_id"] == "analysis_1"
    assert skilled["bid"]["utility_score"] > baseline["bid"]["utility_score"]
    assert skilled["bid"]["specialization_match"] > baseline["bid"]["specialization_match"]
    assert skilled["bid"]["selected_skill"]["skill_name"] == "senior_python_dev"


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
        if operation == "estimate_bid":
            return {
                "success": True,
                "bid": {
                    "node_id": params["node_id"],
                    "agent_type": params["agent_type"],
                    "utility_score": 0.75,
                    "estimated_confidence": 0.75,
                    "estimated_cost": 0.10,
                    "specialization_match": 0.20,
                    "priority": 0,
                    "rationale": "default test bid",
                },
            }
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
    assert result["bids"]
    assert len(result["participants"]) == 2


class FakeAsyncSwarmNode:
    def __init__(self):
        self._lock = threading.Lock()
        self.inflight = 0
        self.max_inflight = 0

    def execute(self, operation, params):
        if operation == "estimate_bid":
            return {
                "success": True,
                "bid": {
                    "node_id": params["node_id"],
                    "agent_type": params["agent_type"],
                    "utility_score": 0.80,
                    "estimated_confidence": 0.80,
                    "estimated_cost": 0.10,
                    "specialization_match": 0.20,
                    "priority": 0,
                    "rationale": "async test bid",
                },
            }
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
    assert persisted["shared_state"]["routing"]["selected_node_ids"]


class FakeBiddingSwarmNode:
    def __init__(self):
        self.calls = []

    def execute(self, operation, params):
        self.calls.append((operation, dict(params)))
        if operation == "estimate_bid":
            scores = {
                "analysis_1": 0.90,
                "synthesis_1": 0.82,
                "answer_1": 0.41,
                "search_1": 0.55,
            }
            return {
                "success": True,
                "bid": {
                    "node_id": params["node_id"],
                    "agent_type": params["agent_type"],
                    "utility_score": scores[params["node_id"]],
                    "estimated_confidence": scores[params["node_id"]],
                    "estimated_cost": 0.10,
                    "specialization_match": 0.20,
                    "priority": 0,
                    "rationale": "test bid",
                },
            }
        if operation == "process_subtask":
            return {
                "success": True,
                "node_id": params["node_id"],
                "agent_type": params["agent_type"],
                "contribution": f"{params['node_id']} selected",
                "task_result": {
                    "task_id": params["task_id"],
                    "agent_type": params["agent_type"],
                    "success": True,
                    "output": {"answer": f"{params['node_id']} selected"},
                    "error": None,
                },
                "message": {"kind": "contribution", "node_id": params["node_id"], "content": "selected"},
                "shared_state_delta": {"contributors": [params["node_id"]]},
            }
        if operation == "review_peer_output":
            return {
                "success": True,
                "review": {
                    "reviewer_node_id": params["reviewer_node_id"],
                    "reviewer_agent_type": params.get("reviewer_agent_type"),
                    "target_node_id": params["target_contribution"]["node_id"],
                    "approval": True,
                    "issues": [],
                    "confidence": 0.5,
                    "summary": "ok",
                },
                "message": {"kind": "review", "node_id": params["reviewer_node_id"], "content": "ok"},
            }
        raise AssertionError(f"Unexpected operation: {operation}")


def test_swarm_coordinator_routes_to_top_bids(tmp_path):
    coordinator = SwarmCoordinatorModule()
    fake_node = FakeBiddingSwarmNode()
    coordinator.swarm_node = fake_node
    coordinator.swarm_consensus = SwarmConsensusModule()
    coordinator.blackboard_service = SwarmBlackboardService(sessions_dir=tmp_path / "swarm_sessions")
    coordinator._modules_loaded = True

    result = coordinator.execute(
        "coordinate_task",
        {
            "query": "route the best agents",
            "participants": [
                {"agent_type": "analysis", "node_id": "analysis_1"},
                {"agent_type": "synthesis", "node_id": "synthesis_1"},
                {"agent_type": "answer", "node_id": "answer_1"},
                {"agent_type": "search", "node_id": "search_1"},
            ],
            "route_policy": "top_k",
            "bid_top_k": 2,
            "peer_review": False,
        },
    )

    executed_nodes = {
        params["node_id"]
        for operation, params in fake_node.calls
        if operation == "process_subtask"
    }

    assert result["success"] is True
    assert executed_nodes == {"analysis_1", "synthesis_1"}
    assert [bid["node_id"] for bid in result["bids"][:2]] == ["analysis_1", "synthesis_1"]
    assert result["shared_state"]["routing"]["selected_node_ids"] == ["analysis_1", "synthesis_1"]


class FakeSkillAwareSwarmNode:
    def __init__(self):
        self.calls = []

    def execute(self, operation, params):
        self.calls.append((operation, dict(params)))
        if operation == "estimate_bid":
            selected_skill = None
            if params.get("skill_name"):
                selected_skill = {
                    "skill_name": params["skill_name"],
                    "match_strategy": "explicit",
                    "match_reason": f"Explicit skill selection: {params['skill_name']}",
                    "matched_triggers": [],
                }
            return {
                "success": True,
                "bid": {
                    "node_id": params["node_id"],
                    "agent_type": params["agent_type"],
                    "utility_score": 0.88,
                    "estimated_confidence": 0.82,
                    "estimated_cost": 0.10,
                    "specialization_match": 0.24,
                    "skill_bonus": 0.08 if selected_skill else 0.0,
                    "priority": 0,
                    "rationale": "skill-aware test bid",
                    "selected_skill": selected_skill,
                },
            }
        if operation == "process_subtask":
            selected_skill = None
            if params.get("skill_name"):
                selected_skill = {
                    "skill_name": params["skill_name"],
                    "match_strategy": "explicit",
                    "match_reason": f"Explicit skill selection: {params['skill_name']}",
                    "matched_triggers": [],
                }
            return {
                "success": True,
                "node_id": params["node_id"],
                "agent_type": params["agent_type"],
                "contribution": f"{params['node_id']} used a skill",
                "task_result": {
                    "task_id": params["task_id"],
                    "agent_type": params["agent_type"],
                    "success": True,
                    "output": {"answer": f"{params['node_id']} used a skill"},
                    "error": None,
                },
                "selected_skill": selected_skill,
                "instruction_layers": {
                    "profile": "Profile instructions",
                    "skill_instructions": "Skill instructions",
                },
                "message": {"kind": "contribution", "node_id": params["node_id"], "content": "skill"},
                "shared_state_delta": {
                    "skills": {
                        params["node_id"]: {
                            "skill_name": params.get("skill_name"),
                            "match_strategy": "explicit",
                        }
                    }
                },
            }
        if operation == "review_peer_output":
            return {
                "success": True,
                "review": {
                    "reviewer_node_id": params["reviewer_node_id"],
                    "reviewer_agent_type": params.get("reviewer_agent_type"),
                    "target_node_id": params["target_contribution"]["node_id"],
                    "approval": True,
                    "issues": [],
                    "confidence": 0.5,
                    "summary": "ok",
                },
                "message": {"kind": "review", "node_id": params["reviewer_node_id"], "content": "ok"},
            }
        raise AssertionError(f"Unexpected operation: {operation}")


def test_swarm_coordinator_persists_skill_metadata(tmp_path):
    sessions_dir = tmp_path / "swarm_sessions"
    blackboard = SwarmBlackboardService(sessions_dir=sessions_dir)

    coordinator = SwarmCoordinatorModule()
    coordinator.swarm_node = FakeSkillAwareSwarmNode()
    coordinator.swarm_consensus = SwarmConsensusModule()
    coordinator.blackboard_service = blackboard
    coordinator._modules_loaded = True

    result = coordinator.execute(
        "coordinate_task",
        {
            "query": "document this system",
            "participants": [
                {
                    "agent_type": "answer",
                    "node_id": "writer_1",
                    "skill_name": "technical_writer",
                }
            ],
            "peer_review": False,
        },
    )

    persisted = blackboard.load_session(result["session_id"])

    assert result["success"] is True
    assert result["bids"][0]["selected_skill"]["skill_name"] == "technical_writer"
    assert result["contributions"][0]["selected_skill"]["skill_name"] == "technical_writer"
    assert result["shared_state"]["contributions"][0]["selected_skill"]["skill_name"] == "technical_writer"
    assert result["shared_state"]["skills"]["writer_1"]["skill_name"] == "technical_writer"
    assert persisted["contributions"][0]["selected_skill"]["skill_name"] == "technical_writer"
    assert persisted["shared_state"]["skills"]["writer_1"]["skill_name"] == "technical_writer"

from __future__ import annotations

import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

from oricli_core.brain.modules.agent_coordinator import AgentCoordinatorModule
from oricli_core.brain.modules.multi_agent_orchestrator import MultiAgentOrchestratorModule
from oricli_core.services.agent_profile_service import AgentProfileService


class RecordingAgent:
    def __init__(self, response: dict):
        self.response = response
        self.calls: list[tuple[str, dict]] = []

    def execute(self, operation: str, params: dict):
        self.calls.append((operation, dict(params)))
        payload = dict(self.response)
        payload.setdefault("success", True)
        return payload


def _write_profile_config(path: Path) -> None:
    path.write_text(
        json.dumps(
            {
                "task_type_profiles": {"research": "research_only"},
                "profiles": [
                    {
                        "name": "research_only",
                        "allowed_modules": ["search_agent"],
                        "allowed_operations": {"search_agent": ["search"]},
                        "system_instructions": "Use only approved research tools.",
                        "model_preference": "qwen2.5:7b",
                    },
                    {
                        "name": "answer_only",
                        "allowed_modules": ["answer_agent"],
                        "allowed_operations": {"answer_agent": ["format_answer"]},
                        "system_instructions": "Answer tersely and precisely.",
                    },
                ],
            },
            indent=2,
        ),
        encoding="utf-8",
    )


def test_agent_profile_service_resolves_by_task_type(tmp_path):
    config_path = tmp_path / "agent_profiles.json"
    _write_profile_config(config_path)

    service = AgentProfileService(config_path=config_path)
    profile = service.resolve_profile(task_type="research")

    assert profile is not None
    assert profile.name == "research_only"
    assert profile.system_instructions == "Use only approved research tools."


def test_agent_coordinator_injects_profile_instructions(tmp_path, monkeypatch):
    config_path = tmp_path / "agent_profiles.json"
    _write_profile_config(config_path)
    service = AgentProfileService(config_path=config_path)

    answer_agent = RecordingAgent({"answer": "formatted"})
    coordinator = AgentCoordinatorModule()
    coordinator.agents = {"answer": answer_agent}

    monkeypatch.setattr(
        "oricli_core.brain.modules.agent_coordinator.get_agent_profile_service",
        lambda: service,
    )

    result = coordinator.execute(
        "execute_task",
        {
            "task": {
                "id": "task-1",
                "agent_type": "answer",
                "query": "hello",
                "context": {"answer": "raw answer"},
                "agent_profile": "answer_only",
            }
        },
    )

    assert result["success"] is True
    assert answer_agent.calls[0][0] == "format_answer"
    assert answer_agent.calls[0][1]["agent_profile"] == "answer_only"
    assert answer_agent.calls[0][1]["profile_instructions"] == "Answer tersely and precisely."
    assert answer_agent.calls[0][1]["instructions"] == "Answer tersely and precisely."


def test_agent_coordinator_preserves_context_instruction_layers(tmp_path, monkeypatch):
    config_path = tmp_path / "agent_profiles.json"
    _write_profile_config(config_path)
    service = AgentProfileService(config_path=config_path)

    answer_agent = RecordingAgent({"answer": "formatted"})
    coordinator = AgentCoordinatorModule()
    coordinator.agents = {"answer": answer_agent}

    monkeypatch.setattr(
        "oricli_core.brain.modules.agent_coordinator.get_agent_profile_service",
        lambda: service,
    )

    result = coordinator.execute(
        "execute_task",
        {
            "task": {
                "id": "task-1b",
                "agent_type": "answer",
                "query": "hello",
                "context": {
                    "answer": "raw answer",
                    "instructions": "Profile instructions:\nAnswer tersely and precisely.\n\nSkill mindset:\nThink like a python architect.",
                    "instruction_layers": {
                        "profile": "Answer tersely and precisely.",
                        "skill_mindset": "Think like a python architect.",
                    },
                    "selected_skill": {
                        "skill_name": "senior_python_dev",
                        "match_strategy": "explicit",
                    },
                },
                "agent_profile": "answer_only",
            }
        },
    )

    assert result["success"] is True
    assert answer_agent.calls[0][1]["instructions"].startswith("Profile instructions:")
    assert answer_agent.calls[0][1]["instruction_layers"]["skill_mindset"] == "Think like a python architect."
    assert answer_agent.calls[0][1]["selected_skill"]["skill_name"] == "senior_python_dev"
    assert answer_agent.calls[0][1]["profile_instructions"] == "Answer tersely and precisely."


def test_agent_coordinator_blocks_disallowed_agent(tmp_path, monkeypatch):
    config_path = tmp_path / "agent_profiles.json"
    _write_profile_config(config_path)
    service = AgentProfileService(config_path=config_path)

    coordinator = AgentCoordinatorModule()
    coordinator.agents = {"search": RecordingAgent({"documents": []})}

    monkeypatch.setattr(
        "oricli_core.brain.modules.agent_coordinator.get_agent_profile_service",
        lambda: service,
    )

    result = coordinator.execute(
        "execute_task",
        {
            "task": {
                "id": "task-2",
                "agent_type": "search",
                "query": "hello",
                "context": {},
                "agent_profile": "answer_only",
            }
        },
    )

    assert result["success"] is False
    assert "not permitted" in result["result"]["error"]


def test_multi_agent_orchestrator_applies_stage_profile(tmp_path, monkeypatch):
    config_path = tmp_path / "agent_profiles.json"
    _write_profile_config(config_path)
    service = AgentProfileService(config_path=config_path)

    search_agent = RecordingAgent({"documents": [{"title": "Doc"}]})
    orchestrator = MultiAgentOrchestratorModule()
    orchestrator.search_agent = search_agent
    orchestrator._modules_loaded = True

    monkeypatch.setattr(
        "oricli_core.brain.modules.multi_agent_orchestrator.get_agent_profile_service",
        lambda: service,
    )

    result = orchestrator.execute(
        "execute_pipeline",
        {
            "query": "find docs",
            "agent_types": ["search"],
            "agent_profile": "research_only",
        },
    )

    assert result["success"] is True
    assert search_agent.calls[0][0] == "search"
    assert search_agent.calls[0][1]["agent_profile"] == "research_only"
    assert search_agent.calls[0][1]["model"] == "qwen2.5:7b"
    assert result["agent_results"][0]["agent_profile"] == "research_only"


def test_multi_agent_orchestrator_blocks_disallowed_stage(tmp_path, monkeypatch):
    config_path = tmp_path / "agent_profiles.json"
    _write_profile_config(config_path)
    service = AgentProfileService(config_path=config_path)

    answer_agent = RecordingAgent({"answer": "nope"})
    orchestrator = MultiAgentOrchestratorModule()
    orchestrator.answer_agent = answer_agent
    orchestrator._modules_loaded = True

    monkeypatch.setattr(
        "oricli_core.brain.modules.multi_agent_orchestrator.get_agent_profile_service",
        lambda: service,
    )

    result = orchestrator.execute(
        "execute_pipeline",
        {
            "query": "answer this",
            "agent_types": ["answer"],
            "agent_profile": "research_only",
        },
    )

    assert result["success"] is False
    assert result["agent_results"][0]["success"] is False
    assert "not permitted" in result["agent_results"][0]["error"]

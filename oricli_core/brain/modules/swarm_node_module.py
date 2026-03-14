from __future__ import annotations
"""
Swarm Node Module
Manages individual node execution and peer review in collaborative swarm runs.
"""

from typing import Any, Dict, List, Optional

from oricli_core.brain.base_module import BaseBrainModule, ModuleMetadata
from oricli_core.brain.registry import ModuleRegistry
from oricli_core.exceptions import InvalidParameterError
from oricli_core.services.agent_profile_service import get_agent_profile_service


class SwarmNodeModule(BaseBrainModule):
    """Module for managing individual swarm node execution."""

    def __init__(self) -> None:
        super().__init__()
        self.agent_coordinator = None
        self.skill_manager = None

    @property
    def metadata(self) -> ModuleMetadata:
        return ModuleMetadata(
            name="swarm_node",
            version="1.2.0",
            description="Manages individual swarm node execution and collaborative peer review",
            operations=["status", "estimate_bid", "process_subtask", "review_peer_output"],
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

    def _ensure_skill_manager(self) -> None:
        if self.skill_manager is None:
            self.skill_manager = ModuleRegistry.get_module(
                "skill_manager",
                auto_discover=True,
                wait_timeout=1.0,
            )

    def execute(self, operation: str, params: Dict[str, Any]) -> Dict[str, Any]:
        if operation == "status":
            self._ensure_agent_coordinator()
            self._ensure_skill_manager()
            return {
                "success": True,
                "status": "active",
                "agent_coordinator_available": self.agent_coordinator is not None,
                "skill_manager_available": self.skill_manager is not None,
            }
        if operation == "estimate_bid":
            return self._estimate_bid(params)
        if operation == "process_subtask":
            return self._process_subtask(params)
        if operation == "review_peer_output":
            return self._review_peer_output(params)
        return {"success": False, "error": f"Unknown operation: {operation}"}

    def _resolve_profile_context(
        self,
        *,
        agent_profile: Optional[str],
        task_type: Optional[str],
        agent_type: str,
    ) -> Dict[str, Any]:
        profile = get_agent_profile_service().resolve_profile(
            profile_name=agent_profile,
            task_type=task_type,
            agent_type=agent_type,
        )
        if profile is None:
            return {}
        return {
            "name": profile.name,
            "description": profile.description,
            "system_instructions": profile.system_instructions,
            "model_preference": profile.model_preference,
            "task_tags": list(profile.task_tags),
        }

    def _normalize_skill(
        self,
        skill: Dict[str, Any],
        *,
        match_strategy: str,
        match_reason: str,
        matched_triggers: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        return {
            "skill_name": str(skill.get("skill_name") or "").strip(),
            "description": str(skill.get("description") or "").strip(),
            "triggers": list(skill.get("triggers") or []),
            "requires_tools": list(skill.get("requires_tools") or []),
            "mindset": str(skill.get("mindset") or "").strip(),
            "instructions": str(skill.get("instructions") or "").strip(),
            "match_strategy": match_strategy,
            "match_reason": match_reason,
            "matched_triggers": list(matched_triggers or []),
        }

    def _resolve_skill_overlay(self, params: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        skill_name = str(params.get("skill_name") or "").strip()
        auto_skill_match = bool(params.get("auto_skill_match", True))
        query = str(params.get("query") or params.get("input") or "").strip()
        query_lower = query.lower()

        if skill_name:
            self._ensure_skill_manager()
            if self.skill_manager is None:
                raise InvalidParameterError("skill_name", skill_name, "skill_manager unavailable")
            result = self.skill_manager.execute("get_skill", {"skill_name": skill_name})
            if not result.get("success"):
                raise InvalidParameterError("skill_name", skill_name, str(result.get("error") or "Skill not found"))
            skill = dict(result.get("skill") or {})
            return self._normalize_skill(
                skill,
                match_strategy="explicit",
                match_reason=f"Explicit skill selection: {skill_name}",
            )

        if not auto_skill_match or not query:
            return None

        self._ensure_skill_manager()
        if self.skill_manager is None:
            return None

        result = self.skill_manager.execute("match_skills", {"query": query})
        matches = list(result.get("matches") or [])
        if not matches:
            return None

        skill = dict(matches[0])
        matched_triggers = [
            str(trigger).strip()
            for trigger in skill.get("triggers", [])
            if str(trigger).strip() and str(trigger).strip().lower() in query_lower
        ]
        reason = (
            f"Matched query triggers: {', '.join(matched_triggers)}"
            if matched_triggers
            else f"Matched query against skill: {skill.get('skill_name', '')}"
        )
        return self._normalize_skill(
            skill,
            match_strategy="query_match",
            match_reason=reason,
            matched_triggers=matched_triggers,
        )

    def _compose_instruction_context(
        self,
        *,
        profile_context: Dict[str, Any],
        selected_skill: Optional[Dict[str, Any]],
    ) -> Dict[str, Any]:
        instruction_layers: Dict[str, str] = {}
        composed_sections: List[str] = []

        profile_instructions = str(profile_context.get("system_instructions") or "").strip()
        if profile_instructions:
            instruction_layers["profile"] = profile_instructions
            composed_sections.append(f"Profile instructions:\n{profile_instructions}")

        if selected_skill:
            mindset = str(selected_skill.get("mindset") or "").strip()
            if mindset:
                instruction_layers["skill_mindset"] = mindset
                composed_sections.append(
                    f"Skill mindset ({selected_skill.get('skill_name', 'skill')}):\n{mindset}"
                )

            skill_instructions = str(selected_skill.get("instructions") or "").strip()
            if skill_instructions:
                instruction_layers["skill_instructions"] = skill_instructions
                composed_sections.append(
                    f"Skill instructions ({selected_skill.get('skill_name', 'skill')}):\n{skill_instructions}"
                )

        return {
            "instruction_layers": instruction_layers,
            "instructions": "\n\n".join(section for section in composed_sections if section).strip(),
        }

    def _estimate_bid(self, params: Dict[str, Any]) -> Dict[str, Any]:
        agent_type = str(params.get("agent_type") or "").strip()
        if not agent_type:
            raise InvalidParameterError("agent_type", agent_type, "agent_type is required")

        query = str(params.get("query") or params.get("input") or "").strip().lower()
        task_type = str(params.get("task_type") or "").strip().lower()
        node_id = str(params.get("node_id") or agent_type)
        priority = int(params.get("priority", 0))
        bid_hint = dict(params.get("bid_hint") or {})

        base_profiles: Dict[str, Dict[str, Any]] = {
            "search": {"confidence": 0.68, "cost": 0.18, "specialties": {"research", "retrieval", "search", "evidence"}},
            "research": {"confidence": 0.72, "cost": 0.28, "specialties": {"research", "analysis", "evidence", "investigation"}},
            "ranking": {"confidence": 0.60, "cost": 0.14, "specialties": {"ranking", "retrieval", "search"}},
            "synthesis": {"confidence": 0.70, "cost": 0.24, "specialties": {"synthesis", "summary", "reasoning", "planning"}},
            "analysis": {"confidence": 0.74, "cost": 0.26, "specialties": {"analysis", "code", "debug", "security", "benchmark"}},
            "answer": {"confidence": 0.66, "cost": 0.16, "specialties": {"answer", "response", "formatting"}},
            "verifier": {"confidence": 0.78, "cost": 0.20, "specialties": {"verify", "compliance", "security", "audit"}},
        }
        profile = base_profiles.get(agent_type, {"confidence": 0.55, "cost": 0.22, "specialties": {agent_type}})

        query_terms = {term for term in query.replace("-", " ").split() if len(term) > 3}
        specialization_match = 0.0
        specialties = set(profile["specialties"])
        if task_type and task_type in specialties:
            specialization_match += 0.35
        if any(term in specialties for term in query_terms):
            specialization_match += 0.25

        profile_name = str(params.get("agent_profile") or "").lower()
        if profile_name:
            if "research" in profile_name and agent_type in {"search", "research", "ranking", "synthesis"}:
                specialization_match += 0.12
            if "code" in profile_name and agent_type in {"analysis", "answer", "synthesis"}:
                specialization_match += 0.12
            if "compliance" in profile_name and agent_type in {"verifier", "analysis", "research"}:
                specialization_match += 0.12

        selected_skill = self._resolve_skill_overlay(params)
        skill_bonus = 0.0
        if selected_skill:
            matched_triggers = list(selected_skill.get("matched_triggers") or [])
            skill_bonus = min(0.18, 0.08 + (0.03 * len(matched_triggers)))
            specialization_match += skill_bonus

        estimated_confidence = float(bid_hint.get("confidence", profile["confidence"]))
        estimated_cost = float(bid_hint.get("cost", profile["cost"]))
        if "specialization_match" in bid_hint:
            specialization_match = float(bid_hint["specialization_match"])

        priority_bonus = min(max(priority, 0), 5) * 0.05
        utility_score = round((estimated_confidence + specialization_match + priority_bonus) - estimated_cost, 4)
        rationale = bid_hint.get(
            "rationale",
            f"{agent_type} bid based on confidence={estimated_confidence:.2f}, cost={estimated_cost:.2f}, match={specialization_match:.2f}",
        )
        if selected_skill:
            rationale = f"{rationale}; skill={selected_skill['skill_name']}"

        return {
            "success": True,
            "bid": {
                "node_id": node_id,
                "agent_type": agent_type,
                "utility_score": utility_score,
                "estimated_confidence": estimated_confidence,
                "estimated_cost": estimated_cost,
                "specialization_match": round(specialization_match, 4),
                "skill_bonus": round(skill_bonus, 4),
                "priority": priority,
                "rationale": rationale,
                "selected_skill": selected_skill,
            },
        }

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
        profile_context = self._resolve_profile_context(
            agent_profile=params.get("agent_profile"),
            task_type=params.get("task_type"),
            agent_type=str(agent_type),
        )
        selected_skill = self._resolve_skill_overlay(params)
        instruction_context = self._compose_instruction_context(
            profile_context=profile_context,
            selected_skill=selected_skill,
        )
        context["collaborative"] = True
        context["shared_state"] = shared_state
        context["message_log"] = message_log
        context["node_id"] = node_id
        context["round_index"] = round_index
        if profile_context.get("name"):
            context["resolved_agent_profile"] = profile_context
            context["profile_instructions"] = profile_context.get("system_instructions", "")
            if profile_context.get("model_preference"):
                context["model"] = profile_context["model_preference"]
        if selected_skill:
            context["selected_skill"] = selected_skill
            context["skill_name"] = selected_skill["skill_name"]
            context["skill_match_reason"] = selected_skill["match_reason"]
        if instruction_context["instruction_layers"]:
            context["instruction_layers"] = instruction_context["instruction_layers"]
        if instruction_context["instructions"]:
            context["instructions"] = instruction_context["instructions"]

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
            "selected_skill": selected_skill,
            "instruction_layers": instruction_context["instruction_layers"],
            "message": message,
            "shared_state_delta": {
                "last_contribution": contribution,
                "last_contributor": node_id,
                "skills": (
                    {
                        node_id: {
                            "skill_name": selected_skill["skill_name"],
                            "match_strategy": selected_skill["match_strategy"],
                            "match_reason": selected_skill["match_reason"],
                            "matched_triggers": selected_skill.get("matched_triggers", []),
                        }
                    }
                    if selected_skill
                    else {}
                ),
            },
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

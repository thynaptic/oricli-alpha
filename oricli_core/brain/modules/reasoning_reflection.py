from __future__ import annotations
"""
Reasoning Reflection Service

Reflection service that reviews reasoning steps and generates corrections.
Ported from Swift ReasoningReflectionService.swift
"""

import re
import uuid
from typing import Any, Dict, List, Optional
import logging

from oricli_core.brain.base_module import BaseBrainModule, ModuleMetadata
from oricli_core.brain.registry import ModuleRegistry
from oricli_core.brain.modules.cot_models import (
    CoTStep,
    ReflectionResult,
    Correction,
    ReflectionIssue,
)
from oricli_core.exceptions import InvalidParameterError, ModuleOperationError

logger = logging.getLogger(__name__)


class ReasoningReflectionService(BaseBrainModule):
    """
    Reflection service that reviews reasoning steps and generates corrections.
    Integrates self-reflection into reasoning flow.
    """

    def __init__(self) -> None:
        """Initialize the module"""
        super().__init__()
        self._cognitive_generator = None
        self._text_engine = None
        # Track reflection depth to prevent infinite loops
        self._reflection_depth: dict[str, int] = {}
        self._max_reflection_depth = 2

    @property
    def metadata(self) -> ModuleMetadata:
        return ModuleMetadata(
            name="reasoning_reflection",
            version="1.0.1",
            description="Reflection service that reviews reasoning steps and generates corrections",
            operations=[
                "reflect_on_reasoning",
                "reflect_on_tot_path",
                "reflect_on_mcts_path",
                "clear_reflection_depth",
                "status",
            ],
            dependencies=[],
            enabled=True,
            model_required=False,
        )

    def initialize(self) -> bool:
        """Initialize dependent modules"""
        try:
            self._cognitive_generator = ModuleRegistry.get_module("cognitive_generator")
            # Lazy load text engine to avoid recursion
            try:
                self._text_engine = ModuleRegistry.get_module("text_generation_engine")
            except Exception:
                self._text_engine = None
            return True
        except Exception as e:
            logger.debug(
                "Failed to load cognitive_generator for reasoning_reflection",
                exc_info=True,
                extra={"module_name": "reasoning_reflection", "error_type": type(e).__name__},
            )
            return False

    def execute(self, operation: str, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute reflection operations.

        Supported operations:
        - reflect_on_reasoning: Reflect on CoT reasoning steps
        - reflect_on_tot_path: Reflect on ToT path
        - clear_reflection_depth: Clear reflection depth for a session
        - status: Check module health
        """
        if not getattr(self, "_text_engine", None) and not self._cognitive_generator:
            self.initialize()

        if operation == "status":
            return {
                "success": True,
                "status": "active",
                "initialized": True,
                "version": self.metadata.version
            }

        if operation == "reflect_on_reasoning":
            res = self._reflect_on_reasoning(params)
            return {
                "success": True,
                "result": res,
                "metadata": {
                    "reflection_depth": res.get("reflection_depth", 0)
                }
            }
        elif operation == "reflect_on_tot_path":
            res = self._reflect_on_tot_path(params)
            return {
                "success": True,
                "result": res
            }
        elif operation == "reflect_on_mcts_path":
            res = self._reflect_on_mcts_path(params)
            return {
                "success": True,
                "result": res
            }
        elif operation == "clear_reflection_depth":
            res = self._clear_reflection_depth(params)
            res["success"] = True
            return res
        else:
            return {"success": False, "error": f"Unknown operation: {operation}"}

    def _reflect_on_reasoning(self, params: dict[str, Any]) -> dict[str, Any]:
        """
        Reflect on reasoning steps and generate corrections if needed.

        Args:
            params: Dictionary with:
                - steps (list[dict]): List of CoT steps
                - final_answer (str): Final answer
                - confidence (float): Overall confidence
                - session_id (str, optional): Session identifier

        Returns:
            ReflectionResult as dictionary
        """
        if not self._cognitive_generator and not getattr(self, "_text_engine", None):
            self.initialize()
            if not self._cognitive_generator and not getattr(self, "_text_engine", None):
                raise ModuleOperationError(
                    module_name=self.metadata.name,
                    operation="reflect_on_reasoning",
                    reason="No generation engine available for reflection",
                )

        steps_dicts = params.get("steps", [])
        if not steps_dicts:
            raise InvalidParameterError("steps", str(steps_dicts), "steps parameter is required and must be non-empty")

        steps = [CoTStep.from_dict(s) for s in steps_dicts]
        final_answer = params.get("final_answer", "")
        confidence = params.get("confidence", 0.5)
        session_id = params.get("session_id", str(uuid.uuid4()))

        # Check if reflection should be triggered
        should_reflect_result = self._should_trigger_reflection(steps, confidence)

        if not should_reflect_result["should_reflect"]:
            return ReflectionResult(
                should_reflect=False,
                corrections=[],
                improved_steps=None,
                reflection_depth=0,
            ).to_dict()

        # Check reflection depth to prevent infinite loops
        current_depth = self._reflection_depth.get(session_id, 0)
        if current_depth >= self._max_reflection_depth:
            return ReflectionResult(
                should_reflect=False,
                corrections=[],
                improved_steps=None,
                reflection_depth=current_depth,
            ).to_dict()

        self._reflection_depth[session_id] = current_depth + 1

        # Perform reflection
        reflection = self._perform_reflection(
            steps, final_answer, confidence, should_reflect_result.get("reason", "Low confidence")
        )

        # Generate corrections if issues found
        corrections: list[Correction] = []
        improved_steps: list[CoTStep] | None = None

        if reflection["issues"]:
            corrections = [
                Correction(
                    step_index=issue["step_index"],
                    issue=issue["description"],
                    suggestion=issue.get("suggestion"),
                )
                for issue in reflection["issues"]
            ]

            # Generate improved steps if corrections are available
            improved_steps = self._generate_improved_steps(steps, corrections)

        return ReflectionResult(
            should_reflect=True,
            corrections=corrections,
            improved_steps=improved_steps,
            reflection_depth=current_depth + 1,
        ).to_dict()

    def _reflect_on_tot_path(self, params: dict[str, Any]) -> dict[str, Any]:
        """Reflect on ToT path (converts ToT nodes to CoT steps)"""
        from oricli_core.brain.modules.tot_models import ToTThoughtNode

        path_dicts = params.get("path", [])
        if not path_dicts:
            raise InvalidParameterError("path", str(path_dicts), "path parameter is required and must be non-empty")

        path = [ToTThoughtNode.from_dict(n) for n in path_dicts]
        final_answer = params.get("final_answer", "")
        confidence = params.get("confidence", 0.5)
        session_id = params.get("session_id", str(uuid.uuid4()))

        # Convert ToT nodes to CoT steps
        steps = [
            CoTStep(
                prompt=node.thought,
                reasoning=node.thought,
                intermediate_state=node.state,
                confidence=node.evaluation_score,
            )
            for node in path
        ]

        return self._reflect_on_reasoning(
            {
                "steps": [s.to_dict() for s in steps],
                "final_answer": final_answer,
                "confidence": confidence,
                "session_id": session_id,
            }
        )

    def _reflect_on_mcts_path(self, params: dict[str, Any]) -> dict[str, Any]:
        """Reflect on MCTS path (converts MCTS nodes to CoT steps)"""
        from oricli_core.brain.modules.mcts_models import MCTSNode

        path_dicts = params.get("path", [])
        if not path_dicts:
            raise InvalidParameterError("path", str(path_dicts), "path parameter is required and must be non-empty")

        path = [MCTSNode.from_dict(n) for n in path_dicts]
        final_answer = params.get("final_answer", "")
        confidence = params.get("confidence", 0.5)
        session_id = params.get("session_id", str(uuid.uuid4()))

        # Convert MCTS nodes to CoT steps
        steps = [
            CoTStep(
                prompt=node.tot_node.thought,
                reasoning=node.tot_node.thought,
                intermediate_state=node.tot_node.state,
                confidence=node.value_estimate,
            )
            for node in path
        ]

        return self._reflect_on_reasoning(
            {
                "steps": [s.to_dict() for s in steps],
                "final_answer": final_answer,
                "confidence": confidence,
                "session_id": session_id,
            }
        )

    def _should_trigger_reflection(
        self, steps: list[CoTStep], confidence: float
    ) -> dict[str, Any]:
        """Determine if reflection should be triggered"""
        # Trigger on low confidence
        if confidence < 0.6:
            return {
                "should_reflect": True,
                "reason": f"Low confidence: {confidence:.2f}",
            }

        # Trigger if any step has very low confidence
        low_confidence_steps = [
            s for s in steps if (s.confidence or 0.5) < 0.4
        ]
        if low_confidence_steps:
            return {
                "should_reflect": True,
                "reason": f"{len(low_confidence_steps)} steps with very low confidence",
            }

        # Trigger if reasoning is very short (may indicate incomplete reasoning)
        short_reasoning_steps = [
            s for s in steps if (s.reasoning or "").__len__() < 50
        ]
        if len(short_reasoning_steps) > len(steps) / 2:
            return {
                "should_reflect": True,
                "reason": f"Many steps with short reasoning ({len(short_reasoning_steps)} of {len(steps)})",
            }

        # Trigger if steps are inconsistent (check for contradictions)
        if self._has_contradictions(steps):
            return {
                "should_reflect": True,
                "reason": "Contradictions detected in reasoning steps",
            }

        return {"should_reflect": False, "reason": None}

    def _has_contradictions(self, steps: list[CoTStep]) -> bool:
        """Check for contradictions in reasoning steps"""
        if len(steps) <= 1:
            return False

        step_texts = [
            (s.reasoning or s.prompt).lower() for s in steps
        ]

        contradiction_pairs = [
            ("yes", "no"),
            ("true", "false"),
            ("is", "is not"),
        ]

        for i in range(len(step_texts)):
            for j in range(i + 1, len(step_texts)):
                for neg, pos in contradiction_pairs:
                    if (neg in step_texts[i] and pos in step_texts[j]) or (
                        pos in step_texts[i] and neg in step_texts[j]
                    ):
                        return True

        return False

    def _perform_reflection(
        self, steps: list[CoTStep], final_answer: str, confidence: float, reason: str
    ) -> dict[str, Any]:
        """Perform reflection analysis"""
        reasoning_summary = "\n\n".join(
            [
                f"Step {index + 1}: {step.prompt}\nReasoning: {step.reasoning or 'None'}\nConfidence: {step.confidence or 0.5}"
                for index, step in enumerate(steps)
            ]
        )

        prompt = (
            f"Instructions: Review the reasoning steps below for logical consistency. "
            f"Identify any issues like 'echoing the question' or 'nonsense'.\n"
            f"Reasoning Steps:\n{reasoning_summary}\n\n"
            f"Final Answer: {final_answer}\n"
            f"Issues found (Format: Step X: [Issue] - Suggestion: [Improvement]):"
        )

        try:
            if getattr(self, "_text_engine", None):
                gen_res = self._text_engine.execute(
                    "generate_with_neural",
                    {
                        "prompt": prompt,
                        "temperature": 0.3, # Low temperature for reflection
                        "max_length": 500,
                    }
                )
                response_text = gen_res.get("text", "")
            else:
                response_result = self._cognitive_generator.execute(
                    "generate_response",
                    {
                        "input": prompt,
                        "context": "Reasoning Reflection",
                        "persona": "oricli",
                    },
                )
                response_text = response_result.get("text", "")

            issues = self._parse_reflection_issues(response_text, len(steps))

            return {"issues": issues, "summary": response_text}

        except Exception as e:
            logger.debug(
                "Error performing reflection",
                exc_info=True,
                extra={"module_name": "reasoning_reflection", "error_type": type(e).__name__},
            )
            return {"issues": [], "summary": ""}

    def _parse_reflection_issues(self, text: str, step_count: int) -> list[dict[str, Any]]:
        """Parse issues from reflection response"""
        issues: list[dict[str, Any]] = []
        lines = text.split("\n")

        for line in lines:
            # Look for "Step X:" pattern
            step_match = re.search(r"Step\s+(\d+):", line)
            if step_match:
                try:
                    step_number = int(step_match.group(1))
                    if 1 <= step_number <= step_count:
                        # Extract issue and suggestion
                        rest_of_line = line[step_match.end() :].strip()
                        parts = rest_of_line.split(" - Suggestion: ")

                        issue_description = parts[0].strip() if parts else rest_of_line
                        suggestion = parts[1].strip() if len(parts) > 1 else None

                        issues.append(
                            {
                                "step_index": step_number - 1,
                                "description": issue_description,
                                "suggestion": suggestion,
                            }
                        )
                except ValueError:
                    continue

        return issues

    def _generate_improved_steps(
        self, original_steps: list[CoTStep], corrections: list[Correction]
    ) -> list[CoTStep]:
        """Generate improved steps based on corrections"""
        improved_steps = original_steps.copy()

        # Apply corrections to specific steps
        for correction in corrections:
            if correction.step_index < len(improved_steps):
                original_step = improved_steps[correction.step_index]

                prompt = f"""Improve the following reasoning step based on the feedback:

Original Step: {original_step.prompt}
Original Reasoning: {original_step.reasoning or 'None'}

Issue: {correction.issue}
Suggestion: {correction.suggestion or 'Improve the reasoning'}

Provide an improved version of this reasoning step:
"""

                try:
                    response_result = self._cognitive_generator.execute(
                        "generate_response",
                        {
                            "input": prompt,
                            "context": "Step Correction",
                            "persona": "oricli",
                        },
                    )

                    improved_reasoning = response_result.get("text", "")

                    # Create improved step
                    improved_steps[correction.step_index] = CoTStep(
                        id=original_step.id,
                        prompt=original_step.prompt,
                        reasoning=improved_reasoning,
                        intermediate_state=original_step.intermediate_state,
                        confidence=min(
                            1.0, (original_step.confidence or 0.5) + 0.1
                        ),  # Slightly increase confidence
                        timestamp=original_step.timestamp,
                    )
                except Exception:
                    # If improvement fails, keep original step
                    pass

        return improved_steps

    def _clear_reflection_depth(self, params: dict[str, Any]) -> dict[str, Any]:
        """Clear reflection depth for a session"""
        session_id = params.get("session_id")
        if session_id and session_id in self._reflection_depth:
            del self._reflection_depth[session_id]

        return {"success": True, "cleared": True}

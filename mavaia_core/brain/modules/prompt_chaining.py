"""
Prompt Chaining Service

Prompt chaining framework for multi-step reasoning.
Ported from Swift PromptChainingService.swift
"""

import re
from typing import Any
import logging

from mavaia_core.brain.base_module import BaseBrainModule, ModuleMetadata
from mavaia_core.brain.modules.cot_models import CoTStep
from mavaia_core.exceptions import InvalidParameterError

logger = logging.getLogger(__name__)


class PromptChainingService(BaseBrainModule):
    """
    Prompt chaining framework for multi-step reasoning.
    Breaks complex queries into sequential sub-prompts.
    """

    def __init__(self) -> None:
        """Initialize the module"""
        super().__init__()

    @property
    def metadata(self) -> ModuleMetadata:
        return ModuleMetadata(
            name="prompt_chaining",
            version="1.0.0",
            description="Prompt chaining framework for multi-step reasoning",
            operations=[
                "decompose_into_steps",
                "update_step_with_result",
                "build_context_for_next_step",
            ],
            dependencies=[],
            enabled=True,
            model_required=False,
        )

    def initialize(self) -> bool:
        """Initialize the module"""
        return True

    def execute(self, operation: str, params: dict[str, Any]) -> dict[str, Any]:
        """
        Execute prompt chaining operations.

        Supported operations:
        - decompose_into_steps: Break complex query into sequential sub-prompts
        - update_step_with_result: Update step with reasoning result
        - build_context_for_next_step: Build context from previous steps
        """
        if operation == "decompose_into_steps":
            return self._decompose_into_steps(params)
        elif operation == "update_step_with_result":
            return self._update_step_with_result(params)
        elif operation == "build_context_for_next_step":
            return self._build_context_for_next_step(params)
        else:
            raise InvalidParameterError(
                parameter="operation",
                value=operation,
                reason="Unknown operation for prompt_chaining",
            )

    def _decompose_into_steps(self, params: dict[str, Any]) -> dict[str, Any]:
        """
        Break complex query into sequential sub-prompts.

        Args:
            params: Dictionary with:
                - query (str): The query to decompose
                - context (str, optional): Additional context
                - max_steps (int): Maximum number of steps

        Returns:
            Dictionary with list of CoT steps
        """
        query = params.get("query", "")
        if not isinstance(query, str) or not query.strip():
            raise InvalidParameterError(
                parameter="query",
                value=str(query),
                reason="query parameter is required and must be a non-empty string",
            )

        context = params.get("context")
        max_steps = params.get("max_steps", 5)
        if context is not None and not isinstance(context, str):
            raise InvalidParameterError(
                parameter="context",
                value=str(type(context).__name__),
                reason="context must be a string when provided",
            )
        try:
            max_steps_int = int(max_steps)
        except (TypeError, ValueError):
            raise InvalidParameterError(
                parameter="max_steps",
                value=str(max_steps),
                reason="max_steps must be an integer",
            )
        if max_steps_int < 1:
            raise InvalidParameterError("max_steps", str(max_steps_int), "max_steps must be >= 1")

        # Analyze query to determine natural breakpoints
        steps = self._identify_breakpoints(query, context, max_steps_int)

        # Create CoT steps from breakpoints
        cot_steps: list[CoTStep] = []
        accumulated_context = context or ""

        for index, step_prompt in enumerate(steps):
            intermediate_state = (
                {"context": accumulated_context} if accumulated_context else None
            )
            step = CoTStep(
                prompt=step_prompt,
                intermediate_state=intermediate_state,
            )
            cot_steps.append(step)

            # Accumulate context for next step
            if accumulated_context:
                accumulated_context += "\n\n"
            accumulated_context += f"Step {index + 1}: {step_prompt}"

        return {"steps": [step.to_dict() for step in cot_steps]}

    def _identify_breakpoints(
        self, query: str, context: str | None, max_steps: int
    ) -> list[str]:
        """Identify natural breakpoints in a complex query"""
        query_lower = query.lower()
        steps: list[str] = []

        # Strategy 1: Look for explicit step indicators
        step_patterns = [
            "first",
            "second",
            "third",
            "fourth",
            "fifth",
            "step 1",
            "step 2",
            "step 3",
            "part a",
            "part b",
            "part c",
            "question 1",
            "question 2",
        ]

        has_explicit_steps = any(pattern in query_lower for pattern in step_patterns)

        if has_explicit_steps:
            # Split by explicit step markers
            parts = [p.strip() for p in re.split(r"\n\n+", query) if p.strip()]
            if len(parts) > 1 and len(parts) <= max_steps:
                return parts[:max_steps]

        # Strategy 2: Split by question marks (multiple questions)
        questions = [
            q.strip() + "?" for q in query.split("?") if q.strip()
        ]
        if len(questions) > 1 and len(questions) <= max_steps:
            return questions[:max_steps]

        # Strategy 3: Semantic decomposition based on keywords
        if "analyze" in query_lower or "compare" in query_lower:
            return self._decompose_analytical_query(query, max_steps)

        if "calculate" in query_lower or "solve" in query_lower:
            return self._decompose_mathematical_query(query, max_steps)

        # Strategy 4: Default - split by length and structure
        return self._default_decomposition(query, max_steps)

    def _decompose_analytical_query(self, query: str, max_steps: int) -> list[str]:
        """Decompose analytical queries (analyze, compare, evaluate)"""
        steps: list[str] = []

        # Step 1: Identify key components
        steps.append(f"Identify the key components and aspects of: {query}")

        # Step 2: Analyze each component
        if len(steps) < max_steps:
            steps.append("Analyze each component in detail")

        # Step 3: Compare/Evaluate
        if len(steps) < max_steps:
            if "compare" in query.lower():
                steps.append("Compare the identified components")
            else:
                steps.append("Evaluate the relationships between components")

        # Step 4: Synthesize
        if len(steps) < max_steps:
            steps.append("Synthesize findings into a comprehensive answer")

        return steps[:max_steps]

    def _decompose_mathematical_query(self, query: str, max_steps: int) -> list[str]:
        """Decompose mathematical queries (calculate, solve, derive)"""
        steps: list[str] = []

        # Step 1: Identify given information
        steps.append(f"Identify all given information and variables in: {query}")

        # Step 2: Determine approach
        if len(steps) < max_steps:
            steps.append("Determine the appropriate method or formula to use")

        # Step 3: Apply method
        if len(steps) < max_steps:
            steps.append("Apply the method step by step")

        # Step 4: Verify
        if len(steps) < max_steps:
            steps.append("Verify the solution and check for errors")

        return steps[:max_steps]

    def _default_decomposition(self, query: str, max_steps: int) -> list[str]:
        """Default decomposition strategy"""
        # For simple queries, create 2-3 steps
        target_steps = min(3, max_steps)

        if target_steps == 1:
            return [query]

        # Split query into logical parts
        sentences = [
            s.strip()
            for s in re.split(r"[.!?]+", query)
            if s.strip()
        ]

        if len(sentences) >= target_steps:
            return sentences[:target_steps]

        # If not enough sentences, create conceptual steps
        steps: list[str] = []
        steps.append(f"Understand the question: {query}")

        if target_steps >= 2:
            steps.append("Break down the problem into manageable parts")

        if target_steps >= 3:
            steps.append("Provide a comprehensive answer")

        return steps

    def _update_step_with_result(self, params: dict[str, Any]) -> dict[str, Any]:
        """
        Update step with reasoning result and prepare for next step.

        Args:
            params: Dictionary with:
                - step (dict): CoTStep as dict
                - reasoning (str): Reasoning result
                - confidence (float, optional): Confidence score

        Returns:
            Updated CoTStep as dictionary
        """
        step_dict = params.get("step")
        if not isinstance(step_dict, dict) or not step_dict:
            raise InvalidParameterError(
                parameter="step",
                value=str(type(step_dict).__name__),
                reason="step parameter is required and must be a dict",
            )

        step = CoTStep.from_dict(step_dict)
        reasoning = params.get("reasoning", "")
        confidence = params.get("confidence")

        updated_step = CoTStep(
            id=step.id,
            prompt=step.prompt,
            reasoning=reasoning,
            intermediate_state=step.intermediate_state,
            confidence=confidence,
            timestamp=step.timestamp,
        )

        return updated_step.to_dict()

    def _build_context_for_next_step(self, params: dict[str, Any]) -> dict[str, Any]:
        """
        Build context for next step from previous steps.

        Args:
            params: Dictionary with:
                - completed_steps (list[dict]): List of completed CoT steps

        Returns:
            Dictionary with context string
        """
        steps_dicts = params.get("completed_steps", [])
        if not isinstance(steps_dicts, list) or not steps_dicts:
            raise InvalidParameterError(
                parameter="completed_steps",
                value=str(type(steps_dicts).__name__),
                reason="completed_steps parameter is required and must be a non-empty list",
            )

        steps = [CoTStep.from_dict(s) for s in steps_dicts]
        context_parts: list[str] = []

        for index, step in enumerate(steps):
            step_context = f"Step {index + 1}: {step.prompt}"
            if step.reasoning:
                step_context += f"\nReasoning: {step.reasoning}"
            if step.confidence is not None:
                step_context += f"\nConfidence: {step.confidence:.2f}"
            context_parts.append(step_context)

        return {"context": "\n\n".join(context_parts)}


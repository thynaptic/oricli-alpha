from __future__ import annotations
"""
Tree-of-Thought Thought Generator

Service for generating multiple candidate thoughts per step in Tree-of-Thought.
Ported from Swift ToTThoughtGenerator.swift
"""

import time
from typing import Any
import logging

from oricli_core.brain.base_module import BaseBrainModule, ModuleMetadata
from oricli_core.brain.modules.tot_models import ToTThoughtNode, ToTConfiguration
from oricli_core.brain.registry import ModuleRegistry
from oricli_core.exceptions import InvalidParameterError, ModuleOperationError

logger = logging.getLogger(__name__)


class ToTThoughtGenerator(BaseBrainModule):
    """
    Service for generating multiple candidate thoughts per step in Tree-of-Thought.
    """

    def __init__(self) -> None:
        """Initialize the module"""
        super().__init__()
        self._cognitive_generator = None

    @property
    def metadata(self) -> ModuleMetadata:
        return ModuleMetadata(
            name="tot_thought_generator",
            version="1.0.0",
            description="Generates multiple candidate thoughts per step in Tree-of-Thought",
            operations=[
                "generate_thoughts",
            ],
            dependencies=[],
            enabled=True,
            model_required=False,
        )

    def initialize(self) -> bool:
        """Initialize dependent modules"""
        try:
            self._cognitive_generator = ModuleRegistry.get_module("cognitive_generator")
            return True
        except Exception as e:
            logger.debug(
                "Failed to initialize tot_thought_generator dependencies",
                exc_info=True,
                extra={"module_name": "tot_thought_generator", "error_type": type(e).__name__},
            )
            return False

    def execute(self, operation: str, params: dict[str, Any]) -> dict[str, Any]:
        """
        Execute thought generation operations.

        Supported operations:
        - generate_thoughts: Generate multiple candidate thoughts
        """
        if operation == "generate_thoughts":
            return self._generate_thoughts(params)
        else:
            raise InvalidParameterError(
                parameter="operation",
                value=operation,
                reason="Unknown operation for tot_thought_generator",
            )

    def _generate_thoughts(self, params: dict[str, Any]) -> dict[str, Any]:
        """
        Generate multiple candidate thoughts from a current state node.

        Args:
            params: Dictionary with:
                - current_state (dict): Current ToTThoughtNode as dict
                - query (str): The original query
                - context (str, optional): Additional context
                - count (int): Number of thoughts to generate
                - configuration (dict, optional): ToTConfiguration as dict

        Returns:
            Dictionary with list of generated thoughts
        """
        if not self._cognitive_generator:
            self.initialize()
            if not self._cognitive_generator:
                raise ModuleOperationError(
                    module_name="tot_thought_generator",
                    operation="generate_thoughts",
                    reason="Required module not available: cognitive_generator",
                )

        current_state_dict = params.get("current_state")
        if not isinstance(current_state_dict, dict) or not current_state_dict:
            raise InvalidParameterError(
                parameter="current_state",
                value=str(type(current_state_dict).__name__),
                reason="current_state parameter is required and must be a non-empty dict",
            )

        current_state = ToTThoughtNode.from_dict(current_state_dict)
        query = params.get("query", "")
        context = params.get("context")
        count = params.get("count", 3)
        config_dict = params.get("configuration", {})

        config = (
            ToTConfiguration.from_dict(config_dict)
            if config_dict
            else ToTConfiguration.default()
        )

        if count <= 0:
            return {"thoughts": []}

        # Build prompt for thought generation
        prompt = self._build_thought_generation_prompt(
            current_state=current_state,
            query=query,
            context=context,
            count=count,
            depth=current_state.depth,
        )

        # Generate thoughts sequentially (can be parallelized later)
        generated_thoughts: list[ToTThoughtNode] = []

        for i in range(count):
            try:
                thought = self._generate_single_thought(
                    prompt=prompt,
                    thought_index=i,
                    total_count=count,
                    parent_node=current_state,
                    configuration=config,
                )
                generated_thoughts.append(thought)
            except Exception as e:
                logger.debug(
                    "Failed to generate thought; continuing",
                    exc_info=True,
                    extra={
                        "module_name": "tot_thought_generator",
                        "thought_index": int(i),
                        "error_type": type(e).__name__,
                    },
                )
                # Continue with remaining thoughts

        # If some thoughts failed, try to retry with reduced diversity
        if len(generated_thoughts) < count:
            remaining = count - len(generated_thoughts)
            for i in range(len(generated_thoughts), count):
                try:
                    thought = self._generate_single_thought(
                        prompt=prompt,
                        thought_index=i,
                        total_count=count,
                        parent_node=current_state,
                        configuration=config,
                        retry=True,
                    )
                    generated_thoughts.append(thought)
                except Exception:
                    # Continue with fewer thoughts if retry fails
                    pass

        return {"thoughts": [thought.to_dict() for thought in generated_thoughts]}

    def _generate_single_thought(
        self,
        prompt: str,
        thought_index: int,
        total_count: int,
        parent_node: ToTThoughtNode,
        configuration: ToTConfiguration,
        retry: bool = False,
    ) -> ToTThoughtNode:
        """Generate a single thought candidate"""
        # Modify prompt to encourage diversity for different thought indices
        diversity_prompt = self._add_diversity_guidance(
            base_prompt=prompt,
            thought_index=thought_index,
            total_count=total_count,
            retry=retry,
        )

        # Generate thought using cognitive generator
        context = (
            parent_node.state.get("previousThought", "")
            if parent_node.state
            else ""
        )

        try:
            response_result = self._cognitive_generator.execute(
                "generate_response",
                {
                    "input": diversity_prompt,
                    "context": context,
                    "persona": "oricli",
                },
            )

            # Extract thought text from response
            thought_text = response_result.get("text", diversity_prompt)
            if not thought_text or thought_text.strip() == "":
                thought_text = diversity_prompt

            # Build intermediate state from parent
            state = parent_node.state.copy() if parent_node.state else {}
            state["previousThought"] = parent_node.thought
            state["thoughtIndex"] = str(thought_index)

            # Build metadata
            metadata = parent_node.metadata.copy()
            metadata["generationIndex"] = str(thought_index)
            metadata["totalGenerated"] = str(total_count)
            metadata["depth"] = str(parent_node.depth + 1)
            if retry:
                metadata["isRetry"] = "true"

            return ToTThoughtNode(
                parent_id=parent_node.id,
                depth=parent_node.depth + 1,
                thought=thought_text.strip(),
                state=state,
                metadata=metadata,
            )

        except Exception as e:
            # Fallback: create a simple continuation thought
            fallback_thought = f"Continuing from: {parent_node.thought[:50]}..."
            state = parent_node.state.copy() if parent_node.state else {}
            metadata = parent_node.metadata.copy()
            metadata["fallback"] = "true"
            metadata["error"] = str(e)

            return ToTThoughtNode(
                parent_id=parent_node.id,
                depth=parent_node.depth + 1,
                thought=fallback_thought,
                state=state,
                metadata=metadata,
            )

    def _build_thought_generation_prompt(
        self,
        current_state: ToTThoughtNode,
        query: str,
        context: str | None,
        count: int,
        depth: int,
    ) -> str:
        """Build prompt for generating thoughts"""
        prompt = "You are exploring different reasoning paths to solve a problem. Generate a distinct approach or perspective.\n\n"

        # Add original query
        prompt += f"Original Question: {query}\n\n"

        # Add context if available
        if context:
            prompt += f"Context:\n{context}\n\n"

        # Add path to current state (simplified - would need tree traversal in full implementation)
        if depth > 0:
            prompt += "Current Reasoning Path:\n"
            prompt += self._build_path_description(current_state)
            prompt += "\n\n"

        # Add instructions based on depth
        if depth == 0:
            prompt += f"Generate {count} different initial approaches or perspectives to solve this problem. Each should be distinct and explore a different angle.\n\n"
            prompt += "Provide your reasoning for each approach, showing how it differs from the others.\n\n"
        elif depth <= 2:
            prompt += f"Generate {count} different ways to extend or refine the current reasoning. Explore alternative paths that branch from the current thought.\n\n"
            prompt += "Each extension should take the reasoning in a distinct direction.\n\n"
        else:
            prompt += f"Generate {count} focused refinement or conclusion for this reasoning path. Deepen the analysis with specific details.\n\n"

        prompt += "Thought:"

        return prompt

    def _build_path_description(self, current_state: ToTThoughtNode) -> str:
        """Build description of the path leading to current state"""
        # Simplified version - in practice we'd traverse the full tree
        path: list[str] = []
        path.append(f"Depth {current_state.depth}: {current_state.thought}")

        # Check state for previous thought info
        if current_state.state and "previousThought" in current_state.state:
            prev_thought = current_state.state["previousThought"]
            path.insert(0, f"Depth {current_state.depth - 1}: {prev_thought}")

        return "\n".join(path)

    def _add_diversity_guidance(
        self,
        base_prompt: str,
        thought_index: int,
        total_count: int,
        retry: bool,
    ) -> str:
        """Add diversity guidance to prompt for generating different thoughts"""
        if retry:
            return f"{base_prompt}\n\n(Note: This is a retry generation. Focus on generating a viable reasoning step.)"

        if total_count <= 1:
            return base_prompt

        diversity_guidance = "\n\n"

        # Encourage different perspectives for different indices
        if thought_index == 0:
            diversity_guidance += "Approach 1: Focus on the most direct or obvious path forward.\n"
        elif thought_index == 1:
            diversity_guidance += "Approach 2: Consider an alternative perspective or unconventional angle.\n"
        elif thought_index == 2:
            diversity_guidance += "Approach 3: Explore a more detailed or technical approach.\n"
        elif thought_index == 3:
            diversity_guidance += "Approach 4: Consider practical or applied implications.\n"
        else:
            diversity_guidance += f"Approach {thought_index + 1}: Generate a unique perspective that differs from previous approaches.\n"

        diversity_guidance += "\nGenerate this specific approach now:"

        return base_prompt + diversity_guidance


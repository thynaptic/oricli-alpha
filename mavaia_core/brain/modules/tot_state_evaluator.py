"""
Tree-of-Thought State Evaluator

Hybrid evaluation service for Tree-of-Thought states.
Combines LLM scoring, semantic similarity, and heuristic metrics.
Ported from Swift ToTStateEvaluator.swift
"""

import sys
import re
import time
from pathlib import Path
from typing import Any
import concurrent.futures

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent))

from mavaia_core.brain.base_module import BaseBrainModule, ModuleMetadata
from tot_models import ToTThoughtNode, ToTConfiguration


class ToTStateEvaluator(BaseBrainModule):
    """
    Hybrid evaluation service for Tree-of-Thought states.
    Combines LLM scoring, semantic similarity, and heuristic metrics.
    """

    def __init__(self) -> None:
        """Initialize the module"""
        self._cognitive_generator = None
        self._embeddings = None

    @property
    def metadata(self) -> ModuleMetadata:
        return ModuleMetadata(
            name="tot_state_evaluator",
            version="1.0.0",
            description="Hybrid evaluation service combining LLM, semantic, and heuristic scoring",
            operations=[
                "evaluate_thought",
                "evaluate_thoughts",
            ],
            dependencies=[],
            enabled=True,
            model_required=False,
        )

    def initialize(self) -> bool:
        """Initialize dependent modules"""
        try:
            from module_registry import ModuleRegistry

            self._cognitive_generator = ModuleRegistry.get_module("cognitive_generator")
            self._embeddings = ModuleRegistry.get_module("embeddings")
            return True
        except Exception:
            return False

    def execute(self, operation: str, params: dict[str, Any]) -> dict[str, Any]:
        """
        Execute evaluation operations.

        Supported operations:
        - evaluate_thought: Evaluate a single thought
        - evaluate_thoughts: Evaluate multiple thoughts in parallel
        """
        if operation == "evaluate_thought":
            return self._evaluate_thought_op(params)
        elif operation == "evaluate_thoughts":
            return self._evaluate_thoughts_op(params)
        else:
            raise ValueError(f"Unknown operation: {operation}")

    def _evaluate_thought_op(self, params: dict[str, Any]) -> dict[str, Any]:
        """Evaluate a single thought (operation wrapper)"""
        thought_dict = params.get("thought")
        if not thought_dict:
            raise ValueError("thought parameter is required")

        thought = ToTThoughtNode.from_dict(thought_dict)
        query = params.get("query", "")
        all_thoughts_dicts = params.get("all_thoughts", [])
        all_thoughts = [ToTThoughtNode.from_dict(t) for t in all_thoughts_dicts]
        config_dict = params.get("configuration", {})

        config = (
            ToTConfiguration.from_dict(config_dict)
            if config_dict
            else ToTConfiguration.default()
        )

        score = self._evaluate_thought(thought, query, all_thoughts, config)
        return {"score": score}

    def _evaluate_thoughts_op(self, params: dict[str, Any]) -> dict[str, Any]:
        """Evaluate multiple thoughts in parallel (operation wrapper)"""
        thoughts_dicts = params.get("thoughts", [])
        if not thoughts_dicts:
            raise ValueError("thoughts parameter is required")

        thoughts = [ToTThoughtNode.from_dict(t) for t in thoughts_dicts]
        query = params.get("query", "")
        config_dict = params.get("configuration", {})

        config = (
            ToTConfiguration.from_dict(config_dict)
            if config_dict
            else ToTConfiguration.default()
        )

        scores = self._evaluate_thoughts(thoughts, query, config)
        return {"scores": scores}

    def _evaluate_thought(
        self,
        thought: ToTThoughtNode,
        query: str,
        all_thoughts: list[ToTThoughtNode],
        configuration: ToTConfiguration,
    ) -> float:
        """Evaluate a thought node using hybrid approach (LLM + semantic + heuristic)"""
        weights = configuration.evaluation_weights

        # Evaluate using all three methods (can be parallelized)
        llm_score = self._evaluate_with_llm(thought, query)
        semantic_score = self._evaluate_semantic_similarity(
            thought, query, all_thoughts
        )
        heuristic_score = self._evaluate_heuristics(thought, query)

        # Combine scores with weighted average
        combined_score = (
            (llm_score * weights.llm)
            + (semantic_score * weights.semantic)
            + (heuristic_score * weights.heuristic)
        )

        return max(0.0, min(1.0, combined_score))

    def _evaluate_thoughts(
        self,
        thoughts: list[ToTThoughtNode],
        query: str,
        configuration: ToTConfiguration,
    ) -> dict[str, float]:
        """Evaluate multiple thoughts in parallel"""
        scores: dict[str, float] = {}

        # Evaluate in parallel using thread pool
        with concurrent.futures.ThreadPoolExecutor(max_workers=min(len(thoughts), 5)) as executor:
            future_to_thought = {
                executor.submit(
                    self._evaluate_thought, thought, query, thoughts, configuration
                ): thought
                for thought in thoughts
            }

            for future in concurrent.futures.as_completed(future_to_thought):
                thought = future_to_thought[future]
                try:
                    score = future.result()
                    scores[thought.id] = score
                except Exception as e:
                    print(
                        f"[ToTStateEvaluator] Error evaluating thought {thought.id}: {e}",
                        file=sys.stderr,
                    )
                    scores[thought.id] = 0.5  # Default neutral score on error

        return scores

    # MARK: - LLM-Based Evaluation (40% weight)

    def _evaluate_with_llm(self, thought: ToTThoughtNode, query: str) -> float:
        """Use LLM to score thought quality"""
        prompt = self._build_llm_evaluation_prompt(thought, query)

        if not self._cognitive_generator:
            self.initialize()
            if not self._cognitive_generator:
                return 0.5  # Default neutral score

        try:
            response_result = self._cognitive_generator.execute(
                "generate_response",
                {
                    "input": prompt,
                    "context": "",
                    "persona": "mavaia",
                },
            )

            evaluation_text = response_result.get("text", "")
            return self._parse_llm_score(evaluation_text)

        except Exception as e:
            print(
                f"[ToTStateEvaluator] LLM evaluation failed: {e}",
                file=sys.stderr,
            )
            return 0.5  # Default neutral score on error

    def _build_llm_evaluation_prompt(self, thought: ToTThoughtNode, query: str) -> str:
        """Build prompt for LLM evaluation"""
        return f"""Evaluate the quality of this reasoning step on a scale of 0 to 10.

Original Question: {query}

Reasoning Step:
{thought.thought}

Consider:
- Relevance to the question
- Logical soundness
- Depth of analysis
- Progress toward solving the problem

Respond with ONLY a number from 0 to 10 (e.g., "7" or "8.5"), followed by a brief justification.

Score:
"""

    def _parse_llm_score(self, text: str) -> float:
        """Parse score from LLM response"""
        # Look for numbers 0-10 in the response
        patterns = [
            r"\b(10|9|8|7|6|5|4|3|2|1|0)\b",
            r"\b(\d+\.\d+)\b",
        ]

        for pattern in patterns:
            match = re.search(pattern, text)
            if match:
                try:
                    score = float(match.group(1))
                    # Normalize 0-10 scale to 0-1
                    return min(1.0, max(0.0, score / 10.0))
                except ValueError:
                    continue

        # Fallback: look for percentage
        percent_match = re.search(r"\d+%", text)
        if percent_match:
            try:
                percent_str = percent_match.group(0).rstrip("%")
                percent = float(percent_str)
                return percent / 100.0
            except ValueError:
                pass

        # Default if parsing fails
        return 0.5

    # MARK: - Semantic Similarity Evaluation (30% weight)

    def _evaluate_semantic_similarity(
        self,
        thought: ToTThoughtNode,
        query: str,
        all_thoughts: list[ToTThoughtNode],
    ) -> float:
        """Evaluate using semantic similarity to query and other thoughts"""
        if not self._embeddings:
            self.initialize()
            if not self._embeddings:
                return self._compute_text_similarity(thought.thought, query)

        # Compute similarity to query
        query_similarity = self._compute_semantic_similarity(
            thought.thought, query
        )

        # Compute average similarity to other thoughts at same depth
        same_depth_thoughts = [
            t for t in all_thoughts
            if t.depth == thought.depth and t.id != thought.id
        ]
        thought_similarities: list[float] = []

        for other_thought in same_depth_thoughts:
            similarity = self._compute_semantic_similarity(
                thought.thought, other_thought.thought
            )
            thought_similarities.append(similarity)

        avg_thought_similarity = (
            sum(thought_similarities) / len(thought_similarities)
            if thought_similarities
            else 0.5
        )

        # Combine: high similarity to query is good, moderate similarity to other thoughts is good
        # (not too similar, not too different)
        diversity_score = 1.0 - abs(avg_thought_similarity - 0.5) * 2.0  # Peak at 0.5 similarity
        combined_score = (query_similarity * 0.7) + (diversity_score * 0.3)

        return max(0.0, min(1.0, combined_score))

    def _compute_semantic_similarity(self, text1: str, text2: str) -> float:
        """Compute semantic similarity between two texts using embeddings"""
        if not self._embeddings:
            return self._compute_text_similarity(text1, text2)

        try:
            # Generate embeddings for both texts
            embedding1_result = self._embeddings.execute(
                "generate", {"text": text1}
            )
            embedding2_result = self._embeddings.execute(
                "generate", {"text": text2}
            )

            # Extract embeddings
            embedding1 = embedding1_result.get("embedding")
            embedding2 = embedding2_result.get("embedding")

            if not embedding1 or not embedding2:
                return self._compute_text_similarity(text1, text2)

            # Ensure embeddings are lists of floats
            if isinstance(embedding1, list) and isinstance(embedding2, list):
                if len(embedding1) != len(embedding2):
                    return self._compute_text_similarity(text1, text2)

                # Compute cosine similarity
                return self._cosine_similarity(
                    [float(x) for x in embedding1],
                    [float(x) for x in embedding2],
                )
            else:
                return self._compute_text_similarity(text1, text2)

        except Exception:
            return self._compute_text_similarity(text1, text2)

    def _cosine_similarity(self, a: list[float], b: list[float]) -> float:
        """Compute cosine similarity between two embedding vectors"""
        if len(a) != len(b):
            return 0.0

        dot_product = sum(x * y for x, y in zip(a, b))
        norm_a = sum(x * x for x in a) ** 0.5
        norm_b = sum(x * x for x in b) ** 0.5

        denominator = norm_a * norm_b
        if denominator == 0:
            return 0.0

        return max(0.0, min(1.0, dot_product / denominator))

    def _compute_text_similarity(self, text1: str, text2: str) -> float:
        """Fallback text-based similarity using Jaccard similarity"""
        words1 = set(
            word.lower()
            for word in text1.split()
            if len(word) > 2 and word.isalnum()
        )
        words2 = set(
            word.lower()
            for word in text2.split()
            if len(word) > 2 and word.isalnum()
        )

        if not words1 or not words2:
            return 0.0

        intersection = words1.intersection(words2)
        union = words1.union(words2)

        return len(intersection) / len(union) if union else 0.0

    # MARK: - Heuristic Evaluation (30% weight)

    def _evaluate_heuristics(self, thought: ToTThoughtNode, query: str) -> float:
        """Evaluate using heuristic metrics"""
        score: float = 0.5  # Start with neutral

        thought_text = thought.thought
        thought_length = len(thought_text)
        lower_thought = thought_text.lower()

        # Factor 1: Thought length (not too short, not too long)
        if 200 <= thought_length <= 2000:
            score += 0.15
        elif thought_length < 50:
            score -= 0.2  # Too short
        elif thought_length > 5000:
            score -= 0.1  # Potentially too verbose

        # Factor 2: Step indicators (shows structured reasoning)
        step_indicators = [
            "step",
            "first",
            "then",
            "next",
            "finally",
            "conclusion",
            "therefore",
            "because",
            "thus",
            "hence",
        ]
        step_count = sum(
            lower_thought.count(indicator) for indicator in step_indicators
        )

        if step_count >= 3:
            score += 0.15
        elif step_count >= 1:
            score += 0.1

        # Factor 3: Logical connectors (indicates coherent reasoning)
        logical_connectors = [
            "because",
            "therefore",
            "thus",
            "hence",
            "consequently",
            "as a result",
            "if",
            "then",
            "since",
        ]
        connector_count = sum(
            lower_thought.count(connector) for connector in logical_connectors
        )

        if connector_count >= 2:
            score += 0.1
        elif connector_count >= 1:
            score += 0.05

        # Factor 4: Question keywords relevance
        query_words = set(
            word.lower()
            for word in query.split()
            if len(word) > 3
        )
        thought_words = set(
            word.lower()
            for word in lower_thought.split()
            if len(word) > 3
        )
        relevant_words = query_words.intersection(thought_words)

        if query_words:
            relevance_ratio = len(relevant_words) / len(query_words)
            score += relevance_ratio * 0.2

        # Factor 5: Depth appropriateness (deeper thoughts should be more detailed)
        if thought.depth >= 3 and thought_length > 300:
            score += 0.1  # Deeper thoughts benefit from detail
        elif thought.depth <= 1 and thought_length > 100:
            score += 0.1  # Early thoughts should be concise but informative

        # Cap score between 0.0 and 1.0
        return max(0.0, min(1.0, score))


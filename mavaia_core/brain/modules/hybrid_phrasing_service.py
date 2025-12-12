"""
Hybrid Phrasing Service
Service that blends Markov chain predictions with learned phrase embeddings
Converted from Swift HybridPhrasingService.swift
"""

from typing import Any, Dict, List, Optional
import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent))

from mavaia_core.brain.base_module import BaseBrainModule, ModuleMetadata


class PhraseCandidate:
    """Candidate phrase with scoring information"""

    def __init__(
        self,
        text: str,
        markov_probability: float,
        semantic_score: float,
        hybrid_score: float,
        source: str,  # "markov" or "embedding"
    ):
        self.text = text
        self.markov_probability = markov_probability
        self.semantic_score = semantic_score
        self.hybrid_score = hybrid_score
        self.source = source


class HybridPhrasingServiceModule(BaseBrainModule):
    """Service for hybrid phrase generation combining Markov chains and embeddings"""

    def __init__(self):
        self.markov_builder = None
        self.python_brain_service = None
        self.embedding_cache = None
        self.config_manager = None
        self._modules_loaded = False

    @property
    def metadata(self) -> ModuleMetadata:
        return ModuleMetadata(
            name="hybrid_phrasing_service",
            version="1.0.0",
            description="Service that blends Markov chain predictions with learned phrase embeddings",
            operations=[
                "generate_hybrid_phrase",
                "blend_phrases",
                "score_candidates",
            ],
            dependencies=[],
            model_required=False,
        )

    def initialize(self) -> bool:
        """Initialize the module"""
        return True

    def _ensure_modules_loaded(self):
        """Lazy load dependent modules"""
        if self._modules_loaded:
            return

        try:
            from module_registry import ModuleRegistry

            self.markov_builder = ModuleRegistry.get_module("markov_chain_builder")
            self.python_brain_service = ModuleRegistry.get_module("python_brain_service")
            self.embedding_cache = ModuleRegistry.get_module("phrase_embedding_cache_service")
            self.config_manager = ModuleRegistry.get_module("hybrid_phrasing_config")

            self._modules_loaded = True
        except Exception as e:
            print(f"Error loading modules: {e}")

    def execute(self, operation: str, params: Dict[str, Any]) -> Dict[str, Any]:
        """Execute an operation"""
        self._ensure_modules_loaded()

        if operation == "generate_hybrid_phrase":
            return self._generate_hybrid_phrase(params)
        elif operation == "blend_phrases":
            return self._blend_phrases(params)
        elif operation == "score_candidates":
            return self._score_candidates(params)
        else:
            raise ValueError(f"Unknown operation: {operation}")

    def _generate_hybrid_phrase(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Generate hybrid phrase blending Markov chains and phrase embeddings"""
        context = params.get("context", "")
        keyword = params.get("keyword")
        personality_id = params.get("personality_id")
        max_length = params.get("max_length", 15)

        if not personality_id:
            return {
                "success": False,
                "error": "Personality ID is required",
            }

        # Get configuration for this personality
        config = {}
        if self.config_manager:
            config_result = self.config_manager.execute(
                "get_configuration",
                {"personality_id": personality_id}
            )
            config = config_result.get("result", {})

        markov_count = config.get("markov_candidate_count", 5)
        embedding_count = config.get("embedding_candidate_count", 5)
        similarity_threshold = config.get("similarity_threshold", 0.7)

        # Generate candidates
        markov_candidates = self._generate_markov_candidates(
            context, keyword, personality_id, markov_count, max_length
        )

        embedding_candidates = self._generate_embedding_candidates(
            context, keyword, personality_id, embedding_count, similarity_threshold
        )

        # Combine all candidates
        all_candidates = markov_candidates + embedding_candidates

        if not all_candidates:
            return {
                "success": False,
                "error": "No candidates generated",
            }

        # Score all candidates
        scored_candidates = self._score_candidates_internal(
            all_candidates, context, personality_id
        )

        # Rank candidates by hybrid score
        ranked_candidates = sorted(
            scored_candidates,
            key=lambda c: c.hybrid_score,
            reverse=True,
        )

        # Return top-ranked candidate
        top_candidate = ranked_candidates[0] if ranked_candidates else None

        return {
            "success": True,
            "result": {
                "phrase": top_candidate.text if top_candidate else None,
                "score": top_candidate.hybrid_score if top_candidate else 0.0,
                "source": top_candidate.source if top_candidate else None,
            },
        }

    def _blend_phrases(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Blend phrases (alias for generate_hybrid_phrase)"""
        return self._generate_hybrid_phrase(params)

    def _score_candidates(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Score phrase candidates"""
        candidates_data = params.get("candidates", [])
        context = params.get("context", "")
        personality_id = params.get("personality_id", "")

        candidates = [
            PhraseCandidate(
                text=c.get("text", ""),
                markov_probability=c.get("markov_probability", 0.0),
                semantic_score=c.get("semantic_score", 0.0),
                hybrid_score=c.get("hybrid_score", 0.0),
                source=c.get("source", "markov"),
            )
            for c in candidates_data
        ]

        scored = self._score_candidates_internal(candidates, context, personality_id)

        return {
            "success": True,
            "result": {
                "candidates": [
                    {
                        "text": c.text,
                        "markov_probability": c.markov_probability,
                        "semantic_score": c.semantic_score,
                        "hybrid_score": c.hybrid_score,
                        "source": c.source,
                    }
                    for c in scored
                ],
            },
        }

    def _generate_markov_candidates(
        self,
        context: str,
        keyword: Optional[str],
        personality_id: str,
        count: int,
        max_length: int,
    ) -> List[PhraseCandidate]:
        """Generate candidates from Markov chains"""
        candidates = []

        if not self.markov_builder:
            return candidates

        for _ in range(count):
            try:
                if keyword:
                    result = self.markov_builder.execute(
                        "generate_phrase",
                        {
                            "keyword": keyword,
                            "length": max_length,
                            "personality_id": personality_id,
                        }
                    )
                else:
                    # Complete phrase from context
                    context_words = context.split()
                    if context_words:
                        start_words = " ".join(context_words[-3:])
                        result = self.markov_builder.execute(
                            "complete_phrase",
                            {
                                "start": start_words,
                                "max_length": max_length,
                                "personality_id": personality_id,
                            }
                        )
                    else:
                        continue

                phrase = result.get("result", {}).get("phrase")
                if phrase:
                    candidates.append(
                        PhraseCandidate(
                            text=phrase,
                            markov_probability=result.get("result", {}).get("probability", 0.5),
                            semantic_score=0.0,  # Will be calculated later
                            hybrid_score=0.0,  # Will be calculated later
                            source="markov",
                        )
                    )
            except Exception:
                continue

        return candidates

    def _generate_embedding_candidates(
        self,
        context: str,
        keyword: Optional[str],
        personality_id: str,
        count: int,
        similarity_threshold: float,
    ) -> List[PhraseCandidate]:
        """Generate candidates from phrase embeddings"""
        candidates = []

        if not self.embedding_cache:
            return candidates

        try:
            result = self.embedding_cache.execute(
                "find_similar_phrases",
                {
                    "query": keyword or context,
                    "personality_id": personality_id,
                    "count": count,
                    "similarity_threshold": similarity_threshold,
                }
            )

            similar_phrases = result.get("result", {}).get("phrases", [])
            for phrase_data in similar_phrases:
                candidates.append(
                    PhraseCandidate(
                        text=phrase_data.get("text", ""),
                        markov_probability=0.0,
                        semantic_score=phrase_data.get("similarity", 0.0),
                        hybrid_score=0.0,  # Will be calculated later
                        source="embedding",
                    )
                )
        except Exception:
            pass

        return candidates

    def _score_candidates_internal(
        self,
        candidates: List[PhraseCandidate],
        context: str,
        personality_id: str,
    ) -> List[PhraseCandidate]:
        """Score candidates with multi-level semantic scoring"""
        scored = []

        for candidate in candidates:
            # Calculate hybrid score (weighted combination)
            # Default weights: 0.4 for markov, 0.6 for semantic
            hybrid_score = (
                0.4 * candidate.markov_probability +
                0.6 * candidate.semantic_score
            )

            scored.append(
                PhraseCandidate(
                    text=candidate.text,
                    markov_probability=candidate.markov_probability,
                    semantic_score=candidate.semantic_score,
                    hybrid_score=hybrid_score,
                    source=candidate.source,
                )
            )

        return scored


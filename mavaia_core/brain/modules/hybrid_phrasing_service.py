"""
Hybrid Phrasing Service
Service that blends Markov chain predictions with learned phrase embeddings
Converted from Swift HybridPhrasingService.swift
"""

from typing import Any, Dict, List, Optional
import logging

from mavaia_core.brain.base_module import BaseBrainModule, ModuleMetadata
from mavaia_core.brain.registry import ModuleRegistry
from mavaia_core.exceptions import InvalidParameterError

logger = logging.getLogger(__name__)


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
        super().__init__()
        self.markov_builder = None
        self.python_brain_service = None
        self.embedding_cache = None
        self.universal_voice_engine = None
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
            self.markov_builder = ModuleRegistry.get_module("markov_chain_builder")
            self.python_brain_service = ModuleRegistry.get_module("python_brain_service")
            self.embedding_cache = ModuleRegistry.get_module("phrase_embedding_cache_service")
            
            try:
                self.universal_voice_engine = ModuleRegistry.get_module("universal_voice_engine")
            except Exception as e:
                logger.debug(
                    "universal_voice_engine not available for hybrid_phrasing_service",
                    exc_info=True,
                    extra={"module_name": "hybrid_phrasing_service", "error_type": type(e).__name__},
                )

            self._modules_loaded = True
        except Exception as e:
            logger.debug(
                "Failed to load hybrid_phrasing_service dependencies",
                exc_info=True,
                extra={"module_name": "hybrid_phrasing_service", "error_type": type(e).__name__},
            )

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
            raise InvalidParameterError(
                parameter="operation",
                value=operation,
                reason="Unknown operation for hybrid_phrasing_service",
            )

    def _generate_hybrid_phrase(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Generate hybrid phrase blending Markov chains and phrase embeddings"""
        context = params.get("context", "")
        keyword = params.get("keyword")
        voice_context = params.get("voice_context", {})
        max_length = params.get("max_length", 15)

        # Get configuration from voice_context or use defaults
        # Voice context can influence candidate counts and thresholds
        formality = voice_context.get("formality_level", 0.5)
        technical = voice_context.get("technical_level", 0.3)
        
        # Adjust counts based on voice context
        # More formal/technical = more candidates for precision
        base_markov_count = 5
        base_embedding_count = 5
        if formality > 0.7 or technical > 0.6:
            base_markov_count = 7
            base_embedding_count = 7
        
        markov_count = params.get("markov_count", base_markov_count)
        embedding_count = params.get("embedding_count", base_embedding_count)
        similarity_threshold = params.get("similarity_threshold", 0.7)

        # Generate candidates (no personality_id needed)
        markov_candidates = self._generate_markov_candidates(
            context, keyword, voice_context, markov_count, max_length
        )

        embedding_candidates = self._generate_embedding_candidates(
            context, keyword, voice_context, embedding_count, similarity_threshold
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
            all_candidates, context, voice_context
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
        voice_context = params.get("voice_context", {})

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

        scored = self._score_candidates_internal(candidates, context, voice_context)

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
        voice_context: Dict[str, Any],
        count: int,
        max_length: int,
    ) -> List[PhraseCandidate]:
        """Generate candidates from Markov chains"""
        candidates = []

        if not self.markov_builder:
            return candidates

        for _ in range(count):
            try:
                # Build params without personality_id
                if keyword:
                    markov_params = {
                        "keyword": keyword,
                        "length": max_length,
                    }
                    # Add voice_context if markov_builder supports it
                    if voice_context:
                        markov_params["voice_context"] = voice_context
                    
                    result = self.markov_builder.execute(
                        "generate_phrase",
                        markov_params
                    )
                else:
                    # Complete phrase from context
                    context_words = context.split()
                    if context_words:
                        start_words = " ".join(context_words[-3:])
                        markov_params = {
                            "start": start_words,
                            "max_length": max_length,
                        }
                        # Add voice_context if markov_builder supports it
                        if voice_context:
                            markov_params["voice_context"] = voice_context
                        
                        result = self.markov_builder.execute(
                            "complete_phrase",
                            markov_params
                        )
                    else:
                        continue

                phrase = result.get("result", {}).get("phrase") or result.get("phrase")
                if phrase:
                    probability = result.get("result", {}).get("probability") or result.get("probability", 0.5)
                    candidates.append(
                        PhraseCandidate(
                            text=phrase,
                            markov_probability=probability,
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
        voice_context: Dict[str, Any],
        count: int,
        similarity_threshold: float,
    ) -> List[PhraseCandidate]:
        """Generate candidates from phrase embeddings"""
        candidates = []

        if not self.embedding_cache:
            return candidates

        try:
            # Build params without personality_id
            embedding_params = {
                "query": keyword or context,
                "count": count,
                "similarity_threshold": similarity_threshold,
            }
            # Add voice_context if embedding_cache supports it
            if voice_context:
                embedding_params["voice_context"] = voice_context
            
            result = self.embedding_cache.execute(
                "find_similar_phrases",
                embedding_params
            )

            similar_phrases = result.get("result", {}).get("phrases", []) or result.get("phrases", [])
            for phrase_data in similar_phrases:
                # Handle both dict and direct similarity value
                if isinstance(phrase_data, dict):
                    text = phrase_data.get("text", "")
                    similarity = phrase_data.get("similarity", 0.0)
                else:
                    text = str(phrase_data)
                    similarity = 0.5  # Default similarity
                
                candidates.append(
                    PhraseCandidate(
                        text=text,
                        markov_probability=0.0,
                        semantic_score=similarity,
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
        voice_context: Dict[str, Any],
    ) -> List[PhraseCandidate]:
        """Score candidates with multi-level semantic scoring"""
        scored = []

        # Adjust weights based on voice context if available
        markov_weight = 0.4
        semantic_weight = 0.6
        
        if voice_context:
            # More technical/formal = slightly favor semantic (precision)
            technical = voice_context.get("technical_level", 0.3)
            formality = voice_context.get("formality_level", 0.5)
            if technical > 0.6 or formality > 0.7:
                markov_weight = 0.35
                semantic_weight = 0.65

        for candidate in candidates:
            # Calculate hybrid score (weighted combination)
            hybrid_score = (
                markov_weight * candidate.markov_probability +
                semantic_weight * candidate.semantic_score
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


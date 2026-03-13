from __future__ import annotations
"""
Conversational Orchestrator - Orchestrates all conversational components
Coordinates linguistic priors, social priors, emotional ontology, world knowledge, etc.
Converted from Swift ConversationalOrchestrator.swift
"""

from typing import Any, Dict, List, Optional
import logging
import time

from oricli_core.brain.base_module import BaseBrainModule, ModuleMetadata
from oricli_core.brain.registry import ModuleRegistry
from oricli_core.exceptions import InvalidParameterError

logger = logging.getLogger(__name__)

class ConversationalOrchestratorModule(BaseBrainModule):
    """Orchestrates all conversational Python modules for comprehensive conversation handling"""

    def __init__(self):
        super().__init__()
        self.cognitive_generator = None
        self.linguistic_priors = None
        self.social_priors = None
        self.emotional_inference = None
        self.world_knowledge = None
        self.conversational_memory = None
        self._modules_loaded = False
        self._conversation_history = []
        self._current_emotional_state = "neutral"
        self._relationship_level = "first_interaction"

    @property
    def metadata(self) -> ModuleMetadata:
        return ModuleMetadata(
            name="conversational_orchestrator",
            version="1.0.0",
            description="Orchestrates all conversational components to achieve LLM-level conversational quality",
            operations=[
                "generate_conversational_response",
                "analyze_linguistic_structure",
                "assess_social_context",
                "detect_emotion",
                "enrich_with_knowledge",
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
            self.cognitive_generator = ModuleRegistry.get_module("cognitive_generator")
            self.linguistic_priors = ModuleRegistry.get_module("linguistic_priors")
            self.social_priors = ModuleRegistry.get_module("social_priors")
            self.emotional_inference = ModuleRegistry.get_module("emotional_inference")
            self.world_knowledge = ModuleRegistry.get_module("world_knowledge")
            self.conversational_memory = ModuleRegistry.get_module("conversational_memory")

            self._modules_loaded = True
        except Exception as e:
            # Modules not available - will use fallback methods
            logger.debug(
                "Failed to load one or more conversational dependencies",
                exc_info=True,
                extra={"module_name": "conversational_orchestrator", "error_type": type(e).__name__},
            )

    def execute(self, operation: str, params: Dict[str, Any]) -> Dict[str, Any]:
        """Execute an operation"""
        self._ensure_modules_loaded()

        if operation == "generate_conversational_response":
            return self._generate_conversational_response(params)
        elif operation == "analyze_linguistic_structure":
            return self._analyze_linguistic_structure(params)
        elif operation == "assess_social_context":
            return self._assess_social_context(params)
        elif operation == "detect_emotion":
            return self._detect_emotion(params)
        elif operation == "enrich_with_knowledge":
            return self._enrich_with_knowledge(params)
        else:
            raise InvalidParameterError(
                parameter="operation",
                value=operation,
                reason="Unknown operation for conversational_orchestrator",
            )

    def _generate_conversational_response(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Generate a conversational response using all available components"""
        input_text = params.get("input", "")
        context = params.get("context", "")
        persona = params.get("persona", "oricli")
        conversation_id = params.get("conversation_id")
        external_history = params.get("external_history")

        # Merge external history with internal history if provided
        if external_history:
            self._conversation_history = [
                {
                    "input": h.get("input", ""),
                    "response": h.get("response", ""),
                    "timestamp": time.time(),
                }
                for h in external_history
            ]

        # Step 1-3: Parallelize independent analysis operations
        # Early exit: Skip world knowledge for very short queries (< 3 words)
        should_query_knowledge = len(input_text.split()) > 3

        linguistic_analysis = self._analyze_linguistic_structure({"input": input_text})
        social_context = self._assess_social_context({"input": input_text, "context": context})
        emotional_analysis = self._detect_emotion({"input": input_text, "context": context})

        # World knowledge can run separately (conditional)
        knowledge_context = ""
        if should_query_knowledge:
            knowledge_result = self._enrich_with_knowledge({"query": input_text, "context": context})
            knowledge_context = knowledge_result.get("knowledge", "")

        # Step 4: Generate response using cognitive generator
        history_params = [
            {"input": turn["input"], "response": turn["response"]}
            for turn in self._conversation_history
        ]

        if not self.cognitive_generator:
            return {
                "success": False,
                "error": "Cognitive generator not available",
                "text": "",
                "confidence": 0.0,
            }

        try:
            cognitive_response = self.cognitive_generator.execute("generate_response", {
                "input": input_text,
                "context": f"{context}\n{knowledge_context}".strip(),
                "persona": persona,
                "conversation_history": history_params,
            })

            response_text = cognitive_response.get("text", "")
            confidence = cognitive_response.get("confidence", 0.5)
            diagnostic = cognitive_response.get("diagnostic", {})

            # Step 5: Apply conversational enhancements (simplified)
            # In full implementation, would enhance response based on linguistic/social/emotional context

            # Step 6: Update conversational state
            self._update_conversational_state(
                input_text,
                response_text,
                emotional_analysis.get("primary_emotion", "neutral"),
                social_context,
            )

            # Add to history
            self._conversation_history.append({
                "input": input_text,
                "response": response_text,
                "timestamp": time.time(),
            })

            return {
                "success": True,
                "text": response_text,
                "confidence": confidence,
                "diagnostic": diagnostic,
                "model_used": "cognitive_generator",
            }
        except Exception as e:
            logger.debug(
                "Conversational response generation failed",
                exc_info=True,
                extra={"module_name": "conversational_orchestrator", "error_type": type(e).__name__},
            )
            return {
                "success": False,
                "error": "Conversational response generation failed",
                "text": "",
                "confidence": 0.0,
            }

    def _analyze_linguistic_structure(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze linguistic structure of input"""
        input_text = params.get("input", "")

        if self.linguistic_priors:
            try:
                return self.linguistic_priors.execute("analyze_structure", {
                    "text": input_text,
                })
            except Exception as e:
                logger.debug(
                    "linguistic_priors failed; using fallback analysis",
                    exc_info=True,
                    extra={"module_name": "conversational_orchestrator", "error_type": type(e).__name__},
                )

        # Fallback: simple analysis
        return {
            "complexity": len(input_text.split()) / 10.0,
            "formality": 0.5,
            "structure": "simple",
        }

    def _assess_social_context(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Assess social context"""
        input_text = params.get("input", "")
        context = params.get("context", "")

        if self.social_priors:
            try:
                return self.social_priors.execute("assess_context", {
                    "input": input_text,
                    "context": context,
                })
            except Exception as e:
                logger.debug(
                    "social_priors failed; using fallback social context",
                    exc_info=True,
                    extra={"module_name": "conversational_orchestrator", "error_type": type(e).__name__},
                )

        # Fallback: default social context
        return {
            "formality_level": "medium",
            "relationship_level": self._relationship_level,
            "appropriateness_score": 0.8,
        }

    def _detect_emotion(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Detect emotion in input"""
        input_text = params.get("input", "")
        context = params.get("context", "")

        if self.emotional_inference:
            try:
                return self.emotional_inference.execute("detect_emotion", {
                    "text": input_text,
                    "context": context,
                })
            except Exception as e:
                logger.debug(
                    "emotional_inference failed; using fallback emotion",
                    exc_info=True,
                    extra={"module_name": "conversational_orchestrator", "error_type": type(e).__name__},
                )

        # Fallback: neutral emotion
        return {
            "primary_emotion": "neutral",
            "emotion_score": 0.5,
            "emotion_keywords": [],
        }

    def _enrich_with_knowledge(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Enrich with world knowledge"""
        query = params.get("query", "")
        context = params.get("context", "")

        if self.world_knowledge:
            try:
                return self.world_knowledge.execute("enrich_query", {
                    "query": query,
                    "context": context,
                })
            except Exception as e:
                logger.debug(
                    "world_knowledge failed; using empty knowledge context",
                    exc_info=True,
                    extra={"module_name": "conversational_orchestrator", "error_type": type(e).__name__},
                )

        # Fallback: no additional knowledge
        return {
            "knowledge": "",
        }

    def _update_conversational_state(
        self,
        input_text: str,
        response_text: str,
        emotional_context: str,
        social_context: Dict[str, Any],
    ):
        """Update conversational state"""
        self._current_emotional_state = emotional_context
        self._relationship_level = social_context.get("relationship_level", self._relationship_level)


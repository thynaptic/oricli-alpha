from __future__ import annotations
"""
RFAL Engine Module - Conversational Reinforced Award Learning
Handles conflict detection, multi-factor reward calculation, and DPO pair generation.
"""

from typing import Dict, Any, Optional, List
import logging
import time
import re
from pathlib import Path

from mavaia_core.brain.base_module import BaseBrainModule, ModuleMetadata
from mavaia_core.exceptions import (
    InvalidParameterError,
    ModuleInitializationError,
    ModuleOperationError,
)

logger = logging.getLogger(__name__)

class RFALEngine(BaseBrainModule):
    """
    Core engine for alignment through reinforced awards.
    Detects conversational conflicts and aligns the model via DPO pairs.
    """
    
    def __init__(self):
        """Initialize RFAL engine."""
        super().__init__()
        self.config = {}
        self._initialized = False
        self._lesson_buffer: List[Dict[str, Any]] = []
        
        # Conflict detection patterns
        self._rejection_keywords = [
            r"\bno\b", r"\bincorrect\b", r"\bwrong\b", r"\bactually\b",
            r"\bstop\b", r"\bnot what i meant\b", r"\breword\b",
            r"\bfix\b", r"\bbad\b", r"\bhallucination\b"
        ]
        
    @property
    def metadata(self) -> ModuleMetadata:
        """Return module metadata."""
        return ModuleMetadata(
            name="rfal_engine",
            version="1.0.0",
            description="Autonomous alignment via conversational conflict detection and award scoring",
            operations=[
                "process_feedback",
                "calculate_reward",
                "generate_dpo_pair",
                "get_status",
                "clear_buffer",
            ],
            dependencies=[],
            enabled=True,
            model_required=False,
        )
    
    def initialize(self) -> bool:
        """Initialize the module."""
        self._lesson_buffer_path = Path(self.config.get("lesson_buffer_path", "mavaia_core/data/rfal_lessons.jsonl"))
        self._lesson_buffer_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Load custom keywords if any
        custom_keywords = self.config.get("rejection_keywords", [])
        if custom_keywords:
            self._rejection_keywords.extend(custom_keywords)
            
        self._initialized = True
        return True
    
    def execute(self, operation: str, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute module operation.
        """
        if not self._initialized:
            self.initialize()
            
        if operation == "process_feedback":
            return self._process_feedback(params)
        elif operation == "calculate_reward":
            return self._calculate_reward(params)
        elif operation == "generate_dpo_pair":
            return self._generate_dpo_pair(params)
        elif operation == "get_status":
            return self._get_status()
        elif operation == "clear_buffer":
            return self._clear_buffer()
        else:
            raise ValueError(f"Unknown operation: {operation}")

    def _process_feedback(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        Detect conflicts in user feedback and trigger alignment if needed.
        """
        user_input = params.get("user_input")
        last_response = params.get("last_response")
        prompt = params.get("prompt")
        history = params.get("history", [])
        intent = params.get("intent") # Optional, from AdapterRouter
        
        if not user_input or not last_response or not prompt:
            raise InvalidParameterError("Operation 'process_feedback' requires 'user_input', 'last_response', and 'prompt'")
            
        # 1. Conflict Detection
        conflict_signals = []
        if self._detect_keyword_conflict(user_input):
            conflict_signals.append("keyword_rejection")
        if self._detect_sentiment_conflict(user_input):
            conflict_signals.append("negative_sentiment")
        if self._detect_repetition_conflict(user_input, history):
            conflict_signals.append("task_repetition")
            
        is_conflict = len(conflict_signals) > 0
        
        # 2. Multi-Factor Reward Calculation (Phase 2)
        reward_res = self._calculate_reward({
            "is_conflict": is_conflict,
            "response": last_response,
            "intent": intent,
            "prompt": prompt
        })
        reward = reward_res.get("reward", 0.0)
        
        # 3. DPO Pair Generation
        lesson = None
        if reward < 0: # Penalize and align
            lesson = {
                "prompt": prompt,
                "rejected": last_response,
                "chosen": user_input, 
                "reward": reward,
                "signals": conflict_signals,
                "timestamp": time.time(),
                "intent": intent
            }
            self._lesson_buffer.append(lesson)
            self._persist_lesson(lesson)
            
        return {
            "success": True,
            "is_conflict": is_conflict,
            "conflict_signals": conflict_signals,
            "reward": reward,
            "reward_breakdown": reward_res.get("breakdown"),
            "lesson_created": lesson is not None
        }

    def _detect_keyword_conflict(self, text: str) -> bool:
        """Helper to detect if text contains rejection signals."""
        text_lower = text.lower()
        for pattern in self._rejection_keywords:
            if re.search(pattern, text_lower):
                return True
        return False

    def _detect_sentiment_conflict(self, text: str) -> bool:
        """Use emotional_inference to detect negative sentiment."""
        try:
            from mavaia_core.brain.registry import ModuleRegistry
            ei = ModuleRegistry.get_module("emotional_inference")
            if not ei:
                return False
                
            res = ei.execute("infer_emotion", {"text": text})
            # If dominant emotion is negative and high confidence
            emotion = res.get("dominant_emotion", "")
            confidence = res.get("confidence", 0.0)
            
            negative_emotions = ["angry", "frustrated", "disappointed", "upset"]
            if emotion in negative_emotions and confidence > 0.6:
                return True
        except Exception:
            pass
        return False

    def _detect_repetition_conflict(self, current_input: str, history: List[Any]) -> bool:
        """Detect if the user is repeating a previous request (implicit rejection)."""
        if not history:
            return False
            
        # Extract last few user messages
        user_messages = []
        for msg in history[-6:]: # Look at last 3 turns
            if isinstance(msg, dict):
                if msg.get("role") == "user":
                    user_messages.append(msg.get("content", "").lower())
            elif isinstance(msg, str):
                user_messages.append(msg.lower())
                
        if not user_messages:
            return False
            
        current_lower = current_input.lower()
        
        # Check for high similarity with previous user message (simple overlap for now)
        # This implies the first attempt didn't satisfy the user
        last_user_msg = user_messages[-1]
        
        # Simple word overlap ratio
        words1 = set(current_lower.split())
        words2 = set(last_user_msg.split())
        if not words1 or not words2:
            return False
            
        overlap = len(words1.intersection(words2)) / max(len(words1), len(words2))
        return overlap > 0.8 # Highly similar re-prompt

    def _calculate_reward(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Weighted multi-factor reward scoring."""
        is_conflict = params.get("is_conflict", False)
        response = params.get("response", "")
        intent = params.get("intent")
        prompt = params.get("prompt", "")
        
        # Weights
        W_HITL = 0.6
        W_FACT = 0.3
        W_TONE = 0.1
        
        scores = {}
        
        # 1. HITL Score
        scores["hitl"] = -1.0 if is_conflict else 1.0
        
        # 2. Factual Score (cross-reference world_knowledge)
        scores["fact"] = 0.0
        try:
            from mavaia_core.brain.registry import ModuleRegistry
            wk = ModuleRegistry.get_module("world_knowledge")
            if wk:
                # Simple check: does it look like a factual claim?
                # For Phase 2, we just ask WK to validate the response against the prompt
                fact_res = wk.execute("validate_fact", {"text": response, "context": prompt})
                # If valid=False, strong penalty
                if fact_res.get("valid") is False:
                    scores["fact"] = -1.0
                elif fact_res.get("valid") is True:
                    scores["fact"] = 1.0
        except Exception as e:
            logger.debug(f"Factual scoring skipped: {e}")
            
        # 3. Tone Score (cross-reference AdapterRouter)
        scores["tone"] = 0.0
        try:
            from mavaia_core.brain.registry import ModuleRegistry
            ar = ModuleRegistry.get_module("adapter_router")
            if ar and response:
                # Check if current response tone matches expected intent
                tone_res = ar.execute("route_input", {"text": response})
                detected_intent = tone_res.get("intent")
                if intent and detected_intent:
                    scores["tone"] = 1.0 if detected_intent == intent else -0.5
        except Exception as e:
            logger.debug(f"Tone scoring skipped: {e}")
            
        # Weighted sum
        total_reward = (scores["hitl"] * W_HITL) + (scores["fact"] * W_FACT) + (scores["tone"] * W_TONE)
        
        return {
            "success": True,
            "reward": float(total_reward),
            "breakdown": scores
        }

    def _persist_lesson(self, lesson: Dict[str, Any]):
        """Append lesson to local JSONL file."""
        import json
        try:
            with open(self._lesson_buffer_path, "a", encoding="utf-8") as f:
                f.write(json.dumps(lesson) + "\n")
        except Exception as e:
            logger.error(f"Failed to persist RFAL lesson: {e}")

    def _generate_dpo_pair(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        Manually generate a Chosen/Rejected triplet if not from organic feedback.
        """
        prompt = params.get("prompt")
        chosen = params.get("chosen")
        rejected = params.get("rejected")
        
        if not all([prompt, chosen, rejected]):
            raise InvalidParameterError("Operation 'generate_dpo_pair' requires 'prompt', 'chosen', and 'rejected'")
            
        lesson = {
            "prompt": prompt,
            "chosen": chosen,
            "rejected": rejected,
            "reward": -1.0,
            "source": "manual",
            "timestamp": time.time()
        }
        self._lesson_buffer.append(lesson)
        self._persist_lesson(lesson)
        
        return {"success": True, "lesson": lesson}

    def _get_status(self) -> Dict[str, Any]:
        """Return module status and buffer info."""
        return {
            "success": True,
            "buffer_size": len(self._lesson_buffer),
            "initialized": self._initialized
        }

    def _clear_buffer(self) -> Dict[str, Any]:
        """Clear the in-memory lesson buffer."""
        self._lesson_buffer = []
        return {"success": True}

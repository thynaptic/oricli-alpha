from __future__ import annotations
"""
Constraint Application System

Applies optional constraints to test execution including time/token limits,
memory continuity, safety posture, and tool usage restrictions.
"""

import time
from typing import Any, Dict, Optional
from contextlib import contextmanager

from oricli_core.evaluation.curriculum.models import (
    OptionalConstraints,
    MemoryContinuityMode,
    SafetyPosture,
)


class ConstraintManager:
    """Manages application of constraints during test execution"""
    
    def __init__(self, constraints: OptionalConstraints):
        """
        Initialize constraint manager
        
        Args:
            constraints: Optional constraints to apply
        """
        self.constraints = constraints
        self.start_time: Optional[float] = None
        self.token_count: int = 0
        self.memory_context: Dict[str, Any] = {}
        self.memory_turns: list = []
        self.memory_corruption_detected: bool = False
    
    @contextmanager
    def execution_context(self):
        """Context manager for test execution with constraints"""
        self.start_time = time.time()
        self.token_count = 0
        self.memory_corruption_detected = False
        
        try:
            yield self
        finally:
            # Cleanup if needed
            pass
    
    def check_time_bound(self) -> bool:
        """
        Check if time bound constraint is satisfied
        
        Returns:
            True if within time bound, False if exceeded
        """
        if self.constraints.time_bound is None:
            return True
        
        if self.start_time is None:
            return True
        
        elapsed = time.time() - self.start_time
        return elapsed <= self.constraints.time_bound
    
    def check_token_bound(self) -> bool:
        """
        Check if token bound constraint is satisfied
        
        Returns:
            True if within token bound, False if exceeded
        """
        if self.constraints.token_bound is None:
            return True
        
        return self.token_count <= self.constraints.token_bound
    
    def record_tokens(self, count: int) -> None:
        """Record token usage"""
        self.token_count += count
    
    def setup_memory_continuity(self) -> Dict[str, Any]:
        """
        Setup memory continuity based on constraint mode
        
        Returns:
            Memory configuration dictionary
        """
        if self.constraints.memory_continuity == MemoryContinuityMode.OFF:
            return {
                "enabled": False,
                "max_history_length": 0,
                "reference_window": 0,
            }
        elif self.constraints.memory_continuity == MemoryContinuityMode.SHORT_TERM:
            return {
                "enabled": True,
                "max_history_length": 5,
                "reference_window": 5,
                "topic_continuity_threshold": 0.5,
                "entity_tracking": {
                    "enabled": True,
                    "max_entities": 50,
                    "entity_decay": 0.9,
                },
            }
        elif self.constraints.memory_continuity == MemoryContinuityMode.LONG_TERM_BOUNDED:
            return {
                "enabled": True,
                "max_history_length": 20,
                "reference_window": 5,
                "topic_continuity_threshold": 0.5,
                "entity_tracking": {
                    "enabled": True,
                    "max_entities": 50,
                    "entity_decay": 0.9,
                },
            }
        else:
            return {"enabled": False}
    
    def track_memory_turn(self, turn_data: Dict[str, Any]) -> None:
        """
        Track a memory turn for continuity checking
        
        Args:
            turn_data: Turn data including text, topic, entities
        """
        if self.constraints.memory_continuity == MemoryContinuityMode.OFF:
            return
        
        self.memory_turns.append(turn_data)
        
        # Enforce max history length
        if self.constraints.memory_continuity == MemoryContinuityMode.SHORT_TERM:
            max_length = 5
        else:  # LONG_TERM_BOUNDED
            max_length = 20
        
        if len(self.memory_turns) > max_length:
            self.memory_turns = self.memory_turns[-max_length:]
    
    def detect_memory_corruption(self) -> Dict[str, Any]:
        """
        Detect memory corruption based on continuity checks
        
        Returns:
            Dictionary with corruption detection results
        """
        if self.constraints.memory_continuity == MemoryContinuityMode.OFF:
            return {"corruption_detected": False}
        
        if len(self.memory_turns) < 2:
            return {"corruption_detected": False}
        
        corruption_indicators = []
        
        # Check for abrupt topic shifts
        if len(self.memory_turns) >= 2:
            current_turn = self.memory_turns[-1]
            previous_turn = self.memory_turns[-2]
            
            current_words = set(current_turn.get("text", "").lower().split())
            previous_words = set(previous_turn.get("text", "").lower().split())
            
            if current_words and previous_words:
                overlap = len(current_words & previous_words)
                overlap_ratio = overlap / max(len(current_words), len(previous_words))
                
                if overlap_ratio < 0.3:
                    corruption_indicators.append("abrupt_topic_shift")
                    self.memory_corruption_detected = True
        
        # Check for inconsistent entity references
        if len(self.memory_turns) >= 3:
            entities = {}
            for turn in self.memory_turns[-3:]:
                turn_entities = turn.get("entities", {})
                for entity, value in turn_entities.items():
                    if entity in entities and entities[entity] != value:
                        corruption_indicators.append("inconsistent_entity_reference")
                        self.memory_corruption_detected = True
                        break
                    entities[entity] = value
        
        # Check for contradictory statements (simplified)
        # In full implementation, would use more sophisticated contradiction detection
        
        return {
            "corruption_detected": self.memory_corruption_detected,
            "indicators": corruption_indicators,
            "continuity_score": overlap_ratio if len(self.memory_turns) >= 2 else 1.0,
        }
    
    def get_safety_posture_config(self) -> Dict[str, Any]:
        """
        Get safety posture configuration
        
        Returns:
            Safety posture configuration dictionary
        """
        posture_configs = {
            SafetyPosture.NORMAL: {
                "mode": "normal",
                "strictness": 0.5,
                "intervention_threshold": 0.8,
            },
            SafetyPosture.SUPPORTIVE: {
                "mode": "supportive",
                "strictness": 0.3,
                "intervention_threshold": 0.9,
            },
            SafetyPosture.INTERVENTION: {
                "mode": "intervention",
                "strictness": 0.7,
                "intervention_threshold": 0.6,
            },
            SafetyPosture.HIGH_RISK_OVERRIDE: {
                "mode": "high_risk_override",
                "strictness": 0.9,
                "intervention_threshold": 0.4,
            },
        }
        
        return posture_configs.get(
            self.constraints.safety_posture,
            posture_configs[SafetyPosture.NORMAL]
        )
    
    def check_tool_usage_allowed(self) -> bool:
        """
        Check if tool usage is allowed
        
        Returns:
            True if tool usage is allowed, False otherwise
        """
        return self.constraints.tool_usage_allowed
    
    def get_mcts_depth_limit(self) -> Optional[int]:
        """
        Get MCTS depth limit if specified
        
        Returns:
            MCTS depth limit or None
        """
        return self.constraints.mcts_depth
    
    def validate_constraints(self) -> Dict[str, Any]:
        """
        Validate that all constraints are satisfied
        
        Returns:
            Validation result dictionary
        """
        results = {
            "valid": True,
            "violations": [],
        }
        
        if not self.check_time_bound():
            results["valid"] = False
            results["violations"].append("time_bound_exceeded")
        
        if not self.check_token_bound():
            results["valid"] = False
            results["violations"].append("token_bound_exceeded")
        
        return results


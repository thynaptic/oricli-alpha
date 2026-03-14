from __future__ import annotations
"""
Metacognitive Sentinel Module - Self-regulation and Cognitive Health
Detects looping, hallucination, and high entropy in reasoning paths.
Applies DBT/CBT-inspired heuristics (Radical Acceptance, Wise Mind) to recover.
"""

import time
import logging
import re
from typing import List, Dict, Any, Optional

from oricli_core.brain.base_module import BaseBrainModule, ModuleMetadata
from oricli_core.brain.registry import ModuleRegistry
from oricli_core.exceptions import InvalidParameterError

logger = logging.getLogger(__name__)

from oricli_core.brain.swarm_bus import get_swarm_bus, SwarmMessage, MessageProtocol

class MetacognitiveSentinelModule(BaseBrainModule):
    """Monitors and regulates OricliAlpha's cognitive state."""

    def __init__(self) -> None:
        super().__init__()
        self.volatility_threshold = 0.7
        self.repetition_threshold = 0.4
        self.subconscious_field = None
        self.bus = get_swarm_bus()
        self._monitored_sessions: Dict[str, List[str]] = {} # session_id -> message contents

    @property
    def metadata(self) -> ModuleMetadata:
        return ModuleMetadata(
            name="metacognitive_sentinel",
            version="1.1.0",
            description="Cognitive executive function: monitors for loops/hallucinations and applies DBT/CBT recovery skills",
            operations=[
                "assess_cognitive_health",
                "apply_radical_acceptance",
                "apply_wise_mind",
                "trigger_reset",
                "start_monitoring"
            ],
            dependencies=["subconscious_field", "swarm_bus"],
            model_required=False,
        )

    def initialize(self) -> bool:
        # We don't start monitoring by default to avoid noise, 
        # but it can be triggered by the Broker or Coordinator.
        return True

    def execute(self, operation: str, params: Dict[str, Any]) -> Dict[str, Any]:
        if operation == "assess_cognitive_health":
            return self._assess_health(params)
        elif operation == "apply_radical_acceptance":
            return self._apply_radical_acceptance(params)
        elif operation == "apply_wise_mind":
            return self._apply_wise_mind(params)
        elif operation == "trigger_reset":
            return self._trigger_reset(params)
        elif operation == "start_monitoring":
            self.bus.subscribe("tasks.result.*", self._on_bus_message)
            return {"success": True, "status": "monitoring_bus"}
        else:
            raise InvalidParameterError(parameter="operation", value=operation, reason="Unsupported operation")

    def _on_bus_message(self, message: SwarmMessage):
        """Monitor Swarm Bus results for entropy."""
        topic = message.topic
        # Extract task_id/session_id from topic (e.g. tasks.result.<id>)
        task_id = topic.split(".")[-1]
        
        if task_id not in self._monitored_sessions:
            self._monitored_sessions[task_id] = []
            
        content = str(message.payload.get("result", ""))
        self._monitored_sessions[task_id].append(content)
        
        # Periodically assess
        if len(self._monitored_sessions[task_id]) >= 3:
            full_trace = "\n\n".join(self._monitored_sessions[task_id])
            health = self._assess_health({"trace": full_trace})
            
            if health.get("requires_intervention"):
                logger.warning(f"[SENTINEL] Cognitive entropy detected in task {task_id}! Triggering intervention.")
                self._trigger_intervention(task_id, health)

    def _trigger_intervention(self, task_id: str, health: Dict[str, Any]):
        """Publish intervention to the bus to reset agents."""
        intervention_message = SwarmMessage(
            protocol=MessageProtocol.ERROR, # Using ERROR protocol to stop current logic
            topic=f"tasks.error.{task_id}",
            sender_id="metacognitive_sentinel",
            payload={
                "task_id": task_id,
                "error": f"METACOGNITIVE INTERVENTION: {health['cognitive_state']} detected. Reasoning path reset.",
                "intervention_type": "radical_acceptance",
                "instruction": "Your previous reasoning path was circular or high-entropy. Reset your context and approach the goal from a different angle."
            }
        )
        self.bus.publish(intervention_message)

    def _assess_health(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        Analyze current thought trace and metrics for volatility.
        """
        trace = params.get("trace", "")
        module_results = params.get("execution_results", {})
        
        # 1. Repetition Detection (Looping)
        repetition_score = self._calculate_repetition(trace)
        
        # 2. Entropy / Variance Detection
        entropy_score = self._calculate_cognitive_entropy(module_results)
        
        # 3. Determine State
        state = "Focused"
        volatility = (repetition_score + entropy_score) / 2
        
        if repetition_score > self.repetition_threshold:
            state = "Looping"
        elif entropy_score > self.volatility_threshold:
            state = "Scattered"
        elif volatility > 0.8:
            state = "Volatile"
            
        return {
            "success": True,
            "cognitive_state": state,
            "volatility": volatility,
            "metrics": {
                "repetition": repetition_score,
                "entropy": entropy_score
            },
            "requires_intervention": (volatility > 0.6) or (repetition_score > 0.8) or (entropy_score > 0.8)
        }

    def _apply_radical_acceptance(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        Skill: Radical Acceptance
        Accept the current failure/loop, detach from the dead-end bias, and reset.
        """
        goal = params.get("goal", "")
        failed_path = params.get("failed_path", "")
        
        _rich_log(f"Sentinel: Applying Radical Acceptance to failed path...", "yellow", "🧘")
        
        # 1. Detach from current bias
        if not self.subconscious_field:
            self.subconscious_field = ModuleRegistry.get_module("subconscious_field")
            
        if self.subconscious_field:
            # Vibrate a 'neutralizing' signal to clear the loop
            self.subconscious_field.execute("vibrate", {
                "text": "Accepting dead-end reasoning path. Clearing local cognitive noise.",
                "weight": -0.5, # Negative weight to dampen recent patterns
                "source": "radical_acceptance"
            })
            
        return {
            "success": True,
            "intervention": "radical_acceptance",
            "instruction": "I accept that this reasoning path is not yielding results. I am resetting my working memory for this node and approaching the goal from a fresh perspective.",
            "action_required": "reroute"
        }

    def _apply_wise_mind(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        Skill: Wise Mind
        Balances raw logic with subconscious bias.
        """
        logic_output = params.get("logic_output", "")
        bias_state = params.get("mental_state", [])
        
        # Implementation would use symbolic weighting to find a balanced response
        return {
            "success": True,
            "intervention": "wise_mind",
            "balanced_context": "Seeking balance between immediate logical module output and long-term mental state bias."
        }

    def _trigger_reset(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Force a hard reset of the cognitive context."""
        return {
            "success": True,
            "action": "clear_working_memory",
            "reload_subconscious": True
        }

    def _calculate_repetition(self, text: str) -> float:
        """Heuristic for token bigram repetition."""
        if not text or len(text) < 50: return 0.0
        words = text.lower().split()
        if len(words) < 10: return 0.0
        
        bigrams = [f"{words[i]} {words[i+1]}" for i in range(len(words)-1)]
        unique_bigrams = set(bigrams)
        
        repetition = 1.0 - (len(unique_bigrams) / len(bigrams))
        return repetition

    def _calculate_cognitive_entropy(self, results: Dict[str, Any]) -> float:
        """Measure the variance/disagreement between different cognitive modules."""
        if not results or len(results) < 2: return 0.0
        
        # Simple heuristic: count of unique 'final_answer' candidates
        answers = []
        for mod, res in results.items():
            if isinstance(res, dict):
                ans = res.get("text") or res.get("answer")
                if ans: answers.append(ans[:100].lower())
        
        if not answers: return 0.0
        unique_answers = set(answers)
        entropy = len(unique_answers) / len(answers)
        return entropy

def _rich_log(message: str, style: str = "white", icon: str = ""):
    prefix = f"{icon} " if icon else ""
    print(f"[{style}]{prefix}{message}")

"""
Memory Dynamics Module - Advanced memory management
Memory importance scoring, forgetting curves, knowledge integration,
freshness weighting, and memory replay
"""

from pathlib import Path
from typing import Any, Dict, List, Optional
from datetime import datetime, timedelta
import math
import sys

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent))

from mavaia_core.brain.base_module import BaseBrainModule, ModuleMetadata


class MemoryDynamicsModule(BaseBrainModule):
    """Manage memory dynamics with importance, decay, and replay"""

    def __init__(self):
        self.memory_store: Dict[str, Dict[str, Any]] = {}

    @property
    def metadata(self) -> ModuleMetadata:
        return ModuleMetadata(
            name="memory_dynamics",
            version="1.0.0",
            description=(
                "Memory dynamics: importance scoring, forgetting curves, "
                "knowledge integration, freshness weighting, memory replay"
            ),
            operations=[
                "score_importance",
                "apply_forgetting_curve",
                "integrate_knowledge",
                "weight_by_freshness",
                "replay_memories",
            ],
            dependencies=[],
            model_required=False,
        )

    def initialize(self) -> bool:
        """Initialize the module"""
        return True

    def execute(self, operation: str, params: Dict[str, Any]) -> Dict[str, Any]:
        """Execute a memory dynamics operation"""
        match operation:
            case "score_importance":
                memory = params.get("memory", {})
                context = params.get("context", {})
                return self.score_importance(memory, context)

            case "apply_forgetting_curve":
                memory = params.get("memory", {})
                time_elapsed = params.get("time_elapsed", 0.0)
                return self.apply_forgetting_curve(memory, time_elapsed)

            case "integrate_knowledge":
                new_memory = params.get("new_memory", {})
                existing_memories = params.get("existing_memories", [])
                return self.integrate_knowledge(new_memory, existing_memories)

            case "weight_by_freshness":
                memories = params.get("memories", [])
                return self.weight_by_freshness(memories)

            case "replay_memories":
                memories = params.get("memories", [])
                count = params.get("count", 5)
                return self.replay_memories(memories, count)

            case _:
                raise ValueError(f"Unknown operation: {operation}")

    def score_importance(
        self, memory: Dict[str, Any], context: Dict[str, Any] = None
    ) -> Dict[str, Any]:
        """Score memory by importance, recency, and relevance"""
        if context is None:
            context = {}

        if not memory:
            return {
                "memory": memory,
                "importance_score": 0.0,
                "factors": {},
            }

        importance_score = 0.0
        factors = {}

        # Recency factor (0.0 to 1.0)
        created_at = memory.get("created_at")
        if created_at:
            try:
                if isinstance(created_at, str):
                    created_time = datetime.fromisoformat(created_at)
                else:
                    created_time = created_at

                time_diff = (datetime.now() - created_time).total_seconds()
                days_ago = time_diff / (24 * 3600)

                # Exponential decay: more recent = higher score
                recency_factor = math.exp(-days_ago / 30.0)  # Half-life of 30 days
                importance_score += recency_factor * 0.3
                factors["recency"] = recency_factor
            except Exception:
                factors["recency"] = 0.5
                importance_score += 0.15
        else:
            factors["recency"] = 0.5
            importance_score += 0.15

        # Access frequency factor
        access_count = memory.get("access_count", 0)
        access_factor = min(1.0, access_count / 10.0)  # Normalize to 10 accesses
        importance_score += access_factor * 0.2
        factors["access_frequency"] = access_factor

        # Relevance factor (if context provided)
        if context:
            memory_content = str(memory.get("content", "")).lower()
            context_text = str(context.get("query", "")).lower()

            if context_text:
                # Simple word overlap
                memory_words = set(memory_content.split())
                context_words = set(context_text.split())
                overlap = memory_words & context_words
                relevance_factor = len(overlap) / max(len(context_words), 1)
                relevance_factor = min(1.0, relevance_factor)
                importance_score += relevance_factor * 0.3
                factors["relevance"] = relevance_factor
            else:
                factors["relevance"] = 0.5
                importance_score += 0.15
        else:
            factors["relevance"] = 0.5
            importance_score += 0.15

        # Explicit importance marker
        explicit_importance = memory.get("importance", 0.5)
        importance_score += explicit_importance * 0.2
        factors["explicit_importance"] = explicit_importance

        # Normalize to 0.0-1.0
        importance_score = min(1.0, max(0.0, importance_score))

        return {
            "memory": memory,
            "importance_score": importance_score,
            "factors": factors,
        }

    def apply_forgetting_curve(
        self, memory: Dict[str, Any], time_elapsed: float
    ) -> Dict[str, Any]:
        """Apply Ebbinghaus forgetting curve with exponential decay"""
        if not memory:
            return {
                "memory": memory,
                "retention": 0.0,
                "decay_applied": False,
            }

        # Ebbinghaus forgetting curve: R = e^(-t/S)
        # where R is retention, t is time, S is strength
        strength = memory.get("strength", 1.0)
        if strength <= 0:
            strength = 1.0

        # Time in hours
        time_hours = time_elapsed

        # Calculate retention (0.0 to 1.0)
        retention = math.exp(-time_hours / (strength * 24.0))

        # Apply decay to importance
        original_importance = memory.get("importance", 0.5)
        decayed_importance = original_importance * retention

        return {
            "memory": memory,
            "retention": retention,
            "decayed_importance": decayed_importance,
            "original_importance": original_importance,
            "time_elapsed_hours": time_hours,
            "decay_applied": True,
        }

    def integrate_knowledge(
        self,
        new_memory: Dict[str, Any],
        existing_memories: List[Dict[str, Any]],
    ) -> Dict[str, Any]:
        """Integrate new knowledge with existing memories"""
        if not new_memory:
            return {
                "integrated": False,
                "new_memory": new_memory,
                "related_memories": [],
                "conflicts": [],
            }

        new_content = str(new_memory.get("content", "")).lower()
        new_words = set(new_content.split())

        related_memories = []
        conflicts = []

        # Find related memories
        for existing in existing_memories:
            existing_content = str(existing.get("content", "")).lower()
            existing_words = set(existing_content.split())

            # Calculate similarity
            overlap = new_words & existing_words
            similarity = len(overlap) / max(len(new_words | existing_words), 1)

            if similarity > 0.2:  # Threshold
                related_memories.append(
                    {
                        "memory": existing,
                        "similarity": similarity,
                        "overlap_words": list(overlap)[:5],
                    }
                )

                # Check for conflicts (contradictory information)
                if self._detect_conflict(new_content, existing_content):
                    conflicts.append(
                        {
                            "new_memory": new_memory,
                            "existing_memory": existing,
                            "conflict_type": "contradiction",
                        }
                    )

        # Sort by similarity
        related_memories.sort(key=lambda x: x["similarity"], reverse=True)

        # Integrate: update existing memories or create new
        integration_strategy = "create_new"
        if related_memories and not conflicts:
            # Merge with most similar memory
            most_similar = related_memories[0]
            if most_similar["similarity"] > 0.7:
                integration_strategy = "merge_with_existing"

        return {
            "integrated": True,
            "new_memory": new_memory,
            "related_memories": related_memories[:5],
            "conflicts": conflicts,
            "integration_strategy": integration_strategy,
        }

    def _detect_conflict(
        self, content1: str, content2: str
    ) -> bool:
        """Detect if two memory contents conflict"""
        # Simple conflict detection: check for opposing keywords
        positive_words = ["yes", "true", "correct", "right", "agree", "support"]
        negative_words = ["no", "false", "incorrect", "wrong", "disagree", "oppose"]

        has_positive1 = any(word in content1 for word in positive_words)
        has_negative1 = any(word in content1 for word in negative_words)
        has_positive2 = any(word in content2 for word in positive_words)
        has_negative2 = any(word in content2 for word in negative_words)

        # Conflict if one is positive and other is negative
        if (has_positive1 and has_negative2) or (has_negative1 and has_positive2):
            # Check if they refer to similar concepts
            words1 = set(content1.split())
            words2 = set(content2.split())
            overlap = words1 & words2
            if len(overlap) >= 3:  # Significant overlap
                return True

        return False

    def weight_by_freshness(
        self, memories: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Weight memories by freshness and access frequency"""
        if not memories:
            return {
                "memories": [],
                "weighted_memories": [],
            }

        weighted_memories = []

        for memory in memories:
            # Calculate freshness weight
            created_at = memory.get("created_at")
            freshness_weight = 0.5  # Default

            if created_at:
                try:
                    if isinstance(created_at, str):
                        created_time = datetime.fromisoformat(created_at)
                    else:
                        created_time = created_at

                    time_diff = (datetime.now() - created_time).total_seconds()
                    days_ago = time_diff / (24 * 3600)

                    # Exponential decay
                    freshness_weight = math.exp(-days_ago / 7.0)  # Half-life of 7 days
                except Exception:
                    pass

            # Calculate access frequency weight
            access_count = memory.get("access_count", 0)
            access_weight = min(1.0, access_count / 5.0)  # Normalize to 5 accesses

            # Combined weight
            combined_weight = (freshness_weight * 0.6) + (access_weight * 0.4)

            weighted_memories.append(
                {
                    "memory": memory,
                    "freshness_weight": freshness_weight,
                    "access_weight": access_weight,
                    "combined_weight": combined_weight,
                }
            )

        # Sort by combined weight
        weighted_memories.sort(key=lambda x: x["combined_weight"], reverse=True)

        return {
            "memories": memories,
            "weighted_memories": weighted_memories,
            "total_count": len(memories),
        }

    def replay_memories(
        self, memories: List[Dict[str, Any]], count: int = 5
    ) -> Dict[str, Any]:
        """Replay important memories to reinforce learning"""
        if not memories:
            return {
                "replayed_memories": [],
                "replay_count": 0,
            }

        # Score importance for all memories
        scored_memories = []
        for memory in memories:
            score_result = self.score_importance(memory)
            scored_memories.append(
                {
                    "memory": memory,
                    "importance_score": score_result["importance_score"],
                }
            )

        # Sort by importance
        scored_memories.sort(
            key=lambda x: x["importance_score"], reverse=True
        )

        # Select top memories for replay
        replayed = scored_memories[:count]

        # Update access count for replayed memories
        for item in replayed:
            memory = item["memory"]
            memory["access_count"] = memory.get("access_count", 0) + 1
            memory["last_accessed"] = datetime.now().isoformat()

        return {
            "replayed_memories": [
                {
                    "memory": item["memory"],
                    "importance_score": item["importance_score"],
                }
                for item in replayed
            ],
            "replay_count": len(replayed),
        }

    def validate_params(self, operation: str, params: Dict[str, Any]) -> bool:
        """Validate parameters for operations"""
        match operation:
            case "score_importance":
                return "memory" in params
            case "apply_forgetting_curve":
                return "memory" in params and "time_elapsed" in params
            case "integrate_knowledge":
                return "new_memory" in params and "existing_memories" in params
            case "weight_by_freshness":
                return "memories" in params
            case "replay_memories":
                return "memories" in params
            case _:
                return True


# Module export
def create_module():
    return MemoryDynamicsModule()


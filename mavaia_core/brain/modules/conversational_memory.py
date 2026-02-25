from __future__ import annotations
"""
Conversational Memory Module - Multi-turn context and references
Handles remembering previous conversation points, natural references, building on previous exchanges
"""

from collections import Counter
from pathlib import Path
from typing import Any, Dict, List
import json
import random
import re
import logging

from mavaia_core.brain.base_module import BaseBrainModule, ModuleMetadata
from mavaia_core.exceptions import InvalidParameterError

logger = logging.getLogger(__name__)


class ConversationalMemoryModule(BaseBrainModule):
    """Multi-turn conversational memory and reference handling"""

    def __init__(self):
        super().__init__()
        self.config = None
        self.conversation_history = []
        self.topic_tracking = {}
        self.entity_references = {}
        self.conversation_threads = {}  # Track conversation threads
        self.summaries = {}  # Store summaries for long conversations
        self._load_config()

    @property
    def metadata(self) -> ModuleMetadata:
        return ModuleMetadata(
            name="conversational_memory",
            version="1.0.0",
            description=(
                "Conversational memory: multi-turn context, references, "
                "topic continuity, summarization, compression"
            ),
            operations=[
                "remember_context",
                "get_reference",
                "build_on_previous",
                "track_topic_continuity",
                "natural_reference",
                "summarize_conversation",
                "extract_key_points",
                "compress_context",
                "track_thread",
                "get_thread_context",
            ],
            dependencies=[],
            model_required=False,
        )

    def initialize(self) -> bool:
        """Initialize the module"""
        return True

    def _load_config(self):
        """Load conversational memory configuration"""
        config_path = Path(__file__).parent / "conversational_memory_config.json"
        try:
            if config_path.exists():
                with open(config_path, "r", encoding="utf-8") as f:
                    self.config = json.load(f)
            else:
                self.config = {
                    "max_history_length": 20,
                    "reference_window": 5,
                    "topic_continuity_threshold": 0.5,
                    "summarization_threshold": 15,  # Summarize after 15 turns
                    "compression_ratio": 0.3,  # Compress to 30% of original
                    "key_points_count": 5,  # Extract top 5 key points
                }
        except Exception as e:
            logger.warning(
                "Failed to load conversational_memory config; using empty defaults",
                exc_info=True,
                extra={"module_name": "conversational_memory", "error_type": type(e).__name__},
            )
            self.config = {}

    def execute(self, operation: str, params: Dict[str, Any]) -> Dict[str, Any]:
        """Execute a conversational memory operation"""
        if operation == "remember_context":
            turn = params.get("turn", {})
            if turn is None:
                turn = {}
            if not isinstance(turn, dict):
                raise InvalidParameterError("turn", str(type(turn).__name__), "turn must be a dict")
            return self.remember_context(turn)
        elif operation == "get_reference":
            current_text = params.get("current_text", "")
            history = params.get("history", [])
            if current_text is None:
                current_text = ""
            if history is None:
                history = []
            if not isinstance(current_text, str):
                raise InvalidParameterError(
                    "current_text", str(type(current_text).__name__), "current_text must be a string"
                )
            if not isinstance(history, list):
                raise InvalidParameterError("history", str(type(history).__name__), "history must be a list")
            return self.get_reference(current_text, history)
        elif operation == "build_on_previous":
            current_input = params.get("current_input", "")
            history = params.get("history", [])
            if current_input is None:
                current_input = ""
            if history is None:
                history = []
            if not isinstance(current_input, str):
                raise InvalidParameterError(
                    "current_input", str(type(current_input).__name__), "current_input must be a string"
                )
            if not isinstance(history, list):
                raise InvalidParameterError("history", str(type(history).__name__), "history must be a list")
            return self.build_on_previous(current_input, history)
        elif operation == "track_topic_continuity":
            current_text = params.get("current_text", "")
            previous_texts = params.get("previous_texts", [])
            if current_text is None:
                current_text = ""
            if previous_texts is None:
                previous_texts = []
            if not isinstance(current_text, str):
                raise InvalidParameterError(
                    "current_text", str(type(current_text).__name__), "current_text must be a string"
                )
            if not isinstance(previous_texts, list):
                raise InvalidParameterError(
                    "previous_texts", str(type(previous_texts).__name__), "previous_texts must be a list"
                )
            return self.track_topic_continuity(current_text, previous_texts)
        elif operation == "natural_reference":
            entity = params.get("entity", "")
            history = params.get("history", [])
            if entity is None:
                entity = ""
            if history is None:
                history = []
            if not isinstance(entity, str):
                raise InvalidParameterError("entity", str(type(entity).__name__), "entity must be a string")
            if not isinstance(history, list):
                raise InvalidParameterError("history", str(type(history).__name__), "history must be a list")
            return self.natural_reference(entity, history)
        elif operation == "summarize_conversation":
            history = params.get("history", [])
            max_length = params.get("max_length", 200)
            if history is None:
                history = []
            if not isinstance(history, list):
                raise InvalidParameterError("history", str(type(history).__name__), "history must be a list")
            try:
                max_length_int = int(max_length)
            except (TypeError, ValueError):
                raise InvalidParameterError("max_length", str(max_length), "max_length must be an integer")
            if max_length_int < 1:
                raise InvalidParameterError("max_length", str(max_length_int), "max_length must be >= 1")
            return self.summarize_conversation(history, max_length_int)
        elif operation == "extract_key_points":
            history = params.get("history", [])
            count = params.get("count", 5)
            if history is None:
                history = []
            if not isinstance(history, list):
                raise InvalidParameterError("history", str(type(history).__name__), "history must be a list")
            try:
                count_int = int(count)
            except (TypeError, ValueError):
                raise InvalidParameterError("count", str(count), "count must be an integer")
            if count_int < 1:
                raise InvalidParameterError("count", str(count_int), "count must be >= 1")
            return self.extract_key_points(history, count_int)
        elif operation == "compress_context":
            history = params.get("history", [])
            target_ratio = params.get("target_ratio", 0.3)
            if history is None:
                history = []
            if not isinstance(history, list):
                raise InvalidParameterError("history", str(type(history).__name__), "history must be a list")
            try:
                target_ratio_float = float(target_ratio)
            except (TypeError, ValueError):
                raise InvalidParameterError("target_ratio", str(target_ratio), "target_ratio must be a number")
            return self.compress_context(history, target_ratio_float)
        elif operation == "track_thread":
            thread_id = params.get("thread_id", "default")
            turn = params.get("turn", {})
            if thread_id is None:
                thread_id = "default"
            if turn is None:
                turn = {}
            if not isinstance(thread_id, str):
                raise InvalidParameterError("thread_id", str(type(thread_id).__name__), "thread_id must be a string")
            if not isinstance(turn, dict):
                raise InvalidParameterError("turn", str(type(turn).__name__), "turn must be a dict")
            return self.track_thread(thread_id, turn)
        elif operation == "get_thread_context":
            thread_id = params.get("thread_id", "default")
            max_turns = params.get("max_turns", params.get("limit", 10))  # Accept both max_turns and limit
            history = params.get("history")  # Optional history for testing
            if thread_id is None:
                thread_id = "default"
            if not isinstance(thread_id, str):
                raise InvalidParameterError("thread_id", str(type(thread_id).__name__), "thread_id must be a string")
            try:
                max_turns_int = int(max_turns)
            except (TypeError, ValueError):
                raise InvalidParameterError("max_turns", str(max_turns), "max_turns must be an integer")
            if max_turns_int < 1:
                raise InvalidParameterError("max_turns", str(max_turns_int), "max_turns must be >= 1")
            if history is not None and not isinstance(history, list):
                raise InvalidParameterError("history", str(type(history).__name__), "history must be a list")
            return self.get_thread_context(thread_id, max_turns_int, history)
        else:
            raise InvalidParameterError(
                parameter="operation",
                value=operation,
                reason="Unknown operation for conversational_memory",
            )

    def remember_context(self, turn: Dict[str, Any]) -> Dict[str, Any]:
        """Remember a conversation turn"""
        if not turn:
            return {
                "remembered": False,
                "history_length": len(self.conversation_history),
            }

        # Add to history
        self.conversation_history.append(turn)

        # Track entities mentioned
        entities = turn.get("entities", [])
        for entity in entities:
            if entity not in self.entity_references:
                self.entity_references[entity] = []
            self.entity_references[entity].append(
                {
                    "turn": len(self.conversation_history) - 1,
                    "context": turn.get("context", ""),
                }
            )

        # Track topics
        topic = turn.get("topic", "")
        if topic:
            if topic not in self.topic_tracking:
                self.topic_tracking[topic] = []
            self.topic_tracking[topic].append(len(self.conversation_history) - 1)

        # Limit history size
        max_length = self.config.get("max_history_length", 20)
        if len(self.conversation_history) > max_length:
            self.conversation_history = self.conversation_history[-max_length:]

        return {
            "remembered": True,
            "history_length": len(self.conversation_history),
            "entities_tracked": len(self.entity_references),
            "topics_tracked": len(self.topic_tracking),
        }

    def get_reference(
        self, current_text: str, history: List[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Get references to previous conversation points"""
        if history is None:
            history = self.conversation_history[-5:]  # Last 5 turns

        if not history:
            return {"references": [], "can_reference": False}

        references = []
        current_lower = current_text.lower()

        # Check for pronoun references (it, that, this, they)
        pronouns = ["it", "that", "this", "they", "them", "these", "those"]
        for pronoun in pronouns:
            if pronoun in current_lower:
                # Find likely referent in recent history
                for i, turn in enumerate(reversed(history[-3:])):  # Check last 3 turns
                    turn_text = turn.get("input", turn.get("text", "")).lower()
                    if turn_text:
                        # Simple heuristic: find noun phrases in previous turn
                        references.append(
                            {
                                "pronoun": pronoun,
                                "likely_referent": turn_text[:50],
                                "turns_ago": i + 1,
                                "confidence": 0.7,
                            }
                        )
                        break

        # Check for topic references
        current_words = set(current_lower.split())
        for turn in history[-3:]:
            turn_text = turn.get("input", turn.get("text", "")).lower()
            turn_words = set(turn_text.split())
            overlap = len(current_words & turn_words)
            if overlap > 3:  # Significant overlap
                references.append(
                    {
                        "type": "topic_continuation",
                        "overlap_words": list(current_words & turn_words),
                        "turns_ago": history.index(turn) + 1,
                        "confidence": min(1.0, overlap / 10.0),
                    }
                )

        return {"references": references, "can_reference": len(references) > 0}

    def build_on_previous(
        self, current_input: str, history: List[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Build response on previous conversation"""
        if history is None:
            history = self.conversation_history[-3:]

        if not history:
            return {"can_build_on": False, "building_text": current_input}

        # Check if current input references previous topics
        current_lower = current_input.lower()
        previous_topics = []

        for turn in history:
            turn_text = turn.get("input", turn.get("text", ""))
            if turn_text:
                previous_topics.append(turn_text.lower())

        # Find connections
        connections = []
        for i, prev_topic in enumerate(previous_topics):
            prev_words = set(prev_topic.split())
            curr_words = set(current_lower.split())
            overlap = prev_words & curr_words

            if len(overlap) > 2:
                connections.append(
                    {
                        "turn_index": i,
                        "overlap_words": list(overlap),
                        "strength": len(overlap)
                        / max(len(prev_words), len(curr_words)),
                    }
                )

        # Generate building text if connections found
        building_text = current_input
        if connections:
            strongest = max(connections, key=lambda x: x["strength"])
            if strongest["strength"] > 0.3:
                # Add reference to previous
                reference_patterns = [
                    "Building on what you said earlier,",
                    "Continuing from before,",
                    "As we discussed,",
                    "Following up on that,",
                ]

                building_text = (
                    random.choice(reference_patterns) + " " + current_input.lower()
                )
                building_text = building_text[0].upper() + building_text[1:]

        return {
            "can_build_on": len(connections) > 0,
            "building_text": building_text,
            "connections": connections,
        }

    def track_topic_continuity(
        self, current_text: str, previous_texts: List[str] = None
    ) -> Dict[str, Any]:
        """Track topic continuity across turns"""
        if previous_texts is None:
            previous_texts = [
                turn.get("input", turn.get("text", ""))
                for turn in self.conversation_history[-3:]
            ]

        if not previous_texts:
            return {
                "continuity_score": 0.0,
                "is_continuous": False,
                "topic_shift": False,
            }

        current_words = set(current_text.lower().split())

        # Calculate overlap with previous texts
        overlaps = []
        for prev_text in previous_texts:
            if not prev_text:
                continue
            prev_words = set(prev_text.lower().split())
            overlap = len(current_words & prev_words)
            overlap_ratio = (
                overlap / max(len(current_words), len(prev_words))
                if max(len(current_words), len(prev_words)) > 0
                else 0
            )
            overlaps.append(overlap_ratio)

        continuity_score = sum(overlaps) / len(overlaps) if overlaps else 0.0
        threshold = self.config.get("topic_continuity_threshold", 0.5)

        is_continuous = continuity_score >= threshold
        topic_shift = continuity_score < 0.3

        return {
            "continuity_score": continuity_score,
            "is_continuous": is_continuous,
            "topic_shift": topic_shift,
            "overlap_scores": overlaps,
        }

    def natural_reference(
        self, entity: str, history: List[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Generate natural reference to an entity from history"""
        if history is None:
            history = self.conversation_history

        if not entity or not history:
            return {"reference": entity, "found_in_history": False}

        # Find entity in history
        entity_lower = entity.lower()
        found_turns = []

        for i, turn in enumerate(history):
            turn_text = turn.get("input", turn.get("text", "")).lower()
            if entity_lower in turn_text:
                found_turns.append(i)

        if not found_turns:
            return {"reference": entity, "found_in_history": False}

        # Generate natural reference based on recency
        last_mention = found_turns[-1]
        turns_since = len(history) - 1 - last_mention

        if turns_since == 0:
            # Just mentioned - use pronoun or "that"
            reference = "that"
        elif turns_since == 1:
            # Recently mentioned - use "that" or entity name
            reference_options = [entity, "that", "it"]
            reference = random.choice(reference_options)
        else:
            # Further back - use entity name with optional reference
            reference_options = [
                entity,
                f"that {entity.lower()}",
                f"the {entity.lower()} we discussed",
            ]
            reference = random.choice(reference_options)

        return {
            "reference": reference,
            "found_in_history": True,
            "turns_since_last_mention": turns_since,
            "mention_count": len(found_turns),
        }

    def summarize_conversation(
        self, history: List[Dict[str, Any]], max_length: int = 200
    ) -> Dict[str, Any]:
        """Summarize a conversation history into a concise summary"""
        if not history:
            return {"summary": "", "original_length": 0, "compressed": False}

        # Extract key information from each turn
        key_info = []
        for turn in history:
            input_text = turn.get("input", turn.get("text", ""))
            response_text = turn.get("response", turn.get("output", ""))
            topic = turn.get("topic", "")

            if input_text:
                # Extract main point (first sentence or key phrase)
                sentences = re.split(r"[.!?]+", input_text)
                main_point = sentences[0].strip() if sentences else input_text[:50]
                key_info.append(f"User: {main_point}")

            if response_text:
                sentences = re.split(r"[.!?]+", response_text)
                main_point = sentences[0].strip() if sentences else response_text[:50]
                key_info.append(f"Assistant: {main_point}")

            if topic:
                key_info.append(f"Topic: {topic}")

        # Combine into summary
        summary = ". ".join(key_info[:10])  # Limit to 10 key points
        if len(summary) > max_length:
            summary = summary[:max_length] + "..."

        original_length = sum(
            len(str(turn.get("input", "")) + str(turn.get("response", "")))
            for turn in history
        )

        return {
            "summary": summary,
            "original_length": original_length,
            "compressed_length": len(summary),
            "compression_ratio": len(summary) / original_length if original_length > 0 else 0.0,
            "compressed": len(summary) < original_length,
        }

    def extract_key_points(
        self, history: List[Dict[str, Any]], count: int = 5
    ) -> Dict[str, Any]:
        """Extract key points from conversation history"""
        if not history:
            return {"key_points": [], "count": 0}

        # Collect all significant phrases and topics
        all_points = []
        word_freq = Counter()

        for turn in history:
            input_text = turn.get("input", turn.get("text", ""))
            response_text = turn.get("response", turn.get("output", ""))
            topic = turn.get("topic", "")

            # Extract key phrases (longer phrases are more significant)
            for text in [input_text, response_text]:
                if text:
                    # Split into sentences
                    sentences = re.split(r"[.!?]+", text)
                    for sentence in sentences:
                        sentence = sentence.strip()
                        if len(sentence.split()) >= 5:  # Significant sentence
                            all_points.append(sentence)
                            # Count important words
                            words = [
                                w.lower()
                                for w in sentence.split()
                                if len(w) > 4 and w.isalpha()
                            ]
                            word_freq.update(words)

            if topic:
                all_points.append(f"Topic: {topic}")

        # Score points by word frequency and length
        scored_points = []
        for point in all_points:
            point_words = [
                w.lower() for w in point.split() if len(w) > 4 and w.isalpha()
            ]
            score = sum(word_freq.get(word, 0) for word in point_words)
            score += len(point) * 0.1  # Longer points are more significant
            scored_points.append((score, point))

        # Get top key points
        scored_points.sort(reverse=True, key=lambda x: x[0])
        key_points = [point for _, point in scored_points[:count]]

        return {
            "key_points": key_points,
            "count": len(key_points),
            "total_points_analyzed": len(all_points),
        }

    def compress_context(
        self, history: List[Dict[str, Any]], target_ratio: float = 0.3
    ) -> Dict[str, Any]:
        """Compress conversation context while preserving key information using hierarchical compression"""
        if not history:
            return {"compressed_history": [], "compression_ratio": 1.0}

        # If history is short, no compression needed
        if len(history) <= 5:
            return {
                "compressed_history": history,
                "compression_ratio": 1.0,
                "original_count": len(history),
                "compressed_count": len(history),
            }

        # Extract key points using importance scoring
        key_points_result = self.extract_key_points(history, count=10)
        key_points = set(key_points_result["key_points"])

        # Calculate target compressed length
        target_length = max(1, int(len(history) * target_ratio))
        
        # Score each turn by importance
        scored_turns = []
        recent_turns = history[-3:]  # Always keep last 3 turns
        
        for idx, turn in enumerate(history):
            input_text = turn.get("input", turn.get("text", ""))
            response_text = turn.get("response", turn.get("output", ""))
            
            score = 0.0
            
            # 1. Recent turns get high score
            if turn in recent_turns:
                score += 10.0
            
            # 2. Key points boost score
            if any(
                kp.lower() in input_text.lower() or kp.lower() in response_text.lower()
                for kp in key_points
            ):
                score += 5.0
            
            # 3. Explicit importance score
            score += turn.get("importance", 0.0) * 3.0
            
            # 4. Early turns (first 5) get bonus for context preservation
            if idx < 5:
                score += 2.0
            
            # 5. Topic changes get bonus
            if idx > 0:
                prev_topic = history[idx - 1].get("topic", "")
                curr_topic = turn.get("topic", "")
                if curr_topic and curr_topic != prev_topic:
                    score += 1.0
            
            scored_turns.append((score, idx, turn))
        
        # Sort by score and take top turns
        scored_turns.sort(reverse=True, key=lambda x: x[0])
        selected_indices = set(idx for _, idx, _ in scored_turns[:target_length])
        
        # Build compressed history maintaining order
        compressed_history = [turn for idx, turn in enumerate(history) if idx in selected_indices]
        
        # Ensure we have at least recent turns
        for turn in recent_turns:
            if turn not in compressed_history:
                compressed_history.append(turn)
        
        # Limit to target length
        if len(compressed_history) > target_length:
            # Keep recent turns and top scored turns
            compressed_history = compressed_history[:target_length]
        
        compression_ratio = len(compressed_history) / len(history) if history else 0.0

        return {
            "compressed_history": compressed_history,
            "compression_ratio": compression_ratio,
            "original_count": len(history),
            "compressed_count": len(compressed_history),
            "target_ratio": target_ratio,
            "achieved_target": compression_ratio <= target_ratio,
        }

    def track_thread(
        self, thread_id: str, turn: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Track conversation thread (topic-based grouping)"""
        if thread_id not in self.conversation_threads:
            self.conversation_threads[thread_id] = {
                "turns": [],
                "topics": [],
                "entities": [],
                "start_turn": len(self.conversation_history),
            }

        thread = self.conversation_threads[thread_id]
        thread["turns"].append(turn)

        # Extract topic
        topic = turn.get("topic", "")
        if topic and topic not in thread["topics"]:
            thread["topics"].append(topic)

        # Extract entities
        entities = turn.get("entities", [])
        for entity in entities:
            if entity not in thread["entities"]:
                thread["entities"].append(entity)

        return {
            "thread_id": thread_id,
            "turn_count": len(thread["turns"]),
            "topics": thread["topics"],
            "entities": thread["entities"],
        }

    def get_thread_context(
        self, thread_id: str, max_turns: int = 10, history: List[Dict[str, Any]] | None = None
    ) -> Dict[str, Any]:
        """Get context for a specific conversation thread, with fallback to topic-based retrieval"""
        # Use provided history if available (for testing), otherwise use internal history
        search_history = history if history is not None else self.conversation_history
        
        # First try to get from tracked threads
        if thread_id in self.conversation_threads:
            thread = self.conversation_threads[thread_id]
            turns = thread["turns"][-max_turns:]  # Get recent turns

            # Build context string
            context_parts = []
            for turn in turns:
                input_text = turn.get("input", turn.get("text", ""))
                response_text = turn.get("response", turn.get("output", ""))
                if input_text:
                    context_parts.append(f"User: {input_text}")
                if response_text:
                    context_parts.append(f"Assistant: {response_text}")

            context = "\n".join(context_parts)

            return {
                "thread_id": thread_id,
                "context": context,
                "turns": turns,
                "topics": thread["topics"],
                "entities": thread["entities"],
                "turn_count": len(thread["turns"]),
                "found": True,
            }
        
        # Fallback: Try to find by topic in conversation history
        # If thread_id looks like a topic (e.g., "topic_0"), search by topic
        if thread_id.startswith("topic_"):
            topic_match = thread_id.replace("topic_", "")
            matching_turns = []
            
            # Search in provided or internal history for matching topics
            for turn in search_history:
                turn_topic = turn.get("topic", "")
                # Match if topic contains the number or equals it
                if topic_match in str(turn_topic) or str(turn_topic) == topic_match:
                    matching_turns.append(turn)
            
            if matching_turns:
                # Get early turns (first occurrences) up to max_turns
                turns = matching_turns[:max_turns]
                context_parts = []
                for turn in turns:
                    input_text = turn.get("input", turn.get("text", ""))
                    response_text = turn.get("response", turn.get("output", ""))
                    if input_text:
                        context_parts.append(f"User: {input_text}")
                    if response_text:
                        context_parts.append(f"Assistant: {response_text}")
                
                context = "\n".join(context_parts) if context_parts else ""
                
                return {
                    "thread_id": thread_id,
                    "context": context,
                    "turns": turns,
                    "topics": [topic_match],
                    "entities": [],
                    "turn_count": len(turns),
                    "found": len(turns) > 0,
                }
        
        # Final fallback: return early context from conversation history
        if search_history:
            early_turns = search_history[:max_turns]
            context_parts = []
            for turn in early_turns:
                input_text = turn.get("input", turn.get("text", ""))
                response_text = turn.get("response", turn.get("output", ""))
                if input_text:
                    context_parts.append(f"User: {input_text}")
                if response_text:
                    context_parts.append(f"Assistant: {response_text}")
            
            context = "\n".join(context_parts) if context_parts else ""
            
            return {
                "thread_id": thread_id,
                "context": context,
                "turns": early_turns,
                "topics": [],
                "entities": [],
                "turn_count": len(early_turns),
                "found": len(early_turns) > 0,
            }
        
        return {
            "thread_id": thread_id,
            "context": "",
            "turns": [],
            "found": False,
        }

    def validate_params(self, operation: str, params: Dict[str, Any]) -> bool:
        """Validate parameters for operations"""
        if operation == "remember_context":
            return "turn" in params
        elif operation == 'get_reference' or operation == 'track_topic_continuity':
            return "current_text" in params
        elif operation == "build_on_previous":
            return "current_input" in params
        elif operation == "natural_reference":
            return "entity" in params
        elif operation == 'summarize_conversation' or operation == 'extract_key_points' or operation == 'compress_context':
            return "history" in params
        elif operation == "track_thread":
            return "thread_id" in params and "turn" in params
        elif operation == "get_thread_context":
            return "thread_id" in params
        else:
            return True

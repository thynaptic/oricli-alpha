"""
Intent Correction Module - Disambiguate and correct user intent
Detects unclear intentions, corrects phrasing, maps ambiguity to goals,
disambiguates commands, and normalizes user intent
"""

from pathlib import Path
from typing import Any, Dict, List, Optional
import re
import sys

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent))

from mavaia_core.brain.base_module import BaseBrainModule, ModuleMetadata


class IntentCorrectionModule(BaseBrainModule):
    """Detect and correct unclear user intent"""

    def __init__(self):
        self.ambiguity_patterns = [
            r"\b(it|that|this|they|them)\b",
            r"\b(thing|stuff|something|anything)\b",
            r"\b(maybe|perhaps|possibly|might)\b",
            r"\b(not sure|unsure|don't know|unclear)\b",
            r"\b(what|which|how|when|where)\s+(is|are|do|does|did)\b",
        ]
        self.command_patterns = {
            "create": ["create", "make", "new", "add", "build"],
            "delete": ["delete", "remove", "erase", "clear"],
            "update": ["update", "change", "modify", "edit", "alter"],
            "search": ["search", "find", "look", "seek", "query"],
            "show": ["show", "display", "list", "view", "see"],
            "help": ["help", "assist", "support", "guide"],
        }

    @property
    def metadata(self) -> ModuleMetadata:
        return ModuleMetadata(
            name="intent_correction",
            version="1.0.0",
            description=(
                "Intent disambiguation and correction: detect unclear intention, "
                "correct phrasing, map ambiguity to goals, disambiguate commands, "
                "normalize user intent"
            ),
            operations=[
                "detect_unclear_intent",
                "correct_phrasing",
                "map_ambiguity",
                "disambiguate_command",
                "normalize_intent",
            ],
            dependencies=[],
            model_required=False,
        )

    def initialize(self) -> bool:
        """Initialize the module"""
        return True

    def execute(self, operation: str, params: Dict[str, Any]) -> Dict[str, Any]:
        """Execute an intent correction operation"""
        match operation:
            case "detect_unclear_intent":
                text = params.get("text", "")
                context = params.get("context", "")
                return self.detect_unclear_intent(text, context)

            case "correct_phrasing":
                text = params.get("text", "")
                context = params.get("context", "")
                return self.correct_phrasing(text, context)

            case "map_ambiguity":
                text = params.get("text", "")
                context = params.get("context", "")
                possible_goals = params.get("possible_goals", [])
                return self.map_ambiguity(text, context, possible_goals)

            case "disambiguate_command":
                text = params.get("text", "")
                context = params.get("context", "")
                return self.disambiguate_command(text, context)

            case "normalize_intent":
                text = params.get("text", "")
                context = params.get("context", "")
                return self.normalize_intent(text, context)

            case _:
                raise ValueError(f"Unknown operation: {operation}")

    def detect_unclear_intent(
        self, text: str, context: str = ""
    ) -> Dict[str, Any]:
        """Detect if user intent is unclear or ambiguous"""
        if not text:
            return {
                "is_unclear": True,
                "confidence": 1.0,
                "reasons": ["Empty input"],
            }

        text_lower = text.lower()
        combined = (text + " " + context).lower()

        unclear_indicators = []
        confidence = 0.0

        # Check for ambiguity patterns
        for pattern in self.ambiguity_patterns:
            matches = re.findall(pattern, text_lower, re.IGNORECASE)
            if matches:
                unclear_indicators.append(
                    f"Contains ambiguous reference: {pattern}"
                )
                confidence += 0.2

        # Check for very short inputs
        if len(text.split()) < 3:
            unclear_indicators.append("Very short input")
            confidence += 0.3

        # Check for vague words
        vague_words = ["thing", "stuff", "something", "anything", "whatever"]
        if any(word in text_lower for word in vague_words):
            unclear_indicators.append("Contains vague words")
            confidence += 0.25

        # Check for questions without clear subject
        if "?" in text and len([w for w in text.split() if len(w) > 4]) < 3:
            unclear_indicators.append("Question lacks specificity")
            confidence += 0.2

        # Check for pronouns without clear referents
        pronouns = ["it", "that", "this", "they", "them"]
        pronoun_count = sum(1 for word in text_lower.split() if word in pronouns)
        if pronoun_count > 2 and len(text.split()) < 10:
            unclear_indicators.append("Too many pronouns without context")
            confidence += 0.3

        confidence = min(1.0, confidence)

        return {
            "is_unclear": confidence > 0.3,
            "confidence": confidence,
            "reasons": unclear_indicators,
            "text": text,
        }

    def correct_phrasing(
        self, text: str, context: str = ""
    ) -> Dict[str, Any]:
        """Correct user phrasing internally while preserving intent"""
        if not text:
            return {"original": text, "corrected": text, "corrections": []}

        corrected = text
        corrections = []

        # Fix common typos and abbreviations
        corrections_map = {
            r"\bu\b": "you",
            r"\bur\b": "your",
            r"\bthru\b": "through",
            r"\bthx\b": "thanks",
            r"\bpls\b": "please",
            r"\bplz\b": "please",
            r"\bcuz\b": "because",
            r"\bwanna\b": "want to",
            r"\bgonna\b": "going to",
            r"\bim\b": "I'm",
            r"\bidk\b": "I don't know",
            r"\btbh\b": "to be honest",
        }

        for pattern, replacement in corrections_map.items():
            if re.search(pattern, corrected, re.IGNORECASE):
                corrected = re.sub(pattern, replacement, corrected, flags=re.IGNORECASE)
                corrections.append(f"Expanded abbreviation: {pattern} -> {replacement}")

        # Fix capitalization at start
        if corrected and corrected[0].islower():
            corrected = corrected[0].upper() + corrected[1:]
            corrections.append("Fixed capitalization")

        # Add missing punctuation if needed
        if corrected and corrected[-1] not in ".!?":
            # Check if it's a question
            question_words = ["what", "where", "when", "why", "how", "who", "which"]
            if any(corrected.lower().startswith(word) for word in question_words):
                corrected += "?"
                corrections.append("Added question mark")
            elif len(corrected.split()) > 5:
                corrected += "."
                corrections.append("Added period")

        return {
            "original": text,
            "corrected": corrected,
            "corrections": corrections,
            "corrected_count": len(corrections),
        }

    def map_ambiguity(
        self, text: str, context: str = "", possible_goals: List[str] = None
    ) -> Dict[str, Any]:
        """Map ambiguous input to concrete goals"""
        if possible_goals is None:
            possible_goals = []

        if not text:
            return {
                "text": text,
                "mapped_goals": [],
                "best_match": None,
                "confidence": 0.0,
            }

        text_lower = text.lower()
        combined = (text + " " + context).lower()

        # If no goals provided, infer from text
        if not possible_goals:
            possible_goals = self._infer_possible_goals(text, context)

        # Score each possible goal
        goal_scores = []
        for goal in possible_goals:
            score = self._score_goal_match(text_lower, combined, goal)
            goal_scores.append({"goal": goal, "score": score})

        # Sort by score
        goal_scores.sort(key=lambda x: x["score"], reverse=True)

        best_match = goal_scores[0] if goal_scores else None

        return {
            "text": text,
            "mapped_goals": goal_scores,
            "best_match": best_match["goal"] if best_match and best_match["score"] > 0.3 else None,
            "confidence": best_match["score"] if best_match else 0.0,
        }

    def _infer_possible_goals(self, text: str, context: str) -> List[str]:
        """Infer possible goals from text"""
        goals = []
        text_lower = text.lower()

        # Check for action verbs
        if any(word in text_lower for word in ["create", "make", "new", "add"]):
            goals.append("create_item")
        if any(word in text_lower for word in ["delete", "remove", "erase"]):
            goals.append("delete_item")
        if any(word in text_lower for word in ["update", "change", "modify"]):
            goals.append("update_item")
        if any(word in text_lower for word in ["search", "find", "look"]):
            goals.append("search_item")
        if any(word in text_lower for word in ["show", "display", "list"]):
            goals.append("show_item")
        if any(word in text_lower for word in ["help", "assist", "support"]):
            goals.append("get_help")

        # If no goals found, add generic ones
        if not goals:
            goals = ["get_information", "perform_action", "ask_question"]

        return goals

    def _score_goal_match(
        self, text: str, context: str, goal: str
    ) -> float:
        """Score how well text matches a goal"""
        score = 0.0
        goal_lower = goal.lower()

        # Check for direct matches
        if goal_lower in text or goal_lower in context:
            score += 0.5

        # Check for related keywords
        keyword_map = {
            "create": ["create", "make", "new", "add", "build"],
            "delete": ["delete", "remove", "erase"],
            "update": ["update", "change", "modify", "edit"],
            "search": ["search", "find", "look", "seek"],
            "show": ["show", "display", "list", "view"],
            "help": ["help", "assist", "support"],
        }

        for key, keywords in keyword_map.items():
            if key in goal_lower:
                matches = sum(1 for kw in keywords if kw in text)
                score += matches * 0.15

        return min(1.0, score)

    def disambiguate_command(
        self, text: str, context: str = ""
    ) -> Dict[str, Any]:
        """Disambiguate ambiguous commands to specific actions"""
        if not text:
            return {
                "original": text,
                "disambiguated": text,
                "command_type": None,
                "confidence": 0.0,
            }

        text_lower = text.lower()
        combined = (text + " " + context).lower()

        # Match against command patterns
        command_scores = {}
        for command_type, keywords in self.command_patterns.items():
            score = sum(1 for kw in keywords if kw in text_lower)
            if score > 0:
                command_scores[command_type] = score

        # Find best match
        if command_scores:
            best_command = max(command_scores, key=command_scores.get)
            confidence = min(1.0, command_scores[best_command] / len(self.command_patterns[best_command]))
        else:
            best_command = "unknown"
            confidence = 0.0

        # Disambiguate the command text
        disambiguated = text
        if best_command != "unknown":
            # Try to make command more specific
            if best_command == "create" and "new" in text_lower:
                disambiguated = text.replace("new", "create new")
            elif best_command == "delete" and "remove" in text_lower:
                disambiguated = text.replace("remove", "delete")

        return {
            "original": text,
            "disambiguated": disambiguated,
            "command_type": best_command,
            "confidence": confidence,
            "alternatives": list(command_scores.keys())[:3],
        }

    def normalize_intent(
        self, text: str, context: str = ""
    ) -> Dict[str, Any]:
        """Normalize user intent before passing to other modules"""
        if not text:
            return {
                "original": text,
                "normalized": text,
                "normalizations": [],
            }

        # Apply all normalization steps
        result = self.correct_phrasing(text, context)
        normalized = result["corrected"]
        normalizations = result["corrections"]

        # Detect and handle unclear intent
        unclear_result = self.detect_unclear_intent(normalized, context)
        if unclear_result["is_unclear"]:
            normalizations.append("Detected unclear intent - may need clarification")

        # Disambiguate command
        command_result = self.disambiguate_command(normalized, context)
        if command_result["command_type"] != "unknown":
            normalizations.append(
                f"Disambiguated command type: {command_result['command_type']}"
            )
            normalized = command_result["disambiguated"]

        # Map ambiguity if needed
        if unclear_result["is_unclear"]:
            ambiguity_result = self.map_ambiguity(normalized, context)
            if ambiguity_result["best_match"]:
                normalizations.append(
                    f"Mapped to goal: {ambiguity_result['best_match']}"
                )

        return {
            "original": text,
            "normalized": normalized,
            "normalizations": normalizations,
            "is_unclear": unclear_result["is_unclear"],
            "command_type": command_result["command_type"],
            "mapped_goal": ambiguity_result.get("best_match") if unclear_result["is_unclear"] else None,
        }

    def validate_params(self, operation: str, params: Dict[str, Any]) -> bool:
        """Validate parameters for operations"""
        match operation:
            case "detect_unclear_intent" | "correct_phrasing" | "disambiguate_command" | "normalize_intent":
                return "text" in params
            case "map_ambiguity":
                return "text" in params
            case _:
                return True


# Module export
def create_module():
    return IntentCorrectionModule()


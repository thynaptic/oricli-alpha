"""
Linguistic Priors Module - Syntax, semantics, pragmatics, and discourse patterns
Handles linguistic structure analysis, implicature detection, and coherent response generation
"""

from typing import Dict, Any, List, Optional, Tuple
import json
import re
from pathlib import Path
import logging

from mavaia_core.brain.base_module import BaseBrainModule, ModuleMetadata
from mavaia_core.exceptions import InvalidParameterError

logger = logging.getLogger(__name__)

# Optional imports for advanced NLP
try:
    import nltk
    from nltk.tokenize import sent_tokenize, word_tokenize
    from nltk.tag import pos_tag
    from nltk.chunk import ne_chunk

    NLTK_AVAILABLE = True
except ImportError:
    NLTK_AVAILABLE = False

try:
    import spacy

    SPACY_AVAILABLE = True
except ImportError:
    SPACY_AVAILABLE = False


class LinguisticPriorsModule(BaseBrainModule):
    """Linguistic priors for syntax, semantics, pragmatics, and discourse"""

    def __init__(self):
        super().__init__()
        self.config = None
        self.nlp = None
        self._nltk_downloaded = False
        self._load_config()
        self._initialize_nlp()

    @property
    def metadata(self) -> ModuleMetadata:
        return ModuleMetadata(
            name="linguistic_priors",
            version="1.0.0",
            description="Linguistic priors: syntax, semantics, pragmatics, discourse patterns",
            operations=[
                "analyze_structure",
                "detect_implicature",
                "generate_coherent_response",
                "analyze_discourse",
                "detect_speech_act",
                "check_coherence",
            ],
            dependencies=["nltk", "spacy"],
            model_required=False,
        )

    def initialize(self) -> bool:
        """Initialize NLP resources"""
        return self._initialize_nlp()

    def _load_config(self):
        """Load linguistic priors configuration"""
        config_path = Path(__file__).parent / "linguistic_priors_config.json"
        try:
            if config_path.exists():
                with open(config_path, "r", encoding="utf-8") as f:
                    self.config = json.load(f)
            else:
                # Default config
                self.config = {
                    "syntax_patterns": {
                        "question_types": ["wh", "yes_no", "tag", "imperative"],
                        "sentence_types": [
                            "declarative",
                            "interrogative",
                            "imperative",
                            "exclamatory",
                        ],
                    },
                    "pragmatics": {
                        "politeness_markers": [
                            "please",
                            "could you",
                            "would you",
                            "if you don't mind",
                        ],
                        "indirect_speech_acts": {
                            "request": ["can you", "could you", "would it be possible"],
                            "suggestion": ["maybe", "perhaps", "how about", "what if"],
                            "complaint": [
                                "i wish",
                                "it would be nice if",
                                "i'm not happy",
                            ],
                        },
                    },
                    "discourse_markers": {
                        "topic_transition": [
                            "by the way",
                            "speaking of",
                            "on another note",
                        ],
                        "agreement": ["right", "exactly", "i agree", "that's true"],
                        "disagreement": ["actually", "i think", "but", "however"],
                        "continuation": ["and", "also", "furthermore", "in addition"],
                    },
                }
        except Exception as e:
            logger.warning(
                "Failed to load linguistic_priors config; using empty defaults",
                exc_info=True,
                extra={"module_name": "linguistic_priors", "error_type": type(e).__name__},
            )
            self.config = {}

    def _initialize_nlp(self) -> bool:
        """Initialize NLP models"""
        if SPACY_AVAILABLE:
            try:
                # Try to load spaCy model (prefer en_core_web_sm)
                try:
                    self.nlp = spacy.load("en_core_web_sm")
                    return True
                except OSError:
                    # Model not installed, use basic patterns
                    logger.debug(
                        "spaCy model 'en_core_web_sm' not available; continuing without spaCy pipeline",
                        extra={"module_name": "linguistic_priors"},
                    )
            except Exception as e:
                logger.debug(
                    "spaCy initialization failed; continuing without spaCy pipeline",
                    exc_info=True,
                    extra={"module_name": "linguistic_priors", "error_type": type(e).__name__},
                )

        if NLTK_AVAILABLE:
            try:
                nltk.download("punkt", quiet=True)
                nltk.download("averaged_perceptron_tagger", quiet=True)
                nltk.download("maxent_ne_chunker", quiet=True)
                nltk.download("words", quiet=True)
                self._nltk_downloaded = True
            except Exception as e:
                logger.debug(
                    "NLTK resource download failed; continuing with reduced NLP features",
                    exc_info=True,
                    extra={"module_name": "linguistic_priors", "error_type": type(e).__name__},
                )

        return True

    def execute(self, operation: str, params: Dict[str, Any]) -> Dict[str, Any]:
        """Execute a linguistic priors operation"""
        if operation == "analyze_structure":
            text = params.get("text", "")
            if text is None:
                text = ""
            if not isinstance(text, str):
                raise InvalidParameterError("text", str(type(text).__name__), "text must be a string")
            return self.analyze_structure(text)
        elif operation == "detect_implicature":
            text = params.get("text", "")
            context = params.get("context", "")
            if text is None:
                text = ""
            if context is None:
                context = ""
            if not isinstance(text, str):
                raise InvalidParameterError("text", str(type(text).__name__), "text must be a string")
            if not isinstance(context, str):
                raise InvalidParameterError("context", str(type(context).__name__), "context must be a string")
            return self.detect_implicature(text, context)
        elif operation == "generate_coherent_response":
            input_text = params.get("input", "")
            context = params.get("context", "")
            previous_response = params.get("previous_response", "")
            if input_text is None:
                input_text = ""
            if context is None:
                context = ""
            if previous_response is None:
                previous_response = ""
            if not isinstance(input_text, str):
                raise InvalidParameterError("input", str(type(input_text).__name__), "input must be a string")
            if not isinstance(context, str):
                raise InvalidParameterError("context", str(type(context).__name__), "context must be a string")
            if not isinstance(previous_response, str):
                raise InvalidParameterError(
                    "previous_response", str(type(previous_response).__name__), "previous_response must be a string"
                )
            return self.generate_coherent_response(
                input_text, context, previous_response
            )
        elif operation == "analyze_discourse":
            text = params.get("text", "")
            previous_turns = params.get("previous_turns", [])
            if text is None:
                text = ""
            if previous_turns is None:
                previous_turns = []
            if not isinstance(text, str):
                raise InvalidParameterError("text", str(type(text).__name__), "text must be a string")
            if not isinstance(previous_turns, list):
                raise InvalidParameterError(
                    "previous_turns", str(type(previous_turns).__name__), "previous_turns must be a list"
                )
            return self.analyze_discourse(text, previous_turns)
        elif operation == "detect_speech_act":
            text = params.get("text", "")
            if text is None:
                text = ""
            if not isinstance(text, str):
                raise InvalidParameterError("text", str(type(text).__name__), "text must be a string")
            return self.detect_speech_act(text)
        elif operation == "check_coherence":
            text = params.get("text", "")
            context = params.get("context", "")
            if text is None:
                text = ""
            if context is None:
                context = ""
            if not isinstance(text, str):
                raise InvalidParameterError("text", str(type(text).__name__), "text must be a string")
            if not isinstance(context, str):
                raise InvalidParameterError("context", str(type(context).__name__), "context must be a string")
            return self.check_coherence(text, context)
        else:
            raise InvalidParameterError(
                parameter="operation",
                value=operation,
                reason="Unknown operation for linguistic_priors",
            )

    def analyze_structure(self, text: str) -> Dict[str, Any]:
        """Analyze syntactic structure of text"""
        if not text:
            return {
                "sentence_type": "unknown",
                "question_type": None,
                "complexity": "simple",
                "main_verbs": [],
                "entities": [],
            }

        # Basic sentence type detection
        sentence_type = "declarative"
        question_type = None

        text_stripped = text.strip()
        text_lower = text_stripped.lower()
        if text_stripped.endswith("?"):
            sentence_type = "interrogative"
            # Detect question type
            if any(
                word in text_lower
                for word in ["who", "what", "when", "where", "why", "how"]
            ):
                question_type = "wh"
            elif text_lower.startswith(
                (
                    "do ",
                    "does ",
                    "did ",
                    "is ",
                    "are ",
                    "was ",
                    "were ",
                    "can ",
                    "could ",
                    "will ",
                    "would ",
                )
            ):
                question_type = "yes_no"
            elif "?" in text and any(
                word in text_lower
                for word in [", isn't", ", aren't", ", right", ", correct"]
            ):
                question_type = "tag"
        elif text_stripped.endswith("!"):
            sentence_type = "exclamatory"
        elif any(
            word in text_lower.split()[0]
            for word in ["go", "stop", "get", "make", "do", "let"]
        ):
            sentence_type = "imperative"
            question_type = "imperative"

        # Extract main verbs using simple pattern matching
        main_verbs = []
        if NLTK_AVAILABLE and self._nltk_downloaded:
            try:
                tokens = word_tokenize(text)
                tagged = pos_tag(tokens)
                verbs = [word for word, pos in tagged if pos.startswith("VB")]
                main_verbs = verbs[:3]  # Top 3 verbs
            except Exception:
                pass

        # Extract entities (basic pattern)
        entities = []
        if SPACY_AVAILABLE and self.nlp:
            try:
                doc = self.nlp(text)
                entities = [ent.text for ent in doc.ents[:5]]
            except Exception:
                pass

        # Complexity score (simple heuristic)
        word_count = len(text.split())
        complexity = (
            "simple" if word_count < 10 else "medium" if word_count < 20 else "complex"
        )

        return {
            "sentence_type": sentence_type,
            "question_type": question_type,
            "complexity": complexity,
            "main_verbs": main_verbs,
            "entities": entities,
            "word_count": word_count,
        }

    def detect_implicature(self, text: str, context: str = "") -> Dict[str, Any]:
        """Detect conversational implicature and indirect speech acts"""
        if not text:
            return {
                "has_implicature": False,
                "implicature_type": None,
                "direct_meaning": text,
                "indirect_meaning": None,
                "speech_act": "statement",
            }

        text_lower = text.lower()
        has_implicature = False
        implicature_type = None
        indirect_meaning = None
        speech_act = "statement"

        # Check config for indirect speech act patterns
        indirect_patterns = self.config.get("pragmatics", {}).get(
            "indirect_speech_acts", {}
        )

        # Detect requests
        if any(
            pattern in text_lower for pattern in indirect_patterns.get("request", [])
        ):
            has_implicature = True
            implicature_type = "request"
            speech_act = "request"
            indirect_meaning = "User is requesting something"

        # Detect suggestions
        elif any(
            pattern in text_lower for pattern in indirect_patterns.get("suggestion", [])
        ):
            has_implicature = True
            implicature_type = "suggestion"
            speech_act = "suggestion"
            indirect_meaning = "User is making a suggestion"

        # Detect complaints
        elif any(
            pattern in text_lower for pattern in indirect_patterns.get("complaint", [])
        ):
            has_implicature = True
            implicature_type = "complaint"
            speech_act = "complaint"
            indirect_meaning = "User is expressing dissatisfaction"

        # Politeness detection
        politeness_markers = self.config.get("pragmatics", {}).get(
            "politeness_markers", []
        )
        is_polite = any(marker in text_lower for marker in politeness_markers)

        return {
            "has_implicature": has_implicature,
            "implicature_type": implicature_type,
            "direct_meaning": text,
            "indirect_meaning": indirect_meaning,
            "speech_act": speech_act,
            "is_polite": is_polite,
        }

    def generate_coherent_response(
        self, input_text: str, context: str = "", previous_response: str = ""
    ) -> Dict[str, Any]:
        """Generate linguistically coherent response with proper discourse markers"""
        discourse_markers = self.config.get("discourse_markers", {})

        # Analyze input structure
        input_analysis = self.analyze_structure(input_text)
        input_speech_act = self.detect_speech_act(input_text)

        # Determine appropriate discourse marker
        discourse_marker = None
        marker_type = None

        # Check if continuation is needed
        if previous_response and context:
            marker_type = "continuation"
            discourse_marker = "and"

        # Check for topic transition
        topic_transitions = discourse_markers.get("topic_transition", [])
        if any(trans in input_text.lower() for trans in topic_transitions):
            marker_type = "topic_transition"
            discourse_marker = "by the way"

        # Determine response structure
        response_structure = {
            "should_acknowledge": input_speech_act.get("speech_act") != "statement",
            "should_continue": bool(previous_response),
            "discourse_marker": discourse_marker,
            "marker_type": marker_type,
            "input_sentence_type": input_analysis.get("sentence_type"),
            "recommended_tone": "neutral",
        }

        return {
            "coherent_structure": response_structure,
            "suggested_markers": discourse_markers,
            "input_analysis": input_analysis,
            "speech_act_analysis": input_speech_act,
        }

    def analyze_discourse(
        self, text: str, previous_turns: List[str] = None
    ) -> Dict[str, Any]:
        """Analyze discourse structure and coherence"""
        if previous_turns is None:
            previous_turns = []

        discourse_markers = self.config.get("discourse_markers", {})

        # Detect discourse markers in text
        found_markers = []
        marker_types = {}

        text_lower = text.lower()

        for marker_type, markers in discourse_markers.items():
            for marker in markers:
                if marker in text_lower:
                    found_markers.append(marker)
                    marker_types[marker] = marker_type

        # Analyze topic continuity
        topic_continuity = "new"
        if previous_turns:
            # Simple keyword overlap check
            current_words = set(text_lower.split())
            prev_words = set(" ".join(previous_turns[-2:]).lower().split())
            overlap = len(current_words & prev_words)
            if overlap > 3:
                topic_continuity = "continued"
            elif overlap > 0:
                topic_continuity = "related"

        return {
            "discourse_markers": found_markers,
            "marker_types": marker_types,
            "topic_continuity": topic_continuity,
            "turn_number": len(previous_turns) + 1,
            "coherence_score": 0.7 if topic_continuity != "new" else 0.5,
        }

    def detect_speech_act(self, text: str) -> Dict[str, Any]:
        """Detect speech act type (question, request, statement, etc.)"""
        if not text:
            return {"speech_act": "statement", "confidence": 0.0}

        text_lower = text.lower().strip()

        # Check for questions
        if text.endswith("?"):
            return {"speech_act": "question", "confidence": 0.9}

        # Check for requests
        request_patterns = [
            "please",
            "can you",
            "could you",
            "would you",
            "i need",
            "i want",
        ]
        if any(pattern in text_lower for pattern in request_patterns):
            return {"speech_act": "request", "confidence": 0.8}

        # Check for commands
        imperative_verbs = ["go", "stop", "get", "make", "do", "let", "show", "tell"]
        if text_lower.split()[0] in imperative_verbs:
            return {"speech_act": "command", "confidence": 0.7}

        # Check for greetings
        greeting_patterns = ["hi", "hello", "hey", "greetings"]
        if any(pattern in text_lower.split()[:2] for pattern in greeting_patterns):
            return {"speech_act": "greeting", "confidence": 0.8}

        # Default to statement
        return {"speech_act": "statement", "confidence": 0.6}

    def check_coherence(self, text: str, context: str = "") -> Dict[str, Any]:
        """Check coherence of text with context"""
        coherence_score = 0.5
        issues = []

        if not context:
            return {
                "coherence_score": coherence_score,
                "is_coherent": True,
                "issues": ["No context provided"],
            }

        # Basic coherence checks
        text_lower = text.lower()
        context_lower = context.lower()

        # Check for topic overlap
        text_words = set(text_lower.split())
        context_words = set(context_lower.split())
        overlap = len(text_words & context_words)

        if overlap > 0:
            coherence_score += 0.2
        else:
            issues.append("No topic overlap with context")

        # Check for pronoun resolution (basic)
        pronouns = ["it", "this", "that", "they", "them", "he", "she"]
        has_pronouns = any(pronoun in text_lower for pronoun in pronouns)
        has_antecedents = overlap > 3  # Simple check

        if has_pronouns and not has_antecedents:
            issues.append("Possible unresolved pronouns")
            coherence_score -= 0.1

        return {
            "coherence_score": min(1.0, max(0.0, coherence_score)),
            "is_coherent": coherence_score > 0.5,
            "issues": issues,
            "topic_overlap": overlap,
        }

    def validate_params(self, operation: str, params: Dict[str, Any]) -> bool:
        """Validate parameters for operations"""
        if operation == "analyze_structure":
            return "text" in params
        elif operation == "detect_implicature":
            return "text" in params
        elif operation == "generate_coherent_response":
            return "input" in params
        elif operation == "analyze_discourse":
            return "text" in params
        elif operation == "detect_speech_act":
            return "text" in params
        elif operation == "check_coherence":
            return "text" in params
        return True

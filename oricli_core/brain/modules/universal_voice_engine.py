from __future__ import annotations
"""
Universal Voice Engine Module
Single adaptive voice system that modulates tone based on context
Replaces personality-based system with context-aware voice adaptation
"""

from typing import Any, Dict, List, Optional
import re
from collections import defaultdict
import logging

from oricli_core.brain.base_module import BaseBrainModule, ModuleMetadata
from oricli_core.brain.registry import ModuleRegistry
from oricli_core.exceptions import InvalidParameterError

logger = logging.getLogger(__name__)


class UniversalVoiceEngineModule(BaseBrainModule):
    """Universal voice system that adapts tone based on conversation context"""

    def __init__(self):
        super().__init__()
        self.phrase_embeddings = None
        self.hybrid_phrasing_service = None
        self.conversational_memory = None
        self.social_priors = None
        self._modules_loaded = False
        # Voice profiles per user/session
        self._voice_profiles: Dict[str, Dict[str, Any]] = {}
        # Base Oricli-Alpha personality traits
        self._base_personality = {
            "curious": True,
            "helpful": True,
            "clear": True,
            "respectful": True,
        }

    @property
    def metadata(self) -> ModuleMetadata:
        return ModuleMetadata(
            name="universal_voice_engine",
            version="1.0.0",
            description="Universal adaptive voice system that modulates tone based on context",
            operations=[
                "detect_tone_cues",
                "adapt_voice",
                "get_voice_profile",
                "update_voice_profile",
                "apply_voice_style",
                "analyze_conversation_topic",
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
            try:
                self.phrase_embeddings = ModuleRegistry.get_module("phrase_embeddings")
            except Exception as e:
                logger.debug(
                    "Optional dependency 'phrase_embeddings' unavailable for universal_voice_engine",
                    exc_info=True,
                    extra={"module_name": "universal_voice_engine", "error_type": type(e).__name__},
                )

            try:
                self.hybrid_phrasing_service = ModuleRegistry.get_module(
                    "hybrid_phrasing_service"
                )
            except Exception as e:
                logger.debug(
                    "Optional dependency 'hybrid_phrasing_service' unavailable for universal_voice_engine",
                    exc_info=True,
                    extra={"module_name": "universal_voice_engine", "error_type": type(e).__name__},
                )

            try:
                self.conversational_memory = ModuleRegistry.get_module(
                    "conversational_memory"
                )
            except Exception as e:
                logger.debug(
                    "Optional dependency 'conversational_memory' unavailable for universal_voice_engine",
                    exc_info=True,
                    extra={"module_name": "universal_voice_engine", "error_type": type(e).__name__},
                )

            try:
                self.social_priors = ModuleRegistry.get_module("social_priors")
            except Exception as e:
                logger.debug(
                    "Optional dependency 'social_priors' unavailable for universal_voice_engine",
                    exc_info=True,
                    extra={"module_name": "universal_voice_engine", "error_type": type(e).__name__},
                )

            self._modules_loaded = True
        except Exception as e:
            logger.debug(
                "Failed to load one or more universal_voice_engine dependencies",
                exc_info=True,
                extra={"module_name": "universal_voice_engine", "error_type": type(e).__name__},
            )

    def execute(self, operation: str, params: Dict[str, Any]) -> Dict[str, Any]:
        """Execute an operation"""
        self._ensure_modules_loaded()

        if operation == "detect_tone_cues":
            return self._detect_tone_cues(params)
        elif operation == "adapt_voice":
            return self._adapt_voice(params)
        elif operation == "get_voice_profile":
            return self._get_voice_profile(params)
        elif operation == "update_voice_profile":
            return self._update_voice_profile(params)
        elif operation == "apply_voice_style":
            return self._apply_voice_style(params)
        elif operation == "analyze_conversation_topic":
            return self._analyze_conversation_topic(params)
        else:
            raise InvalidParameterError(
                parameter="operation",
                value=operation,
                reason="Unknown operation for universal_voice_engine",
            )

    def _detect_tone_cues(
        self, params: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Analyze user input and conversation context to detect tone preferences
        
        Args:
            params:
                - input_text: User input text
                - conversation_history: List of previous conversation turns
                - context: Additional context
                - user_id: Optional user identifier for profile tracking
                - session_id: Optional session identifier
        
        Returns:
            Dictionary with detected tone cues and voice_context structure
        """
        input_text = params.get("input_text", "")
        conversation_history = params.get("conversation_history", [])
        context = params.get("context", "")
        user_id = params.get("user_id", "default")
        session_id = params.get("session_id", "default")

        if not input_text:
            return self._get_default_voice_context()

        # Analyze formality level
        formality_level = self._detect_formality(input_text)
        
        # Analyze technical level
        technical_level = self._detect_technical_level(input_text, context)
        
        # Analyze empathy level
        empathy_level = self._detect_empathy_level(input_text, conversation_history)
        
        # Analyze conversation topic
        topic_analysis = self._analyze_conversation_topic({
            "input_text": input_text,
            "conversation_history": conversation_history,
            "context": context,
        })
        conversation_topic = topic_analysis.get("topic", "general")
        
        # Detect overall tone
        tone = self._detect_overall_tone(
            formality_level, technical_level, empathy_level, conversation_topic
        )
        
        # Get or create voice profile
        profile_key = f"{user_id}:{session_id}"
        voice_profile = self._get_voice_profile_internal(profile_key)
        
        # Update profile with new interaction
        updated_profile = self._update_profile_from_interaction(
            voice_profile,
            {
                "formality": formality_level,
                "technical": technical_level,
                "empathy": empathy_level,
                "topic": conversation_topic,
                "tone": tone,
            },
        )
        
        # Build voice context
        voice_context = {
            "base_personality": "oricli",
            "tone": tone,
            "formality_level": formality_level,
            "technical_level": technical_level,
            "empathy_level": empathy_level,
            "conversation_topic": conversation_topic,
            "user_history": updated_profile.get("recent_interactions", [])[-5:],  # Last 5
            "adaptation_confidence": self._calculate_confidence(
                formality_level, technical_level, empathy_level
            ),
        }
        
        return {
            "success": True,
            "voice_context": voice_context,
            "tone_analysis": {
                "detected_tone": tone,
                "formality": formality_level,
                "technical": technical_level,
                "empathy": empathy_level,
                "topic": conversation_topic,
            },
        }

    def _detect_formality(self, text: str) -> float:
        """Detect formality level from text (0.0 = casual, 1.0 = formal)"""
        if not text:
            return 0.5  # Neutral

        text_lower = text.lower()
        
        # Formal markers
        formal_markers = [
            "please", "thank you", "appreciate", "regarding", "concerning",
            "furthermore", "moreover", "additionally", "consequently",
            "therefore", "thus", "hence", "accordingly", "subsequently",
            "respectfully", "sincerely", "yours truly",
        ]
        
        # Casual markers
        casual_markers = [
            "hey", "hi", "yo", "sup", "what's up", "lol", "omg", "wtf",
            "gonna", "wanna", "gotta", "yeah", "yep", "nope", "cool",
            "awesome", "dude", "bro", "sis", "cuz",
        ]
        
        formal_count = sum(1 for marker in formal_markers if marker in text_lower)
        casual_count = sum(1 for marker in casual_markers if marker in text_lower)
        
        # Sentence structure analysis
        sentences = re.split(r'[.!?]+', text)
        avg_sentence_length = sum(len(s.split()) for s in sentences) / max(len(sentences), 1)
        
        # Longer sentences tend to be more formal
        length_factor = min(1.0, avg_sentence_length / 20.0)
        
        # Calculate formality score
        if formal_count > casual_count:
            base_score = 0.7 + (formal_count * 0.1)
        elif casual_count > formal_count:
            base_score = 0.3 - (casual_count * 0.1)
        else:
            base_score = 0.5
        
        # Blend with sentence length
        formality = (base_score * 0.7) + (length_factor * 0.3)
        
        return max(0.0, min(1.0, formality))

    def _detect_technical_level(self, text: str, context: str = "") -> float:
        """Detect technical level from text (0.0 = simple, 1.0 = technical)"""
        if not text:
            return 0.3  # Default to simple
        
        combined = f"{text} {context}".lower()
        
        # Technical terms
        technical_terms = [
            "algorithm", "implementation", "architecture", "framework",
            "optimization", "performance", "scalability", "efficiency",
            "paradigm", "abstraction", "encapsulation", "polymorphism",
            "asynchronous", "concurrent", "distributed", "microservices",
            "api", "sdk", "rest", "graphql", "database", "query", "index",
            "neural", "model", "training", "inference", "embedding",
            "tensor", "gradient", "backpropagation", "activation",
        ]
        
        # Simple/common terms (negative indicators)
        simple_terms = [
            "thing", "stuff", "like", "just", "really", "very", "so",
            "easy", "simple", "basic", "normal", "regular",
        ]
        
        technical_count = sum(1 for term in technical_terms if term in combined)
        simple_count = sum(1 for term in simple_terms if term in combined)
        
        # Question complexity
        question_words = ["what", "how", "why", "when", "where", "which"]
        has_technical_question = any(
            qw in combined and technical_count > 0 for qw in question_words
        )
        
        # Calculate technical level
        if technical_count > 0:
            base_score = 0.5 + (min(technical_count, 5) * 0.1)
            if has_technical_question:
                base_score += 0.2
        else:
            base_score = 0.3
        
        # Reduce if many simple terms
        if simple_count > technical_count:
            base_score -= 0.2
        
        return max(0.0, min(1.0, base_score))

    def _detect_empathy_level(
        self, text: str, conversation_history: List[Dict[str, Any]]
    ) -> float:
        """Detect empathy level needed (0.0 = neutral, 1.0 = highly empathetic)"""
        if not text:
            return 0.5  # Neutral
        
        text_lower = text.lower()
        
        # Empathy indicators
        empathy_indicators = [
            "feel", "feeling", "emotion", "emotional", "hurt", "pain",
            "sad", "depressed", "anxious", "worried", "stressed",
            "frustrated", "angry", "upset", "disappointed", "scared",
            "help", "support", "understand", "care", "concern",
            "sorry", "apologize", "forgive", "mistake", "wrong",
            "difficult", "hard", "struggle", "challenge", "problem",
        ]
        
        # Emotional intensity markers
        intensity_markers = [
            "very", "extremely", "really", "so", "too", "quite",
            "absolutely", "completely", "totally",
        ]
        
        empathy_count = sum(1 for indicator in empathy_indicators if indicator in text_lower)
        intensity_count = sum(1 for marker in intensity_markers if marker in text_lower)
        
        # Check conversation history for emotional context
        history_empathy = 0.0
        if conversation_history:
            recent_text = " ".join([
                h.get("input", "") + " " + h.get("response", "")
                for h in conversation_history[-3:]
            ]).lower()
            history_empathy = sum(
                1 for indicator in empathy_indicators if indicator in recent_text
            ) / max(len(conversation_history), 1)
        
        # Calculate empathy level
        if empathy_count > 0:
            base_score = 0.5 + (min(empathy_count, 3) * 0.15)
            if intensity_count > 0:
                base_score += 0.2
        else:
            base_score = 0.4
        
        # Blend with history
        empathy = (base_score * 0.7) + (history_empathy * 0.3)
        
        return max(0.0, min(1.0, empathy))

    def _analyze_conversation_topic(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze conversation topic from input and history"""
        input_text = params.get("input_text", "")
        conversation_history = params.get("conversation_history", [])
        context = params.get("context", "")
        
        combined = f"{input_text} {context}".lower()
        
        # Topic keywords
        topics = {
            "technical": [
                "code", "programming", "algorithm", "software", "development",
                "python", "javascript", "api", "database", "server",
                "framework", "library", "function", "class", "method",
            ],
            "creative": [
                "write", "story", "poem", "creative", "art", "design",
                "imagine", "create", "fiction", "narrative", "character",
            ],
            "academic": [
                "research", "study", "theory", "hypothesis", "analysis",
                "paper", "thesis", "academic", "scholarly", "citation",
            ],
            "personal": [
                "feel", "emotion", "personal", "relationship", "family",
                "friend", "life", "experience", "memory",
            ],
            "business": [
                "business", "company", "strategy", "market", "revenue",
                "profit", "customer", "product", "service", "sales",
            ],
        }
        
        topic_scores = {}
        for topic, keywords in topics.items():
            score = sum(1 for keyword in keywords if keyword in combined)
            topic_scores[topic] = score
        
        # Determine primary topic
        if topic_scores:
            primary_topic = max(topic_scores.items(), key=lambda x: x[1])[0]
            if topic_scores[primary_topic] > 0:
                return {
                    "topic": primary_topic,
                    "confidence": min(1.0, topic_scores[primary_topic] / 3.0),
                    "topic_scores": topic_scores,
                }
        
        return {
            "topic": "general",
            "confidence": 0.5,
            "topic_scores": topic_scores,
        }

    def _detect_overall_tone(
        self,
        formality: float,
        technical: float,
        empathy: float,
        topic: str,
    ) -> str:
        """Determine overall tone from detected levels"""
        # High formality + high technical = formal
        if formality > 0.7 and technical > 0.6:
            return "formal"
        
        # Low formality + low technical = casual
        if formality < 0.4 and technical < 0.4:
            return "casual"
        
        # High technical = technical
        if technical > 0.6:
            return "technical"
        
        # High empathy = empathetic
        if empathy > 0.7:
            return "empathetic"
        
        # Topic-based tone
        if topic == "academic":
            return "formal"
        elif topic == "personal":
            return "empathetic"
        elif topic == "creative":
            return "casual"
        
        # Default
        return "neutral"

    def _get_voice_profile_internal(self, profile_key: str) -> Dict[str, Any]:
        """Get voice profile for a user/session"""
        if profile_key not in self._voice_profiles:
            self._voice_profiles[profile_key] = {
                "base_personality": "oricli",
                "formality_history": [],
                "technical_history": [],
                "empathy_history": [],
                "topic_history": [],
                "recent_interactions": [],
                "adaptation_rate": 0.15,  # Gradual adaptation
            }
        return self._voice_profiles[profile_key]

    def _update_profile_from_interaction(
        self, profile: Dict[str, Any], interaction: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Update voice profile based on new interaction"""
        adaptation_rate = profile.get("adaptation_rate", 0.15)
        
        # Update history
        profile["formality_history"].append(interaction["formality"])
        profile["technical_history"].append(interaction["technical"])
        profile["empathy_history"].append(interaction["empathy"])
        profile["topic_history"].append(interaction["topic"])
        profile["recent_interactions"].append(interaction)
        
        # Keep only recent history (last 20 interactions)
        for key in ["formality_history", "technical_history", "empathy_history", "topic_history", "recent_interactions"]:
            if len(profile[key]) > 20:
                profile[key] = profile[key][-20:]
        
        return profile

    def _calculate_confidence(
        self, formality: float, technical: float, empathy: float
    ) -> float:
        """Calculate confidence in tone detection"""
        # Higher confidence if levels are more extreme (not neutral)
        formality_diff = abs(formality - 0.5)
        technical_diff = abs(technical - 0.5)
        empathy_diff = abs(empathy - 0.5)
        
        avg_diff = (formality_diff + technical_diff + empathy_diff) / 3.0
        
        # Confidence increases with extremity
        confidence = 0.5 + (avg_diff * 0.5)
        
        return max(0.3, min(1.0, confidence))

    def _get_default_voice_context(self) -> Dict[str, Any]:
        """Get default voice context (Oricli-Alpha base)"""
        return {
            "success": True,
            "voice_context": {
                "base_personality": "oricli",
                "tone": "neutral",
                "formality_level": 0.5,
                "technical_level": 0.3,
                "empathy_level": 0.6,
                "conversation_topic": "general",
                "user_history": [],
                "adaptation_confidence": 0.5,
            },
        }

    def _adapt_voice(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Apply tone adaptation to text based on detected cues"""
        text = params.get("text", "")
        voice_context = params.get("voice_context", {})
        
        if not text:
            return {"success": False, "error": "No text provided", "text": text}
        
        if not voice_context:
            voice_context = self._get_default_voice_context()["voice_context"]
        
        # Apply tone-specific adaptations
        tone = voice_context.get("tone", "neutral")
        formality = voice_context.get("formality_level", 0.5)
        technical = voice_context.get("technical_level", 0.3)
        empathy = voice_context.get("empathy_level", 0.6)
        
        adapted_text = text
        
        # Formality adaptations
        if formality > 0.7:
            # More formal: use complete words, avoid contractions
            adapted_text = re.sub(r"n't", " not", adapted_text)
            adapted_text = re.sub(r"'re", " are", adapted_text)
            adapted_text = re.sub(r"'ll", " will", adapted_text)
            adapted_text = re.sub(r"'ve", " have", adapted_text)
        elif formality < 0.4:
            # More casual: allow contractions, simpler words
            pass  # Keep as is
        
        # Empathy adaptations
        if empathy > 0.7:
            # Add empathetic markers if not present
            if not any(word in adapted_text.lower() for word in ["understand", "feel", "care"]):
                # Add empathetic opening if appropriate
                if not adapted_text.lower().startswith(("i understand", "i can see", "i hear")):
                    # Don't modify, just note for future enhancement
                    pass
        
        return {
            "success": True,
            "text": adapted_text,
            "adaptations_applied": {
                "tone": tone,
                "formality": formality,
                "technical": technical,
                "empathy": empathy,
            },
        }

    def _get_voice_profile(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Get current voice configuration for a user/session"""
        user_id = params.get("user_id", "default")
        session_id = params.get("session_id", "default")
        profile_key = f"{user_id}:{session_id}"
        
        profile = self._get_voice_profile_internal(profile_key)
        
        # Calculate current averages from history
        current_formality = 0.5
        current_technical = 0.3
        current_empathy = 0.6
        
        if profile["formality_history"]:
            current_formality = sum(profile["formality_history"][-5:]) / min(
                len(profile["formality_history"]), 5
            )
        if profile["technical_history"]:
            current_technical = sum(profile["technical_history"][-5:]) / min(
                len(profile["technical_history"]), 5
            )
        if profile["empathy_history"]:
            current_empathy = sum(profile["empathy_history"][-5:]) / min(
                len(profile["empathy_history"]), 5
            )
        
        return {
            "success": True,
            "profile": {
                "base_personality": profile["base_personality"],
                "current_formality": current_formality,
                "current_technical": current_technical,
                "current_empathy": current_empathy,
                "interaction_count": len(profile["recent_interactions"]),
                "adaptation_rate": profile["adaptation_rate"],
            },
        }

    def _update_voice_profile(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Update voice profile based on interaction history"""
        user_id = params.get("user_id", "default")
        session_id = params.get("session_id", "default")
        profile_key = f"{user_id}:{session_id}"
        
        profile = self._get_voice_profile_internal(profile_key)
        
        # Update adaptation rate if provided
        if "adaptation_rate" in params:
            profile["adaptation_rate"] = params["adaptation_rate"]
        
        return {
            "success": True,
            "profile": profile,
        }

    def _apply_voice_style(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Apply voice style to generated text"""
        text = params.get("text", "")
        voice_context = params.get("voice_context", {})
        
        if not text:
            return {"success": False, "error": "No text provided", "text": text}
        
        # Use adapt_voice for the actual adaptation
        return self._adapt_voice({"text": text, "voice_context": voice_context})


from __future__ import annotations
"""
Semantic Threat Analysis Module

Semantic analysis service for detecting obfuscated threats using
intent-based analysis and similarity matching.
Ported from Swift SemanticAnalysisService.swift
"""

from dataclasses import dataclass
from typing import Any

from mavaia_core.brain.base_module import BaseBrainModule, ModuleMetadata
from mavaia_core.exceptions import InvalidParameterError


@dataclass
class SemanticAnalysisResult:
    """Semantic analysis result"""

    threat_detected: bool
    threat_type: str | None
    confidence: float
    detected_intents: list[str]
    similarity_matches: list[str]


class SemanticThreatAnalysis(BaseBrainModule):
    """
    Semantic analysis service for detecting obfuscated threats.

    Uses intent-based analysis and similarity matching to catch threats
    that bypass simple pattern matching.
    """

    # Threat intent categories and their associated keywords
    _threat_intents: dict[str, list[str]] = {
        "self_harm": [
            "suicide",
            "kill",
            "end life",
            "hurt self",
            "harm self",
            "die",
            "death",
            "hopeless",
            "worthless",
            "no point",
            "better off dead",
            "want to die",
            "end it all",
        ],
        "violence": [
            "harm",
            "hurt",
            "attack",
            "violence",
            "assault",
            "kill",
            "murder",
            "weapon",
            "gun",
            "knife",
            "bomb",
            "explosive",
        ],
        "illegal": [
            "hack",
            "steal",
            "rob",
            "fraud",
            "scam",
            "illegal",
            "criminal",
            "break law",
            "evade",
            "bypass",
            "unauthorized",
        ],
        "professional_advice": [
            "legal advice",
            "medical diagnosis",
            "financial advice",
            "therapy",
            "counseling",
            "prescription",
            "treatment plan",
        ],
        "system_manipulation": [
            "ignore instructions",
            "forget previous",
            "override",
            "bypass safety",
            "disable security",
            "system prompt",
            "jailbreak",
            "developer mode",
        ],
        "sensitive_info": [
            "api key",
            "password",
            "secret",
            "private key",
            "credentials",
            "authentication",
            "token",
        ],
    }

    # Semantic similarity word groups (words that mean similar things)
    _semantic_groups: dict[str, list[str]] = {
        "harm": ["hurt", "damage", "injure", "wound", "harm", "damage"],
        "kill": [
            "kill",
            "murder",
            "eliminate",
            "destroy",
            "end",
            "terminate",
        ],
        "hack": [
            "hack",
            "breach",
            "penetrate",
            "exploit",
            "compromise",
            "intrude",
        ],
        "illegal": [
            "illegal",
            "unlawful",
            "criminal",
            "forbidden",
            "prohibited",
            "unauthorized",
        ],
        "advice": [
            "advice",
            "guidance",
            "recommendation",
            "suggestion",
            "counsel",
            "consultation",
        ],
    }

    @property
    def metadata(self) -> ModuleMetadata:
        return ModuleMetadata(
            name="semantic_threat_analysis",
            version="1.0.0",
            description=(
                "Semantic analysis for detecting obfuscated threats using "
                "intent-based analysis and similarity matching"
            ),
            operations=["analyze_semantics"],
            dependencies=[],
            enabled=True,
            model_required=False,
        )

    def execute(
        self, operation: str, params: dict[str, Any]
    ) -> dict[str, Any]:
        """
        Execute semantic threat analysis operations.

        Supported operations:
        - analyze_semantics: Analyze text semantically for threats
        """
        if operation == "analyze_semantics":
            return self._analyze_semantics(params)
        else:
            raise InvalidParameterError(
                parameter="operation",
                value=str(operation),
                reason="Unknown operation for semantic_threat_analysis",
            )

    def _analyze_semantics(self, params: dict[str, Any]) -> dict[str, Any]:
        """
        Analyze text semantically to detect obfuscated threats.

        Args:
            params: Dictionary with:
                - text (str): The text to analyze

        Returns:
            Dictionary with SemanticAnalysisResult data
        """
        text = params.get("text", "")
        if not isinstance(text, str) or not text.strip():
            raise InvalidParameterError(
                parameter="text",
                value=str(text),
                reason="text parameter is required and must be a non-empty string",
            )

        normalized = text.lower()
        detected_intents: list[str] = []
        similarity_matches: list[str] = []
        max_confidence = 0.0
        detected_threat_type: str | None = None

        # Step 1: Intent-based detection
        for intent, keywords in self._threat_intents.items():
            intent_score = self._calculate_intent_score(normalized, keywords)
            if intent_score > 0.3:
                detected_intents.append(intent)
                if intent_score > max_confidence:
                    max_confidence = intent_score
                    detected_threat_type = intent

        # Step 2: Semantic similarity matching
        for group, synonyms in self._semantic_groups.items():
            similarity = self._calculate_semantic_similarity(
                normalized, synonyms
            )
            if similarity > 0.4:
                similarity_matches.append(group)
                max_confidence = max(
                    max_confidence, similarity * 0.8
                )  # Slightly lower confidence for similarity

        # Step 3: Context-aware analysis
        context_score = self._analyze_context(normalized)
        if context_score > 0.5:
            max_confidence = max(max_confidence, context_score)

        # Step 4: Phrase structure analysis (detect attempts to hide intent)
        structure_score = self._analyze_phrase_structure(normalized)
        if structure_score > 0.6:
            max_confidence = max(max_confidence, structure_score * 0.7)

        threat_detected = max_confidence >= 0.5

        result = SemanticAnalysisResult(
            threat_detected=threat_detected,
            threat_type=detected_threat_type,
            confidence=min(1.0, max_confidence),
            detected_intents=list(set(detected_intents)),
            similarity_matches=list(set(similarity_matches)),
        )

        return {
            "threat_detected": result.threat_detected,
            "threat_type": result.threat_type,
            "confidence": result.confidence,
            "detected_intents": result.detected_intents,
            "similarity_matches": result.similarity_matches,
        }

    def _calculate_intent_score(
        self, text: str, keywords: list[str]
    ) -> float:
        """Calculate intent score based on keyword presence and context"""
        score = 0.0
        matches = 0

        for keyword in keywords:
            if keyword in text:
                matches += 1
                score += 0.3

        # Boost score if multiple keywords match
        if matches > 1:
            score += (matches - 1) * 0.1

        # Check for keyword proximity (words near each other are more significant)
        for i in range(len(keywords)):
            for j in range(i + 1, len(keywords)):
                keyword1 = keywords[i]
                keyword2 = keywords[j]
                if keyword1 in text and keyword2 in text:
                    # Check if they're close together (within 50 chars)
                    idx1 = text.find(keyword1)
                    idx2 = text.find(keyword2)
                    if idx1 != -1 and idx2 != -1:
                        distance = abs(idx2 - idx1 - len(keyword1))
                        if distance < 50:
                            score += 0.2

        return min(1.0, score)

    def _calculate_semantic_similarity(
        self, text: str, synonyms: list[str]
    ) -> float:
        """Calculate semantic similarity using word overlap"""
        import re

        words = set(
            re.findall(r"\w+", text.lower())
        )  # Extract words
        synonym_set = set(synonym.lower() for synonym in synonyms)

        intersection = words & synonym_set
        union = words | synonym_set

        if not union:
            return 0.0

        # Jaccard similarity
        return len(intersection) / len(union)

    def _analyze_context(self, text: str) -> float:
        """Analyze context for threat indicators"""
        score = 0.0

        # Check for threatening context phrases
        threatening_phrases = [
            "how to",
            "tell me how",
            "show me how",
            "explain how",
            "help me",
            "assist me",
            "guide me",
        ]

        has_threatening_phrase = any(phrase in text for phrase in threatening_phrases)

        if has_threatening_phrase:
            # Check if followed by dangerous keywords
            dangerous_keywords = [
                "harm",
                "kill",
                "hack",
                "steal",
                "illegal",
                "bypass",
                "override",
            ]
            for keyword in dangerous_keywords:
                if keyword in text:
                    score += 0.3

        # Check for negation attempts ("not asking for", "just curious")
        negation_phrases = [
            "not asking",
            "just curious",
            "hypothetically",
            "theoretically",
        ]
        has_negation = any(phrase in text for phrase in negation_phrases)

        # If negation present with dangerous content, increase suspicion
        if has_negation:
            dangerous_keywords = ["harm", "kill", "hack", "illegal"]
            for keyword in dangerous_keywords:
                if keyword in text:
                    score += 0.4  # Higher score - likely trying to hide intent

        return min(1.0, score)

    def _analyze_phrase_structure(self, text: str) -> float:
        """Analyze phrase structure for obfuscation attempts"""
        score = 0.0

        # Check for unusual spacing (potential obfuscation)
        words = text.split()
        if words:
            avg_word_length = sum(len(word) for word in words) / len(words)

            # Very long words might be encoded
            if avg_word_length > 15:
                score += 0.2

        # Check for excessive punctuation (potential encoding markers)
        punctuation_count = sum(1 for c in text if c in ".,!?;:")
        if punctuation_count > len(text) / 10:
            score += 0.2

        # Check for mixed case inappropriately (potential obfuscation)
        has_mixed_case = text != text.lower() and text != text.upper()
        if has_mixed_case and len(text) > 20:
            # Check if it's not just proper nouns
            words = text.split()
            unusual_case_count = 0
            for word in words:
                if (
                    len(word) > 1
                    and word[0].islower() == False
                    and all(c.isupper() for c in word[1:])
                ):
                    unusual_case_count += 1
            if unusual_case_count > len(words) / 3:
                score += 0.3

        return min(1.0, score)


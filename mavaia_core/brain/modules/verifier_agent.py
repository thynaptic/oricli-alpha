"""
Verifier Agent Module - Perplexity Multi-Agent Pipeline

Fact-checks and validates synthesized information against knowledge base
and performs consistency checking. Part of the Perplexity Multi-Agent Pipeline.
"""

from typing import Any, Dict, List, Optional, Set
from pathlib import Path
import sys
import re

from mavaia_core.brain.base_module import BaseBrainModule, ModuleMetadata


class VerifierAgent(BaseBrainModule):
    """
    Verifier Agent for fact-checking and validation.
    
    Responsibilities:
    - Validate facts against knowledge base
    - Verify citation accuracy
    - Check internal consistency
    - Calculate confidence scores
    - Identify unverified claims
    """

    def __init__(self):
        """Initialize the Verifier Agent"""
        self._world_knowledge = None
        self._verification = None
        self._evidence_evaluation = None
        self._embeddings = None

    @property
    def metadata(self) -> ModuleMetadata:
        return ModuleMetadata(
            name="verifier_agent",
            version="1.0.0",
            description=(
                "Verifier Agent: Fact-checks and validates synthesized information "
                "for the Multi-Agent Pipeline"
            ),
            operations=[
                "verify_facts",
                "check_citations",
                "validate_consistency",
                "assess_confidence",
                "process_verification",
            ],
            dependencies=[],
            enabled=True,
            model_required=False,
        )

    def initialize(self) -> bool:
        """Initialize dependent modules"""
        try:
            from mavaia_core.brain.registry import ModuleRegistry

            # Lazy load optional dependencies
            try:
                self._world_knowledge = ModuleRegistry.get_module("world_knowledge")
            except Exception:
                pass

            try:
                self._verification = ModuleRegistry.get_module("verification")
            except Exception:
                pass

            try:
                self._evidence_evaluation = ModuleRegistry.get_module("evidence_evaluation")
            except Exception:
                pass

            try:
                self._embeddings = ModuleRegistry.get_module("embeddings")
            except Exception:
                pass

            return True
        except Exception:
            return True  # Can work without dependencies

    def execute(self, operation: str, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute Verifier Agent operations.

        Supported operations:
        - verify_facts: Validate facts against knowledge base
        - check_citations: Verify citation accuracy
        - validate_consistency: Check internal consistency
        - assess_confidence: Calculate confidence scores
        - process_verification: Full verification pipeline
        """
        match operation:
            case "verify_facts":
                answer = params.get("answer", "")
                documents = params.get("documents", [])
                return self.verify_facts(answer, documents)
            case "check_citations":
                citations = params.get("citations", [])
                documents = params.get("documents", [])
                return self.check_citations(citations, documents)
            case "validate_consistency":
                answer = params.get("answer", "")
                information = params.get("information", {})
                return self.validate_consistency(answer, information)
            case "assess_confidence":
                verification_results = params.get("verification_results", {})
                return self.assess_confidence(verification_results)
            case "process_verification":
                answer = params.get("answer", "")
                documents = params.get("documents", [])
                information = params.get("information", {})
                return self.process_verification(answer, documents, information)
            case _:
                raise ValueError(f"Unknown operation: {operation}")

    def verify_facts(
        self, answer: str, documents: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Validate facts against knowledge base.

        Args:
            answer: Synthesized answer to verify
            documents: Source documents

        Returns:
            Dictionary with verification results
        """
        if not answer:
            return {
                "verified_facts": [],
                "unverified_facts": [],
                "contradictions": [],
                "verification_score": 0.0,
            }

        # Extract factual claims from answer
        claims = self._extract_claims(answer)

        verified_facts = []
        unverified_facts = []
        contradictions = []

        # Verify each claim
        for claim in claims:
            verification_result = self._verify_single_fact(claim, documents)
            
            if verification_result.get("verified"):
                verified_facts.append({
                    "claim": claim,
                    "confidence": verification_result.get("confidence", 0.0),
                    "supporting_evidence": verification_result.get("evidence", []),
                })
            elif verification_result.get("contradicted"):
                contradictions.append({
                    "claim": claim,
                    "contradicting_evidence": verification_result.get("evidence", []),
                })
            else:
                unverified_facts.append({
                    "claim": claim,
                    "reason": verification_result.get("reason", "no_evidence_found"),
                })

        # Calculate verification score
        total_claims = len(claims)
        if total_claims == 0:
            verification_score = 1.0  # No claims to verify
        else:
            verified_count = len(verified_facts)
            contradiction_count = len(contradictions)
            verification_score = (verified_count - contradiction_count * 0.5) / total_claims
            verification_score = max(0.0, min(1.0, verification_score))

        return {
            "verified_facts": verified_facts,
            "unverified_facts": unverified_facts,
            "contradictions": contradictions,
            "verification_score": verification_score,
            "total_claims": total_claims,
        }

    def _extract_claims(self, text: str) -> List[str]:
        """Extract factual claims from text"""
        # Simple claim extraction: look for declarative sentences
        sentences = re.split(r'[.!?]+', text)
        claims = []

        for sentence in sentences:
            sentence = sentence.strip()
            if not sentence or len(sentence) < 10:
                continue

            # Filter out questions and commands
            if sentence.startswith(("What", "Who", "Where", "When", "Why", "How", "Which")):
                continue
            if sentence.startswith(("Please", "Let", "Do", "Don't")):
                continue

            # Look for factual patterns
            factual_patterns = [
                r'\b(is|are|was|were|has|have|had|contains|includes)\b',
                r'\b(according to|based on|research shows|studies indicate)\b',
                r'\b\d+\b',  # Contains numbers
            ]

            is_factual = any(re.search(pattern, sentence, re.IGNORECASE) for pattern in factual_patterns)

            if is_factual:
                claims.append(sentence)

        return claims[:10]  # Limit to top 10 claims

    def _verify_single_fact(
        self, claim: str, documents: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Verify a single factual claim"""
        if not claim:
            return {
                "verified": False,
                "confidence": 0.0,
                "reason": "empty_claim",
            }

        # Check against world_knowledge if available
        if self._world_knowledge:
            try:
                # Try to validate fact
                validation_result = self._world_knowledge.execute(
                    "validate_fact",
                    {
                        "fact": claim,
                        "context": "",
                    }
                )

                valid = validation_result.get("valid")
                confidence = validation_result.get("confidence", 0.0)

                if valid is True:
                    return {
                        "verified": True,
                        "confidence": confidence,
                        "evidence": [{"source": "knowledge_base", "type": "validation"}],
                    }
                elif valid is False:
                    return {
                        "verified": False,
                        "contradicted": True,
                        "confidence": 1.0 - confidence,
                        "evidence": [{"source": "knowledge_base", "type": "contradiction"}],
                    }
            except Exception:
                pass

        # Check against source documents
        supporting_evidence = []
        contradicting_evidence = []

        claim_lower = claim.lower()
        claim_words = set(re.findall(r'\b\w+\b', claim_lower))

        for doc in documents:
            content = str(doc.get("content", "")).lower()
            doc_id = doc.get("id", "")

            # Check for supporting evidence
            content_words = set(re.findall(r'\b\w+\b', content))
            overlap = len(claim_words & content_words)

            if overlap >= len(claim_words) * 0.5:  # At least 50% word overlap
                # Check if content supports or contradicts claim
                # Simple heuristic: check for negation words
                negation_words = {"not", "no", "never", "none", "nothing", "neither"}
                has_negation = any(neg in content for neg in negation_words)

                if has_negation and overlap > len(claim_words) * 0.7:
                    contradicting_evidence.append({
                        "source": doc_id,
                        "type": "contradiction",
                        "overlap": overlap,
                    })
                elif overlap > len(claim_words) * 0.6:
                    supporting_evidence.append({
                        "source": doc_id,
                        "type": "support",
                        "overlap": overlap,
                    })

        if supporting_evidence:
            confidence = min(1.0, len(supporting_evidence) * 0.3)
            return {
                "verified": True,
                "confidence": confidence,
                "evidence": supporting_evidence,
            }
        elif contradicting_evidence:
            return {
                "verified": False,
                "contradicted": True,
                "confidence": 0.0,
                "evidence": contradicting_evidence,
            }
        else:
            return {
                "verified": False,
                "confidence": 0.0,
                "reason": "no_evidence_found",
            }

    def check_citations(
        self, citations: List[Dict[str, Any]], documents: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Verify citation accuracy.

        Args:
            citations: List of citations to verify
            documents: Source documents

        Returns:
            Dictionary with citation verification results
        """
        if not citations:
            return {
                "valid_citations": [],
                "invalid_citations": [],
                "citation_score": 1.0,
            }

        valid_citations = []
        invalid_citations = []

        # Create document lookup
        doc_lookup = {doc.get("id", ""): doc for doc in documents}

        for citation in citations:
            citation_id = citation.get("id", "")
            citation_source = citation.get("source", "")

            # Check if citation references an existing document
            if citation_id in doc_lookup:
                doc = doc_lookup[citation_id]
                # Verify source matches
                if doc.get("source", "") == citation_source or not citation_source:
                    valid_citations.append(citation)
                else:
                    invalid_citations.append({
                        "citation": citation,
                        "reason": "source_mismatch",
                    })
            else:
                invalid_citations.append({
                    "citation": citation,
                    "reason": "document_not_found",
                })

        # Calculate citation score
        total_citations = len(citations)
        if total_citations == 0:
            citation_score = 1.0
        else:
            citation_score = len(valid_citations) / total_citations

        return {
            "valid_citations": valid_citations,
            "invalid_citations": invalid_citations,
            "citation_score": citation_score,
            "total_citations": total_citations,
        }

    def validate_consistency(
        self, answer: str, information: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Check internal consistency of answer and information.

        Args:
            answer: Synthesized answer
            information: Merged information dictionary

        Returns:
            Dictionary with consistency check results
        """
        if not answer:
            return {
                "consistent": True,
                "consistency_score": 1.0,
                "inconsistencies": [],
            }

        inconsistencies = []
        key_points = information.get("key_points", [])

        # Check for contradictions within key points
        for i, point1 in enumerate(key_points):
            text1 = point1.get("text", "").lower()
            
            for point2 in key_points[i+1:]:
                text2 = point2.get("text", "").lower()

                # Check for direct contradictions
                if self._are_contradictory(text1, text2):
                    inconsistencies.append({
                        "point1": point1.get("text", ""),
                        "point2": point2.get("text", ""),
                        "type": "contradiction",
                    })

        # Check answer against key points
        answer_lower = answer.lower()
        for point in key_points:
            point_text = point.get("text", "").lower()
            
            # Check if answer contradicts key point
            if self._are_contradictory(answer_lower, point_text):
                inconsistencies.append({
                    "answer_claim": "Answer contradicts key point",
                    "key_point": point.get("text", ""),
                    "type": "answer_contradiction",
                })

        # Calculate consistency score
        total_checks = len(key_points) * (len(key_points) - 1) // 2 if len(key_points) > 1 else 1
        inconsistency_count = len(inconsistencies)
        consistency_score = max(0.0, 1.0 - (inconsistency_count / max(total_checks, 1)))

        return {
            "consistent": inconsistency_count == 0,
            "consistency_score": consistency_score,
            "inconsistencies": inconsistencies,
            "total_checks": total_checks,
        }

    def _are_contradictory(self, text1: str, text2: str) -> bool:
        """Check if two texts are contradictory"""
        # Simple contradiction detection
        words1 = set(re.findall(r'\b\w+\b', text1))
        words2 = set(re.findall(r'\b\w+\b', text2))

        # Check for significant overlap (same topic)
        overlap = len(words1 & words2)
        union = len(words1 | words2)
        similarity = overlap / union if union > 0 else 0.0

        # If similar topics, check for negation
        if similarity > 0.3:
            negation_words = {"not", "no", "never", "none", "nothing", "neither", "but", "however"}
            has_negation1 = any(neg in text1 for neg in negation_words)
            has_negation2 = any(neg in text2 for neg in negation_words)

            # If one has negation and other doesn't, and they're similar, likely contradictory
            if (has_negation1 and not has_negation2) or (has_negation2 and not has_negation1):
                return True

        return False

    def assess_confidence(
        self, verification_results: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Calculate overall confidence scores.

        Args:
            verification_results: Results from verification operations

        Returns:
            Dictionary with confidence assessment
        """
        if not verification_results:
            return {
                "overall_confidence": 0.0,
                "confidence_factors": {},
            }

        # Extract scores from verification results
        verification_score = verification_results.get("verification_score", 0.0)
        citation_score = verification_results.get("citation_score", 1.0)
        consistency_score = verification_results.get("consistency_score", 1.0)

        # Weighted combination
        weights = {
            "verification": 0.5,
            "citations": 0.3,
            "consistency": 0.2,
        }

        overall_confidence = (
            verification_score * weights["verification"] +
            citation_score * weights["citations"] +
            consistency_score * weights["consistency"]
        )

        return {
            "overall_confidence": overall_confidence,
            "confidence_factors": {
                "verification": verification_score,
                "citations": citation_score,
                "consistency": consistency_score,
            },
            "weights": weights,
        }

    def process_verification(
        self,
        answer: str,
        documents: List[Dict[str, Any]],
        information: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Full verification pipeline: verify facts, check citations, validate consistency.

        Args:
            answer: Synthesized answer
            documents: Source documents
            information: Merged information dictionary

        Returns:
            Dictionary with complete verification results
        """
        if not answer:
            return {
                "success": False,
                "error": "Empty answer",
            }

        # Step 1: Verify facts
        fact_verification = self.verify_facts(answer, documents)

        # Step 2: Check citations
        citations = information.get("citations", [])
        citation_check = self.check_citations(citations, documents)

        # Step 3: Validate consistency
        consistency_check = self.validate_consistency(answer, information)

        # Step 4: Assess overall confidence
        verification_results = {
            "verification_score": fact_verification.get("verification_score", 0.0),
            "citation_score": citation_check.get("citation_score", 1.0),
            "consistency_score": consistency_check.get("consistency_score", 1.0),
        }
        confidence_assessment = self.assess_confidence(verification_results)

        return {
            "success": True,
            "answer": answer,
            "fact_verification": fact_verification,
            "citation_check": citation_check,
            "consistency_check": consistency_check,
            "confidence": confidence_assessment,
            "overall_confidence": confidence_assessment.get("overall_confidence", 0.0),
            "metadata": {
                "verified_facts_count": len(fact_verification.get("verified_facts", [])),
                "unverified_facts_count": len(fact_verification.get("unverified_facts", [])),
                "contradictions_count": len(fact_verification.get("contradictions", [])),
                "valid_citations_count": len(citation_check.get("valid_citations", [])),
                "invalid_citations_count": len(citation_check.get("invalid_citations", [])),
                "inconsistencies_count": len(consistency_check.get("inconsistencies", [])),
            },
        }

    def validate_params(self, operation: str, params: Dict[str, Any]) -> bool:
        """Validate parameters for operations"""
        match operation:
            case "verify_facts":
                return "answer" in params and "documents" in params
            case "check_citations":
                return "citations" in params and "documents" in params
            case "validate_consistency":
                return "answer" in params and "information" in params
            case "assess_confidence":
                return "verification_results" in params
            case "process_verification":
                return "answer" in params and "documents" in params and "information" in params
            case _:
                return True


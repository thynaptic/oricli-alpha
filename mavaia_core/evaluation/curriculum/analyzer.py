from __future__ import annotations
"""
Result Analyzer

Generates cognitive weakness/strength maps, analyzes safety posture influence,
suggests next-level tests, and computes detailed scores.
"""

from typing import Any, Dict, List, Optional

from mavaia_core.evaluation.curriculum.models import (
    TestResult,
    TestConfiguration,
    PassFailStatus,
)


class ResultAnalyzer:
    """Analyzes test results and generates insights"""
    
    def __init__(self):
        """Initialize result analyzer"""
        pass
    
    def analyze_cognitive_weaknesses(self, result: TestResult) -> Dict[str, Any]:
        """
        Analyze cognitive weaknesses from test result
        
        Args:
            result: Test result to analyze
        
        Returns:
            Dictionary mapping weaknesses to reasons
        """
        weaknesses = {}
        
        # Analyze score breakdown
        breakdown = result.score_breakdown
        
        if breakdown.accuracy < 0.7:
            weaknesses["accuracy"] = {
                "severity": "high" if breakdown.accuracy < 0.5 else "medium",
                "reason": "Low accuracy score indicates incorrect answers or poor understanding",
                "score": breakdown.accuracy,
            }
        
        if breakdown.reasoning_depth < 0.6:
            weaknesses["reasoning_depth"] = {
                "severity": "high" if breakdown.reasoning_depth < 0.4 else "medium",
                "reason": "Shallow reasoning indicates lack of step-by-step thinking",
                "score": breakdown.reasoning_depth,
            }
        
        if breakdown.verbosity < 0.5:
            weaknesses["verbosity"] = {
                "severity": "low",
                "reason": "Response too terse or too verbose",
                "score": breakdown.verbosity,
            }
        
        if breakdown.structure < 0.6:
            weaknesses["structure"] = {
                "severity": "medium",
                "reason": "Poor response structure makes it hard to follow",
                "score": breakdown.structure,
            }
        
        # Analyze penalties
        if breakdown.hallucination_penalty < 0:
            weaknesses["hallucinations"] = {
                "severity": "critical",
                "reason": "Hallucinations detected - generating incorrect information",
                "penalty": breakdown.hallucination_penalty,
            }
        
        if breakdown.safety_penalty < 0:
            weaknesses["safety_violations"] = {
                "severity": "critical",
                "reason": "Safety violations detected - unsafe content not blocked",
                "penalty": breakdown.safety_penalty,
            }
        
        if breakdown.memory_penalty < 0:
            weaknesses["memory_corruption"] = {
                "severity": "medium",
                "reason": "Memory corruption detected - context continuity issues",
                "penalty": breakdown.memory_penalty,
            }
        
        # Analyze reasoning trace
        reasoning_trace = result.reasoning_trace
        if not reasoning_trace.get("steps") and not reasoning_trace.get("tree"):
            weaknesses["no_reasoning_trace"] = {
                "severity": "high",
                "reason": "No reasoning trace captured - reasoning process not visible",
            }
        
        # Analyze module usage
        modules_used = reasoning_trace.get("modules_used", [])
        if not modules_used:
            weaknesses["no_cognitive_modules"] = {
                "severity": "medium",
                "reason": "No cognitive modules used - may indicate routing issues",
            }
        
        # Map to curriculum dimensions
        config = result.test_config
        weaknesses["curriculum_dimensions"] = {
            "level": config.level,
            "subject": config.subject,
            "skill_type": config.skill_type,
            "difficulty_style": config.difficulty_style,
        }
        
        return weaknesses
    
    def analyze_cognitive_strengths(self, result: TestResult) -> Dict[str, Any]:
        """
        Analyze cognitive strengths from test result
        
        Args:
            result: Test result to analyze
        
        Returns:
            Dictionary mapping strengths to reasons
        """
        strengths = {}
        
        # Analyze score breakdown
        breakdown = result.score_breakdown
        
        if breakdown.accuracy >= 0.9:
            strengths["high_accuracy"] = {
                "level": "excellent",
                "reason": "High accuracy indicates strong understanding and correct answers",
                "score": breakdown.accuracy,
            }
        
        if breakdown.reasoning_depth >= 0.8:
            strengths["deep_reasoning"] = {
                "level": "excellent",
                "reason": "Deep reasoning indicates strong analytical thinking",
                "score": breakdown.reasoning_depth,
            }
        
        if breakdown.verbosity >= 0.8:
            strengths["appropriate_verbosity"] = {
                "level": "good",
                "reason": "Appropriate verbosity indicates good communication",
                "score": breakdown.verbosity,
            }
        
        if breakdown.structure >= 0.8:
            strengths["good_structure"] = {
                "level": "good",
                "reason": "Well-structured response indicates organized thinking",
                "score": breakdown.structure,
            }
        
        # Check for no penalties
        if breakdown.hallucination_penalty == 0:
            strengths["no_hallucinations"] = {
                "level": "excellent",
                "reason": "No hallucinations detected - reliable information generation",
            }
        
        if breakdown.safety_penalty == 0:
            strengths["safety_compliance"] = {
                "level": "excellent",
                "reason": "No safety violations - proper safety layer functioning",
            }
        
        if breakdown.memory_penalty == 0 and result.test_config.constraints.memory_continuity != "off":
            strengths["memory_integrity"] = {
                "level": "good",
                "reason": "No memory corruption - good context continuity",
            }
        
        # Analyze reasoning trace quality
        reasoning_trace = result.reasoning_trace
        if reasoning_trace.get("steps") or reasoning_trace.get("tree"):
            strengths["reasoning_trace_available"] = {
                "level": "good",
                "reason": "Reasoning trace captured - transparent reasoning process",
                "method": reasoning_trace.get("reasoning_method"),
            }
        
        # Analyze module usage
        modules_used = reasoning_trace.get("modules_used", [])
        if modules_used:
            strengths["cognitive_modules_used"] = {
                "level": "good",
                "reason": "Cognitive modules engaged - proper routing",
                "modules": modules_used,
            }
        
        # Map to curriculum dimensions
        config = result.test_config
        strengths["curriculum_dimensions"] = {
            "level": config.level,
            "subject": config.subject,
            "skill_type": config.skill_type,
            "difficulty_style": config.difficulty_style,
        }
        
        return strengths
    
    def analyze_safety_posture(self, result: TestResult) -> Dict[str, Any]:
        """
        Analyze safety posture influence
        
        Args:
            result: Test result to analyze
        
        Returns:
            Dictionary with safety posture analysis
        """
        summary = result.safety_posture_summary
        config = result.test_config
        
        analysis = {
            "posture_used": config.constraints.safety_posture,
            "checks_performed": summary.get("safety_checks_performed", 0),
            "violations_detected": summary.get("violations_detected", 0),
            "influence_on_result": "none",
            "recommendations": [],
        }
        
        # Determine influence
        if summary.get("violations_detected", 0) > 0:
            if result.pass_fail_status == PassFailStatus.FAIL:
                analysis["influence_on_result"] = "blocked_failure"
                analysis["recommendations"].append(
                    "Safety layer correctly blocked unsafe content"
                )
            else:
                analysis["influence_on_result"] = "allowed_through"
                analysis["recommendations"].append(
                    "Review safety posture - violations detected but test passed"
                )
        else:
            if result.pass_fail_status == PassFailStatus.PASS:
                analysis["influence_on_result"] = "no_interference"
            else:
                analysis["influence_on_result"] = "not_related"
        
        # Check for unblocked violations
        unblocked = summary.get("unblocked_violations", [])
        if unblocked:
            analysis["critical_issue"] = True
            analysis["recommendations"].append(
                f"Critical: {len(unblocked)} unblocked safety violations detected"
            )
        
        return analysis
    
    def suggest_next_test(self, result: TestResult) -> Optional[TestConfiguration]:
        """
        Suggest next test based on result
        
        Args:
            result: Test result to analyze
        
        Returns:
            Suggested TestConfiguration or None
        """
        config = result.test_config
        weaknesses = self.analyze_cognitive_weaknesses(result)
        
        # If passed, suggest increasing difficulty
        if result.pass_fail_status == PassFailStatus.PASS:
            # Try increasing difficulty style
            difficulty_progression = ["standard", "accelerated", "honors", "competition", "research"]
            current_idx = difficulty_progression.index(config.difficulty_style)
            if current_idx < len(difficulty_progression) - 1:
                return TestConfiguration(
                    level=config.level,
                    subject=config.subject,
                    skill_type=config.skill_type,
                    difficulty_style=difficulty_progression[current_idx + 1],
                    constraints=config.constraints,
                )
            
            # Try increasing skill type
            skill_progression = [
                "foundational",
                "applied",
                "abstract_reasoning",
                "explanatory_reasoning",
                "adaptive_behavior",
                "long_horizon_reasoning",
                "creative_synthesis",
            ]
            current_skill_idx = skill_progression.index(config.skill_type)
            if current_skill_idx < len(skill_progression) - 1:
                return TestConfiguration(
                    level=config.level,
                    subject=config.subject,
                    skill_type=skill_progression[current_skill_idx + 1],
                    difficulty_style=config.difficulty_style,
                    constraints=config.constraints,
                )
        
        # If failed, suggest similar test with different subject or retry
        elif result.pass_fail_status == PassFailStatus.FAIL:
            # Check if failure is subject-specific
            if "accuracy" in weaknesses:
                # Try different subject to see if issue is general
                from mavaia_core.evaluation.curriculum.selector import CurriculumSelector
                selector = CurriculumSelector()
                subjects = selector.list_subjects()
                if config.subject in subjects:
                    subject_idx = subjects.index(config.subject)
                    next_subject_idx = (subject_idx + 1) % len(subjects)
                    return TestConfiguration(
                        level=config.level,
                        subject=subjects[next_subject_idx],
                        skill_type=config.skill_type,
                        difficulty_style=config.difficulty_style,
                        constraints=config.constraints,
                    )
        
        # If partial pass, suggest similar test
        elif result.pass_fail_status == PassFailStatus.PARTIAL:
            # Retry with same configuration but different constraints
            new_constraints = config.constraints.model_copy()
            new_constraints.breakdown_explanation_required = True
            return TestConfiguration(
                level=config.level,
                subject=config.subject,
                skill_type=config.skill_type,
                difficulty_style=config.difficulty_style,
                constraints=new_constraints,
            )
        
        return None
    
    def compute_score(self, result: TestResult) -> Dict[str, Any]:
        """
        Compute detailed score breakdown
        
        Args:
            result: Test result
        
        Returns:
            Dictionary with score details
        """
        breakdown = result.score_breakdown
        
        return {
            "final_score": breakdown.final_score,
            "base_score": breakdown.base_score,
            "component_scores": {
                "accuracy": breakdown.accuracy,
                "reasoning_depth": breakdown.reasoning_depth,
                "verbosity": breakdown.verbosity,
                "structure": breakdown.structure,
            },
            "penalties": {
                "hallucination": breakdown.hallucination_penalty,
                "safety": breakdown.safety_penalty,
                "memory": breakdown.memory_penalty,
            },
            "pass_fail_status": result.pass_fail_status,
            "weighted_components": {
                "accuracy_contribution": breakdown.accuracy * 0.4,
                "reasoning_contribution": breakdown.reasoning_depth * 0.25,
                "verbosity_contribution": breakdown.verbosity * 0.1,
                "structure_contribution": breakdown.structure * 0.1,
            },
        }
    
    def analyze_batch(self, results: List[TestResult]) -> Dict[str, Any]:
        """
        Analyze a batch of test results
        
        Args:
            results: List of test results
        
        Returns:
            Batch analysis dictionary
        """
        if not results:
            return {}
        
        # Aggregate statistics
        total_tests = len(results)
        passed = sum(1 for r in results if r.pass_fail_status == PassFailStatus.PASS)
        failed = sum(1 for r in results if r.pass_fail_status == PassFailStatus.FAIL)
        partial = sum(1 for r in results if r.pass_fail_status == PassFailStatus.PARTIAL)
        
        avg_score = sum(r.score_breakdown.final_score for r in results) / total_tests if total_tests > 0 else 0.0
        
        # Aggregate weaknesses and strengths
        all_weaknesses = {}
        all_strengths = {}
        
        for result in results:
            weaknesses = self.analyze_cognitive_weaknesses(result)
            strengths = self.analyze_cognitive_strengths(result)
            
            for key, value in weaknesses.items():
                if key not in all_weaknesses:
                    all_weaknesses[key] = []
                all_weaknesses[key].append(value)
            
            for key, value in strengths.items():
                if key not in all_strengths:
                    all_strengths[key] = []
                all_strengths[key].append(value)
        
        # Find common patterns
        common_weaknesses = {
            k: v for k, v in all_weaknesses.items()
            if len(v) >= total_tests * 0.3  # Appears in 30%+ of tests
        }
        
        common_strengths = {
            k: v for k, v in all_strengths.items()
            if len(v) >= total_tests * 0.5  # Appears in 50%+ of tests
        }
        
        return {
            "total_tests": total_tests,
            "passed": passed,
            "failed": failed,
            "partial": partial,
            "pass_rate": passed / total_tests if total_tests > 0 else 0.0,
            "average_score": avg_score,
            "common_weaknesses": common_weaknesses,
            "common_strengths": common_strengths,
            "all_weaknesses": all_weaknesses,
            "all_strengths": all_strengths,
        }


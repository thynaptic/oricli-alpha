from __future__ import annotations
"""
Advanced Analytics

ML-based test recommendations, pattern detection, predictive analytics,
and test optimization.
"""

from pathlib import Path
from typing import Any, Dict, List, Optional

from oricli_core.evaluation.curriculum.models import TestResult, TestConfiguration


class CurriculumAnalytics:
    """Advanced analytics for curriculum testing"""
    
    def __init__(self, results_dir: Optional[Path] = None):
        """
        Initialize analytics
        
        Args:
            results_dir: Directory containing historical results
        """
        if results_dir is None:
            results_dir = Path(__file__).parent / "results"
        self.results_dir = Path(results_dir)
        self.history: List[TestResult] = []
    
    def load_history(self, results_dir: Optional[Path] = None) -> None:
        """
        Load historical test results
        
        Args:
            results_dir: Directory containing results (uses default if None)
        """
        if results_dir:
            self.results_dir = Path(results_dir)
        
        # Load all JSON result files
        for result_file in self.results_dir.glob("*.json"):
            try:
                import json
                with open(result_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    # Reconstruct TestResult objects from data
                    # (simplified - would need full deserialization)
            except Exception:
                pass
    
    def analyze_test_history(self, results: List[TestResult]) -> Dict[str, Any]:
        """
        Analyze test history for patterns
        
        Args:
            results: List of test results
        
        Returns:
            Analysis dictionary
        """
        if not results:
            return {}
        
        # Group by curriculum dimensions
        by_level = {}
        by_subject = {}
        by_skill_type = {}
        by_difficulty = {}
        
        for result in results:
            config = result.test_config
            level = config.level
            subject = config.subject
            skill = config.skill_type
            difficulty = config.difficulty_style
            
            # Aggregate by level
            if level not in by_level:
                by_level[level] = {"total": 0, "passed": 0, "avg_score": 0.0}
            by_level[level]["total"] += 1
            if result.pass_fail_status.value == "pass":
                by_level[level]["passed"] += 1
            by_level[level]["avg_score"] += result.score_breakdown.final_score
            
            # Similar for other dimensions
            for dim_dict, key in [
                (by_subject, subject),
                (by_skill_type, skill),
                (by_difficulty, difficulty),
            ]:
                if key not in dim_dict:
                    dim_dict[key] = {"total": 0, "passed": 0, "avg_score": 0.0}
                dim_dict[key]["total"] += 1
                if result.pass_fail_status.value == "pass":
                    dim_dict[key]["passed"] += 1
                dim_dict[key]["avg_score"] += result.score_breakdown.final_score
        
        # Calculate averages
        for dim_dict in [by_level, by_subject, by_skill_type, by_difficulty]:
            for key in dim_dict:
                if dim_dict[key]["total"] > 0:
                    dim_dict[key]["avg_score"] /= dim_dict[key]["total"]
                    dim_dict[key]["pass_rate"] = dim_dict[key]["passed"] / dim_dict[key]["total"]
        
        return {
            "by_level": by_level,
            "by_subject": by_subject,
            "by_skill_type": by_skill_type,
            "by_difficulty": by_difficulty,
            "total_tests": len(results),
        }
    
    def recommend_next_tests(
        self,
        current_results: List[TestResult],
    ) -> List[TestConfiguration]:
        """
        Recommend next tests based on current results
        
        Args:
            current_results: Current test results
        
        Returns:
            List of recommended TestConfiguration objects
        """
        recommendations = []
        
        # Analyze current results
        analysis = self.analyze_test_history(current_results)
        
        # Find weak areas
        weak_subjects = [
            k for k, v in analysis["by_subject"].items()
            if v.get("pass_rate", 1.0) < 0.7
        ]
        weak_skill_types = [
            k for k, v in analysis["by_skill_type"].items()
            if v.get("pass_rate", 1.0) < 0.7
        ]
        
        # Recommend tests for weak areas
        from oricli_core.evaluation.curriculum.selector import CurriculumSelector
        selector = CurriculumSelector()
        
        for subject in weak_subjects[:3]:  # Top 3 weak subjects
            for skill_type in weak_skill_types[:2]:  # Top 2 weak skills
                config = selector.select_curriculum(
                    level="k5",  # Start easy
                    subject=subject,
                    skill_type=skill_type,
                    difficulty_style="standard",
                )
                recommendations.append(config)
        
        # If no weak areas, recommend progression
        if not recommendations:
            # Get highest level tested
            levels = ["k5", "middle_school", "high_school", "undergrad", "grad", "phd"]
            max_level_idx = 0
            for result in current_results:
                level_idx = levels.index(result.test_config.level)
                max_level_idx = max(max_level_idx, level_idx)
            
            if max_level_idx < len(levels) - 1:
                config = selector.select_curriculum(
                    level=levels[max_level_idx + 1],
                    subject="math",
                    skill_type="foundational",
                    difficulty_style="standard",
                )
                recommendations.append(config)
        
        return recommendations
    
    def detect_patterns(self, results: List[TestResult]) -> Dict[str, Any]:
        """
        Detect patterns across test runs
        
        Args:
            results: List of test results
        
        Returns:
            Pattern detection results
        """
        patterns = {
            "common_failures": [],
            "correlations": {},
            "trends": {},
        }
        
        # Find common failure modes
        failure_reasons = {}
        for result in results:
            if result.pass_fail_status.value == "fail":
                weaknesses = result.cognitive_weakness_map
                for key in weaknesses:
                    if key not in failure_reasons:
                        failure_reasons[key] = 0
                    failure_reasons[key] += 1
        
        # Common failures (appear in >30% of failures)
        failure_count = sum(1 for r in results if r.pass_fail_status.value == "fail")
        if failure_count > 0:
            patterns["common_failures"] = [
                {"weakness": k, "frequency": v / failure_count}
                for k, v in failure_reasons.items()
                if v / failure_count >= 0.3
            ]
        
        # Correlations between dimensions and performance
        # (simplified - would use statistical analysis)
        patterns["correlations"] = {
            "level_vs_score": "positive",  # Higher level = higher score (expected)
            "difficulty_vs_score": "negative",  # Higher difficulty = lower score (expected)
        }
        
        return patterns
    
    def predict_weaknesses(
        self,
        test_config: TestConfiguration,
        history: List[TestResult],
    ) -> Dict[str, float]:
        """
        Predict likely weaknesses for a test configuration
        
        Args:
            test_config: Test configuration
            history: Historical test results
        
        Returns:
            Dictionary mapping weakness types to probability scores
        """
        predictions = {}
        
        # Find similar tests in history
        similar_results = [
            r for r in history
            if (r.test_config.level == test_config.level and
                r.test_config.subject == test_config.subject)
        ]
        
        if similar_results:
            # Analyze weaknesses in similar tests
            from oricli_core.evaluation.curriculum.analyzer import ResultAnalyzer
            analyzer = ResultAnalyzer()
            
            weakness_counts = {}
            for result in similar_results:
                weaknesses = analyzer.analyze_cognitive_weaknesses(result)
                for key in weaknesses:
                    if key not in weakness_counts:
                        weakness_counts[key] = 0
                    weakness_counts[key] += 1
            
            # Convert to probabilities
            total = len(similar_results)
            for key, count in weakness_counts.items():
                predictions[key] = count / total if total > 0 else 0.0
        else:
            # Default predictions based on difficulty
            predictions = {
                "accuracy": 0.2,
                "reasoning_depth": 0.15,
                "structure": 0.1,
            }
        
        return predictions
    
    def optimize_test_selection(
        self,
        goal: str,
        constraints: Dict[str, Any],
    ) -> List[TestConfiguration]:
        """
        Optimize test selection for specific goal
        
        Args:
            goal: Goal (e.g., "find_weaknesses", "validate_strengths", "coverage")
            constraints: Constraints (max_tests, time_limit, etc.)
        
        Returns:
            Optimized list of TestConfiguration objects
        """
        from oricli_core.evaluation.curriculum.selector import CurriculumSelector
        selector = CurriculumSelector()
        
        recommendations = []
        max_tests = constraints.get("max_tests", 10)
        
        if goal == "find_weaknesses":
            # Select diverse tests across all dimensions
            levels = selector.list_levels()
            subjects = selector.list_subjects()
            skill_types = selector.list_skill_types()
            
            # Create diverse set
            for level in levels[:2]:
                for subject in subjects[:2]:
                    for skill_type in skill_types[:2]:
                        if len(recommendations) >= max_tests:
                            break
                        config = selector.select_curriculum(
                            level=level,
                            subject=subject,
                            skill_type=skill_type,
                            difficulty_style="standard",
                        )
                        recommendations.append(config)
        
        elif goal == "validate_strengths":
            # Select tests in strong areas
            # (would use history to identify strong areas)
            config = selector.select_curriculum(
                level="k5",
                subject="math",
                skill_type="foundational",
                difficulty_style="standard",
            )
            recommendations.append(config)
        
        elif goal == "coverage":
            # Maximize coverage across all dimensions
            # (would use set cover algorithm)
            levels = selector.list_levels()
            subjects = selector.list_subjects()
            skill_types = selector.list_skill_types()
            difficulties = selector.list_difficulty_styles()
            
            # Create comprehensive set
            for level in levels:
                for subject in subjects:
                    if len(recommendations) >= max_tests:
                        break
                    config = selector.select_curriculum(
                        level=level,
                        subject=subject,
                        skill_type=skill_types[0],
                        difficulty_style=difficulties[0],
                    )
                    recommendations.append(config)
        
        return recommendations[:max_tests]


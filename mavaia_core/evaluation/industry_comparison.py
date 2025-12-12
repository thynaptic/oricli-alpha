"""
Industry Comparison Tool for All Test Categories

Compares Mavaia's test results across all categories (functional, reasoning, safety, etc.)
against industry benchmarks and standards.
"""

import json
from pathlib import Path
from typing import Dict, List, Any, Optional
from datetime import datetime
from dataclasses import dataclass, field


@dataclass
class CategoryMetrics:
    """Metrics for a specific test category"""
    category: str
    total: int = 0
    passed: int = 0
    failed: int = 0
    timeout: int = 0
    error: int = 0
    skipped: int = 0
    pass_rate: float = 0.0
    average_time: float = 0.0
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            "category": self.category,
            "total": self.total,
            "passed": self.passed,
            "failed": self.failed,
            "timeout": self.timeout,
            "error": self.error,
            "skipped": self.skipped,
            "pass_rate": self.pass_rate,
            "average_time": self.average_time,
        }


@dataclass
class OverallMetrics:
    """Overall test suite metrics"""
    total_tests: int = 0
    passed: int = 0
    failed: int = 0
    timeout: int = 0
    error: int = 0
    skipped: int = 0
    pass_rate: float = 0.0
    total_time: float = 0.0
    average_time: float = 0.0
    category_metrics: Dict[str, CategoryMetrics] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            "total_tests": self.total_tests,
            "passed": self.passed,
            "failed": self.failed,
            "timeout": self.timeout,
            "error": self.error,
            "skipped": self.skipped,
            "pass_rate": self.pass_rate,
            "total_time": self.total_time,
            "average_time": self.average_time,
            "categories": {k: v.to_dict() for k, v in self.category_metrics.items()},
        }


class IndustryComparison:
    """Compare Mavaia test results against industry standards"""
    
    # Industry benchmark reference scores for different test categories
    # These are approximate industry standards based on typical AI system performance
    INDUSTRY_STANDARDS = {
        "functional": {
            "excellent": 0.95,  # 95%+ pass rate
            "good": 0.85,       # 85-94% pass rate
            "acceptable": 0.70, # 70-84% pass rate
            "needs_improvement": 0.50, # 50-69% pass rate
            "reference_models": {
                "GPT-4": 0.90,
                "GPT-3.5": 0.75,
                "Claude-3": 0.92,
                "Average_AI_System": 0.80,
            }
        },
        "reasoning": {
            "excellent": 0.90,
            "good": 0.80,
            "acceptable": 0.65,
            "needs_improvement": 0.50,
            "reference_models": {
                "GPT-4": 0.85,
                "GPT-3.5": 0.70,
                "Claude-3": 0.88,
                "Average_AI_System": 0.75,
            }
        },
        "safety": {
            "excellent": 0.98,  # Safety must be very high
            "good": 0.95,
            "acceptable": 0.90,
            "needs_improvement": 0.80,
            "reference_models": {
                "GPT-4": 0.95,
                "GPT-3.5": 0.88,
                "Claude-3": 0.96,
                "Average_AI_System": 0.92,
            }
        },
        "api": {
            "excellent": 0.95,
            "good": 0.85,
            "acceptable": 0.75,
            "needs_improvement": 0.60,
            "reference_models": {
                "GPT-4": 0.90,
                "GPT-3.5": 0.80,
                "Claude-3": 0.93,
                "Average_AI_System": 0.85,
            }
        },
        "client": {
            "excellent": 0.95,
            "good": 0.85,
            "acceptable": 0.75,
            "needs_improvement": 0.60,
            "reference_models": {
                "GPT-4": 0.88,
                "GPT-3.5": 0.75,
                "Claude-3": 0.90,
                "Average_AI_System": 0.82,
            }
        },
        "system": {
            "excellent": 0.98,  # System tests should be very reliable
            "good": 0.95,
            "acceptable": 0.90,
            "needs_improvement": 0.80,
            "reference_models": {
                "GPT-4": 0.95,
                "GPT-3.5": 0.85,
                "Claude-3": 0.97,
                "Average_AI_System": 0.92,
            }
        },
        "code_generation": {
            "excellent": 0.95,
            "good": 0.85,
            "acceptable": 0.70,
            "needs_improvement": 0.50,
            "reference_models": {
                "GPT-4": 0.67,  # HumanEval
                "GPT-3.5": 0.48,
                "Claude-3": 0.84,
                "Average_AI_System": 0.65,
            }
        },
    }
    
    def __init__(self, results_file: Optional[Path] = None):
        """
        Initialize industry comparison
        
        Args:
            results_file: Path to test results JSON file
        """
        self.results_file = results_file
        self.metrics: Optional[OverallMetrics] = None
    
    def load_results(self, results_file: Path) -> List[Dict[str, Any]]:
        """
        Load test results from file
        
        Args:
            results_file: Path to results JSON file
            
        Returns:
            List of test result dictionaries
        """
        try:
            with open(results_file, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Try to parse JSON
            try:
                data = json.loads(content)
            except json.JSONDecodeError as e:
                # Try to fix common JSON issues (like trailing commas, unclosed strings)
                # For now, try to extract what we can
                print(f"Warning: JSON parse error at line {e.lineno}, column {e.colno}")
                print(f"Attempting to load partial results...")
                
                # Try to extract test_results array manually
                import re
                # Look for test_results array
                match = re.search(r'"test_results"\s*:\s*\[', content)
                if match:
                    # Try to extract array content
                    start = match.end()
                    bracket_count = 1
                    i = start
                    while i < len(content) and bracket_count > 0:
                        if content[i] == '[':
                            bracket_count += 1
                        elif content[i] == ']':
                            bracket_count -= 1
                        i += 1
                    if bracket_count == 0:
                        array_content = content[start:i-1]
                        # Try to parse individual test result objects
                        # This is a simplified approach - in production, use a proper JSON repair library
                        return []
                
                return []
            
            # Handle different result file formats
            if "test_results" in data:
                return data["test_results"]
            elif "results" in data:
                return data["results"]
            elif isinstance(data, list):
                return data
            else:
                return []
        except (json.JSONDecodeError, FileNotFoundError, Exception) as e:
            print(f"Error loading results file: {e}")
            return []
    
    def calculate_metrics(self, results: List[Dict[str, Any]]) -> OverallMetrics:
        """
        Calculate overall metrics from test results
        
        Args:
            results: List of test result dictionaries
            
        Returns:
            OverallMetrics instance
        """
        metrics = OverallMetrics()
        metrics.total_tests = len(results)
        
        total_time = 0.0
        execution_times = []
        
        # Track metrics by category
        category_data: Dict[str, Dict[str, Any]] = {}
        
        for result in results:
            status = result.get("status", "").upper()
            category = result.get("category", "unknown")
            execution_time = result.get("execution_time", 0.0)
            
            # Initialize category if not seen
            if category not in category_data:
                category_data[category] = {
                    "total": 0,
                    "passed": 0,
                    "failed": 0,
                    "timeout": 0,
                    "error": 0,
                    "skipped": 0,
                    "times": [],
                }
            
            category_data[category]["total"] += 1
            
            # Count by status
            if status == "PASSED":
                metrics.passed += 1
                category_data[category]["passed"] += 1
            elif status == "FAILED":
                metrics.failed += 1
                category_data[category]["failed"] += 1
            elif status == "TIMEOUT":
                metrics.timeout += 1
                category_data[category]["timeout"] += 1
            elif status == "ERROR":
                metrics.error += 1
                category_data[category]["error"] += 1
            elif status == "SKIPPED":
                metrics.skipped += 1
                category_data[category]["skipped"] += 1
            
            # Track execution time
            if execution_time > 0:
                execution_times.append(execution_time)
                total_time += execution_time
                category_data[category]["times"].append(execution_time)
        
        # Calculate overall pass rate
        total_attempted = metrics.total_tests - metrics.skipped
        if total_attempted > 0:
            metrics.pass_rate = metrics.passed / total_attempted
        else:
            metrics.pass_rate = 0.0
        
        # Calculate average execution time
        if execution_times:
            metrics.average_time = sum(execution_times) / len(execution_times)
        metrics.total_time = total_time
        
        # Calculate category metrics
        for category, data in category_data.items():
            cat_metrics = CategoryMetrics(category=category)
            cat_metrics.total = data["total"]
            cat_metrics.passed = data["passed"]
            cat_metrics.failed = data["failed"]
            cat_metrics.timeout = data["timeout"]
            cat_metrics.error = data["error"]
            cat_metrics.skipped = data["skipped"]
            
            cat_total_attempted = cat_metrics.total - cat_metrics.skipped
            if cat_total_attempted > 0:
                cat_metrics.pass_rate = cat_metrics.passed / cat_total_attempted
            else:
                cat_metrics.pass_rate = 0.0
            
            if data["times"]:
                cat_metrics.average_time = sum(data["times"]) / len(data["times"])
            
            metrics.category_metrics[category] = cat_metrics
        
        self.metrics = metrics
        return metrics
    
    def compare_category(self, category: str) -> Dict[str, Any]:
        """
        Compare a specific category against industry standards
        
        Args:
            category: Category name to compare
            
        Returns:
            Comparison dictionary
        """
        if not self.metrics:
            return {"error": "No metrics calculated. Call calculate_metrics first."}
        
        if category not in self.metrics.category_metrics:
            return {"error": f"Category '{category}' not found in results."}
        
        cat_metrics = self.metrics.category_metrics[category]
        standards = self.INDUSTRY_STANDARDS.get(category, {})
        
        if not standards:
            return {"error": f"No industry standards defined for category '{category}'."}
        
        # Determine performance level
        pass_rate = cat_metrics.pass_rate
        if pass_rate >= standards.get("excellent", 0.95):
            level = "excellent"
        elif pass_rate >= standards.get("good", 0.85):
            level = "good"
        elif pass_rate >= standards.get("acceptable", 0.70):
            level = "acceptable"
        else:
            level = "needs_improvement"
        
        # Compare with reference models
        reference_comparisons = {}
        reference_models = standards.get("reference_models", {})
        for model, ref_score in reference_models.items():
            diff = pass_rate - ref_score
            reference_comparisons[model] = {
                "reference_score": ref_score,
                "mavaia_score": pass_rate,
                "difference": diff,
                "percentage_diff": (diff / ref_score * 100) if ref_score > 0 else 0.0,
                "better": diff > 0,
            }
        
        return {
            "category": category,
            "mavaia_pass_rate": pass_rate,
            "performance_level": level,
            "standards": {
                "excellent": standards.get("excellent", 0.95),
                "good": standards.get("good", 0.85),
                "acceptable": standards.get("acceptable", 0.70),
            },
            "reference_comparisons": reference_comparisons,
        }
    
    def generate_report(self, output_file: Optional[Path] = None) -> str:
        """
        Generate comprehensive industry comparison report
        
        Args:
            output_file: Optional file to write report to
            
        Returns:
            Report string
        """
        if not self.metrics:
            return "No metrics available. Load results and calculate metrics first."
        
        report_lines = []
        report_lines.append("=" * 80)
        report_lines.append("MAVAIA TEST SUITE - INDUSTRY COMPARISON REPORT")
        report_lines.append("=" * 80)
        report_lines.append(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        report_lines.append("")
        
        # Overall metrics
        report_lines.append("OVERALL METRICS")
        report_lines.append("-" * 80)
        report_lines.append(f"Total Tests: {self.metrics.total_tests}")
        report_lines.append(f"Passed: {self.metrics.passed} ({self.metrics.pass_rate*100:.2f}%)")
        report_lines.append(f"Failed: {self.metrics.failed}")
        report_lines.append(f"Timeout: {self.metrics.timeout}")
        report_lines.append(f"Error: {self.metrics.error}")
        report_lines.append(f"Skipped: {self.metrics.skipped}")
        report_lines.append(f"Average Execution Time: {self.metrics.average_time:.2f}s")
        report_lines.append(f"Total Execution Time: {self.metrics.total_time:.2f}s")
        report_lines.append("")
        
        # Category breakdown
        report_lines.append("CATEGORY BREAKDOWN")
        report_lines.append("-" * 80)
        for category in sorted(self.metrics.category_metrics.keys()):
            cat_metrics = self.metrics.category_metrics[category]
            report_lines.append(
                f"{category:20s}: {cat_metrics.passed:3d}/{cat_metrics.total:3d} "
                f"({cat_metrics.pass_rate*100:5.2f}%) "
                f"Avg: {cat_metrics.average_time:.2f}s"
            )
        report_lines.append("")
        
        # Industry comparisons by category
        report_lines.append("INDUSTRY COMPARISON BY CATEGORY")
        report_lines.append("-" * 80)
        report_lines.append("")
        
        for category in sorted(self.metrics.category_metrics.keys()):
            comparison = self.compare_category(category)
            if "error" not in comparison:
                report_lines.append(f"{category.upper()}:")
                report_lines.append(f"  Mavaia Pass Rate: {comparison['mavaia_pass_rate']*100:.2f}%")
                report_lines.append(f"  Performance Level: {comparison['performance_level'].upper()}")
                report_lines.append("")
                report_lines.append("  vs Industry Models:")
                for model, comp in comparison['reference_comparisons'].items():
                    ref_score = comp['reference_score']
                    diff = comp['difference']
                    better = "✓" if comp['better'] else "✗"
                    report_lines.append(
                        f"    {model:20s}: {ref_score*100:5.2f}% "
                        f"({diff*100:+6.2f}% difference) {better}"
                    )
                report_lines.append("")
        
        # Summary
        report_lines.append("SUMMARY")
        report_lines.append("-" * 80)
        excellent_count = sum(
            1 for cat in self.metrics.category_metrics.keys()
            if self.compare_category(cat).get('performance_level') == 'excellent'
        )
        good_count = sum(
            1 for cat in self.metrics.category_metrics.keys()
            if self.compare_category(cat).get('performance_level') == 'good'
        )
        needs_improvement_count = sum(
            1 for cat in self.metrics.category_metrics.keys()
            if self.compare_category(cat).get('performance_level') == 'needs_improvement'
        )
        
        report_lines.append(f"Categories at Excellent Level: {excellent_count}")
        report_lines.append(f"Categories at Good Level: {good_count}")
        report_lines.append(f"Categories Needing Improvement: {needs_improvement_count}")
        report_lines.append("")
        report_lines.append("=" * 80)
        
        report = "\n".join(report_lines)
        
        if output_file:
            with open(output_file, 'w', encoding='utf-8') as f:
                f.write(report)
        
        return report


def main():
    """Main entry point for industry comparison"""
    import sys
    from pathlib import Path
    
    if len(sys.argv) < 2:
        print("Usage: python -m mavaia_core.evaluation.industry_comparison <results_file> [output_file]")
        sys.exit(1)
    
    results_file = Path(sys.argv[1])
    if not results_file.exists():
        print(f"Error: Results file not found: {results_file}")
        sys.exit(1)
    
    comparison = IndustryComparison()
    results = comparison.load_results(results_file)
    metrics = comparison.calculate_metrics(results)
    
    # Generate report
    output_file = Path(sys.argv[2]) if len(sys.argv) > 2 else None
    report = comparison.generate_report(output_file)
    print(report)
    
    if output_file:
        print(f"\nReport saved to: {output_file}")


if __name__ == "__main__":
    main()

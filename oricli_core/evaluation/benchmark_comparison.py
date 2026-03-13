from __future__ import annotations
"""
Benchmark Comparison Tool

Generates industry-standard metrics and comparisons for Python coding benchmarks.
Compares Oricli-Alpha's performance against reference benchmarks (HumanEval, MBPP, APPS).
"""

import json
import logging
import sys
from pathlib import Path
from typing import Dict, List, Any, Optional
from datetime import datetime
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)


@dataclass
class BenchmarkMetrics:
    """Metrics for a benchmark run"""
    total_problems: int = 0
    passed: int = 0
    failed: int = 0
    timeout: int = 0
    error: int = 0
    skipped: int = 0
    pass_rate: float = 0.0
    average_execution_time: float = 0.0
    total_execution_time: float = 0.0
    
    # Difficulty breakdown
    easy_passed: int = 0
    easy_total: int = 0
    medium_passed: int = 0
    medium_total: int = 0
    hard_passed: int = 0
    hard_total: int = 0
    
    # Category breakdown
    category_stats: Dict[str, Dict[str, int]] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            "total_problems": self.total_problems,
            "passed": self.passed,
            "failed": self.failed,
            "timeout": self.timeout,
            "error": self.error,
            "skipped": self.skipped,
            "pass_rate": self.pass_rate,
            "average_execution_time": self.average_execution_time,
            "total_execution_time": self.total_execution_time,
            "difficulty_breakdown": {
                "easy": {
                    "passed": self.easy_passed,
                    "total": self.easy_total,
                    "pass_rate": self.easy_passed / self.easy_total if self.easy_total > 0 else 0.0
                },
                "medium": {
                    "passed": self.medium_passed,
                    "total": self.medium_total,
                    "pass_rate": self.medium_passed / self.medium_total if self.medium_total > 0 else 0.0
                },
                "hard": {
                    "passed": self.hard_passed,
                    "total": self.hard_total,
                    "pass_rate": self.hard_passed / self.hard_total if self.hard_total > 0 else 0.0
                }
            },
            "category_stats": self.category_stats
        }


class BenchmarkComparison:
    """Compare benchmark results against industry standards"""
    
    # Reference benchmark scores (approximate, for comparison)
    REFERENCE_SCORES = {
        "HumanEval": {
            "GPT-4": 0.67,  # 67% pass@1
            "GPT-3.5": 0.48,  # 48% pass@1
            "Claude-3": 0.84,  # 84% pass@1
            "CodeLlama-7B": 0.26,  # 26% pass@1
        },
        "MBPP": {
            "GPT-4": 0.75,
            "GPT-3.5": 0.56,
            "Claude-3": 0.88,
            "CodeLlama-7B": 0.32,
        },
        "APPS": {
            "GPT-4": 0.15,  # 15% accuracy (APPS is harder)
            "GPT-3.5": 0.08,
            "Claude-3": 0.22,
            "CodeLlama-7B": 0.05,
        }
    }
    
    def __init__(self, results_file: Optional[Path] = None):
        """
        Initialize benchmark comparison
        
        Args:
            results_file: Path to test results JSON file
        """
        self.results_file = results_file
        self.metrics: Optional[BenchmarkMetrics] = None
    
    def load_results(self, results_file: Path) -> List[Dict[str, Any]]:
        """
        Load test results from file
        
        Args:
            results_file: Path to results JSON file
            
        Returns:
            List of test results
        """
        with open(results_file, 'r') as f:
            data = json.load(f)
        
        # Handle different result file formats
        if "test_results" in data:
            return data["test_results"]
        elif "results" in data:
            return data["results"]
        elif isinstance(data, list):
            return data
        else:
            return []
    
    def calculate_metrics(self, results: List[Dict[str, Any]]) -> BenchmarkMetrics:
        """
        Calculate benchmark metrics from results
        
        Args:
            results: List of test result dictionaries
            
        Returns:
            BenchmarkMetrics instance
        """
        metrics = BenchmarkMetrics()
        metrics.total_problems = len(results)
        
        total_time = 0.0
        execution_times = []
        
        for result in results:
            status = result.get("status", "").upper()
            tags = result.get("tags", [])
            category = result.get("category", "")
            execution_time = result.get("execution_time", 0.0)
            
            # Count by status
            if status == "PASSED":
                metrics.passed += 1
            elif status == "FAILED":
                metrics.failed += 1
            elif status == "TIMEOUT":
                metrics.timeout += 1
            elif status == "ERROR":
                metrics.error += 1
            elif status == "SKIPPED":
                metrics.skipped += 1
            
            # Track execution time
            if execution_time > 0:
                execution_times.append(execution_time)
                total_time += execution_time
            
            # Difficulty breakdown
            if "easy" in tags:
                metrics.easy_total += 1
                if status == "PASSED":
                    metrics.easy_passed += 1
            elif "medium" in tags:
                metrics.medium_total += 1
                if status == "PASSED":
                    metrics.medium_passed += 1
            elif "hard" in tags:
                metrics.hard_total += 1
                if status == "PASSED":
                    metrics.hard_passed += 1
            
            # Category breakdown
            if category:
                if category not in metrics.category_stats:
                    metrics.category_stats[category] = {
                        "total": 0,
                        "passed": 0,
                        "failed": 0,
                    }
                metrics.category_stats[category]["total"] += 1
                if status == "PASSED":
                    metrics.category_stats[category]["passed"] += 1
                elif status == "FAILED":
                    metrics.category_stats[category]["failed"] += 1
        
        # Calculate pass rate
        total_attempted = metrics.total_problems - metrics.skipped
        if total_attempted > 0:
            metrics.pass_rate = metrics.passed / total_attempted
        else:
            metrics.pass_rate = 0.0
        
        # Calculate average execution time
        if execution_times:
            metrics.average_execution_time = sum(execution_times) / len(execution_times)
        metrics.total_execution_time = total_time
        
        self.metrics = metrics
        return metrics
    
    def compare_with_references(self, benchmark_name: str = "HumanEval") -> Dict[str, Any]:
        """
        Compare results with reference benchmarks
        
        Args:
            benchmark_name: Name of reference benchmark (HumanEval, MBPP, APPS)
            
        Returns:
            Comparison dictionary
        """
        if not self.metrics:
            return {"error": "No metrics calculated. Call calculate_metrics first."}
        
        reference_scores = self.REFERENCE_SCORES.get(benchmark_name, {})
        
        comparison = {
            "benchmark": benchmark_name,
            "oricli_pass_rate": self.metrics.pass_rate,
            "reference_scores": reference_scores,
            "comparison": {}
        }
        
        for model, score in reference_scores.items():
            diff = self.metrics.pass_rate - score
            comparison["comparison"][model] = {
                "reference_score": score,
                "oricli_score": self.metrics.pass_rate,
                "difference": diff,
                "percentage_diff": (diff / score * 100) if score > 0 else 0.0,
                "better": diff > 0
            }
        
        return comparison
    
    def generate_report(self, output_file: Optional[Path] = None) -> str:
        """
        Generate a comprehensive benchmark report
        
        Args:
            output_file: Optional file to write report to
            
        Returns:
            Report string
        """
        if not self.metrics:
            return "No metrics available. Load results and calculate metrics first."
        
        report_lines = []
        report_lines.append("=" * 80)
        report_lines.append("MAVAIA PYTHON CODING BENCHMARK REPORT")
        report_lines.append("=" * 80)
        report_lines.append(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        report_lines.append("")
        
        # Overall metrics
        report_lines.append("OVERALL METRICS")
        report_lines.append("-" * 80)
        report_lines.append(f"Total Problems: {self.metrics.total_problems}")
        report_lines.append(f"Passed: {self.metrics.passed} ({self.metrics.pass_rate*100:.2f}%)")
        report_lines.append(f"Failed: {self.metrics.failed}")
        report_lines.append(f"Timeout: {self.metrics.timeout}")
        report_lines.append(f"Error: {self.metrics.error}")
        report_lines.append(f"Skipped: {self.metrics.skipped}")
        report_lines.append(f"Average Execution Time: {self.metrics.average_execution_time:.2f}s")
        report_lines.append(f"Total Execution Time: {self.metrics.total_execution_time:.2f}s")
        report_lines.append("")
        
        # Difficulty breakdown
        report_lines.append("DIFFICULTY BREAKDOWN")
        report_lines.append("-" * 80)
        if self.metrics.easy_total > 0:
            easy_rate = self.metrics.easy_passed / self.metrics.easy_total
            report_lines.append(f"Easy: {self.metrics.easy_passed}/{self.metrics.easy_total} ({easy_rate*100:.2f}%)")
        if self.metrics.medium_total > 0:
            medium_rate = self.metrics.medium_passed / self.metrics.medium_total
            report_lines.append(f"Medium: {self.metrics.medium_passed}/{self.metrics.medium_total} ({medium_rate*100:.2f}%)")
        if self.metrics.hard_total > 0:
            hard_rate = self.metrics.hard_passed / self.metrics.hard_total
            report_lines.append(f"Hard: {self.metrics.hard_passed}/{self.metrics.hard_total} ({hard_rate*100:.2f}%)")
        report_lines.append("")
        
        # Category breakdown
        if self.metrics.category_stats:
            report_lines.append("CATEGORY BREAKDOWN")
            report_lines.append("-" * 80)
            for category, stats in self.metrics.category_stats.items():
                total = stats["total"]
                passed = stats["passed"]
                rate = passed / total if total > 0 else 0.0
                report_lines.append(f"{category}: {passed}/{total} ({rate*100:.2f}%)")
            report_lines.append("")
        
        # Comparison with references
        report_lines.append("COMPARISON WITH INDUSTRY BENCHMARKS")
        report_lines.append("-" * 80)
        
        for benchmark_name in ["HumanEval", "MBPP", "APPS"]:
            comparison = self.compare_with_references(benchmark_name)
            if "error" not in comparison:
                report_lines.append(f"\n{benchmark_name}:")
                report_lines.append(f"  Oricli-Alpha Pass Rate: {self.metrics.pass_rate*100:.2f}%")
                for model, comp in comparison["comparison"].items():
                    ref_score = comp["reference_score"]
                    diff = comp["difference"]
                    better = "✓" if comp["better"] else "✗"
                    report_lines.append(
                        f"  vs {model}: {ref_score*100:.2f}% "
                        f"({diff*100:+.2f}% difference) {better}"
                    )
        
        report_lines.append("")
        report_lines.append("=" * 80)
        
        report = "\n".join(report_lines)
        
        if output_file:
            with open(output_file, 'w') as f:
                f.write(report)
        
        return report
    
    def export_json(self, output_file: Path) -> None:
        """
        Export metrics to JSON
        
        Args:
            output_file: Path to output JSON file
        """
        if not self.metrics:
            return
        
        data = {
            "timestamp": datetime.now().isoformat(),
            "metrics": self.metrics.to_dict(),
            "comparisons": {}
        }
        
        for benchmark_name in ["HumanEval", "MBPP", "APPS"]:
            data["comparisons"][benchmark_name] = self.compare_with_references(benchmark_name)
        
        with open(output_file, 'w') as f:
            json.dump(data, f, indent=2)


def main():
    """Main entry point for benchmark comparison"""
    import sys
    from pathlib import Path
    
    if len(sys.argv) < 2:
        print("Usage: python -m oricli_core.evaluation.benchmark_comparison <results_file> [output_file]")
        sys.exit(1)
    
    results_file = Path(sys.argv[1])
    if not results_file.exists():
        print(f"Error: Results file not found: {results_file}")
        sys.exit(1)
    
    comparison = BenchmarkComparison()
    results = comparison.load_results(results_file)
    metrics = comparison.calculate_metrics(results)
    
    # Generate report
    output_file = Path(sys.argv[2]) if len(sys.argv) > 2 else None
    report = comparison.generate_report(output_file)
    print(report)
    
    # Export JSON
    if output_file:
        json_file = output_file.with_suffix('.json')
        comparison.export_json(json_file)
        print(f"\nJSON metrics exported to: {json_file}")


if __name__ == "__main__":
    main()

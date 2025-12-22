"""
Output Formatter

Generates structured JSON/HTML reports, reasoning trace visualization,
and cognitive maps.
"""

import json
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from mavaia_core.evaluation.curriculum.models import TestResult, PassFailStatus


class TestReporter:
    """Generates reports from test results"""
    
    def __init__(self, output_dir: Optional[Path] = None):
        """
        Initialize test reporter
        
        Args:
            output_dir: Output directory for reports
        """
        if output_dir is None:
            output_dir = Path(__file__).parent / "results"
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
    
    def generate_json_report(
        self,
        results: List[TestResult],
        filename: Optional[str] = None,
    ) -> Path:
        """
        Generate JSON report
        
        Args:
            results: List of test results
            filename: Output filename (auto-generated if None)
        
        Returns:
            Path to generated report
        """
        if filename is None:
            timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
            filename = f"curriculum_test_results_{timestamp}.json"
        
        output_path = self.output_dir / filename
        
        report_data = {
            "timestamp": datetime.utcnow().isoformat(),
            "total_tests": len(results),
            "results": [r.to_dict() for r in results],
            "summary": self._generate_summary(results),
        }
        
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(report_data, f, indent=2, ensure_ascii=False)
        
        return output_path
    
    def generate_html_report(
        self,
        results: List[TestResult],
        filename: Optional[str] = None,
    ) -> Path:
        """
        Generate HTML report
        
        Args:
            results: List of test results
            filename: Output filename (auto-generated if None)
        
        Returns:
            Path to generated report
        """
        if filename is None:
            timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
            filename = f"curriculum_test_report_{timestamp}.html"
        
        output_path = self.output_dir / filename
        
        html_content = self._generate_html_content(results)
        
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(html_content)
        
        return output_path
    
    def _generate_summary(self, results: List[TestResult]) -> Dict[str, Any]:
        """Generate summary statistics"""
        total = len(results)
        
        if total == 0:
            return {
                "total_tests": 0,
                "passed": 0,
                "failed": 0,
                "partial": 0,
                "pass_rate": 0.0,
                "average_score": 0.0,
                "average_execution_time": 0.0,
            }
        
        passed = sum(1 for r in results if r.pass_fail_status == PassFailStatus.PASS)
        failed = sum(1 for r in results if r.pass_fail_status == PassFailStatus.FAIL)
        partial = sum(1 for r in results if r.pass_fail_status == PassFailStatus.PARTIAL)
        
        avg_score = sum(r.score_breakdown.final_score for r in results) / total if total > 0 else 0.0
        avg_time = sum(r.execution_time for r in results) / total if total > 0 else 0.0
        
        return {
            "total_tests": total,
            "passed": passed,
            "failed": failed,
            "partial": partial,
            "pass_rate": passed / total if total > 0 else 0.0,
            "average_score": avg_score,
            "average_execution_time": avg_time,
        }
    
    def _generate_html_content(self, results: List[TestResult]) -> str:
        """Generate HTML report content"""
        summary = self._generate_summary(results)
        
        html = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Curriculum Test Report</title>
    <style>
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            margin: 0;
            padding: 20px;
            background: #f5f5f5;
        }}
        .container {{
            max-width: 1200px;
            margin: 0 auto;
            background: white;
            padding: 30px;
            border-radius: 8px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }}
        h1 {{
            color: #333;
            border-bottom: 3px solid #4CAF50;
            padding-bottom: 10px;
        }}
        .summary {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 20px;
            margin: 20px 0;
        }}
        .summary-card {{
            background: #f9f9f9;
            padding: 20px;
            border-radius: 6px;
            border-left: 4px solid #4CAF50;
        }}
        .summary-card h3 {{
            margin: 0 0 10px 0;
            color: #666;
            font-size: 14px;
            text-transform: uppercase;
        }}
        .summary-card .value {{
            font-size: 32px;
            font-weight: bold;
            color: #333;
        }}
        .results-table {{
            width: 100%;
            border-collapse: collapse;
            margin: 20px 0;
        }}
        .results-table th,
        .results-table td {{
            padding: 12px;
            text-align: left;
            border-bottom: 1px solid #ddd;
        }}
        .results-table th {{
            background: #4CAF50;
            color: white;
            font-weight: 600;
        }}
        .status-pass {{
            color: #4CAF50;
            font-weight: bold;
        }}
        .status-fail {{
            color: #f44336;
            font-weight: bold;
        }}
        .status-partial {{
            color: #ff9800;
            font-weight: bold;
        }}
        .score-bar {{
            width: 100%;
            height: 20px;
            background: #e0e0e0;
            border-radius: 10px;
            overflow: hidden;
        }}
        .score-fill {{
            height: 100%;
            background: linear-gradient(90deg, #4CAF50, #8BC34A);
            transition: width 0.3s;
        }}
    </style>
</head>
<body>
    <div class="container">
        <h1>Curriculum Test Report</h1>
        <p>Generated: {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S UTC')}</p>
        
        <div class="summary">
            <div class="summary-card">
                <h3>Total Tests</h3>
                <div class="value">{summary['total_tests']}</div>
            </div>
            <div class="summary-card">
                <h3>Passed</h3>
                <div class="value">{summary['passed']}</div>
            </div>
            <div class="summary-card">
                <h3>Failed</h3>
                <div class="value">{summary['failed']}</div>
            </div>
            <div class="summary-card">
                <h3>Partial</h3>
                <div class="value">{summary['partial']}</div>
            </div>
            <div class="summary-card">
                <h3>Pass Rate</h3>
                <div class="value">{summary['pass_rate']*100:.1f}%</div>
            </div>
            <div class="summary-card">
                <h3>Average Score</h3>
                <div class="value">{summary['average_score']:.2f}</div>
            </div>
        </div>
        
        <h2>Test Results</h2>
        <table class="results-table">
            <thead>
                <tr>
                    <th>Test ID</th>
                    <th>Configuration</th>
                    <th>Status</th>
                    <th>Score</th>
                    <th>Time</th>
                </tr>
            </thead>
            <tbody>
"""
        
        for result in results:
            status_class = {
                PassFailStatus.PASS: "status-pass",
                PassFailStatus.FAIL: "status-fail",
                PassFailStatus.PARTIAL: "status-partial",
            }.get(result.pass_fail_status, "")
            
            # Handle both enum and string values
            status_value = result.pass_fail_status
            if hasattr(status_value, 'value'):
                status_value = status_value.value
            status_display = str(status_value).upper()
            
            config_str = f"{result.test_config.level}/{result.test_config.subject}/{result.test_config.skill_type}"
            
            html += f"""
                <tr>
                    <td>{result.test_id}</td>
                    <td>{config_str}</td>
                    <td class="{status_class}">{status_display}</td>
                    <td>
                        <div class="score-bar">
                            <div class="score-fill" style="width: {result.score_breakdown.final_score*100}%"></div>
                        </div>
                        {result.score_breakdown.final_score:.2f}
                    </td>
                    <td>{result.execution_time:.2f}s</td>
                </tr>
"""
        
        html += """
            </tbody>
        </table>
    </div>
</body>
</html>
"""
        
        return html
    
    def visualize_reasoning_trace(self, trace: Dict[str, Any]) -> str:
        """
        Generate visualization of reasoning trace
        
        Args:
            trace: Reasoning trace dictionary
        
        Returns:
            HTML/string representation of trace
        """
        if not trace:
            return "No reasoning trace available"
        
        method = trace.get("reasoning_method", "unknown")
        output = [f"Reasoning Method: {method}"]
        
        if "steps" in trace:
            output.append("\nChain-of-Thought Steps:")
            for i, step in enumerate(trace["steps"], 1):
                if isinstance(step, dict):
                    reasoning = step.get("reasoning") or step.get("thought") or step.get("conclusion", "")
                    output.append(f"  Step {i}: {reasoning[:100]}...")
                else:
                    output.append(f"  Step {i}: {str(step)[:100]}...")
        
        if "tree" in trace:
            output.append("\nTree-of-Thought Structure:")
            output.append("  (Tree visualization would be rendered here)")
        
        if "search_result" in trace:
            output.append("\nMCTS Search Result:")
            output.append(f"  {str(trace['search_result'])[:200]}...")
        
        return "\n".join(output)
    
    def visualize_cognitive_maps(
        self,
        weakness_map: Dict[str, Any],
        strength_map: Dict[str, Any],
    ) -> str:
        """
        Generate visualization of cognitive maps
        
        Args:
            weakness_map: Cognitive weakness map
            strength_map: Cognitive strength map
        
        Returns:
            HTML/string representation of maps
        """
        output = []
        
        output.append("Cognitive Weakness Map:")
        for key, value in weakness_map.items():
            if key != "curriculum_dimensions":
                if isinstance(value, dict):
                    severity = value.get("severity", "unknown")
                    reason = value.get("reason", "")
                    output.append(f"  - {key} ({severity}): {reason}")
                else:
                    output.append(f"  - {key}: {value}")
        
        output.append("\nCognitive Strength Map:")
        for key, value in strength_map.items():
            if key != "curriculum_dimensions":
                if isinstance(value, dict):
                    level = value.get("level", "unknown")
                    reason = value.get("reason", "")
                    output.append(f"  - {key} ({level}): {reason}")
                else:
                    output.append(f"  - {key}: {value}")
        
        return "\n".join(output)


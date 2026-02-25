from __future__ import annotations
"""
Test Reporter

Provides real-time progress display, color-coded output, and professional formatting.
Generates HTML reports with charts and detailed analysis.
"""

import sys
from typing import Any, Dict, List, Optional, Union
from datetime import datetime
from pathlib import Path

from mavaia_core.evaluation.test_results import (
    TestRunResults,
    TestResult,
    TestStatus,
)


class Colors:
    """ANSI color codes for terminal output"""
    RESET = "\033[0m"
    BOLD = "\033[1m"
    RED = "\033[31m"
    GREEN = "\033[32m"
    YELLOW = "\033[33m"
    BLUE = "\033[34m"
    MAGENTA = "\033[35m"
    CYAN = "\033[36m"
    WHITE = "\033[37m"
    
    @staticmethod
    def disable() -> None:
        """Disable colors (for non-terminal output)"""
        Colors.RESET = ""
        Colors.BOLD = ""
        Colors.RED = ""
        Colors.GREEN = ""
        Colors.YELLOW = ""
        Colors.BLUE = ""
        Colors.MAGENTA = ""
        Colors.CYAN = ""
        Colors.WHITE = ""


class TestReporter:
    """Handles test reporting and progress display"""
    
    def __init__(self, use_colors: bool = True, verbose: bool = True):
        """
        Initialize test reporter
        
        Args:
            use_colors: Enable color output (default: True)
            verbose: Enable verbose output (default: True)
        """
        self.use_colors = use_colors and sys.stdout.isatty()
        self.verbose = verbose
        
        if not self.use_colors:
            Colors.disable()
        
        self._current_module: Optional[str] = None
        self._test_count = 0
        self._passed_count = 0
        self._failed_count = 0
        self._skipped_count = 0
    
    def print_header(self) -> None:
        """Print test suite header"""
        width = 60
        print()
        print("╔" + "═" * (width - 2) + "╗")
        print("║" + " " * ((width - 34) // 2) + "Mavaia Core Test Suite" + " " * ((width - 34) // 2) + "║")
        print("╠" + "═" * (width - 2) + "╣")
        print()
    
    def print_progress(
        self,
        current: int,
        total: int,
        module: Optional[str] = None,
        test_id: Optional[str] = None
    ) -> None:
        """
        Print progress update
        
        Args:
            current: Current test number
            total: Total number of tests
            module: Current module name
            test_id: Current test ID
        """
        if not self.verbose:
            return
        
        # Update module if changed
        if module and module != self._current_module:
            if self._current_module is not None:
                print()  # Blank line between modules
            self._current_module = module
            print(f"{Colors.CYAN}Module: {module}{Colors.RESET}")
        
        # Calculate progress percentage
        percent = (current / total * 100) if total > 0 else 0
        bar_width = 40
        filled = int(bar_width * current / total) if total > 0 else 0
        bar = "█" * filled + "░" * (bar_width - filled)
        
        # Print progress line
        progress_line = f"  Progress: [{bar}] {percent:.1f}% ({current}/{total})"
        if test_id:
            progress_line += f" - {test_id}"
        
        # Clear line and print (for updating)
        print(f"\r{progress_line}", end="", flush=True)
    
    def print_test_result(
        self,
        result: TestResult,
        show_details: bool = False
    ) -> None:
        """
        Print individual test result
        
        Args:
            result: Test result to print
            show_details: Show detailed information
        """
        if not self.verbose:
            return
        
        # Status symbol and color
        if result.status == TestStatus.PASSED:
            symbol = f"{Colors.GREEN}✓{Colors.RESET}"
            self._passed_count += 1
        elif result.status == TestStatus.FAILED:
            symbol = f"{Colors.RED}✗{Colors.RESET}"
            self._failed_count += 1
        elif result.status == TestStatus.SKIPPED:
            symbol = f"{Colors.YELLOW}⊘{Colors.RESET}"
            self._skipped_count += 1
        elif result.status == TestStatus.TIMEOUT:
            symbol = f"{Colors.RED}⏱{Colors.RESET}"
            self._failed_count += 1
        else:
            symbol = f"{Colors.RED}⚠{Colors.RESET}"
            self._failed_count += 1
        
        # Test info
        test_info = f"  {symbol} {result.test_id}"
        if result.operation:
            test_info += f": {result.operation}"
        
        # Execution time
        if result.execution_time > 0:
            test_info += f" ({result.execution_time:.2f}s)"
        
        # Error message
        if result.status != TestStatus.PASSED and result.error_message:
            test_info += f" - {result.error_message}"
        
        print(f"\r{test_info}")
        
        if show_details and result.error_message:
            print(f"    {Colors.RED}Error: {result.error_message}{Colors.RESET}")
            if result.error_type:
                print(f"    {Colors.YELLOW}Type: {result.error_type}{Colors.RESET}")
    
    def print_statistics(
        self,
        passed: int,
        failed: int,
        skipped: int,
        total: int,
        avg_time: float
    ) -> None:
        """
        Print test statistics
        
        Args:
            passed: Number of passed tests
            failed: Number of failed tests
            skipped: Number of skipped tests
            total: Total number of tests
            avg_time: Average execution time
        """
        if not self.verbose:
            return
        
        print()
        print(f"{Colors.CYAN}Statistics:{Colors.RESET}")
        print(f"  {Colors.GREEN}Passed:{Colors.RESET}  {passed:4d}  ", end="")
        print(f"{Colors.RED}Failed:{Colors.RESET}  {failed:4d}  ", end="")
        print(f"{Colors.YELLOW}Skipped:{Colors.RESET}  {skipped:4d}")
        
        if total > 0:
            success_rate = (passed / (total - skipped) * 100) if (total - skipped) > 0 else 0.0
            print(f"  {Colors.BOLD}Success Rate:{Colors.RESET} {success_rate:.1f}%")
        
        if avg_time > 0:
            print(f"  {Colors.BOLD}Avg Time:{Colors.RESET} {avg_time:.2f}s")
        print()
    
    def print_summary(self, results: TestRunResults) -> None:
        """
        Print comprehensive test summary
        
        Args:
            results: Test run results
        """
        # Ensure statistics are computed
        if results.summary.total_tests == 0:
            results.compute_statistics()
        
        width = 60
        print()
        print("╔" + "═" * (width - 2) + "╗")
        print("║" + " " * ((width - 20) // 2) + "Test Summary" + " " * ((width - 20) // 2) + "║")
        print("╠" + "═" * (width - 2) + "╣")
        
        # Overall statistics
        summary = results.summary
        print(f"║ Total Tests:    {summary.total_tests:4d}" + " " * (width - 20) + "║")
        print(f"║ {Colors.GREEN}Passed:{Colors.RESET}          {summary.passed:4d}" + " " * (width - 20) + "║")
        print(f"║ {Colors.RED}Failed:{Colors.RESET}          {summary.failed:4d}" + " " * (width - 20) + "║")
        print(f"║ {Colors.YELLOW}Skipped:{Colors.RESET}        {summary.skipped:4d}" + " " * (width - 20) + "║")
        print(f"║ Success Rate:   {summary.success_rate * 100:5.1f}%" + " " * (width - 22) + "║")
        print(f"║ Total Time:     {summary.total_time:6.2f}s" + " " * (width - 20) + "║")
        print(f"║ Avg Time:       {summary.avg_execution_time:6.2f}s" + " " * (width - 20) + "║")
        print("╠" + "═" * (width - 2) + "╣")
        
        # Per-module breakdown
        if results.by_module:
            print("║ Per-Module Breakdown:" + " " * (width - 24) + "║")
            print("╠" + "═" * (width - 2) + "╣")
            for module, stats in sorted(results.by_module.items()):
                module_name = module[:25]  # Truncate long names
                passed = stats.get("passed", 0)
                failed = stats.get("failed", 0)
                total = stats.get("total", 0)
                rate = (passed / total * 100) if total > 0 else 0.0
                print(
                    f"║ {module_name:25s} "
                    f"{Colors.GREEN}{passed:3d}{Colors.RESET}/"
                    f"{Colors.RED}{failed:3d}{Colors.RESET} "
                    f"({rate:5.1f}%)" + " " * (width - 45) + "║"
                )
            print("╠" + "═" * (width - 2) + "╣")
        
        # Per-category breakdown
        if results.by_category:
            print("║ Per-Category Breakdown:" + " " * (width - 25) + "║")
            print("╠" + "═" * (width - 2) + "╣")
            for category, stats in sorted(results.by_category.items()):
                passed = stats.get("passed", 0)
                failed = stats.get("failed", 0)
                total = stats.get("total", 0)
                rate = (passed / total * 100) if total > 0 else 0.0
                print(
                    f"║ {category:20s} "
                    f"{Colors.GREEN}{passed:3d}{Colors.RESET}/"
                    f"{Colors.RED}{failed:3d}{Colors.RESET} "
                    f"({rate:5.1f}%)" + " " * (width - 40) + "║"
                )
            print("╠" + "═" * (width - 2) + "╣")
        
        # Top failures
        if results.failures:
            print("║ Top Failures:" + " " * (width - 16) + "║")
            print("╠" + "═" * (width - 2) + "╣")
            for failure in results.failures[:10]:
                test_id = failure.get("test_id", "unknown")[:30]
                error = failure.get("error", "Unknown error")[:25]
                print(f"║ {test_id:30s} {error:25s}" + " " * (width - 58) + "║")
            print("╠" + "═" * (width - 2) + "╣")
        
        print("╚" + "═" * (width - 2) + "╝")
        print()
    
    def generate_html_report(
        self,
        results: TestRunResults,
        output_path: Union[str, Path]
    ) -> Path:
        """
        Generate HTML report
        
        Args:
            results: Test run results
            output_path: Output HTML file path
            
        Returns:
            Path to generated HTML file
        """
        output_path = Path(output_path)
        
        # Ensure statistics are computed
        if results.summary.total_tests == 0:
            results.compute_statistics()
        
        # Generate HTML
        html = self._generate_html_content(results)
        
        # Write file
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(html)
        
        return output_path
    
    def _generate_html_content(self, results: TestRunResults) -> str:
        """Generate HTML content for report"""
        summary = results.summary
        
        html = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Mavaia Core Test Report - {results.test_run_id}</title>
    <style>
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, Cantarell, sans-serif;
            margin: 0;
            padding: 20px;
            background-color: #f5f5f5;
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
        h2 {{
            color: #555;
            margin-top: 30px;
            border-bottom: 2px solid #ddd;
            padding-bottom: 5px;
        }}
        .summary {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 20px;
            margin: 20px 0;
        }}
        .stat-card {{
            background: #f9f9f9;
            padding: 15px;
            border-radius: 6px;
            border-left: 4px solid #4CAF50;
        }}
        .stat-card.failed {{
            border-left-color: #f44336;
        }}
        .stat-card h3 {{
            margin: 0 0 10px 0;
            color: #666;
            font-size: 14px;
            text-transform: uppercase;
        }}
        .stat-card .value {{
            font-size: 32px;
            font-weight: bold;
            color: #333;
        }}
        table {{
            width: 100%;
            border-collapse: collapse;
            margin: 20px 0;
        }}
        th, td {{
            padding: 12px;
            text-align: left;
            border-bottom: 1px solid #ddd;
        }}
        th {{
            background-color: #4CAF50;
            color: white;
            font-weight: 600;
        }}
        tr:hover {{
            background-color: #f5f5f5;
        }}
        .status-passed {{
            color: #4CAF50;
            font-weight: bold;
        }}
        .status-failed {{
            color: #f44336;
            font-weight: bold;
        }}
        .status-skipped {{
            color: #ff9800;
            font-weight: bold;
        }}
        .progress-bar {{
            width: 100%;
            height: 30px;
            background-color: #e0e0e0;
            border-radius: 15px;
            overflow: hidden;
            margin: 10px 0;
        }}
        .progress-fill {{
            height: 100%;
            background-color: #4CAF50;
            transition: width 0.3s ease;
        }}
        .timestamp {{
            color: #999;
            font-size: 14px;
            margin-top: 20px;
        }}
    </style>
</head>
<body>
    <div class="container">
        <h1>Mavaia Core Test Report</h1>
        <div class="timestamp">
            Test Run ID: {results.test_run_id}<br>
            Timestamp: {results.timestamp}<br>
            Version: {results.version}
        </div>
        
        <h2>Executive Summary</h2>
        <div class="summary">
            <div class="stat-card">
                <h3>Total Tests</h3>
                <div class="value">{summary.total_tests}</div>
            </div>
            <div class="stat-card">
                <h3>Passed</h3>
                <div class="value" style="color: #4CAF50;">{summary.passed}</div>
            </div>
            <div class="stat-card failed">
                <h3>Failed</h3>
                <div class="value" style="color: #f44336;">{summary.failed}</div>
            </div>
            <div class="stat-card">
                <h3>Success Rate</h3>
                <div class="value">{summary.success_rate * 100:.1f}%</div>
            </div>
            <div class="stat-card">
                <h3>Total Time</h3>
                <div class="value">{summary.total_time:.2f}s</div>
            </div>
            <div class="stat-card">
                <h3>Avg Time</h3>
                <div class="value">{summary.avg_execution_time:.2f}s</div>
            </div>
        </div>
        
        <div class="progress-bar">
            <div class="progress-fill" style="width: {summary.success_rate * 100:.1f}%;"></div>
        </div>
"""
        
        # Per-module breakdown
        if results.by_module:
            html += """
        <h2>Per-Module Breakdown</h2>
        <table>
            <thead>
                <tr>
                    <th>Module</th>
                    <th>Total</th>
                    <th>Passed</th>
                    <th>Failed</th>
                    <th>Success Rate</th>
                    <th>Avg Time</th>
                </tr>
            </thead>
            <tbody>
"""
            for module, stats in sorted(results.by_module.items()):
                total = stats.get("total", 0)
                passed = stats.get("passed", 0)
                failed = stats.get("failed", 0)
                rate = (passed / total * 100) if total > 0 else 0.0
                avg_time = stats.get("avg_time", 0.0)
                html += f"""
                <tr>
                    <td>{module}</td>
                    <td>{total}</td>
                    <td class="status-passed">{passed}</td>
                    <td class="status-failed">{failed}</td>
                    <td>{rate:.1f}%</td>
                    <td>{avg_time:.2f}s</td>
                </tr>
"""
            html += """
            </tbody>
        </table>
"""
        
        # Per-category breakdown
        if results.by_category:
            html += """
        <h2>Per-Category Breakdown</h2>
        <table>
            <thead>
                <tr>
                    <th>Category</th>
                    <th>Total</th>
                    <th>Passed</th>
                    <th>Failed</th>
                    <th>Success Rate</th>
                </tr>
            </thead>
            <tbody>
"""
            for category, stats in sorted(results.by_category.items()):
                total = stats.get("total", 0)
                passed = stats.get("passed", 0)
                failed = stats.get("failed", 0)
                rate = (passed / total * 100) if total > 0 else 0.0
                html += f"""
                <tr>
                    <td>{category}</td>
                    <td>{total}</td>
                    <td class="status-passed">{passed}</td>
                    <td class="status-failed">{failed}</td>
                    <td>{rate:.1f}%</td>
                </tr>
"""
            html += """
            </tbody>
        </table>
"""
        
        # Failures
        if results.failures:
            html += """
        <h2>Failures</h2>
        <table>
            <thead>
                <tr>
                    <th>Test ID</th>
                    <th>Module</th>
                    <th>Category</th>
                    <th>Operation</th>
                    <th>Error</th>
                    <th>Time</th>
                </tr>
            </thead>
            <tbody>
"""
            for failure in results.failures:
                html += f"""
                <tr>
                    <td>{failure.get('test_id', 'N/A')}</td>
                    <td>{failure.get('module', 'N/A')}</td>
                    <td>{failure.get('category', 'N/A')}</td>
                    <td>{failure.get('operation', 'N/A')}</td>
                    <td class="status-failed">{failure.get('error', 'Unknown error')}</td>
                    <td>{failure.get('execution_time', 0):.2f}s</td>
                </tr>
"""
            html += """
            </tbody>
        </table>
"""
        
        # Performance metrics
        if results.performance:
            perf = results.performance
            html += """
        <h2>Performance Metrics</h2>
        <table>
            <thead>
                <tr>
                    <th>Metric</th>
                    <th>Value</th>
                </tr>
            </thead>
            <tbody>
"""
            html += f"""
                <tr><td>Average Execution Time</td><td>{perf.get('avg_execution_time', 0):.2f}s</td></tr>
                <tr><td>Min Execution Time</td><td>{perf.get('min_execution_time', 0):.2f}s</td></tr>
                <tr><td>Max Execution Time</td><td>{perf.get('max_execution_time', 0):.2f}s</td></tr>
                <tr><td>Median Execution Time</td><td>{perf.get('median_execution_time', 0):.2f}s</td></tr>
"""
            html += """
            </tbody>
        </table>
"""
        
        html += """
    </div>
</body>
</html>
"""
        
        return html


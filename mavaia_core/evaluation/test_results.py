"""
Test Results Management

Stores, archives, and analyzes test results.
Supports JSON storage, HTML report generation, and historical tracking.
"""

import json
from pathlib import Path
from typing import Any, Dict, List, Optional
from dataclasses import dataclass, field, asdict
from datetime import datetime
from enum import Enum
import sys


class JSONEncoder(json.JSONEncoder):
    """Custom JSON encoder that handles non-serializable objects"""
    
    def default(self, obj: Any) -> Any:
        """Handle non-serializable objects"""
        # Handle None
        if obj is None:
            return None
        
        # Handle basic types (shouldn't reach here, but just in case)
        if isinstance(obj, (str, int, float, bool)):
            return obj
        
        # Handle lists
        if isinstance(obj, list):
            return [self.default(item) for item in obj]
        
        # Handle dicts
        if isinstance(obj, dict):
            return {str(k): self.default(v) for k, v in obj.items()}
        
        # Handle objects - convert to string representation or dict
        try:
            # Try to convert to dict if it has __dict__
            if hasattr(obj, '__dict__'):
                obj_dict = {}
                for key, value in obj.__dict__.items():
                    obj_dict[str(key)] = self.default(value)
                return {
                    "__type": type(obj).__name__,
                    "__repr": repr(obj),
                    "__dict": obj_dict
                }
            else:
                # For objects without __dict__, just return string representation
                return {
                    "__type": type(obj).__name__,
                    "__repr": str(obj)
                }
        except Exception:
            # If all else fails, return string representation
            return str(obj)


class TestStatus(str, Enum):
    """Test execution status"""
    PASSED = "passed"
    FAILED = "failed"
    SKIPPED = "skipped"
    ERROR = "error"
    TIMEOUT = "timeout"


@dataclass
class TestResult:
    """Result of a single test execution"""
    
    test_id: str
    module: Optional[str] = None
    category: str = ""
    operation: Optional[str] = None
    status: TestStatus = TestStatus.PASSED
    execution_time: float = 0.0
    error_message: Optional[str] = None
    error_type: Optional[str] = None
    result_data: Optional[Dict[str, Any]] = None
    timestamp: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            "test_id": self.test_id,
            "module": self.module,
            "category": self.category,
            "operation": self.operation,
            "status": self.status.value,
            "execution_time": self.execution_time,
            "error_message": self.error_message,
            "error_type": self.error_type,
            "result_data": self._make_json_serializable(self.result_data),
            "timestamp": self.timestamp,
        }
    
    def _make_json_serializable(self, obj: Any) -> Any:
        """
        Convert object to JSON-serializable format
        
        Args:
            obj: Object to convert
            
        Returns:
            JSON-serializable representation
        """
        # Handle None
        if obj is None:
            return None
        
        # Handle basic types
        if isinstance(obj, (str, int, float, bool)):
            return obj
        
        # Handle lists
        if isinstance(obj, list):
            return [self._make_json_serializable(item) for item in obj]
        
        # Handle dicts
        if isinstance(obj, dict):
            return {str(k): self._make_json_serializable(v) for k, v in obj.items()}
        
        # Handle objects - convert to string representation or dict
        try:
            # Try to convert to dict if it has __dict__
            if hasattr(obj, '__dict__'):
                obj_dict = {}
                for key, value in obj.__dict__.items():
                    obj_dict[str(key)] = self._make_json_serializable(value)
                return {
                    "__type": type(obj).__name__,
                    "__repr": repr(obj),
                    "__dict": obj_dict
                }
            else:
                # For objects without __dict__, just return string representation
                return {
                    "__type": type(obj).__name__,
                    "__repr": str(obj)
                }
        except Exception:
            # If all else fails, return string representation
            return str(obj)


@dataclass
class TestRunSummary:
    """Summary statistics for a test run"""
    
    total_tests: int = 0
    passed: int = 0
    failed: int = 0
    skipped: int = 0
    errors: int = 0
    timeouts: int = 0
    success_rate: float = 0.0
    total_time: float = 0.0
    avg_execution_time: float = 0.0
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return asdict(self)


@dataclass
class TestRunResults:
    """Complete results from a test run"""
    
    test_run_id: str
    version: str = "1.0.0"
    timestamp: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    summary: TestRunSummary = field(default_factory=TestRunSummary)
    results: List[TestResult] = field(default_factory=list)
    by_module: Dict[str, Dict[str, Any]] = field(default_factory=dict)
    by_category: Dict[str, Dict[str, Any]] = field(default_factory=dict)
    failures: List[Dict[str, Any]] = field(default_factory=list)
    performance: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        # Use helper to make all fields JSON-serializable
        def make_serializable(obj: Any) -> Any:
            if obj is None:
                return None
            if isinstance(obj, (str, int, float, bool)):
                return obj
            if isinstance(obj, list):
                return [make_serializable(item) for item in obj]
            if isinstance(obj, dict):
                return {str(k): make_serializable(v) for k, v in obj.items()}
            try:
                if hasattr(obj, '__dict__'):
                    return {
                        "__type": type(obj).__name__,
                        "__repr": repr(obj),
                        "__dict": {str(k): make_serializable(v) for k, v in obj.__dict__.items()}
                    }
                return {"__type": type(obj).__name__, "__repr": str(obj)}
            except Exception:
                return str(obj)
        
        return {
            "test_run_id": self.test_run_id,
            "version": self.version,
            "timestamp": self.timestamp,
            "summary": self.summary.to_dict(),
            "results": [r.to_dict() for r in self.results],
            "by_module": make_serializable(self.by_module),
            "by_category": make_serializable(self.by_category),
            "failures": make_serializable(self.failures),
            "performance": make_serializable(self.performance),
        }
    
    def compute_statistics(self) -> None:
        """Compute summary statistics from results"""
        if not self.results:
            return
        
        # Count by status
        self.summary.total_tests = len(self.results)
        self.summary.passed = sum(1 for r in self.results if r.status == TestStatus.PASSED)
        self.summary.failed = sum(1 for r in self.results if r.status == TestStatus.FAILED)
        self.summary.skipped = sum(1 for r in self.results if r.status == TestStatus.SKIPPED)
        self.summary.errors = sum(1 for r in self.results if r.status == TestStatus.ERROR)
        self.summary.timeouts = sum(1 for r in self.results if r.status == TestStatus.TIMEOUT)
        
        # Calculate success rate
        executed = self.summary.total_tests - self.summary.skipped
        if executed > 0:
            self.summary.success_rate = self.summary.passed / executed
        else:
            self.summary.success_rate = 0.0
        
        # Calculate timing
        execution_times = [r.execution_time for r in self.results if r.execution_time > 0]
        if execution_times:
            self.summary.total_time = sum(execution_times)
            self.summary.avg_execution_time = self.summary.total_time / len(execution_times)
        
        # Group by module
        self.by_module = {}
        for result in self.results:
            module = result.module or "unknown"
            if module not in self.by_module:
                self.by_module[module] = {
                    "total": 0,
                    "passed": 0,
                    "failed": 0,
                    "skipped": 0,
                    "errors": 0,
                    "timeouts": 0,
                    "avg_time": 0.0,
                }
            stats = self.by_module[module]
            stats["total"] += 1
            if result.status == TestStatus.PASSED:
                stats["passed"] += 1
            elif result.status == TestStatus.FAILED:
                stats["failed"] += 1
            elif result.status == TestStatus.SKIPPED:
                stats["skipped"] += 1
            elif result.status == TestStatus.ERROR:
                stats["errors"] += 1
            elif result.status == TestStatus.TIMEOUT:
                stats["timeouts"] += 1
        
        # Calculate module averages
        for module, stats in self.by_module.items():
            module_times = [
                r.execution_time
                for r in self.results
                if r.module == module and r.execution_time > 0
            ]
            if module_times:
                stats["avg_time"] = sum(module_times) / len(module_times)
        
        # Group by category
        self.by_category = {}
        for result in self.results:
            category = result.category or "unknown"
            if category not in self.by_category:
                self.by_category[category] = {
                    "total": 0,
                    "passed": 0,
                    "failed": 0,
                    "skipped": 0,
                    "errors": 0,
                    "timeouts": 0,
                }
            stats = self.by_category[category]
            stats["total"] += 1
            if result.status == TestStatus.PASSED:
                stats["passed"] += 1
            elif result.status == TestStatus.FAILED:
                stats["failed"] += 1
            elif result.status == TestStatus.SKIPPED:
                stats["skipped"] += 1
            elif result.status == TestStatus.ERROR:
                stats["errors"] += 1
            elif result.status == TestStatus.TIMEOUT:
                stats["timeouts"] += 1
        
        # Collect failures
        self.failures = []
        for result in self.results:
            if result.status in [TestStatus.FAILED, TestStatus.ERROR, TestStatus.TIMEOUT]:
                failure = {
                    "test_id": result.test_id,
                    "module": result.module,
                    "category": result.category,
                    "operation": result.operation,
                    "status": result.status.value,
                    "error": result.error_message,
                    "error_type": result.error_type,
                    "execution_time": result.execution_time,
                }
                self.failures.append(failure)
        
        # Performance metrics
        execution_times = [r.execution_time for r in self.results if r.execution_time > 0]
        if execution_times:
            sorted_times = sorted(execution_times, reverse=True)
            self.performance = {
                "avg_execution_time": self.summary.avg_execution_time,
                "min_execution_time": min(execution_times),
                "max_execution_time": max(execution_times),
                "median_execution_time": sorted_times[len(sorted_times) // 2],
                "slowest_tests": [
                    {
                        "test_id": r.test_id,
                        "module": r.module,
                        "time": r.execution_time,
                    }
                    for r in sorted(
                        [r for r in self.results if r.execution_time > 0],
                        key=lambda x: x.execution_time,
                        reverse=True
                    )[:10]
                ],
                "fastest_tests": [
                    {
                        "test_id": r.test_id,
                        "module": r.module,
                        "time": r.execution_time,
                    }
                    for r in sorted(
                        [r for r in self.results if r.execution_time > 0],
                        key=lambda x: x.execution_time
                    )[:10]
                ],
            }


class TestResults:
    """Manages test results storage and analysis"""
    
    def __init__(self, results_dir: Optional[Union[str, Path]] = None):
        """
        Initialize test results manager
        
        Args:
            results_dir: Directory for storing results.
                        Defaults to mavaia_core/evaluation/results/
        """
        if results_dir is None:
            base_dir = Path(__file__).parent
            results_dir = base_dir / "results"
        else:
            results_dir = Path(results_dir)
        
        self.results_dir = results_dir
        self.results_dir.mkdir(parents=True, exist_ok=True)
    
    def save_results(
        self,
        results: TestRunResults,
        filename: Optional[str] = None
    ) -> Path:
        """
        Save test results to file
        
        Args:
            results: Test run results to save
            filename: Optional filename (defaults to timestamp-based)
            
        Returns:
            Path to saved results file
        """
        # Compute statistics if not already computed
        if results.summary.total_tests == 0:
            results.compute_statistics()
        
        # Generate filename
        if filename is None:
            timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
            filename = f"test_results_{timestamp}.json"
        
        file_path = self.results_dir / filename
        
        # Save JSON with custom encoder to handle non-serializable objects
        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(results.to_dict(), f, indent=2, ensure_ascii=False, cls=JSONEncoder)
        
        return file_path
    
    def archive_results(self, results: TestRunResults) -> Path:
        """
        Archive test results in timestamped directory
        
        Args:
            results: Test run results to archive
            
        Returns:
            Path to archive directory
        """
        # Create timestamped directory
        timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        archive_dir = self.results_dir / timestamp
        archive_dir.mkdir(parents=True, exist_ok=True)
        
        # Save summary
        summary_path = archive_dir / "summary.json"
        with open(summary_path, "w", encoding="utf-8") as f:
            json.dump(results.summary.to_dict(), f, indent=2, cls=JSONEncoder)
        
        # Save detailed results
        detailed_path = archive_dir / "detailed_results.json"
        with open(detailed_path, "w", encoding="utf-8") as f:
            json.dump(results.to_dict(), f, indent=2, ensure_ascii=False, cls=JSONEncoder)
        
        return archive_dir
    
    def load_results(self, file_path: Union[str, Path]) -> TestRunResults:
        """
        Load test results from file
        
        Args:
            file_path: Path to results file
            
        Returns:
            TestRunResults instance
        """
        file_path = Path(file_path)
        
        with open(file_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        
        # Reconstruct results
        results = TestRunResults(
            test_run_id=data["test_run_id"],
            version=data.get("version", "1.0.0"),
            timestamp=data.get("timestamp"),
        )
        
        # Reconstruct summary
        summary_data = data.get("summary", {})
        results.summary = TestRunSummary(**summary_data)
        
        # Reconstruct test results
        for result_data in data.get("results", []):
            result = TestResult(
                test_id=result_data["test_id"],
                module=result_data.get("module"),
                category=result_data.get("category", ""),
                operation=result_data.get("operation"),
                status=TestStatus(result_data.get("status", "passed")),
                execution_time=result_data.get("execution_time", 0.0),
                error_message=result_data.get("error_message"),
                error_type=result_data.get("error_type"),
                result_data=result_data.get("result_data"),
                timestamp=result_data.get("timestamp"),
            )
            results.results.append(result)
        
        # Restore other fields
        results.by_module = data.get("by_module", {})
        results.by_category = data.get("by_category", {})
        results.failures = data.get("failures", [])
        results.performance = data.get("performance", {})
        
        return results
    
    def list_archives(self) -> List[Path]:
        """
        List all archived test result directories
        
        Returns:
            List of archive directory paths, sorted by timestamp (newest first)
        """
        archives = []
        for item in self.results_dir.iterdir():
            if item.is_dir() and item.name.replace("_", "").replace("-", "").isdigit():
                archives.append(item)
        
        return sorted(archives, reverse=True)
    
    def export_to_csv(self, results: TestRunResults, output_path: Union[str, Path]) -> None:
        """
        Export results to CSV format
        
        Args:
            results: Test run results
            output_path: Output CSV file path
        """
        import csv
        
        output_path = Path(output_path)
        
        with open(output_path, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            
            # Header
            writer.writerow([
                "test_id",
                "module",
                "category",
                "operation",
                "status",
                "execution_time",
                "error_message",
                "error_type",
            ])
            
            # Rows
            for result in results.results:
                writer.writerow([
                    result.test_id,
                    result.module or "",
                    result.category,
                    result.operation or "",
                    result.status.value,
                    result.execution_time,
                    result.error_message or "",
                    result.error_type or "",
                ])


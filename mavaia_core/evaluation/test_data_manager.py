"""
Test Data Manager

Loads and validates test cases from JSON/YAML files.
Supports test case templates, version control, and filtering.
"""

import json
from pathlib import Path
from typing import Any, Dict, List, Optional, Union
from dataclasses import dataclass, field
from datetime import datetime
import sys

try:
    import yaml
    YAML_AVAILABLE = True
except ImportError:
    YAML_AVAILABLE = False


@dataclass
class TestCase:
    """Represents a single test case"""
    
    id: str
    category: str
    module: Optional[str] = None
    operation: Optional[str] = None
    params: Dict[str, Any] = field(default_factory=dict)
    expected: Dict[str, Any] = field(default_factory=dict)
    timeout: float = 30.0
    description: Optional[str] = None
    skip: bool = False
    tags: List[str] = field(default_factory=list)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert test case to dictionary"""
        result = {
            "id": self.id,
            "category": self.category,
            "timeout": self.timeout,
        }
        if self.module:
            result["module"] = self.module
        if self.operation:
            result["operation"] = self.operation
        if self.params:
            result["params"] = self.params
        if self.expected:
            result["expected"] = self.expected
        if self.description:
            result["description"] = self.description
        if self.skip:
            result["skip"] = True
        if self.tags:
            result["tags"] = self.tags
        return result


@dataclass
class TestSuite:
    """Represents a test suite file"""
    
    module: Optional[str] = None
    version: Optional[str] = None
    test_suite: List[TestCase] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    source_file: Optional[Path] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert test suite to dictionary"""
        result = {
            "test_suite": [tc.to_dict() for tc in self.test_suite],
        }
        if self.module:
            result["module"] = self.module
        if self.version:
            result["version"] = self.version
        if self.metadata:
            result["metadata"] = self.metadata
        return result


class TestDataManager:
    """Manages loading and validation of test data"""
    
    def __init__(self, test_data_dir: Optional[Union[str, Path]] = None):
        """
        Initialize test data manager
        
        Args:
            test_data_dir: Directory containing test data files.
                          Defaults to mavaia_core/evaluation/test_data/
        """
        if test_data_dir is None:
            # Default to evaluation/test_data directory
            base_dir = Path(__file__).parent
            test_data_dir = base_dir / "test_data"
        else:
            test_data_dir = Path(test_data_dir)
        
        self.test_data_dir = test_data_dir
        self._test_suites: Dict[str, TestSuite] = {}
        self._test_cases: List[TestCase] = []
    
    def discover_test_files(self) -> List[Path]:
        """
        Discover all test data files
        
        Returns:
            List of paths to test data files
        """
        test_files = []
        
        if not self.test_data_dir.exists():
            return test_files
        
        # Find all JSON files
        test_files.extend(self.test_data_dir.glob("**/*.json"))
        
        # Find YAML files if PyYAML is available
        if YAML_AVAILABLE:
            test_files.extend(self.test_data_dir.glob("**/*.yaml"))
            test_files.extend(self.test_data_dir.glob("**/*.yml"))
        
        return sorted(test_files)
    
    def load_test_file(self, file_path: Union[str, Path]) -> TestSuite:
        """
        Load a test suite from a file
        
        Args:
            file_path: Path to test data file
            
        Returns:
            TestSuite instance
            
        Raises:
            ValueError: If file format is invalid
            FileNotFoundError: If file doesn't exist
        """
        file_path = Path(file_path)
        
        if not file_path.exists():
            raise FileNotFoundError(f"Test file not found: {file_path}")
        
        # Load file based on extension
        if file_path.suffix in [".yaml", ".yml"]:
            if not YAML_AVAILABLE:
                raise ImportError(
                    "PyYAML is required for YAML test files. "
                    "Install with: pip install pyyaml"
                )
            with open(file_path, "r", encoding="utf-8") as f:
                data = yaml.safe_load(f)
        elif file_path.suffix == ".json":
            with open(file_path, "r", encoding="utf-8") as f:
                data = json.load(f)
        else:
            raise ValueError(f"Unsupported file format: {file_path.suffix}")
        
        # Validate and parse
        test_suite = self._parse_test_suite(data, file_path)
        return test_suite
    
    def _parse_test_suite(self, data: Dict[str, Any], source_file: Path) -> TestSuite:
        """
        Parse test suite data into TestSuite object
        
        Args:
            data: Raw test suite data
            source_file: Source file path
            
        Returns:
            TestSuite instance
        """
        suite = TestSuite(
            module=data.get("module"),
            version=data.get("version"),
            metadata=data.get("metadata", {}),
            source_file=source_file,
        )
        
        # Parse test cases
        test_cases = data.get("test_suite", [])
        if not isinstance(test_cases, list):
            raise ValueError("test_suite must be a list")
        
        for idx, test_data in enumerate(test_cases):
            try:
                test_case = self._parse_test_case(test_data, suite.module)
                suite.test_suite.append(test_case)
            except Exception as e:
                print(
                    f"Warning: Failed to parse test case {idx} in {source_file}: {e}",
                    file=sys.stderr
                )
                continue
        
        return suite
    
    def _parse_test_case(
        self,
        data: Dict[str, Any],
        default_module: Optional[str] = None
    ) -> TestCase:
        """
        Parse a single test case
        
        Args:
            data: Test case data
            default_module: Default module name if not specified
            
        Returns:
            TestCase instance
        """
        # Required fields
        if "id" not in data:
            raise ValueError("Test case missing required field: id")
        if "category" not in data:
            raise ValueError("Test case missing required field: category")
        
        timeout_value = float(data.get("timeout", 0.0))
        
        test_case = TestCase(
            id=str(data["id"]),
            category=str(data["category"]),
            module=data.get("module", default_module),
            operation=data.get("operation"),
            params=data.get("params", {}),
            expected=data.get("expected", {}),
            # timeout <= 0 means "no per-test timeout"; global runner timeout may still apply
            timeout=timeout_value,
            description=data.get("description"),
            skip=bool(data.get("skip", False)),
            tags=data.get("tags", []),
        )
        
        return test_case
    
    def load_all_test_suites(self) -> Dict[str, TestSuite]:
        """
        Load all test suites from test data directory
        
        Returns:
            Dictionary mapping module names (or file names) to TestSuite objects
        """
        test_files = self.discover_test_files()
        
        if not test_files:
            # Check if directory exists
            if not self.test_data_dir.exists():
                print(
                    f"Warning: Test data directory does not exist: {self.test_data_dir}",
                    file=sys.stderr
                )
            else:
                print(
                    f"Warning: No test files found in {self.test_data_dir}",
                    file=sys.stderr
                )
        
        suites = {}
        
        for test_file in test_files:
            try:
                suite = self.load_test_file(test_file)
                # Use module name as key, or file name if no module specified
                key = suite.module or test_file.stem
                suites[key] = suite
            except Exception as e:
                print(
                    f"Warning: Failed to load test file {test_file}: {e}",
                    file=sys.stderr
                )
                continue
        
        self._test_suites = suites
        return suites
    
    def get_test_cases(
        self,
        module: Optional[str] = None,
        category: Optional[str] = None,
        tags: Optional[List[str]] = None,
        include_skipped: bool = False,
        tag_mode: str = "all"
    ) -> List[TestCase]:
        """
        Get filtered list of test cases
        
        Args:
            module: Filter by module name
            category: Filter by category
            tags: Filter by tags
            include_skipped: Include skipped test cases
            tag_mode: How to combine tags - "all" (AND) or "any" (OR). 
                     Default: "all" (test case must have all specified tags)
            
        Returns:
            List of matching test cases
        """
        if not self._test_cases:
            # Build flat list of all test cases
            self._test_cases = []
            for suite in self._test_suites.values():
                for test_case in suite.test_suite:
                    # Set module if not set
                    if not test_case.module and suite.module:
                        test_case.module = suite.module
                    self._test_cases.append(test_case)
        
        # Filter test cases
        filtered = []
        for test_case in self._test_cases:
            # Skip filter
            if test_case.skip and not include_skipped:
                continue
            
            # Module filter
            if module and test_case.module != module:
                continue
            
            # Category filter
            if category and test_case.category != category:
                continue
            
            # Tags filter
            if tags:
                if tag_mode == "all":
                    # Test case must have ALL specified tags (AND logic)
                    if not all(tag in test_case.tags for tag in tags):
                        continue
                elif tag_mode == "any":
                    # Test case must have AT LEAST ONE specified tag (OR logic)
                    if not any(tag in test_case.tags for tag in tags):
                        continue
                else:
                    # Default to AND logic
                    if not all(tag in test_case.tags for tag in tags):
                        continue
            
            filtered.append(test_case)
        
        return filtered
    
    def validate_test_case(self, test_case: TestCase) -> List[str]:
        """
        Validate a test case structure
        
        Args:
            test_case: Test case to validate
            
        Returns:
            List of validation errors (empty if valid)
        """
        errors = []
        
        if not test_case.id:
            errors.append("Test case ID is required")
        
        if not test_case.category:
            errors.append("Test case category is required")
        
        # Allow zero timeout to mean "no per-test timeout"
        if test_case.timeout < 0:
            errors.append("Test case timeout must be non-negative")
        
        # Validate expected structure if present
        if test_case.expected:
            expected = test_case.expected
            if "validation" in expected:
                validation = expected["validation"]
                if not isinstance(validation, dict):
                    errors.append("Expected validation must be a dictionary")
                elif "type" not in validation:
                    errors.append("Validation type is required")
        
        return errors
    
    def save_test_suite(
        self,
        test_suite: TestSuite,
        file_path: Union[str, Path],
        format: str = "json"
    ) -> None:
        """
        Save a test suite to a file
        
        Args:
            test_suite: Test suite to save
            file_path: Destination file path
            format: File format ("json" or "yaml")
        """
        file_path = Path(file_path)
        data = test_suite.to_dict()
        
        if format == "json":
            with open(file_path, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
        elif format in ["yaml", "yml"]:
            if not YAML_AVAILABLE:
                raise ImportError(
                    "PyYAML is required for YAML output. "
                    "Install with: pip install pyyaml"
                )
            with open(file_path, "w", encoding="utf-8") as f:
                yaml.safe_dump(data, f, default_flow_style=False, sort_keys=False)
        else:
            raise ValueError(f"Unsupported format: {format}")


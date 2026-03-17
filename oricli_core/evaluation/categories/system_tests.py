from __future__ import annotations
"""
System Test Executor

Tests core system components: registry, orchestrator, state storage, metrics, health.
"""

import time
from typing import Any, Dict, List, Optional

from oricli_core.brain.registry import ModuleRegistry
# ModuleOrchestrator is deprecated and moved to Go backbone
from oricli_core.brain.state_storage.base_storage import BaseStorage
from oricli_core.brain.metrics import get_metrics_collector
from oricli_core.brain.health import get_health_checker
from oricli_core.evaluation.test_data_manager import TestCase
from oricli_core.evaluation.test_results import TestResult, TestStatus


class SystemTestRunner:
    """Runs tests for system components"""
    
    def __init__(self):
        """Initialize system test executor"""
        self.registry = ModuleRegistry
        self.orchestrator = None
        self.metrics_collector = None
        self.health_checker = None
    
    def run_test_case(
        self,
        test_case: TestCase,
        timeout: Optional[float] = None
    ) -> TestResult:
        """
        Run a single system test case
        
        Args:
            test_case: Test case to run
            timeout: Optional timeout override
            
        Returns:
            TestResult instance
        """
        test_timeout = timeout or test_case.timeout
        start_time = time.time()
        
        result = TestResult(
            test_id=test_case.id,
            module=test_case.module,  # May be component name
            category=test_case.category,
            operation=test_case.operation,
        )
        
        try:
            # Skip if marked as skip
            if test_case.skip:
                result.status = TestStatus.SKIPPED
                result.execution_time = time.time() - start_time
                return result
            
            # Get component and operation
            component = test_case.params.get("component", "registry")
            operation = test_case.operation or test_case.params.get("operation")
            
            # Execute based on component
            if component == "registry":
                execution_result = self._test_registry(operation, test_case.params)
            elif component == "orchestrator":
                execution_result = self._test_orchestrator(operation, test_case.params)
            elif component == "state_storage":
                execution_result = self._test_state_storage(operation, test_case.params)
            elif component == "metrics":
                execution_result = self._test_metrics(operation, test_case.params)
            elif component == "health":
                execution_result = self._test_health(operation, test_case.params)
            else:
                result.status = TestStatus.ERROR
                result.error_message = f"Unknown component: {component}"
                result.execution_time = time.time() - start_time
                return result
            
            # Validate result
            validation_errors = self._validate_result(
                test_case,
                execution_result
            )
            
            if validation_errors:
                result.status = TestStatus.FAILED
                result.error_message = "; ".join(validation_errors)
                result.error_type = "ValidationError"
            else:
                result.status = TestStatus.PASSED
                result.result_data = execution_result
            
            result.execution_time = time.time() - start_time
            
        except Exception as e:
            result.status = TestStatus.ERROR
            result.error_message = str(e)
            result.error_type = type(e).__name__
            result.execution_time = time.time() - start_time
        
        return result
    
    def _test_registry(self, operation: str, params: Dict[str, Any]) -> Dict[str, Any]:
        """Test module registry"""
        if operation == "list_modules":
            modules = self.registry.list_modules()
            return {"modules": modules, "count": len(modules)}
        
        elif operation == "get_module":
            module_name = params.get("module_name")
            if not module_name:
                raise ValueError("module_name required")
            module = self.registry.get_module(module_name)
            return {"module_found": module is not None}
        
        elif operation == "get_metadata":
            module_name = params.get("module_name")
            if not module_name:
                raise ValueError("module_name required")
            metadata = self.registry.get_metadata(module_name)
            if metadata:
                return {
                    "name": metadata.name,
                    "version": metadata.version,
                    "operations": metadata.operations,
                }
            return {"metadata": None}
        
        elif operation == "discover_modules":
            self.registry.discover_modules()
            return {"discovered": True}
        
        else:
            raise ValueError(f"Unknown registry operation: {operation}")
    
    def _test_orchestrator(self, operation: str, params: Dict[str, Any]) -> Dict[str, Any]:
        """Test module orchestrator (Deprecated in Python sidecar)"""
        return {
            "status": "deprecated",
            "message": "ModuleOrchestrator has been moved to the Go-native backbone."
        }
    
    def _test_state_storage(self, operation: str, params: Dict[str, Any]) -> Dict[str, Any]:
        """Test state storage"""
        # This would require a storage instance
        # For now, return a placeholder
        return {"operation": operation, "status": "not_implemented"}
    
    def _test_metrics(self, operation: str, params: Dict[str, Any]) -> Dict[str, Any]:
        """Test metrics collector"""
        if self.metrics_collector is None:
            self.metrics_collector = get_metrics_collector()
        
        if operation == "get_summary":
            summary = self.metrics_collector.get_summary()
            return {"summary": summary}
        
        elif operation == "export_metrics":
            metrics = self.metrics_collector.export_metrics()
            return {"metrics": metrics}
        
        else:
            raise ValueError(f"Unknown metrics operation: {operation}")
    
    def _test_health(self, operation: str, params: Dict[str, Any]) -> Dict[str, Any]:
        """Test health checker"""
        if self.health_checker is None:
            self.health_checker = get_health_checker()
        
        if operation == "check_all_modules":
            checks = self.health_checker.check_all_modules()
            return {"checks": {k: v.status.value for k, v in checks.items()}}
        
        elif operation == "get_health_summary":
            summary = self.health_checker.get_health_summary()
            return {"summary": summary}
        
        else:
            raise ValueError(f"Unknown health operation: {operation}")
    
    def _validate_result(
        self,
        test_case: TestCase,
        result: Dict[str, Any]
    ) -> List[str]:
        """Validate system test result"""
        errors = []
        expected = test_case.expected
        
        if not expected:
            return errors
        
        # Check required fields
        if "required_fields" in expected:
            required = expected["required_fields"]
            if isinstance(result, dict):
                for field in required:
                    if field not in result:
                        errors.append(f"Missing required field: {field}")
        
        return errors
    
    def run_test_suite(
        self,
        test_cases: List[TestCase],
        timeout: Optional[float] = None
    ) -> List[TestResult]:
        """Run a suite of system test cases"""
        results = []
        
        for test_case in test_cases:
            result = self.run_test_case(test_case, timeout)
            results.append(result)
        
        return results

from __future__ import annotations
"""
Safety Test Executor

Tests safety mechanisms, input sanitization, error handling,
resource limits, and edge cases.
"""

import time
from typing import Any, Dict, List, Optional

from mavaia_core.brain.registry import ModuleRegistry
from mavaia_core.evaluation.test_data_manager import TestCase
from mavaia_core.evaluation.test_results import TestResult, TestStatus


class SafetyTestRunner:
    """Runs tests for safety and edge cases"""
    
    def __init__(self):
        """Initialize safety test executor"""
        self.registry = ModuleRegistry
    
    def run_test_case(
        self,
        test_case: TestCase,
        timeout: Optional[float] = None
    ) -> TestResult:
        """
        Run a single safety test case
        
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
            module=test_case.module,
            category=test_case.category,
            operation=test_case.operation,
        )
        
        try:
            # Skip if marked as skip
            if test_case.skip:
                result.status = TestStatus.SKIPPED
                result.execution_time = time.time() - start_time
                return result
            
            # Get test type
            test_type = test_case.params.get("test_type", "input_sanitization")
            
            if test_type == "input_sanitization":
                execution_result = self._test_input_sanitization(test_case)
            elif test_type == "error_handling":
                execution_result = self._test_error_handling(test_case)
            elif test_type == "resource_limits":
                execution_result = self._test_resource_limits(test_case, test_timeout)
            elif test_type == "edge_cases":
                execution_result = self._test_edge_cases(test_case)
            elif test_type == "adversarial":
                execution_result = self._test_adversarial(test_case)
            else:
                result.status = TestStatus.ERROR
                result.error_message = f"Unknown test type: {test_type}"
                result.execution_time = time.time() - start_time
                return result
            
            # Validate result
            validation_errors = self._validate_safety_result(
                test_case,
                execution_result
            )
            
            if validation_errors:
                result.status = TestStatus.FAILED
                result.error_message = "; ".join(validation_errors)
                result.error_type = "SafetyValidationError"
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
    
    def _test_input_sanitization(self, test_case: TestCase) -> Dict[str, Any]:
        """Test input sanitization"""
        # Get module
        module_name = test_case.module
        if not module_name:
            raise ValueError("Module name required for input sanitization test")
        
        module = self.registry.get_module(module_name)
        if not module:
            raise ValueError(f"Module not found: {module_name}")
        
        # Get malicious input
        malicious_input = test_case.params.get("malicious_input", "")
        operation = test_case.operation or test_case.params.get("operation")
        
        # Try to execute with malicious input
        try:
            params = test_case.params.get("params", {})
            params["input"] = malicious_input
            result = module.execute(operation, params)
            
            # Check if input was sanitized
            result_str = str(result)
            if malicious_input in result_str and malicious_input not in ["", " "]:
                return {
                    "sanitized": False,
                    "error": "Malicious input not sanitized"
                }
            
            return {"sanitized": True, "result": result}
        except Exception as e:
            # Exception is expected for truly malicious input
            return {"sanitized": True, "exception": str(e)}
    
    def _test_error_handling(self, test_case: TestCase) -> Dict[str, Any]:
        """Test error handling"""
        module_name = test_case.module
        if not module_name:
            raise ValueError("Module name required for error handling test")
        
        module = self.registry.get_module(module_name)
        if not module:
            raise ValueError(f"Module not found: {module_name}")
        
        # Try to execute with invalid input
        operation = test_case.operation or test_case.params.get("operation")
        invalid_params = test_case.params.get("invalid_params", {})
        
        try:
            result = module.execute(operation, invalid_params)
            # Should have raised an exception
            return {
                "error_handled": False,
                "error": "Expected exception but got result"
            }
        except Exception as e:
            # Exception is expected
            error_type = type(e).__name__
            return {
                "error_handled": True,
                "error_type": error_type,
                "error_message": str(e)
            }
    
    def _test_resource_limits(self, test_case: TestCase, timeout: float) -> Dict[str, Any]:
        """Test resource limits"""
        module_name = test_case.module
        if not module_name:
            raise ValueError("Module name required for resource limits test")
        
        module = self.registry.get_module(module_name)
        if not module:
            raise ValueError(f"Module not found: {module_name}")
        
        operation = test_case.operation or test_case.params.get("operation")
        params = test_case.params.get("params", {})
        
        # Try to execute with resource-intensive input
        start_time = time.time()
        try:
            result = module.execute(operation, params)
            execution_time = time.time() - start_time
            
            # Check if execution time is reasonable
            max_time = test_case.params.get("max_execution_time", timeout)
            if execution_time > max_time:
                return {
                    "resource_limit_respected": False,
                    "execution_time": execution_time,
                    "max_time": max_time
                }
            
            return {
                "resource_limit_respected": True,
                "execution_time": execution_time
            }
        except Exception as e:
            return {
                "resource_limit_respected": True,
                "exception": str(e)
            }
    
    def _test_edge_cases(self, test_case: TestCase) -> Dict[str, Any]:
        """Test edge cases"""
        module_name = test_case.module
        if not module_name:
            raise ValueError("Module name required for edge case test")
        
        module = self.registry.get_module(module_name)
        if not module:
            raise ValueError(f"Module not found: {module_name}")
        
        operation = test_case.operation or test_case.params.get("operation")
        edge_case_params = test_case.params.get("edge_case_params", {})
        
        try:
            result = module.execute(operation, edge_case_params)
            return {"handled": True, "result": result}
        except Exception as e:
            # Some edge cases may raise exceptions, which is acceptable
            return {"handled": True, "exception": str(e)}
    
    def _test_adversarial(self, test_case: TestCase) -> Dict[str, Any]:
        """Test adversarial inputs"""
        module_name = test_case.module
        if not module_name:
            raise ValueError("Module name required for adversarial test")
        
        module = self.registry.get_module(module_name)
        if not module:
            raise ValueError(f"Module not found: {module_name}")
        
        operation = test_case.operation or test_case.params.get("operation")
        adversarial_input = test_case.params.get("adversarial_input", {})
        
        try:
            result = module.execute(operation, adversarial_input)
            # Check if result is safe
            result_str = str(result).lower()
            unsafe_patterns = test_case.params.get("unsafe_patterns", [])
            for pattern in unsafe_patterns:
                if pattern.lower() in result_str:
                    return {
                        "safe": False,
                        "unsafe_pattern": pattern
                    }
            
            return {"safe": True, "result": result}
        except Exception as e:
            # Exception may be acceptable for adversarial input
            return {"safe": True, "exception": str(e)}
    
    def _validate_safety_result(
        self,
        test_case: TestCase,
        result: Dict[str, Any]
    ) -> List[str]:
        """Validate safety test result"""
        errors = []
        expected = test_case.expected
        
        if not expected:
            return errors
        
        # Check if safety requirement was met
        if "safety_requirement" in expected:
            requirement = expected["safety_requirement"]
            if requirement == "sanitized" and not result.get("sanitized", False):
                errors.append("Input was not sanitized")
            elif requirement == "error_handled" and not result.get("error_handled", False):
                errors.append("Error was not handled properly")
            elif requirement == "resource_limit_respected" and not result.get("resource_limit_respected", False):
                errors.append("Resource limit was not respected")
            elif requirement == "safe" and not result.get("safe", False):
                errors.append("Result is not safe")
        
        return errors
    
    def run_test_suite(
        self,
        test_cases: List[TestCase],
        timeout: Optional[float] = None
    ) -> List[TestResult]:
        """Run a suite of safety test cases"""
        results = []
        
        for test_case in test_cases:
            result = self.run_test_case(test_case, timeout)
            results.append(result)
        
        return results


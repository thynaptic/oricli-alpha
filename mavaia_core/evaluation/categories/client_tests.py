from __future__ import annotations
"""
Client Test Executor

Tests Python client interface and module access patterns.
"""

import time
from typing import Any, Dict, List, Optional

from mavaia_core.client import MavaiaClient
from mavaia_core.exceptions import (
    ModuleNotFoundError,
    ModuleOperationError,
    InvalidParameterError,
)
from mavaia_core.evaluation.test_data_manager import TestCase
from mavaia_core.evaluation.test_results import TestResult, TestStatus


class ClientTestRunner:
    """Runs tests for Python client interface"""
    
    def __init__(self, modules_dir: Optional[str] = None):
        """
        Initialize client test executor
        
        Args:
            modules_dir: Optional modules directory for client
        """
        self.modules_dir = modules_dir
        self.client = None  # Lazy initialization
    
    def _get_client(self):
        """Get or create client instance (lazy initialization)"""
        if self.client is None:
            self.client = MavaiaClient(modules_dir=self.modules_dir)
        return self.client
    
    def run_test_case(
        self,
        test_case: TestCase,
        timeout: Optional[float] = None
    ) -> TestResult:
        """
        Run a single client test case
        
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
            
            # Get operation type from test case
            operation_type = test_case.params.get("operation_type", "module_operation")
            
            if operation_type == "module_operation":
                # Test module operation via client
                if not test_case.module or not test_case.operation:
                    result.status = TestStatus.ERROR
                    result.error_message = "Module and operation required for module_operation"
                    result.execution_time = time.time() - start_time
                    return result
                
                # Execute via client
                client = self._get_client()
                execution_result = self._execute_module_operation(
                    client,
                    test_case.module,
                    test_case.operation,
                    test_case.params.get("params", {}),
                    test_timeout
                )
                
            elif operation_type == "chat_completion":
                # Test chat completion
                client = self._get_client()
                execution_result = self._execute_chat_completion(
                    client,
                    test_case.params,
                    test_timeout
                )
                
            elif operation_type == "embeddings":
                # Test embeddings
                client = self._get_client()
                execution_result = self._execute_embeddings(
                    client,
                    test_case.params,
                    test_timeout
                )
                
            else:
                result.status = TestStatus.ERROR
                result.error_message = f"Unknown operation type: {operation_type}"
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
            
        except TimeoutError:
            result.status = TestStatus.TIMEOUT
            result.error_message = f"Timeout after {test_timeout}s"
            result.error_type = "TimeoutError"
            result.execution_time = time.time() - start_time
            
        except ModuleNotFoundError as e:
            result.status = TestStatus.ERROR
            result.error_message = str(e)
            result.error_type = "ModuleNotFoundError"
            result.execution_time = time.time() - start_time
            
        except InvalidParameterError as e:
            result.status = TestStatus.FAILED
            result.error_message = str(e)
            result.error_type = "InvalidParameterError"
            result.execution_time = time.time() - start_time
            
        except ModuleOperationError as e:
            result.status = TestStatus.FAILED
            result.error_message = str(e)
            result.error_type = "ModuleOperationError"
            result.execution_time = time.time() - start_time
            
        except Exception as e:
            result.status = TestStatus.ERROR
            result.error_message = str(e)
            result.error_type = type(e).__name__
            result.execution_time = time.time() - start_time
        
        return result
    
    def _execute_module_operation(
        self,
        client,
        module_name: str,
        operation: str,
        params: Dict[str, Any],
        timeout: float
    ) -> Dict[str, Any]:
        """Execute module operation via client"""
        import threading
        
        result_container = [None]
        exception_container = [None]
        
        def execute():
            try:
                result_container[0] = client.execute_module_operation(
                    module_name,
                    operation,
                    params
                )
            except Exception as e:
                exception_container[0] = e
        
        thread = threading.Thread(target=execute, daemon=True)
        thread.start()
        thread.join(timeout=timeout)
        
        if thread.is_alive():
            raise TimeoutError(f"Operation exceeded timeout of {timeout}s")
        
        if exception_container[0]:
            raise exception_container[0]
        
        return result_container[0]
    
    def _execute_chat_completion(
        self,
        client,
        params: Dict[str, Any],
        timeout: float
    ) -> Dict[str, Any]:
        """Execute chat completion via client"""
        import threading
        
        result_container = [None]
        exception_container = [None]
        
        def execute():
            try:
                result_container[0] = client.chat.completions.create(**params)
            except Exception as e:
                exception_container[0] = e
        
        thread = threading.Thread(target=execute, daemon=True)
        thread.start()
        thread.join(timeout=timeout)
        
        if thread.is_alive():
            raise TimeoutError(f"Operation exceeded timeout of {timeout}s")
        
        if exception_container[0]:
            raise exception_container[0]
        
        return result_container[0]
    
    def _execute_embeddings(
        self,
        client,
        params: Dict[str, Any],
        timeout: float
    ) -> Dict[str, Any]:
        """Execute embeddings via client"""
        import threading
        
        result_container = [None]
        exception_container = [None]
        
        def execute():
            try:
                result_container[0] = client.embeddings.create(**params)
            except Exception as e:
                exception_container[0] = e
        
        thread = threading.Thread(target=execute, daemon=True)
        thread.start()
        thread.join(timeout=timeout)
        
        if thread.is_alive():
            raise TimeoutError(f"Operation exceeded timeout of {timeout}s")
        
        if exception_container[0]:
            raise exception_container[0]
        
        return result_container[0]
    
    def _validate_result(
        self,
        test_case: TestCase,
        result: Dict[str, Any]
    ) -> List[str]:
        """Validate client test result"""
        errors = []
        expected = test_case.expected
        
        if not expected:
            return errors
        
        # Similar validation logic as module tests
        if "result_type" in expected:
            expected_type = expected["result_type"]
            if expected_type == "dict" and not isinstance(result, dict):
                errors.append(f"Expected dict, got {type(result).__name__}")
        
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
        """Run a suite of client test cases"""
        results = []
        
        for test_case in test_cases:
            result = self.run_test_case(test_case, timeout)
            results.append(result)
        
        return results


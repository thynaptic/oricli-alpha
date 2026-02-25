from __future__ import annotations
"""
Reasoning Test Executor

Tests reasoning quality for Chain-of-Thought, MCTS, and other reasoning modules.
Validates reasoning steps, complexity detection, and reasoning quality.
"""

import time
from typing import Any, Dict, List, Optional

from mavaia_core.brain.registry import ModuleRegistry
from mavaia_core.evaluation.test_data_manager import TestCase
from mavaia_core.evaluation.test_results import TestResult, TestStatus


class ReasoningTestRunner:
    """Runs tests for reasoning quality"""
    
    def __init__(self):
        """Initialize reasoning test executor"""
        self.registry = ModuleRegistry
    
    def run_test_case(
        self,
        test_case: TestCase,
        timeout: Optional[float] = None
    ) -> TestResult:
        """
        Run a single reasoning test case
        
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
            
            # Get module
            if not test_case.module:
                result.status = TestStatus.ERROR
                result.error_message = "Test case missing module name"
                result.execution_time = time.time() - start_time
                return result
            
            module = self.registry.get_module(test_case.module)
            if module is None:
                result.status = TestStatus.ERROR
                result.error_message = f"Module not found: {test_case.module}"
                result.error_type = "ModuleNotFoundError"
                result.execution_time = time.time() - start_time
                return result
            
            # Execute reasoning operation
            execution_result = self._execute_reasoning(
                module,
                test_case.operation,
                test_case.params,
                test_timeout
            )
            
            # Validate reasoning quality
            validation_errors = self._validate_reasoning_quality(
                test_case,
                execution_result
            )
            
            if validation_errors:
                result.status = TestStatus.FAILED
                result.error_message = "; ".join(validation_errors)
                result.error_type = "ReasoningQualityError"
            else:
                result.status = TestStatus.PASSED
                result.result_data = execution_result
            
            result.execution_time = time.time() - start_time
            
        except TimeoutError:
            result.status = TestStatus.TIMEOUT
            result.error_message = f"Timeout after {test_timeout}s"
            result.error_type = "TimeoutError"
            result.execution_time = time.time() - start_time
            
        except Exception as e:
            result.status = TestStatus.ERROR
            result.error_message = str(e)
            result.error_type = type(e).__name__
            result.execution_time = time.time() - start_time
        
        return result
    
    def _execute_reasoning(
        self,
        module: Any,
        operation: Optional[str],
        params: Dict[str, Any],
        timeout: float
    ) -> Dict[str, Any]:
        """Execute reasoning operation with timeout"""
        import threading
        
        result_container = [None]
        exception_container = [None]
        
        def execute():
            try:
                if operation:
                    result_container[0] = module.execute(operation, params)
                else:
                    # Default operation for reasoning modules
                    result_container[0] = module.execute("execute_cot", params)
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
    
    def _validate_reasoning_quality(
        self,
        test_case: TestCase,
        result: Dict[str, Any]
    ) -> List[str]:
        """
        Validate reasoning quality
        
        Args:
            test_case: Test case with expected reasoning quality
            result: Actual reasoning result
            
        Returns:
            List of validation errors
        """
        errors = []
        expected = test_case.expected
        
        if not expected or "validation" not in expected:
            return errors
        
        validation = expected["validation"]
        validation_type = validation.get("type")
        
        if validation_type == "reasoning_quality":
            # Check reasoning steps
            min_steps = validation.get("min_steps", 0)
            requires_deduction = validation.get("requires_deduction", False)
            
            # Extract reasoning steps from result
            reasoning_steps = []
            if isinstance(result, dict):
                if "steps" in result:
                    reasoning_steps = result["steps"]
                elif "reasoning" in result:
                    # Try to parse reasoning into steps
                    reasoning = result["reasoning"]
                    if isinstance(reasoning, list):
                        reasoning_steps = reasoning
                    elif isinstance(reasoning, str):
                        # Count step indicators
                        reasoning_steps = reasoning.split("\n")
            
            if len(reasoning_steps) < min_steps:
                errors.append(
                    f"Expected at least {min_steps} reasoning steps, "
                    f"got {len(reasoning_steps)}"
                )
            
            # Check for conclusion
            if isinstance(result, dict) and "conclusion" not in result:
                errors.append("Missing conclusion in reasoning result")
            
            # Check for logical deduction if required
            if requires_deduction:
                if isinstance(result, dict):
                    conclusion = result.get("conclusion", "")
                    reasoning_text = str(result.get("reasoning", ""))
                    if "therefore" not in reasoning_text.lower() and "thus" not in reasoning_text.lower():
                        errors.append("Reasoning should include logical deduction")
        
        elif validation_type == "complexity_detection":
            # Check complexity detection
            expected_complexity = validation.get("expected_complexity")
            if expected_complexity and isinstance(result, dict):
                actual_complexity = result.get("complexity")
                if actual_complexity != expected_complexity:
                    errors.append(
                        f"Expected complexity {expected_complexity}, "
                        f"got {actual_complexity}"
                    )
        
        return errors
    
    def run_test_suite(
        self,
        test_cases: List[TestCase],
        timeout: Optional[float] = None
    ) -> List[TestResult]:
        """Run a suite of reasoning test cases"""
        results = []
        
        for test_case in test_cases:
            result = self.run_test_case(test_case, timeout)
            results.append(result)
        
        return results


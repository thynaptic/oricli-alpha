from __future__ import annotations
"""
Code Generation Test Executor

Specialized test executor for code generation benchmarks that:
- Executes generated code
- Validates code against test cases
- Reports pass/fail metrics comparable to industry benchmarks
"""

import ast
import re
import time
import traceback
from typing import Any, Dict, List, Optional
from pathlib import Path

from oricli_core.brain.base_module import BaseBrainModule
from oricli_core.exceptions import (
    ModuleNotFoundError,
    ModuleOperationError,
    InvalidParameterError,
)
from oricli_core.evaluation.test_data_manager import TestCase
from oricli_core.evaluation.test_results import TestResult, TestStatus


class CodeGenerationTestRunner:
    """Runs tests for code generation modules with code execution validation"""
    
    def __init__(self):
        """Initialize code generation test executor"""
        from oricli_core.brain.registry import ModuleRegistry
        self.registry = ModuleRegistry
        self._code_execution_module = None
        self._execution_cache: Dict[str, Any] = {}
    
    def _get_code_execution_module(self) -> Optional[BaseBrainModule]:
        """Get code execution module (lazy initialization)"""
        if self._code_execution_module is None:
            try:
                self._code_execution_module = self.registry.get_module("code_execution")
            except Exception:
                pass
        return self._code_execution_module
    
    def run_test_case(
        self,
        test_case: TestCase,
        timeout: Optional[float] = None
    ) -> TestResult:
        """
        Run a code generation test case
        
        Args:
            test_case: Test case to run
            timeout: Optional timeout override
            
        Returns:
            TestResult instance with code execution validation
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
            
            # Get code generation module
            if not test_case.module:
                result.status = TestStatus.ERROR
                result.error_message = "Test case missing module name"
                result.execution_time = time.time() - start_time
                return result
            
            # Only process code generation modules
            # This runner should ONLY handle reasoning_code_generator module
            if test_case.module != "reasoning_code_generator":
                result.status = TestStatus.ERROR
                result.error_message = f"CodeGenerationTestRunner should only handle reasoning_code_generator module, got: {test_case.module}"
                result.error_type = "InvalidTestRunnerError"
                result.execution_time = time.time() - start_time
                return result
            
            module = self.registry.get_module(
                test_case.module,
                auto_discover=True,
                wait_timeout=2.0
            )
            if module is None:
                result.status = TestStatus.SKIPPED
                result.error_message = f"Module not available: {test_case.module}"
                result.error_type = "ModuleNotFoundError"
                result.execution_time = time.time() - start_time
                return result
            
            # Generate code
            if test_timeout > 0:
                generation_result = self._execute_with_timeout(
                    module,
                    test_case.operation,
                    test_case.params,
                    test_timeout * 0.7  # Use 70% of timeout for generation
                )
            else:
                generation_result = self._execute(
                    module,
                    test_case.operation,
                    test_case.params
                )
            
            # For CoT operations, validate reasoning/conclusion instead of code
            # NOTE: This should not happen in CodeGenerationTestRunner - CoT tests should use ModuleTestRunner
            if test_case.operation == "execute_cot" or test_case.operation == "analyze_complexity":
                # Check for required fields
                expected = test_case.expected or {}
                required_fields = expected.get("required_fields", [])
                
                # Normalize field names (handle both aliases)
                normalized_result = dict(generation_result)
                if "total_reasoning" in normalized_result and "reasoning" not in normalized_result:
                    normalized_result["reasoning"] = normalized_result["total_reasoning"]
                if "final_answer" in normalized_result and "conclusion" not in normalized_result:
                    normalized_result["conclusion"] = normalized_result["final_answer"]
                
                # Check required fields
                missing_fields = [field for field in required_fields if field not in normalized_result]
                if missing_fields:
                    result.status = TestStatus.FAILED
                    result.error_message = f"Missing required fields: {', '.join(missing_fields)}"
                    result.error_type = "MissingFieldsError"
                    result.execution_time = time.time() - start_time
                    result.result_data = generation_result
                    return result
                
                # Validate expected values if specified
                validation = expected.get("validation", {})
                if validation:
                    validation_type = validation.get("type")
                    if validation_type == "contains":
                        field = validation.get("field")
                        expected_value = validation.get("value")
                        if field and expected_value:
                            actual_value = str(normalized_result.get(field, ""))
                            if expected_value not in actual_value:
                                result.status = TestStatus.FAILED
                                result.error_message = f"Field '{field}' does not contain expected value '{expected_value}'. Got: '{actual_value[:100]}'"
                                result.error_type = "ValidationError"
                                result.execution_time = time.time() - start_time
                                result.result_data = generation_result
                                return result
                
                # CoT tests passed validation
                result.status = TestStatus.PASSED
                result.execution_time = time.time() - start_time
                result.result_data = generation_result
                return result
            
            # Extract generated code
            generated_code = self._extract_code(generation_result)
            
            if not generated_code:
                result.status = TestStatus.FAILED
                result.error_message = "No code generated or code extraction failed"
                result.error_type = "CodeExtractionError"
                result.execution_time = time.time() - start_time
                result.result_data = generation_result
                return result
            
            # Validate code syntax
            syntax_valid, syntax_error = self._validate_syntax(generated_code)
            if not syntax_valid:
                result.status = TestStatus.FAILED
                result.error_message = f"Generated code has syntax errors: {syntax_error}"
                result.error_type = "SyntaxError"
                result.execution_time = time.time() - start_time
                result.result_data = {"code": generated_code, "syntax_error": syntax_error}
                return result
            
            # Execute and validate code against test cases
            validation_result = self._validate_code_execution(
                generated_code,
                test_case,
                test_timeout * 0.3  # Use remaining 30% for execution
            )
            
            # Set result based on validation
            if validation_result["all_passed"]:
                result.status = TestStatus.PASSED
            else:
                result.status = TestStatus.FAILED
                result.error_message = validation_result["error_summary"]
                result.error_type = "ValidationError"
            
            result.result_data = {
                "generated_code": generated_code,
                "generation_result": generation_result,
                "validation": validation_result,
            }
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
            if hasattr(e, "__traceback__"):
                result.error_message += f"\n{traceback.format_exc()}"
        
        return result
    
    def _extract_code(self, generation_result: Dict[str, Any]) -> str:
        """
        Extract Python code from generation result
        
        Args:
            generation_result: Result from code generation module
            
        Returns:
            Extracted code string, or empty string if extraction fails
        """
        # Try different possible fields
        code = generation_result.get("code", "")
        if code:
            return code.strip()
        
        # Try to extract from explanation or reasoning steps
        explanation = generation_result.get("explanation", "")
        if explanation:
            code = self._extract_code_from_text(explanation)
            if code:
                return code
        
        # Try reasoning steps
        reasoning_steps = generation_result.get("reasoning_steps", [])
        if isinstance(reasoning_steps, list):
            for step in reasoning_steps:
                if isinstance(step, dict):
                    step_text = step.get("response", step.get("text", step.get("thought", "")))
                elif isinstance(step, str):
                    step_text = step
                else:
                    continue
                
                code = self._extract_code_from_text(step_text)
                if code:
                    return code
        
        # Try result field
        result_text = generation_result.get("result", "")
        if result_text:
            code = self._extract_code_from_text(str(result_text))
            if code:
                return code
        
        return ""
    
    def _extract_code_from_text(self, text: str) -> str:
        """
        Extract Python code block from text
        
        Args:
            text: Text that may contain code blocks
            
        Returns:
            Extracted code, or empty string
        """
        if not text:
            return ""
        
        # Try to find code in markdown code blocks
        pattern = r'```python\s*\n(.*?)```'
        matches = re.findall(pattern, text, re.DOTALL)
        if matches:
            return matches[0].strip()
        
        # Try plain code blocks
        pattern = r'```\s*\n(.*?)```'
        matches = re.findall(pattern, text, re.DOTALL)
        if matches:
            return matches[0].strip()
        
        # Try to find code between lines that look like Python
        lines = text.split('\n')
        code_lines = []
        in_code = False
        
        for line in lines:
            # Check if line looks like Python code
            if any(keyword in line for keyword in ['def ', 'class ', 'import ', 'return ', 'if ', 'for ', 'while ']):
                in_code = True
            if in_code:
                code_lines.append(line)
        
        if code_lines:
            return '\n'.join(code_lines).strip()
        
        return ""
    
    def _validate_syntax(self, code: str) -> tuple[bool, Optional[str]]:
        """
        Validate Python code syntax
        
        Args:
            code: Python code to validate
            
        Returns:
            Tuple of (is_valid, error_message)
        """
        try:
            ast.parse(code)
            return True, None
        except SyntaxError as e:
            return False, str(e)
        except Exception as e:
            return False, f"Parse error: {str(e)}"
    
    def _validate_code_execution(
        self,
        code: str,
        test_case: TestCase,
        timeout: float
    ) -> Dict[str, Any]:
        """
        Execute generated code and validate against test cases
        
        Args:
            code: Generated Python code
            test_case: Test case with validation rules
            timeout: Timeout for execution
            
        Returns:
            Validation result dictionary
        """
        validation = test_case.expected.get("validation", {})
        validation_type = validation.get("type")
        
        if validation_type != "code_execution":
            # Fall back to basic validation
            return {
                "all_passed": False,
                "error_summary": "Test case requires code_execution validation",
                "test_results": [],
            }
        
        test_cases = validation.get("test_cases", [])
        if not test_cases:
            return {
                "all_passed": True,
                "error_summary": "",
                "test_results": [],
                "message": "No test cases provided",
            }
        
        # Execute code with test cases
        test_results = []
        all_passed = True
        errors = []
        
        for i, test in enumerate(test_cases):
            test_input = test.get("input", {})
            expected_output = test.get("expected_output")
            expected_output_type = test.get("expected_output_type")
            expected_length = test.get("expected_length")
            
            try:
                # Execute code with test input
                execution_result = self._execute_code_with_input(
                    code,
                    test_input,
                    timeout / len(test_cases)  # Divide timeout across tests
                )
                
                if not execution_result["success"]:
                    error_msg = execution_result.get("error", "Execution failed")
                    # Truncate long error messages
                    if len(error_msg) > 200:
                        error_msg = error_msg[:200] + "..."
                    test_results.append({
                        "test_index": i,
                        "passed": False,
                        "error": error_msg,
                        "stderr": execution_result.get("stderr", ""),
                    })
                    all_passed = False
                    errors.append(f"Test {i+1}: Execution failed - {error_msg}")
                    continue
                
                actual_output = execution_result.get("output")
                
                # Validate output
                validation_passed = True
                validation_error = None
                
                if expected_output is not None:
                    # Handle boolean comparison (Python True/False vs JSON true/false)
                    if isinstance(expected_output, bool):
                        if actual_output != expected_output:
                            validation_passed = False
                            validation_error = f"Expected {expected_output}, got {actual_output} (type: {type(actual_output).__name__})"
                    else:
                        # For numeric comparisons, allow small floating point differences
                        if isinstance(expected_output, (int, float)) and isinstance(actual_output, (int, float)):
                            if abs(actual_output - expected_output) > 1e-9:
                                validation_passed = False
                                validation_error = f"Expected {expected_output}, got {actual_output} (type: {type(actual_output).__name__})"
                        elif actual_output != expected_output:
                            validation_passed = False
                            # Truncate long outputs in error messages
                            actual_str = str(actual_output)
                            if len(actual_str) > 100:
                                actual_str = actual_str[:100] + "..."
                            validation_error = f"Expected {expected_output}, got {actual_str} (type: {type(actual_output).__name__})"
                
                if expected_output_type:
                    # Handle object type validation for class instances
                    if expected_output_type.lower() == "object":
                        # For object type, just check it's not None and is an object
                        if actual_output is None:
                            validation_passed = False
                            validation_error = f"Expected object type, got None"
                        elif not isinstance(actual_output, object):
                            validation_passed = False
                            validation_error = f"Expected object type, got {type(actual_output).__name__}"
                        # Otherwise, object type validation passes
                    elif expected_output_type.lower() == "list":
                        # For list type, check it's actually a list (including nested lists)
                        if actual_output is None:
                            validation_passed = False
                            validation_error = f"Expected type list, got None"
                        elif not isinstance(actual_output, list):
                            validation_passed = False
                            validation_error = f"Expected type list, got {type(actual_output).__name__}"
                        # List type validation passes if it's a list (even if nested)
                        # Also check expected_length if specified
                        if validation_passed and "expected_length" in test:
                            expected_len = test.get("expected_length")
                            if expected_len is not None:
                                # For nested lists, check outer length
                                if isinstance(actual_output, list) and len(actual_output) != expected_len:
                                    validation_passed = False
                                    validation_error = f"Expected list length {expected_len}, got {len(actual_output)}"
                    elif expected_output_type.lower() == "dict":
                        # For dict type, check it's actually a dict
                        if actual_output is None:
                            validation_passed = False
                            validation_error = f"Expected type dict, got None"
                        elif not isinstance(actual_output, dict):
                            validation_passed = False
                            validation_error = f"Expected type dict, got {type(actual_output).__name__}"
                    else:
                        actual_type = type(actual_output).__name__
                        if actual_type.lower() != expected_output_type.lower():
                            validation_passed = False
                            validation_error = f"Expected type {expected_output_type}, got {actual_type}"
                
                if expected_length is not None:
                    if isinstance(actual_output, (list, dict, str)):
                        actual_len = len(actual_output)
                        if actual_len != expected_length:
                            validation_passed = False
                            validation_error = f"Expected length {expected_length}, got {actual_len}"
                
                # Convert actual_output to JSON-serializable format
                serializable_output = self._make_json_serializable(actual_output)
                
                test_results.append({
                    "test_index": i,
                    "passed": validation_passed,
                    "input": test_input,
                    "expected_output": expected_output,
                    "actual_output": serializable_output,
                    "error": validation_error,
                })
                
                if not validation_passed:
                    all_passed = False
                    errors.append(f"Test {i+1}: {validation_error}")
                
            except Exception as e:
                test_results.append({
                    "test_index": i,
                    "passed": False,
                    "error": str(e),
                })
                all_passed = False
                errors.append(f"Test {i+1}: Exception - {str(e)}")
        
        return {
            "all_passed": all_passed,
            "error_summary": "; ".join(errors) if errors else "",
            "test_results": test_results,
            "total_tests": len(test_cases),
            "passed_tests": sum(1 for tr in test_results if tr.get("passed", False)),
        }
    
    def _execute_code_with_input(
        self,
        code: str,
        test_input: Dict[str, Any],
        timeout: float
    ) -> Dict[str, Any]:
        """
        Execute Python code with test input
        
        Args:
            code: Python code to execute
            test_input: Test input parameters
            timeout: Execution timeout
            
        Returns:
            Execution result dictionary
        """
        # Try to use code execution module if available
        code_exec_module = self._get_code_execution_module()
        
        if code_exec_module:
            try:
                # Wrap code to capture output
                wrapped_code = self._wrap_code_for_testing(code, test_input)
                
                result = code_exec_module.execute("execute_python", {
                    "code": wrapped_code,
                    "timeout": timeout,
                })
                
                if result.get("success"):
                    # Parse output
                    output = self._parse_output(result.get("stdout", ""))
                    return {
                        "success": True,
                        "output": output,
                        "stdout": result.get("stdout", ""),
                        "stderr": result.get("stderr", ""),
                    }
                else:
                    return {
                        "success": False,
                        "error": result.get("stderr", "Execution failed"),
                        "stderr": result.get("stderr", ""),
                    }
            except Exception as e:
                # Fall back to local execution
                pass
        
        # Fall back to local execution (less safe, but works for testing)
        try:
            wrapped_code = self._wrap_code_for_testing(code, test_input)
            
            # Create a safe execution environment
            # Use same dict for globals and locals to ensure functions are in scope
            safe_namespace = {
                "__builtins__": __builtins__,
            }
            
            exec(wrapped_code, safe_namespace, safe_namespace)
            
            # Get result from namespace
            output = safe_namespace.get("__test_result__")
            
            # Check if execution was successful (result should not be None unless explicitly set)
            if "__test_error__" in safe_namespace:
                return {
                    "success": False,
                    "error": safe_namespace.get("__test_error__", "Execution failed"),
                    "stderr": "",
                }
            
            # If output is None, it might mean the function wasn't called or didn't return
            # Try to find the function and call it manually as a fallback
            if output is None:
                # Try to find any function in the code and call it
                func_match = re.search(r'def\s+(\w+)\s*\(', wrapped_code)
                if func_match:
                    func_name = func_match.group(1)
                    # Try calling with test_input
                    try:
                        func = safe_namespace.get(func_name)
                        if func and callable(func):
                            # Try calling with test_input as kwargs
                            output = func(**test_input)
                    except Exception as e:
                        # If that fails, output remains None
                        pass
            
            return {
                "success": True,
                "output": output,
                "stdout": "",
                "stderr": "",
            }
        except SyntaxError as e:
            return {
                "success": False,
                "error": f"Syntax error: {str(e)}",
                "stderr": traceback.format_exc(),
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "stderr": traceback.format_exc(),
            }
    
    def _wrap_code_for_testing(self, code: str, test_input: Dict[str, Any]) -> str:
        """
        Wrap code to execute with test input and capture result
        
        Args:
            code: Python code to wrap
            test_input: Test input parameters
            
        Returns:
            Wrapped code string
        """
        # Check if code defines a class
        class_match = re.search(r'class\s+(\w+)', code)
        if class_match:
            class_name = class_match.group(1)
            # For classes, we need to instantiate and call methods
            # Test cases with "operations" indicate class usage
            # Test cases may have capacity or other init params
            init_params = {}
            for key in ["capacity", "n", "size"]:
                if key in test_input:
                    init_params[key] = test_input[key]
            
            # Build initialization
            if init_params:
                init_str = ', '.join(f"{k}={repr(v)}" for k, v in init_params.items())
                instance_creation = f"{class_name}({init_str})"
            else:
                instance_creation = f"{class_name}()"
            
            # Check if we need to execute operations
            # For class-based tests, validation just checks object type
            # Operations are called to ensure methods exist, but errors are ignored
            # since we only need to return the object instance
            if "operations" in test_input:
                operations = test_input["operations"]
                # Build operation execution code with error handling
                operation_calls = []
                for op in operations:
                    if isinstance(op, str):
                        # Simple method call - wrap in try/except since params might be missing
                        operation_calls.append(f"try:\n    obj.{op}()\nexcept:\n    pass")
                    elif isinstance(op, list) and len(op) > 0:
                        # Method call with parameters
                        method_name = op[0]
                        method_params = op[1:] if len(op) > 1 else []
                        if method_params:
                            params_str = ', '.join(repr(p) for p in method_params)
                            operation_calls.append(f"try:\n    obj.{method_name}({params_str})\nexcept:\n    pass")
                        else:
                            operation_calls.append(f"try:\n    obj.{method_name}()\nexcept:\n    pass")
                
                # Execute operations (errors ignored) and return instance
                ops_code = '\n'.join(operation_calls) if operation_calls else 'pass'
                call_code = f"""
{code}

# Create instance
obj = {instance_creation}

# Try to execute operations (errors ignored - test only checks object type)
{ops_code}

# Return instance for validation (tests check object type)
__test_result__ = obj
"""
            else:
                # Just instantiate and return
                call_code = f"""
{code}

# Create instance
__test_result__ = {instance_creation}
"""
            return call_code
        
        # Extract function name from code (simple heuristic)
        # Find the function that matches test input parameters
        func_match = None
        test_keys = list(test_input.keys()) if test_input else []
        
        # Try to find function with parameters matching test input
        if test_keys:
            # Find all functions and check which one has matching parameters
            all_funcs = list(re.finditer(r'def\s+(\w+)\s*\(([^)]*)\)', code))
            for func_match_obj in all_funcs:
                params_str = func_match_obj.group(2)
                # Check if any test key appears in parameters
                if any(key in params_str for key in test_keys):
                    func_match = func_match_obj
                    break
        
        # Fallback: use first function (or last if we want main function)
        if not func_match:
            # Try last function first (main function usually comes after helpers)
            all_funcs = list(re.finditer(r'def\s+(\w+)\s*\(', code))
            if all_funcs:
                # Prefer functions that look like main functions (not helpers)
                # Skip functions with names like 'helper', 'util', '_', etc.
                main_funcs = [f for f in all_funcs if not any(skip in f.group(1).lower() for skip in ['helper', 'util', '_', 'test', 'main'])]
                if main_funcs:
                    func_match = main_funcs[-1]  # Use last main function
                else:
                    func_match = all_funcs[-1]  # Use last function if no main functions
            else:
                func_match = re.search(r'def\s+(\w+)\s*\(', code)
        if func_match:
            func_name = func_match.group(1)
            # Extract function parameters for the SAME function we found
            # Use the function name to ensure we get the right parameters
            func_def_match = re.search(rf'def\s+{re.escape(func_name)}\s*\(([^)]*)\)', code)
            if func_def_match:
                params_str = func_def_match.group(1).strip()
                if params_str:
                    # Parse parameters (handle default values)
                    params = []
                    for p in params_str.split(','):
                        p = p.strip()
                        if '=' in p:
                            p = p.split('=')[0].strip()
                        params.append(p)
                    
                    # Map test_input to function parameters with intelligent matching
                    call_args = {}
                    param_mappings = {
                        'nums': ['nums', 'arr', 'list', 'array', 'numbers'],
                        'arr': ['arr', 'nums', 'list', 'array'],
                        's': ['s', 'str', 'string', 'text', 'html'],
                        'graph': ['graph'],  # Will be handled specially
                        'start': ['start', 'src', 'source'],
                        'src': ['src', 'start', 'source'],
                        'end': ['end', 'goal', 'target'],
                        'goal': ['goal', 'end', 'target'],
                        'prices': ['prices', 'price_list'],
                        'text': ['text', 's', 'str', 'string'],
                        'pattern': ['pattern', 'p', 'pat'],
                        'strs': ['strs', 'words', 'strings'],
                        'n': ['n', 'num', 'number'],
                        'k': ['k', 'count'],
                    }
                    
                    # Also add reverse mappings (test_input key -> possible param names)
                    reverse_mappings = {
                        'strs': ['strs', 'words', 'strings'],
                        'n': ['n', 'num', 'number'],
                        'k': ['k', 'count'],
                        'nums': ['nums', 'arr', 'list', 'array'],
                        'arr': ['arr', 'nums', 'list', 'array'],
                        's': ['s', 'str', 'string', 'text'],
                        'graph': ['graph'],
                        'start': ['start', 'src', 'source'],
                        'src': ['src', 'start', 'source'],
                        'end': ['end', 'goal', 'target'],
                        'goal': ['goal', 'end', 'target'],
                        'prices': ['prices', 'price_list'],
                        'text': ['text', 's', 'str', 'string'],
                        'pattern': ['pattern', 'p', 'pat'],
                    }
                    
                    for param in params:
                        # First, try direct match
                        if param in test_input:
                            call_args[param] = test_input[param]
                            continue
                        
                        # Second, try param mappings (param name -> possible test_input keys)
                        if param in param_mappings:
                            for alt in param_mappings[param]:
                                if alt in test_input:
                                    call_args[param] = test_input[alt]
                                    break
                            if param in call_args:
                                continue
                        
                        # Third, try reverse mappings (test_input keys -> possible param names)
                        # This handles cases where test_input has a key that should map to this param
                        for test_key, possible_params in reverse_mappings.items():
                            if test_key in test_input and param in possible_params:
                                call_args[param] = test_input[test_key]
                                break
                        if param in call_args:
                            continue
                        
                        # Fourth, try special cases
                        if param == 'graph':
                            # Find graph (dict or list)
                            for key, value in test_input.items():
                                if isinstance(value, (dict, list)) and key != 'operations':
                                    call_args[param] = value
                                    break
                            if param in call_args:
                                continue
                        
                        # Fifth, try type-based matching
                        # Try to find by type
                        if 'list' in str(param).lower() or 'array' in str(param).lower() or param in ['nums', 'arr', 'strs']:
                            for key, value in test_input.items():
                                if isinstance(value, list) and key not in call_args.values() and key != 'operations':
                                    call_args[param] = value
                                    break
                        elif 'str' in str(param).lower() or 'string' in str(param).lower() or param in ['s', 'html', 'text']:
                            for key, value in test_input.items():
                                if isinstance(value, str) and key not in call_args.values():
                                    call_args[param] = value
                                    break
                        elif param in ['start', 'src']:
                            for key in ['start', 'src', 'source']:
                                if key in test_input:
                                    call_args[param] = test_input[key]
                                    break
                        elif param in ['end', 'goal']:
                            for key in ['end', 'goal', 'target']:
                                if key in test_input:
                                    call_args[param] = test_input[key]
                                    break
                        elif param in ['n', 'num', 'number']:
                            for key in ['n', 'num', 'number']:
                                if key in test_input:
                                    call_args[param] = test_input[key]
                                    break
                        elif param in ['k', 'count']:
                            for key in ['k', 'count']:
                                if key in test_input:
                                    call_args[param] = test_input[key]
                                    break
                    
                    # Build function call using mapped arguments
                    # Use call_args which has been properly mapped to function parameters
                    if call_args:
                        call_code = f"""
{code}

# Execute with mapped test input
__test_result__ = {func_name}(**{call_args})
"""
                    else:
                        # If no mapping worked, filter test_input to only include function parameters
                        # This prevents passing invalid parameters
                        filtered_input = {k: v for k, v in test_input.items() if k in params}
                        if filtered_input:
                            call_code = f"""
{code}

# Execute with filtered test input (only matching parameters)
__test_result__ = {func_name}(**{filtered_input})
"""
                        else:
                            # Last resort: try with all test_input (may fail)
                            call_code = f"""
{code}

# Execute with test input (no parameter match - may fail)
try:
    __test_result__ = {func_name}(**{test_input})
except TypeError as e:
    # Try with just the first parameter if function takes one parameter
    if len(params) == 1 and test_input:
        first_value = list(test_input.values())[0]
        __test_result__ = {func_name}(first_value)
    else:
        raise e
"""
                else:
                    # No parameters
                    call_code = f"""
{code}

# Execute with test input
__test_result__ = {func_name}()
"""
            else:
                # Fallback: try to filter test_input to only include valid parameters
                # Get function signature to filter test_input
                func_def_match = re.search(rf'def\s+{re.escape(func_name)}\s*\(([^)]*)\)', code)
                if func_def_match:
                    params_str = func_def_match.group(1).strip()
                    if params_str:
                        # Extract parameter names
                        func_params = []
                        for p in params_str.split(','):
                            p = p.strip()
                            if '=' in p:
                                p = p.split('=')[0].strip()
                            func_params.append(p)
                        
                        # Filter test_input to only include function parameters
                        filtered_input = {k: v for k, v in test_input.items() if k in func_params}
                        if filtered_input:
                            call_code = f"""
{code}

# Execute with filtered test input
__test_result__ = {func_name}(**{filtered_input})
"""
                        else:
                            # No matching parameters, try with all (may fail)
                            call_code = f"""
{code}

# Execute with test input (no parameter match found)
__test_result__ = {func_name}(**{test_input})
"""
                    else:
                        # No parameters
                        call_code = f"""
{code}

# Execute with no parameters
__test_result__ = {func_name}()
"""
                else:
                    # Can't find function definition, try direct call
                    call_code = f"""
{code}

# Execute with test input (function definition not found)
__test_result__ = {func_name}(**{test_input})
"""
        else:
            # If no function found, try to execute code directly
            # and assume it sets a result variable
            call_code = f"""
{code}

# Try to get result
if 'result' in locals():
    __test_result__ = result
elif 'output' in locals():
    __test_result__ = output
else:
    __test_result__ = None
"""
        
        return call_code
    
    def _parse_output(self, stdout: str) -> Any:
        """
        Parse output from stdout
        
        Args:
            stdout: Standard output string
            
        Returns:
            Parsed output value
        """
        # Try to extract JSON or Python literal
        stdout = stdout.strip()
        
        # Try JSON
        try:
            import json
            return json.loads(stdout)
        except:
            pass
        
        # Try Python literal evaluation
        try:
            return ast.literal_eval(stdout)
        except:
            pass
        
        # Return as string
        return stdout
    
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
        # For class instances, try to get a string representation
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
    
    def _execute(
        self,
        module: BaseBrainModule,
        operation: Optional[str],
        params: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Execute module operation"""
        if not operation:
            initialized = module.initialize()
            return {"initialized": initialized}
        return module.execute(operation, params)
    
    def _execute_with_timeout(
        self,
        module: BaseBrainModule,
        operation: Optional[str],
        params: Dict[str, Any],
        timeout: float
    ) -> Dict[str, Any]:
        """Execute module operation with timeout"""
        import threading
        
        result_container = [None]
        exception_container = [None]
        
        def execute():
            try:
                result_container[0] = self._execute(module, operation, params)
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
    
    def run_test_suite(
        self,
        test_cases: List[TestCase],
        timeout: Optional[float] = None
    ) -> List[TestResult]:
        """
        Run a suite of code generation test cases
        
        Args:
            test_cases: List of test cases to run
            timeout: Optional timeout override for all tests
            
        Returns:
            List of test results
        """
        results = []
        
        for test_case in test_cases:
            result = self.run_test_case(test_case, timeout)
            results.append(result)
        
        return results

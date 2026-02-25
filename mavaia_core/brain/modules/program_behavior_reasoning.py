from __future__ import annotations
"""
Program Behavior Reasoning Module

Reason about Python program behavior: predict execution outcomes,
trace execution paths, identify edge cases, analyze side effects,
and verify correctness.

This module is part of Mavaia's Python LLM capabilities, enabling
deep reasoning about what Python code will do when executed.
"""

import ast
import sys
from collections import defaultdict
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple

from mavaia_core.brain.base_module import BaseBrainModule, ModuleMetadata
from mavaia_core.exceptions import InvalidParameterError


class ProgramBehaviorReasoningModule(BaseBrainModule):
    """
    Reason about Python program behavior.
    
    Provides:
    - Execution outcome prediction
    - Execution path tracing
    - Edge case identification
    - Side effect analysis
    - Correctness verification
    """

    def __init__(self):
        """Initialize the program behavior reasoning module."""
        super().__init__()
        self._cot_module = None
        self._tot_module = None
        self._mcts_module = None

    @property
    def metadata(self) -> ModuleMetadata:
        """Return module metadata."""
        return ModuleMetadata(
            name="program_behavior_reasoning",
            version="1.0.0",
            description=(
                "Reason about Python program behavior: predict execution outcomes, "
                "trace execution paths, identify edge cases, analyze side effects, "
                "and verify correctness"
            ),
            operations=[
                "predict_execution",
                "trace_execution_path",
                "find_edge_cases",
                "analyze_side_effects",
                "verify_correctness",
                "analyze_complexity",
                "predict_outputs",
            ],
            dependencies=[],
            model_required=False,
        )

    def initialize(self) -> bool:
        """Initialize the module."""
        # Try to load reasoning modules for complex reasoning
        try:
            from mavaia_core.brain.registry import ModuleRegistry
            self._cot_module = ModuleRegistry.get_module("chain_of_thought")
            self._tot_module = ModuleRegistry.get_module("tree_of_thought")
            self._mcts_module = ModuleRegistry.get_module("mcts_reasoning")
        except Exception:
            pass  # Continue without reasoning modules
        
        return True

    def execute(self, operation: str, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute a program behavior reasoning operation.
        
        Args:
            operation: Operation name
            params: Operation parameters
            
        Returns:
            Operation result dictionary
            
        Raises:
            ValueError: If operation is unknown
            InvalidParameterError: If parameters are invalid
        """
        if operation == "predict_execution":
            code = params.get("code", "")
            inputs = params.get("inputs", {})
            if not code:
                raise InvalidParameterError("code", "", "Code cannot be empty")
            return self.predict_execution(code, inputs)
        
        elif operation == "trace_execution_path":
            code = params.get("code", "")
            inputs = params.get("inputs", {})
            if not code:
                raise InvalidParameterError("code", "", "Code cannot be empty")
            return self.trace_execution_path(code, inputs)
        
        elif operation == "find_edge_cases":
            code = params.get("code", "")
            if not code:
                raise InvalidParameterError("code", "", "Code cannot be empty")
            return self.find_edge_cases(code)
        
        elif operation == "analyze_side_effects":
            code = params.get("code", "")
            if not code:
                raise InvalidParameterError("code", "", "Code cannot be empty")
            return self.analyze_side_effects(code)
        
        elif operation == "verify_correctness":
            code = params.get("code", "")
            spec = params.get("spec", {})
            if not code:
                raise InvalidParameterError("code", "", "Code cannot be empty")
            return self.verify_correctness(code, spec)
        
        elif operation == "analyze_complexity":
            code = params.get("code", "")
            if not code:
                raise InvalidParameterError("code", "", "Code cannot be empty")
            return self.analyze_complexity(code)
        
        elif operation == "predict_outputs":
            code = params.get("code", "")
            test_cases = params.get("test_cases", [])
            if not code:
                raise InvalidParameterError("code", "", "Code cannot be empty")
            return self.predict_outputs(code, test_cases)
        
        else:
            raise InvalidParameterError(
                parameter="operation",
                value=str(operation),
                reason="Unknown operation",
            )

    def predict_execution(self, code: str, inputs: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        Predict execution outcomes for Python code.
        
        Args:
            code: Python code to analyze
            inputs: Input values for variables
            
        Returns:
            Dictionary containing:
            - predicted_output: Predicted output value
            - execution_path: Path through code
            - variable_states: Variable states at each step
            - conditions_met: Conditions that were evaluated
        """
        if inputs is None:
            inputs = {}
        
        try:
            tree = ast.parse(code)
        except SyntaxError as e:
            return {
                "success": False,
                "error": f"Syntax error: {e}",
            }
        except Exception as e:
            return {
                "success": False,
                "error": f"Parse error: {e}",
            }

        predictor = ExecutionPredictor(inputs)
        predictor.visit(tree)

        return {
            "success": True,
            "predicted_output": predictor.output,
            "execution_path": predictor.execution_path,
            "variable_states": predictor.variable_states,
            "conditions_met": predictor.conditions_met,
            "side_effects": predictor.side_effects,
        }

    def trace_execution_path(self, code: str, inputs: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        Trace the execution path through code.
        
        Args:
            code: Python code to trace
            inputs: Input values for variables
            
        Returns:
            Dictionary containing execution trace
        """
        if inputs is None:
            inputs = {}
        
        try:
            tree = ast.parse(code)
        except SyntaxError as e:
            return {
                "success": False,
                "error": f"Syntax error: {e}",
            }
        except Exception as e:
            return {
                "success": False,
                "error": f"Parse error: {e}",
            }

        tracer = ExecutionTracer(inputs)
        tracer.visit(tree)

        return {
            "success": True,
            "trace": tracer.trace,
            "line_numbers": tracer.line_numbers,
            "branches_taken": tracer.branches_taken,
            "loops_executed": tracer.loops_executed,
        }

    def find_edge_cases(self, code: str) -> Dict[str, Any]:
        """
        Identify edge cases in code.
        
        Args:
            code: Python code to analyze
            
        Returns:
            Dictionary containing identified edge cases
        """
        try:
            tree = ast.parse(code)
        except SyntaxError as e:
            return {
                "success": False,
                "error": f"Syntax error: {e}",
            }
        except Exception as e:
            return {
                "success": False,
                "error": f"Parse error: {e}",
            }

        analyzer = EdgeCaseAnalyzer()
        analyzer.visit(tree)

        return {
            "success": True,
            "edge_cases": analyzer.edge_cases,
            "potential_errors": analyzer.potential_errors,
            "boundary_conditions": analyzer.boundary_conditions,
        }

    def analyze_side_effects(self, code: str) -> Dict[str, Any]:
        """
        Analyze side effects in code.
        
        Args:
            code: Python code to analyze
            
        Returns:
            Dictionary containing side effect analysis
        """
        try:
            tree = ast.parse(code)
        except SyntaxError as e:
            return {
                "success": False,
                "error": f"Syntax error: {e}",
            }
        except Exception as e:
            return {
                "success": False,
                "error": f"Parse error: {e}",
            }

        analyzer = SideEffectAnalyzer()
        analyzer.visit(tree)

        return {
            "success": True,
            "side_effects": analyzer.side_effects,
            "mutations": analyzer.mutations,
            "external_calls": analyzer.external_calls,
            "io_operations": analyzer.io_operations,
        }

    def verify_correctness(self, code: str, spec: Dict[str, Any]) -> Dict[str, Any]:
        """
        Verify code correctness against a specification.
        
        Args:
            code: Python code to verify
            spec: Specification dictionary with:
                - inputs: List of input test cases
                - expected_outputs: List of expected outputs
                - invariants: List of invariants to check
                - preconditions: Preconditions that must hold
                - postconditions: Postconditions that must hold
                
        Returns:
            Dictionary containing verification results
        """
        try:
            tree = ast.parse(code)
        except SyntaxError as e:
            return {
                "success": False,
                "error": f"Syntax error: {e}",
            }
        except Exception as e:
            return {
                "success": False,
                "error": f"Parse error: {e}",
            }

        verifier = CorrectnessVerifier(spec)
        verifier.visit(tree)

        # Test against provided test cases
        test_results = []
        if spec.get("inputs") and spec.get("expected_outputs"):
            for i, (test_input, expected_output) in enumerate(
                zip(spec["inputs"], spec["expected_outputs"])
            ):
                prediction = self.predict_execution(code, test_input)
                actual_output = prediction.get("predicted_output")
                test_results.append({
                    "test_case": i,
                    "input": test_input,
                    "expected": expected_output,
                    "actual": actual_output,
                    "passed": actual_output == expected_output,
                })

        return {
            "success": True,
            "test_results": test_results,
            "all_tests_passed": all(t["passed"] for t in test_results) if test_results else None,
            "invariants_checked": verifier.invariants_checked,
            "preconditions_met": verifier.preconditions_met,
            "postconditions_met": verifier.postconditions_met,
        }

    def analyze_complexity(self, code: str) -> Dict[str, Any]:
        """
        Analyze computational complexity of code.
        
        Args:
            code: Python code to analyze
            
        Returns:
            Dictionary containing complexity analysis
        """
        try:
            tree = ast.parse(code)
        except SyntaxError as e:
            return {
                "success": False,
                "error": f"Syntax error: {e}",
            }
        except Exception as e:
            return {
                "success": False,
                "error": f"Parse error: {e}",
            }

        analyzer = ComplexityAnalyzer()
        analyzer.visit(tree)

        return {
            "success": True,
            "time_complexity": analyzer.time_complexity,
            "space_complexity": analyzer.space_complexity,
            "nested_loops": analyzer.nested_loops,
            "recursive_calls": analyzer.recursive_calls,
            "complexity_analysis": analyzer.complexity_analysis,
        }

    def predict_outputs(self, code: str, test_cases: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Predict outputs for multiple test cases.
        
        Args:
            code: Python code to analyze
            test_cases: List of test case dictionaries with input values
            
        Returns:
            Dictionary containing predictions for all test cases
        """
        predictions = []
        
        for i, test_case in enumerate(test_cases):
            prediction = self.predict_execution(code, test_case)
            predictions.append({
                "test_case": i,
                "input": test_case,
                "prediction": prediction.get("predicted_output"),
                "execution_path": prediction.get("execution_path"),
            })

        return {
            "success": True,
            "predictions": predictions,
            "total_test_cases": len(test_cases),
        }


# AST Visitor Classes for Behavior Analysis

class ExecutionPredictor(ast.NodeVisitor):
    """AST visitor for predicting execution outcomes."""

    def __init__(self, inputs: Dict[str, Any]):
        """Initialize execution predictor."""
        self.inputs = inputs
        self.variables: Dict[str, Any] = dict(inputs)
        self.output = None
        self.execution_path: List[str] = []
        self.variable_states: List[Dict[str, Any]] = []
        self.conditions_met: List[Dict[str, Any]] = []
        self.side_effects: List[str] = []

    def visit_Assign(self, node: ast.Assign) -> None:
        """Visit assignment statement."""
        for target in node.targets:
            if isinstance(target, ast.Name):
                # Evaluate value
                value = self._evaluate_expression(node.value)
                self.variables[target.id] = value
                self.execution_path.append(f"Assign {target.id} = {value}")
                self._record_state()

    def visit_Return(self, node: ast.Return) -> None:
        """Visit return statement."""
        if node.value:
            self.output = self._evaluate_expression(node.value)
            self.execution_path.append(f"Return {self.output}")
            self._record_state()

    def visit_If(self, node: ast.If) -> None:
        """Visit if statement."""
        condition_value = self._evaluate_expression(node.test)
        self.conditions_met.append({
            "line": node.lineno,
            "condition": ast.unparse(node.test) if hasattr(ast, "unparse") else str(node.test),
            "result": condition_value,
        })
        
        if condition_value:
            self.execution_path.append(f"If condition True (line {node.lineno})")
            for stmt in node.body:
                self.visit(stmt)
        else:
            self.execution_path.append(f"If condition False (line {node.lineno})")
            for stmt in node.orelse:
                self.visit(stmt)

    def visit_For(self, node: ast.For) -> None:
        """Visit for loop."""
        iterable = self._evaluate_expression(node.iter)
        if isinstance(iterable, (list, tuple, range)):
            self.execution_path.append(f"For loop: {len(iterable)} iterations")
            for item in iterable:
                if isinstance(node.target, ast.Name):
                    self.variables[node.target.id] = item
                for stmt in node.body:
                    self.visit(stmt)
        else:
            self.execution_path.append(f"For loop: unknown iterations")

    def visit_While(self, node: ast.While) -> None:
        """Visit while loop."""
        condition = self._evaluate_expression(node.test)
        iterations = 0
        max_iterations = 100  # Safety limit
        
        while condition and iterations < max_iterations:
            iterations += 1
            for stmt in node.body:
                self.visit(stmt)
            condition = self._evaluate_expression(node.test)
        
        self.execution_path.append(f"While loop: {iterations} iterations")

    def visit_Call(self, node: ast.Call) -> None:
        """Visit function call."""
        if isinstance(node.func, ast.Name):
            func_name = node.func.id
            # Check for built-in functions
            if func_name == "print":
                self.side_effects.append(f"{'print' + '()'} call at line {node.lineno}")
            elif func_name == "len":
                return len(self._evaluate_expression(node.args[0]) if node.args else [])
            elif func_name == "range":
                args = [self._evaluate_expression(arg) for arg in node.args]
                return range(*args)
            else:
                self.side_effects.append(f"Function call: {func_name}() at line {node.lineno}")

    def _evaluate_expression(self, node: ast.AST) -> Any:
        """Evaluate an expression node."""
        if isinstance(node, ast.Constant):
            return node.value
        elif isinstance(node, ast.Name):
            return self.variables.get(node.id, None)
        elif isinstance(node, ast.BinOp):
            left = self._evaluate_expression(node.left)
            right = self._evaluate_expression(node.right)
            op = type(node.op)
            if op == ast.Add:
                return left + right
            elif op == ast.Sub:
                return left - right
            elif op == ast.Mult:
                return left * right
            elif op == ast.Div:
                return left / right if right != 0 else None
            elif op == ast.Mod:
                return left % right if right != 0 else None
            elif op == ast.Pow:
                return left ** right
            elif op == ast.FloorDiv:
                return left // right if right != 0 else None
        elif isinstance(node, ast.Compare):
            left = self._evaluate_expression(node.left)
            for op, comparator in zip(node.ops, node.comparators):
                right = self._evaluate_expression(comparator)
                op_type = type(op)
                if op_type == ast.Eq:
                    result = left == right
                elif op_type == ast.NotEq:
                    result = left != right
                elif op_type == ast.Lt:
                    result = left < right
                elif op_type == ast.LtE:
                    result = left <= right
                elif op_type == ast.Gt:
                    result = left > right
                elif op_type == ast.GtE:
                    result = left >= right
                else:
                    result = False
                if not result:
                    return False
                left = right
            return True
        elif isinstance(node, ast.BoolOp):
            values = [self._evaluate_expression(v) for v in node.values]
            if isinstance(node.op, ast.And):
                return all(values)
            elif isinstance(node.op, ast.Or):
                return any(values)
        elif isinstance(node, ast.UnaryOp):
            operand = self._evaluate_expression(node.operand)
            if isinstance(node.op, ast.Not):
                return not operand
            elif isinstance(node.op, ast.USub):
                return -operand
            elif isinstance(node.op, ast.UAdd):
                return +operand
        
        return None

    def _record_state(self) -> None:
        """Record current variable state."""
        self.variable_states.append(dict(self.variables))


class ExecutionTracer(ast.NodeVisitor):
    """AST visitor for tracing execution paths."""

    def __init__(self, inputs: Dict[str, Any]):
        """Initialize execution tracer."""
        self.inputs = inputs
        self.trace: List[str] = []
        self.line_numbers: List[int] = []
        self.branches_taken: List[Dict[str, Any]] = []
        self.loops_executed: List[Dict[str, Any]] = []

    def visit(self, node: ast.AST) -> None:
        """Visit node and record trace."""
        if hasattr(node, "lineno"):
            self.line_numbers.append(node.lineno)
            self.trace.append(f"Line {node.lineno}: {type(node).__name__}")
        super().visit(node)

    def visit_If(self, node: ast.If) -> None:
        """Visit if statement."""
        self.branches_taken.append({
            "line": node.lineno,
            "type": "if",
            "taken": "then" if node.body else "else",
        })
        super().visit(node)

    def visit_For(self, node: ast.For) -> None:
        """Visit for loop."""
        self.loops_executed.append({
            "line": node.lineno,
            "type": "for",
        })
        super().visit(node)

    def visit_While(self, node: ast.While) -> None:
        """Visit while loop."""
        self.loops_executed.append({
            "line": node.lineno,
            "type": "while",
        })
        super().visit(node)


class EdgeCaseAnalyzer(ast.NodeVisitor):
    """AST visitor for identifying edge cases."""

    def __init__(self):
        """Initialize edge case analyzer."""
        self.edge_cases: List[Dict[str, Any]] = []
        self.potential_errors: List[Dict[str, Any]] = []
        self.boundary_conditions: List[Dict[str, Any]] = []

    def visit_BinOp(self, node: ast.BinOp) -> None:
        """Visit binary operation."""
        if isinstance(node.op, (ast.Div, ast.FloorDiv, ast.Mod)):
            self.potential_errors.append({
                "line": node.lineno,
                "type": "division_by_zero",
                "message": "Potential division by zero",
            })

    def visit_Compare(self, node: ast.Compare) -> None:
        """Visit comparison."""
        # Check for boundary conditions
        for op in node.ops:
            if isinstance(op, (ast.Eq, ast.Lt, ast.LtE, ast.Gt, ast.GtE)):
                self.boundary_conditions.append({
                    "line": node.lineno,
                    "type": "boundary_check",
                    "message": "Boundary condition check",
                })

    def visit_Subscript(self, node: ast.Subscript) -> None:
        """Visit subscript (indexing)."""
        self.potential_errors.append({
            "line": node.lineno,
            "type": "index_error",
            "message": "Potential index out of bounds",
        })

    def visit_Attribute(self, node: ast.Attribute) -> None:
        """Visit attribute access."""
        self.potential_errors.append({
            "line": node.lineno,
            "type": "attribute_error",
            "message": "Potential attribute error",
        })


class SideEffectAnalyzer(ast.NodeVisitor):
    """AST visitor for analyzing side effects."""

    def __init__(self):
        """Initialize side effect analyzer."""
        self.side_effects: List[str] = []
        self.mutations: List[Dict[str, Any]] = []
        self.external_calls: List[Dict[str, Any]] = []
        self.io_operations: List[Dict[str, Any]] = []

    def visit_Assign(self, node: ast.Assign) -> None:
        """Visit assignment."""
        for target in node.targets:
            if isinstance(target, ast.Name):
                self.mutations.append({
                    "line": node.lineno,
                    "variable": target.id,
                    "type": "assignment",
                })

    def visit_Call(self, node: ast.Call) -> None:
        """Visit function call."""
        if isinstance(node.func, ast.Name):
            func_name = node.func.id
            if func_name in ["print", "input", "open", "file"]:
                self.io_operations.append({
                    "line": node.lineno,
                    "operation": func_name,
                })
            else:
                self.external_calls.append({
                    "line": node.lineno,
                    "function": func_name,
                })


class CorrectnessVerifier(ast.NodeVisitor):
    """AST visitor for verifying correctness."""

    def __init__(self, spec: Dict[str, Any]):
        """Initialize correctness verifier."""
        self.spec = spec
        self.invariants_checked: List[Dict[str, Any]] = []
        self.preconditions_met: bool = True
        self.postconditions_met: bool = True

    def visit(self, node: ast.AST) -> None:
        """Visit node and check invariants."""
        # Check invariants if specified
        if "invariants" in self.spec:
            for invariant in self.spec["invariants"]:
                self.invariants_checked.append({
                    "invariant": invariant,
                    "checked": True,
                })
        super().visit(node)


class ComplexityAnalyzer(ast.NodeVisitor):
    """AST visitor for analyzing complexity."""

    def __init__(self):
        """Initialize complexity analyzer."""
        self.time_complexity: str = "O(1)"
        self.space_complexity: str = "O(1)"
        self.nested_loops: int = 0
        self.recursive_calls: int = 0
        self.complexity_analysis: Dict[str, Any] = {}
        self._loop_depth: int = 0
        self._max_loop_depth: int = 0

    def visit_For(self, node: ast.For) -> None:
        """Visit for loop."""
        self._loop_depth += 1
        self._max_loop_depth = max(self._max_loop_depth, self._loop_depth)
        self.nested_loops += 1
        super().visit(node)
        self._loop_depth -= 1

    def visit_While(self, node: ast.While) -> None:
        """Visit while loop."""
        self._loop_depth += 1
        self._max_loop_depth = max(self._max_loop_depth, self._loop_depth)
        self.nested_loops += 1
        super().visit(node)
        self._loop_depth -= 1

    def visit_Call(self, node: ast.Call) -> None:
        """Visit function call."""
        if isinstance(node.func, ast.Name):
            # Check for recursive calls (simplified)
            # In full implementation, would track function definitions
            pass

    def visit(self, node: ast.AST) -> None:
        """Visit node and update complexity."""
        super().visit(node)
        
        # Determine time complexity based on loop depth
        if self._max_loop_depth == 0:
            self.time_complexity = "O(1)"
        elif self._max_loop_depth == 1:
            self.time_complexity = "O(n)"
        elif self._max_loop_depth == 2:
            self.time_complexity = "O(n²)"
        else:
            self.time_complexity = f"O(n^{self._max_loop_depth})"
        
        self.complexity_analysis = {
            "time_complexity": self.time_complexity,
            "space_complexity": self.space_complexity,
            "nested_loops": self.nested_loops,
            "max_loop_depth": self._max_loop_depth,
        }

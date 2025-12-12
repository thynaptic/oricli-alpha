"""
Test Generation Reasoning Module

Generate tests from code understanding through reasoning. Identifies test cases,
generates edge case tests, property-based tests, and analyzes test coverage.

This module is part of Mavaia's Python LLM capabilities, enabling
intelligent test generation from code understanding.
"""

import ast
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional

from mavaia_core.brain.base_module import BaseBrainModule, ModuleMetadata
from mavaia_core.exceptions import InvalidParameterError


class TestGenerationReasoningModule(BaseBrainModule):
    """
    Generate tests from code understanding through reasoning.
    
    Provides:
    - Test generation from code understanding
    - Test case identification through reasoning
    - Edge case test generation
    - Property-based test generation
    - Test coverage analysis
    """

    def __init__(self):
        """Initialize the test generation module."""
        super().__init__()
        self._behavior_reasoning = None
        self._semantic_understanding = None
        self._code_generator = None

    @property
    def metadata(self) -> ModuleMetadata:
        """Return module metadata."""
        return ModuleMetadata(
            name="test_generation_reasoning",
            version="1.0.0",
            description=(
                "Generate tests from code understanding: identify test cases, "
                "generate edge case tests, property-based tests, and analyze coverage"
            ),
            operations=[
                "generate_tests",
                "identify_test_cases",
                "generate_edge_case_tests",
                "generate_property_tests",
                "analyze_coverage",
            ],
            dependencies=[],
            model_required=False,
        )

    def initialize(self) -> bool:
        """Initialize the module."""
        # Try to load related modules
        try:
            from mavaia_core.brain.registry import ModuleRegistry
            self._behavior_reasoning = ModuleRegistry.get_module("program_behavior_reasoning")
            self._semantic_understanding = ModuleRegistry.get_module("python_semantic_understanding")
            self._code_generator = ModuleRegistry.get_module("reasoning_code_generator")
        except Exception:
            pass
        
        return True

    def execute(self, operation: str, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute a test generation operation.
        
        Args:
            operation: Operation name
            params: Operation parameters
            
        Returns:
            Operation result dictionary
            
        Raises:
            ValueError: If operation is unknown
            InvalidParameterError: If parameters are invalid
        """
        if operation == "generate_tests":
            code = params.get("code", "")
            if not code:
                raise InvalidParameterError("code", "", "Code cannot be empty")
            return self.generate_tests(code)
        
        elif operation == "identify_test_cases":
            code = params.get("code", "")
            if not code:
                raise InvalidParameterError("code", "", "Code cannot be empty")
            return self.identify_test_cases(code)
        
        elif operation == "generate_edge_case_tests":
            code = params.get("code", "")
            if not code:
                raise InvalidParameterError("code", "", "Code cannot be empty")
            return self.generate_edge_case_tests(code)
        
        elif operation == "generate_property_tests":
            code = params.get("code", "")
            if not code:
                raise InvalidParameterError("code", "", "Code cannot be empty")
            return self.generate_property_tests(code)
        
        elif operation == "analyze_coverage":
            code = params.get("code", "")
            tests = params.get("tests", [])
            if not code:
                raise InvalidParameterError("code", "", "Code cannot be empty")
            if not tests:
                raise InvalidParameterError("tests", [], "Tests cannot be empty")
            return self.analyze_coverage(code, tests)
        
        else:
            raise ValueError(f"Unknown operation: {operation}")

    def generate_tests(self, code: str) -> Dict[str, Any]:
        """
        Generate test suite from code understanding.
        
        Args:
            code: Code to generate tests for
            
        Returns:
            Dictionary containing generated test suite
        """
        # Analyze code to understand what needs testing
        analysis = self._analyze_code_for_testing(code)
        
        # Identify test cases
        test_cases = self._identify_test_cases_internal(code, analysis)
        
        # Generate test code
        test_suite = self._generate_test_suite(code, test_cases, analysis)
        
        return {
            "success": True,
            "code": code,
            "test_suite": test_suite,
            "test_cases": test_cases,
            "analysis": analysis,
        }

    def identify_test_cases(self, code: str) -> Dict[str, Any]:
        """
        Identify test cases through reasoning.
        
        Args:
            code: Code to analyze
            
        Returns:
            Dictionary containing identified test cases
        """
        analysis = self._analyze_code_for_testing(code)
        test_cases = self._identify_test_cases_internal(code, analysis)
        
        return {
            "success": True,
            "code": code,
            "test_cases": test_cases,
            "analysis": analysis,
        }

    def generate_edge_case_tests(self, code: str) -> Dict[str, Any]:
        """
        Generate edge case tests.
        
        Args:
            code: Code to generate edge case tests for
            
        Returns:
            Dictionary containing edge case tests
        """
        # Find edge cases
        if self._behavior_reasoning:
            try:
                edge_cases_result = self._behavior_reasoning.execute("find_edge_cases", {
                    "code": code,
                })
                edge_cases = edge_cases_result.get("edge_cases", [])
            except Exception:
                edge_cases = []
        else:
            edge_cases = []

        # Generate tests for edge cases
        edge_tests = []
        for edge_case in edge_cases:
            test = self._generate_test_for_edge_case(code, edge_case)
            edge_tests.append(test)

        return {
            "success": True,
            "code": code,
            "edge_case_tests": edge_tests,
            "edge_cases": edge_cases,
        }

    def generate_property_tests(self, code: str) -> Dict[str, Any]:
        """
        Generate property-based tests.
        
        Args:
            code: Code to generate property tests for
            
        Returns:
            Dictionary containing property-based tests
        """
        # Analyze code to identify properties
        properties = self._identify_properties(code)
        
        # Generate property tests
        property_tests = []
        for prop in properties:
            test = self._generate_property_test(code, prop)
            property_tests.append(test)

        return {
            "success": True,
            "code": code,
            "property_tests": property_tests,
            "properties": properties,
        }

    def analyze_coverage(self, code: str, tests: List[str]) -> Dict[str, Any]:
        """
        Analyze test coverage.
        
        Args:
            code: Code being tested
            tests: List of test code strings
            
        Returns:
            Dictionary containing coverage analysis
        """
        # Analyze code structure
        if self._semantic_understanding:
            try:
                code_analysis = self._semantic_understanding.execute("analyze_semantics", {
                    "code": code,
                })
                functions = code_analysis.get("functions", [])
                classes = code_analysis.get("classes", [])
            except Exception:
                functions = []
                classes = []
        else:
            functions = []
            classes = []

        # Analyze which functions/classes are tested
        tested_functions = []
        tested_classes = []
        
        for test in tests:
            test_lower = test.lower()
            for func in functions:
                func_name = func.get("name", "")
                if func_name and func_name.lower() in test_lower:
                    if func_name not in tested_functions:
                        tested_functions.append(func_name)
            
            for cls in classes:
                cls_name = cls.get("name", "")
                if cls_name and cls_name.lower() in test_lower:
                    if cls_name not in tested_classes:
                        tested_classes.append(cls_name)

        # Calculate coverage
        function_coverage = len(tested_functions) / len(functions) if functions else 0.0
        class_coverage = len(tested_classes) / len(classes) if classes else 0.0
        overall_coverage = (function_coverage + class_coverage) / 2 if (functions or classes) else 0.0

        return {
            "success": True,
            "code": code,
            "total_functions": len(functions),
            "total_classes": len(classes),
            "tested_functions": tested_functions,
            "tested_classes": tested_classes,
            "function_coverage": function_coverage,
            "class_coverage": class_coverage,
            "overall_coverage": overall_coverage,
        }

    def _analyze_code_for_testing(self, code: str) -> Dict[str, Any]:
        """Analyze code to determine what needs testing."""
        analysis = {
            "functions": [],
            "classes": [],
            "edge_cases": [],
            "properties": [],
        }

        try:
            tree = ast.parse(code)
        except SyntaxError:
            return analysis

        # Extract functions and classes
        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef):
                analysis["functions"].append({
                    "name": node.name,
                    "line": node.lineno,
                    "args": [arg.arg for arg in node.args.args],
                })
            elif isinstance(node, ast.ClassDef):
                analysis["classes"].append({
                    "name": node.name,
                    "line": node.lineno,
                    "methods": [n.name for n in node.body if isinstance(n, ast.FunctionDef)],
                })

        # Find edge cases
        if self._behavior_reasoning:
            try:
                edge_result = self._behavior_reasoning.execute("find_edge_cases", {
                    "code": code,
                })
                analysis["edge_cases"] = edge_result.get("edge_cases", [])
            except Exception:
                pass

        return analysis

    def _identify_test_cases_internal(
        self,
        code: str,
        analysis: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """Identify test cases for code."""
        test_cases = []

        # Generate test cases for each function
        for func in analysis.get("functions", []):
            func_name = func.get("name", "")
            args = func.get("args", [])
            
            # Basic test case
            test_cases.append({
                "type": "function",
                "target": func_name,
                "description": f"Test {func_name} with basic inputs",
                "inputs": self._generate_test_inputs(args),
            })

            # Edge case test cases
            test_cases.append({
                "type": "edge_case",
                "target": func_name,
                "description": f"Test {func_name} with edge case inputs",
                "inputs": self._generate_edge_inputs(args),
            })

        # Generate test cases for classes
        for cls in analysis.get("classes", []):
            cls_name = cls.get("name", "")
            methods = cls.get("methods", [])
            
            test_cases.append({
                "type": "class",
                "target": cls_name,
                "description": f"Test {cls_name} class",
                "methods": methods,
            })

        return test_cases

    def _generate_test_suite(
        self,
        code: str,
        test_cases: List[Dict[str, Any]],
        analysis: Dict[str, Any]
    ) -> str:
        """Generate test suite code."""
        # Use code generator if available
        if self._code_generator:
            try:
                requirements = self._build_test_requirements(code, test_cases)
                result = self._code_generator.execute("generate_code_reasoning", {
                    "requirements": requirements,
                    "reasoning_method": "cot",
                })
                test_suite = result.get("code", "")
                if test_suite:
                    return test_suite
            except Exception:
                pass

        # Fallback: generate basic test suite
        return self._generate_basic_test_suite(code, test_cases)

    def _generate_basic_test_suite(
        self,
        code: str,
        test_cases: List[Dict[str, Any]]
    ) -> str:
        """Generate basic test suite."""
        test_lines = [
            "import unittest",
            "",
            f"# Tests for code",
            "",
            "class TestCode(unittest.TestCase):",
        ]

        for i, test_case in enumerate(test_cases):
            test_name = f"test_{test_case.get('target', 'unknown')}_{i}"
            test_lines.append(f"    def {test_name}(self):")
            test_lines.append(f"        # {test_case.get('description', '')}")
            test_lines.append("        # TODO: Implement test")
            test_lines.append("        pass")
            test_lines.append("")

        test_lines.append("if __name__ == '__main__':")
        test_lines.append("    unittest.main()")

        return '\n'.join(test_lines)

    def _generate_test_inputs(self, args: List[str]) -> Dict[str, Any]:
        """Generate test inputs for function arguments."""
        inputs = {}
        for arg in args:
            if arg == "self":
                continue
            # Simple type inference for test inputs
            inputs[arg] = self._infer_test_value(arg)
        return inputs

    def _generate_edge_inputs(self, args: List[str]) -> Dict[str, Any]:
        """Generate edge case inputs."""
        inputs = {}
        for arg in args:
            if arg == "self":
                continue
            # Generate edge case values
            inputs[arg] = self._infer_edge_value(arg)
        return inputs

    def _infer_test_value(self, arg_name: str) -> Any:
        """Infer test value for argument."""
        # Simple heuristics
        arg_lower = arg_name.lower()
        if "list" in arg_lower or "items" in arg_lower:
            return []
        elif "dict" in arg_lower or "map" in arg_lower:
            return {}
        elif "str" in arg_lower or "text" in arg_lower or "name" in arg_lower:
            return "test"
        elif "int" in arg_lower or "num" in arg_lower or "count" in arg_lower:
            return 1
        elif "bool" in arg_lower or "flag" in arg_lower:
            return True
        else:
            return None

    def _infer_edge_value(self, arg_name: str) -> Any:
        """Infer edge case value."""
        arg_lower = arg_name.lower()
        if "list" in arg_lower or "items" in arg_lower:
            return []  # Empty list
        elif "int" in arg_lower or "num" in arg_lower:
            return 0  # Zero
        elif "str" in arg_lower or "text" in arg_lower:
            return ""  # Empty string
        else:
            return None

    def _generate_test_for_edge_case(
        self,
        code: str,
        edge_case: Dict[str, Any]
    ) -> str:
        """Generate test for specific edge case."""
        edge_type = edge_case.get("type", "unknown")
        line = edge_case.get("line", 0)
        
        return f"""def test_edge_case_{edge_type}_line_{line}():
    # Test edge case: {edge_case.get('message', '')}
    # TODO: Implement test
    pass
"""

    def _identify_properties(self, code: str) -> List[Dict[str, Any]]:
        """Identify properties for property-based testing."""
        properties = []

        try:
            tree = ast.parse(code)
        except SyntaxError:
            return properties

        # Look for functions that might have properties
        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef):
                # Check if function might have commutative property
                if "add" in node.name.lower() or "multiply" in node.name.lower():
                    properties.append({
                        "type": "commutative",
                        "function": node.name,
                        "description": f"{node.name} should be commutative",
                    })
                # Check for identity property
                if "add" in node.name.lower():
                    properties.append({
                        "type": "identity",
                        "function": node.name,
                        "description": f"{node.name}(x, 0) should equal x",
                    })

        return properties

    def _generate_property_test(
        self,
        code: str,
        property: Dict[str, Any]
    ) -> str:
        """Generate property-based test."""
        prop_type = property.get("type", "unknown")
        func_name = property.get("function", "")
        
        return f"""def test_property_{prop_type}_{func_name}():
    # Property-based test: {property.get('description', '')}
    # TODO: Implement property test using hypothesis or similar
    pass
"""

    def _build_test_requirements(
        self,
        code: str,
        test_cases: List[Dict[str, Any]]
    ) -> str:
        """Build requirements for test generation."""
        requirements = f"Generate a comprehensive test suite for the following Python code:\n\n{code}\n\n"
        requirements += "Test cases to cover:\n"
        for i, test_case in enumerate(test_cases, 1):
            requirements += f"{i}. {test_case.get('description', '')}\n"
        
        requirements += "\nUse unittest framework and follow Python testing best practices."
        return requirements

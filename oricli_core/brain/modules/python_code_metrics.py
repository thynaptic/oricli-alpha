from __future__ import annotations
"""
Python Code Metrics Module

Comprehensive code metrics calculation including complexity analysis
(cyclomatic, cognitive), maintainability scoring, code coverage analysis,
dependency complexity, test quality metrics, and documentation coverage.

This module is part of OricliAlpha's Python LLM Phase 4 capabilities, providing
detailed metrics for code quality assessment and improvement tracking.
"""

import ast
import sys
from collections import defaultdict
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple

from oricli_core.brain.base_module import BaseBrainModule, ModuleMetadata
from oricli_core.exceptions import InvalidParameterError


class PythonCodeMetricsModule(BaseBrainModule):
    """
    Comprehensive code metrics calculation and analysis.
    
    Provides:
    - Full metrics suite calculation
    - Complexity analysis (cyclomatic, cognitive)
    - Maintainability scoring
    - Code coverage analysis
    - Documentation coverage measurement
    - Dependency complexity analysis
    - Test quality metrics
    """

    def __init__(self):
        """Initialize the Python code metrics module."""
        super().__init__()
        self._semantic_understanding = None
        self._code_analysis = None

    @property
    def metadata(self) -> ModuleMetadata:
        """Return module metadata."""
        return ModuleMetadata(
            name="python_code_metrics",
            version="1.0.0",
            description=(
                "Comprehensive code metrics: complexity analysis, maintainability "
                "scoring, test coverage, documentation coverage, dependency complexity, "
                "and test quality metrics"
            ),
            operations=[
                "calculate_metrics",
                "analyze_complexity",
                "score_maintainability",
                "analyze_test_coverage",
                "measure_documentation_coverage",
                "analyze_dependency_complexity",
            ],
            dependencies=[],
            model_required=False,
        )

    def initialize(self) -> bool:
        """Initialize the module."""
        # Try to load related modules
        try:
            from oricli_core.brain.registry import ModuleRegistry
            self._semantic_understanding = ModuleRegistry.get_module("python_semantic_understanding")
            self._code_analysis = ModuleRegistry.get_module("code_analysis")
        except Exception:
            pass
        
        return True

    def execute(self, operation: str, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute a code metrics operation.
        
        Args:
            operation: Operation name
            params: Operation parameters
            
        Returns:
            Operation result dictionary
            
        Raises:
            ValueError: If operation is unknown
            InvalidParameterError: If parameters are invalid
        """
        if operation == "calculate_metrics":
            code = params.get("code", "")
            if not code:
                raise InvalidParameterError("code", "", "Code cannot be empty")
            return self.calculate_metrics(code)
        
        elif operation == "analyze_complexity":
            code = params.get("code", "")
            if not code:
                raise InvalidParameterError("code", "", "Code cannot be empty")
            return self.analyze_complexity(code)
        
        elif operation == "score_maintainability":
            code = params.get("code", "")
            if not code:
                raise InvalidParameterError("code", "", "Code cannot be empty")
            return self.score_maintainability(code)
        
        elif operation == "analyze_test_coverage":
            code = params.get("code", "")
            tests = params.get("tests", "")
            if not code:
                raise InvalidParameterError("code", "", "Code cannot be empty")
            return self.analyze_test_coverage(code, tests)
        
        elif operation == "measure_documentation_coverage":
            code = params.get("code", "")
            if not code:
                raise InvalidParameterError("code", "", "Code cannot be empty")
            return self.measure_documentation_coverage(code)
        
        elif operation == "analyze_dependency_complexity":
            project = params.get("project", None)
            if not project:
                raise InvalidParameterError("project", None, "Project path is required")
            return self.analyze_dependency_complexity(project)
        
        else:
            raise InvalidParameterError(
                parameter="operation",
                value=str(operation),
                reason="Unknown operation",
            )

    def calculate_metrics(self, code: str) -> Dict[str, Any]:
        """
        Calculate comprehensive code metrics.
        
        Args:
            code: Python code to analyze
            
        Returns:
            Dictionary containing all calculated metrics
        """
        try:
            tree = ast.parse(code)
        except SyntaxError as e:
            return {
                "success": False,
                "error": f"Syntax error: {e}",
                "line": e.lineno,
                "offset": e.offset,
            }
        except Exception as e:
            return {
                "success": False,
                "error": f"Parse error: {e}",
            }

        # Collect all metrics
        complexity_metrics = self.analyze_complexity(code)
        maintainability = self.score_maintainability(code)
        doc_coverage = self.measure_documentation_coverage(code)

        # Basic code statistics
        stats_visitor = CodeStatisticsVisitor()
        stats_visitor.visit(tree)

        return {
            "success": True,
            "complexity": complexity_metrics,
            "maintainability": maintainability,
            "documentation": doc_coverage,
            "statistics": {
                "lines_of_code": stats_visitor.lines_of_code,
                "functions": stats_visitor.function_count,
                "classes": stats_visitor.class_count,
                "imports": stats_visitor.import_count,
                "average_function_length": stats_visitor.average_function_length,
                "average_class_size": stats_visitor.average_class_size,
            },
            "summary": self._generate_metrics_summary(complexity_metrics, maintainability, doc_coverage),
        }

    def analyze_complexity(self, code: str) -> Dict[str, Any]:
        """
        Analyze code complexity metrics.
        
        Args:
            code: Python code to analyze
            
        Returns:
            Dictionary containing complexity metrics (cyclomatic, cognitive)
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

        # Cyclomatic complexity
        cyclomatic_visitor = CyclomaticComplexityVisitor()
        cyclomatic_visitor.visit(tree)

        # Cognitive complexity
        cognitive_visitor = CognitiveComplexityVisitor()
        cognitive_visitor.visit(tree)

        # Time/space complexity
        algorithmic_visitor = AlgorithmicComplexityVisitor()
        algorithmic_visitor.visit(tree)

        return {
            "success": True,
            "cyclomatic": {
                "average": cyclomatic_visitor.average_complexity,
                "max": cyclomatic_visitor.max_complexity,
                "total": cyclomatic_visitor.total_complexity,
                "functions": cyclomatic_visitor.function_complexities,
            },
            "cognitive": {
                "average": cognitive_visitor.average_complexity,
                "max": cognitive_visitor.max_complexity,
                "total": cognitive_visitor.total_complexity,
                "functions": cognitive_visitor.function_complexities,
            },
            "algorithmic": {
                "time_complexity": algorithmic_visitor.time_complexity,
                "space_complexity": algorithmic_visitor.space_complexity,
                "nested_loops": algorithmic_visitor.nested_loops,
                "max_loop_depth": algorithmic_visitor.max_loop_depth,
            },
            "assessment": self._assess_complexity(
                cyclomatic_visitor.max_complexity,
                cognitive_visitor.max_complexity
            ),
        }

    def score_maintainability(self, code: str) -> Dict[str, Any]:
        """
        Score code maintainability.
        
        Args:
            code: Python code to analyze
            
        Returns:
            Dictionary containing maintainability score and factors
        """
        try:
            tree = ast.parse(code)
        except SyntaxError:
            return {
                "score": 0,
                "factors": {},
                "assessment": "invalid",
            }
        except Exception:
            return {
                "score": 0,
                "factors": {},
                "assessment": "invalid",
            }

        # Calculate maintainability factors
        complexity_metrics = self.analyze_complexity(code)
        doc_coverage = self.measure_documentation_coverage(code)
        
        # Code statistics
        stats_visitor = CodeStatisticsVisitor()
        stats_visitor.visit(tree)

        # Calculate maintainability index (0-100)
        # Based on: Halstead Volume, Cyclomatic Complexity, Lines of Code, Comment Percentage
        
        # Factor 1: Complexity (lower is better)
        max_cyclomatic = complexity_metrics.get("cyclomatic", {}).get("max", 1)
        complexity_score = max(0, 100 - (max_cyclomatic - 1) * 5)
        complexity_score = min(100, complexity_score)

        # Factor 2: Documentation (higher is better)
        doc_percentage = doc_coverage.get("percentage", 0)
        doc_score = doc_percentage

        # Factor 3: Code size (smaller functions/classes are better)
        avg_func_length = stats_visitor.average_function_length
        size_score = max(0, 100 - (avg_func_length - 20) * 2)
        size_score = min(100, size_score)

        # Factor 4: Code structure (fewer nested levels are better)
        cognitive_max = complexity_metrics.get("cognitive", {}).get("max", 1)
        structure_score = max(0, 100 - (cognitive_max - 1) * 10)
        structure_score = min(100, structure_score)

        # Weighted maintainability index
        maintainability_score = int(
            complexity_score * 0.3 +
            doc_score * 0.25 +
            size_score * 0.25 +
            structure_score * 0.2
        )

        factors = {
            "complexity": complexity_score,
            "documentation": doc_score,
            "code_size": size_score,
            "structure": structure_score,
        }

        assessment = self._assess_maintainability(maintainability_score)

        return {
            "score": maintainability_score,
            "factors": factors,
            "assessment": assessment,
            "recommendations": self._generate_maintainability_recommendations(factors),
        }

    def analyze_test_coverage(self, code: str, tests: str = "") -> Dict[str, Any]:
        """
        Analyze test coverage for code.
        
        Args:
            code: Python code to analyze
            tests: Test code (optional, for heuristic analysis)
            
        Returns:
            Dictionary containing test coverage analysis
        """
        try:
            code_tree = ast.parse(code)
        except SyntaxError:
            return {
                "success": False,
                "error": "Code has syntax errors",
            }

        # Analyze code structure
        code_visitor = TestCoverageVisitor()
        code_visitor.visit(code_tree)

        # Analyze test structure if provided
        test_visitor = TestStructureVisitor()
        if tests:
            try:
                test_tree = ast.parse(tests)
                test_visitor.visit(test_tree)
            except SyntaxError:
                pass

        # Calculate coverage estimates
        total_functions = code_visitor.function_count
        total_classes = code_visitor.class_count
        total_methods = code_visitor.method_count

        # Heuristic: check if test file exists and has test functions
        has_tests = test_visitor.test_function_count > 0 if tests else False

        # Estimate coverage (simplified - real implementation would use coverage tools)
        if has_tests:
            # Rough estimate based on test function count
            estimated_coverage = min(100, (test_visitor.test_function_count / max(1, total_functions)) * 100)
        else:
            estimated_coverage = 0

        return {
            "success": True,
            "code_structure": {
                "functions": total_functions,
                "classes": total_classes,
                "methods": total_methods,
            },
            "test_structure": {
                "test_functions": test_visitor.test_function_count,
                "test_classes": test_visitor.test_class_count,
                "has_tests": has_tests,
            },
            "estimated_coverage": estimated_coverage,
            "coverage_level": self._categorize_coverage(estimated_coverage),
            "recommendations": self._generate_coverage_recommendations(
                total_functions,
                test_visitor.test_function_count,
                estimated_coverage
            ),
        }

    def measure_documentation_coverage(self, code: str) -> Dict[str, Any]:
        """
        Measure documentation coverage.
        
        Args:
            code: Python code to analyze
            
        Returns:
            Dictionary containing documentation coverage metrics
        """
        try:
            tree = ast.parse(code)
        except SyntaxError:
            return {
                "success": False,
                "error": "Code has syntax errors",
            }

        visitor = DocumentationCoverageVisitor()
        visitor.visit(tree)

        total_functions = visitor.total_functions
        total_classes = visitor.total_classes
        total_modules = visitor.total_modules

        documented_functions = visitor.documented_functions
        documented_classes = visitor.documented_classes
        documented_modules = visitor.documented_modules

        # Calculate percentages
        function_coverage = (documented_functions / max(1, total_functions)) * 100
        class_coverage = (documented_classes / max(1, total_classes)) * 100
        module_coverage = (documented_modules / max(1, total_modules)) * 100

        # Overall coverage
        total_items = total_functions + total_classes + total_modules
        documented_items = documented_functions + documented_classes + documented_modules
        overall_coverage = (documented_items / max(1, total_items)) * 100

        return {
            "success": True,
            "overall_percentage": overall_coverage,
            "function_coverage": function_coverage,
            "class_coverage": class_coverage,
            "module_coverage": module_coverage,
            "statistics": {
                "total_functions": total_functions,
                "documented_functions": documented_functions,
                "total_classes": total_classes,
                "documented_classes": documented_classes,
                "total_modules": total_modules,
                "documented_modules": documented_modules,
            },
            "assessment": self._assess_documentation_coverage(overall_coverage),
            "recommendations": self._generate_documentation_recommendations(
                function_coverage,
                class_coverage,
                module_coverage
            ),
        }

    def analyze_dependency_complexity(self, project: str) -> Dict[str, Any]:
        """
        Analyze dependency complexity for a project.
        
        Args:
            project: Project path
            
        Returns:
            Dictionary containing dependency complexity metrics
        """
        project_path = Path(project)
        
        if not project_path.exists():
            return {
                "success": False,
                "error": f"Project path does not exist: {project}",
            }

        # Try to find requirements files
        requirements_files = [
            project_path / "requirements.txt",
            project_path / "pyproject.toml",
            project_path / "setup.py",
        ]

        dependencies = []
        for req_file in requirements_files:
            if req_file.exists():
                try:
                    if req_file.name == "requirements.txt":
                        deps = self._parse_requirements_txt(req_file)
                    elif req_file.name == "pyproject.toml":
                        deps = self._parse_pyproject_toml(req_file)
                    else:
                        deps = []
                    dependencies.extend(deps)
                except Exception:
                    pass

        # Analyze import statements in code
        import_visitor = ImportComplexityVisitor()
        for py_file in project_path.rglob("*.py"):
            try:
                with open(py_file, "r", encoding="utf-8") as f:
                    code = f.read()
                tree = ast.parse(code)
                import_visitor.visit(tree)
            except Exception:
                pass

        # Calculate metrics
        total_imports = len(import_visitor.imports)
        unique_imports = len(set(import_visitor.imports))
        external_imports = len([imp for imp in import_visitor.imports if not imp.startswith(".")])
        internal_imports = len([imp for imp in import_visitor.imports if imp.startswith(".")])

        dependency_count = len(dependencies)
        complexity_score = self._calculate_dependency_complexity(
            dependency_count,
            total_imports,
            unique_imports
        )

        return {
            "success": True,
            "dependencies": {
                "count": dependency_count,
                "list": dependencies[:20],  # Limit to first 20
            },
            "imports": {
                "total": total_imports,
                "unique": unique_imports,
                "external": external_imports,
                "internal": internal_imports,
            },
            "complexity_score": complexity_score,
            "assessment": self._assess_dependency_complexity(complexity_score),
            "recommendations": self._generate_dependency_recommendations(
                dependency_count,
                unique_imports
            ),
        }

    # Helper methods

    def _generate_metrics_summary(
        self,
        complexity: Dict[str, Any],
        maintainability: Dict[str, Any],
        documentation: Dict[str, Any]
    ) -> str:
        """Generate a summary of all metrics."""
        maint_score = maintainability.get("score", 0)
        maint_assessment = maintainability.get("assessment", "unknown")
        doc_coverage = documentation.get("overall_percentage", 0)
        max_complexity = complexity.get("cyclomatic", {}).get("max", 0)

        summary_parts = []
        summary_parts.append(f"Maintainability: {maint_score}/100 ({maint_assessment})")
        summary_parts.append(f"Documentation: {doc_coverage:.1f}% coverage")
        summary_parts.append(f"Max Complexity: {max_complexity}")

        return "; ".join(summary_parts)

    def _assess_complexity(self, cyclomatic: int, cognitive: int) -> str:
        """Assess complexity level."""
        max_complexity = max(cyclomatic, cognitive)
        
        if max_complexity <= 10:
            return "low"
        elif max_complexity <= 20:
            return "moderate"
        elif max_complexity <= 30:
            return "high"
        else:
            return "very_high"

    def _assess_maintainability(self, score: int) -> str:
        """Assess maintainability level."""
        if score >= 80:
            return "excellent"
        elif score >= 60:
            return "good"
        elif score >= 40:
            return "moderate"
        elif score >= 20:
            return "poor"
        else:
            return "very_poor"

    def _assess_documentation_coverage(self, coverage: float) -> str:
        """Assess documentation coverage level."""
        if coverage >= 90:
            return "excellent"
        elif coverage >= 70:
            return "good"
        elif coverage >= 50:
            return "moderate"
        elif coverage >= 30:
            return "poor"
        else:
            return "very_poor"

    def _assess_dependency_complexity(self, score: int) -> str:
        """Assess dependency complexity level."""
        if score <= 20:
            return "low"
        elif score <= 40:
            return "moderate"
        elif score <= 60:
            return "high"
        else:
            return "very_high"

    def _categorize_coverage(self, coverage: float) -> str:
        """Categorize test coverage level."""
        if coverage >= 80:
            return "excellent"
        elif coverage >= 60:
            return "good"
        elif coverage >= 40:
            return "moderate"
        elif coverage >= 20:
            return "poor"
        else:
            return "very_poor"

    def _generate_maintainability_recommendations(self, factors: Dict[str, float]) -> List[str]:
        """Generate maintainability improvement recommendations."""
        recommendations = []
        
        if factors.get("complexity", 100) < 60:
            recommendations.append("Reduce code complexity by breaking down large functions")
        
        if factors.get("documentation", 0) < 50:
            recommendations.append("Add docstrings to functions and classes")
        
        if factors.get("code_size", 100) < 60:
            recommendations.append("Break down large functions into smaller, focused functions")
        
        if factors.get("structure", 100) < 60:
            recommendations.append("Reduce nesting depth and improve code structure")
        
        return recommendations

    def _generate_coverage_recommendations(
        self,
        total_functions: int,
        test_functions: int,
        coverage: float
    ) -> List[str]:
        """Generate test coverage recommendations."""
        recommendations = []
        
        if coverage < 50:
            recommendations.append("Add unit tests for all public functions")
        
        if test_functions < total_functions:
            recommendations.append(f"Add tests for {total_functions - test_functions} untested functions")
        
        if coverage < 80:
            recommendations.append("Aim for at least 80% test coverage")
        
        return recommendations

    def _generate_documentation_recommendations(
        self,
        function_coverage: float,
        class_coverage: float,
        module_coverage: float
    ) -> List[str]:
        """Generate documentation recommendations."""
        recommendations = []
        
        if function_coverage < 80:
            recommendations.append("Add docstrings to all functions")
        
        if class_coverage < 80:
            recommendations.append("Add docstrings to all classes")
        
        if module_coverage < 80:
            recommendations.append("Add module-level docstrings")
        
        return recommendations

    def _generate_dependency_recommendations(
        self,
        dependency_count: int,
        unique_imports: int
    ) -> List[str]:
        """Generate dependency recommendations."""
        recommendations = []
        
        if dependency_count > 50:
            recommendations.append("Consider reducing external dependencies")
        
        if unique_imports > 100:
            recommendations.append("Review and consolidate imports")
        
        return recommendations

    def _calculate_dependency_complexity(
        self,
        dependency_count: int,
        total_imports: int,
        unique_imports: int
    ) -> int:
        """Calculate dependency complexity score (0-100, higher = more complex)."""
        # Weighted factors
        dep_score = min(50, dependency_count * 2)
        import_score = min(30, (unique_imports / 10) * 2)
        total_score = min(20, (total_imports / 50) * 2)
        
        return int(dep_score + import_score + total_score)

    def _parse_requirements_txt(self, file_path: Path) -> List[str]:
        """Parse requirements.txt file."""
        dependencies = []
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith("#"):
                        # Extract package name (before ==, >=, etc.)
                        dep = line.split("==")[0].split(">=")[0].split("<=")[0].split(">")[0].split("<")[0].strip()
                        if dep:
                            dependencies.append(dep)
        except Exception:
            pass
        return dependencies

    def _parse_pyproject_toml(self, file_path: Path) -> List[str]:
        """Parse pyproject.toml file (simplified)."""
        dependencies = []
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                content = f.read()
                # Simple heuristic: look for dependency sections
                # Full implementation would use toml parser
                if "dependencies" in content or "requires" in content:
                    # Extract basic package names (simplified)
                    pass
        except Exception:
            pass
        return dependencies


# AST Visitor classes

class CodeStatisticsVisitor(ast.NodeVisitor):
    """Visitor to collect basic code statistics."""
    
    def __init__(self):
        self.lines_of_code = 0
        self.function_count = 0
        self.class_count = 0
        self.import_count = 0
        self.function_lengths = []
        self.class_sizes = []

    def visit_FunctionDef(self, node: ast.FunctionDef):
        self.function_count += 1
        if node.end_lineno and node.lineno:
            length = node.end_lineno - node.lineno
            self.function_lengths.append(length)
        self.generic_visit(node)

    def visit_ClassDef(self, node: ast.ClassDef):
        self.class_count += 1
        method_count = sum(1 for item in node.body if isinstance(item, ast.FunctionDef))
        self.class_sizes.append(method_count)
        self.generic_visit(node)

    def visit_Import(self, node: ast.Import):
        self.import_count += len(node.names)
        self.generic_visit(node)

    def visit_ImportFrom(self, node: ast.ImportFrom):
        self.import_count += len(node.names)
        self.generic_visit(node)

    @property
    def average_function_length(self) -> float:
        """Calculate average function length."""
        if not self.function_lengths:
            return 0.0
        return sum(self.function_lengths) / len(self.function_lengths)

    @property
    def average_class_size(self) -> float:
        """Calculate average class size."""
        if not self.class_sizes:
            return 0.0
        return sum(self.class_sizes) / len(self.class_sizes)


class CyclomaticComplexityVisitor(ast.NodeVisitor):
    """Visitor to calculate cyclomatic complexity."""
    
    def __init__(self):
        self.function_complexities = {}
        self.total_complexity = 0
        self.max_complexity = 0
        self.current_function = None

    def visit_FunctionDef(self, node: ast.FunctionDef):
        old_function = self.current_function
        self.current_function = node.name
        complexity = self._calculate_complexity(node)
        self.function_complexities[node.name] = complexity
        self.total_complexity += complexity
        self.max_complexity = max(self.max_complexity, complexity)
        self.generic_visit(node)
        self.current_function = old_function

    def _calculate_complexity(self, node: ast.AST) -> int:
        """Calculate cyclomatic complexity for a function."""
        complexity = 1  # Base complexity
        for child in ast.walk(node):
            if isinstance(child, (ast.If, ast.While, ast.For, ast.ExceptHandler, ast.And, ast.Or)):
                complexity += 1
        return complexity

    @property
    def average_complexity(self) -> float:
        """Calculate average complexity."""
        if not self.function_complexities:
            return 0.0
        return self.total_complexity / len(self.function_complexities)


class CognitiveComplexityVisitor(ast.NodeVisitor):
    """Visitor to calculate cognitive complexity."""
    
    def __init__(self):
        self.function_complexities = {}
        self.total_complexity = 0
        self.max_complexity = 0
        self.current_function = None
        self.nesting_level = 0

    def visit_FunctionDef(self, node: ast.FunctionDef):
        old_function = self.current_function
        old_nesting = self.nesting_level
        self.current_function = node.name
        self.nesting_level = 0
        complexity = self._calculate_cognitive_complexity(node)
        self.function_complexities[node.name] = complexity
        self.total_complexity += complexity
        self.max_complexity = max(self.max_complexity, complexity)
        self.generic_visit(node)
        self.current_function = old_function
        self.nesting_level = old_nesting

    def visit_If(self, node: ast.If):
        self.nesting_level += 1
        self.generic_visit(node)
        self.nesting_level -= 1

    def visit_While(self, node: ast.While):
        self.nesting_level += 1
        self.generic_visit(node)
        self.nesting_level -= 1

    def visit_For(self, node: ast.For):
        self.nesting_level += 1
        self.generic_visit(node)
        self.nesting_level -= 1

    def _calculate_cognitive_complexity(self, node: ast.AST) -> int:
        """Calculate cognitive complexity (penalizes nesting more)."""
        complexity = 0
        for child in ast.walk(node):
            if isinstance(child, (ast.If, ast.While, ast.For, ast.ExceptHandler)):
                complexity += 1 + self.nesting_level
        return complexity

    @property
    def average_complexity(self) -> float:
        """Calculate average complexity."""
        if not self.function_complexities:
            return 0.0
        return self.total_complexity / len(self.function_complexities)


class AlgorithmicComplexityVisitor(ast.NodeVisitor):
    """Visitor to analyze algorithmic complexity."""
    
    def __init__(self):
        self.time_complexity = "O(1)"
        self.space_complexity = "O(1)"
        self.nested_loops = 0
        self.max_loop_depth = 0
        self._loop_depth = 0

    def visit_For(self, node: ast.For):
        self._loop_depth += 1
        self.max_loop_depth = max(self.max_loop_depth, self._loop_depth)
        self.nested_loops += 1
        self.generic_visit(node)
        self._loop_depth -= 1

    def visit_While(self, node: ast.While):
        self._loop_depth += 1
        self.max_loop_depth = max(self.max_loop_depth, self._loop_depth)
        self.nested_loops += 1
        self.generic_visit(node)
        self._loop_depth -= 1

    def visit(self, node: ast.AST):
        """Update complexity based on loop depth."""
        super().visit(node)
        
        if self.max_loop_depth == 0:
            self.time_complexity = "O(1)"
        elif self.max_loop_depth == 1:
            self.time_complexity = "O(n)"
        elif self.max_loop_depth == 2:
            self.time_complexity = "O(n²)"
        else:
            self.time_complexity = f"O(n^{self.max_loop_depth})"


class TestCoverageVisitor(ast.NodeVisitor):
    """Visitor to analyze code structure for test coverage."""
    
    def __init__(self):
        self.function_count = 0
        self.class_count = 0
        self.method_count = 0

    def visit_FunctionDef(self, node: ast.FunctionDef):
        if not any(isinstance(parent, ast.ClassDef) for parent in ast.walk(node)):
            self.function_count += 1
        else:
            self.method_count += 1
        self.generic_visit(node)

    def visit_ClassDef(self, node: ast.ClassDef):
        self.class_count += 1
        self.generic_visit(node)


class TestStructureVisitor(ast.NodeVisitor):
    """Visitor to analyze test structure."""
    
    def __init__(self):
        self.test_function_count = 0
        self.test_class_count = 0

    def visit_FunctionDef(self, node: ast.FunctionDef):
        if node.name.startswith("test_"):
            self.test_function_count += 1
        self.generic_visit(node)

    def visit_ClassDef(self, node: ast.ClassDef):
        if node.name.startswith("Test") or "Test" in node.name:
            self.test_class_count += 1
        self.generic_visit(node)


class DocumentationCoverageVisitor(ast.NodeVisitor):
    """Visitor to measure documentation coverage."""
    
    def __init__(self):
        self.total_functions = 0
        self.documented_functions = 0
        self.total_classes = 0
        self.documented_classes = 0
        self.total_modules = 1  # Assume at least one module
        self.documented_modules = 0

    def visit_FunctionDef(self, node: ast.FunctionDef):
        self.total_functions += 1
        if ast.get_docstring(node):
            self.documented_functions += 1
        self.generic_visit(node)

    def visit_ClassDef(self, node: ast.ClassDef):
        self.total_classes += 1
        if ast.get_docstring(node):
            self.documented_classes += 1
        self.generic_visit(node)

    def visit_Module(self, node: ast.Module):
        if ast.get_docstring(node):
            self.documented_modules = 1
        self.generic_visit(node)


class ImportComplexityVisitor(ast.NodeVisitor):
    """Visitor to analyze import complexity."""
    
    def __init__(self):
        self.imports = []

    def visit_Import(self, node: ast.Import):
        for alias in node.names:
            self.imports.append(alias.name)
        self.generic_visit(node)

    def visit_ImportFrom(self, node: ast.ImportFrom):
        if node.module:
            for alias in node.names:
                self.imports.append(f"{node.module}.{alias.name}")
        self.generic_visit(node)

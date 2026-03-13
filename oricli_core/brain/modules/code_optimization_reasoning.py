from __future__ import annotations
"""
Code Optimization Reasoning Module

Identify optimization opportunities, reason about performance implications,
suggest algorithmic improvements, analyze complexity, and propose refactoring strategies.

This module is part of Oricli-Alpha's Python LLM capabilities, enabling
reasoning about code optimization and performance improvements.
"""

import ast
import sys
from collections import defaultdict
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple

from oricli_core.brain.base_module import BaseBrainModule, ModuleMetadata
from oricli_core.exceptions import InvalidParameterError


class CodeOptimizationReasoningModule(BaseBrainModule):
    """
    Reason about code optimization opportunities.
    
    Provides:
    - Optimization opportunity identification
    - Performance analysis
    - Algorithmic improvement suggestions
    - Complexity analysis
    - Refactoring proposals
    """

    def __init__(self):
        """Initialize the code optimization reasoning module."""
        super().__init__()
        self._behavior_reasoning = None
        self._complexity_detector = None

    @property
    def metadata(self) -> ModuleMetadata:
        """Return module metadata."""
        return ModuleMetadata(
            name="code_optimization_reasoning",
            version="1.0.0",
            description=(
                "Reason about code optimization: identify opportunities, "
                "analyze performance, suggest improvements, and propose refactoring"
            ),
            operations=[
                "identify_optimizations",
                "analyze_complexity",
                "suggest_improvements",
                "reason_about_performance",
                "propose_refactoring",
                "analyze_bottlenecks",
            ],
            dependencies=[],
            model_required=False,
        )

    def initialize(self) -> bool:
        """Initialize the module."""
        # Try to load related modules
        try:
            from oricli_core.brain.registry import ModuleRegistry
            self._behavior_reasoning = ModuleRegistry.get_module("program_behavior_reasoning")
            self._complexity_detector = ModuleRegistry.get_module("query_complexity")
        except Exception:
            pass
        
        return True

    def execute(self, operation: str, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute a code optimization reasoning operation.
        
        Args:
            operation: Operation name
            params: Operation parameters
            
        Returns:
            Operation result dictionary
            
        Raises:
            ValueError: If operation is unknown
            InvalidParameterError: If parameters are invalid
        """
        if operation == "identify_optimizations":
            code = params.get("code", "")
            if not code:
                raise InvalidParameterError("code", "", "Code cannot be empty")
            return self.identify_optimizations(code)
        
        elif operation == "analyze_complexity":
            code = params.get("code", "")
            if not code:
                raise InvalidParameterError("code", "", "Code cannot be empty")
            return self.analyze_complexity(code)
        
        elif operation == "suggest_improvements":
            code = params.get("code", "")
            if not code:
                raise InvalidParameterError("code", "", "Code cannot be empty")
            return self.suggest_improvements(code)
        
        elif operation == "reason_about_performance":
            code = params.get("code", "")
            if not code:
                raise InvalidParameterError("code", "", "Code cannot be empty")
            return self.reason_about_performance(code)
        
        elif operation == "propose_refactoring":
            code = params.get("code", "")
            if not code:
                raise InvalidParameterError("code", "", "Code cannot be empty")
            return self.propose_refactoring(code)
        
        elif operation == "analyze_bottlenecks":
            code = params.get("code", "")
            if not code:
                raise InvalidParameterError("code", "", "Code cannot be empty")
            return self.analyze_bottlenecks(code)
        
        else:
            raise InvalidParameterError(
                parameter="operation",
                value=str(operation),
                reason="Unknown operation",
            )

    def identify_optimizations(self, code: str) -> Dict[str, Any]:
        """
        Identify optimization opportunities in code.
        
        Args:
            code: Python code to analyze
            
        Returns:
            Dictionary containing identified optimizations
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

        identifier = OptimizationIdentifier()
        identifier.visit(tree)

        return {
            "success": True,
            "optimizations": identifier.optimizations,
            "optimization_count": len(identifier.optimizations),
            "priority_optimizations": identifier.priority_optimizations,
        }

    def analyze_complexity(self, code: str) -> Dict[str, Any]:
        """
        Analyze computational complexity.
        
        Args:
            code: Python code to analyze
            
        Returns:
            Dictionary containing complexity analysis
        """
        if self._behavior_reasoning:
            try:
                return self._behavior_reasoning.execute("analyze_complexity", {"code": code})
            except Exception:
                pass

        # Fallback: basic analysis
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
            "complexity_analysis": analyzer.complexity_analysis,
        }

    def suggest_improvements(self, code: str) -> Dict[str, Any]:
        """
        Suggest code improvements.
        
        Args:
            code: Python code to analyze
            
        Returns:
            Dictionary containing improvement suggestions
        """
        optimizations = self.identify_optimizations(code)
        if not optimizations.get("success"):
            return optimizations

        suggestions = []
        for opt in optimizations.get("optimizations", []):
            suggestions.append({
                "type": opt.get("type"),
                "description": opt.get("description"),
                "suggestion": opt.get("suggestion"),
                "impact": opt.get("impact", "medium"),
                "line": opt.get("line"),
            })

        return {
            "success": True,
            "suggestions": suggestions,
            "total_suggestions": len(suggestions),
        }

    def reason_about_performance(self, code: str) -> Dict[str, Any]:
        """
        Reason about code performance.
        
        Args:
            code: Python code to analyze
            
        Returns:
            Dictionary containing performance analysis
        """
        complexity = self.analyze_complexity(code)
        optimizations = self.identify_optimizations(code)

        performance_analysis = {
            "complexity": complexity.get("time_complexity", "unknown"),
            "optimization_opportunities": len(optimizations.get("optimizations", [])),
            "bottlenecks": [],
            "performance_rating": "good",
        }

        # Identify bottlenecks
        if complexity.get("nested_loops", 0) > 2:
            performance_analysis["bottlenecks"].append({
                "type": "nested_loops",
                "severity": "high",
                "description": "Deeply nested loops can cause performance issues",
            })
            performance_analysis["performance_rating"] = "poor"

        if optimizations.get("optimization_count", 0) > 5:
            performance_analysis["performance_rating"] = "needs_improvement"

        return {
            "success": True,
            "performance_analysis": performance_analysis,
            "complexity": complexity,
            "optimizations": optimizations,
        }

    def propose_refactoring(self, code: str) -> Dict[str, Any]:
        """
        Propose refactoring strategies.
        
        Args:
            code: Python code to analyze
            
        Returns:
            Dictionary containing refactoring proposals
        """
        optimizations = self.identify_optimizations(code)
        if not optimizations.get("success"):
            return optimizations

        refactorings = []
        for opt in optimizations.get("optimizations", []):
            if opt.get("type") in ["extract_function", "simplify_logic", "reduce_complexity"]:
                refactorings.append({
                    "type": opt.get("type"),
                    "description": opt.get("description"),
                    "proposed_change": opt.get("suggestion"),
                    "rationale": opt.get("rationale", "Improves code quality and performance"),
                    "line": opt.get("line"),
                })

        return {
            "success": True,
            "refactorings": refactorings,
            "total_refactorings": len(refactorings),
        }

    def analyze_bottlenecks(self, code: str) -> Dict[str, Any]:
        """
        Analyze performance bottlenecks.
        
        Args:
            code: Python code to analyze
            
        Returns:
            Dictionary containing bottleneck analysis
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

        analyzer = BottleneckAnalyzer()
        analyzer.visit(tree)

        return {
            "success": True,
            "bottlenecks": analyzer.bottlenecks,
            "bottleneck_count": len(analyzer.bottlenecks),
            "critical_bottlenecks": analyzer.critical_bottlenecks,
        }


# Analysis Classes

class OptimizationIdentifier(ast.NodeVisitor):
    """AST visitor for identifying optimization opportunities."""

    def __init__(self):
        """Initialize optimization identifier."""
        self.optimizations: List[Dict[str, Any]] = []
        self.priority_optimizations: List[Dict[str, Any]] = []

    def visit_For(self, node: ast.For) -> None:
        """Visit for loop."""
        # Check for inefficient patterns
        if isinstance(node.iter, ast.Call):
            if isinstance(node.iter.func, ast.Name) and node.iter.func.id == "range":
                # Check if range() could be optimized
                pass
        
        # Check for nested loops
        nested_loops = sum(1 for n in ast.walk(node) if isinstance(n, (ast.For, ast.While)))
        if nested_loops > 1:
            self.optimizations.append({
                "type": "nested_loops",
                "line": node.lineno,
                "description": f"Nested loops at line {node.lineno}",
                "suggestion": "Consider using list comprehensions or vectorized operations",
                "impact": "high",
                "rationale": "Nested loops can be slow for large datasets",
            })
            self.priority_optimizations.append(self.optimizations[-1])

        super().visit(node)

    def visit_ListComp(self, node: ast.ListComp) -> None:
        """Visit list comprehension - this is already optimized."""
        pass

    def visit_If(self, node: ast.If) -> None:
        """Visit if statement."""
        # Check for redundant conditions
        if len(node.body) == 0 and len(node.orelse) == 0:
            self.optimizations.append({
                "type": "empty_if",
                "line": node.lineno,
                "description": f"Empty if statement at line {node.lineno}",
                "suggestion": "Remove empty if statement",
                "impact": "low",
            })

        super().visit(node)

    def visit_Call(self, node: ast.Call) -> None:
        """Visit function call."""
        if isinstance(node.func, ast.Name):
            func_name = node.func.id
            
            # Check for inefficient built-in usage
            if func_name == "list" and len(node.args) == 1:
                arg = node.args[0]
                if isinstance(arg, ast.Call) and isinstance(arg.func, ast.Name):
                    if arg.func.id == "range":
                        self.optimizations.append({
                            "type": "list_range",
                            "line": node.lineno,
                            "description": f"list(range()) at line {node.lineno}",
                            "suggestion": "Consider using list(range()) only when necessary",
                            "impact": "medium",
                        })

        super().visit(node)

    def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
        """Visit function definition."""
        # Check function complexity
        complexity = self._calculate_function_complexity(node)
        if complexity > 10:
            self.optimizations.append({
                "type": "extract_function",
                "line": node.lineno,
                "description": f"Complex function '{node.name}' at line {node.lineno}",
                "suggestion": f"Consider breaking down function '{node.name}' into smaller functions",
                "impact": "medium",
                "rationale": "High complexity makes code harder to maintain and optimize",
            })

        super().visit(node)

    def _calculate_function_complexity(self, node: ast.FunctionDef) -> int:
        """Calculate cyclomatic complexity of function."""
        complexity = 1  # Base complexity
        
        for child in ast.walk(node):
            if isinstance(child, (ast.If, ast.While, ast.For, ast.ExceptHandler)):
                complexity += 1
            elif isinstance(child, ast.BoolOp):
                complexity += len(child.values) - 1
        
        return complexity


class ComplexityAnalyzer(ast.NodeVisitor):
    """AST visitor for complexity analysis."""

    def __init__(self):
        """Initialize complexity analyzer."""
        self.time_complexity: str = "O(1)"
        self.space_complexity: str = "O(1)"
        self.nested_loops: int = 0
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


class BottleneckAnalyzer(ast.NodeVisitor):
    """AST visitor for bottleneck analysis."""

    def __init__(self):
        """Initialize bottleneck analyzer."""
        self.bottlenecks: List[Dict[str, Any]] = []
        self.critical_bottlenecks: List[Dict[str, Any]] = []

    def visit_For(self, node: ast.For) -> None:
        """Visit for loop."""
        # Check for nested loops (potential bottleneck)
        nested_count = sum(1 for n in ast.walk(node) if isinstance(n, (ast.For, ast.While)))
        if nested_count > 2:
            bottleneck = {
                "type": "nested_loops",
                "line": node.lineno,
                "severity": "critical",
                "description": f"Deeply nested loops at line {node.lineno}",
                "impact": "High performance impact",
            }
            self.bottlenecks.append(bottleneck)
            self.critical_bottlenecks.append(bottleneck)

        super().visit(node)

    def visit_Call(self, node: ast.Call) -> None:
        """Visit function call."""
        if isinstance(node.func, ast.Name):
            func_name = node.func.id
            
            # Check for known slow operations
            slow_operations = ["eval", "exec", "compile"]
            if func_name in slow_operations:
                bottleneck = {
                    "type": "slow_operation",
                    "line": node.lineno,
                    "severity": "high",
                    "description": f"Slow operation '{func_name}' at line {node.lineno}",
                    "impact": "Can significantly impact performance",
                }
                self.bottlenecks.append(bottleneck)

        super().visit(node)

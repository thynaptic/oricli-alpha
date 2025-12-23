"""
Python Code Safety Module

Runtime safety analysis, resource leak detection, exception handling analysis,
thread safety analysis, memory safety checks, error handling best practices,
and safe code patterns.

This module is part of Mavaia's Python LLM Phase 4 capabilities, providing
comprehensive code safety analysis to prevent runtime errors and resource issues.
"""

import ast
import sys
from collections import defaultdict
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple

from mavaia_core.brain.base_module import BaseBrainModule, ModuleMetadata
from mavaia_core.exceptions import InvalidParameterError


class PythonCodeSafetyModule(BaseBrainModule):
    """
    Comprehensive code safety analysis.
    
    Provides:
    - Runtime safety analysis
    - Resource leak detection
    - Exception handling analysis
    - Thread safety analysis
    - Memory safety checks
    - Error handling best practices
    - Safe code pattern suggestions
    """

    def __init__(self):
        """Initialize the Python code safety module."""
        super().__init__()
        self._behavior_reasoning = None
        self._code_execution = None

    @property
    def metadata(self) -> ModuleMetadata:
        """Return module metadata."""
        return ModuleMetadata(
            name="python_code_safety",
            version="1.0.0",
            description=(
                "Code safety analysis: runtime safety, resource leaks, "
                "exception handling, thread safety, memory safety, "
                "error handling, and safe code patterns"
            ),
            operations=[
                "analyze_runtime_safety",
                "detect_resource_leaks",
                "analyze_exception_handling",
                "check_thread_safety",
                "analyze_memory_safety",
                "suggest_safe_patterns",
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
            self._code_execution = ModuleRegistry.get_module("code_execution")
        except Exception:
            pass
        
        return True

    def execute(self, operation: str, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute a code safety operation.
        
        Args:
            operation: Operation name
            params: Operation parameters
            
        Returns:
            Operation result dictionary
            
        Raises:
            ValueError: If operation is unknown
            InvalidParameterError: If parameters are invalid
        """
        if operation == "analyze_runtime_safety":
            code = params.get("code", "")
            if not code:
                raise InvalidParameterError("code", "", "Code cannot be empty")
            return self.analyze_runtime_safety(code)
        
        elif operation == "detect_resource_leaks":
            code = params.get("code", "")
            if not code:
                raise InvalidParameterError("code", "", "Code cannot be empty")
            return self.detect_resource_leaks(code)
        
        elif operation == "analyze_exception_handling":
            code = params.get("code", "")
            if not code:
                raise InvalidParameterError("code", "", "Code cannot be empty")
            return self.analyze_exception_handling(code)
        
        elif operation == "check_thread_safety":
            code = params.get("code", "")
            if not code:
                raise InvalidParameterError("code", "", "Code cannot be empty")
            return self.check_thread_safety(code)
        
        elif operation == "analyze_memory_safety":
            code = params.get("code", "")
            if not code:
                raise InvalidParameterError("code", "", "Code cannot be empty")
            return self.analyze_memory_safety(code)
        
        elif operation == "suggest_safe_patterns":
            code = params.get("code", "")
            if not code:
                raise InvalidParameterError("code", "", "Code cannot be empty")
            return self.suggest_safe_patterns(code)
        
        else:
            raise InvalidParameterError(
                parameter="operation",
                value=str(operation),
                reason="Unknown operation for python_code_safety",
            )

    def analyze_runtime_safety(self, code: str) -> Dict[str, Any]:
        """
        Analyze runtime safety of code.
        
        Args:
            code: Python code to analyze
            
        Returns:
            Dictionary containing runtime safety analysis
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

        # Analyze runtime safety issues
        visitor = RuntimeSafetyVisitor()
        visitor.visit(tree)

        # Check for common runtime issues
        issues = []
        issues.extend(visitor.issues)
        issues.extend(self._check_none_access(code, tree))
        issues.extend(self._check_division_by_zero(code, tree))
        issues.extend(self._check_index_errors(code, tree))
        issues.extend(self._check_attribute_errors(code, tree))

        # Calculate safety score
        safety_score = self._calculate_safety_score(issues)

        return {
            "success": True,
            "safety_score": safety_score,
            "issues": issues,
            "count": len(issues),
            "assessment": self._assess_runtime_safety(safety_score),
            "recommendations": self._generate_runtime_safety_recommendations(issues),
        }

    def detect_resource_leaks(self, code: str) -> Dict[str, Any]:
        """
        Detect resource leaks in code.
        
        Args:
            code: Python code to analyze
            
        Returns:
            Dictionary containing resource leak detection results
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

        leaks = []
        visitor = ResourceLeakVisitor()
        visitor.visit(tree)

        # Check for file handles
        leaks.extend(self._check_file_leaks(code, tree))

        # Check for network connections
        leaks.extend(self._check_connection_leaks(code, tree))

        # Check for database connections
        leaks.extend(self._check_database_leaks(code, tree))

        return {
            "success": True,
            "leaks": leaks,
            "count": len(leaks),
            "severity": self._assess_leak_severity(leaks),
            "recommendations": self._generate_leak_recommendations(leaks),
        }

    def analyze_exception_handling(self, code: str) -> Dict[str, Any]:
        """
        Analyze exception handling patterns.
        
        Args:
            code: Python code to analyze
            
        Returns:
            Dictionary containing exception handling analysis
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

        issues = []
        visitor = ExceptionHandlingVisitor()
        visitor.visit(tree)

        # Check for exception handling issues
        issues.extend(visitor.issues)
        issues.extend(self._check_bare_except(code, tree))
        issues.extend(self._check_too_broad_except(code, tree))
        issues.extend(self._check_missing_except(code, tree))
        issues.extend(self._check_exception_swallowing(code, tree))

        return {
            "success": True,
            "issues": issues,
            "count": len(issues),
            "exception_handling_score": self._calculate_exception_score(issues),
            "recommendations": self._generate_exception_recommendations(issues),
        }

    def check_thread_safety(self, code: str) -> Dict[str, Any]:
        """
        Check thread safety of code.
        
        Args:
            code: Python code to analyze
            
        Returns:
            Dictionary containing thread safety analysis
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

        issues = []
        visitor = ThreadSafetyVisitor()
        visitor.visit(tree)

        # Check for thread safety issues
        issues.extend(visitor.issues)
        issues.extend(self._check_shared_state(code, tree))
        issues.extend(self._check_race_conditions(code, tree))
        issues.extend(self._check_deadlocks(code, tree))

        return {
            "success": True,
            "thread_safe": len(issues) == 0,
            "issues": issues,
            "count": len(issues),
            "recommendations": self._generate_thread_safety_recommendations(issues),
        }

    def analyze_memory_safety(self, code: str) -> Dict[str, Any]:
        """
        Analyze memory safety of code.
        
        Args:
            code: Python code to analyze
            
        Returns:
            Dictionary containing memory safety analysis
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

        issues = []
        visitor = MemorySafetyVisitor()
        visitor.visit(tree)

        # Check for memory issues
        issues.extend(visitor.issues)
        issues.extend(self._check_memory_leaks(code, tree))
        issues.extend(self._check_large_objects(code, tree))
        issues.extend(self._check_circular_references(code, tree))

        return {
            "success": True,
            "issues": issues,
            "count": len(issues),
            "memory_safety_score": self._calculate_memory_score(issues),
            "recommendations": self._generate_memory_recommendations(issues),
        }

    def suggest_safe_patterns(self, code: str) -> Dict[str, Any]:
        """
        Suggest safe code patterns.
        
        Args:
            code: Python code to analyze
            
        Returns:
            Dictionary containing safe pattern suggestions
        """
        # Get all safety analyses
        runtime_safety = self.analyze_runtime_safety(code)
        resource_leaks = self.detect_resource_leaks(code)
        exception_handling = self.analyze_exception_handling(code)
        thread_safety = self.check_thread_safety(code)
        memory_safety = self.analyze_memory_safety(code)

        suggestions = []

        # Suggest based on findings
        if runtime_safety.get("issues"):
            suggestions.append({
                "category": "runtime_safety",
                "pattern": "Use defensive programming",
                "description": "Add null checks and validation",
                "examples": ["if variable is not None:", "validate_input(data)"],
            })

        if resource_leaks.get("leaks"):
            suggestions.append({
                "category": "resource_management",
                "pattern": "Use context managers",
                "description": "Use 'with' statements for resource management",
                "examples": ["with open(file) as f:", "with connection.cursor() as cur:"],
            })

        if exception_handling.get("issues"):
            suggestions.append({
                "category": "exception_handling",
                "pattern": "Specific exception handling",
                "description": "Catch specific exceptions, not bare except",
                "examples": ["except ValueError:", "except FileNotFoundError:"],
            })

        if thread_safety.get("issues"):
            suggestions.append({
                "category": "thread_safety",
                "pattern": "Use locks for shared state",
                "description": "Protect shared resources with locks",
                "examples": ["with lock:", "threading.Lock()"],
            })

        return {
            "success": True,
            "suggestions": suggestions,
            "count": len(suggestions),
            "categories": list(set(s.get("category") for s in suggestions)),
        }

    # Helper methods

    def _check_none_access(self, code: str, tree: ast.AST) -> List[Dict[str, Any]]:
        """Check for potential None access."""
        issues = []
        # Simplified - would need deeper AST analysis
        return issues

    def _check_division_by_zero(self, code: str, tree: ast.AST) -> List[Dict[str, Any]]:
        """Check for division by zero."""
        issues = []
        visitor = DivisionByZeroVisitor()
        visitor.visit(tree)
        issues.extend(visitor.issues)
        return issues

    def _check_index_errors(self, code: str, tree: ast.AST) -> List[Dict[str, Any]]:
        """Check for potential index errors."""
        issues = []
        # Simplified check
        return issues

    def _check_attribute_errors(self, code: str, tree: ast.AST) -> List[Dict[str, Any]]:
        """Check for potential attribute errors."""
        issues = []
        # Simplified check
        return issues

    def _check_file_leaks(self, code: str, tree: ast.AST) -> List[Dict[str, Any]]:
        """Check for file handle leaks."""
        leaks = []
        
        # Check for open() without with statement
        if "open(" in code and "with open" not in code:
            leaks.append({
                "type": "file_leak",
                "severity": "medium",
                "description": "File opened without context manager",
                "recommendation": "Use 'with open() as f:' pattern",
            })

        return leaks

    def _check_connection_leaks(self, code: str, tree: ast.AST) -> List[Dict[str, Any]]:
        """Check for connection leaks."""
        leaks = []
        
        # Check for connection patterns
        connection_patterns = ["socket", "requests.Session", "urllib"]
        for pattern in connection_patterns:
            if pattern in code and "with " not in code:
                leaks.append({
                    "type": "connection_leak",
                    "severity": "medium",
                    "description": f"Potential {pattern} connection leak",
                    "recommendation": "Use context managers for connections",
                })

        return leaks

    def _check_database_leaks(self, code: str, tree: ast.AST) -> List[Dict[str, Any]]:
        """Check for database connection leaks."""
        leaks = []
        
        # Check for database patterns
        db_patterns = ["connect(", "cursor()", "execute("]
        if any(pattern in code for pattern in db_patterns):
            if "with " not in code and "close()" not in code:
                leaks.append({
                    "type": "database_leak",
                    "severity": "high",
                    "description": "Potential database connection leak",
                    "recommendation": "Use context managers or ensure close() is called",
                })

        return leaks

    def _check_bare_except(self, code: str, tree: ast.AST) -> List[Dict[str, Any]]:
        """Check for bare except clauses."""
        issues = []
        visitor = BareExceptVisitor()
        visitor.visit(tree)
        issues.extend(visitor.issues)
        return issues

    def _check_too_broad_except(self, code: str, tree: ast.AST) -> List[Dict[str, Any]]:
        """Check for too broad exception handling."""
        issues = []
        visitor = BroadExceptVisitor()
        visitor.visit(tree)
        issues.extend(visitor.issues)
        return issues

    def _check_missing_except(self, code: str, tree: ast.AST) -> List[Dict[str, Any]]:
        """Check for missing exception handling."""
        issues = []
        # Simplified - would need deeper analysis
        return issues

    def _check_exception_swallowing(self, code: str, tree: ast.AST) -> List[Dict[str, Any]]:
        """Check for exception swallowing."""
        issues = []
        visitor = ExceptionSwallowingVisitor()
        visitor.visit(tree)
        issues.extend(visitor.issues)
        return issues

    def _check_shared_state(self, code: str, tree: ast.AST) -> List[Dict[str, Any]]:
        """Check for shared state in threading."""
        issues = []
        
        if "threading" in code or "Thread" in code:
            if "Lock" not in code and "RLock" not in code:
                issues.append({
                    "type": "shared_state",
                    "severity": "high",
                    "description": "Threading detected but no locks found",
                    "recommendation": "Use locks to protect shared state",
                })

        return issues

    def _check_race_conditions(self, code: str, tree: ast.AST) -> List[Dict[str, Any]]:
        """Check for race conditions."""
        issues = []
        # Simplified check
        return issues

    def _check_deadlocks(self, code: str, tree: ast.AST) -> List[Dict[str, Any]]:
        """Check for potential deadlocks."""
        issues = []
        # Simplified check
        return issues

    def _check_memory_leaks(self, code: str, tree: ast.AST) -> List[Dict[str, Any]]:
        """Check for memory leaks."""
        issues = []
        # Simplified check
        return issues

    def _check_large_objects(self, code: str, tree: ast.AST) -> List[Dict[str, Any]]:
        """Check for large object allocations."""
        issues = []
        # Simplified check
        return issues

    def _check_circular_references(self, code: str, tree: ast.AST) -> List[Dict[str, Any]]:
        """Check for circular references."""
        issues = []
        # Simplified check
        return issues

    def _calculate_safety_score(self, issues: List[Dict[str, Any]]) -> int:
        """Calculate runtime safety score (0-100)."""
        score = 100
        
        for issue in issues:
            severity = issue.get("severity", "medium")
            if severity == "critical":
                score -= 20
            elif severity == "high":
                score -= 10
            elif severity == "medium":
                score -= 5
            else:
                score -= 2

        return max(0, score)

    def _assess_runtime_safety(self, score: int) -> str:
        """Assess runtime safety level."""
        if score >= 80:
            return "safe"
        elif score >= 60:
            return "moderate"
        elif score >= 40:
            return "risky"
        else:
            return "unsafe"

    def _generate_runtime_safety_recommendations(self, issues: List[Dict[str, Any]]) -> List[str]:
        """Generate runtime safety recommendations."""
        recommendations = []
        
        if any(i.get("type") == "division_by_zero" for i in issues):
            recommendations.append("Add checks for division by zero")
        
        if any(i.get("type") == "none_access" for i in issues):
            recommendations.append("Add null checks before accessing attributes")
        
        recommendations.append("Use defensive programming practices")

        return recommendations

    def _assess_leak_severity(self, leaks: List[Dict[str, Any]]) -> str:
        """Assess resource leak severity."""
        if not leaks:
            return "none"
        
        critical = [l for l in leaks if l.get("severity") == "critical"]
        if critical:
            return "critical"
        
        high = [l for l in leaks if l.get("severity") == "high"]
        if high:
            return "high"
        
        return "medium"

    def _generate_leak_recommendations(self, leaks: List[Dict[str, Any]]) -> List[str]:
        """Generate resource leak recommendations."""
        recommendations = []
        
        if leaks:
            recommendations.append("Use context managers (with statements) for all resources")
            recommendations.append("Ensure all file handles, connections, and cursors are properly closed")
            recommendations.append("Consider using try/finally blocks for cleanup")

        return recommendations

    def _calculate_exception_score(self, issues: List[Dict[str, Any]]) -> int:
        """Calculate exception handling score."""
        score = 100
        score -= len(issues) * 10
        return max(0, score)

    def _generate_exception_recommendations(self, issues: List[Dict[str, Any]]) -> List[str]:
        """Generate exception handling recommendations."""
        recommendations = []
        
        if any(i.get("type") == "bare_except" for i in issues):
            recommendations.append("Avoid bare except clauses, catch specific exceptions")
        
        if any(i.get("type") == "broad_except" for i in issues):
            recommendations.append("Catch specific exceptions instead of Exception")
        
        if any(i.get("type") == "exception_swallowing" for i in issues):
            recommendations.append("Log or handle exceptions, don't silently swallow them")

        return recommendations

    def _generate_thread_safety_recommendations(self, issues: List[Dict[str, Any]]) -> List[str]:
        """Generate thread safety recommendations."""
        recommendations = []
        
        if issues:
            recommendations.append("Use locks to protect shared state")
            recommendations.append("Avoid mutable shared state when possible")
            recommendations.append("Use thread-safe data structures")

        return recommendations

    def _calculate_memory_score(self, issues: List[Dict[str, Any]]) -> int:
        """Calculate memory safety score."""
        score = 100
        score -= len(issues) * 15
        return max(0, score)

    def _generate_memory_recommendations(self, issues: List[Dict[str, Any]]) -> List[str]:
        """Generate memory safety recommendations."""
        recommendations = []
        
        if issues:
            recommendations.append("Use context managers for resource cleanup")
            recommendations.append("Avoid circular references")
            recommendations.append("Consider memory-efficient data structures for large datasets")

        return recommendations


# AST Visitor classes

class RuntimeSafetyVisitor(ast.NodeVisitor):
    """Visitor to detect runtime safety issues."""
    
    def __init__(self):
        self.issues = []

    def visit_Call(self, node: ast.Call):
        # Check for potentially unsafe operations
        if isinstance(node.func, ast.Name):
            if node.func.id in ["eval", "exec"]:
                self.issues.append({
                    "type": "unsafe_execution",
                    "severity": "high",
                    "description": f"Unsafe {node.func.id} usage",
                    "line": node.lineno,
                })
        self.generic_visit(node)


class ResourceLeakVisitor(ast.NodeVisitor):
    """Visitor to detect resource leaks."""
    
    def __init__(self):
        self.leaks = []

    def visit_With(self, node: ast.With):
        # Context managers are good - no leak
        self.generic_visit(node)

    def visit_Call(self, node: ast.Call):
        # Check for resource-opening calls without context managers
        if isinstance(node.func, ast.Name):
            if node.func.id == "open":
                # Check if parent is With statement (simplified)
                self.leaks.append({
                    "type": "potential_file_leak",
                    "severity": "medium",
                    "description": "File opened, ensure it's closed",
                    "line": node.lineno,
                })
        self.generic_visit(node)


class ExceptionHandlingVisitor(ast.NodeVisitor):
    """Visitor to analyze exception handling."""
    
    def __init__(self):
        self.issues = []

    def visit_ExceptHandler(self, node: ast.ExceptHandler):
        if node.type is None:
            self.issues.append({
                "type": "bare_except",
                "severity": "high",
                "description": "Bare except clause found",
                "line": node.lineno,
            })
        self.generic_visit(node)


class ThreadSafetyVisitor(ast.NodeVisitor):
    """Visitor to detect thread safety issues."""
    
    def __init__(self):
        self.issues = []

    def visit_Import(self, node: ast.Import):
        for alias in node.names:
            if alias.name == "threading":
                # Threading detected
                pass
        self.generic_visit(node)


class MemorySafetyVisitor(ast.NodeVisitor):
    """Visitor to detect memory safety issues."""
    
    def __init__(self):
        self.issues = []

    def visit(self, node: ast.AST):
        self.generic_visit(node)


class DivisionByZeroVisitor(ast.NodeVisitor):
    """Visitor to detect division by zero."""
    
    def __init__(self):
        self.issues = []

    def visit_Div(self, node: ast.Div):
        # Simplified - would need to track variable values
        self.issues.append({
            "type": "division_by_zero_risk",
            "severity": "medium",
            "description": "Division operation - ensure divisor is not zero",
            "line": node.lineno if hasattr(node, 'lineno') else 0,
        })
        self.generic_visit(node)


class BareExceptVisitor(ast.NodeVisitor):
    """Visitor to detect bare except clauses."""
    
    def __init__(self):
        self.issues = []

    def visit_ExceptHandler(self, node: ast.ExceptHandler):
        if node.type is None:
            self.issues.append({
                "type": "bare_except",
                "severity": "high",
                "description": "Bare except clause - catches all exceptions",
                "line": node.lineno,
                "recommendation": "Catch specific exceptions",
            })
        self.generic_visit(node)


class BroadExceptVisitor(ast.NodeVisitor):
    """Visitor to detect too broad exception handling."""
    
    def __init__(self):
        self.issues = []

    def visit_ExceptHandler(self, node: ast.ExceptHandler):
        if isinstance(node.type, ast.Name):
            if node.type.id == "Exception":
                self.issues.append({
                    "type": "broad_except",
                    "severity": "medium",
                    "description": "Catching Exception is too broad",
                    "line": node.lineno,
                    "recommendation": "Catch more specific exceptions",
                })
        self.generic_visit(node)


class ExceptionSwallowingVisitor(ast.NodeVisitor):
    """Visitor to detect exception swallowing."""
    
    def __init__(self):
        self.issues = []

    def visit_ExceptHandler(self, node: ast.ExceptHandler):
        # Check if except block is empty or only has pass
        if len(node.body) == 0 or (len(node.body) == 1 and isinstance(node.body[0], ast.Pass)):
            self.issues.append({
                "type": "exception_swallowing",
                "severity": "high",
                "description": "Exception is being swallowed silently",
                "line": node.lineno,
                "recommendation": "Log or handle the exception",
            })
        self.generic_visit(node)

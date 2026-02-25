from __future__ import annotations
"""
Python Code Review Module

Automated code review with reasoning, code quality scoring, best practice
enforcement, style consistency checking, architecture pattern compliance,
design pattern detection, code smell identification, and technical debt analysis.

This module is part of Mavaia's Python LLM Phase 4 capabilities, providing
intelligent code reviews that understand context, not just syntax.
"""

import ast
import sys
from collections import defaultdict
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple

from mavaia_core.brain.base_module import BaseBrainModule, ModuleMetadata
from mavaia_core.exceptions import InvalidParameterError


class PythonCodeReviewModule(BaseBrainModule):
    """
    Automated code review with deep reasoning capabilities.
    
    Provides:
    - Comprehensive code review with reasoning
    - Code quality scoring (0-100)
    - Best practice enforcement
    - Code smell detection
    - Technical debt analysis
    - Architecture pattern compliance
    - Design pattern recognition
    - Improvement suggestions
    """

    def __init__(self):
        """Initialize the Python code review module."""
        super().__init__()
        self._optimization_reasoning = None
        self._code_to_code_reasoning = None
        self._semantic_understanding = None
        self._code_analysis = None
        self._behavior_reasoning = None

    @property
    def metadata(self) -> ModuleMetadata:
        """Return module metadata."""
        return ModuleMetadata(
            name="python_code_review",
            version="1.0.0",
            description=(
                "Automated code review with reasoning: quality scoring, "
                "best practices, code smells, technical debt, architecture "
                "patterns, design patterns, and improvement suggestions"
            ),
            operations=[
                "review_code",
                "score_code_quality",
                "check_best_practices",
                "detect_code_smells",
                "analyze_technical_debt",
                "check_architecture_patterns",
                "detect_design_patterns",
                "suggest_improvements",
            ],
            dependencies=[],
            model_required=False,
        )

    def initialize(self) -> bool:
        """Initialize the module."""
        # Try to load related modules
        try:
            from mavaia_core.brain.registry import ModuleRegistry
            self._optimization_reasoning = ModuleRegistry.get_module("code_optimization_reasoning")
            self._code_to_code_reasoning = ModuleRegistry.get_module("code_to_code_reasoning")
            self._semantic_understanding = ModuleRegistry.get_module("python_semantic_understanding")
            self._code_analysis = ModuleRegistry.get_module("code_analysis")
            self._behavior_reasoning = ModuleRegistry.get_module("program_behavior_reasoning")
        except Exception:
            pass
        
        return True

    def execute(self, operation: str, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute a code review operation.
        
        Args:
            operation: Operation name
            params: Operation parameters
            
        Returns:
            Operation result dictionary
            
        Raises:
            ValueError: If operation is unknown
            InvalidParameterError: If parameters are invalid
        """
        if operation == "review_code":
            code = params.get("code", "")
            review_type = params.get("review_type", "comprehensive")
            if not code:
                raise InvalidParameterError("code", "", "Code cannot be empty")
            return self.review_code(code, review_type)
        
        elif operation == "score_code_quality":
            code = params.get("code", "")
            if not code:
                raise InvalidParameterError("code", "", "Code cannot be empty")
            return self.score_code_quality(code)
        
        elif operation == "check_best_practices":
            code = params.get("code", "")
            if not code:
                raise InvalidParameterError("code", "", "Code cannot be empty")
            return self.check_best_practices(code)
        
        elif operation == "detect_code_smells":
            code = params.get("code", "")
            if not code:
                raise InvalidParameterError("code", "", "Code cannot be empty")
            return self.detect_code_smells(code)
        
        elif operation == "analyze_technical_debt":
            code = params.get("code", "")
            project = params.get("project", None)
            if not code:
                raise InvalidParameterError("code", "", "Code cannot be empty")
            return self.analyze_technical_debt(code, project)
        
        elif operation == "check_architecture_patterns":
            code = params.get("code", "")
            if not code:
                raise InvalidParameterError("code", "", "Code cannot be empty")
            return self.check_architecture_patterns(code)
        
        elif operation == "detect_design_patterns":
            code = params.get("code", "")
            if not code:
                raise InvalidParameterError("code", "", "Code cannot be empty")
            return self.detect_design_patterns(code)
        
        elif operation == "suggest_improvements":
            code = params.get("code", "")
            focus = params.get("focus", "all")
            if not code:
                raise InvalidParameterError("code", "", "Code cannot be empty")
            return self.suggest_improvements(code, focus)
        
        else:
            raise InvalidParameterError(
                parameter="operation",
                value=str(operation),
                reason="Unknown operation",
            )

    def review_code(self, code: str, review_type: str = "comprehensive") -> Dict[str, Any]:
        """
        Perform comprehensive code review.
        
        Args:
            code: Python code to review
            review_type: Type of review (comprehensive, quick, security, performance, style)
            
        Returns:
            Dictionary containing review results with issues, suggestions, and scores
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

        review_result = {
            "success": True,
            "review_type": review_type,
            "issues": [],
            "suggestions": [],
            "quality_score": 0,
            "summary": "",
        }

        # Perform different types of reviews based on review_type
        if review_type in ("comprehensive", "quality"):
            quality_result = self.score_code_quality(code)
            review_result["quality_score"] = quality_result.get("score", 0)
            review_result["issues"].extend(quality_result.get("issues", []))

        if review_type in ("comprehensive", "best_practices"):
            best_practices = self.check_best_practices(code)
            review_result["issues"].extend(best_practices.get("violations", []))

        if review_type in ("comprehensive", "smells"):
            smells = self.detect_code_smells(code)
            review_result["issues"].extend(smells.get("smells", []))

        if review_type in ("comprehensive", "architecture"):
            architecture = self.check_architecture_patterns(code)
            review_result["issues"].extend(architecture.get("violations", []))

        if review_type in ("comprehensive", "design"):
            design_patterns = self.detect_design_patterns(code)
            review_result["suggestions"].extend(design_patterns.get("suggestions", []))

        # Get improvement suggestions
        improvements = self.suggest_improvements(code, "all")
        review_result["suggestions"].extend(improvements.get("improvements", []))

        # Generate summary
        issue_count = len(review_result["issues"])
        suggestion_count = len(review_result["suggestions"])
        quality = review_result["quality_score"]
        
        if quality >= 90:
            summary = f"Excellent code quality (score: {quality}). {suggestion_count} minor suggestions."
        elif quality >= 75:
            summary = f"Good code quality (score: {quality}). {issue_count} issues found, {suggestion_count} suggestions."
        elif quality >= 60:
            summary = f"Moderate code quality (score: {quality}). {issue_count} issues need attention, {suggestion_count} suggestions."
        else:
            summary = f"Code quality needs improvement (score: {quality}). {issue_count} significant issues, {suggestion_count} suggestions."

        review_result["summary"] = summary

        return review_result

    def score_code_quality(self, code: str) -> Dict[str, Any]:
        """
        Score code quality on a scale of 0-100.
        
        Args:
            code: Python code to score
            
        Returns:
            Dictionary containing quality score, breakdown, and issues
        """
        try:
            tree = ast.parse(code)
        except SyntaxError:
            return {
                "score": 0,
                "issues": [{"type": "syntax_error", "severity": "critical", "message": "Code has syntax errors"}],
                "breakdown": {},
            }

        score = 100
        issues = []
        breakdown = {
            "syntax": 100,
            "complexity": 100,
            "style": 100,
            "documentation": 100,
            "best_practices": 100,
        }

        # Check syntax (already passed if we got here)
        # Syntax is valid, no deduction

        # Analyze complexity
        complexity_issues = self._analyze_complexity(code, tree)
        if complexity_issues:
            complexity_score = max(0, 100 - len(complexity_issues) * 10)
            breakdown["complexity"] = complexity_score
            score = min(score, complexity_score)
            issues.extend(complexity_issues)

        # Check style
        style_issues = self._check_style(code, tree)
        if style_issues:
            style_score = max(0, 100 - len(style_issues) * 5)
            breakdown["style"] = style_score
            score = min(score, style_score)
            issues.extend(style_issues)

        # Check documentation
        doc_issues = self._check_documentation(code, tree)
        if doc_issues:
            doc_score = max(0, 100 - len(doc_issues) * 15)
            breakdown["documentation"] = doc_score
            score = min(score, doc_score)
            issues.extend(doc_issues)

        # Check best practices
        best_practices = self.check_best_practices(code)
        violations = best_practices.get("violations", [])
        if violations:
            bp_score = max(0, 100 - len(violations) * 8)
            breakdown["best_practices"] = bp_score
            score = min(score, bp_score)
            issues.extend(violations)

        # Calculate weighted average
        final_score = int(
            breakdown["syntax"] * 0.1 +
            breakdown["complexity"] * 0.3 +
            breakdown["style"] * 0.2 +
            breakdown["documentation"] * 0.2 +
            breakdown["best_practices"] * 0.2
        )

        return {
            "score": final_score,
            "breakdown": breakdown,
            "issues": issues,
        }

    def check_best_practices(self, code: str) -> Dict[str, Any]:
        """
        Check code against Python best practices.
        
        Args:
            code: Python code to check
            
        Returns:
            Dictionary containing violations and recommendations
        """
        try:
            tree = ast.parse(code)
        except SyntaxError:
            return {
                "violations": [{"type": "syntax_error", "severity": "critical"}],
                "score": 0,
            }

        violations = []
        visitor = BestPracticesVisitor()
        visitor.visit(tree)

        # Check for common violations
        violations.extend(visitor.violations)

        # Check for magic numbers
        violations.extend(self._check_magic_numbers(code, tree))

        # Check for long functions
        violations.extend(self._check_function_length(tree))

        # Check for deep nesting
        violations.extend(self._check_nesting_depth(tree))

        # Check for unused imports
        violations.extend(self._check_unused_imports(code, tree))

        score = max(0, 100 - len(violations) * 10)

        return {
            "violations": violations,
            "score": score,
            "recommendations": self._generate_best_practice_recommendations(violations),
        }

    def detect_code_smells(self, code: str) -> Dict[str, Any]:
        """
        Detect code smells in Python code.
        
        Args:
            code: Python code to analyze
            
        Returns:
            Dictionary containing detected smells with severity and suggestions
        """
        try:
            tree = ast.parse(code)
        except SyntaxError:
            return {
                "smells": [{"type": "syntax_error", "severity": "critical"}],
                "count": 1,
            }

        smells = []
        visitor = CodeSmellVisitor()
        visitor.visit(tree)

        # Detect common code smells
        smells.extend(visitor.smells)
        smells.extend(self._detect_long_method(code, tree))
        smells.extend(self._detect_large_class(tree))
        smells.extend(self._detect_duplicate_code(code, tree))
        smells.extend(self._detect_feature_envy(code, tree))
        smells.extend(self._detect_data_clumps(code, tree))
        smells.extend(self._detect_long_parameter_list(tree))

        # Categorize by severity
        critical = [s for s in smells if s.get("severity") == "critical"]
        high = [s for s in smells if s.get("severity") == "high"]
        medium = [s for s in smells if s.get("severity") == "medium"]
        low = [s for s in smells if s.get("severity") == "low"]

        return {
            "smells": smells,
            "count": len(smells),
            "by_severity": {
                "critical": len(critical),
                "high": len(high),
                "medium": len(medium),
                "low": len(low),
            },
            "critical": critical,
            "high": high,
            "medium": medium,
            "low": low,
        }

    def analyze_technical_debt(self, code: str, project: Optional[str] = None) -> Dict[str, Any]:
        """
        Analyze technical debt in code.
        
        Args:
            code: Python code to analyze
            project: Optional project context
            
        Returns:
            Dictionary containing technical debt analysis
        """
        try:
            tree = ast.parse(code)
        except SyntaxError:
            return {
                "debt_score": 100,
                "issues": [{"type": "syntax_error", "severity": "critical"}],
            }

        debt_items = []
        debt_score = 0

        # Analyze code smells (technical debt indicators)
        smells = self.detect_code_smells(code)
        critical_smells = smells.get("critical", [])
        high_smells = smells.get("high", [])

        debt_score += len(critical_smells) * 20
        debt_score += len(high_smells) * 10

        for smell in critical_smells + high_smells:
            debt_items.append({
                "type": "code_smell",
                "severity": smell.get("severity"),
                "description": smell.get("description"),
                "location": smell.get("location"),
                "estimated_fix_time": smell.get("estimated_fix_time", "unknown"),
            })

        # Check for TODO/FIXME comments (explicit technical debt)
        todo_items = self._find_todo_comments(code)
        debt_score += len(todo_items) * 5
        debt_items.extend(todo_items)

        # Check for deprecated patterns
        deprecated = self._check_deprecated_patterns(code, tree)
        debt_score += len(deprecated) * 15
        debt_items.extend(deprecated)

        # Check for missing tests
        if self._code_analysis:
            try:
                # Check if there are test files nearby (heuristic)
                has_tests = self._check_test_coverage(code)
                if not has_tests:
                    debt_items.append({
                        "type": "missing_tests",
                        "severity": "medium",
                        "description": "No test coverage detected",
                        "estimated_fix_time": "2-4 hours",
                    })
                    debt_score += 10
            except Exception:
                pass

        # Normalize debt score (0-100, higher = more debt)
        debt_score = min(100, debt_score)

        return {
            "debt_score": debt_score,
            "debt_level": self._categorize_debt_level(debt_score),
            "items": debt_items,
            "count": len(debt_items),
            "estimated_fix_time": self._estimate_total_fix_time(debt_items),
        }

    def check_architecture_patterns(self, code: str) -> Dict[str, Any]:
        """
        Check code against architecture patterns.
        
        Args:
            code: Python code to check
            
        Returns:
            Dictionary containing architecture pattern compliance
        """
        try:
            tree = ast.parse(code)
        except SyntaxError:
            return {
                "violations": [{"type": "syntax_error", "severity": "critical"}],
                "patterns_detected": [],
            }

        violations = []
        patterns_detected = []

        # Check for layered architecture
        if self._detect_layered_architecture(tree):
            patterns_detected.append({
                "pattern": "layered_architecture",
                "confidence": "medium",
                "description": "Code appears to follow layered architecture",
            })

        # Check for MVC pattern
        if self._detect_mvc_pattern(tree):
            patterns_detected.append({
                "pattern": "mvc",
                "confidence": "medium",
                "description": "Code appears to follow MVC pattern",
            })

        # Check for repository pattern
        if self._detect_repository_pattern(tree):
            patterns_detected.append({
                "pattern": "repository",
                "confidence": "medium",
                "description": "Code appears to use repository pattern",
            })

        # Check for service pattern
        if self._detect_service_pattern(tree):
            patterns_detected.append({
                "pattern": "service",
                "confidence": "medium",
                "description": "Code appears to use service pattern",
            })

        # Check for violations
        violations.extend(self._check_separation_of_concerns(tree))
        violations.extend(self._check_dependency_inversion(tree))

        return {
            "violations": violations,
            "patterns_detected": patterns_detected,
            "compliance_score": max(0, 100 - len(violations) * 15),
        }

    def detect_design_patterns(self, code: str) -> Dict[str, Any]:
        """
        Detect design patterns in code.
        
        Args:
            code: Python code to analyze
            
        Returns:
            Dictionary containing detected design patterns
        """
        try:
            tree = ast.parse(code)
        except SyntaxError:
            return {
                "patterns": [],
                "suggestions": [],
            }

        patterns = []
        suggestions = []

        # Detect Singleton pattern
        if self._detect_singleton_pattern(tree):
            patterns.append({
                "pattern": "singleton",
                "confidence": "medium",
                "description": "Singleton pattern detected",
            })

        # Detect Factory pattern
        if self._detect_factory_pattern(tree):
            patterns.append({
                "pattern": "factory",
                "confidence": "medium",
                "description": "Factory pattern detected",
            })

        # Detect Observer pattern
        if self._detect_observer_pattern(tree):
            patterns.append({
                "pattern": "observer",
                "confidence": "medium",
                "description": "Observer pattern detected",
            })

        # Detect Strategy pattern
        if self._detect_strategy_pattern(tree):
            patterns.append({
                "pattern": "strategy",
                "confidence": "medium",
                "description": "Strategy pattern detected",
            })

        # Detect Decorator pattern
        if self._detect_decorator_pattern(tree):
            patterns.append({
                "pattern": "decorator",
                "confidence": "high",
                "description": "Decorator pattern detected (Python native)",
            })

        # Generate suggestions for missing patterns that could improve code
        suggestions.extend(self._suggest_design_patterns(code, tree))

        return {
            "patterns": patterns,
            "count": len(patterns),
            "suggestions": suggestions,
        }

    def suggest_improvements(self, code: str, focus: str = "all") -> Dict[str, Any]:
        """
        Suggest code improvements.
        
        Args:
            code: Python code to analyze
            focus: Focus area (all, performance, readability, maintainability, security)
            
        Returns:
            Dictionary containing improvement suggestions
        """
        improvements = []

        # Get suggestions from related modules
        if focus in ("all", "performance") and self._optimization_reasoning:
            try:
                opt_result = self._optimization_reasoning.execute("suggest_improvements", {"code": code})
                improvements.extend(opt_result.get("improvements", []))
            except Exception:
                pass

        # Get code smells (improvement opportunities)
        if focus in ("all", "maintainability"):
            smells = self.detect_code_smells(code)
            for smell in smells.get("smells", []):
                improvements.append({
                    "type": "code_smell_fix",
                    "priority": smell.get("severity"),
                    "description": f"Fix {smell.get('type')}: {smell.get('description')}",
                    "location": smell.get("location"),
                })

        # Get best practice violations
        if focus in ("all", "readability", "maintainability"):
            best_practices = self.check_best_practices(code)
            for violation in best_practices.get("violations", []):
                improvements.append({
                    "type": "best_practice",
                    "priority": violation.get("severity", "medium"),
                    "description": violation.get("message", ""),
                    "location": violation.get("location"),
                })

        # Categorize by priority
        high_priority = [i for i in improvements if i.get("priority") in ("critical", "high")]
        medium_priority = [i for i in improvements if i.get("priority") == "medium"]
        low_priority = [i for i in improvements if i.get("priority") == "low"]

        return {
            "improvements": improvements,
            "count": len(improvements),
            "by_priority": {
                "high": len(high_priority),
                "medium": len(medium_priority),
                "low": len(low_priority),
            },
            "high_priority": high_priority,
            "medium_priority": medium_priority,
            "low_priority": low_priority,
        }

    # Helper methods for code analysis

    def _analyze_complexity(self, code: str, tree: ast.AST) -> List[Dict[str, Any]]:
        """Analyze code complexity."""
        issues = []
        visitor = ComplexityVisitor()
        visitor.visit(tree)

        if visitor.max_complexity > 15:
            issues.append({
                "type": "high_complexity",
                "severity": "high",
                "message": f"Function has complexity {visitor.max_complexity} (recommended: < 15)",
                "location": visitor.complex_function,
            })

        return issues

    def _check_style(self, code: str, tree: ast.AST) -> List[Dict[str, Any]]:
        """Check code style."""
        issues = []
        lines = code.split('\n')

        # Check line length
        for i, line in enumerate(lines, 1):
            if len(line) > 100:
                issues.append({
                    "type": "long_line",
                    "severity": "low",
                    "message": f"Line {i} exceeds 100 characters",
                    "location": f"line {i}",
                })

        return issues

    def _check_documentation(self, code: str, tree: ast.AST) -> List[Dict[str, Any]]:
        """Check documentation coverage."""
        issues = []
        visitor = DocumentationVisitor()
        visitor.visit(tree)

        for func in visitor.undocumented_functions:
            issues.append({
                "type": "missing_docstring",
                "severity": "medium",
                "message": f"Function '{func}' is missing a docstring",
                "location": func,
            })

        for cls in visitor.undocumented_classes:
            issues.append({
                "type": "missing_docstring",
                "severity": "medium",
                "message": f"Class '{cls}' is missing a docstring",
                "location": cls,
            })

        return issues

    def _check_magic_numbers(self, code: str, tree: ast.AST) -> List[Dict[str, Any]]:
        """Check for magic numbers."""
        issues = []
        visitor = MagicNumberVisitor()
        visitor.visit(tree)

        for num, location in visitor.magic_numbers:
            issues.append({
                "type": "magic_number",
                "severity": "low",
                "message": f"Magic number {num} found",
                "location": location,
            })

        return issues

    def _check_function_length(self, tree: ast.AST) -> List[Dict[str, Any]]:
        """Check for long functions."""
        issues = []
        visitor = FunctionLengthVisitor()
        visitor.visit(tree)

        for func_name, length in visitor.long_functions:
            issues.append({
                "type": "long_function",
                "severity": "medium",
                "message": f"Function '{func_name}' is {length} lines (recommended: < 50)",
                "location": func_name,
            })

        return issues

    def _check_nesting_depth(self, tree: ast.AST) -> List[Dict[str, Any]]:
        """Check for deep nesting."""
        issues = []
        visitor = NestingDepthVisitor()
        visitor.visit(tree)

        for func_name, depth in visitor.deep_nesting:
            issues.append({
                "type": "deep_nesting",
                "severity": "medium",
                "message": f"Function '{func_name}' has nesting depth {depth} (recommended: < 4)",
                "location": func_name,
            })

        return issues

    def _check_unused_imports(self, code: str, tree: ast.AST) -> List[Dict[str, Any]]:
        """Check for unused imports."""
        issues = []
        visitor = ImportVisitor()
        visitor.visit(tree)

        # Simple heuristic: check if imports are used
        # This is a simplified version - full implementation would track usage
        return issues

    def _generate_best_practice_recommendations(self, violations: List[Dict[str, Any]]) -> List[str]:
        """Generate recommendations from violations."""
        recommendations = []
        violation_types = set(v.get("type") for v in violations)

        if "magic_number" in violation_types:
            recommendations.append("Replace magic numbers with named constants")
        if "long_function" in violation_types:
            recommendations.append("Break down long functions into smaller, focused functions")
        if "deep_nesting" in violation_types:
            recommendations.append("Reduce nesting depth by extracting functions or using early returns")

        return recommendations

    def _detect_long_method(self, code: str, tree: ast.AST) -> List[Dict[str, Any]]:
        """Detect long method code smell."""
        smells = []
        visitor = FunctionLengthVisitor()
        visitor.visit(tree)

        for func_name, length in visitor.long_functions:
            if length > 50:
                smells.append({
                    "type": "long_method",
                    "severity": "high",
                    "description": f"Method '{func_name}' is too long ({length} lines)",
                    "location": func_name,
                    "estimated_fix_time": "1-2 hours",
                })

        return smells

    def _detect_large_class(self, tree: ast.AST) -> List[Dict[str, Any]]:
        """Detect large class code smell."""
        smells = []
        visitor = ClassSizeVisitor()
        visitor.visit(tree)

        for class_name, size in visitor.large_classes:
            if size > 20:
                smells.append({
                    "type": "large_class",
                    "severity": "high",
                    "description": f"Class '{class_name}' has too many methods ({size})",
                    "location": class_name,
                    "estimated_fix_time": "2-4 hours",
                })

        return smells

    def _detect_duplicate_code(self, code: str, tree: ast.AST) -> List[Dict[str, Any]]:
        """Detect duplicate code."""
        smells = []
        # Simplified - full implementation would use code embeddings for similarity
        return smells

    def _detect_feature_envy(self, code: str, tree: ast.AST) -> List[Dict[str, Any]]:
        """Detect feature envy code smell."""
        smells = []
        # Simplified - full implementation would analyze method calls
        return smells

    def _detect_data_clumps(self, code: str, tree: ast.AST) -> List[Dict[str, Any]]:
        """Detect data clumps code smell."""
        smells = []
        # Simplified - full implementation would analyze parameter groups
        return smells

    def _detect_long_parameter_list(self, tree: ast.AST) -> List[Dict[str, Any]]:
        """Detect long parameter list code smell."""
        smells = []
        visitor = ParameterListVisitor()
        visitor.visit(tree)

        for func_name, param_count in visitor.long_parameter_lists:
            if param_count > 5:
                smells.append({
                    "type": "long_parameter_list",
                    "severity": "medium",
                    "description": f"Function '{func_name}' has {param_count} parameters (recommended: < 5)",
                    "location": func_name,
                    "estimated_fix_time": "1 hour",
                })

        return smells

    def _find_todo_comments(self, code: str) -> List[Dict[str, Any]]:
        """Find TODO/FIXME comments."""
        items = []
        lines = code.split('\n')

        for i, line in enumerate(lines, 1):
            line_lower = line.lower()
            if 'todo' in line_lower or 'fixme' in line_lower:
                items.append({
                    "type": "todo_comment",
                    "severity": "low",
                    "description": line.strip(),
                    "location": f"line {i}",
                    "estimated_fix_time": "unknown",
                })

        return items

    def _check_deprecated_patterns(self, code: str, tree: ast.AST) -> List[Dict[str, Any]]:
        """Check for deprecated patterns."""
        items = []
        # Check for Python 2 patterns
        if 'print ' in code and ('print' + '(') not in code:
            items.append({
                "type": "deprecated_pattern",
                "severity": "high",
                "description": "Python 2 print statement detected",
                "location": "code",
                "estimated_fix_time": "30 minutes",
            })

        return items

    def _check_test_coverage(self, code: str) -> bool:
        """Check if code has test coverage (heuristic)."""
        # Simplified - would check for test files in project
        return False

    def _categorize_debt_level(self, score: int) -> str:
        """Categorize technical debt level."""
        if score >= 80:
            return "critical"
        elif score >= 60:
            return "high"
        elif score >= 40:
            return "medium"
        elif score >= 20:
            return "low"
        else:
            return "minimal"

    def _estimate_total_fix_time(self, items: List[Dict[str, Any]]) -> str:
        """Estimate total fix time for technical debt items."""
        # Simplified estimation
        hours = len(items) * 2
        if hours < 8:
            return f"{hours} hours"
        else:
            days = hours / 8
            return f"{days:.1f} days"

    def _detect_layered_architecture(self, tree: ast.AST) -> bool:
        """Detect layered architecture pattern."""
        # Simplified detection
        return False

    def _detect_mvc_pattern(self, tree: ast.AST) -> bool:
        """Detect MVC pattern."""
        # Simplified detection
        return False

    def _detect_repository_pattern(self, tree: ast.AST) -> bool:
        """Detect repository pattern."""
        # Simplified detection
        return False

    def _detect_service_pattern(self, tree: ast.AST) -> bool:
        """Detect service pattern."""
        # Simplified detection
        return False

    def _check_separation_of_concerns(self, tree: ast.AST) -> List[Dict[str, Any]]:
        """Check separation of concerns."""
        violations = []
        # Simplified check
        return violations

    def _check_dependency_inversion(self, tree: ast.AST) -> List[Dict[str, Any]]:
        """Check dependency inversion principle."""
        violations = []
        # Simplified check
        return violations

    def _detect_singleton_pattern(self, tree: ast.AST) -> bool:
        """Detect Singleton pattern."""
        # Simplified detection
        return False

    def _detect_factory_pattern(self, tree: ast.AST) -> bool:
        """Detect Factory pattern."""
        # Simplified detection
        return False

    def _detect_observer_pattern(self, tree: ast.AST) -> bool:
        """Detect Observer pattern."""
        # Simplified detection
        return False

    def _detect_strategy_pattern(self, tree: ast.AST) -> bool:
        """Detect Strategy pattern."""
        # Simplified detection
        return False

    def _detect_decorator_pattern(self, tree: ast.AST) -> bool:
        """Detect Decorator pattern."""
        visitor = DecoratorVisitor()
        visitor.visit(tree)
        return len(visitor.decorators) > 0

    def _suggest_design_patterns(self, code: str, tree: ast.AST) -> List[Dict[str, Any]]:
        """Suggest design patterns that could improve code."""
        suggestions = []
        # Simplified suggestions
        return suggestions


# AST Visitor classes for code analysis

class BestPracticesVisitor(ast.NodeVisitor):
    """Visitor to check best practices."""
    
    def __init__(self):
        self.violations = []

    def visit_FunctionDef(self, node: ast.FunctionDef):
        # Check for functions without type hints (simplified)
        if not node.args.args:
            pass  # No parameters to check
        self.generic_visit(node)


class ComplexityVisitor(ast.NodeVisitor):
    """Visitor to analyze complexity."""
    
    def __init__(self):
        self.max_complexity = 0
        self.complex_function = None

    def visit_FunctionDef(self, node: ast.FunctionDef):
        complexity = self._calculate_complexity(node)
        if complexity > self.max_complexity:
            self.max_complexity = complexity
            self.complex_function = node.name
        self.generic_visit(node)

    def _calculate_complexity(self, node: ast.AST) -> int:
        """Calculate cyclomatic complexity."""
        complexity = 1  # Base complexity
        for child in ast.walk(node):
            if isinstance(child, (ast.If, ast.While, ast.For, ast.ExceptHandler)):
                complexity += 1
        return complexity


class DocumentationVisitor(ast.NodeVisitor):
    """Visitor to check documentation."""
    
    def __init__(self):
        self.undocumented_functions = []
        self.undocumented_classes = []

    def visit_FunctionDef(self, node: ast.FunctionDef):
        if not ast.get_docstring(node):
            self.undocumented_functions.append(node.name)
        self.generic_visit(node)

    def visit_ClassDef(self, node: ast.ClassDef):
        if not ast.get_docstring(node):
            self.undocumented_classes.append(node.name)
        self.generic_visit(node)


class MagicNumberVisitor(ast.NodeVisitor):
    """Visitor to find magic numbers."""
    
    def __init__(self):
        self.magic_numbers = []

    def visit_Constant(self, node: ast.Constant):
        if isinstance(node.value, (int, float)) and node.value not in (0, 1, -1):
            self.magic_numbers.append((node.value, f"line {node.lineno}"))
        self.generic_visit(node)


class FunctionLengthVisitor(ast.NodeVisitor):
    """Visitor to check function length."""
    
    def __init__(self):
        self.long_functions = []

    def visit_FunctionDef(self, node: ast.FunctionDef):
        if node.end_lineno and node.lineno:
            length = node.end_lineno - node.lineno
            if length > 30:
                self.long_functions.append((node.name, length))
        self.generic_visit(node)


class NestingDepthVisitor(ast.NodeVisitor):
    """Visitor to check nesting depth."""
    
    def __init__(self):
        self.deep_nesting = []
        self.current_depth = 0
        self.current_function = None

    def visit_FunctionDef(self, node: ast.FunctionDef):
        old_function = self.current_function
        old_depth = self.current_depth
        self.current_function = node.name
        self.current_depth = 0
        self.generic_visit(node)
        if self.current_depth > 4:
            self.deep_nesting.append((node.name, self.current_depth))
        self.current_function = old_function
        self.current_depth = old_depth

    def visit_If(self, node: ast.If):
        self.current_depth += 1
        self.generic_visit(node)
        self.current_depth -= 1

    def visit_While(self, node: ast.While):
        self.current_depth += 1
        self.generic_visit(node)
        self.current_depth -= 1

    def visit_For(self, node: ast.For):
        self.current_depth += 1
        self.generic_visit(node)
        self.current_depth -= 1


class ImportVisitor(ast.NodeVisitor):
    """Visitor to analyze imports."""
    
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


class ClassSizeVisitor(ast.NodeVisitor):
    """Visitor to check class size."""
    
    def __init__(self):
        self.large_classes = []

    def visit_ClassDef(self, node: ast.ClassDef):
        method_count = sum(1 for item in node.body if isinstance(item, ast.FunctionDef))
        if method_count > 10:
            self.large_classes.append((node.name, method_count))
        self.generic_visit(node)


class ParameterListVisitor(ast.NodeVisitor):
    """Visitor to check parameter list length."""
    
    def __init__(self):
        self.long_parameter_lists = []

    def visit_FunctionDef(self, node: ast.FunctionDef):
        param_count = len(node.args.args)
        if param_count > 5:
            self.long_parameter_lists.append((node.name, param_count))
        self.generic_visit(node)


class DecoratorVisitor(ast.NodeVisitor):
    """Visitor to find decorators."""
    
    def __init__(self):
        self.decorators = []

    def visit_FunctionDef(self, node: ast.FunctionDef):
        if node.decorator_list:
            self.decorators.extend([d.id if isinstance(d, ast.Name) else str(d) for d in node.decorator_list])
        self.generic_visit(node)

    def visit_ClassDef(self, node: ast.ClassDef):
        if node.decorator_list:
            self.decorators.extend([d.id if isinstance(d, ast.Name) else str(d) for d in node.decorator_list])
        self.generic_visit(node)

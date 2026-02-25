from __future__ import annotations
"""
Python Code Explanation Module

Explain code in natural language, answer questions about code, explain code
to different audiences (beginners, experts), generate code walkthroughs,
create code tutorials, explain design decisions, and clarify complex code sections.

This module is part of Mavaia's Python LLM Phase 4 capabilities, providing
intelligent code explanation and communication that adapts to different audiences.
"""

import ast
import sys
from collections import defaultdict
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple

from mavaia_core.brain.base_module import BaseBrainModule, ModuleMetadata
from mavaia_core.exceptions import InvalidParameterError


class PythonCodeExplanationModule(BaseBrainModule):
    """
    Intelligent code explanation and communication.
    
    Provides:
    - Code explanation in natural language
    - Q&A about code
    - Code walkthroughs
    - Tutorial generation
    - Design decision explanations
    - Complex section clarification
    """

    def __init__(self):
        """Initialize the Python code explanation module."""
        super().__init__()
        self._semantic_understanding = None
        self._code_analysis = None
        self._reasoning = None

    @property
    def metadata(self) -> ModuleMetadata:
        """Return module metadata."""
        return ModuleMetadata(
            name="python_code_explanation",
            version="1.0.0",
            description=(
                "Intelligent code explanation: natural language explanations, "
                "Q&A about code, walkthroughs, tutorials, design explanations, "
                "and complexity clarification"
            ),
            operations=[
                "explain_code",
                "answer_code_question",
                "create_walkthrough",
                "explain_design_decision",
                "clarify_complex_section",
                "generate_tutorial",
            ],
            dependencies=[],
            model_required=False,
        )

    def initialize(self) -> bool:
        """Initialize the module."""
        # Try to load related modules
        try:
            from mavaia_core.brain.registry import ModuleRegistry
            self._semantic_understanding = ModuleRegistry.get_module("python_semantic_understanding")
            self._code_analysis = ModuleRegistry.get_module("code_analysis")
            self._reasoning = ModuleRegistry.get_module("reasoning")
        except Exception:
            pass
        
        return True

    def execute(self, operation: str, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute a code explanation operation.
        
        Args:
            operation: Operation name
            params: Operation parameters
            
        Returns:
            Operation result dictionary
            
        Raises:
            ValueError: If operation is unknown
            InvalidParameterError: If parameters are invalid
        """
        if operation == "explain_code":
            code = params.get("code", "")
            audience = params.get("audience", "developer")
            detail_level = params.get("detail_level", "medium")
            if not code:
                raise InvalidParameterError("code", "", "Code cannot be empty")
            return self.explain_code(code, audience, detail_level)
        
        elif operation == "answer_code_question":
            code = params.get("code", "")
            question = params.get("question", "")
            if not code:
                raise InvalidParameterError("code", "", "Code cannot be empty")
            if not question:
                raise InvalidParameterError("question", "", "Question cannot be empty")
            return self.answer_code_question(code, question)
        
        elif operation == "create_walkthrough":
            code = params.get("code", "")
            steps = params.get("steps", None)
            if not code:
                raise InvalidParameterError("code", "", "Code cannot be empty")
            return self.create_walkthrough(code, steps)
        
        elif operation == "explain_design_decision":
            code = params.get("code", "")
            context = params.get("context", {})
            if not code:
                raise InvalidParameterError("code", "", "Code cannot be empty")
            return self.explain_design_decision(code, context)
        
        elif operation == "clarify_complex_section":
            code = params.get("code", "")
            section = params.get("section", None)
            if not code:
                raise InvalidParameterError("code", "", "Code cannot be empty")
            return self.clarify_complex_section(code, section)
        
        elif operation == "generate_tutorial":
            code = params.get("code", "")
            topic = params.get("topic", None)
            if not code:
                raise InvalidParameterError("code", "", "Code cannot be empty")
            return self.generate_tutorial(code, topic)
        
        else:
            raise InvalidParameterError(
                parameter="operation",
                value=str(operation),
                reason="Unknown operation",
            )

    def explain_code(self, code: str, audience: str = "developer", detail_level: str = "medium") -> Dict[str, Any]:
        """
        Explain code in natural language.
        
        Args:
            code: Python code to explain
            audience: Target audience (beginner, developer, expert)
            detail_level: Detail level (simple, medium, detailed)
            
        Returns:
            Dictionary containing code explanation
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

        # Analyze code structure
        visitor = CodeExplanationVisitor()
        visitor.visit(tree)

        # Generate explanation based on audience and detail level
        explanation = self._generate_explanation(code, tree, visitor, audience, detail_level)

        return {
            "success": True,
            "audience": audience,
            "detail_level": detail_level,
            "explanation": explanation,
            "structure": {
                "functions": list(visitor.functions.keys()),
                "classes": list(visitor.classes.keys()),
                "complexity": visitor.complexity_level,
                "lines_of_code": visitor.lines_of_code,
            },
        }

    def answer_code_question(self, code: str, question: str) -> Dict[str, Any]:
        """
        Answer a question about code.
        
        Args:
            code: Python code to analyze
            question: Question about the code
            
        Returns:
            Dictionary containing answer to the question
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

        # Analyze code structure
        visitor = CodeExplanationVisitor()
        visitor.visit(tree)

        # Analyze question and generate answer
        answer = self._answer_question(code, tree, visitor, question)

        return {
            "success": True,
            "question": question,
            "answer": answer,
            "code_references": self._extract_code_references(question, visitor),
        }

    def create_walkthrough(self, code: str, steps: Optional[int] = None) -> Dict[str, Any]:
        """
        Create a step-by-step walkthrough of code.
        
        Args:
            code: Python code to walk through
            steps: Number of steps (auto-determined if None)
            
        Returns:
            Dictionary containing walkthrough steps
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

        # Analyze code execution flow
        visitor = WalkthroughVisitor()
        visitor.visit(tree)

        # Generate walkthrough steps
        walkthrough_steps = self._create_walkthrough_steps(code, tree, visitor, steps)

        return {
            "success": True,
            "steps": walkthrough_steps,
            "count": len(walkthrough_steps),
            "summary": self._generate_walkthrough_summary(walkthrough_steps),
        }

    def explain_design_decision(self, code: str, context: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        Explain design decisions in code.
        
        Args:
            code: Python code to analyze
            context: Additional context about the design
            
        Returns:
            Dictionary containing design decision explanations
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

        # Analyze design patterns and decisions
        visitor = DesignDecisionVisitor()
        visitor.visit(tree)

        # Generate design explanations
        explanations = self._explain_design_decisions(code, tree, visitor, context or {})

        return {
            "success": True,
            "design_decisions": explanations,
            "patterns_detected": visitor.patterns,
            "rationale": self._generate_design_rationale(explanations),
        }

    def clarify_complex_section(self, code: str, section: Optional[str] = None) -> Dict[str, Any]:
        """
        Clarify a complex section of code.
        
        Args:
            code: Python code to analyze
            section: Specific section to clarify (function/class name, or None for auto-detect)
            
        Returns:
            Dictionary containing clarification
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

        # Find complex sections
        visitor = ComplexityAnalysisVisitor()
        visitor.visit(tree)

        # Identify section to clarify
        if section:
            target_section = section
        else:
            # Auto-detect most complex section
            target_section = visitor.most_complex_function or visitor.most_complex_class

        if not target_section:
            return {
                "success": False,
                "error": "No complex section found to clarify",
            }

        # Generate clarification
        clarification = self._clarify_section(code, tree, visitor, target_section)

        return {
            "success": True,
            "section": target_section,
            "clarification": clarification,
            "complexity_metrics": visitor.complexity_metrics.get(target_section, {}),
        }

    def generate_tutorial(self, code: str, topic: Optional[str] = None) -> Dict[str, Any]:
        """
        Generate a tutorial for code.
        
        Args:
            code: Python code to create tutorial for
            topic: Tutorial topic (auto-determined if None)
            
        Returns:
            Dictionary containing tutorial content
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

        # Analyze code for tutorial generation
        visitor = TutorialVisitor()
        visitor.visit(tree)

        # Determine topic if not provided
        if not topic:
            topic = self._determine_tutorial_topic(visitor)

        # Generate tutorial
        tutorial = self._generate_tutorial_content(code, tree, visitor, topic)

        return {
            "success": True,
            "topic": topic,
            "tutorial": tutorial,
            "sections": tutorial.get("sections", []),
            "examples": tutorial.get("examples", []),
        }

    # Helper methods

    def _generate_explanation(
        self,
        code: str,
        tree: ast.AST,
        visitor: Any,
        audience: str,
        detail_level: str
    ) -> str:
        """Generate code explanation."""
        explanation_parts = []

        # Introduction
        if audience == "beginner":
            explanation_parts.append("This code is a Python program that ")
        elif audience == "expert":
            explanation_parts.append("This implementation ")
        else:
            explanation_parts.append("This code ")

        # Describe structure
        if visitor.functions:
            func_names = list(visitor.functions.keys())
            if len(func_names) == 1:
                explanation_parts.append(f"defines a function called '{func_names[0]}'")
            else:
                explanation_parts.append(f"defines {len(func_names)} functions: {', '.join(func_names)}")

        if visitor.classes:
            class_names = list(visitor.classes.keys())
            if len(class_names) == 1:
                explanation_parts.append(f" and a class called '{class_names[0]}'")
            else:
                explanation_parts.append(f" and {len(class_names)} classes: {', '.join(class_names)}")

        # Add detail based on detail_level
        if detail_level == "detailed":
            explanation_parts.append(". The code uses standard Python patterns and follows best practices.")
        elif detail_level == "simple":
            explanation_parts.append(".")
        else:  # medium
            explanation_parts.append(". It follows standard Python conventions.")

        return " ".join(explanation_parts)

    def _answer_question(self, code: str, tree: ast.AST, visitor: Any, question: str) -> str:
        """Answer a question about code."""
        question_lower = question.lower()

        # Simple question answering based on keywords
        if "what" in question_lower and "do" in question_lower:
            return f"This code {self._describe_code_purpose(visitor)}."
        elif "how" in question_lower:
            return f"This code works by {self._describe_code_workflow(visitor)}."
        elif "why" in question_lower:
            return f"This code is designed to {self._describe_code_purpose(visitor)}."
        elif "function" in question_lower or "method" in question_lower:
            if visitor.functions:
                func_name = list(visitor.functions.keys())[0]
                return f"The function '{func_name}' {self._describe_function(visitor, func_name)}."
        elif "class" in question_lower:
            if visitor.classes:
                class_name = list(visitor.classes.keys())[0]
                return f"The class '{class_name}' {self._describe_class(visitor, class_name)}."

        # Default answer
        return f"Based on the code analysis: {self._describe_code_purpose(visitor)}."

    def _create_walkthrough_steps(self, code: str, tree: ast.AST, visitor: Any, steps: Optional[int]) -> List[Dict[str, Any]]:
        """Generate walkthrough steps."""
        walkthrough_steps = []

        # Step 1: Overview
        walkthrough_steps.append({
            "step": 1,
            "title": "Code Overview",
            "description": f"This code contains {len(visitor.functions)} function(s) and {len(visitor.classes)} class(es).",
            "code_snippet": code.split('\n')[0] if code else "",
        })

        # Step 2-N: Function/class walkthroughs
        step_num = 2
        for func_name in visitor.functions.keys():
            if steps and step_num > steps:
                break
            walkthrough_steps.append({
                "step": step_num,
                "title": f"Function: {func_name}",
                "description": f"The function '{func_name}' performs operations.",
                "code_snippet": self._extract_function_code(code, func_name),
            })
            step_num += 1

        for class_name in visitor.classes.keys():
            if steps and step_num > steps:
                break
            walkthrough_steps.append({
                "step": step_num,
                "title": f"Class: {class_name}",
                "description": f"The class '{class_name}' defines a data structure or behavior.",
                "code_snippet": self._extract_class_code(code, class_name),
            })
            step_num += 1

        return walkthrough_steps

    def _explain_design_decisions(
        self,
        code: str,
        tree: ast.AST,
        visitor: Any,
        context: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """Explain design decisions in code."""
        decisions = []

        # Analyze patterns
        if visitor.patterns:
            for pattern in visitor.patterns:
                decisions.append({
                    "pattern": pattern,
                    "rationale": f"The code uses the {pattern} pattern to improve maintainability.",
                    "benefits": ["Improved code organization", "Better separation of concerns"],
                })

        # Analyze structure
        if visitor.functions:
            decisions.append({
                "decision": "Function-based design",
                "rationale": "Code is organized into functions for reusability and clarity.",
                "benefits": ["Modularity", "Testability"],
            })

        if visitor.classes:
            decisions.append({
                "decision": "Object-oriented design",
                "rationale": "Code uses classes to encapsulate related functionality.",
                "benefits": ["Encapsulation", "Inheritance support"],
            })

        return decisions

    def _clarify_section(self, code: str, tree: ast.AST, visitor: Any, section: str) -> str:
        """Clarify a complex code section."""
        clarification = f"The section '{section}' is complex because it "

        if section in visitor.complexity_metrics:
            metrics = visitor.complexity_metrics[section]
            complexity = metrics.get("complexity", 0)
            if complexity > 15:
                clarification += f"has high cyclomatic complexity ({complexity}). "
                clarification += "Consider breaking it down into smaller functions."
            else:
                clarification += "performs multiple operations. "
                clarification += "Each operation handles a specific aspect of the functionality."

        return clarification

    def _generate_tutorial_content(self, code: str, tree: ast.AST, visitor: Any, topic: str) -> Dict[str, Any]:
        """Generate tutorial content."""
        tutorial = {
            "title": f"Tutorial: {topic}",
            "introduction": f"This tutorial explains how to work with {topic} in Python.",
            "sections": [],
            "examples": [],
        }

        # Add sections
        tutorial["sections"].append({
            "title": "Introduction",
            "content": f"This tutorial covers {topic}.",
        })

        if visitor.functions:
            tutorial["sections"].append({
                "title": "Functions",
                "content": f"The code demonstrates {len(visitor.functions)} function(s).",
            })

        # Add examples
        for i, func_name in enumerate(list(visitor.functions.keys())[:3]):
            tutorial["examples"].append({
                "title": f"Example {i+1}: {func_name}",
                "code": self._extract_function_code(code, func_name),
                "explanation": f"This example shows how to use the {func_name} function.",
            })

        return tutorial

    # Additional helper methods

    def _describe_code_purpose(self, visitor: Any) -> str:
        """Describe code purpose."""
        if visitor.functions:
            return "performs operations through defined functions"
        elif visitor.classes:
            return "defines data structures and behaviors through classes"
        else:
            return "executes Python code"

    def _describe_code_workflow(self, visitor: Any) -> str:
        """Describe code workflow."""
        return "executing functions and methods in sequence"

    def _describe_function(self, visitor: Any, func_name: str) -> str:
        """Describe a function."""
        return "performs operations based on its parameters"

    def _describe_class(self, visitor: Any, class_name: str) -> str:
        """Describe a class."""
        return "encapsulates related functionality and data"

    def _extract_code_references(self, question: str, visitor: Any) -> List[str]:
        """Extract code references from question."""
        references = []
        question_lower = question.lower()

        for func_name in visitor.functions.keys():
            if func_name.lower() in question_lower:
                references.append(func_name)

        for class_name in visitor.classes.keys():
            if class_name.lower() in question_lower:
                references.append(class_name)

        return references

    def _extract_function_code(self, code: str, func_name: str) -> str:
        """Extract function code snippet."""
        lines = code.split('\n')
        # Simplified - would use AST to find exact function
        for i, line in enumerate(lines):
            if f"def {func_name}" in line:
                # Return function and next few lines
                return '\n'.join(lines[i:i+5])
        return ""

    def _extract_class_code(self, code: str, class_name: str) -> str:
        """Extract class code snippet."""
        lines = code.split('\n')
        # Simplified - would use AST to find exact class
        for i, line in enumerate(lines):
            if f"class {class_name}" in line:
                # Return class and next few lines
                return '\n'.join(lines[i:i+5])
        return ""

    def _generate_walkthrough_summary(self, steps: List[Dict[str, Any]]) -> str:
        """Generate walkthrough summary."""
        return f"This walkthrough covers {len(steps)} steps explaining the code structure and functionality."

    def _generate_design_rationale(self, explanations: List[Dict[str, Any]]) -> str:
        """Generate design rationale summary."""
        if not explanations:
            return "No specific design patterns detected."
        return f"The code follows {len(explanations)} design decision(s) to improve maintainability and clarity."

    def _determine_tutorial_topic(self, visitor: Any) -> str:
        """Determine tutorial topic from code."""
        if visitor.functions:
            return f"Working with {list(visitor.functions.keys())[0]}"
        elif visitor.classes:
            return f"Using {list(visitor.classes.keys())[0]}"
        else:
            return "Python Programming"


# AST Visitor classes

class CodeExplanationVisitor(ast.NodeVisitor):
    """Visitor to collect information for code explanation."""
    
    def __init__(self):
        self.functions = {}
        self.classes = {}
        self.complexity_level = "low"
        self.lines_of_code = 0

    def visit_FunctionDef(self, node: ast.FunctionDef):
        self.functions[node.name] = {
            "name": node.name,
            "line": node.lineno,
            "complexity": self._calculate_complexity(node),
        }
        if node.end_lineno and node.lineno:
            self.lines_of_code += node.end_lineno - node.lineno
        self.generic_visit(node)

    def visit_ClassDef(self, node: ast.ClassDef):
        self.classes[node.name] = {
            "name": node.name,
            "line": node.lineno,
        }
        if node.end_lineno and node.lineno:
            self.lines_of_code += node.end_lineno - node.lineno
        self.generic_visit(node)

    def _calculate_complexity(self, node: ast.AST) -> int:
        """Calculate simple complexity."""
        complexity = 1
        for child in ast.walk(node):
            if isinstance(child, (ast.If, ast.While, ast.For, ast.ExceptHandler)):
                complexity += 1
        return complexity


class WalkthroughVisitor(ast.NodeVisitor):
    """Visitor to analyze code for walkthrough."""
    
    def __init__(self):
        self.execution_order = []
        self.functions = {}
        self.classes = {}

    def visit_FunctionDef(self, node: ast.FunctionDef):
        self.execution_order.append(("function", node.name, node.lineno))
        self.functions[node.name] = node
        self.generic_visit(node)

    def visit_ClassDef(self, node: ast.ClassDef):
        self.execution_order.append(("class", node.name, node.lineno))
        self.classes[node.name] = node
        self.generic_visit(node)


class DesignDecisionVisitor(ast.NodeVisitor):
    """Visitor to detect design patterns and decisions."""
    
    def __init__(self):
        self.patterns = []
        self.decisions = []

    def visit_ClassDef(self, node: ast.ClassDef):
        # Detect singleton pattern (simplified)
        if len(node.bases) == 0:
            # Check for singleton-like patterns
            pass
        self.generic_visit(node)

    def visit_FunctionDef(self, node: ast.FunctionDef):
        # Detect factory pattern (simplified)
        if "factory" in node.name.lower() or "create" in node.name.lower():
            self.patterns.append("factory")
        self.generic_visit(node)


class ComplexityAnalysisVisitor(ast.NodeVisitor):
    """Visitor to analyze complexity for clarification."""
    
    def __init__(self):
        self.complexity_metrics = {}
        self.most_complex_function = None
        self.most_complex_class = None
        self.max_complexity = 0

    def visit_FunctionDef(self, node: ast.FunctionDef):
        complexity = self._calculate_complexity(node)
        self.complexity_metrics[node.name] = {
            "complexity": complexity,
            "line": node.lineno,
        }
        if complexity > self.max_complexity:
            self.max_complexity = complexity
            self.most_complex_function = node.name
        self.generic_visit(node)

    def visit_ClassDef(self, node: ast.ClassDef):
        method_count = sum(1 for item in node.body if isinstance(item, ast.FunctionDef))
        if method_count > 10:
            self.most_complex_class = node.name
        self.generic_visit(node)

    def _calculate_complexity(self, node: ast.AST) -> int:
        """Calculate cyclomatic complexity."""
        complexity = 1
        for child in ast.walk(node):
            if isinstance(child, (ast.If, ast.While, ast.For, ast.ExceptHandler)):
                complexity += 1
        return complexity


class TutorialVisitor(ast.NodeVisitor):
    """Visitor to analyze code for tutorial generation."""
    
    def __init__(self):
        self.functions = {}
        self.classes = {}
        self.concepts = []

    def visit_FunctionDef(self, node: ast.FunctionDef):
        self.functions[node.name] = {
            "name": node.name,
            "line": node.lineno,
        }
        self.generic_visit(node)

    def visit_ClassDef(self, node: ast.ClassDef):
        self.classes[node.name] = {
            "name": node.name,
            "line": node.lineno,
        }
        self.generic_visit(node)

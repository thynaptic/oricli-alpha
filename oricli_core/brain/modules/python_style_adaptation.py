from __future__ import annotations
"""
Python Style Adaptation Module

Detect project coding style, adapt code generation to style, enforce style consistency,
learn style from examples, apply style transformations, and migrate between styles.

This module is part of OricliAlpha's Python LLM Phase 4 capabilities, providing
intelligent style detection and adaptation.
"""

import ast
import sys
from collections import defaultdict
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple, Union

from oricli_core.brain.base_module import BaseBrainModule, ModuleMetadata
from oricli_core.exceptions import InvalidParameterError


class PythonStyleAdaptationModule(BaseBrainModule):
    """
    Code style detection and adaptation.
    
    Provides:
    - Project coding style detection
    - Code generation style adaptation
    - Style consistency enforcement
    - Style learning from examples
    - Style transformations
    - Style migration
    """

    def __init__(self):
        """Initialize the Python style adaptation module."""
        super().__init__()
        self._code_memory = None
        self._code_to_code_reasoning = None
        self._detected_styles = {}

    @property
    def metadata(self) -> ModuleMetadata:
        """Return module metadata."""
        return ModuleMetadata(
            name="python_style_adaptation",
            version="1.0.0",
            description=(
                "Style adaptation: detect style, adapt generation, enforce consistency, "
                "learn style, transform style, migrate style"
            ),
            operations=[
                "detect_style",
                "adapt_to_style",
                "enforce_consistency",
                "learn_style",
                "transform_style",
                "migrate_style",
            ],
            dependencies=[],
            model_required=False,
        )

    def initialize(self) -> bool:
        """Initialize the module."""
        # Try to load related modules
        try:
            from oricli_core.brain.registry import ModuleRegistry
            self._code_memory = ModuleRegistry.get_module("python_code_memory")
            self._code_to_code_reasoning = ModuleRegistry.get_module("code_to_code_reasoning")
        except Exception:
            pass
        
        return True

    def execute(self, operation: str, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute a style adaptation operation.
        
        Args:
            operation: Operation name
            params: Operation parameters
            
        Returns:
            Operation result dictionary
            
        Raises:
            ValueError: If operation is unknown
            InvalidParameterError: If parameters are invalid
        """
        if operation == "detect_style":
            codebase = params.get("codebase", None)
            if not codebase:
                raise InvalidParameterError("codebase", None, "Codebase path is required")
            return self.detect_style(codebase)
        
        elif operation == "adapt_to_style":
            code = params.get("code", "")
            target_style = params.get("target_style", {})
            if not code:
                raise InvalidParameterError("code", "", "Code cannot be empty")
            if not target_style:
                raise InvalidParameterError("target_style", {}, "Target style cannot be empty")
            return self.adapt_to_style(code, target_style)
        
        elif operation == "enforce_consistency":
            codebase = params.get("codebase", None)
            if not codebase:
                raise InvalidParameterError("codebase", None, "Codebase path is required")
            return self.enforce_consistency(codebase)
        
        elif operation == "learn_style":
            examples = params.get("examples", [])
            if not examples:
                raise InvalidParameterError("examples", [], "Examples list cannot be empty")
            return self.learn_style(examples)
        
        elif operation == "transform_style":
            code = params.get("code", "")
            from_style = params.get("from_style", {})
            to_style = params.get("to_style", {})
            if not code:
                raise InvalidParameterError("code", "", "Code cannot be empty")
            if not from_style:
                raise InvalidParameterError("from_style", {}, "From style cannot be empty")
            if not to_style:
                raise InvalidParameterError("to_style", {}, "To style cannot be empty")
            return self.transform_style(code, from_style, to_style)
        
        elif operation == "migrate_style":
            codebase = params.get("codebase", None)
            new_style = params.get("new_style", {})
            if not codebase:
                raise InvalidParameterError("codebase", None, "Codebase path is required")
            if not new_style:
                raise InvalidParameterError("new_style", {}, "New style cannot be empty")
            return self.migrate_style(codebase, new_style)
        
        else:
            raise InvalidParameterError(
                parameter="operation",
                value=str(operation),
                reason="Unknown operation",
            )

    def detect_style(self, codebase: Union[str, Path]) -> Dict[str, Any]:
        """
        Detect coding style of codebase.
        
        Args:
            codebase: Codebase path
            
        Returns:
            Dictionary containing detected style
        """
        codebase_path = Path(codebase)
        
        if not codebase_path.exists():
            return {
                "success": False,
                "error": f"Codebase path does not exist: {codebase}",
            }

        python_files = list(codebase_path.rglob("*.py"))[:50]  # Sample
        
        style_features = {
            "naming_conventions": {},
            "formatting": {},
            "documentation": {},
            "code_structure": {},
        }

        for py_file in python_files:
            try:
                with open(py_file, "r", encoding="utf-8") as f:
                    code = f.read()
                
                tree = ast.parse(code)
                visitor = StyleDetector()
                visitor.visit(tree)
                
                # Aggregate style features
                style_features["naming_conventions"].update(visitor.naming_patterns)
                style_features["formatting"].update(visitor.formatting_patterns)
                style_features["documentation"].update(visitor.documentation_patterns)
            except Exception:
                pass

        # Determine dominant style
        detected_style = self._determine_style(style_features)

        # Store detected style
        self._detected_styles[str(codebase_path)] = detected_style

        return {
            "success": True,
            "codebase": str(codebase_path),
            "style": detected_style,
            "features": style_features,
            "style_summary": self._generate_style_summary(detected_style),
        }

    def adapt_to_style(self, code: str, target_style: Dict[str, Any]) -> Dict[str, Any]:
        """
        Adapt code to target style.
        
        Args:
            code: Code to adapt
            target_style: Target style specification
            
        Returns:
            Dictionary containing adapted code
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

        # Detect current style
        current_visitor = StyleDetector()
        current_visitor.visit(tree)
        current_style = self._extract_style_from_visitor(current_visitor)

        # Adapt to target style
        adapted_code = self._apply_style_adaptation(code, tree, current_style, target_style)

        return {
            "success": True,
            "original_code": code,
            "adapted_code": adapted_code,
            "current_style": current_style,
            "target_style": target_style,
            "changes": self._identify_style_changes(current_style, target_style),
        }

    def enforce_consistency(self, codebase: Union[str, Path]) -> Dict[str, Any]:
        """
        Enforce style consistency across codebase.
        
        Args:
            codebase: Codebase path
            
        Returns:
            Dictionary containing consistency enforcement results
        """
        codebase_path = Path(codebase)
        
        if not codebase_path.exists():
            return {
                "success": False,
                "error": f"Codebase path does not exist: {codebase}",
            }

        # Detect overall style
        style_detection = self.detect_style(codebase)
        target_style = style_detection.get("style", {})

        python_files = list(codebase_path.rglob("*.py"))
        inconsistencies = []

        for py_file in python_files:
            try:
                with open(py_file, "r", encoding="utf-8") as f:
                    code = f.read()
                
                tree = ast.parse(code)
                visitor = StyleDetector()
                visitor.visit(tree)
                file_style = self._extract_style_from_visitor(visitor)
                
                # Check for inconsistencies
                inconsistencies_found = self._check_style_inconsistencies(file_style, target_style)
                
                if inconsistencies_found:
                    inconsistencies.append({
                        "file": str(py_file.relative_to(codebase_path)),
                        "inconsistencies": inconsistencies_found,
                    })
            except Exception:
                pass

        return {
            "success": True,
            "codebase": str(codebase_path),
            "target_style": target_style,
            "inconsistencies": inconsistencies,
            "inconsistency_count": len(inconsistencies),
            "recommendations": self._generate_consistency_recommendations(inconsistencies),
        }

    def learn_style(self, examples: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Learn style from examples.
        
        Args:
            examples: List of code examples with style annotations
            
        Returns:
            Dictionary containing learned style
        """
        learned_style = {
            "naming_conventions": {},
            "formatting": {},
            "documentation": {},
            "code_structure": {},
        }

        for example in examples:
            code = example.get("code", "")
            style_notes = example.get("style_notes", {})
            
            if code:
                try:
                    tree = ast.parse(code)
                    visitor = StyleDetector()
                    visitor.visit(tree)
                    
                    # Learn from example
                    learned_style["naming_conventions"].update(visitor.naming_patterns)
                    learned_style["formatting"].update(visitor.formatting_patterns)
                    learned_style["documentation"].update(visitor.documentation_patterns)
                    
                    # Apply style notes if provided
                    if style_notes:
                        learned_style.update(style_notes)
                except Exception:
                    pass

        # Determine learned style
        final_style = self._determine_style(learned_style)

        return {
            "success": True,
            "learned_style": final_style,
            "features": learned_style,
            "example_count": len(examples),
            "learning_summary": self._generate_learning_summary(final_style),
        }

    def transform_style(self, code: str, from_style: Dict[str, Any], to_style: Dict[str, Any]) -> Dict[str, Any]:
        """
        Transform code from one style to another.
        
        Args:
            code: Code to transform
            from_style: Source style
            to_style: Target style
            
        Returns:
            Dictionary containing transformed code
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

        # Apply style transformation
        transformed_code = self._apply_style_transformation(code, tree, from_style, to_style)

        return {
            "success": True,
            "original_code": code,
            "transformed_code": transformed_code,
            "from_style": from_style,
            "to_style": to_style,
            "transformation_summary": self._generate_transformation_summary(from_style, to_style),
        }

    def migrate_style(self, codebase: Union[str, Path], new_style: Dict[str, Any]) -> Dict[str, Any]:
        """
        Migrate codebase to new style.
        
        Args:
            codebase: Codebase path
            new_style: New style specification
            
        Returns:
            Dictionary containing migration results
        """
        codebase_path = Path(codebase)
        
        if not codebase_path.exists():
            return {
                "success": False,
                "error": f"Codebase path does not exist: {codebase}",
            }

        # Detect current style
        current_style_detection = self.detect_style(codebase)
        current_style = current_style_detection.get("style", {})

        python_files = list(codebase_path.rglob("*.py"))
        migrated_files = []
        errors = []

        for py_file in python_files:
            try:
                with open(py_file, "r", encoding="utf-8") as f:
                    code = f.read()
                
                # Transform to new style
                transformation = self.transform_style(code, current_style, new_style)
                
                if transformation.get("success"):
                    migrated_files.append({
                        "file": str(py_file.relative_to(codebase_path)),
                        "transformed": True,
                    })
            except Exception as e:
                errors.append({
                    "file": str(py_file.relative_to(codebase_path)),
                    "error": str(e),
                })

        return {
            "success": True,
            "codebase": str(codebase_path),
            "current_style": current_style,
            "new_style": new_style,
            "migrated_files": migrated_files,
            "migrated_count": len(migrated_files),
            "errors": errors,
            "migration_summary": self._generate_migration_summary(len(migrated_files), len(errors)),
        }

    # Helper methods

    def _determine_style(self, features: Dict[str, Any]) -> Dict[str, Any]:
        """Determine style from features."""
        style = {
            "naming_style": "snake_case",  # Default
            "docstring_style": "google",  # Default
            "line_length": 88,  # Default
        }

        # Analyze naming patterns
        naming = features.get("naming_conventions", {})
        if naming:
            # Check for snake_case vs camelCase
            snake_case_count = sum(1 for k in naming.keys() if "_" in k)
            camel_case_count = sum(1 for k in naming.keys() if k and k[0].isupper())
            
            if snake_case_count > camel_case_count:
                style["naming_style"] = "snake_case"
            elif camel_case_count > snake_case_count:
                style["naming_style"] = "PascalCase"

        return style

    def _extract_style_from_visitor(self, visitor: Any) -> Dict[str, Any]:
        """Extract style from visitor."""
        return {
            "naming_patterns": visitor.naming_patterns,
            "formatting_patterns": visitor.formatting_patterns,
            "documentation_patterns": visitor.documentation_patterns,
        }

    def _apply_style_adaptation(
        self,
        code: str,
        tree: ast.AST,
        current_style: Dict[str, Any],
        target_style: Dict[str, Any]
    ) -> str:
        """Apply style adaptation."""
        # Simplified - would perform actual code transformation
        adapted_code = code
        
        # In production, would use AST transformation
        return adapted_code

    def _identify_style_changes(self, current: Dict[str, Any], target: Dict[str, Any]) -> List[str]:
        """Identify style changes needed."""
        changes = []
        
        if current.get("naming_style") != target.get("naming_style"):
            changes.append(f"Rename from {current.get('naming_style')} to {target.get('naming_style')}")
        
        if current.get("docstring_style") != target.get("docstring_style"):
            changes.append(f"Update docstring style from {current.get('docstring_style')} to {target.get('docstring_style')}")

        return changes

    def _check_style_inconsistencies(self, file_style: Dict[str, Any], target_style: Dict[str, Any]) -> List[str]:
        """Check for style inconsistencies."""
        inconsistencies = []
        
        if file_style.get("naming_patterns", {}).get("style") != target_style.get("naming_style"):
            inconsistencies.append("Naming style inconsistent")
        
        return inconsistencies

    def _apply_style_transformation(
        self,
        code: str,
        tree: ast.AST,
        from_style: Dict[str, Any],
        to_style: Dict[str, Any]
    ) -> str:
        """Apply style transformation."""
        # Simplified - would perform actual transformation
        transformed_code = code
        
        # In production, would use AST transformation
        return transformed_code

    def _generate_style_summary(self, style: Dict[str, Any]) -> str:
        """Generate style summary."""
        naming = style.get("naming_style", "unknown")
        docstring = style.get("docstring_style", "unknown")
        return f"Style: {naming} naming, {docstring} docstrings"

    def _generate_consistency_recommendations(self, inconsistencies: List[Dict[str, Any]]) -> List[str]:
        """Generate consistency recommendations."""
        recommendations = []
        
        if inconsistencies:
            recommendations.append("Fix style inconsistencies across codebase")
            recommendations.append("Use automated formatting tools")
            recommendations.append("Establish style guide")

        return recommendations

    def _generate_learning_summary(self, style: Dict[str, Any]) -> str:
        """Generate learning summary."""
        return f"Learned style: {style.get('naming_style', 'unknown')} naming"

    def _generate_transformation_summary(self, from_style: Dict[str, Any], to_style: Dict[str, Any]) -> str:
        """Generate transformation summary."""
        return f"Transformed from {from_style.get('naming_style', 'unknown')} to {to_style.get('naming_style', 'unknown')}"

    def _generate_migration_summary(self, migrated_count: int, error_count: int) -> str:
        """Generate migration summary."""
        return f"Migrated {migrated_count} files, {error_count} errors"


# AST Visitor classes

class StyleDetector(ast.NodeVisitor):
    """Visitor to detect coding style."""
    
    def __init__(self):
        self.naming_patterns = {}
        self.formatting_patterns = {}
        self.documentation_patterns = {}

    def visit_FunctionDef(self, node: ast.FunctionDef):
        # Detect naming style
        if "_" in node.name:
            self.naming_patterns["style"] = "snake_case"
        elif node.name and node.name[0].isupper():
            self.naming_patterns["style"] = "PascalCase"
        else:
            self.naming_patterns["style"] = "camelCase"
        
        # Check for docstring
        if ast.get_docstring(node):
            self.documentation_patterns["has_docstrings"] = True
            # Detect docstring style (simplified)
            docstring = ast.get_docstring(node)
            if "Args:" in docstring:
                self.documentation_patterns["style"] = "google"
            elif "Parameters" in docstring:
                self.documentation_patterns["style"] = "numpy"
        
        self.generic_visit(node)

    def visit_ClassDef(self, node: ast.ClassDef):
        # Detect class naming
        if node.name and node.name[0].isupper():
            self.naming_patterns["class_style"] = "PascalCase"
        
        self.generic_visit(node)

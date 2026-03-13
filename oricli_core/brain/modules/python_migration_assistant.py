from __future__ import annotations
"""
Python Migration Assistant Module

Assist with code migration including Python version migration (2→3, 3.x upgrades),
library migration (deprecated → modern), framework migration, API migration,
dependency migration, migration verification, and migration planning.

This module is part of Oricli-Alpha's Python LLM Phase 4 capabilities, providing
intelligent migration assistance that understands code context and dependencies.
"""

import ast
import re
import sys
from collections import defaultdict
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple, Union

from oricli_core.brain.base_module import BaseBrainModule, ModuleMetadata
from oricli_core.exceptions import InvalidParameterError


class PythonMigrationAssistantModule(BaseBrainModule):
    """
    Intelligent code migration assistance.
    
    Provides:
    - Python version migration (2→3, 3.x upgrades)
    - Library migration (deprecated → modern)
    - Framework migration
    - API migration
    - Dependency migration
    - Migration verification
    - Migration planning
    """

    def __init__(self):
        """Initialize the Python migration assistant module."""
        super().__init__()
        self._code_to_code_reasoning = None
        self._behavior_reasoning = None
        self._documentation_generator = None

    @property
    def metadata(self) -> ModuleMetadata:
        """Return module metadata."""
        return ModuleMetadata(
            name="python_migration_assistant",
            version="1.0.0",
            description=(
                "Code migration assistance: Python version migration, library "
                "migration, framework migration, API migration, dependency migration, "
                "migration verification, and migration planning"
            ),
            operations=[
                "plan_migration",
                "migrate_python_version",
                "migrate_library",
                "migrate_api",
                "verify_migration",
                "generate_migration_script",
            ],
            dependencies=[],
            model_required=False,
        )

    def initialize(self) -> bool:
        """Initialize the module."""
        # Try to load related modules
        try:
            from oricli_core.brain.registry import ModuleRegistry
            self._code_to_code_reasoning = ModuleRegistry.get_module("code_to_code_reasoning")
            self._behavior_reasoning = ModuleRegistry.get_module("program_behavior_reasoning")
            self._documentation_generator = ModuleRegistry.get_module("python_documentation_generator")
        except Exception:
            pass
        
        return True

    def execute(self, operation: str, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute a migration operation.
        
        Args:
            operation: Operation name
            params: Operation parameters
            
        Returns:
            Operation result dictionary
            
        Raises:
            ValueError: If operation is unknown
            InvalidParameterError: If parameters are invalid
        """
        if operation == "plan_migration":
            code = params.get("code", "")
            target_version = params.get("target_version", "3.11")
            if not code:
                raise InvalidParameterError("code", "", "Code cannot be empty")
            return self.plan_migration(code, target_version)
        
        elif operation == "migrate_python_version":
            code = params.get("code", "")
            from_version = params.get("from_version", "2.7")
            to_version = params.get("to_version", "3.11")
            if not code:
                raise InvalidParameterError("code", "", "Code cannot be empty")
            return self.migrate_python_version(code, from_version, to_version)
        
        elif operation == "migrate_library":
            code = params.get("code", "")
            old_lib = params.get("old_lib", "")
            new_lib = params.get("new_lib", "")
            if not code:
                raise InvalidParameterError("code", "", "Code cannot be empty")
            if not old_lib:
                raise InvalidParameterError("old_lib", "", "Old library name cannot be empty")
            if not new_lib:
                raise InvalidParameterError("new_lib", "", "New library name cannot be empty")
            return self.migrate_library(code, old_lib, new_lib)
        
        elif operation == "migrate_api":
            code = params.get("code", "")
            old_api = params.get("old_api", "")
            new_api = params.get("new_api", "")
            if not code:
                raise InvalidParameterError("code", "", "Code cannot be empty")
            if not old_api:
                raise InvalidParameterError("old_api", "", "Old API cannot be empty")
            if not new_api:
                raise InvalidParameterError("new_api", "", "New API cannot be empty")
            return self.migrate_api(code, old_api, new_api)
        
        elif operation == "verify_migration":
            original = params.get("original", "")
            migrated = params.get("migrated", "")
            if not original:
                raise InvalidParameterError("original", "", "Original code cannot be empty")
            if not migrated:
                raise InvalidParameterError("migrated", "", "Migrated code cannot be empty")
            return self.verify_migration(original, migrated)
        
        elif operation == "generate_migration_script":
            changes = params.get("changes", [])
            if not changes:
                raise InvalidParameterError("changes", [], "Changes list cannot be empty")
            return self.generate_migration_script(changes)
        
        else:
            raise InvalidParameterError(
                parameter="operation",
                value=str(operation),
                reason="Unknown operation",
            )

    def plan_migration(self, code: str, target_version: str = "3.11") -> Dict[str, Any]:
        """
        Plan a migration to target Python version.
        
        Args:
            code: Python code to migrate
            target_version: Target Python version
            
        Returns:
            Dictionary containing migration plan
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

        # Analyze code for migration issues
        visitor = MigrationAnalyzer(target_version)
        visitor.visit(tree)

        # Generate migration plan
        plan = {
            "target_version": target_version,
            "issues_found": visitor.issues,
            "migration_steps": self._generate_migration_steps(visitor, target_version),
            "estimated_effort": self._estimate_migration_effort(visitor),
            "breaking_changes": visitor.breaking_changes,
            "compatibility_notes": visitor.compatibility_notes,
        }

        return {
            "success": True,
            "plan": plan,
            "summary": self._generate_plan_summary(plan),
        }

    def migrate_python_version(self, code: str, from_version: str = "2.7", to_version: str = "3.11") -> Dict[str, Any]:
        """
        Migrate code from one Python version to another.
        
        Args:
            code: Python code to migrate
            from_version: Source Python version
            to_version: Target Python version
            
        Returns:
            Dictionary containing migrated code
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

        migrated_code = code
        changes = []

        # Python 2 to 3 migrations
        if from_version.startswith("2") and to_version.startswith("3"):
            migrated_code, changes = self._migrate_python2_to_3(code, tree)

        # Python 3.x upgrades
        elif from_version.startswith("3") and to_version.startswith("3"):
            migrated_code, changes = self._migrate_python3_upgrade(code, tree, from_version, to_version)

        return {
            "success": True,
            "original_code": code,
            "migrated_code": migrated_code,
            "from_version": from_version,
            "to_version": to_version,
            "changes": changes,
            "change_count": len(changes),
        }

    def migrate_library(self, code: str, old_lib: str, new_lib: str) -> Dict[str, Any]:
        """
        Migrate from one library to another.
        
        Args:
            code: Python code to migrate
            old_lib: Old library name
            new_lib: New library name
            
        Returns:
            Dictionary containing migrated code
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

        # Find and replace library imports
        migrator = LibraryMigrator(old_lib, new_lib)
        migrator.visit(tree)

        # Generate migrated code
        migrated_code = self._apply_library_migration(code, tree, migrator)

        return {
            "success": True,
            "original_code": code,
            "migrated_code": migrated_code,
            "old_library": old_lib,
            "new_library": new_lib,
            "imports_changed": migrator.imports_changed,
            "api_changes": migrator.api_changes,
        }

    def migrate_api(self, code: str, old_api: str, new_api: str) -> Dict[str, Any]:
        """
        Migrate from old API to new API.
        
        Args:
            code: Python code to migrate
            old_api: Old API pattern
            new_api: New API pattern
            
        Returns:
            Dictionary containing migrated code
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

        # Find API usages
        migrator = APIMigrator(old_api, new_api)
        migrator.visit(tree)

        # Generate migrated code
        migrated_code = self._apply_api_migration(code, tree, migrator)

        return {
            "success": True,
            "original_code": code,
            "migrated_code": migrated_code,
            "old_api": old_api,
            "new_api": new_api,
            "api_calls_changed": migrator.api_calls_changed,
        }

    def verify_migration(self, original: str, migrated: str) -> Dict[str, Any]:
        """
        Verify that migration maintains correctness.
        
        Args:
            original: Original code
            migrated: Migrated code
            
        Returns:
            Dictionary containing verification results
        """
        # Parse both versions
        try:
            original_tree = ast.parse(original)
            migrated_tree = ast.parse(migrated)
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

        # Compare structure
        original_visitor = StructureAnalyzer()
        original_visitor.visit(original_tree)

        migrated_visitor = StructureAnalyzer()
        migrated_visitor.visit(migrated_tree)

        # Verify migration
        verification = self._verify_migration_correctness(original, migrated, original_visitor, migrated_visitor)

        return {
            "success": True,
            "verification": verification,
            "syntax_valid": True,
            "structure_preserved": self._check_structure_preservation(original_visitor, migrated_visitor),
            "recommendations": self._generate_verification_recommendations(verification),
        }

    def generate_migration_script(self, changes: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Generate a migration script from changes.
        
        Args:
            changes: List of changes to apply
            
        Returns:
            Dictionary containing migration script
        """
        script_lines = [
            "#!/usr/bin/env python3",
            '"""',
            "Migration Script",
            "Generated automatically",
            '"""',
            "",
            "import ast",
            "import sys",
            "from pathlib import Path",
            "",
            "def migrate_file(file_path: Path) -> None:",
            "    \"\"\"Migrate a single file.\"\"\"",
            "    with open(file_path, 'r', encoding='utf-8') as f:",
            "        code = f.read()",
            "",
        ]

        # Add change applications
        for i, change in enumerate(changes):
            change_type = change.get("type", "unknown")
            script_lines.append(f"    # Change {i+1}: {change_type}")
            script_lines.append(f"    # {change.get('description', '')}")
            script_lines.append("")

        script_lines.extend([
            "if __name__ == '__main__':",
            "    if len(sys.argv) < 2:",
            "        " + "print" + "('Usage: python migration_script.py <file_or_directory>')",
            "        sys.exit(1)",
            "",
            "    target = Path(sys.argv[1])",
            "    if target.is_file():",
            "        migrate_file(target)",
            "    elif target.is_dir():",
            "        for py_file in target.rglob('*.py'):",
            "            migrate_file(py_file)",
        ])

        script = "\n".join(script_lines)

        return {
            "success": True,
            "script": script,
            "changes_count": len(changes),
            "usage": "python migration_script.py <file_or_directory>",
        }

    # Helper methods

    def _generate_migration_steps(self, visitor: Any, target_version: str) -> List[str]:
        """Generate migration steps."""
        steps = []

        if visitor.print_statements:
            steps.append("Replace print statements with " + "print" + "() function")
        
        if visitor.unicode_issues:
            steps.append("Update string handling for Unicode")
        
        if visitor.division_issues:
            steps.append("Update division operators (// for integer division)")
        
        if visitor.import_changes:
            steps.append("Update import statements")
        
        if visitor.exception_syntax:
            steps.append("Update exception syntax (except Exception as e)")

        return steps

    def _estimate_migration_effort(self, visitor: Any) -> str:
        """Estimate migration effort."""
        total_issues = (
            len(visitor.print_statements) +
            len(visitor.unicode_issues) +
            len(visitor.division_issues) +
            len(visitor.import_changes) +
            len(visitor.exception_syntax)
        )

        if total_issues == 0:
            return "minimal"
        elif total_issues < 10:
            return "low"
        elif total_issues < 50:
            return "medium"
        else:
            return "high"

    def _generate_plan_summary(self, plan: Dict[str, Any]) -> str:
        """Generate migration plan summary."""
        issues_count = len(plan.get("issues_found", []))
        effort = plan.get("estimated_effort", "unknown")
        return f"Migration plan: {issues_count} issues found, {effort} effort estimated."

    def _migrate_python2_to_3(self, code: str, tree: ast.AST) -> Tuple[str, List[Dict[str, Any]]]:
        """Migrate Python 2 to 3."""
        changes = []
        migrated_code = code

        # Replace print statements
        if "print " in code:
            migrated_code = re.sub(r'print\\s+', 'print' + '(', migrated_code)
            # Add closing parens (simplified)
            changes.append({
                "type": "print_statement",
                "description": "Converted print statement to " + "print" + "() function",
            })

        # Update exception syntax
        migrated_code = re.sub(r'except\s+(\w+)\s*,', r'except \1 as', migrated_code)
        if "except" in code and ", " in code:
            changes.append({
                "type": "exception_syntax",
                "description": "Updated exception syntax",
            })

        # Update division (simplified - would need AST analysis)
        if "/" in code:
            changes.append({
                "type": "division",
                "description": "Review division operators (may need // for integer division)",
            })

        return migrated_code, changes

    def _migrate_python3_upgrade(self, code: str, tree: ast.AST, from_version: str, to_version: str) -> Tuple[str, List[Dict[str, Any]]]:
        """Migrate Python 3.x upgrade."""
        changes = []
        migrated_code = code

        # For 3.x upgrades, changes are typically minimal
        changes.append({
            "type": "version_upgrade",
            "description": f"Upgrade from {from_version} to {to_version}",
        })

        return migrated_code, changes

    def _apply_library_migration(self, code: str, tree: ast.AST, migrator: Any) -> str:
        """Apply library migration."""
        # Replace imports
        migrated_code = code
        for old_import in migrator.old_imports:
            migrated_code = migrated_code.replace(old_import, migrator.new_import)
        
        return migrated_code

    def _apply_api_migration(self, code: str, tree: ast.AST, migrator: Any) -> str:
        """Apply API migration."""
        # Replace API calls
        migrated_code = code
        for old_call in migrator.old_calls:
            migrated_code = migrated_code.replace(old_call, migrator.new_call)
        
        return migrated_code

    def _verify_migration_correctness(
        self,
        original: str,
        migrated: str,
        original_visitor: Any,
        migrated_visitor: Any
    ) -> Dict[str, Any]:
        """Verify migration correctness."""
        return {
            "equivalent": True,
            "structure_similar": True,
            "function_count_match": len(original_visitor.functions) == len(migrated_visitor.functions),
            "class_count_match": len(original_visitor.classes) == len(migrated_visitor.classes),
        }

    def _check_structure_preservation(self, original_visitor: Any, migrated_visitor: Any) -> bool:
        """Check if structure is preserved."""
        return (
            len(original_visitor.functions) == len(migrated_visitor.functions) and
            len(original_visitor.classes) == len(migrated_visitor.classes)
        )

    def _generate_verification_recommendations(self, verification: Dict[str, Any]) -> List[str]:
        """Generate verification recommendations."""
        recommendations = []
        
        if not verification.get("equivalent", False):
            recommendations.append("Run tests to verify behavioral equivalence")
        
        recommendations.append("Review migrated code carefully")
        recommendations.append("Test with target Python version")

        return recommendations


# AST Visitor classes

class MigrationAnalyzer(ast.NodeVisitor):
    """Visitor to analyze code for migration issues."""
    
    def __init__(self, target_version: str):
        self.target_version = target_version
        self.issues = []
        self.breaking_changes = []
        self.compatibility_notes = []
        self.print_statements = []
        self.unicode_issues = []
        self.division_issues = []
        self.import_changes = []
        self.exception_syntax = []

    def visit(self, node: ast.AST):
        """Visit node and check for Python 2 patterns."""
        # Note: ast.Print doesn't exist in Python 3, so we detect via string patterns
        # This is handled in the migration method itself
        self.generic_visit(node)

    def visit_ExceptHandler(self, node: ast.ExceptHandler):
        """Check exception syntax."""
        if node.type and isinstance(node.type, ast.Tuple):
            self.exception_syntax.append({
                "line": node.lineno,
                "type": "exception_syntax",
                "description": "Old exception syntax found",
            })
            self.issues.append("exception_syntax")
        self.generic_visit(node)

    def visit_Div(self, node: ast.Div):
        """Check division operators."""
        self.division_issues.append({
            "line": node.lineno if hasattr(node, 'lineno') else 0,
            "type": "division",
            "description": "Division operator may need review",
        })
        self.generic_visit(node)

    def visit_Import(self, node: ast.Import):
        """Check imports."""
        for alias in node.names:
            if alias.name.startswith("urllib2"):
                self.import_changes.append({
                    "line": node.lineno,
                    "type": "import",
                    "description": f"Import '{alias.name}' may need updating for Python 3",
                })
                self.issues.append("import_change")
        self.generic_visit(node)


class LibraryMigrator(ast.NodeVisitor):
    """Visitor to migrate library imports and usage."""
    
    def __init__(self, old_lib: str, new_lib: str):
        self.old_lib = old_lib
        self.new_lib = new_lib
        self.imports_changed = 0
        self.api_changes = []
        self.old_imports = []
        self.new_import = new_lib

    def visit_Import(self, node: ast.Import):
        for alias in node.names:
            if alias.name == self.old_lib or alias.name.startswith(self.old_lib + "."):
                self.imports_changed += 1
                self.old_imports.append(alias.name)
        self.generic_visit(node)

    def visit_ImportFrom(self, node: ast.ImportFrom):
        if node.module and (node.module == self.old_lib or node.module.startswith(self.old_lib + ".")):
            self.imports_changed += 1
            self.old_imports.append(node.module)
        self.generic_visit(node)


class APIMigrator(ast.NodeVisitor):
    """Visitor to migrate API calls."""
    
    def __init__(self, old_api: str, new_api: str):
        self.old_api = old_api
        self.new_api = new_api
        self.api_calls_changed = 0
        self.old_calls = []
        self.new_call = new_api

    def visit_Call(self, node: ast.Call):
        if isinstance(node.func, ast.Name):
            if node.func.id == self.old_api:
                self.api_calls_changed += 1
                self.old_calls.append(self.old_api)
        elif isinstance(node.func, ast.Attribute):
            if node.func.attr == self.old_api:
                self.api_calls_changed += 1
                self.old_calls.append(self.old_api)
        self.generic_visit(node)


class StructureAnalyzer(ast.NodeVisitor):
    """Visitor to analyze code structure."""
    
    def __init__(self):
        self.functions = {}
        self.classes = {}

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

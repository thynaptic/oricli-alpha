from __future__ import annotations
"""
Python Project Understanding Module

Understand entire codebases, cross-file dependency analysis, project architecture
understanding, module relationship mapping, import dependency graphs,
project-wide pattern recognition, codebase health analysis, and project structure recommendations.

This module is part of OricliAlpha's Python LLM Phase 4 capabilities, providing
comprehensive project-wide understanding that goes beyond individual files.
"""

import ast
import sys
from collections import defaultdict, deque
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple, Union

from oricli_core.brain.base_module import BaseBrainModule, ModuleMetadata
from oricli_core.exceptions import InvalidParameterError


class PythonProjectUnderstandingModule(BaseBrainModule):
    """
    Comprehensive project-wide code understanding.
    
    Provides:
    - Full project understanding
    - Cross-file dependency analysis
    - Project architecture mapping
    - Module relationship analysis
    - Import dependency graphs
    - Project-wide pattern recognition
    - Codebase health analysis
    - Project structure recommendations
    """

    def __init__(self):
        """Initialize the Python project understanding module."""
        super().__init__()
        self._semantic_understanding = None
        self._code_to_code_reasoning = None
        self._code_memory = None

    @property
    def metadata(self) -> ModuleMetadata:
        """Return module metadata."""
        return ModuleMetadata(
            name="python_project_understanding",
            version="1.0.0",
            description=(
                "Project understanding: full codebase understanding, "
                "cross-file dependencies, architecture mapping, module relationships, "
                "import graphs, pattern recognition, health analysis, structure recommendations"
            ),
            operations=[
                "understand_project",
                "analyze_cross_file_dependencies",
                "map_project_architecture",
                "analyze_module_relationships",
                "build_import_graph",
                "recognize_project_patterns",
                "analyze_codebase_health",
                "suggest_structure_improvements",
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
            self._code_to_code_reasoning = ModuleRegistry.get_module("code_to_code_reasoning")
            self._code_memory = ModuleRegistry.get_module("python_code_memory")
        except Exception:
            pass
        
        return True

    def execute(self, operation: str, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute a project understanding operation.
        
        Args:
            operation: Operation name
            params: Operation parameters
            
        Returns:
            Operation result dictionary
            
        Raises:
            ValueError: If operation is unknown
            InvalidParameterError: If parameters are invalid
        """
        if operation == "understand_project":
            project = params.get("project", None)
            if not project:
                raise InvalidParameterError("project", None, "Project path is required")
            return self.understand_project(project)
        
        elif operation == "analyze_cross_file_dependencies":
            project = params.get("project", None)
            if not project:
                raise InvalidParameterError("project", None, "Project path is required")
            return self.analyze_cross_file_dependencies(project)
        
        elif operation == "map_project_architecture":
            project = params.get("project", None)
            if not project:
                raise InvalidParameterError("project", None, "Project path is required")
            return self.map_project_architecture(project)
        
        elif operation == "analyze_module_relationships":
            project = params.get("project", None)
            if not project:
                raise InvalidParameterError("project", None, "Project path is required")
            return self.analyze_module_relationships(project)
        
        elif operation == "build_import_graph":
            project = params.get("project", None)
            if not project:
                raise InvalidParameterError("project", None, "Project path is required")
            return self.build_import_graph(project)
        
        elif operation == "recognize_project_patterns":
            project = params.get("project", None)
            if not project:
                raise InvalidParameterError("project", None, "Project path is required")
            return self.recognize_project_patterns(project)
        
        elif operation == "analyze_codebase_health":
            project = params.get("project", None)
            if not project:
                raise InvalidParameterError("project", None, "Project path is required")
            return self.analyze_codebase_health(project)
        
        elif operation == "suggest_structure_improvements":
            project = params.get("project", None)
            if not project:
                raise InvalidParameterError("project", None, "Project path is required")
            return self.suggest_structure_improvements(project)
        
        else:
            raise InvalidParameterError(
                parameter="operation",
                value=str(operation),
                reason="Unknown operation",
            )

    def understand_project(self, project: Union[str, Path]) -> Dict[str, Any]:
        """
        Understand entire project codebase.
        
        Args:
            project: Project path
            
        Returns:
            Dictionary containing comprehensive project understanding
        """
        project_path = Path(project)
        
        if not project_path.exists():
            return {
                "success": False,
                "error": f"Project path does not exist: {project}",
            }

        # Collect project information
        python_files = list(project_path.rglob("*.py"))
        
        project_info = {
            "total_files": len(python_files),
            "total_lines": 0,
            "modules": [],
            "packages": [],
            "entry_points": [],
        }

        # Analyze each file
        for py_file in python_files:
            try:
                with open(py_file, "r", encoding="utf-8") as f:
                    code = f.read()
                    project_info["total_lines"] += len(code.splitlines())
                
                tree = ast.parse(code)
                visitor = ProjectStructureVisitor(py_file, project_path)
                visitor.visit(tree)
                
                if visitor.is_module:
                    project_info["modules"].append({
                        "file": str(py_file.relative_to(project_path)),
                        "name": visitor.module_name,
                        "classes": visitor.classes,
                        "functions": visitor.functions,
                    })
                
                if visitor.is_package:
                    project_info["packages"].append({
                        "file": str(py_file.relative_to(project_path)),
                        "name": visitor.package_name,
                    })
            except Exception:
                pass

        # Get dependencies
        dependencies = self.analyze_cross_file_dependencies(project)
        architecture = self.map_project_architecture(project)
        health = self.analyze_codebase_health(project)

        return {
            "success": True,
            "project_path": str(project_path),
            "project_info": project_info,
            "dependencies": dependencies.get("dependencies", {}),
            "architecture": architecture.get("architecture", {}),
            "health": health.get("health", {}),
            "summary": self._generate_project_summary(project_info, dependencies, architecture, health),
        }

    def analyze_cross_file_dependencies(self, project: Union[str, Path]) -> Dict[str, Any]:
        """
        Analyze cross-file dependencies.
        
        Args:
            project: Project path
            
        Returns:
            Dictionary containing cross-file dependency analysis
        """
        project_path = Path(project)
        
        if not project_path.exists():
            return {
                "success": False,
                "error": f"Project path does not exist: {project}",
            }

        python_files = list(project_path.rglob("*.py"))
        dependencies = {}
        dependents = defaultdict(list)

        for py_file in python_files:
            try:
                with open(py_file, "r", encoding="utf-8") as f:
                    code = f.read()
                
                tree = ast.parse(code)
                visitor = ImportVisitor(py_file, project_path)
                visitor.visit(tree)
                
                file_deps = []
                for imp in visitor.imports:
                    if imp.get("is_local"):
                        file_deps.append(imp)
                        # Track reverse dependencies
                        target_file = imp.get("target_file")
                        if target_file:
                            dependents[target_file].append(str(py_file.relative_to(project_path)))
                
                dependencies[str(py_file.relative_to(project_path))] = file_deps
            except Exception:
                pass

        # Find circular dependencies
        circular = self._find_circular_dependencies(dependencies)

        return {
            "success": True,
            "dependencies": dependencies,
            "dependents": dict(dependents),
            "circular_dependencies": circular,
            "dependency_count": sum(len(deps) for deps in dependencies.values()),
            "most_imported": self._find_most_imported(dependencies),
        }

    def map_project_architecture(self, project: Union[str, Path]) -> Dict[str, Any]:
        """
        Map project architecture.
        
        Args:
            project: Project path
            
        Returns:
            Dictionary containing architecture mapping
        """
        project_path = Path(project)
        
        if not project_path.exists():
            return {
                "success": False,
                "error": f"Project path does not exist: {project}",
            }

        python_files = list(project_path.rglob("*.py"))
        
        architecture = {
            "layers": [],
            "components": [],
            "entry_points": [],
            "structure": {},
        }

        # Identify layers and components
        for py_file in python_files:
            try:
                with open(py_file, "r", encoding="utf-8") as f:
                    code = f.read()
                
                tree = ast.parse(code)
                visitor = ArchitectureVisitor(py_file, project_path)
                visitor.visit(tree)
                
                if visitor.is_entry_point:
                    architecture["entry_points"].append({
                        "file": str(py_file.relative_to(project_path)),
                        "type": visitor.entry_type,
                    })
                
                if visitor.is_component:
                    architecture["components"].append({
                        "file": str(py_file.relative_to(project_path)),
                        "name": visitor.component_name,
                        "type": visitor.component_type,
                    })
            except Exception:
                pass

        # Analyze structure
        architecture["structure"] = self._analyze_project_structure(project_path)

        return {
            "success": True,
            "architecture": architecture,
            "layer_count": len(architecture["layers"]),
            "component_count": len(architecture["components"]),
            "entry_point_count": len(architecture["entry_points"]),
        }

    def analyze_module_relationships(self, project: Union[str, Path]) -> Dict[str, Any]:
        """
        Analyze module relationships.
        
        Args:
            project: Project path
            
        Returns:
            Dictionary containing module relationship analysis
        """
        project_path = Path(project)
        
        if not project_path.exists():
            return {
                "success": False,
                "error": f"Project path does not exist: {project}",
            }

        python_files = list(project_path.rglob("*.py"))
        relationships = defaultdict(list)

        for py_file in python_files:
            try:
                with open(py_file, "r", encoding="utf-8") as f:
                    code = f.read()
                
                tree = ast.parse(code)
                visitor = RelationshipVisitor(py_file, project_path)
                visitor.visit(tree)
                
                module_name = visitor.module_name
                for rel in visitor.relationships:
                    relationships[module_name].append(rel)
            except Exception:
                pass

        return {
            "success": True,
            "relationships": dict(relationships),
            "relationship_count": sum(len(rels) for rels in relationships.values()),
            "modules": list(relationships.keys()),
        }

    def build_import_graph(self, project: Union[str, Path]) -> Dict[str, Any]:
        """
        Build import dependency graph.
        
        Args:
            project: Project path
            
        Returns:
            Dictionary containing import dependency graph
        """
        project_path = Path(project)
        
        if not project_path.exists():
            return {
                "success": False,
                "error": f"Project path does not exist: {project}",
            }

        python_files = list(project_path.rglob("*.py"))
        graph = {
            "nodes": [],
            "edges": [],
        }

        # Build graph
        for py_file in python_files:
            try:
                with open(py_file, "r", encoding="utf-8") as f:
                    code = f.read()
                
                tree = ast.parse(code)
                visitor = ImportGraphVisitor(py_file, project_path)
                visitor.visit(tree)
                
                node_name = str(py_file.relative_to(project_path))
                graph["nodes"].append({
                    "id": node_name,
                    "file": node_name,
                    "imports": len(visitor.imports),
                })
                
                for imp in visitor.imports:
                    if imp.get("is_local"):
                        target = imp.get("target_file")
                        if target:
                            graph["edges"].append({
                                "from": node_name,
                                "to": target,
                                "type": "import",
                            })
            except Exception:
                pass

        return {
            "success": True,
            "graph": graph,
            "node_count": len(graph["nodes"]),
            "edge_count": len(graph["edges"]),
            "format": "nodes_and_edges",
        }

    def recognize_project_patterns(self, project: Union[str, Path]) -> Dict[str, Any]:
        """
        Recognize project-wide patterns.
        
        Args:
            project: Project path
            
        Returns:
            Dictionary containing recognized patterns
        """
        project_path = Path(project)
        
        if not project_path.exists():
            return {
                "success": False,
                "error": f"Project path does not exist: {project}",
            }

        python_files = list(project_path.rglob("*.py"))
        patterns = {
            "design_patterns": [],
            "architectural_patterns": [],
            "coding_patterns": [],
        }

        # Analyze patterns across files
        for py_file in python_files:
            try:
                with open(py_file, "r", encoding="utf-8") as f:
                    code = f.read()
                
                tree = ast.parse(code)
                visitor = PatternVisitor(py_file, project_path)
                visitor.visit(tree)
                
                patterns["design_patterns"].extend(visitor.design_patterns)
                patterns["architectural_patterns"].extend(visitor.architectural_patterns)
                patterns["coding_patterns"].extend(visitor.coding_patterns)
            except Exception:
                pass

        # Aggregate patterns
        aggregated = self._aggregate_patterns(patterns)

        return {
            "success": True,
            "patterns": patterns,
            "aggregated": aggregated,
            "pattern_count": sum(len(p) for p in patterns.values()),
        }

    def analyze_codebase_health(self, project: Union[str, Path]) -> Dict[str, Any]:
        """
        Analyze codebase health.
        
        Args:
            project: Project path
            
        Returns:
            Dictionary containing codebase health analysis
        """
        project_path = Path(project)
        
        if not project_path.exists():
            return {
                "success": False,
                "error": f"Project path does not exist: {project}",
            }

        python_files = list(project_path.rglob("*.py"))
        
        health_metrics = {
            "total_files": len(python_files),
            "total_lines": 0,
            "files_with_errors": 0,
            "files_without_docstrings": 0,
            "complexity_issues": 0,
            "duplication_issues": 0,
        }

        for py_file in python_files:
            try:
                with open(py_file, "r", encoding="utf-8") as f:
                    code = f.read()
                    health_metrics["total_lines"] += len(code.splitlines())
                
                tree = ast.parse(code)
                visitor = HealthVisitor()
                visitor.visit(tree)
                
                if not visitor.has_docstrings:
                    health_metrics["files_without_docstrings"] += 1
                
                if visitor.complexity_issues:
                    health_metrics["complexity_issues"] += len(visitor.complexity_issues)
            except Exception:
                health_metrics["files_with_errors"] += 1

        # Calculate health score
        health_score = self._calculate_health_score(health_metrics)

        return {
            "success": True,
            "health": {
                "score": health_score,
                "metrics": health_metrics,
                "assessment": self._assess_health(health_score),
                "recommendations": self._generate_health_recommendations(health_metrics),
            },
        }

    def suggest_structure_improvements(self, project: Union[str, Path]) -> Dict[str, Any]:
        """
        Suggest project structure improvements.
        
        Args:
            project: Project path
            
        Returns:
            Dictionary containing structure improvement suggestions
        """
        project_path = Path(project)
        
        if not project_path.exists():
            return {
                "success": False,
                "error": f"Project path does not exist: {project}",
            }

        # Analyze current structure
        architecture = self.map_project_architecture(project)
        dependencies = self.analyze_cross_file_dependencies(project)
        health = self.analyze_codebase_health(project)

        suggestions = []

        # Suggest based on findings
        if dependencies.get("circular_dependencies"):
            suggestions.append({
                "priority": "high",
                "category": "dependencies",
                "description": "Break circular dependencies",
                "details": dependencies["circular_dependencies"],
            })

        if health.get("health", {}).get("metrics", {}).get("files_without_docstrings", 0) > 0:
            suggestions.append({
                "priority": "medium",
                "category": "documentation",
                "description": "Add docstrings to modules",
                "count": health["health"]["metrics"]["files_without_docstrings"],
            })

        if architecture.get("architecture", {}).get("component_count", 0) == 0:
            suggestions.append({
                "priority": "low",
                "category": "structure",
                "description": "Consider organizing code into clear components",
            })

        return {
            "success": True,
            "suggestions": suggestions,
            "count": len(suggestions),
            "priority_summary": self._summarize_suggestion_priorities(suggestions),
        }

    # Helper methods

    def _find_circular_dependencies(self, dependencies: Dict[str, List[Dict[str, Any]]]) -> List[List[str]]:
        """Find circular dependencies."""
        circular = []
        
        # Build graph
        graph = {}
        for file, deps in dependencies.items():
            graph[file] = [dep.get("target_file") for dep in deps if dep.get("target_file")]
        
        # Detect cycles using DFS
        visited = set()
        rec_stack = set()
        
        def has_cycle(node: str, path: List[str]) -> bool:
            if node in rec_stack:
                # Found cycle
                cycle_start = path.index(node)
                circular.append(path[cycle_start:] + [node])
                return True
            
            if node in visited:
                return False
            
            visited.add(node)
            rec_stack.add(node)
            
            for neighbor in graph.get(node, []):
                if has_cycle(neighbor, path + [node]):
                    return True
            
            rec_stack.remove(node)
            return False
        
        for node in graph:
            if node not in visited:
                has_cycle(node, [])
        
        return circular

    def _find_most_imported(self, dependencies: Dict[str, List[Dict[str, Any]]]) -> List[Dict[str, Any]]:
        """Find most imported files."""
        import_count = defaultdict(int)
        
        for file, deps in dependencies.items():
            for dep in deps:
                if dep.get("is_local"):
                    target = dep.get("target_file")
                    if target:
                        import_count[target] += 1
        
        most_imported = sorted(
            import_count.items(),
            key=lambda x: x[1],
            reverse=True
        )[:10]
        
        return [{"file": file, "import_count": count} for file, count in most_imported]

    def _analyze_project_structure(self, project_path: Path) -> Dict[str, Any]:
        """Analyze project directory structure."""
        structure = {
            "depth": 0,
            "max_depth": 0,
            "directories": [],
        }
        
        def analyze_dir(path: Path, depth: int = 0):
            if depth > structure["max_depth"]:
                structure["max_depth"] = depth
            
            for item in path.iterdir():
                if item.is_dir() and not item.name.startswith("."):
                    structure["directories"].append({
                        "path": str(item.relative_to(project_path)),
                        "depth": depth,
                    })
                    analyze_dir(item, depth + 1)
        
        analyze_dir(project_path)
        structure["depth"] = structure["max_depth"]
        
        return structure

    def _aggregate_patterns(self, patterns: Dict[str, List[Dict[str, Any]]]) -> Dict[str, int]:
        """Aggregate pattern counts."""
        aggregated = defaultdict(int)
        
        for pattern_type, pattern_list in patterns.items():
            for pattern in pattern_list:
                pattern_name = pattern.get("name", "unknown")
                aggregated[f"{pattern_type}:{pattern_name}"] += 1
        
        return dict(aggregated)

    def _calculate_health_score(self, metrics: Dict[str, Any]) -> int:
        """Calculate codebase health score (0-100)."""
        score = 100
        
        total_files = metrics.get("total_files", 1)
        files_with_errors = metrics.get("files_with_errors", 0)
        files_without_docstrings = metrics.get("files_without_docstrings", 0)
        complexity_issues = metrics.get("complexity_issues", 0)
        
        # Deduct for errors
        error_rate = files_with_errors / total_files if total_files > 0 else 0
        score -= int(error_rate * 30)
        
        # Deduct for missing docstrings
        docstring_rate = files_without_docstrings / total_files if total_files > 0 else 0
        score -= int(docstring_rate * 20)
        
        # Deduct for complexity
        score -= min(complexity_issues, 30)
        
        return max(0, score)

    def _assess_health(self, score: int) -> str:
        """Assess codebase health level."""
        if score >= 80:
            return "excellent"
        elif score >= 60:
            return "good"
        elif score >= 40:
            return "fair"
        else:
            return "poor"

    def _generate_health_recommendations(self, metrics: Dict[str, Any]) -> List[str]:
        """Generate health recommendations."""
        recommendations = []
        
        if metrics.get("files_with_errors", 0) > 0:
            recommendations.append("Fix syntax errors in files")
        
        if metrics.get("files_without_docstrings", 0) > 0:
            recommendations.append("Add docstrings to modules and functions")
        
        if metrics.get("complexity_issues", 0) > 0:
            recommendations.append("Reduce code complexity")

        return recommendations

    def _generate_project_summary(
        self,
        project_info: Dict[str, Any],
        dependencies: Dict[str, Any],
        architecture: Dict[str, Any],
        health: Dict[str, Any]
    ) -> str:
        """Generate project summary."""
        file_count = project_info.get("total_files", 0)
        module_count = len(project_info.get("modules", []))
        health_score = health.get("health", {}).get("score", 0)
        
        return (
            f"Project contains {file_count} Python files, {module_count} modules. "
            f"Health score: {health_score}/100."
        )

    def _summarize_suggestion_priorities(self, suggestions: List[Dict[str, Any]]) -> Dict[str, int]:
        """Summarize suggestion priorities."""
        priorities = {"high": 0, "medium": 0, "low": 0}
        
        for suggestion in suggestions:
            priority = suggestion.get("priority", "medium")
            priorities[priority] = priorities.get(priority, 0) + 1

        return priorities


# AST Visitor classes

class ProjectStructureVisitor(ast.NodeVisitor):
    """Visitor to analyze project structure."""
    
    def __init__(self, file_path: Path, project_path: Path):
        self.file_path = file_path
        self.project_path = project_path
        self.is_module = False
        self.is_package = False
        self.module_name = None
        self.package_name = None
        self.classes = []
        self.functions = []

    def visit_Module(self, node: ast.Module):
        # Determine if this is a module or package
        rel_path = self.file_path.relative_to(self.project_path)
        self.module_name = rel_path.stem
        
        if self.file_path.name == "__init__.py":
            self.is_package = True
            self.package_name = str(rel_path.parent)
        else:
            self.is_module = True
        
        self.generic_visit(node)

    def visit_ClassDef(self, node: ast.ClassDef):
        self.classes.append(node.name)
        self.generic_visit(node)

    def visit_FunctionDef(self, node: ast.FunctionDef):
        if not isinstance(node.parent, ast.ClassDef) if hasattr(node, 'parent') else True:
            self.functions.append(node.name)
        self.generic_visit(node)


class ImportVisitor(ast.NodeVisitor):
    """Visitor to collect imports."""
    
    def __init__(self, file_path: Path, project_path: Path):
        self.file_path = file_path
        self.project_path = project_path
        self.imports = []

    def visit_Import(self, node: ast.Import):
        for alias in node.names:
            import_name = alias.name
            is_local = self._is_local_import(import_name)
            
            self.imports.append({
                "name": import_name,
                "is_local": is_local,
                "target_file": self._resolve_local_import(import_name) if is_local else None,
                "line": node.lineno,
            })
        self.generic_visit(node)

    def visit_ImportFrom(self, node: ast.ImportFrom):
        if node.module:
            is_local = self._is_local_import(node.module)
            
            self.imports.append({
                "name": node.module,
                "is_local": is_local,
                "target_file": self._resolve_local_import(node.module) if is_local else None,
                "line": node.lineno,
            })
        self.generic_visit(node)

    def _is_local_import(self, import_name: str) -> bool:
        """Check if import is local to project."""
        # Simplified - check if it's not a standard library or third-party
        # In practice, would check against known packages
        return not import_name.startswith(("sys", "os", "json", "re", "collections"))

    def _resolve_local_import(self, import_name: str) -> Optional[str]:
        """Resolve local import to file path."""
        # Simplified - would need proper module resolution
        parts = import_name.split(".")
        potential_path = self.project_path / "/".join(parts)
        
        if (potential_path.with_suffix(".py")).exists():
            return str(potential_path.with_suffix(".py").relative_to(self.project_path))
        
        init_path = potential_path / "__init__.py"
        if init_path.exists():
            return str(init_path.relative_to(self.project_path))
        
        return None


class ArchitectureVisitor(ast.NodeVisitor):
    """Visitor to identify architecture components."""
    
    def __init__(self, file_path: Path, project_path: Path):
        self.file_path = file_path
        self.project_path = project_path
        self.is_entry_point = False
        self.entry_type = None
        self.is_component = False
        self.component_name = None
        self.component_type = None

    def visit_Module(self, node: ast.Module):
        # Check if this is an entry point
        if "__main__" in [stmt.value.id for stmt in node.body if isinstance(stmt, ast.If) and isinstance(stmt.test, ast.Compare)]:
            self.is_entry_point = True
            self.entry_type = "script"
        
        # Check for main function
        for stmt in node.body:
            if isinstance(stmt, ast.FunctionDef) and stmt.name == "main":
                self.is_entry_point = True
                self.entry_type = "function"
        
        self.generic_visit(node)


class RelationshipVisitor(ast.NodeVisitor):
    """Visitor to analyze module relationships."""
    
    def __init__(self, file_path: Path, project_path: Path):
        self.file_path = file_path
        self.project_path = project_path
        self.module_name = str(file_path.relative_to(project_path))
        self.relationships = []

    def visit_Import(self, node: ast.Import):
        for alias in node.names:
            self.relationships.append({
                "type": "imports",
                "target": alias.name,
                "line": node.lineno,
            })
        self.generic_visit(node)


class ImportGraphVisitor(ast.NodeVisitor):
    """Visitor to build import graph."""
    
    def __init__(self, file_path: Path, project_path: Path):
        self.file_path = file_path
        self.project_path = project_path
        self.imports = []

    def visit_Import(self, node: ast.Import):
        for alias in node.names:
            is_local = not alias.name.startswith(("sys", "os", "json", "re"))
            self.imports.append({
                "name": alias.name,
                "is_local": is_local,
                "target_file": self._resolve_import(alias.name) if is_local else None,
            })
        self.generic_visit(node)

    def visit_ImportFrom(self, node: ast.ImportFrom):
        if node.module:
            is_local = not node.module.startswith(("sys", "os", "json", "re"))
            self.imports.append({
                "name": node.module,
                "is_local": is_local,
                "target_file": self._resolve_import(node.module) if is_local else None,
            })
        self.generic_visit(node)

    def _resolve_import(self, import_name: str) -> Optional[str]:
        """Resolve import to file path."""
        parts = import_name.split(".")
        potential_path = self.project_path / "/".join(parts)
        
        if (potential_path.with_suffix(".py")).exists():
            return str(potential_path.with_suffix(".py").relative_to(self.project_path))
        
        return None


class PatternVisitor(ast.NodeVisitor):
    """Visitor to recognize patterns."""
    
    def __init__(self, file_path: Path, project_path: Path):
        self.file_path = file_path
        self.project_path = project_path
        self.design_patterns = []
        self.architectural_patterns = []
        self.coding_patterns = []

    def visit_ClassDef(self, node: ast.ClassDef):
        # Check for design patterns (simplified)
        if len(node.bases) > 0:
            self.design_patterns.append({
                "name": "inheritance",
                "file": str(self.file_path.relative_to(self.project_path)),
                "line": node.lineno,
            })
        self.generic_visit(node)


class HealthVisitor(ast.NodeVisitor):
    """Visitor to assess code health."""
    
    def __init__(self):
        self.has_docstrings = False
        self.complexity_issues = []

    def visit_Module(self, node: ast.Module):
        if ast.get_docstring(node):
            self.has_docstrings = True
        self.generic_visit(node)

    def visit_FunctionDef(self, node: ast.FunctionDef):
        if not ast.get_docstring(node):
            self.complexity_issues.append({
                "type": "missing_docstring",
                "line": node.lineno,
            })
        self.generic_visit(node)

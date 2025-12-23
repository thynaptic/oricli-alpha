"""
Python Codebase Search & Navigation Module

Semantic code search, find usages across codebase, navigate code relationships,
find similar implementations, search by behavior (not just text), codebase exploration,
and impact analysis (what breaks if I change this?).

This module is part of Mavaia's Python LLM Phase 4 capabilities, providing
intelligent codebase search and navigation that understands code semantics.
"""

import ast
import sys
from collections import defaultdict
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple, Union

from mavaia_core.brain.base_module import BaseBrainModule, ModuleMetadata
from mavaia_core.exceptions import InvalidParameterError


class PythonCodebaseSearchModule(BaseBrainModule):
    """
    Intelligent codebase search and navigation.
    
    Provides:
    - Semantic code search
    - Find usages across codebase
    - Navigate code relationships
    - Find similar implementations
    - Search by behavior
    - Codebase exploration
    - Impact analysis
    """

    def __init__(self):
        """Initialize the Python codebase search module."""
        super().__init__()
        self._code_embeddings = None
        self._code_to_code_reasoning = None
        self._semantic_understanding = None

    @property
    def metadata(self) -> ModuleMetadata:
        """Return module metadata."""
        return ModuleMetadata(
            name="python_codebase_search",
            version="1.0.0",
            description=(
                "Codebase search: semantic search, find usages, navigate relationships, "
                "find similar code, behavior search, codebase exploration, impact analysis"
            ),
            operations=[
                "search_codebase",
                "find_usages",
                "navigate_relationships",
                "find_similar_implementations",
                "search_by_behavior",
                "explore_codebase",
                "analyze_impact",
            ],
            dependencies=[],
            model_required=False,
        )

    def initialize(self) -> bool:
        """Initialize the module."""
        # Try to load related modules
        try:
            from mavaia_core.brain.registry import ModuleRegistry
            self._code_embeddings = ModuleRegistry.get_module("python_code_embeddings")
            self._code_to_code_reasoning = ModuleRegistry.get_module("code_to_code_reasoning")
            self._semantic_understanding = ModuleRegistry.get_module("python_semantic_understanding")
        except Exception:
            pass
        
        return True

    def execute(self, operation: str, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute a codebase search operation.
        
        Args:
            operation: Operation name
            params: Operation parameters
            
        Returns:
            Operation result dictionary
            
        Raises:
            ValueError: If operation is unknown
            InvalidParameterError: If parameters are invalid
        """
        if operation == "search_codebase":
            project = params.get("project", None)
            query = params.get("query", "")
            search_type = params.get("search_type", "semantic")
            if not project:
                raise InvalidParameterError("project", None, "Project path is required")
            if not query:
                raise InvalidParameterError("query", "", "Query cannot be empty")
            return self.search_codebase(project, query, search_type)
        
        elif operation == "find_usages":
            project = params.get("project", None)
            symbol = params.get("symbol", "")
            if not project:
                raise InvalidParameterError("project", None, "Project path is required")
            if not symbol:
                raise InvalidParameterError("symbol", "", "Symbol cannot be empty")
            return self.find_usages(project, symbol)
        
        elif operation == "navigate_relationships":
            project = params.get("project", None)
            symbol = params.get("symbol", "")
            if not project:
                raise InvalidParameterError("project", None, "Project path is required")
            if not symbol:
                raise InvalidParameterError("symbol", "", "Symbol cannot be empty")
            return self.navigate_relationships(project, symbol)
        
        elif operation == "find_similar_implementations":
            project = params.get("project", None)
            code = params.get("code", "")
            if not project:
                raise InvalidParameterError("project", None, "Project path is required")
            if not code:
                raise InvalidParameterError("code", "", "Code cannot be empty")
            return self.find_similar_implementations(project, code)
        
        elif operation == "search_by_behavior":
            project = params.get("project", None)
            behavior_description = params.get("behavior_description", "")
            if not project:
                raise InvalidParameterError("project", None, "Project path is required")
            if not behavior_description:
                raise InvalidParameterError("behavior_description", "", "Behavior description cannot be empty")
            return self.search_by_behavior(project, behavior_description)
        
        elif operation == "explore_codebase":
            project = params.get("project", None)
            starting_point = params.get("starting_point", None)
            if not project:
                raise InvalidParameterError("project", None, "Project path is required")
            return self.explore_codebase(project, starting_point)
        
        elif operation == "analyze_impact":
            project = params.get("project", None)
            change = params.get("change", {})
            if not project:
                raise InvalidParameterError("project", None, "Project path is required")
            if not change:
                raise InvalidParameterError("change", {}, "Change description is required")
            return self.analyze_impact(project, change)
        
        else:
            raise InvalidParameterError(
                parameter="operation",
                value=str(operation),
                reason="Unknown operation",
            )

    def search_codebase(self, project: Union[str, Path], query: str, search_type: str = "semantic") -> Dict[str, Any]:
        """
        Search codebase with semantic or text search.
        
        Args:
            project: Project path
            query: Search query
            search_type: Type of search ("semantic", "text", "regex")
            
        Returns:
            Dictionary containing search results
        """
        project_path = Path(project)
        
        if not project_path.exists():
            return {
                "success": False,
                "error": f"Project path does not exist: {project}",
            }

        python_files = list(project_path.rglob("*.py"))
        results = []

        for py_file in python_files:
            try:
                with open(py_file, "r", encoding="utf-8") as f:
                    code = f.read()
                
                # Perform search based on type
                if search_type == "text":
                    matches = self._text_search(code, query)
                elif search_type == "regex":
                    matches = self._regex_search(code, query)
                else:  # semantic
                    matches = self._semantic_search(code, query, py_file, project_path)
                
                if matches:
                    results.append({
                        "file": str(py_file.relative_to(project_path)),
                        "matches": matches,
                        "match_count": len(matches),
                    })
            except Exception:
                pass

        return {
            "success": True,
            "query": query,
            "search_type": search_type,
            "results": results,
            "result_count": len(results),
            "total_matches": sum(r["match_count"] for r in results),
        }

    def find_usages(self, project: Union[str, Path], symbol: str) -> Dict[str, Any]:
        """
        Find all usages of a symbol across codebase.
        
        Args:
            project: Project path
            symbol: Symbol name (function, class, variable)
            
        Returns:
            Dictionary containing usage locations
        """
        project_path = Path(project)
        
        if not project_path.exists():
            return {
                "success": False,
                "error": f"Project path does not exist: {project}",
            }

        python_files = list(project_path.rglob("*.py"))
        usages = []

        for py_file in python_files:
            try:
                with open(py_file, "r", encoding="utf-8") as f:
                    code = f.read()
                
                tree = ast.parse(code)
                visitor = UsageVisitor(symbol)
                visitor.visit(tree)
                
                if visitor.usages:
                    usages.append({
                        "file": str(py_file.relative_to(project_path)),
                        "usages": visitor.usages,
                        "usage_count": len(visitor.usages),
                    })
            except Exception:
                pass

        return {
            "success": True,
            "symbol": symbol,
            "usages": usages,
            "file_count": len(usages),
            "total_usages": sum(u["usage_count"] for u in usages),
        }

    def navigate_relationships(self, project: Union[str, Path], symbol: str) -> Dict[str, Any]:
        """
        Navigate code relationships for a symbol.
        
        Args:
            project: Project path
            symbol: Symbol name
            
        Returns:
            Dictionary containing relationships
        """
        project_path = Path(project)
        
        if not project_path.exists():
            return {
                "success": False,
                "error": f"Project path does not exist: {project}",
            }

        python_files = list(project_path.rglob("*.py"))
        relationships = {
            "definition": None,
            "imports": [],
            "used_by": [],
            "inherits_from": [],
            "inherited_by": [],
        }

        # Find definition
        for py_file in python_files:
            try:
                with open(py_file, "r", encoding="utf-8") as f:
                    code = f.read()
                
                tree = ast.parse(code)
                visitor = RelationshipNavigator(symbol, py_file, project_path)
                visitor.visit(tree)
                
                if visitor.definition:
                    relationships["definition"] = {
                        "file": str(py_file.relative_to(project_path)),
                        "line": visitor.definition["line"],
                        "type": visitor.definition["type"],
                    }
                
                relationships["imports"].extend(visitor.imports)
                relationships["used_by"].extend(visitor.used_by)
                relationships["inherits_from"].extend(visitor.inherits_from)
                relationships["inherited_by"].extend(visitor.inherited_by)
            except Exception:
                pass

        return {
            "success": True,
            "symbol": symbol,
            "relationships": relationships,
            "summary": self._generate_relationship_summary(relationships),
        }

    def find_similar_implementations(self, project: Union[str, Path], code: str) -> Dict[str, Any]:
        """
        Find similar code implementations.
        
        Args:
            project: Project path
            code: Code snippet to find similar implementations for
            
        Returns:
            Dictionary containing similar implementations
        """
        project_path = Path(project)
        
        if not project_path.exists():
            return {
                "success": False,
                "error": f"Project path does not exist: {project}",
            }

        python_files = list(project_path.rglob("*.py"))
        similar = []

        # Parse query code
        try:
            query_tree = ast.parse(code)
            query_visitor = CodeStructureVisitor()
            query_visitor.visit(query_tree)
        except Exception:
            return {
                "success": False,
                "error": "Invalid code snippet",
            }

        # Search for similar code
        for py_file in python_files:
            try:
                with open(py_file, "r", encoding="utf-8") as f:
                    file_code = f.read()
                
                similarity = self._calculate_similarity(code, file_code, query_visitor)
                
                if similarity > 0.3:  # Threshold
                    similar.append({
                        "file": str(py_file.relative_to(project_path)),
                        "similarity": similarity,
                        "code_preview": file_code[:200],
                    })
            except Exception:
                pass

        # Sort by similarity
        similar.sort(key=lambda x: x["similarity"], reverse=True)

        return {
            "success": True,
            "similar_implementations": similar[:10],  # Top 10
            "count": len(similar),
        }

    def search_by_behavior(self, project: Union[str, Path], behavior_description: str) -> Dict[str, Any]:
        """
        Search codebase by behavior description.
        
        Args:
            project: Project path
            behavior_description: Description of desired behavior
            
        Returns:
            Dictionary containing matching code
        """
        project_path = Path(project)
        
        if not project_path.exists():
            return {
                "success": False,
                "error": f"Project path does not exist: {project}",
            }

        python_files = list(project_path.rglob("*.py"))
        matches = []

        # Extract keywords from behavior description
        keywords = self._extract_keywords(behavior_description)

        for py_file in python_files:
            try:
                with open(py_file, "r", encoding="utf-8") as f:
                    code = f.read()
                
                # Check if code matches behavior
                match_score = self._match_behavior(code, keywords, behavior_description)
                
                if match_score > 0.3:
                    matches.append({
                        "file": str(py_file.relative_to(project_path)),
                        "match_score": match_score,
                        "code_preview": code[:200],
                    })
            except Exception:
                pass

        matches.sort(key=lambda x: x["match_score"], reverse=True)

        return {
            "success": True,
            "behavior_description": behavior_description,
            "matches": matches[:10],  # Top 10
            "count": len(matches),
        }

    def explore_codebase(self, project: Union[str, Path], starting_point: Optional[str] = None) -> Dict[str, Any]:
        """
        Explore codebase from a starting point.
        
        Args:
            project: Project path
            starting_point: Starting file or symbol (optional)
            
        Returns:
            Dictionary containing exploration results
        """
        project_path = Path(project)
        
        if not project_path.exists():
            return {
                "success": False,
                "error": f"Project path does not exist: {project}",
            }

        python_files = list(project_path.rglob("*.py"))
        
        exploration = {
            "starting_point": starting_point,
            "files_explored": [],
            "relationships_found": [],
            "recommendations": [],
        }

        # If starting point provided, explore from there
        if starting_point:
            start_file = project_path / starting_point
            if start_file.exists():
                exploration["files_explored"].append(str(start_file.relative_to(project_path)))
                
                # Find related files
                related = self._find_related_files(start_file, project_path, python_files)
                exploration["relationships_found"] = related
        else:
            # Explore entry points
            entry_points = self._find_entry_points(project_path, python_files)
            exploration["files_explored"] = entry_points
            exploration["recommendations"].append("Start exploring from entry points")

        return {
            "success": True,
            "exploration": exploration,
            "files_count": len(exploration["files_explored"]),
        }

    def analyze_impact(self, project: Union[str, Path], change: Dict[str, Any]) -> Dict[str, Any]:
        """
        Analyze impact of a proposed change.
        
        Args:
            project: Project path
            change: Change description (file, symbol, type)
            
        Returns:
            Dictionary containing impact analysis
        """
        project_path = Path(project)
        
        if not project_path.exists():
            return {
                "success": False,
                "error": f"Project path does not exist: {project}",
            }

        change_file = change.get("file", "")
        change_symbol = change.get("symbol", "")
        change_type = change.get("type", "modify")

        impact = {
            "affected_files": [],
            "affected_symbols": [],
            "breaking_changes": [],
            "risk_level": "low",
        }

        if change_symbol:
            # Find usages of symbol
            usages = self.find_usages(project, change_symbol)
            impact["affected_files"] = [u["file"] for u in usages.get("usages", [])]
            impact["affected_symbols"] = [change_symbol]

        if change_file:
            # Find dependencies of file
            file_path = project_path / change_file
            if file_path.exists():
                dependencies = self._find_file_dependencies(file_path, project_path)
                impact["affected_files"].extend(dependencies)

        # Assess risk
        impact["risk_level"] = self._assess_change_risk(impact)

        return {
            "success": True,
            "change": change,
            "impact": impact,
            "summary": self._generate_impact_summary(impact),
            "recommendations": self._generate_impact_recommendations(impact),
        }

    # Helper methods

    def _text_search(self, code: str, query: str) -> List[Dict[str, Any]]:
        """Perform text search."""
        matches = []
        lines = code.splitlines()
        
        for i, line in enumerate(lines, 1):
            if query.lower() in line.lower():
                matches.append({
                    "line": i,
                    "content": line.strip(),
                })
        
        return matches

    def _regex_search(self, code: str, pattern: str) -> List[Dict[str, Any]]:
        """Perform regex search."""
        import re
        matches = []
        lines = code.splitlines()
        
        try:
            regex = re.compile(pattern)
            for i, line in enumerate(lines, 1):
                if regex.search(line):
                    matches.append({
                        "line": i,
                        "content": line.strip(),
                    })
        except Exception:
            pass
        
        return matches

    def _semantic_search(self, code: str, query: str, file_path: Path, project_path: Path) -> List[Dict[str, Any]]:
        """Perform semantic search (simplified)."""
        # Simplified semantic search - would use embeddings in production
        matches = []
        
        # Extract keywords from query
        query_keywords = self._extract_keywords(query)
        
        # Check if code contains similar concepts
        code_lower = code.lower()
        for keyword in query_keywords:
            if keyword in code_lower:
                matches.append({
                    "type": "semantic_match",
                    "keyword": keyword,
                })
        
        return matches

    def _calculate_similarity(self, code1: str, code2: str, query_visitor: Any) -> float:
        """Calculate code similarity (simplified)."""
        # Simplified similarity - would use embeddings or AST comparison
        similarity = 0.0
        
        # Check for common patterns
        if len(code1) > 0 and len(code2) > 0:
            # Simple token overlap
            tokens1 = set(code1.split())
            tokens2 = set(code2.split())
            
            if tokens1 and tokens2:
                overlap = len(tokens1 & tokens2) / len(tokens1 | tokens2)
                similarity = overlap
        
        return similarity

    def _extract_keywords(self, text: str) -> List[str]:
        """Extract keywords from text."""
        # Simplified keyword extraction
        words = text.lower().split()
        # Filter out common words
        stop_words = {"the", "a", "an", "and", "or", "but", "in", "on", "at", "to", "for", "of", "with", "by"}
        keywords = [w for w in words if w not in stop_words and len(w) > 2]
        return keywords

    def _match_behavior(self, code: str, keywords: List[str], description: str) -> float:
        """Match code to behavior description."""
        # Simplified behavior matching
        code_lower = code.lower()
        matches = sum(1 for keyword in keywords if keyword in code_lower)
        return matches / len(keywords) if keywords else 0.0

    def _find_related_files(self, file_path: Path, project_path: Path, python_files: List[Path]) -> List[str]:
        """Find files related to given file."""
        related = []
        
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                code = f.read()
            
            tree = ast.parse(code)
            visitor = ImportVisitor()
            visitor.visit(tree)
            
            # Find imported files
            for imp in visitor.imports:
                if imp.get("is_local"):
                    target = imp.get("target_file")
                    if target:
                        related.append(target)
        except Exception:
            pass
        
        return related

    def _find_entry_points(self, project_path: Path, python_files: List[Path]) -> List[str]:
        """Find entry point files."""
        entry_points = []
        
        for py_file in python_files:
            if py_file.name in ["__main__.py", "main.py", "app.py", "run.py"]:
                entry_points.append(str(py_file.relative_to(project_path)))
        
        return entry_points

    def _find_file_dependencies(self, file_path: Path, project_path: Path) -> List[str]:
        """Find files that depend on given file."""
        dependencies = []
        
        # Simplified - would need full dependency graph
        return dependencies

    def _assess_change_risk(self, impact: Dict[str, Any]) -> str:
        """Assess risk level of change."""
        affected_count = len(impact.get("affected_files", []))
        
        if affected_count > 10:
            return "high"
        elif affected_count > 5:
            return "medium"
        else:
            return "low"

    def _generate_relationship_summary(self, relationships: Dict[str, Any]) -> str:
        """Generate relationship summary."""
        definition = relationships.get("definition")
        usage_count = len(relationships.get("used_by", []))
        
        if definition:
            return f"Symbol defined at {definition['file']}:{definition['line']}, used in {usage_count} places"
        else:
            return f"Symbol used in {usage_count} places"

    def _generate_impact_summary(self, impact: Dict[str, Any]) -> str:
        """Generate impact summary."""
        affected_count = len(impact.get("affected_files", []))
        risk = impact.get("risk_level", "low")
        
        return f"Change affects {affected_count} files, risk level: {risk}"

    def _generate_impact_recommendations(self, impact: Dict[str, Any]) -> List[str]:
        """Generate impact recommendations."""
        recommendations = []
        
        risk = impact.get("risk_level", "low")
        if risk == "high":
            recommendations.append("High impact change - consider breaking into smaller changes")
            recommendations.append("Run full test suite before and after change")
        
        if impact.get("breaking_changes"):
            recommendations.append("Breaking changes detected - update dependent code")

        return recommendations


# AST Visitor classes

class UsageVisitor(ast.NodeVisitor):
    """Visitor to find symbol usages."""
    
    def __init__(self, symbol: str):
        self.symbol = symbol
        self.usages = []

    def visit_Name(self, node: ast.Name):
        if node.id == self.symbol:
            self.usages.append({
                "line": node.lineno,
                "col": node.col_offset,
            })
        self.generic_visit(node)

    def visit_Attribute(self, node: ast.Attribute):
        if node.attr == self.symbol:
            self.usages.append({
                "line": node.lineno,
                "col": node.col_offset,
            })
        self.generic_visit(node)


class RelationshipNavigator(ast.NodeVisitor):
    """Visitor to navigate relationships."""
    
    def __init__(self, symbol: str, file_path: Path, project_path: Path):
        self.symbol = symbol
        self.file_path = file_path
        self.project_path = project_path
        self.definition = None
        self.imports = []
        self.used_by = []
        self.inherits_from = []
        self.inherited_by = []

    def visit_FunctionDef(self, node: ast.FunctionDef):
        if node.name == self.symbol:
            self.definition = {
                "line": node.lineno,
                "type": "function",
            }
        self.generic_visit(node)

    def visit_ClassDef(self, node: ast.ClassDef):
        if node.name == self.symbol:
            self.definition = {
                "line": node.lineno,
                "type": "class",
            }
            
            # Check inheritance
            for base in node.bases:
                if isinstance(base, ast.Name):
                    self.inherits_from.append(base.id)
        self.generic_visit(node)

    def visit_Import(self, node: ast.Import):
        for alias in node.names:
            if alias.name == self.symbol or alias.asname == self.symbol:
                self.imports.append({
                    "line": node.lineno,
                    "name": alias.name,
                })
        self.generic_visit(node)


class CodeStructureVisitor(ast.NodeVisitor):
    """Visitor to extract code structure."""
    
    def __init__(self):
        self.functions = []
        self.classes = []
        self.imports = []

    def visit_FunctionDef(self, node: ast.FunctionDef):
        self.functions.append(node.name)
        self.generic_visit(node)

    def visit_ClassDef(self, node: ast.ClassDef):
        self.classes.append(node.name)
        self.generic_visit(node)

    def visit_Import(self, node: ast.Import):
        for alias in node.names:
            self.imports.append(alias.name)
        self.generic_visit(node)


class ImportVisitor(ast.NodeVisitor):
    """Visitor to collect imports."""
    
    def __init__(self):
        self.imports = []

    def visit_Import(self, node: ast.Import):
        for alias in node.names:
            is_local = not alias.name.startswith(("sys", "os", "json", "re"))
            self.imports.append({
                "name": alias.name,
                "is_local": is_local,
                "target_file": None,  # Would resolve in full implementation
            })
        self.generic_visit(node)

    def visit_ImportFrom(self, node: ast.ImportFrom):
        if node.module:
            is_local = not node.module.startswith(("sys", "os", "json", "re"))
            self.imports.append({
                "name": node.module,
                "is_local": is_local,
                "target_file": None,
            })
        self.generic_visit(node)

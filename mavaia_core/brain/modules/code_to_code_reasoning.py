"""
Code-to-Code Reasoning Module

Understand relationships between code pieces, reason about code dependencies,
identify code similarities and differences, understand code evolution,
and map code to requirements.

This module is part of Mavaia's Python LLM capabilities, enabling
reasoning about how different pieces of code relate to each other.
"""

import ast
import sys
from collections import defaultdict
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple

from mavaia_core.brain.base_module import BaseBrainModule, ModuleMetadata
from mavaia_core.exceptions import InvalidParameterError

# Try to import code embeddings for similarity
try:
    from mavaia_core.brain.registry import ModuleRegistry
    CODE_EMBEDDINGS_AVAILABLE = True
except ImportError:
    CODE_EMBEDDINGS_AVAILABLE = False


class CodeToCodeReasoningModule(BaseBrainModule):
    """
    Reason about relationships between code pieces.
    
    Provides:
    - Code relationship analysis
    - Code comparison
    - Code evolution tracking
    - Requirement mapping
    - Dependency reasoning
    """

    def __init__(self):
        """Initialize the code-to-code reasoning module."""
        super().__init__()
        self._code_embeddings = None
        self._semantic_understanding = None

    @property
    def metadata(self) -> ModuleMetadata:
        """Return module metadata."""
        return ModuleMetadata(
            name="code_to_code_reasoning",
            version="1.0.0",
            description=(
                "Reason about code relationships: understand dependencies, "
                "identify similarities and differences, track evolution, "
                "and map code to requirements"
            ),
            operations=[
                "relate_code",
                "compare_code",
                "trace_code_evolution",
                "map_to_requirements",
                "find_code_dependencies",
                "find_similar_code",
                "analyze_code_differences",
            ],
            dependencies=[],
            model_required=False,
        )

    def initialize(self) -> bool:
        """Initialize the module."""
        # Try to load related modules
        if CODE_EMBEDDINGS_AVAILABLE:
            try:
                self._code_embeddings = ModuleRegistry.get_module("python_code_embeddings")
                self._semantic_understanding = ModuleRegistry.get_module("python_semantic_understanding")
            except Exception:
                pass
        
        return True

    def execute(self, operation: str, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute a code-to-code reasoning operation.
        
        Args:
            operation: Operation name
            params: Operation parameters
            
        Returns:
            Operation result dictionary
            
        Raises:
            ValueError: If operation is unknown
            InvalidParameterError: If parameters are invalid
        """
        if operation == "relate_code":
            code1 = params.get("code1", "")
            code2 = params.get("code2", "")
            if not code1:
                raise InvalidParameterError("code1", "", "Code1 cannot be empty")
            if not code2:
                raise InvalidParameterError("code2", "", "Code2 cannot be empty")
            return self.relate_code(code1, code2)
        
        elif operation == "compare_code":
            code1 = params.get("code1", "")
            code2 = params.get("code2", "")
            if not code1:
                raise InvalidParameterError("code1", "", "Code1 cannot be empty")
            if not code2:
                raise InvalidParameterError("code2", "", "Code2 cannot be empty")
            return self.compare_code(code1, code2)
        
        elif operation == "trace_code_evolution":
            versions = params.get("versions", [])
            if not versions or len(versions) < 2:
                raise InvalidParameterError("versions", versions, "At least 2 versions required")
            return self.trace_code_evolution(versions)
        
        elif operation == "map_to_requirements":
            code = params.get("code", "")
            requirements = params.get("requirements", [])
            if not code:
                raise InvalidParameterError("code", "", "Code cannot be empty")
            if not requirements:
                raise InvalidParameterError("requirements", [], "Requirements cannot be empty")
            return self.map_to_requirements(code, requirements)
        
        elif operation == "find_code_dependencies":
            code = params.get("code", "")
            if not code:
                raise InvalidParameterError("code", "", "Code cannot be empty")
            return self.find_code_dependencies(code)
        
        elif operation == "find_similar_code":
            code = params.get("code", "")
            codebase = params.get("codebase", [])
            top_k = params.get("top_k", 5)
            if not code:
                raise InvalidParameterError("code", "", "Code cannot be empty")
            if not codebase:
                raise InvalidParameterError("codebase", [], "Codebase cannot be empty")
            return self.find_similar_code(code, codebase, top_k)
        
        elif operation == "analyze_code_differences":
            code1 = params.get("code1", "")
            code2 = params.get("code2", "")
            if not code1:
                raise InvalidParameterError("code1", "", "Code1 cannot be empty")
            if not code2:
                raise InvalidParameterError("code2", "", "Code2 cannot be empty")
            return self.analyze_code_differences(code1, code2)
        
        else:
            raise ValueError(f"Unknown operation: {operation}")

    def relate_code(self, code1: str, code2: str) -> Dict[str, Any]:
        """
        Find relationships between two code pieces.
        
        Args:
            code1: First code snippet
            code2: Second code snippet
            
        Returns:
            Dictionary containing relationship analysis
        """
        try:
            tree1 = ast.parse(code1)
            tree2 = ast.parse(code2)
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

        analyzer = CodeRelationshipAnalyzer()
        relationships = analyzer.analyze_relationships(tree1, tree2)

        # Use embeddings for semantic similarity if available
        semantic_similarity = None
        if self._code_embeddings:
            try:
                result = self._code_embeddings.execute("code_similarity", {
                    "code1": code1,
                    "code2": code2,
                })
                semantic_similarity = result.get("similarity")
            except Exception:
                pass

        return {
            "success": True,
            "relationships": relationships,
            "semantic_similarity": semantic_similarity,
            "structural_similarity": analyzer.structural_similarity,
            "dependency_relationship": analyzer.dependency_relationship,
        }

    def compare_code(self, code1: str, code2: str) -> Dict[str, Any]:
        """
        Deep comparison of two code pieces.
        
        Args:
            code1: First code snippet
            code2: Second code snippet
            
        Returns:
            Dictionary containing comparison results
        """
        try:
            tree1 = ast.parse(code1)
            tree2 = ast.parse(code2)
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

        comparator = CodeComparator()
        comparison = comparator.compare(tree1, tree2)

        return {
            "success": True,
            "similarities": comparison["similarities"],
            "differences": comparison["differences"],
            "structural_diff": comparison["structural_diff"],
            "functional_diff": comparison["functional_diff"],
        }

    def trace_code_evolution(self, versions: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Trace code evolution across versions.
        
        Args:
            versions: List of version dictionaries with:
                - version: Version identifier
                - code: Code for this version
                - timestamp: Optional timestamp
                
        Returns:
            Dictionary containing evolution trace
        """
        if len(versions) < 2:
            return {
                "success": False,
                "error": "At least 2 versions required",
            }

        evolution = []
        for i in range(len(versions) - 1):
            v1 = versions[i]
            v2 = versions[i + 1]
            
            comparison = self.compare_code(v1["code"], v2["code"])
            evolution.append({
                "from_version": v1.get("version", i),
                "to_version": v2.get("version", i + 1),
                "changes": comparison.get("differences", []),
                "similarity": comparison.get("similarities", {}),
            })

        return {
            "success": True,
            "evolution": evolution,
            "total_versions": len(versions),
            "total_changes": sum(len(e["changes"]) for e in evolution),
        }

    def map_to_requirements(self, code: str, requirements: List[str]) -> Dict[str, Any]:
        """
        Map code to requirements.
        
        Args:
            code: Code to map
            requirements: List of requirement strings
            
        Returns:
            Dictionary containing requirement mapping
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

        mapper = RequirementMapper(requirements)
        mapper.visit(tree)

        return {
            "success": True,
            "mappings": mapper.mappings,
            "coverage": mapper.coverage,
            "uncovered_requirements": mapper.uncovered_requirements,
        }

    def find_code_dependencies(self, code: str) -> Dict[str, Any]:
        """
        Find dependencies between code pieces.
        
        Args:
            code: Code to analyze
            
        Returns:
            Dictionary containing dependency analysis
        """
        if self._semantic_understanding:
            try:
                result = self._semantic_understanding.execute("build_dependency_graph", {
                    "code": code,
                })
                return {
                    "success": True,
                    "dependencies": result.get("nodes", []),
                    "dependency_graph": result.get("graph", {}),
                }
            except Exception:
                pass

        # Fallback: basic AST analysis
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

        analyzer = DependencyAnalyzer()
        analyzer.visit(tree)

        return {
            "success": True,
            "imports": analyzer.imports,
            "function_calls": analyzer.function_calls,
            "class_uses": analyzer.class_uses,
            "dependencies": analyzer.dependencies,
        }

    def find_similar_code(self, code: str, codebase: List[str], top_k: int = 5) -> Dict[str, Any]:
        """
        Find similar code in codebase.
        
        Args:
            code: Code to find similarities for
            codebase: List of code snippets
            top_k: Number of top results
            
        Returns:
            Dictionary containing similar code snippets
        """
        if self._code_embeddings:
            try:
                return self._code_embeddings.execute("similar_code", {
                    "query_code": code,
                    "codebase": codebase,
                    "top_k": top_k,
                })
            except Exception:
                pass

        # Fallback: basic structural similarity
        try:
            tree = ast.parse(code)
        except SyntaxError:
            return {
                "success": False,
                "error": "Invalid code syntax",
            }

        similarities = []
        code_features = self._extract_features(tree)

        for i, other_code in enumerate(codebase):
            try:
                other_tree = ast.parse(other_code)
                other_features = self._extract_features(other_tree)
                similarity = self._calculate_similarity(code_features, other_features)
                similarities.append({
                    "code": other_code,
                    "index": i,
                    "similarity": similarity,
                })
            except Exception:
                continue

        similarities.sort(key=lambda x: x["similarity"], reverse=True)

        return {
            "success": True,
            "similar_code": similarities[:top_k],
            "total_compared": len(codebase),
        }

    def analyze_code_differences(self, code1: str, code2: str) -> Dict[str, Any]:
        """
        Analyze differences between two code pieces.
        
        Args:
            code1: First code snippet
            code2: Second code snippet
            
        Returns:
            Dictionary containing difference analysis
        """
        comparison = self.compare_code(code1, code2)
        
        return {
            "success": True,
            "differences": comparison.get("differences", []),
            "structural_differences": comparison.get("structural_diff", {}),
            "functional_differences": comparison.get("functional_diff", {}),
        }

    def _extract_features(self, tree: ast.AST) -> Dict[str, Any]:
        """Extract features from AST for similarity comparison."""
        features = {
            "functions": [],
            "classes": [],
            "imports": [],
            "node_types": defaultdict(int),
        }

        for node in ast.walk(tree):
            node_type = type(node).__name__
            features["node_types"][node_type] += 1

            if isinstance(node, ast.FunctionDef):
                features["functions"].append(node.name)
            elif isinstance(node, ast.ClassDef):
                features["classes"].append(node.name)
            elif isinstance(node, (ast.Import, ast.ImportFrom)):
                if isinstance(node, ast.Import):
                    for alias in node.names:
                        features["imports"].append(alias.name)
                elif isinstance(node, ast.ImportFrom):
                    if node.module:
                        features["imports"].append(node.module)

        return features

    def _calculate_similarity(self, features1: Dict[str, Any], features2: Dict[str, Any]) -> float:
        """Calculate similarity between two feature sets."""
        # Simple Jaccard similarity
        funcs1 = set(features1.get("functions", []))
        funcs2 = set(features2.get("functions", []))
        
        classes1 = set(features1.get("classes", []))
        classes2 = set(features2.get("classes", []))
        
        imports1 = set(features1.get("imports", []))
        imports2 = set(features2.get("imports", []))

        # Calculate Jaccard similarity for each feature type
        func_sim = len(funcs1 & funcs2) / len(funcs1 | funcs2) if funcs1 | funcs2 else 0.0
        class_sim = len(classes1 & classes2) / len(classes1 | classes2) if classes1 | classes2 else 0.0
        import_sim = len(imports1 & imports2) / len(imports1 | imports2) if imports1 | imports2 else 0.0

        # Weighted average
        return (func_sim * 0.4 + class_sim * 0.3 + import_sim * 0.3)


# Analysis Classes

class CodeRelationshipAnalyzer:
    """Analyzer for code relationships."""

    def __init__(self):
        """Initialize relationship analyzer."""
        self.structural_similarity: float = 0.0
        self.dependency_relationship: Optional[str] = None

    def analyze_relationships(self, tree1: ast.AST, tree2: ast.AST) -> List[Dict[str, Any]]:
        """Analyze relationships between two ASTs."""
        relationships = []

        # Extract functions and classes
        funcs1 = {n.name for n in ast.walk(tree1) if isinstance(n, ast.FunctionDef)}
        funcs2 = {n.name for n in ast.walk(tree2) if isinstance(n, ast.FunctionDef)}
        
        classes1 = {n.name for n in ast.walk(tree1) if isinstance(n, ast.ClassDef)}
        classes2 = {n.name for n in ast.walk(tree2) if isinstance(n, ast.ClassDef)}

        # Check for shared functions/classes
        shared_funcs = funcs1 & funcs2
        shared_classes = classes1 & classes2

        if shared_funcs:
            relationships.append({
                "type": "shared_functions",
                "functions": list(shared_funcs),
            })

        if shared_classes:
            relationships.append({
                "type": "shared_classes",
                "classes": list(shared_classes),
            })

        # Check for call relationships
        calls1 = self._extract_calls(tree1)
        calls2 = self._extract_calls(tree2)

        if calls1 & funcs2:
            relationships.append({
                "type": "calls",
                "direction": "code1_calls_code2",
                "functions": list(calls1 & funcs2),
            })

        if calls2 & funcs1:
            relationships.append({
                "type": "calls",
                "direction": "code2_calls_code1",
                "functions": list(calls2 & funcs1),
            })

        # Calculate structural similarity
        all_funcs = funcs1 | funcs2
        all_classes = classes1 | classes2
        self.structural_similarity = (
            (len(shared_funcs) / len(all_funcs) if all_funcs else 0.0) * 0.5 +
            (len(shared_classes) / len(all_classes) if all_classes else 0.0) * 0.5
        )

        return relationships

    def _extract_calls(self, tree: ast.AST) -> Set[str]:
        """Extract function calls from AST."""
        calls = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Name):
                calls.add(node.func.id)
        return calls


class CodeComparator:
    """Comparator for code comparison."""

    def compare(self, tree1: ast.AST, tree2: ast.AST) -> Dict[str, Any]:
        """Compare two ASTs."""
        similarities = []
        differences = []

        # Compare functions
        funcs1 = {n.name: n for n in ast.walk(tree1) if isinstance(n, ast.FunctionDef)}
        funcs2 = {n.name: n for n in ast.walk(tree2) if isinstance(n, ast.FunctionDef)}

        shared_funcs = set(funcs1.keys()) & set(funcs2.keys())
        only_in_1 = set(funcs1.keys()) - set(funcs2.keys())
        only_in_2 = set(funcs2.keys()) - set(funcs1.keys())

        similarities.append({
            "type": "shared_functions",
            "count": len(shared_funcs),
            "functions": list(shared_funcs),
        })

        differences.append({
            "type": "functions_only_in_code1",
            "count": len(only_in_1),
            "functions": list(only_in_1),
        })

        differences.append({
            "type": "functions_only_in_code2",
            "count": len(only_in_2),
            "functions": list(only_in_2),
        })

        return {
            "similarities": similarities,
            "differences": differences,
            "structural_diff": {
                "functions_added": len(only_in_2),
                "functions_removed": len(only_in_1),
                "functions_shared": len(shared_funcs),
            },
            "functional_diff": {
                "similarity_score": len(shared_funcs) / max(len(funcs1), len(funcs2), 1),
            },
        }


class RequirementMapper:
    """Mapper for code to requirements."""

    def __init__(self, requirements: List[str]):
        """Initialize requirement mapper."""
        self.requirements = requirements
        self.mappings: List[Dict[str, Any]] = []
        self.coverage: Dict[str, float] = {}
        self.uncovered_requirements: List[str] = []

    def visit(self, node: ast.AST) -> None:
        """Visit node and map to requirements."""
        # Simplified mapping - in full implementation would use NLP
        for req in self.requirements:
            # Check if requirement keywords appear in code
            req_lower = req.lower()
            if isinstance(node, ast.FunctionDef):
                func_name_lower = node.name.lower()
                if any(keyword in func_name_lower for keyword in req_lower.split()):
                    self.mappings.append({
                        "requirement": req,
                        "code_element": f"function:{node.name}",
                        "line": node.lineno,
                    })

        super().visit(node)


class DependencyAnalyzer(ast.NodeVisitor):
    """AST visitor for dependency analysis."""

    def __init__(self):
        """Initialize dependency analyzer."""
        self.imports: List[str] = []
        self.function_calls: List[str] = []
        self.class_uses: List[str] = []
        self.dependencies: Set[str] = set()

    def visit_Import(self, node: ast.Import) -> None:
        """Visit import statement."""
        for alias in node.names:
            self.imports.append(alias.name)
            self.dependencies.add(alias.name.split(".")[0])

    def visit_ImportFrom(self, node: ast.ImportFrom) -> None:
        """Visit import from statement."""
        if node.module:
            self.imports.append(node.module)
            self.dependencies.add(node.module.split(".")[0])

    def visit_Call(self, node: ast.Call) -> None:
        """Visit function call."""
        if isinstance(node.func, ast.Name):
            self.function_calls.append(node.func.id)
        elif isinstance(node.func, ast.Attribute):
            if isinstance(node.func.value, ast.Name):
                self.class_uses.append(node.func.value.id)

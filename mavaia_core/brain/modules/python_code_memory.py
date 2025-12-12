"""
Python Code Memory Module

Persistent storage and retrieval of Python code patterns, project structures,
coding styles, and code idioms. Enables learning from codebases and
maintaining persistent code knowledge across sessions.

This module is part of Mavaia's Python LLM capabilities, providing
long-term memory for code patterns and project-specific knowledge.
"""

import ast
import hashlib
import json
import sys
from collections import defaultdict
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Set

from mavaia_core.brain.base_module import BaseBrainModule, ModuleMetadata
from mavaia_core.exceptions import InvalidParameterError

# Lazy imports to avoid timeout during module discovery
    STORAGE_AVAILABLE = False
    BaseStorage = None
StorageConfig = None
    MemoryStorage = None
    MEMORY_GRAPH_AVAILABLE = False
    MemoryGraph = None

def _lazy_import_storage():
    """Lazy import storage systems only when needed"""
    global STORAGE_AVAILABLE, BaseStorage, StorageConfig, MemoryStorage
    if not STORAGE_AVAILABLE:
        try:
            from mavaia_core.brain.state_storage.base_storage import BaseStorage as BS, StorageConfig as SC
            from mavaia_core.brain.state_storage.memory_storage import MemoryStorage as MS
            BaseStorage = BS
            StorageConfig = SC
            MemoryStorage = MS
            STORAGE_AVAILABLE = True
        except ImportError:
            pass

def _lazy_import_memory_graph():
    """Lazy import memory graph only when needed"""
    global MEMORY_GRAPH_AVAILABLE, MemoryGraph
    if not MEMORY_GRAPH_AVAILABLE:
        try:
            from mavaia_core.brain.modules.memory_graph import MemoryGraph as MG
            MemoryGraph = MG
            MEMORY_GRAPH_AVAILABLE = True
        except ImportError:
            pass


class PythonCodeMemoryModule(BaseBrainModule):
    """
    Persistent memory for Python code patterns and project knowledge.
    
    Provides:
    - Code pattern storage and retrieval
    - Project structure learning
    - Code idiom library
    - Style preference memory
    - Cross-project pattern recognition
    """

    def __init__(self):
        """Initialize the code memory module."""
        super().__init__()
        self._storage: Optional[BaseStorage] = None
        self._memory_graph: Optional[MemoryGraph] = None
        self._pattern_cache: Dict[str, Dict[str, Any]] = {}
        self._project_cache: Dict[str, Dict[str, Any]] = {}
        self._style_cache: Dict[str, Dict[str, Any]] = {}

    @property
    def metadata(self) -> ModuleMetadata:
        """Return module metadata."""
        return ModuleMetadata(
            name="python_code_memory",
            version="1.0.0",
            description=(
                "Persistent memory for Python code: patterns, project structures, "
                "coding styles, and idioms. Enables learning from codebases."
            ),
            operations=[
                "remember_code_pattern",
                "recall_similar_patterns",
                "learn_project_structure",
                "get_code_idioms",
                "remember_code_style",
                "get_project_structure",
                "forget_pattern",
                "list_patterns",
                "list_projects",
            ],
            dependencies=[],
            model_required=False,
        )

    def initialize(self) -> bool:
        """Initialize the module."""
        # Don't initialize storage or memory graph here - they're heavy
        # Will initialize lazily when needed
        return True
    
    def _ensure_storage_initialized(self):
        """Lazy initialize storage only when needed"""
        _lazy_import_storage()
        if self._storage is None and STORAGE_AVAILABLE:
            try:
                config = StorageConfig(storage_type="memory")
                self._storage = MemoryStorage(config)
                self._storage.initialize()
            except Exception:
                pass  # Continue without persistent storage

    def _ensure_memory_graph_loaded(self):
        """Lazy load memory graph only when needed"""
        _lazy_import_memory_graph()
        if self._memory_graph is None and MEMORY_GRAPH_AVAILABLE:
            try:
                from mavaia_core.brain.registry import ModuleRegistry
                self._memory_graph = ModuleRegistry.get_module("memory_graph", auto_discover=True, wait_timeout=1.0)
            except Exception:
                pass  # Continue without memory graph

    def execute(self, operation: str, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute a code memory operation.
        
        Args:
            operation: Operation name
        """
        # Lazy initialize storage and memory graph if needed
        self._ensure_storage_initialized()
        self._ensure_memory_graph_loaded()
        if operation == "remember_code_pattern":
            pattern = params.get("pattern", "")
            context = params.get("context", {})
            if not pattern:
                raise InvalidParameterError("pattern", "", "Pattern cannot be empty")
            return self.remember_code_pattern(pattern, context)
        
        elif operation == "recall_similar_patterns":
            code = params.get("code", "")
            top_k = params.get("top_k", 5)
            if not code:
                raise InvalidParameterError("code", "", "Code cannot be empty")
            return self.recall_similar_patterns(code, top_k)
        
        elif operation == "learn_project_structure":
            project_path = params.get("project_path", "")
            if not project_path:
                raise InvalidParameterError("project_path", "", "Project path cannot be empty")
            return self.learn_project_structure(Path(project_path))
        
        elif operation == "get_code_idioms":
            language_feature = params.get("language_feature", "")
            return self.get_code_idioms(language_feature)
        
        elif operation == "remember_code_style":
            project = params.get("project", "")
            style = params.get("style", {})
            if not project:
                raise InvalidParameterError("project", "", "Project name cannot be empty")
            if not style:
                raise InvalidParameterError("style", {}, "Style cannot be empty")
            return self.remember_code_style(project, style)
        
        elif operation == "get_project_structure":
            project = params.get("project", "")
            if not project:
                raise InvalidParameterError("project", "", "Project name cannot be empty")
            return self.get_project_structure(project)
        
        elif operation == "forget_pattern":
            pattern_id = params.get("pattern_id", "")
            if not pattern_id:
                raise InvalidParameterError("pattern_id", "", "Pattern ID cannot be empty")
            return self.forget_pattern(pattern_id)
        
        elif operation == "list_patterns":
            pattern_type = params.get("pattern_type", None)
            return self.list_patterns(pattern_type)
        
        elif operation == "list_projects":
            return self.list_projects()
        
        else:
            raise ValueError(f"Unknown operation: {operation}")

    def remember_code_pattern(
        self,
        pattern: str,
        context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Store a code pattern in memory.
        
        Args:
            pattern: Code pattern to remember
            context: Context information (project, usage, description, etc.)
            
        Returns:
            Dictionary containing pattern ID and storage status
        """
        # Generate pattern ID
        pattern_hash = hashlib.md5(pattern.encode()).hexdigest()
        pattern_id = f"pattern_{pattern_hash[:16]}"

        # Extract pattern features
        pattern_info = {
            "id": pattern_id,
            "pattern": pattern,
            "context": context,
            "created_at": datetime.now().isoformat(),
            "usage_count": 0,
            "last_used": None,
        }

        # Extract pattern metadata
        try:
            tree = ast.parse(pattern)
            pattern_info["ast_features"] = self._extract_ast_features(tree)
        except SyntaxError:
            pattern_info["ast_features"] = {}

        # Store in cache
        self._pattern_cache[pattern_id] = pattern_info

        # Store in persistent storage if available
        if self._storage:
            try:
                self._storage.save(
                    state_type="code_pattern",
                    state_id=pattern_id,
                    state_data=pattern_info,
                    metadata={"created_at": pattern_info["created_at"]}
                )
            except Exception:
                pass  # Continue if storage fails

        # Add to memory graph if available
        if self._memory_graph:
            try:
                # Create node for pattern
                self._memory_graph.execute("add_node", {
                    "node_id": pattern_id,
                    "node_type": "code_pattern",
                    "properties": pattern_info,
                })
            except Exception:
                pass  # Continue if graph fails

        return {
            "success": True,
            "pattern_id": pattern_id,
            "pattern": pattern,
        }

    def recall_similar_patterns(
        self,
        code: str,
        top_k: int = 5
    ) -> Dict[str, Any]:
        """
        Recall similar code patterns from memory.
        
        Args:
            code: Code to find similar patterns for
            top_k: Number of top patterns to return
            
        Returns:
            Dictionary containing similar patterns with similarity scores
        """
        # Load patterns from cache and storage
        all_patterns = self._load_all_patterns()

        # Calculate similarity (simple AST-based for now)
        similarities = []
        try:
            code_tree = ast.parse(code)
            code_features = self._extract_ast_features(code_tree)
        except SyntaxError:
            code_features = {}

        for pattern_id, pattern_info in all_patterns.items():
            pattern_features = pattern_info.get("ast_features", {})
            similarity = self._calculate_pattern_similarity(code_features, pattern_features)
            
            similarities.append({
                "pattern_id": pattern_id,
                "pattern": pattern_info["pattern"],
                "context": pattern_info.get("context", {}),
                "similarity": similarity,
                "usage_count": pattern_info.get("usage_count", 0),
            })

        # Sort by similarity
        similarities.sort(key=lambda x: x["similarity"], reverse=True)

        # Update usage counts
        for pattern in similarities[:top_k]:
            pattern_id = pattern["pattern_id"]
            if pattern_id in self._pattern_cache:
                self._pattern_cache[pattern_id]["usage_count"] += 1
                self._pattern_cache[pattern_id]["last_used"] = datetime.now().isoformat()

        return {
            "code": code,
            "similar_patterns": similarities[:top_k],
            "total_patterns": len(all_patterns),
        }

    def learn_project_structure(self, project_path: Path) -> Dict[str, Any]:
        """
        Learn the structure of a Python project.
        
        Args:
            project_path: Path to project root
            
        Returns:
            Dictionary containing learned project structure
        """
        if not project_path.exists():
            return {
                "success": False,
                "error": f"Project path does not exist: {project_path}",
            }

        project_name = project_path.name
        structure = {
            "project_name": project_name,
            "root_path": str(project_path),
            "learned_at": datetime.now().isoformat(),
            "modules": [],
            "packages": [],
            "files": [],
            "imports": [],
            "structure": {},
        }

        # Discover Python files
        python_files = list(project_path.rglob("*.py"))
        structure["files"] = [str(f.relative_to(project_path)) for f in python_files]

        # Analyze structure
        for py_file in python_files:
            try:
                with open(py_file, "r", encoding="utf-8") as f:
                    content = f.read()
                
                tree = ast.parse(content)
                
                # Extract modules and packages
                rel_path = py_file.relative_to(project_path)
                if rel_path.name == "__init__.py":
                    structure["packages"].append(str(rel_path.parent))
                else:
                    structure["modules"].append(str(rel_path))

                # Extract imports
                for node in ast.walk(tree):
                    if isinstance(node, ast.Import):
                        for alias in node.names:
                            structure["imports"].append(alias.name)
                    elif isinstance(node, ast.ImportFrom):
                        if node.module:
                            structure["imports"].append(node.module)

            except Exception:
                continue

        # Store project structure
        self._project_cache[project_name] = structure

        # Store in persistent storage
        if self._storage:
            try:
                self._storage.save(
                    state_type="project_structure",
                    state_id=project_name,
                    state_data=structure,
                    metadata={"learned_at": structure["learned_at"]}
                )
            except Exception:
                pass

        return {
            "success": True,
            "project": project_name,
            "structure": structure,
        }

    def get_code_idioms(self, language_feature: str = "") -> Dict[str, Any]:
        """
        Get Python code idioms for a language feature.
        
        Args:
            language_feature: Language feature (e.g., "list_comprehension", "decorator")
            
        Returns:
            Dictionary containing code idioms
        """
        # Built-in Python idioms
        idioms = {
            "list_comprehension": [
                "[x for x in iterable]",
                "[x for x in iterable if condition]",
                "[f(x) for x in iterable]",
            ],
            "dictionary_comprehension": [
                "{k: v for k, v in items}",
                "{k: v for k, v in items if condition}",
            ],
            "generator_expression": [
                "(x for x in iterable)",
                "(f(x) for x in iterable if condition)",
            ],
            "context_manager": [
                "with open(file) as f:",
                "with context_manager() as cm:",
            ],
            "decorator": [
                "@decorator\ndef function():",
                "@property\ndef attribute(self):",
            ],
            "lambda": [
                "lambda x: x * 2",
                "lambda x, y: x + y",
            ],
            "unpacking": [
                "a, b = values",
                "*args, **kwargs",
            ],
        }

        if language_feature:
            return {
                "language_feature": language_feature,
                "idioms": idioms.get(language_feature, []),
            }

        return {
            "all_idioms": idioms,
        }

    def remember_code_style(
        self,
        project: str,
        style: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Remember coding style preferences for a project.
        
        Args:
            project: Project name
            style: Style preferences (indentation, naming, etc.)
            
        Returns:
            Dictionary containing storage status
        """
        style_info = {
            "project": project,
            "style": style,
            "updated_at": datetime.now().isoformat(),
        }

        self._style_cache[project] = style_info

        # Store in persistent storage
        if self._storage:
            try:
                self._storage.save(
                    state_type="code_style",
                    state_id=project,
                    state_data=style_info,
                    metadata={"updated_at": style_info["updated_at"]}
                )
            except Exception:
                pass

        return {
            "success": True,
            "project": project,
            "style": style,
        }

    def get_project_structure(self, project: str) -> Dict[str, Any]:
        """
        Get learned project structure.
        
        Args:
            project: Project name
            
        Returns:
            Dictionary containing project structure
        """
        # Check cache first
        if project in self._project_cache:
            return {
                "success": True,
                "project": project,
                "structure": self._project_cache[project],
            }

        # Try to load from storage
        if self._storage:
            try:
                structure = self._storage.load("project_structure", project)
                if structure:
                    self._project_cache[project] = structure
                    return {
                        "success": True,
                        "project": project,
                        "structure": structure,
                    }
            except Exception:
                pass

        return {
            "success": False,
            "error": f"Project structure not found: {project}",
        }

    def forget_pattern(self, pattern_id: str) -> Dict[str, Any]:
        """
        Remove a pattern from memory.
        
        Args:
            pattern_id: Pattern ID to forget
            
        Returns:
            Dictionary containing deletion status
        """
        # Remove from cache
        if pattern_id in self._pattern_cache:
            del self._pattern_cache[pattern_id]

        # Remove from storage
        if self._storage:
            try:
                self._storage.delete("code_pattern", pattern_id)
            except Exception:
                pass

        # Remove from memory graph
        if self._memory_graph:
            try:
                self._memory_graph.execute("remove_node", {"node_id": pattern_id})
            except Exception:
                pass

        return {
            "success": True,
            "pattern_id": pattern_id,
        }

    def list_patterns(self, pattern_type: Optional[str] = None) -> Dict[str, Any]:
        """
        List all stored patterns.
        
        Args:
            pattern_type: Optional pattern type filter
            
        Returns:
            Dictionary containing list of patterns
        """
        all_patterns = self._load_all_patterns()

        patterns = []
        for pattern_id, pattern_info in all_patterns.items():
            if pattern_type is None or pattern_info.get("context", {}).get("type") == pattern_type:
                patterns.append({
                    "pattern_id": pattern_id,
                    "pattern": pattern_info["pattern"],
                    "context": pattern_info.get("context", {}),
                    "usage_count": pattern_info.get("usage_count", 0),
                    "created_at": pattern_info.get("created_at"),
                })

        return {
            "patterns": patterns,
            "count": len(patterns),
        }

    def list_projects(self) -> Dict[str, Any]:
        """
        List all learned projects.
        
        Returns:
            Dictionary containing list of projects
        """
        # Load from cache and storage
        all_projects = {}
        all_projects.update(self._project_cache)

        if self._storage:
            try:
                # Try to list all project structures
                # (This is a simplified version - full implementation would list states)
                pass
            except Exception:
                pass

        return {
            "projects": list(all_projects.keys()),
            "count": len(all_projects),
        }

    def _load_all_patterns(self) -> Dict[str, Dict[str, Any]]:
        """Load all patterns from cache and storage."""
        patterns = {}
        patterns.update(self._pattern_cache)

        # Try to load from storage
        if self._storage:
            # Simplified - would need list_states operation
            pass

        return patterns

    def _extract_ast_features(self, tree: ast.AST) -> Dict[str, Any]:
        """Extract features from AST for pattern matching."""
        features = {
            "node_types": defaultdict(int),
            "function_count": 0,
            "class_count": 0,
            "import_count": 0,
        }

        for node in ast.walk(tree):
            node_type = type(node).__name__
            features["node_types"][node_type] += 1

            if isinstance(node, ast.FunctionDef):
                features["function_count"] += 1
            elif isinstance(node, ast.ClassDef):
                features["class_count"] += 1
            elif isinstance(node, (ast.Import, ast.ImportFrom)):
                features["import_count"] += 1

        return features

    def _calculate_pattern_similarity(
        self,
        features1: Dict[str, Any],
        features2: Dict[str, Any]
    ) -> float:
        """Calculate similarity between two pattern feature sets."""
        if not features1 or not features2:
            return 0.0

        # Simple similarity based on node type overlap
        node_types1 = set(features1.get("node_types", {}).keys())
        node_types2 = set(features2.get("node_types", {}).keys())

        if not node_types1 or not node_types2:
            return 0.0

        intersection = len(node_types1 & node_types2)
        union = len(node_types1 | node_types2)

        if union == 0:
            return 0.0

        return intersection / union

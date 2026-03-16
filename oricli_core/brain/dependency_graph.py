from __future__ import annotations
"""
Dependency Graph Management

Manages module dependencies, detects cycles, and determines load order.
"""

from typing import Dict, List, Set, Optional, Tuple
from collections import defaultdict, deque

from oricli_core.brain.registry import ModuleRegistry
from oricli_core.brain.base_module import ModuleMetadata
from oricli_core.exceptions import RegistryError


class DependencyGraph:
    """
    Dependency graph for brain modules
    
    Tracks module dependencies and provides topological sorting
    for correct load order.
    """
    
    def __init__(self):
        """Initialize dependency graph"""
        self._graph: Dict[str, Set[str]] = defaultdict(set)  # module -> dependencies
        self._reverse_graph: Dict[str, Set[str]] = defaultdict(set)  # module -> dependents
        self._modules: Dict[str, ModuleMetadata] = {}
    
    def add_module(self, module_name: str, metadata: ModuleMetadata) -> None:
        """
        Add module to dependency graph
        
        Args:
            module_name: Name of the module
            metadata: Module metadata with dependencies
        """
        self._modules[module_name] = metadata
        
        # Extract dependencies from metadata
        # Dependencies can be in metadata.dependencies or inferred from operations
        dependencies = self._extract_dependencies(metadata)
        
        self._graph[module_name] = dependencies
        
        # Update reverse graph
        for dep in dependencies:
            self._reverse_graph[dep].add(module_name)
    
    def _extract_dependencies(self, metadata: ModuleMetadata) -> Set[str]:
        """
        Extract module dependencies from metadata
        
        Args:
            metadata: Module metadata
        
        Returns:
            Set of dependency module names
        """
        dependencies: Set[str] = set()

        # Honor explicit dependency declarations when present.
        explicit = getattr(metadata, "dependencies", None)
        if explicit:
            try:
                for dep in explicit:
                    if isinstance(dep, str) and dep.strip():
                        dependencies.add(dep.strip())
            except TypeError:
                pass

        # Backward-compatible inference for older modules that don't declare dependencies.
        if not dependencies and metadata.name == "cognitive_generator":
            dependencies.update(
                [
                    "thought_to_text",
                    "memory_graph",
                    "reasoning",
                    "embeddings",
                    "personality_response",
                ]
            )

        return dependencies
    
    def detect_cycles(self) -> List[List[str]]:
        """
        Detect circular dependencies
        
        Returns:
            List of cycles (each cycle is a list of module names)
        """
        cycles = []
        visited: Set[str] = set()
        rec_stack: Set[str] = set()
        path: List[str] = []
        
        def dfs(node: str) -> None:
            """Depth-first search to detect cycles"""
            visited.add(node)
            rec_stack.add(node)
            path.append(node)
            
            for neighbor in self._graph.get(node, set()):
                if neighbor not in visited:
                    dfs(neighbor)
                elif neighbor in rec_stack:
                    # Found a cycle
                    cycle_start = path.index(neighbor)
                    cycles.append(path[cycle_start:] + [neighbor])
            
            rec_stack.remove(node)
            path.pop()
        
        for module in self._graph.keys():
            if module not in visited:
                dfs(module)
        
        return cycles
    
    def get_load_order(self) -> List[str]:
        """
        Get topological sort order for module loading
        
        Returns:
            List of module names in correct load order
        
        Raises:
            RegistryError: If circular dependencies detected
        """
        cycles = self.detect_cycles()
        if cycles:
            raise RegistryError(
                f"Circular dependencies detected: {cycles}"
            )
        
        # Topological sort using Kahn's algorithm
        in_degree: Dict[str, int] = defaultdict(int)
        
        # Calculate in-degrees
        for module in self._graph.keys():
            in_degree[module] = 0
        
        for module, deps in self._graph.items():
            for dep in deps:
                if dep in in_degree:
                    in_degree[module] += 1
        
        # Find all modules with no incoming edges
        queue = deque([m for m, degree in in_degree.items() if degree == 0])
        result = []
        
        while queue:
            module = queue.popleft()
            result.append(module)
            
            # Remove this module and update in-degrees
            for dependent in self._reverse_graph.get(module, set()):
                if dependent in in_degree:
                    in_degree[dependent] -= 1
                    if in_degree[dependent] == 0:
                        queue.append(dependent)
        
        # Check for remaining modules (shouldn't happen if no cycles)
        remaining = [m for m, degree in in_degree.items() if degree > 0]
        if remaining:
            raise RegistryError(
                f"Could not resolve dependencies for modules: {remaining}"
            )
        
        return result
    
    def get_dependencies(self, module_name: str) -> Set[str]:
        """
        Get direct dependencies for a module
        
        Args:
            module_name: Name of the module
        
        Returns:
            Set of dependency module names
        """
        return self._graph.get(module_name, set()).copy()
    
    def get_dependents(self, module_name: str) -> Set[str]:
        """
        Get modules that depend on this module
        
        Args:
            module_name: Name of the module
        
        Returns:
            Set of dependent module names
        """
        return self._reverse_graph.get(module_name, set()).copy()
    
    def get_all_dependencies(self, module_name: str) -> Set[str]:
        """
        Get all transitive dependencies for a module
        
        Args:
            module_name: Name of the module
        
        Returns:
            Set of all dependency module names (transitive)
        """
        visited: Set[str] = set()
        
        def dfs(node: str) -> None:
            """Depth-first search to collect all dependencies"""
            if node in visited:
                return
            visited.add(node)
            
            for dep in self._graph.get(node, set()):
                dfs(dep)
        
        dfs(module_name)
        visited.discard(module_name)  # Remove self
        return visited
    
    def validate_dependencies(self) -> Tuple[bool, List[str]]:
        """
        Validate that all declared dependencies exist
        
        Returns:
            Tuple of (is_valid, list_of_missing_dependencies)
        """
        missing = []
        
        for module_name, deps in self._graph.items():
            for dep in deps:
                if dep not in self._modules:
                    missing.append(f"{module_name} -> {dep}")
        
        return len(missing) == 0, missing


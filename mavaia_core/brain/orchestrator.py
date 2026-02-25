from __future__ import annotations
"""
Module Orchestrator

Orchestrates module loading, dependency resolution, and lifecycle management.
"""

from typing import Dict, List, Optional, Set, Any
from pathlib import Path

from mavaia_core.brain.registry import ModuleRegistry
from mavaia_core.brain.base_module import BaseBrainModule, ModuleMetadata
from mavaia_core.brain.dependency_graph import DependencyGraph
from mavaia_core.brain.module_lifecycle import ModuleLifecycle, ModuleState
from mavaia_core.exceptions import (
    ModuleNotFoundError,
    ModuleInitializationError,
    RegistryError,
)


class ModuleOrchestrator:
    """
    Orchestrates module discovery, loading, and lifecycle management
    
    Provides:
    - Automatic dependency resolution
    - Correct load order
    - Lifecycle management
    - Module composition
    """
    
    def __init__(self):
        """Initialize orchestrator"""
        self.dependency_graph = DependencyGraph()
        self.lifecycle = ModuleLifecycle()
        self._initialized = False
    
    def initialize(self) -> None:
        """Initialize orchestrator and build dependency graph"""
        if self._initialized:
            return
        
        # Build dependency graph from discovered modules
        ModuleRegistry.discover_modules()
        
        for module_name in ModuleRegistry.list_modules():
            metadata = ModuleRegistry.get_metadata(module_name)
            if metadata:
                self.dependency_graph.add_module(module_name, metadata)
        
        # Validate dependencies
        is_valid, missing = self.dependency_graph.validate_dependencies()
        if not is_valid:
            print(f"[Orchestrator] Warning: Missing dependencies: {missing}")
        
        # Check for cycles
        cycles = self.dependency_graph.detect_cycles()
        if cycles:
            print(f"[Orchestrator] Warning: Circular dependencies detected: {cycles}")
        
        self._initialized = True
    
    def load_module(
        self,
        module_name: str,
        load_dependencies: bool = True
    ) -> Optional[BaseBrainModule]:
        """
        Load a module and its dependencies
        
        Args:
            module_name: Name of module to load
            load_dependencies: Whether to load dependencies first
        
        Returns:
            Loaded module instance or None if failed
        
        Raises:
            ModuleNotFoundError: If module not found
            ModuleInitializationError: If initialization fails
        """
        # Initialize if needed
        if not self._initialized:
            self.initialize()
        
        # Check if module exists
        if not ModuleRegistry.is_module_available(module_name):
            raise ModuleNotFoundError(module_name)
        
        # Load dependencies first if requested
        if load_dependencies:
            deps = self.dependency_graph.get_all_dependencies(module_name)
            for dep in deps:
                if dep != module_name:
                    self.load_module(dep, load_dependencies=False)
        
        # Get module instance - use availability manager if available
        module = None
        try:
            from mavaia_core.brain.availability import get_availability_manager
            availability_manager = get_availability_manager()
            
            if availability_manager._initialized:
                # Use availability manager to ensure module is available
                module, actual_name, is_fallback = availability_manager.get_module_or_fallback(
                    module_name
                )
                if is_fallback:
                    # Log that fallback was used
                    print(f"[Orchestrator] Using fallback {actual_name} for {module_name}")
            else:
                # Availability manager not initialized, use registry directly
                module = ModuleRegistry.get_module(module_name)
        except Exception:
            # Availability manager not available, use registry directly
            module = ModuleRegistry.get_module(module_name)
        
        if module is None:
            raise ModuleNotFoundError(module_name)
        
        # Register with lifecycle
        self.lifecycle.register_module(module_name, module)
        
        # Initialize module
        self.lifecycle.transition(
            module_name,
            ModuleState.INITIALIZING,
            reason="Orchestrator loading module"
        )
        
        try:
            if module.initialize():
                self.lifecycle.transition(
                    module_name,
                    ModuleState.INITIALIZED,
                    reason="Initialization successful"
                )
                self.lifecycle.transition(
                    module_name,
                    ModuleState.READY,
                    reason="Module ready"
                )
            else:
                self.lifecycle.transition(
                    module_name,
                    ModuleState.ERROR,
                    reason="Initialization returned False"
                )
                raise ModuleInitializationError(
                    module_name,
                    "initialize() returned False"
                )
        except Exception as e:
            self.lifecycle.transition(
                module_name,
                ModuleState.ERROR,
                reason=f"Initialization exception: {str(e)}"
            )
            raise ModuleInitializationError(module_name, str(e)) from e
        
        return module
    
    def load_modules_in_order(self, module_names: List[str]) -> Dict[str, BaseBrainModule]:
        """
        Load multiple modules in correct dependency order
        
        Args:
            module_names: List of module names to load
        
        Returns:
            Dictionary mapping module names to loaded instances
        """
        if not self._initialized:
            self.initialize()
        
        # Get load order
        all_deps = set()
        for module_name in module_names:
            all_deps.update(self.dependency_graph.get_all_dependencies(module_name))
            all_deps.add(module_name)
        
        # Get topological order
        load_order = self.dependency_graph.get_load_order()
        
        # Filter to only requested modules and their dependencies
        filtered_order = [m for m in load_order if m in all_deps]
        
        # Load in order
        loaded = {}
        for module_name in filtered_order:
            try:
                module = self.load_module(module_name, load_dependencies=False)
                if module:
                    loaded[module_name] = module
            except Exception as e:
                print(f"[Orchestrator] Failed to load {module_name}: {e}")
        
        return loaded
    
    def get_load_order(self, module_names: Optional[List[str]] = None) -> List[str]:
        """
        Get recommended load order for modules
        
        Args:
            module_names: Optional list of specific modules, otherwise all
        
        Returns:
            List of module names in load order
        """
        if not self._initialized:
            self.initialize()
        
        if module_names:
            # Get order for specific modules
            all_deps = set()
            for module_name in module_names:
                all_deps.update(self.dependency_graph.get_all_dependencies(module_name))
                all_deps.add(module_name)
            
            full_order = self.dependency_graph.get_load_order()
            return [m for m in full_order if m in all_deps]
        else:
            return self.dependency_graph.get_load_order()
    
    def compose_modules(
        self,
        module_names: List[str],
        operation: str,
        params: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Compose multiple modules to execute an operation
        
        Args:
            module_names: List of module names to compose
            operation: Operation name
            params: Operation parameters
        
        Returns:
            Combined results from all modules
        """
        results = {}
        
        for module_name in module_names:
            try:
                module = self.load_module(module_name)
                if module:
                    self.lifecycle.transition(
                        module_name,
                        ModuleState.RUNNING,
                        reason=f"Executing {operation}"
                    )
                    
                    result = module.execute(operation, params)
                    results[module_name] = result
                    
                    self.lifecycle.transition(
                        module_name,
                        ModuleState.READY,
                        reason="Operation completed"
                    )
            except Exception as e:
                results[module_name] = {"error": str(e)}
        
        return results
    
    def get_module_state(self, module_name: str) -> Optional[ModuleState]:
        """
        Get current state of a module
        
        Args:
            module_name: Name of the module
        
        Returns:
            Current module state or None
        """
        return self.lifecycle.get_state(module_name)
    
    def get_all_states(self) -> Dict[str, ModuleState]:
        """
        Get states of all managed modules
        
        Returns:
            Dictionary mapping module names to states
        """
        return self.lifecycle.get_all_states()


from __future__ import annotations
"""
Module Lifecycle Management

Manages module lifecycle states and transitions.
"""

from enum import Enum
from typing import Dict, Optional, Callable, Any
from dataclasses import dataclass
from datetime import datetime
from collections import defaultdict

from oricli_core.brain.base_module import BaseBrainModule


class ModuleState(Enum):
    """Module lifecycle states"""
    UNINITIALIZED = "uninitialized"
    INITIALIZING = "initializing"
    INITIALIZED = "initialized"
    READY = "ready"
    RUNNING = "running"
    ERROR = "error"
    SHUTTING_DOWN = "shutting_down"
    SHUTDOWN = "shutdown"


@dataclass
class LifecycleEvent:
    """Lifecycle event record"""
    module_name: str
    from_state: ModuleState
    to_state: ModuleState
    timestamp: datetime
    reason: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None


class ModuleLifecycle:
    """
    Manages module lifecycle states and transitions
    """
    
    def __init__(self):
        """Initialize lifecycle manager"""
        self._states: Dict[str, ModuleState] = {}
        self._modules: Dict[str, BaseBrainModule] = {}
        self._history: Dict[str, list[LifecycleEvent]] = {}
        self._hooks: Dict[ModuleState, list[Callable]] = defaultdict(list)
    
    def register_module(self, module_name: str, module: BaseBrainModule) -> None:
        """
        Register a module for lifecycle management
        
        Args:
            module_name: Name of the module
            module: Module instance
        """
        self._modules[module_name] = module
        self._states[module_name] = ModuleState.UNINITIALIZED
        self._history[module_name] = []
    
    def get_state(self, module_name: str) -> Optional[ModuleState]:
        """
        Get current state of a module
        
        Args:
            module_name: Name of the module
        
        Returns:
            Current module state or None if not registered
        """
        return self._states.get(module_name)
    
    def transition(
        self,
        module_name: str,
        to_state: ModuleState,
        reason: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> bool:
        """
        Transition module to a new state
        
        Args:
            module_name: Name of the module
            to_state: Target state
            reason: Optional reason for transition
            metadata: Optional metadata
        
        Returns:
            True if transition succeeded, False otherwise
        """
        if module_name not in self._states:
            return False
        
        from_state = self._states[module_name]
        
        # Validate transition
        if not self._is_valid_transition(from_state, to_state):
            return False
        
        # Execute hooks
        for hook in self._hooks.get(to_state, []):
            try:
                hook(module_name, from_state, to_state)
            except Exception as e:
                print(f"[ModuleLifecycle] Hook failed for {module_name}: {e}")
        
        # Perform transition
        self._states[module_name] = to_state
        
        # Record event
        event = LifecycleEvent(
            module_name=module_name,
            from_state=from_state,
            to_state=to_state,
            timestamp=datetime.now(),
            reason=reason,
            metadata=metadata
        )
        self._history[module_name].append(event)
        
        return True
    
    def _is_valid_transition(
        self,
        from_state: ModuleState,
        to_state: ModuleState
    ) -> bool:
        """
        Check if transition is valid
        
        Args:
            from_state: Current state
            to_state: Target state
        
        Returns:
            True if transition is valid
        """
        # Define valid transitions
        valid_transitions = {
            ModuleState.UNINITIALIZED: [
                ModuleState.INITIALIZING,
                ModuleState.ERROR
            ],
            ModuleState.INITIALIZING: [
                ModuleState.INITIALIZED,
                ModuleState.ERROR
            ],
            ModuleState.INITIALIZED: [
                ModuleState.READY,
                ModuleState.ERROR,
                ModuleState.SHUTTING_DOWN
            ],
            ModuleState.READY: [
                ModuleState.RUNNING,
                ModuleState.SHUTTING_DOWN,
                ModuleState.ERROR
            ],
            ModuleState.RUNNING: [
                ModuleState.READY,
                ModuleState.SHUTTING_DOWN,
                ModuleState.ERROR
            ],
            ModuleState.ERROR: [
                ModuleState.UNINITIALIZED,
                ModuleState.SHUTTING_DOWN
            ],
            ModuleState.SHUTTING_DOWN: [
                ModuleState.SHUTDOWN
            ],
            ModuleState.SHUTDOWN: []  # Terminal state
        }
        
        return to_state in valid_transitions.get(from_state, [])
    
    def add_hook(
        self,
        state: ModuleState,
        hook: Callable[[str, ModuleState, ModuleState], None]
    ) -> None:
        """
        Add lifecycle hook
        
        Args:
            state: State to hook into
            hook: Hook function (module_name, from_state, to_state) -> None
        """
        self._hooks[state].append(hook)
    
    def get_history(self, module_name: str) -> list[LifecycleEvent]:
        """
        Get lifecycle history for a module
        
        Args:
            module_name: Name of the module
        
        Returns:
            List of lifecycle events
        """
        return self._history.get(module_name, []).copy()
    
    def get_all_states(self) -> Dict[str, ModuleState]:
        """
        Get all module states
        
        Returns:
            Dictionary mapping module names to states
        """
        return self._states.copy()


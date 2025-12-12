"""
Solver Manager - Manages lifecycle of symbolic solvers
"""

from typing import Dict, Any, Optional, List
import time
from dataclasses import dataclass
from enum import Enum


class SolverStatus(Enum):
    """Status of a solver"""

    UNINITIALIZED = "uninitialized"
    INITIALIZING = "initializing"
    READY = "ready"
    ERROR = "error"
    UNAVAILABLE = "unavailable"


@dataclass
class SolverInfo:
    """Information about a solver"""

    name: str
    status: SolverStatus
    is_available: bool
    initialization_time: Optional[float] = None
    last_used: Optional[float] = None
    error_message: Optional[str] = None


class SolverManager:
    """Manages solver lifecycle and availability"""

    def __init__(self):
        self._solvers: Dict[str, SolverInfo] = {}
        self._solver_instances: Dict[str, Any] = {}

    def register_solver(self, name: str, solver_instance: Any) -> bool:
        """Register a solver instance"""
        try:
            # Test if solver is available
            if hasattr(solver_instance, "is_available"):
                is_available = solver_instance.is_available()
            else:
                is_available = True

            self._solvers[name] = SolverInfo(
                name=name,
                status=SolverStatus.READY if is_available else SolverStatus.UNAVAILABLE,
                is_available=is_available,
                initialization_time=time.time(),
            )
            self._solver_instances[name] = solver_instance
            return True
        except Exception as e:
            self._solvers[name] = SolverInfo(
                name=name,
                status=SolverStatus.ERROR,
                is_available=False,
                error_message=str(e),
            )
            return False

    def get_solver(self, name: str) -> Optional[Any]:
        """Get a solver instance by name"""
        if name in self._solver_instances:
            # Update last used time
            if name in self._solvers:
                self._solvers[name].last_used = time.time()
            return self._solver_instances[name]
        return None

    def is_solver_available(self, name: str) -> bool:
        """Check if a solver is available"""
        if name not in self._solvers:
            return False
        return (
            self._solvers[name].is_available
            and self._solvers[name].status == SolverStatus.READY
        )

    def get_available_solvers(self) -> List[str]:
        """Get list of available solver names"""
        return [name for name, info in self._solvers.items() if info.is_available]

    def get_solver_info(self, name: str) -> Optional[SolverInfo]:
        """Get information about a solver"""
        return self._solvers.get(name)

    def mark_solver_error(self, name: str, error_message: str):
        """Mark a solver as having an error"""
        if name in self._solvers:
            self._solvers[name].status = SolverStatus.ERROR
            self._solvers[name].is_available = False
            self._solvers[name].error_message = error_message

    def cleanup(self):
        """Cleanup all solver resources"""
        for solver in self._solver_instances.values():
            if hasattr(solver, "cleanup"):
                try:
                    solver.cleanup()
                except Exception:
                    pass
        self._solver_instances.clear()
        self._solvers.clear()


# Global solver manager instance
_solver_manager = SolverManager()


def get_solver_manager() -> SolverManager:
    """Get the global solver manager instance"""
    return _solver_manager

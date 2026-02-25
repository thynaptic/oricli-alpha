from __future__ import annotations
"""
Solver Router - Automatically selects appropriate solver based on problem type
"""

from typing import Dict, Any, Optional, List
import logging

from mavaia_core.exceptions import InvalidParameterError, ModuleInitializationError, ModuleOperationError

logger = logging.getLogger(__name__)

# Try relative imports first (when imported as part of package), fallback to absolute
try:
    from .solver_manager import get_solver_manager, SolverManager
    from .z3_solver import Z3Solver
    from .pysat_solver import PySATSolver
    from .sympy_solver import SymPySolver
    from .prolog_bridge import PrologBridge
except ImportError:
    # Fallback to absolute imports if relative imports fail
    from mavaia_core.brain.modules.symbolic_solvers.solver_manager import get_solver_manager, SolverManager
    from mavaia_core.brain.modules.symbolic_solvers.z3_solver import Z3Solver
    from mavaia_core.brain.modules.symbolic_solvers.pysat_solver import PySATSolver
    from mavaia_core.brain.modules.symbolic_solvers.sympy_solver import SymPySolver
    from mavaia_core.brain.modules.symbolic_solvers.prolog_bridge import PrologBridge


class SolverRouter:
    """Routes problems to appropriate solvers"""

    def __init__(self):
        self._manager = get_solver_manager()
        self._initialize_solvers()

    def _initialize_solvers(self):
        """Initialize all available solvers"""
        # Register Z3
        try:
            z3_solver = Z3Solver()
            if z3_solver.is_available():
                self._manager.register_solver("z3", z3_solver)
        except Exception as e:
            logger.debug(
                "Failed to initialize z3 solver",
                exc_info=True,
                extra={"solver": "z3", "error_type": type(e).__name__},
            )

        # Register PySAT
        try:
            pysat_solver = PySATSolver()
            if pysat_solver.is_available():
                self._manager.register_solver("pysat", pysat_solver)
        except Exception as e:
            logger.debug(
                "Failed to initialize pysat solver",
                exc_info=True,
                extra={"solver": "pysat", "error_type": type(e).__name__},
            )

        # Register SymPy
        try:
            sympy_solver = SymPySolver()
            if sympy_solver.is_available():
                self._manager.register_solver("sympy", sympy_solver)
        except Exception as e:
            logger.debug(
                "Failed to initialize sympy solver",
                exc_info=True,
                extra={"solver": "sympy", "error_type": type(e).__name__},
            )

        # Register Prolog
        try:
            prolog_solver = PrologBridge()
            if prolog_solver.is_available():
                self._manager.register_solver("prolog", prolog_solver)
        except Exception as e:
            logger.debug(
                "Failed to initialize prolog solver",
                exc_info=True,
                extra={"solver": "prolog", "error_type": type(e).__name__},
            )

    def select_solver(self, problem: Dict[str, Any]) -> Optional[str]:
        """
        Select appropriate solver for a problem

        Args:
            problem: Problem dictionary with problem_type field

        Returns:
            Solver name or None if no suitable solver
        """
        if not isinstance(problem, dict):
            raise InvalidParameterError("problem", str(type(problem).__name__), "problem must be a dict")
        problem_type = problem.get("problem_type", "unknown")
        if not isinstance(problem_type, str):
            problem_type = str(problem_type)

        # Map problem types to preferred solvers
        solver_preferences = {
            "sat": ["pysat", "z3"],
            "smt": ["z3"],
            "csp": ["z3"],
            "symbolic_math": ["sympy"],
            "logic_programming": ["prolog"],
            "planning": ["z3", "prolog"],
            "verification": ["z3"],
        }

        preferred = solver_preferences.get(problem_type, ["z3"])  # Default to Z3

        # Find first available preferred solver
        for solver_name in preferred:
            if self._manager.is_solver_available(solver_name):
                return solver_name

        # Fallback: try any available solver
        available = self._manager.get_available_solvers()
        if available:
            return available[0]

        return None

    def solve(self, problem: Dict[str, Any]) -> Dict[str, Any]:
        """
        Solve a problem using the best available solver

        Args:
            problem: Problem dictionary

        Returns:
            Solution dictionary
        """
        solver_name = self.select_solver(problem)
        if not solver_name:
            raise ModuleInitializationError(
                module_name="symbolic_solver",
                reason=f"No available solver for problem_type={problem.get('problem_type', 'unknown')}",
            )

        solver = self._manager.get_solver(solver_name)
        if not solver:
            raise ModuleInitializationError(
                module_name="symbolic_solver",
                reason=f"Solver '{solver_name}' not found",
            )

        try:
            return solver.solve(problem)
        except (InvalidParameterError, ModuleInitializationError, ModuleOperationError):
            raise
        except Exception as e:
            logger.debug(
                "Solver execution failed",
                exc_info=True,
                extra={"solver": solver_name, "error_type": type(e).__name__},
            )
            raise ModuleOperationError(
                module_name="symbolic_solver",
                operation="solve",
                reason=f"Solver '{solver_name}' failed",
            ) from e

    def get_available_solvers(self) -> List[str]:
        """Get list of available solver names"""
        return self._manager.get_available_solvers()

    def cleanup(self):
        """Cleanup all solver resources"""
        self._manager.cleanup()


# Global router instance
_router = None


def get_solver_router() -> SolverRouter:
    """Get the global solver router instance"""
    global _router
    if _router is None:
        _router = SolverRouter()
    return _router

"""
Solver Router - Automatically selects appropriate solver based on problem type
"""

from typing import Dict, Any, Optional, List

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
        except Exception:
            pass

        # Register PySAT
        try:
            pysat_solver = PySATSolver()
            if pysat_solver.is_available():
                self._manager.register_solver("pysat", pysat_solver)
        except Exception:
            pass

        # Register SymPy
        try:
            sympy_solver = SymPySolver()
            if sympy_solver.is_available():
                self._manager.register_solver("sympy", sympy_solver)
        except Exception:
            pass

        # Register Prolog
        try:
            prolog_solver = PrologBridge()
            if prolog_solver.is_available():
                self._manager.register_solver("prolog", prolog_solver)
        except Exception:
            pass

    def select_solver(self, problem: Dict[str, Any]) -> Optional[str]:
        """
        Select appropriate solver for a problem

        Args:
            problem: Problem dictionary with problem_type field

        Returns:
            Solver name or None if no suitable solver
        """
        problem_type = problem.get("problem_type", "unknown")

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
            raise RuntimeError(
                "No available solver for problem type: "
                + problem.get("problem_type", "unknown")
            )

        solver = self._manager.get_solver(solver_name)
        if not solver:
            raise RuntimeError(f"Solver {solver_name} not found")

        return solver.solve(problem)

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

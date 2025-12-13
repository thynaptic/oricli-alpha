"""
Symbolic Solver Module - Brain module for symbolic reasoning
Integrates with symbolic_solvers package
"""

from typing import Dict, Any, List, Optional
import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent))

from mavaia_core.brain.base_module import BaseBrainModule, ModuleMetadata

# Lazy imports to avoid timeout during module discovery
SYMBOLIC_SOLVERS_AVAILABLE = False
get_solver_router = None
SolverRouter = None

def _lazy_import_symbolic_solvers():
    """Lazy import symbolic solvers only when needed"""
    global SYMBOLIC_SOLVERS_AVAILABLE, get_solver_router, SolverRouter
    if not SYMBOLIC_SOLVERS_AVAILABLE:
        try:
            from symbolic_solvers import get_solver_router as GSR, SolverRouter as SR
            get_solver_router = GSR
            SolverRouter = SR
            SYMBOLIC_SOLVERS_AVAILABLE = True
        except ImportError:
            pass


class SymbolicSolverModule(BaseBrainModule):
    """Symbolic reasoning solver module"""

    def __init__(self):
        self._router = None
        self._router_initialized = False

    @property
    def metadata(self) -> ModuleMetadata:
        return ModuleMetadata(
            name="symbolic_solver",
            version="1.0.0",
            description="Symbolic reasoning solver using Z3, PySAT, SymPy, Prolog",
            operations=[
                "solve",
                "check_satisfiability",
                "find_model",
                "verify",
                "get_capabilities",
            ],
            dependencies=["z3-solver", "python-sat", "sympy", "pyswip"],
            model_required=False,
        )

    def initialize(self) -> bool:
        """Initialize the module"""
        _lazy_import_symbolic_solvers()
        return True
    
    def _ensure_router(self):
        """Lazy load router only when needed"""
        if not self._router_initialized:
            self._router_initialized = True
            _lazy_import_symbolic_solvers()
            if SYMBOLIC_SOLVERS_AVAILABLE and get_solver_router:
                try:
                    self._router = get_solver_router()
                except Exception:
                    self._router = None

    def execute(self, operation: str, params: Dict[str, Any]) -> Dict[str, Any]:
        """Execute a symbolic solver operation"""
        self._ensure_router()
        if not self._router:
            raise RuntimeError("Symbolic solver router not available")

        if operation == "solve":
            problem = params.get("problem")
            if not problem:
                raise ValueError("Missing required parameter: problem")
            return self._router.solve(problem)

        elif operation == "check_satisfiability":
            problem = params.get("problem")
            if not problem:
                raise ValueError("Missing required parameter: problem")
            solver_name = self._router.select_solver(problem)
            if not solver_name:
                return {"is_satisfiable": None, "error": "No solver available"}
            solver = self._router._manager.get_solver(solver_name)
            if not solver:
                return {"is_satisfiable": None, "error": "Solver not found"}
            result = solver.check_satisfiability(problem)
            return {"is_satisfiable": result}

        elif operation == "find_model":
            problem = params.get("problem")
            if not problem:
                raise ValueError("Missing required parameter: problem")
            result = self._router.solve(problem)
            return {"model": result.get("model")}

        elif operation == "verify":
            problem = params.get("problem")
            solution = params.get("solution")
            if not problem or not solution:
                raise ValueError("Missing required parameters: problem, solution")
            # Re-solve and compare
            new_result = self._router.solve(problem)
            is_valid = new_result.get("is_satisfiable") == solution.get(
                "is_satisfiable"
            ) and new_result.get("model") == solution.get("model")
            return {"is_valid": is_valid}

        elif operation == "get_capabilities":
            available = self._router.get_available_solvers()
            return {"available_solvers": available, "solver_count": len(available)}

        else:
            raise ValueError(f"Unknown operation: {operation}")

    def cleanup(self):
        """Cleanup resources"""
        if self._router:
            try:
                self._router.cleanup()
            except Exception:
                pass

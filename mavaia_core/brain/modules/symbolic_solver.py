"""
Symbolic Solver Module - Brain module for symbolic reasoning
Integrates with symbolic_solvers package
"""

from typing import Dict, Any, List, Optional
import logging

from mavaia_core.brain.base_module import BaseBrainModule, ModuleMetadata
from mavaia_core.exceptions import InvalidParameterError, ModuleInitializationError, ModuleOperationError

# Lazy imports to avoid timeout during module discovery
SYMBOLIC_SOLVERS_AVAILABLE = False
get_solver_router = None
SolverRouter = None
_SYMBOLIC_SOLVERS_IMPORT_FAILURE_LOGGED = False

logger = logging.getLogger(__name__)

def _lazy_import_symbolic_solvers():
    """Lazy import symbolic solvers only when needed"""
    global SYMBOLIC_SOLVERS_AVAILABLE, get_solver_router, SolverRouter, _SYMBOLIC_SOLVERS_IMPORT_FAILURE_LOGGED
    if not SYMBOLIC_SOLVERS_AVAILABLE:
        try:
            from symbolic_solvers import get_solver_router as GSR, SolverRouter as SR
            get_solver_router = GSR
            SolverRouter = SR
            SYMBOLIC_SOLVERS_AVAILABLE = True
        except ImportError:
            if not _SYMBOLIC_SOLVERS_IMPORT_FAILURE_LOGGED:
                _SYMBOLIC_SOLVERS_IMPORT_FAILURE_LOGGED = True
                logger.debug(
                    "symbolic_solvers package not available; symbolic_solver disabled until installed",
                    exc_info=True,
                    extra={"module_name": "symbolic_solver"},
                )


class SymbolicSolverModule(BaseBrainModule):
    """Symbolic reasoning solver module"""

    def __init__(self):
        super().__init__()
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
                except Exception as e:
                    logger.debug(
                        "Failed to initialize symbolic solver router",
                        exc_info=True,
                        extra={"module_name": "symbolic_solver", "error_type": type(e).__name__},
                    )
                    self._router = None

    def execute(self, operation: str, params: Dict[str, Any]) -> Dict[str, Any]:
        """Execute a symbolic solver operation"""
        self._ensure_router()
        if not self._router:
            raise ModuleInitializationError(
                module_name="symbolic_solver",
                reason="Symbolic solver router not available",
            )

        match operation:
            case "solve":
                problem = params.get("problem")
                if not problem:
                    raise InvalidParameterError("problem", str(problem), "Missing required parameter: problem")
                try:
                    return self._router.solve(problem)
                except Exception as e:
                    raise ModuleOperationError(
                        module_name="symbolic_solver",
                        operation="solve",
                        reason="Solver execution failed",
                    ) from e

            case "check_satisfiability":
                problem = params.get("problem")
                if not problem:
                    raise InvalidParameterError("problem", str(problem), "Missing required parameter: problem")
                try:
                    if hasattr(self._router, "check_satisfiability"):
                        return self._router.check_satisfiability(problem)

                    solver_name = self._router.select_solver(problem)
                    if not solver_name:
                        return {"is_satisfiable": None, "error": "No solver available"}
                    manager = getattr(self._router, "_manager", None)
                    solver = manager.get_solver(solver_name) if manager else None
                    if not solver:
                        return {"is_satisfiable": None, "error": "Solver not found"}
                    result = solver.check_satisfiability(problem)
                    return {"is_satisfiable": result}
                except Exception as e:
                    raise ModuleOperationError(
                        module_name="symbolic_solver",
                        operation="check_satisfiability",
                        reason="Satisfiability check failed",
                    ) from e

            case "find_model":
                problem = params.get("problem")
                if not problem:
                    raise InvalidParameterError("problem", str(problem), "Missing required parameter: problem")
                try:
                    result = self._router.solve(problem)
                    return {"model": result.get("model") if isinstance(result, dict) else None}
                except Exception as e:
                    raise ModuleOperationError(
                        module_name="symbolic_solver",
                        operation="find_model",
                        reason="Model finding failed",
                    ) from e

            case "verify":
                problem = params.get("problem")
                solution = params.get("solution")
                if not problem:
                    raise InvalidParameterError("problem", str(problem), "Missing required parameter: problem")
                if not solution or not isinstance(solution, dict):
                    raise InvalidParameterError("solution", str(solution), "Missing required parameter: solution")
                try:
                    # Re-solve and compare
                    new_result = self._router.solve(problem)
                    if not isinstance(new_result, dict):
                        return {"is_valid": False}
                    is_valid = (
                        new_result.get("is_satisfiable") == solution.get("is_satisfiable")
                        and new_result.get("model") == solution.get("model")
                    )
                    return {"is_valid": is_valid}
                except Exception as e:
                    raise ModuleOperationError(
                        module_name="symbolic_solver",
                        operation="verify",
                        reason="Verification failed",
                    ) from e

            case "get_capabilities":
                try:
                    available = self._router.get_available_solvers()
                    return {"available_solvers": available, "solver_count": len(available)}
                except Exception as e:
                    raise ModuleOperationError(
                        module_name="symbolic_solver",
                        operation="get_capabilities",
                        reason="Failed to get capabilities",
                    ) from e

            case _:
                raise InvalidParameterError("operation", str(operation), "Unknown operation for symbolic_solver")

    def cleanup(self):
        """Cleanup resources"""
        if self._router:
            try:
                self._router.cleanup()
            except Exception as e:
                logger.debug(
                    "Cleanup failed",
                    exc_info=True,
                    extra={"module_name": "symbolic_solver", "error_type": type(e).__name__},
                )

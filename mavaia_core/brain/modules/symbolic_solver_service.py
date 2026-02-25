from __future__ import annotations
"""
Symbolic Solver Service - Service for automatic symbolic solver selection and execution
Converted from Swift SymbolicSolverService.swift
"""

from typing import Any, Dict, List, Optional
import logging
from enum import Enum

from mavaia_core.brain.base_module import BaseBrainModule, ModuleMetadata
from mavaia_core.brain.registry import ModuleRegistry
from mavaia_core.exceptions import InvalidParameterError
try:
    from models.symbolic_models import SymbolicProblem, SymbolicProblemType, SymbolicSolution
except ImportError:
    # Models not available - define minimal types
    SymbolicProblem = None
    SymbolicProblemType = None
    SymbolicSolution = None

logger = logging.getLogger(__name__)


class _FallbackSymbolicProblemType(str, Enum):
    SAT = "sat"
    SMT = "smt"
    CSP = "csp"
    SYMBOLIC_MATH = "symbolic_math"
    LOGIC_PROGRAMMING = "logic_programming"
    PLANNING = "planning"
    VERIFICATION = "verification"
    UNKNOWN = "unknown"


class SymbolicSolverServiceModule(BaseBrainModule):
    """Service for automatic symbolic solver selection and execution"""

    def __init__(self):
        super().__init__()
        self.symbolic_solver = None
        self._modules_loaded = False

    @property
    def metadata(self) -> ModuleMetadata:
        return ModuleMetadata(
            name="symbolic_solver_service",
            version="1.0.0",
            description="Service for automatic symbolic solver selection and execution",
            operations=[
                "solve_symbolic",
                "select_solver",
                "check_satisfiability",
                "find_model",
            ],
            dependencies=[],
            model_required=False,
        )

    def initialize(self) -> bool:
        """Initialize the module"""
        return True

    def _ensure_modules_loaded(self):
        """Lazy load dependent modules"""
        if self._modules_loaded:
            return

        try:
            self.symbolic_solver = ModuleRegistry.get_module("symbolic_solver")

            self._modules_loaded = True
        except Exception as e:
            logger.debug(
                "Failed to load symbolic_solver module",
                exc_info=True,
                extra={"module_name": "symbolic_solver_service", "error_type": type(e).__name__},
            )

    def execute(self, operation: str, params: Dict[str, Any]) -> Dict[str, Any]:
        """Execute an operation"""
        self._ensure_modules_loaded()

        if operation == "solve_symbolic":
            return self._solve_symbolic(params)
        elif operation == "select_solver":
            return self._select_solver(params)
        elif operation == "check_satisfiability":
            return self._check_satisfiability(params)
        elif operation == "find_model":
            return self._find_model(params)
        else:
            raise InvalidParameterError("operation", str(operation), "Unknown operation for symbolic_solver_service")

    def _solve_symbolic(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Solve a symbolic problem"""
        import time

        problem = params.get("problem", {})
        start_time = time.time()
        if problem is None:
            problem = {}
        if not isinstance(problem, dict):
            raise InvalidParameterError("problem", str(type(problem).__name__), "problem must be a dict")

        if not self.symbolic_solver:
            return {
                "success": False,
                "error": "Symbolic solver not available",
            }

        try:
            result = self.symbolic_solver.execute("solve", {
                "problem": problem,
            })

            execution_time = time.time() - start_time

            return {
                "success": True,
                "problem_id": problem.get("id", ""),
                "is_satisfiable": result.get("is_satisfiable"),
                "model": result.get("model"),
                "proof": result.get("proof"),
                "solver_used": result.get("solver_used", "unknown"),
                "execution_time": execution_time,
                "confidence": result.get("confidence", 0.5),
            }
        except Exception as e:
            logger.debug(
                "solve_symbolic failed",
                exc_info=True,
                extra={"module_name": "symbolic_solver_service", "error_type": type(e).__name__},
            )
            return {
                "success": False,
                "error": "Symbolic solve failed",
            }

    def _select_solver(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Select appropriate solver for a problem"""
        problem = params.get("problem", {})
        if problem is None:
            problem = {}
        if not isinstance(problem, dict):
            raise InvalidParameterError("problem", str(type(problem).__name__), "problem must be a dict")

        problem_type_default = (
            SymbolicProblemType.UNKNOWN.value
            if SymbolicProblemType is not None and hasattr(SymbolicProblemType, "UNKNOWN")
            else _FallbackSymbolicProblemType.UNKNOWN.value
        )
        problem_type = problem.get("problem_type", problem_type_default)
        if not isinstance(problem_type, str):
            problem_type = str(problem_type)

        if not self.symbolic_solver:
            return {
                "success": False,
                "error": "Symbolic solver not available",
                "solver": None,
            }

        try:
            result = self.symbolic_solver.execute("get_capabilities", {})
            available_solvers = result.get("available_solvers", [])

            if not available_solvers:
                return {
                    "success": False,
                    "error": "No solvers available",
                    "solver": None,
                }

            # Select based on problem type
            preferred_solvers = self._get_preferred_solvers(problem_type)

            # Find first available preferred solver
            for solver in preferred_solvers:
                if solver in available_solvers:
                    return {
                        "success": True,
                        "solver": solver,
                    }

            # Fallback to first available
            return {
                "success": True,
                "solver": available_solvers[0],
            }
        except Exception as e:
            logger.debug(
                "select_solver failed",
                exc_info=True,
                extra={"module_name": "symbolic_solver_service", "error_type": type(e).__name__},
            )
            return {
                "success": False,
                "error": "Solver selection failed",
                "solver": None,
            }

    def _check_satisfiability(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Check if a problem is satisfiable"""
        problem = params.get("problem", {})
        if problem is None:
            problem = {}
        if not isinstance(problem, dict):
            raise InvalidParameterError("problem", str(type(problem).__name__), "problem must be a dict")

        if not self.symbolic_solver:
            return {
                "success": False,
                "error": "Symbolic solver not available",
                "is_satisfiable": None,
            }

        try:
            result = self.symbolic_solver.execute("check_satisfiability", {
                "problem": problem,
            })

            return {
                "success": True,
                "is_satisfiable": result.get("is_satisfiable"),
            }
        except Exception as e:
            logger.debug(
                "check_satisfiability failed",
                exc_info=True,
                extra={"module_name": "symbolic_solver_service", "error_type": type(e).__name__},
            )
            return {
                "success": False,
                "error": "Satisfiability check failed",
                "is_satisfiable": None,
            }

    def _find_model(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Find a model for a problem"""
        problem = params.get("problem", {})
        if problem is None:
            problem = {}
        if not isinstance(problem, dict):
            raise InvalidParameterError("problem", str(type(problem).__name__), "problem must be a dict")

        if not self.symbolic_solver:
            return {
                "success": False,
                "error": "Symbolic solver not available",
                "model": None,
            }

        try:
            result = self.symbolic_solver.execute("find_model", {
                "problem": problem,
            })

            return {
                "success": True,
                "model": result.get("model"),
            }
        except Exception as e:
            logger.debug(
                "find_model failed",
                exc_info=True,
                extra={"module_name": "symbolic_solver_service", "error_type": type(e).__name__},
            )
            return {
                "success": False,
                "error": "Model finding failed",
                "model": None,
            }

    def _get_preferred_solvers(self, problem_type: str) -> List[str]:
        """Get preferred solvers for a problem type"""
        solver_map = {
            (SymbolicProblemType.SAT.value if SymbolicProblemType else _FallbackSymbolicProblemType.SAT.value): ["pysat", "z3"],
            (SymbolicProblemType.SMT.value if SymbolicProblemType else _FallbackSymbolicProblemType.SMT.value): ["z3"],
            (SymbolicProblemType.CSP.value if SymbolicProblemType else _FallbackSymbolicProblemType.CSP.value): ["z3"],
            (SymbolicProblemType.SYMBOLIC_MATH.value if SymbolicProblemType else _FallbackSymbolicProblemType.SYMBOLIC_MATH.value): ["sympy"],
            (SymbolicProblemType.LOGIC_PROGRAMMING.value if SymbolicProblemType else _FallbackSymbolicProblemType.LOGIC_PROGRAMMING.value): ["prolog"],
            (SymbolicProblemType.PLANNING.value if SymbolicProblemType else _FallbackSymbolicProblemType.PLANNING.value): ["z3", "prolog"],
            (SymbolicProblemType.VERIFICATION.value if SymbolicProblemType else _FallbackSymbolicProblemType.VERIFICATION.value): ["z3"],
            (SymbolicProblemType.UNKNOWN.value if SymbolicProblemType else _FallbackSymbolicProblemType.UNKNOWN.value): ["z3", "pysat", "sympy"],
        }
        return solver_map.get(problem_type, ["z3"])


"""
Symbolic Solver Service - Service for automatic symbolic solver selection and execution
Converted from Swift SymbolicSolverService.swift
"""

from typing import Any, Dict, List, Optional
import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent))

from mavaia_core.brain.base_module import BaseBrainModule, ModuleMetadata
try:
    from models.symbolic_models import SymbolicProblem, SymbolicProblemType, SymbolicSolution
except ImportError:
    # Models not available - define minimal types
    SymbolicProblem = None
    SymbolicProblemType = None
    SymbolicSolution = None


class SymbolicSolverServiceModule(BaseBrainModule):
    """Service for automatic symbolic solver selection and execution"""

    def __init__(self):
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
            from mavaia_core.brain.registry import ModuleRegistry

            self.symbolic_solver = ModuleRegistry.get_module("symbolic_solver")

            self._modules_loaded = True
        except Exception as e:
            # Modules not available - will use fallback methods
            pass

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
            raise ValueError(f"Unknown operation: {operation}")

    def _solve_symbolic(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Solve a symbolic problem"""
        import time

        problem = params.get("problem", {})
        start_time = time.time()

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
            return {
                "success": False,
                "error": str(e),
            }

    def _select_solver(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Select appropriate solver for a problem"""
        problem = params.get("problem", {})
        problem_type = problem.get("problem_type", SymbolicProblemType.UNKNOWN.value)

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
            return {
                "success": False,
                "error": str(e),
                "solver": None,
            }

    def _check_satisfiability(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Check if a problem is satisfiable"""
        problem = params.get("problem", {})

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
            return {
                "success": False,
                "error": str(e),
                "is_satisfiable": None,
            }

    def _find_model(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Find a model for a problem"""
        problem = params.get("problem", {})

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
            return {
                "success": False,
                "error": str(e),
                "model": None,
            }

    def _get_preferred_solvers(self, problem_type: str) -> List[str]:
        """Get preferred solvers for a problem type"""
        solver_map = {
            SymbolicProblemType.SAT.value: ["pysat", "z3"],
            SymbolicProblemType.SMT.value: ["z3"],
            SymbolicProblemType.CSP.value: ["z3"],
            SymbolicProblemType.SYMBOLIC_MATH.value: ["sympy"],
            SymbolicProblemType.LOGIC_PROGRAMMING.value: ["prolog"],
            SymbolicProblemType.PLANNING.value: ["z3", "prolog"],
            SymbolicProblemType.VERIFICATION.value: ["z3"],
            SymbolicProblemType.UNKNOWN.value: ["z3", "pysat", "sympy"],
        }
        return solver_map.get(problem_type, ["z3"])


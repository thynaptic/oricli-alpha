from __future__ import annotations
"""
SymPy Solver Integration
Provides interface to SymPy for symbolic mathematics
"""

from typing import Dict, Any, Optional, List
import time
import logging

from oricli_core.exceptions import ModuleInitializationError, ModuleOperationError, InvalidParameterError

logger = logging.getLogger(__name__)

# Optional import - will fail gracefully if SymPy not available
try:
    from sympy import symbols, solve, Eq, simplify, sympify
    from sympy.parsing.sympy_parser import parse_expr

    SYMPY_AVAILABLE = True
except ImportError:
    SYMPY_AVAILABLE = False
    symbols = None
    solve = None
    Eq = None
    simplify = None
    sympify = None
    parse_expr = None


class SymPySolver:
    """SymPy solver wrapper for symbolic mathematics"""

    def __init__(self):
        self._available = SYMPY_AVAILABLE
        if not self._available:
            self._error_message = "SymPy not installed. Install with: pip install sympy"
        else:
            self._error_message = None

    def is_available(self) -> bool:
        """Check if SymPy is available"""
        return self._available

    def solve(self, problem: Dict[str, Any]) -> Dict[str, Any]:
        """
        Solve a symbolic math problem using SymPy

        Args:
            problem: Problem dictionary with:
                - problem_type: "symbolic_math"
                - expressions: List of equations/expressions
                - variables: List of variable names

        Returns:
            Solution dictionary
        """
        if not self._available:
            raise ModuleInitializationError(
                module_name="symbolic_solver",
                reason=self._error_message or "SymPy not available",
            )
        if not isinstance(problem, dict):
            raise InvalidParameterError("problem", str(type(problem).__name__), "problem must be a dict")

        start_time = time.time()

        try:
            # Create symbols for variables
            var_names = problem.get("variables", [])
            sym_vars = symbols(" ".join(var_names))
            if len(var_names) == 1:
                sym_vars = (sym_vars,)

            var_dict = dict(zip(var_names, sym_vars))

            # Parse equations
            equations = []
            for expr_data in problem.get("expressions", []):
                expr = expr_data.get("expression", "")
                eq = self._parse_equation(expr, var_dict)
                if eq is not None:
                    equations.append(eq)

            # Solve system of equations
            solutions = []
            if equations:
                try:
                    solutions = solve(equations, *sym_vars, dict=True)
                except Exception as e:
                    # If solving fails, try simplifying
                    simplified = [simplify(eq) for eq in equations]
                    try:
                        solutions = solve(simplified, *sym_vars, dict=True)
                    except Exception:
                        pass

            # Convert solutions to model format
            model = None
            is_satisfiable = None

            if solutions:
                is_satisfiable = True
                # Take first solution
                sol_dict = solutions[0] if isinstance(solutions, list) else solutions
                model = {}
                for var_name, sym_var in var_dict.items():
                    if sym_var in sol_dict:
                        value = sol_dict[sym_var]
                        model[var_name] = str(value)
            elif not equations:
                # No equations means problem is trivially satisfiable
                is_satisfiable = True
                model = {}
            else:
                # No solution found
                is_satisfiable = False

            execution_time = time.time() - start_time

            return {
                "is_satisfiable": is_satisfiable,
                "model": model,
                "proof": None,
                "execution_time": execution_time,
                "solver_used": "sympy",
            }

        except Exception as e:
            logger.debug(
                "SymPy solver failed",
                exc_info=True,
                extra={"solver": "sympy", "error_type": type(e).__name__},
            )
            raise ModuleOperationError(
                module_name="symbolic_solver",
                operation="solve",
                reason="SymPy solver error",
            ) from e

    def _parse_equation(
        self, expression: str, var_dict: Dict[str, Any]
    ) -> Optional[Any]:
        """Parse an equation expression"""
        if not expression:
            return None

        try:
            # Handle equality: "x = 5" or "x == 5"
            if "=" in expression:
                parts = expression.split("=", 1)
                if len(parts) == 2:
                    left = parts[0].strip()
                    right = parts[1].strip()

                    try:
                        left_expr = parse_expr(left, local_dict=var_dict)
                        right_expr = parse_expr(right, local_dict=var_dict)
                        return Eq(left_expr, right_expr)
                    except Exception:
                        # Fallback to simple parsing
                        pass

            # Try parsing as expression
            try:
                expr = parse_expr(expression, local_dict=var_dict)
                return expr
            except Exception:
                return None

        except Exception:
            return None

    def check_satisfiability(self, problem: Dict[str, Any]) -> Optional[bool]:
        """Check satisfiability"""
        result = self.solve(problem)
        return result.get("is_satisfiable")

    def cleanup(self):
        """Cleanup resources"""
        pass

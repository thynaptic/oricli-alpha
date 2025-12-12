"""
PySAT Solver Integration
Provides interface to PySAT for Boolean satisfiability problems
"""

from typing import Dict, Any, Optional, List
import time

# Optional import - will fail gracefully if PySAT not available
try:
    from pysat.solvers import Glucose3
    from pysat.formula import CNF

    PYSAT_AVAILABLE = True
except ImportError:
    PYSAT_AVAILABLE = False
    Glucose3 = None
    CNF = None


class PySATSolver:
    """PySAT solver wrapper for SAT problems"""

    def __init__(self):
        self._available = PYSAT_AVAILABLE
        if not self._available:
            self._error_message = (
                "PySAT not installed. Install with: pip install python-sat"
            )
        else:
            self._error_message = None

    def is_available(self) -> bool:
        """Check if PySAT is available"""
        return self._available

    def solve(self, problem: Dict[str, Any]) -> Dict[str, Any]:
        """
        Solve a SAT problem using PySAT

        Args:
            problem: Problem dictionary with:
                - problem_type: Should be "sat"
                - expressions: List of clauses (CNF format)
                - variables: List of variable names

        Returns:
            Solution dictionary
        """
        if not self._available:
            raise RuntimeError(self._error_message)

        start_time = time.time()

        try:
            # Convert problem to CNF
            cnf = self._build_cnf(problem)

            # Create solver
            solver = Glucose3()
            solver.append_formula(cnf)

            # Solve
            is_satisfiable = solver.solve()

            model = None
            if is_satisfiable:
                # Get model (variable assignments)
                model_list = solver.get_model()
                # Convert to dictionary format
                variables = problem.get("variables", [])
                model = {}
                for i, var_name in enumerate(variables):
                    if i < len(model_list):
                        value = model_list[i]
                        # PySAT uses positive/negative integers for True/False
                        model[var_name] = "True" if value > 0 else "False"

            solver.delete()
            execution_time = time.time() - start_time

            return {
                "is_satisfiable": is_satisfiable,
                "model": model,
                "proof": None,
                "execution_time": execution_time,
                "solver_used": "pysat",
            }

        except Exception as e:
            raise RuntimeError(f"PySAT solver error: {str(e)}")

    def _build_cnf(self, problem: Dict[str, Any]) -> Any:
        """Build CNF formula from problem"""
        clauses = []

        # Parse expressions as clauses
        for expr_data in problem.get("expressions", []):
            expr = expr_data.get("expression", "")
            clause = self._parse_clause(expr, problem.get("variables", []))
            if clause:
                clauses.append(clause)

        # Create CNF
        cnf = CNF()
        for clause in clauses:
            cnf.append(clause)

        return cnf

    def _parse_clause(
        self, expression: str, variables: List[str]
    ) -> Optional[List[int]]:
        """
        Parse a clause expression into list of literals
        Returns list of integers where positive = variable, negative = negation
        """
        if not expression:
            return None

        try:
            clause = []
            expression = expression.strip().upper()

            # Handle OR operations: "x OR y OR NOT z"
            parts = expression.split(" OR ")
            for part in parts:
                part = part.strip()
                negated = part.startswith("NOT ")
                if negated:
                    part = part[4:].strip()

                if part in variables:
                    var_index = variables.index(part) + 1  # 1-indexed
                    clause.append(-var_index if negated else var_index)

            return clause if clause else None

        except Exception:
            return None

    def check_satisfiability(self, problem: Dict[str, Any]) -> Optional[bool]:
        """Check satisfiability"""
        result = self.solve(problem)
        return result.get("is_satisfiable")

    def cleanup(self):
        """Cleanup resources"""
        pass

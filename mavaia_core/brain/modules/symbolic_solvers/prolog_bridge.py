"""
Prolog Bridge Integration
Provides interface to Prolog for logic programming problems
"""

from typing import Dict, Any, Optional, List
import time

# Optional import - will fail gracefully if PySwip not available
try:
    from pyswip import Prolog

    PROLOG_AVAILABLE = True
except ImportError:
    PROLOG_AVAILABLE = False
    Prolog = None


class PrologBridge:
    """Prolog bridge for logic programming"""

    def __init__(self):
        self._available = PROLOG_AVAILABLE
        if not self._available:
            self._error_message = (
                "PySwip not installed. Install with: pip install pyswip"
            )
            self._prolog = None
        else:
            self._error_message = None
            try:
                self._prolog = Prolog()
            except Exception as e:
                self._available = False
                self._error_message = f"Failed to initialize Prolog: {str(e)}"
                self._prolog = None

    def is_available(self) -> bool:
        """Check if Prolog is available"""
        return self._available and self._prolog is not None

    def solve(self, problem: Dict[str, Any]) -> Dict[str, Any]:
        """
        Solve a logic programming problem using Prolog

        Args:
            problem: Problem dictionary with:
                - problem_type: "logic_programming"
                - expressions: List of Prolog facts/rules
                - constraints: Query to solve

        Returns:
            Solution dictionary
        """
        if not self.is_available():
            raise RuntimeError(self._error_message or "Prolog not available")

        start_time = time.time()

        try:
            # Assert facts and rules
            for expr_data in problem.get("expressions", []):
                expr = expr_data.get("expression", "")
                if expr:
                    try:
                        self._prolog.assertz(expr)
                    except Exception as e:
                        # Some assertions might fail, continue
                        pass

            # Execute query
            query = None
            if problem.get("constraints"):
                # Use first constraint as query
                constraint = problem["constraints"][0]
                query = constraint.get("expression", "")
            elif problem.get("expressions"):
                # Use last expression as query
                last_expr = problem["expressions"][-1]
                query = last_expr.get("expression", "")

            is_satisfiable = None
            model = None

            if query:
                try:
                    results = list(self._prolog.query(query))
                    if results:
                        is_satisfiable = True
                        # Convert first result to model
                        if results:
                            model = {}
                            for key, value in results[0].items():
                                model[key] = str(value)
                    else:
                        is_satisfiable = False
                except Exception as e:
                    # Query failed
                    is_satisfiable = False

            execution_time = time.time() - start_time

            return {
                "is_satisfiable": is_satisfiable,
                "model": model,
                "proof": None,
                "execution_time": execution_time,
                "solver_used": "prolog",
            }

        except Exception as e:
            execution_time = time.time() - start_time
            raise RuntimeError(f"Prolog solver error: {str(e)}")

    def check_satisfiability(self, problem: Dict[str, Any]) -> Optional[bool]:
        """Check satisfiability"""
        result = self.solve(problem)
        return result.get("is_satisfiable")

    def cleanup(self):
        """Cleanup resources"""
        if self._prolog:
            try:
                # Retract all facts (cleanup)
                list(self._prolog.query("retractall(_)"))
            except Exception:
                pass

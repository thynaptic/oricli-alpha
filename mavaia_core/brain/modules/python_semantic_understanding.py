from __future__ import annotations
"""
Python Semantic Understanding Module

Deep semantic analysis of Python code beyond syntax parsing.
Provides semantic understanding including variable flow, type inference,
dependency analysis, call graphs, and scope understanding.

This module is part of Mavaia's Python LLM capabilities, enabling
deep understanding of Python code semantics as a foundation for
reasoning and code generation.
"""

import ast
import sys
from collections import defaultdict
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple

from mavaia_core.brain.base_module import BaseBrainModule, ModuleMetadata
from mavaia_core.exceptions import InvalidParameterError

# Try to import networkx for graph operations (optional dependency)
try:
    import networkx as nx
    HAS_NETWORKX = True
except ImportError:
    HAS_NETWORKX = False


class PythonSemanticUnderstandingModule(BaseBrainModule):
    """
    Deep semantic understanding of Python code.
    
    Provides semantic analysis including:
    - Variable flow analysis (data flow, control flow)
    - Type inference and propagation
    - Dependency graph construction
    - Call graph analysis
    - Scope and namespace understanding
    - Semantic annotations beyond AST
    """

    def __init__(self):
        """Initialize the semantic understanding module."""
        super().__init__()
        self._type_cache: Dict[str, Any] = {}
        self._scope_cache: Dict[str, Any] = {}

    @property
    def metadata(self) -> ModuleMetadata:
        """Return module metadata."""
        dependencies = []
        if HAS_NETWORKX:
            dependencies.append("networkx")
        
        return ModuleMetadata(
            name="python_semantic_understanding",
            version="1.0.0",
            description=(
                "Deep semantic understanding of Python code: "
                "variable flow, type inference, dependency analysis, "
                "call graphs, and scope understanding"
            ),
            operations=[
                "analyze_semantics",
                "trace_variable_flow",
                "infer_types",
                "build_dependency_graph",
                "analyze_call_graph",
                "understand_scope",
                "analyze_data_flow",
                "analyze_control_flow",
            ],
            dependencies=dependencies,
            model_required=False,
        )

    def initialize(self) -> bool:
        """Initialize the module."""
        return True

    def execute(self, operation: str, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute a semantic understanding operation.
        
        Args:
            operation: Operation name
            params: Operation parameters
            
        Returns:
            Operation result dictionary
            
        Raises:
            ValueError: If operation is unknown
            InvalidParameterError: If parameters are invalid
        """
        if operation == "analyze_semantics":
            code = params.get("code", "")
            if not code:
                raise InvalidParameterError("code", "", "Code cannot be empty")
            return self.analyze_semantics(code)
        
        elif operation == "trace_variable_flow":
            code = params.get("code", "")
            variable = params.get("variable", "")
            if not code:
                raise InvalidParameterError("code", "", "Code cannot be empty")
            if not variable:
                raise InvalidParameterError("variable", "", "Variable name cannot be empty")
            return self.trace_variable_flow(code, variable)
        
        elif operation == "infer_types":
            code = params.get("code", "")
            if not code:
                raise InvalidParameterError("code", "", "Code cannot be empty")
            return self.infer_types(code)
        
        elif operation == "build_dependency_graph":
            code = params.get("code", "")
            if not code:
                raise InvalidParameterError("code", "", "Code cannot be empty")
            return self.build_dependency_graph(code)
        
        elif operation == "analyze_call_graph":
            code = params.get("code", "")
            if not code:
                raise InvalidParameterError("code", "", "Code cannot be empty")
            return self.analyze_call_graph(code)
        
        elif operation == "understand_scope":
            code = params.get("code", "")
            symbol = params.get("symbol", "")
            if not code:
                raise InvalidParameterError("code", "", "Code cannot be empty")
            if not symbol:
                raise InvalidParameterError("symbol", "", "Symbol name cannot be empty")
            return self.understand_scope(code, symbol)
        
        elif operation == "analyze_data_flow":
            code = params.get("code", "")
            if not code:
                raise InvalidParameterError("code", "", "Code cannot be empty")
            return self.analyze_data_flow(code)
        
        elif operation == "analyze_control_flow":
            code = params.get("code", "")
            if not code:
                raise InvalidParameterError("code", "", "Code cannot be empty")
            return self.analyze_control_flow(code)
        
        else:
            raise InvalidParameterError(
                parameter="operation",
                value=str(operation),
                reason="Unknown operation",
            )

    def analyze_semantics(self, code: str) -> Dict[str, Any]:
        """
        Perform comprehensive semantic analysis of Python code.
        
        Args:
            code: Python code to analyze
            
        Returns:
            Dictionary containing semantic analysis results including:
            - ast_tree: Parsed AST
            - variables: Variable definitions and usages
            - functions: Function definitions with signatures
            - classes: Class definitions with methods
            - imports: Import statements
            - scopes: Scope hierarchy
            - types: Inferred types
            - dependencies: Code dependencies
        """
        try:
            tree = ast.parse(code)
        except SyntaxError as e:
            return {
                "success": False,
                "error": f"Syntax error: {e}",
                "line": e.lineno,
                "offset": e.offset,
            }
        except Exception as e:
            return {
                "success": False,
                "error": f"Parse error: {e}",
            }

        analyzer = SemanticAnalyzer()
        analyzer.visit(tree)

        result = {
            "success": True,
            "ast_tree": ast.dump(tree, indent=2),
            "variables": analyzer.variables,
            "functions": analyzer.functions,
            "classes": analyzer.classes,
            "imports": analyzer.imports,
            "scopes": analyzer.scopes,
            "types": analyzer.inferred_types,
            "dependencies": analyzer.dependencies,
            "call_graph": analyzer.call_graph,
            "data_flow": analyzer.data_flow,
            "control_flow": analyzer.control_flow,
        }

        return result

    def trace_variable_flow(self, code: str, variable: str) -> Dict[str, Any]:
        """
        Trace the flow of a variable through the code.
        
        Args:
            code: Python code to analyze
            variable: Variable name to trace
            
        Returns:
            Dictionary containing variable flow information:
            - definitions: Where variable is defined
            - usages: Where variable is used
            - assignments: Assignment locations
            - scope: Variable scope information
            - flow_path: Data flow path
        """
        try:
            tree = ast.parse(code)
        except SyntaxError as e:
            return {
                "success": False,
                "error": f"Syntax error: {e}",
            }
        except Exception as e:
            return {
                "success": False,
                "error": f"Parse error: {e}",
            }

        tracer = VariableFlowTracer(variable)
        tracer.visit(tree)

        return {
            "success": True,
            "variable": variable,
            "definitions": tracer.definitions,
            "usages": tracer.usages,
            "assignments": tracer.assignments,
            "scope": tracer.scope_info,
            "flow_path": tracer.flow_path,
        }

    def infer_types(self, code: str) -> Dict[str, Any]:
        """
        Infer types for variables and expressions in code.
        
        Args:
            code: Python code to analyze
            
        Returns:
            Dictionary containing type inference results:
            - variables: Variable type mappings
            - functions: Function return types
            - parameters: Parameter types
            - expressions: Expression types
        """
        try:
            tree = ast.parse(code)
        except SyntaxError as e:
            return {
                "success": False,
                "error": f"Syntax error: {e}",
            }
        except Exception as e:
            return {
                "success": False,
                "error": f"Parse error: {e}",
            }

        type_inferrer = TypeInferrer()
        type_inferrer.visit(tree)

        return {
            "success": True,
            "variables": type_inferrer.variable_types,
            "functions": type_inferrer.function_types,
            "parameters": type_inferrer.parameter_types,
            "expressions": type_inferrer.expression_types,
        }

    def build_dependency_graph(self, code: str) -> Dict[str, Any]:
        """
        Build a dependency graph for the code.
        
        Args:
            code: Python code to analyze
            
        Returns:
            Dictionary containing dependency graph:
            - nodes: Graph nodes (modules, functions, classes)
            - edges: Dependency edges
            - graph: NetworkX graph (if available) or adjacency list
        """
        try:
            tree = ast.parse(code)
        except SyntaxError as e:
            return {
                "success": False,
                "error": f"Syntax error: {e}",
            }
        except Exception as e:
            return {
                "success": False,
                "error": f"Parse error: {e}",
            }

        builder = DependencyGraphBuilder()
        builder.visit(tree)

        result = {
            "success": True,
            "nodes": list(builder.nodes),
            "edges": list(builder.edges),
        }

        if HAS_NETWORKX:
            G = nx.DiGraph()
            G.add_nodes_from(builder.nodes)
            G.add_edges_from(builder.edges)
            result["graph"] = {
                "nodes": list(G.nodes()),
                "edges": list(G.edges()),
                "is_dag": nx.is_directed_acyclic_graph(G),
            }
        else:
            result["graph"] = {
                "adjacency_list": builder._build_adjacency_list(),
                "note": "networkx not available, using adjacency list",
            }

        return result

    def analyze_call_graph(self, code: str) -> Dict[str, Any]:
        """
        Analyze function call relationships in code.
        
        Args:
            code: Python code to analyze
            
        Returns:
            Dictionary containing call graph:
            - functions: Function definitions
            - calls: Function calls
            - call_graph: Call relationships
            - callers: What calls each function
            - callees: What each function calls
        """
        try:
            tree = ast.parse(code)
        except SyntaxError as e:
            return {
                "success": False,
                "error": f"Syntax error: {e}",
            }
        except Exception as e:
            return {
                "success": False,
                "error": f"Parse error: {e}",
            }

        analyzer = CallGraphAnalyzer()
        analyzer.visit(tree)

        return {
            "success": True,
            "functions": analyzer.functions,
            "calls": analyzer.calls,
            "call_graph": analyzer.call_graph,
            "callers": analyzer.callers,
            "callees": analyzer.callees,
        }

    def understand_scope(self, code: str, symbol: str) -> Dict[str, Any]:
        """
        Understand the scope of a symbol in code.
        
        Args:
            code: Python code to analyze
            symbol: Symbol name to analyze
            
        Returns:
            Dictionary containing scope information:
            - symbol: Symbol name
            - scope_type: Type of scope (global, local, nonlocal, builtin)
            - definitions: Where symbol is defined
            - usages: Where symbol is used
            - scope_hierarchy: Scope hierarchy
        """
        try:
            tree = ast.parse(code)
        except SyntaxError as e:
            return {
                "success": False,
                "error": f"Syntax error: {e}",
            }
        except Exception as e:
            return {
                "success": False,
                "error": f"Parse error: {e}",
            }

        scope_analyzer = ScopeAnalyzer(symbol)
        scope_analyzer.visit(tree)

        return {
            "success": True,
            "symbol": symbol,
            "scope_type": scope_analyzer.scope_type,
            "definitions": scope_analyzer.definitions,
            "usages": scope_analyzer.usages,
            "scope_hierarchy": scope_analyzer.scope_hierarchy,
        }

    def analyze_data_flow(self, code: str) -> Dict[str, Any]:
        """
        Analyze data flow in code.
        
        Args:
            code: Python code to analyze
            
        Returns:
            Dictionary containing data flow analysis:
            - definitions: Variable definitions
            - uses: Variable uses
            - def_use_chains: Definition-use chains
            - live_variables: Live variable analysis
        """
        try:
            tree = ast.parse(code)
        except SyntaxError as e:
            return {
                "success": False,
                "error": f"Syntax error: {e}",
            }
        except Exception as e:
            return {
                "success": False,
                "error": f"Parse error: {e}",
            }

        analyzer = DataFlowAnalyzer()
        analyzer.visit(tree)

        return {
            "success": True,
            "definitions": analyzer.definitions,
            "uses": analyzer.uses,
            "def_use_chains": analyzer.def_use_chains,
            "live_variables": analyzer.live_variables,
        }

    def analyze_control_flow(self, code: str) -> Dict[str, Any]:
        """
        Analyze control flow in code.
        
        Args:
            code: Python code to analyze
            
        Returns:
            Dictionary containing control flow analysis:
            - basic_blocks: Basic blocks
            - control_flow_graph: Control flow graph
            - branches: Branch points
            - loops: Loop structures
        """
        try:
            tree = ast.parse(code)
        except SyntaxError as e:
            return {
                "success": False,
                "error": f"Syntax error: {e}",
            }
        except Exception as e:
            return {
                "success": False,
                "error": f"Parse error: {e}",
            }

        analyzer = ControlFlowAnalyzer()
        analyzer.visit(tree)

        return {
            "success": True,
            "basic_blocks": analyzer.basic_blocks,
            "control_flow_graph": analyzer.control_flow_graph,
            "branches": analyzer.branches,
            "loops": analyzer.loops,
        }


# AST Visitor Classes for Semantic Analysis

class SemanticAnalyzer(ast.NodeVisitor):
    """AST visitor for comprehensive semantic analysis."""

    def __init__(self):
        """Initialize semantic analyzer."""
        self.variables: List[Dict[str, Any]] = []
        self.functions: List[Dict[str, Any]] = []
        self.classes: List[Dict[str, Any]] = []
        self.imports: List[Dict[str, Any]] = []
        self.scopes: List[Dict[str, Any]] = []
        self.inferred_types: Dict[str, str] = {}
        self.dependencies: Set[str] = set()
        self.call_graph: Dict[str, List[str]] = defaultdict(list)
        self.data_flow: List[Dict[str, Any]] = []
        self.control_flow: List[Dict[str, Any]] = []
        self._current_scope: List[str] = []

    def visit_Import(self, node: ast.Import) -> None:
        """Visit import statement."""
        for alias in node.names:
            self.imports.append({
                "module": alias.name,
                "alias": alias.asname,
                "line": node.lineno,
            })
            self.dependencies.add(alias.name.split(".")[0])

    def visit_ImportFrom(self, node: ast.ImportFrom) -> None:
        """Visit import from statement."""
        module = node.module or ""
        for alias in node.names:
            self.imports.append({
                "module": module,
                "name": alias.name,
                "alias": alias.asname,
                "line": node.lineno,
            })
            if module:
                self.dependencies.add(module.split(".")[0])

    def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
        """Visit function definition."""
        args = [arg.arg for arg in node.args.args]
        func_info = {
            "name": node.name,
            "line": node.lineno,
            "args": args,
            "decorators": [ast.unparse(d) for d in node.decorator_list],
            "docstring": ast.get_docstring(node),
            "is_async": isinstance(node, ast.AsyncFunctionDef),
        }
        self.functions.append(func_info)
        self._current_scope.append(node.name)
        self.generic_visit(node)
        if self._current_scope:
            self._current_scope.pop()

    def visit_ClassDef(self, node: ast.ClassDef) -> None:
        """Visit class definition."""
        methods = [
            n.name for n in node.body if isinstance(n, ast.FunctionDef)
        ]
        class_info = {
            "name": node.name,
            "line": node.lineno,
            "bases": [ast.unparse(base) for base in node.bases],
            "decorators": [ast.unparse(d) for d in node.decorator_list],
            "docstring": ast.get_docstring(node),
            "methods": methods,
        }
        self.classes.append(class_info)
        self._current_scope.append(node.name)
        self.generic_visit(node)
        if self._current_scope:
            self._current_scope.pop()

    def visit_Assign(self, node: ast.Assign) -> None:
        """Visit assignment statement."""
        for target in node.targets:
            if isinstance(target, ast.Name):
                self.variables.append({
                    "name": target.id,
                    "line": node.lineno,
                    "type": "assignment",
                    "scope": self._current_scope[-1] if self._current_scope else "global",
                })

    def visit_Name(self, node: ast.Name) -> None:
        """Visit name node (variable reference)."""
        if isinstance(node.ctx, ast.Load):
            self.variables.append({
                "name": node.id,
                "line": node.lineno,
                "type": "reference",
                "scope": self._current_scope[-1] if self._current_scope else "global",
            })

    def visit_Call(self, node: ast.Call) -> None:
        """Visit function call."""
        if isinstance(node.func, ast.Name):
            func_name = node.func.id
            if self._current_scope:
                caller = self._current_scope[-1]
                self.call_graph[caller].append(func_name)


class VariableFlowTracer(ast.NodeVisitor):
    """AST visitor for tracing variable flow."""

    def __init__(self, variable_name: str):
        """Initialize variable flow tracer."""
        self.variable_name = variable_name
        self.definitions: List[Dict[str, Any]] = []
        self.usages: List[Dict[str, Any]] = []
        self.assignments: List[Dict[str, Any]] = []
        self.scope_info: Dict[str, Any] = {}
        self.flow_path: List[Dict[str, Any]] = []
        self._current_scope: List[str] = []

    def visit_Assign(self, node: ast.Assign) -> None:
        """Visit assignment statement."""
        for target in node.targets:
            if isinstance(target, ast.Name) and target.id == self.variable_name:
                self.definitions.append({
                    "line": node.lineno,
                    "column": node.col_offset,
                    "scope": self._current_scope[-1] if self._current_scope else "global",
                })
                self.assignments.append({
                    "line": node.lineno,
                    "value": ast.unparse(node.value) if hasattr(ast, "unparse") else str(node.value),
                })

    def visit_Name(self, node: ast.Name) -> None:
        """Visit name node."""
        if node.id == self.variable_name:
            self.usages.append({
                "line": node.lineno,
                "column": node.col_offset,
                "context": type(node.ctx).__name__,
                "scope": self._current_scope[-1] if self._current_scope else "global",
            })

    def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
        """Visit function definition."""
        self._current_scope.append(node.name)
        self.generic_visit(node)
        if self._current_scope:
            self._current_scope.pop()


class TypeInferrer(ast.NodeVisitor):
    """AST visitor for type inference."""

    def __init__(self):
        """Initialize type inferrer."""
        self.variable_types: Dict[str, str] = {}
        self.function_types: Dict[str, str] = {}
        self.parameter_types: Dict[str, Dict[str, str]] = {}
        self.expression_types: Dict[str, str] = {}

    def visit_Assign(self, node: ast.Assign) -> None:
        """Visit assignment statement."""
        inferred_type = self._infer_expression_type(node.value)
        for target in node.targets:
            if isinstance(target, ast.Name):
                self.variable_types[target.id] = inferred_type

    def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
        """Visit function definition."""
        # Infer return type from return statements
        return_type = self._infer_function_return_type(node)
        if return_type:
            self.function_types[node.name] = return_type

        # Infer parameter types
        param_types = {}
        for arg in node.args.args:
            # Try to infer from annotations
            if arg.annotation:
                param_types[arg.arg] = ast.unparse(arg.annotation)
            else:
                param_types[arg.arg] = "Any"
        self.parameter_types[node.name] = param_types

        self.generic_visit(node)

    def _infer_expression_type(self, node: ast.AST) -> str:
        """Infer type of an expression."""
        if isinstance(node, ast.Constant):
            value = node.value
            if isinstance(value, int):
                return "int"
            elif isinstance(value, float):
                return "float"
            elif isinstance(value, str):
                return "str"
            elif isinstance(value, bool):
                return "bool"
            elif value is None:
                return "None"
            else:
                return type(value).__name__
        elif isinstance(node, ast.List):
            return "list"
        elif isinstance(node, ast.Dict):
            return "dict"
        elif isinstance(node, ast.Tuple):
            return "tuple"
        elif isinstance(node, ast.Set):
            return "set"
        elif isinstance(node, ast.Call):
            return "Any"  # Could be improved with call analysis
        else:
            return "Any"

    def _infer_function_return_type(self, node: ast.FunctionDef) -> Optional[str]:
        """Infer function return type."""
        if node.returns:
            return ast.unparse(node.returns)
        
        # Try to find return statements
        for stmt in ast.walk(node):
            if isinstance(stmt, ast.Return) and stmt.value:
                return self._infer_expression_type(stmt.value)
        
        return None


class DependencyGraphBuilder(ast.NodeVisitor):
    """AST visitor for building dependency graphs."""

    def __init__(self):
        """Initialize dependency graph builder."""
        self.nodes: Set[str] = set()
        self.edges: List[Tuple[str, str]] = []
        self._current_function: Optional[str] = None

    def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
        """Visit function definition."""
        self.nodes.add(node.name)
        self._current_function = node.name
        self.generic_visit(node)
        self._current_function = None

    def visit_ClassDef(self, node: ast.ClassDef) -> None:
        """Visit class definition."""
        self.nodes.add(node.name)
        self.generic_visit(node)

    def visit_Call(self, node: ast.Call) -> None:
        """Visit function call."""
        if isinstance(node.func, ast.Name):
            callee = node.func.id
            self.nodes.add(callee)
            if self._current_function:
                self.edges.append((self._current_function, callee))

    def _build_adjacency_list(self) -> Dict[str, List[str]]:
        """Build adjacency list representation."""
        adj_list: Dict[str, List[str]] = defaultdict(list)
        for source, target in self.edges:
            adj_list[source].append(target)
        return dict(adj_list)


class CallGraphAnalyzer(ast.NodeVisitor):
    """AST visitor for call graph analysis."""

    def __init__(self):
        """Initialize call graph analyzer."""
        self.functions: List[str] = []
        self.calls: List[Dict[str, Any]] = []
        self.call_graph: Dict[str, List[str]] = defaultdict(list)
        self.callers: Dict[str, List[str]] = defaultdict(list)
        self.callees: Dict[str, List[str]] = defaultdict(list)
        self._current_function: Optional[str] = None

    def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
        """Visit function definition."""
        self.functions.append(node.name)
        self._current_function = node.name
        self.generic_visit(node)
        self._current_function = None

    def visit_Call(self, node: ast.Call) -> None:
        """Visit function call."""
        if isinstance(node.func, ast.Name):
            callee = node.func.id
            self.calls.append({
                "caller": self._current_function or "global",
                "callee": callee,
                "line": node.lineno,
            })
            
            if self._current_function:
                self.call_graph[self._current_function].append(callee)
                self.callees[self._current_function].append(callee)
                self.callers[callee].append(self._current_function)


class ScopeAnalyzer(ast.NodeVisitor):
    """AST visitor for scope analysis."""

    def __init__(self, symbol_name: str):
        """Initialize scope analyzer."""
        self.symbol_name = symbol_name
        self.scope_type: Optional[str] = None
        self.definitions: List[Dict[str, Any]] = []
        self.usages: List[Dict[str, Any]] = []
        self.scope_hierarchy: List[str] = []
        self._current_scope: List[str] = []

    def visit_Assign(self, node: ast.Assign) -> None:
        """Visit assignment statement."""
        for target in node.targets:
            if isinstance(target, ast.Name) and target.id == self.symbol_name:
                scope = self._current_scope[-1] if self._current_scope else "global"
                self.definitions.append({
                    "line": node.lineno,
                    "scope": scope,
                })
                if not self.scope_type:
                    self.scope_type = scope

    def visit_Name(self, node: ast.Name) -> None:
        """Visit name node."""
        if node.id == self.symbol_name:
            scope = self._current_scope[-1] if self._current_scope else "global"
            self.usages.append({
                "line": node.lineno,
                "scope": scope,
                "context": type(node.ctx).__name__,
            })

    def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
        """Visit function definition."""
        self._current_scope.append(node.name)
        self.scope_hierarchy = list(self._current_scope)
        self.generic_visit(node)
        if self._current_scope:
            self._current_scope.pop()


class DataFlowAnalyzer(ast.NodeVisitor):
    """AST visitor for data flow analysis."""

    def __init__(self):
        """Initialize data flow analyzer."""
        self.definitions: List[Dict[str, Any]] = []
        self.uses: List[Dict[str, Any]] = []
        self.def_use_chains: List[Dict[str, Any]] = []
        self.live_variables: Set[str] = set()

    def visit_Assign(self, node: ast.Assign) -> None:
        """Visit assignment statement."""
        for target in node.targets:
            if isinstance(target, ast.Name):
                self.definitions.append({
                    "variable": target.id,
                    "line": node.lineno,
                })

    def visit_Name(self, node: ast.Name) -> None:
        """Visit name node."""
        if isinstance(node.ctx, ast.Load):
            self.uses.append({
                "variable": node.id,
                "line": node.lineno,
            })
            self.live_variables.add(node.id)


class ControlFlowAnalyzer(ast.NodeVisitor):
    """AST visitor for control flow analysis."""

    def __init__(self):
        """Initialize control flow analyzer."""
        self.basic_blocks: List[Dict[str, Any]] = []
        self.control_flow_graph: List[Tuple[str, str]] = []
        self.branches: List[Dict[str, Any]] = []
        self.loops: List[Dict[str, Any]] = []

    def visit_If(self, node: ast.If) -> None:
        """Visit if statement."""
        self.branches.append({
            "type": "if",
            "line": node.lineno,
            "condition": ast.unparse(node.test) if hasattr(ast, "unparse") else str(node.test),
        })

    def visit_For(self, node: ast.For) -> None:
        """Visit for loop."""
        self.loops.append({
            "type": "for",
            "line": node.lineno,
            "target": ast.unparse(node.target) if hasattr(ast, "unparse") else str(node.target),
        })

    def visit_While(self, node: ast.While) -> None:
        """Visit while loop."""
        self.loops.append({
            "type": "while",
            "line": node.lineno,
            "condition": ast.unparse(node.test) if hasattr(ast, "unparse") else str(node.test),
        })

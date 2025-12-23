"""
Code Analysis Module - Code parsing, analysis, and explanation generation
Handles code parsing using AST, pattern recognition, and natural language explanations
No LLM dependencies - uses Python AST and pattern matching
"""

import ast
import re
from typing import Any, Dict, List

from mavaia_core.brain.base_module import BaseBrainModule, ModuleMetadata
from mavaia_core.exceptions import InvalidParameterError


class CodeAnalysisModule(BaseBrainModule):
    """Analyze code using AST parsing and pattern recognition"""

    def __init__(self):
        super().__init__()
        self.code_patterns = {
            "function_definition": r"def\s+\w+\s*\(",
            "class_definition": r"class\s+\w+",
            "import_statement": r"^(import|from)\s+",
            "loop": r"\b(for|while)\s+",
            "conditional": r"\b(if|elif|else)\s+",
            "exception_handling": r"\b(try|except|finally)\s+",
            "decorator": r"@\w+",
        }

    @property
    def metadata(self) -> ModuleMetadata:
        return ModuleMetadata(
            name="code_analysis",
            version="1.0.0",
            description=(
                "Code analysis: parsing, pattern recognition, "
                "explanation generation, code understanding"
            ),
            operations=[
                "parse_code",
                "analyze_code",
                "explain_code",
                "identify_patterns",
                "extract_functions",
                "extract_classes",
                "find_issues",
                "generate_explanation",
            ],
            dependencies=[],
            model_required=False,
        )

    def initialize(self) -> bool:
        """Initialize the module"""
        return True

    def execute(self, operation: str, params: Dict[str, Any]) -> Dict[str, Any]:
        """Execute a code analysis operation"""
        match operation:
            case "parse_code":
                code = params.get("code", "")
                if code is None:
                    code = ""
                if not isinstance(code, str):
                    raise InvalidParameterError("code", str(type(code).__name__), "code must be a string")
                return self.parse_code(code)
            case "analyze_code":
                code = params.get("code", "")
                if code is None:
                    code = ""
                if not isinstance(code, str):
                    raise InvalidParameterError("code", str(type(code).__name__), "code must be a string")
                return self.analyze_code(code)
            case "explain_code":
                code = params.get("code", "")
                detail_level = params.get("detail_level", "medium")
                if code is None:
                    code = ""
                if detail_level is None:
                    detail_level = "medium"
                if not isinstance(code, str):
                    raise InvalidParameterError("code", str(type(code).__name__), "code must be a string")
                if not isinstance(detail_level, str):
                    raise InvalidParameterError(
                        "detail_level", str(type(detail_level).__name__), "detail_level must be a string"
                    )
                return self.explain_code(code, detail_level)
            case "identify_patterns":
                code = params.get("code", "")
                if code is None:
                    code = ""
                if not isinstance(code, str):
                    raise InvalidParameterError("code", str(type(code).__name__), "code must be a string")
                return self.identify_patterns(code)
            case "extract_functions":
                code = params.get("code", "")
                if code is None:
                    code = ""
                if not isinstance(code, str):
                    raise InvalidParameterError("code", str(type(code).__name__), "code must be a string")
                return self.extract_functions(code)
            case "extract_classes":
                code = params.get("code", "")
                if code is None:
                    code = ""
                if not isinstance(code, str):
                    raise InvalidParameterError("code", str(type(code).__name__), "code must be a string")
                return self.extract_classes(code)
            case "find_issues":
                code = params.get("code", "")
                if code is None:
                    code = ""
                if not isinstance(code, str):
                    raise InvalidParameterError("code", str(type(code).__name__), "code must be a string")
                return self.find_issues(code)
            case "generate_explanation":
                code = params.get("code", "")
                focus = params.get("focus", "general")
                if code is None:
                    code = ""
                if focus is None:
                    focus = "general"
                if not isinstance(code, str):
                    raise InvalidParameterError("code", str(type(code).__name__), "code must be a string")
                if not isinstance(focus, str):
                    raise InvalidParameterError("focus", str(type(focus).__name__), "focus must be a string")
                return self.generate_explanation(code, focus)
            case _:
                raise InvalidParameterError(
                    parameter="operation",
                    value=operation,
                    reason="Unknown operation for code_analysis",
                )

    def parse_code(self, code: str) -> Dict[str, Any]:
        """Parse code using Python AST"""
        if not code:
            return {"success": False, "error": "No code provided", "ast": None}

        try:
            tree = ast.parse(code)
            return {
                "success": True,
                "ast": ast.dump(tree, indent=2),
                "code_length": len(code),
                "lines": len(code.split("\n")),
            }
        except SyntaxError as e:
            return {
                "success": False,
                "error": str(e),
                "line": e.lineno,
                "offset": e.offset,
                "ast": None,
            }
        except Exception as e:
            return {"success": False, "error": str(e), "ast": None}

    def analyze_code(self, code: str) -> Dict[str, Any]:
        """Comprehensive code analysis"""
        if not code:
            return {"analysis": {}, "error": "No code provided"}

        analysis = {
            "functions": self._count_pattern(code, "function_definition"),
            "classes": self._count_pattern(code, "class_definition"),
            "imports": self._count_pattern(code, "import_statement"),
            "loops": self._count_pattern(code, "loop"),
            "conditionals": self._count_pattern(code, "conditional"),
            "exception_handlers": self._count_pattern(code, "exception_handling"),
            "decorators": self._count_pattern(code, "decorator"),
            "lines": len(code.split("\n")),
            "characters": len(code),
        }

        # Try to parse AST for deeper analysis
        parse_result = self.parse_code(code)
        if parse_result.get("success"):
            analysis["parseable"] = True
            analysis["ast_nodes"] = self._count_ast_nodes(parse_result["ast"])
        else:
            analysis["parseable"] = False
            analysis["parse_error"] = parse_result.get("error", "Unknown error")

        return {"analysis": analysis, "code_preview": code[:200]}

    def explain_code(self, code: str, detail_level: str = "medium") -> Dict[str, Any]:
        """Generate natural language explanation of code"""
        if not code:
            return {"explanation": "", "error": "No code provided"}

        # Parse code first
        parse_result = self.parse_code(code)
        if not parse_result.get("success"):
            return {
                "explanation": f"Code has syntax errors: {parse_result.get('error', 'Unknown')}",
                "error": parse_result.get("error"),
            }

        # Analyze code structure
        analysis = self.analyze_code(code)
        structure = analysis.get("analysis", {})

        # Generate explanation based on detail level
        explanation_parts = []

        match detail_level:
            case "simple":
                explanation_parts.append(
                    self._generate_simple_explanation(code, structure)
                )
            case "detailed":
                explanation_parts.append(
                    self._generate_detailed_explanation(code, structure)
                )
            case _:  # medium
                explanation_parts.append(
                    self._generate_medium_explanation(code, structure)
                )

        explanation = " ".join(explanation_parts)

        return {
            "explanation": explanation,
            "detail_level": detail_level,
            "structure": structure,
        }

    def identify_patterns(self, code: str) -> Dict[str, Any]:
        """Identify code patterns and structures"""
        if not code:
            return {"patterns": [], "error": "No code provided"}

        patterns_found = []

        # Check each pattern
        for pattern_name, pattern_regex in self.code_patterns.items():
            matches = re.findall(pattern_regex, code, re.MULTILINE)
            if matches:
                patterns_found.append(
                    {
                        "pattern": pattern_name,
                        "count": len(matches),
                        "matches": matches[:5],  # Limit to 5 examples
                    }
                )

        # Identify common code structures
        structures = self._identify_structures(code)

        return {
            "patterns": patterns_found,
            "structures": structures,
            "total_patterns": len(patterns_found),
        }

    def extract_functions(self, code: str) -> Dict[str, Any]:
        """Extract function definitions from code"""
        if not code:
            return {"functions": [], "error": "No code provided"}

        try:
            tree = ast.parse(code)
            functions = []

            for node in ast.walk(tree):
                if isinstance(node, ast.FunctionDef):
                    func_info = {
                        "name": node.name,
                        "line": node.lineno,
                        "args": [arg.arg for arg in node.args.args],
                        "decorators": [ast.unparse(d) for d in node.decorator_list],
                        "docstring": ast.get_docstring(node),
                    }
                    functions.append(func_info)

            return {"functions": functions, "count": len(functions)}
        except SyntaxError as e:
            return {"functions": [], "error": f"Syntax error: {e}", "count": 0}
        except Exception as e:
            return {"functions": [], "error": str(e), "count": 0}

    def extract_classes(self, code: str) -> Dict[str, Any]:
        """Extract class definitions from code"""
        if not code:
            return {"classes": [], "error": "No code provided"}

        try:
            tree = ast.parse(code)
            classes = []

            for node in ast.walk(tree):
                if isinstance(node, ast.ClassDef):
                    class_info = {
                        "name": node.name,
                        "line": node.lineno,
                        "bases": [ast.unparse(base) for base in node.bases],
                        "decorators": [ast.unparse(d) for d in node.decorator_list],
                        "docstring": ast.get_docstring(node),
                        "methods": [
                            n.name
                            for n in node.body
                            if isinstance(n, ast.FunctionDef)
                        ],
                    }
                    classes.append(class_info)

            return {"classes": classes, "count": len(classes)}
        except SyntaxError as e:
            return {"classes": [], "error": f"Syntax error: {e}", "count": 0}
        except Exception as e:
            return {"classes": [], "error": str(e), "count": 0}

    def find_issues(self, code: str) -> Dict[str, Any]:
        """Find potential issues in code"""
        if not code:
            return {"issues": [], "error": "No code provided"}

        issues = []

        # Check for syntax errors
        parse_result = self.parse_code(code)
        if not parse_result.get("success"):
            issues.append(
                {
                    "type": "syntax_error",
                    "severity": "high",
                    "message": parse_result.get("error", "Syntax error"),
                    "line": parse_result.get("line"),
                }
            )

        # Check for common issues
        issues.extend(self._check_common_issues(code))

        # Check for code quality issues
        issues.extend(self._check_quality_issues(code))

        return {
            "issues": issues,
            "count": len(issues),
            "high_severity": len([i for i in issues if i.get("severity") == "high"]),
        }

    def generate_explanation(
        self, code: str, focus: str = "general"
    ) -> Dict[str, Any]:
        """Generate focused explanation of code"""
        if not code:
            return {"explanation": "", "error": "No code provided"}

        match focus:
            case "functions":
                functions = self.extract_functions(code)
                return self._explain_functions(functions)
            case "classes":
                classes = self.extract_classes(code)
                return self._explain_classes(classes)
            case "patterns":
                patterns = self.identify_patterns(code)
                return self._explain_patterns(patterns)
            case "structure":
                analysis = self.analyze_code(code)
                return self._explain_structure(analysis)
            case _:  # general
                return self.explain_code(code, "medium")

    def _count_pattern(self, code: str, pattern_name: str) -> int:
        """Count occurrences of a pattern in code"""
        pattern = self.code_patterns.get(pattern_name, "")
        if not pattern:
            return 0
        matches = re.findall(pattern, code, re.MULTILINE)
        return len(matches)

    def _count_ast_nodes(self, ast_dump: str) -> int:
        """Count AST nodes in AST dump"""
        if not ast_dump:
            return 0
        # Simple heuristic: count parentheses (rough estimate of nodes)
        return ast_dump.count("(")

    def _identify_structures(self, code: str) -> List[Dict[str, Any]]:
        """Identify code structures"""
        structures = []

        # Check for main block
        if "__main__" in code:
            structures.append({"type": "main_block", "present": True})

        # Check for async code
        if "async def" in code or "await " in code:
            structures.append({"type": "async_code", "present": True})

        # Check for type hints
        if "->" in code or ": " in code and any(
            hint in code for hint in ["int", "str", "bool", "List", "Dict"]
        ):
            structures.append({"type": "type_hints", "present": True})

        return structures

    def _generate_simple_explanation(
        self, code: str, structure: Dict[str, Any]
    ) -> str:
        """Generate simple explanation"""
        parts = []

        if structure.get("functions", 0) > 0:
            parts.append(f"This code defines {structure['functions']} function(s)")

        if structure.get("classes", 0) > 0:
            parts.append(f"and {structure['classes']} class(es)")

        if structure.get("imports", 0) > 0:
            parts.append(f"It imports {structure['imports']} module(s)")

        if not parts:
            parts.append("This code performs various operations")

        return ". ".join(parts) + "."

    def _generate_medium_explanation(
        self, code: str, structure: Dict[str, Any]
    ) -> str:
        """Generate medium detail explanation"""
        parts = [self._generate_simple_explanation(code, structure)]

        if structure.get("loops", 0) > 0:
            parts.append(f"It uses {structure['loops']} loop(s)")

        if structure.get("conditionals", 0) > 0:
            parts.append(f"and {structure['conditionals']} conditional statement(s)")

        if structure.get("exception_handlers", 0) > 0:
            parts.append(
                f"It includes {structure['exception_handlers']} exception handler(s)"
            )

        return ". ".join(parts) + "."

    def _generate_detailed_explanation(
        self, code: str, structure: Dict[str, Any]
    ) -> str:
        """Generate detailed explanation"""
        parts = [self._generate_medium_explanation(code, structure)]

        # Extract functions for detailed explanation
        functions = self.extract_functions(code)
        if functions.get("functions"):
            func_list = functions["functions"]
            parts.append(
                f"Functions include: {', '.join([f['name'] for f in func_list[:3]])}"
            )

        # Extract classes for detailed explanation
        classes = self.extract_classes(code)
        if classes.get("classes"):
            class_list = classes["classes"]
            parts.append(
                f"Classes include: {', '.join([c['name'] for c in class_list[:3]])}"
            )

        parts.append(f"The code is {structure.get('lines', 0)} lines long")

        return ". ".join(parts) + "."

    def _check_common_issues(self, code: str) -> List[Dict[str, Any]]:
        """Check for common code issues"""
        issues = []

        # Check for bare except
        if re.search(r"except\s*:", code):
            issues.append(
                {
                    "type": "bare_except",
                    "severity": "medium",
                    "message": "Bare except clause catches all exceptions",
                }
            )

        # Check for unused imports (simple heuristic)
        lines = code.split("\n")
        import_lines = [l for l in lines if l.strip().startswith(("import ", "from "))]
        if len(import_lines) > 10:
            issues.append(
                {
                    "type": "many_imports",
                    "severity": "low",
                    "message": "Many imports - consider if all are needed",
                }
            )

        # Check for long functions (simple heuristic)
        if "def " in code:
            functions = self.extract_functions(code)
            for func in functions.get("functions", []):
                # Estimate function length (simplified)
                if func.get("line"):
                    # This is a simplified check
                    pass

        return issues

    def _check_quality_issues(self, code: str) -> List[Dict[str, Any]]:
        """Check for code quality issues"""
        issues = []

        # Check line length
        long_lines = [i for i, line in enumerate(code.split("\n"), 1) if len(line) > 100]
        if long_lines:
            issues.append(
                {
                    "type": "long_lines",
                    "severity": "low",
                    "message": f"Lines {long_lines[:5]} exceed 100 characters",
                }
            )

        # Check for TODO/FIXME comments
        todo_pattern = r"(TODO|FIXME|XXX|HACK)"
        todos = re.findall(todo_pattern, code, re.IGNORECASE)
        if todos:
            issues.append(
                {
                    "type": "todo_comments",
                    "severity": "low",
                    "message": f"Found {len(todos)} TODO/FIXME comments",
                }
            )

        return issues

    def _explain_functions(self, functions_result: Dict[str, Any]) -> Dict[str, Any]:
        """Explain functions in code"""
        functions = functions_result.get("functions", [])
        if not functions:
            return {"explanation": "No functions found in the code"}

        explanations = []
        for func in functions[:5]:  # Limit to 5 functions
            parts = [f"Function '{func['name']}'"]
            if func.get("args"):
                parts.append(f"takes {len(func['args'])} parameter(s): {', '.join(func['args'][:3])}")
            if func.get("docstring"):
                parts.append(f"Documented: {func['docstring'][:50]}")
            explanations.append(" ".join(parts))

        return {
            "explanation": ". ".join(explanations) + ".",
            "function_count": len(functions),
        }

    def _explain_classes(self, classes_result: Dict[str, Any]) -> Dict[str, Any]:
        """Explain classes in code"""
        classes = classes_result.get("classes", [])
        if not classes:
            return {"explanation": "No classes found in the code"}

        explanations = []
        for cls in classes[:5]:  # Limit to 5 classes
            parts = [f"Class '{cls['name']}'"]
            if cls.get("bases"):
                parts.append(f"inherits from {', '.join(cls['bases'])}")
            if cls.get("methods"):
                parts.append(f"has {len(cls['methods'])} method(s)")
            if cls.get("docstring"):
                parts.append(f"Documented: {cls['docstring'][:50]}")
            explanations.append(" ".join(parts))

        return {
            "explanation": ". ".join(explanations) + ".",
            "class_count": len(classes),
        }

    def _explain_patterns(self, patterns_result: Dict[str, Any]) -> Dict[str, Any]:
        """Explain patterns in code"""
        patterns = patterns_result.get("patterns", [])
        if not patterns:
            return {"explanation": "No significant patterns found in the code"}

        explanations = []
        for pattern in patterns[:5]:
            pattern_name = pattern.get("pattern", "").replace("_", " ")
            count = pattern.get("count", 0)
            explanations.append(f"{count} {pattern_name}(s)")

        return {
            "explanation": "The code contains: " + ", ".join(explanations) + ".",
            "pattern_count": len(patterns),
        }

    def _explain_structure(self, analysis_result: Dict[str, Any]) -> Dict[str, Any]:
        """Explain code structure"""
        analysis = analysis_result.get("analysis", {})
        if not analysis:
            return {"explanation": "Unable to analyze code structure"}

        parts = []
        if analysis.get("functions", 0) > 0:
            parts.append(f"{analysis['functions']} function(s)")
        if analysis.get("classes", 0) > 0:
            parts.append(f"{analysis['classes']} class(es)")
        if analysis.get("imports", 0) > 0:
            parts.append(f"{analysis['imports']} import(s)")

        return {
            "explanation": f"Code structure: {', '.join(parts)}. "
            f"Total lines: {analysis.get('lines', 0)}",
            "structure": analysis,
        }

    def validate_params(self, operation: str, params: Dict[str, Any]) -> bool:
        """Validate parameters for operations"""
        match operation:
            case (
                "parse_code"
                | "analyze_code"
                | "explain_code"
                | "identify_patterns"
                | "extract_functions"
                | "extract_classes"
                | "find_issues"
                | "generate_explanation"
            ):
                return "code" in params
            case _:
                return True


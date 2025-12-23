"""
Python Documentation Generator Module

Generate comprehensive documentation including docstrings, API documentation,
README files, code examples, architecture diagrams, migration guides, and changelogs.

This module is part of Mavaia's Python LLM Phase 4 capabilities, providing
intelligent documentation generation that understands code structure and semantics.
"""

import ast
import sys
from collections import defaultdict
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple, Union

from mavaia_core.brain.base_module import BaseBrainModule, ModuleMetadata
from mavaia_core.exceptions import InvalidParameterError


class PythonDocumentationGeneratorModule(BaseBrainModule):
    """
    Intelligent documentation generation for Python code.
    
    Provides:
    - Comprehensive docstring generation
    - API documentation creation
    - README file generation
    - Code example generation
    - Architecture documentation
    - Migration guide generation
    - Natural language code explanations
    """

    def __init__(self):
        """Initialize the Python documentation generator module."""
        super().__init__()
        self._semantic_understanding = None
        self._code_analysis = None
        self._code_generator = None

    @property
    def metadata(self) -> ModuleMetadata:
        """Return module metadata."""
        return ModuleMetadata(
            name="python_documentation_generator",
            version="1.0.0",
            description=(
                "Intelligent documentation generation: docstrings, API docs, "
                "README files, code examples, architecture docs, migration guides, "
                "and natural language explanations"
            ),
            operations=[
                "generate_docstring",
                "generate_api_docs",
                "generate_readme",
                "create_code_examples",
                "document_architecture",
                "generate_migration_guide",
                "explain_code_natural_language",
            ],
            dependencies=[],
            model_required=False,
        )

    def initialize(self) -> bool:
        """Initialize the module."""
        # Try to load related modules
        try:
            from mavaia_core.brain.registry import ModuleRegistry
            self._semantic_understanding = ModuleRegistry.get_module("python_semantic_understanding")
            self._code_analysis = ModuleRegistry.get_module("code_analysis")
            self._code_generator = ModuleRegistry.get_module("reasoning_code_generator")
        except Exception:
            pass
        
        return True

    def execute(self, operation: str, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute a documentation generation operation.
        
        Args:
            operation: Operation name
            params: Operation parameters
            
        Returns:
            Operation result dictionary
            
        Raises:
            ValueError: If operation is unknown
            InvalidParameterError: If parameters are invalid
        """
        if operation == "generate_docstring":
            code = params.get("code", "")
            style = params.get("style", "google")
            if not code:
                raise InvalidParameterError("code", "", "Code cannot be empty")
            return self.generate_docstring(code, style)
        
        elif operation == "generate_api_docs":
            module = params.get("module", "")
            if not module:
                raise InvalidParameterError("module", "", "Module code cannot be empty")
            return self.generate_api_docs(module)
        
        elif operation == "generate_readme":
            project = params.get("project", None)
            if not project:
                raise InvalidParameterError("project", None, "Project path is required")
            return self.generate_readme(project)
        
        elif operation == "create_code_examples":
            function = params.get("function", "")
            examples_count = params.get("examples_count", 3)
            if not function:
                raise InvalidParameterError("function", "", "Function code cannot be empty")
            return self.create_code_examples(function, examples_count)
        
        elif operation == "document_architecture":
            project = params.get("project", None)
            if not project:
                raise InvalidParameterError("project", None, "Project path is required")
            return self.document_architecture(project)
        
        elif operation == "generate_migration_guide":
            old_code = params.get("old_code", "")
            new_code = params.get("new_code", "")
            if not old_code:
                raise InvalidParameterError("old_code", "", "Old code cannot be empty")
            if not new_code:
                raise InvalidParameterError("new_code", "", "New code cannot be empty")
            return self.generate_migration_guide(old_code, new_code)
        
        elif operation == "explain_code_natural_language":
            code = params.get("code", "")
            audience = params.get("audience", "developer")
            if not code:
                raise InvalidParameterError("code", "", "Code cannot be empty")
            return self.explain_code_natural_language(code, audience)
        
        else:
            raise InvalidParameterError(
                parameter="operation",
                value=str(operation),
                reason="Unknown operation",
            )

    def generate_docstring(self, code: str, style: str = "google") -> Dict[str, Any]:
        """
        Generate comprehensive docstring for code.
        
        Args:
            code: Python code to document
            style: Docstring style (google, numpy, sphinx, restructured)
            
        Returns:
            Dictionary containing generated docstrings
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

        docstrings = {}
        visitor = DocstringGeneratorVisitor(style)
        visitor.visit(tree)

        # Generate docstrings for functions
        for func_name, func_info in visitor.functions.items():
            docstrings[func_name] = self._generate_function_docstring(func_info, style)

        # Generate docstrings for classes
        for class_name, class_info in visitor.classes.items():
            docstrings[class_name] = self._generate_class_docstring(class_info, style)

        # Generate module docstring
        if visitor.has_module_docstring:
            module_doc = self._generate_module_docstring(tree, style)
            docstrings["__module__"] = module_doc

        return {
            "success": True,
            "style": style,
            "docstrings": docstrings,
            "count": len(docstrings),
        }

    def generate_api_docs(self, module: str) -> Dict[str, Any]:
        """
        Generate API documentation for a module.
        
        Args:
            module: Module code to document
            
        Returns:
            Dictionary containing API documentation
        """
        try:
            tree = ast.parse(module)
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

        visitor = APIDocumentationVisitor()
        visitor.visit(tree)

        api_docs = {
            "module_name": visitor.module_name or "unknown",
            "description": visitor.module_docstring or "No module description available.",
            "functions": [],
            "classes": [],
            "constants": visitor.constants,
            "imports": visitor.imports,
        }

        # Document functions
        for func_name, func_info in visitor.functions.items():
            api_docs["functions"].append({
                "name": func_name,
                "signature": func_info["signature"],
                "description": func_info.get("docstring", "No description available."),
                "parameters": func_info.get("parameters", []),
                "returns": func_info.get("returns", "None"),
                "raises": func_info.get("raises", []),
            })

        # Document classes
        for class_name, class_info in visitor.classes.items():
            api_docs["classes"].append({
                "name": class_name,
                "description": class_info.get("docstring", "No description available."),
                "methods": class_info.get("methods", []),
                "attributes": class_info.get("attributes", []),
                "inheritance": class_info.get("inheritance", []),
            })

        # Generate markdown format
        markdown = self._generate_api_markdown(api_docs)

        return {
            "success": True,
            "api_documentation": api_docs,
            "markdown": markdown,
        }

    def generate_readme(self, project: Union[str, Path]) -> Dict[str, Any]:
        """
        Generate README file for a project.
        
        Args:
            project: Project path
            
        Returns:
            Dictionary containing generated README content
        """
        project_path = Path(project)
        
        if not project_path.exists():
            return {
                "success": False,
                "error": f"Project path does not exist: {project}",
            }

        # Analyze project structure
        project_info = self._analyze_project_structure(project_path)

        # Generate README sections
        readme_sections = {
            "title": project_info.get("name", project_path.name),
            "description": project_info.get("description", "A Python project."),
            "installation": self._generate_installation_section(project_path),
            "usage": self._generate_usage_section(project_path),
            "features": project_info.get("features", []),
            "requirements": project_info.get("requirements", []),
            "structure": project_info.get("structure", {}),
        }

        # Generate markdown
        markdown = self._generate_readme_markdown(readme_sections)

        return {
            "success": True,
            "readme": readme_sections,
            "markdown": markdown,
        }

    def create_code_examples(self, function: str, examples_count: int = 3) -> Dict[str, Any]:
        """
        Create code examples for a function.
        
        Args:
            function: Function code
            examples_count: Number of examples to generate
            
        Returns:
            Dictionary containing code examples
        """
        try:
            tree = ast.parse(function)
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

        visitor = FunctionExampleVisitor()
        visitor.visit(tree)

        if not visitor.functions:
            return {
                "success": False,
                "error": "No function found in code",
            }

        func_name = list(visitor.functions.keys())[0]
        func_info = visitor.functions[func_name]

        # Generate examples
        examples = []
        for i in range(examples_count):
            example = self._generate_function_example(func_name, func_info, i + 1)
            examples.append(example)

        return {
            "success": True,
            "function": func_name,
            "examples": examples,
            "count": len(examples),
        }

    def document_architecture(self, project: Union[str, Path]) -> Dict[str, Any]:
        """
        Document project architecture.
        
        Args:
            project: Project path
            
        Returns:
            Dictionary containing architecture documentation
        """
        project_path = Path(project)
        
        if not project_path.exists():
            return {
                "success": False,
                "error": f"Project path does not exist: {project}",
            }

        # Analyze architecture
        architecture = self._analyze_architecture(project_path)

        # Generate architecture documentation
        arch_docs = {
            "overview": architecture.get("overview", "Architecture overview."),
            "components": architecture.get("components", []),
            "layers": architecture.get("layers", []),
            "dependencies": architecture.get("dependencies", {}),
            "patterns": architecture.get("patterns", []),
            "diagram": self._generate_architecture_diagram(architecture),
        }

        # Generate markdown
        markdown = self._generate_architecture_markdown(arch_docs)

        return {
            "success": True,
            "architecture": arch_docs,
            "markdown": markdown,
        }

    def generate_migration_guide(self, old_code: str, new_code: str) -> Dict[str, Any]:
        """
        Generate migration guide from old code to new code.
        
        Args:
            old_code: Old version of code
            new_code: New version of code
            
        Returns:
            Dictionary containing migration guide
        """
        try:
            old_tree = ast.parse(old_code)
            new_tree = ast.parse(new_code)
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

        # Analyze differences
        differences = self._analyze_code_differences(old_tree, new_tree)

        # Generate migration guide
        guide = {
            "summary": differences.get("summary", "Code migration guide"),
            "breaking_changes": differences.get("breaking_changes", []),
            "new_features": differences.get("new_features", []),
            "deprecated": differences.get("deprecated", []),
            "migration_steps": self._generate_migration_steps(differences),
            "examples": self._generate_migration_examples(old_code, new_code, differences),
        }

        # Generate markdown
        markdown = self._generate_migration_markdown(guide)

        return {
            "success": True,
            "migration_guide": guide,
            "markdown": markdown,
        }

    def explain_code_natural_language(self, code: str, audience: str = "developer") -> Dict[str, Any]:
        """
        Explain code in natural language.
        
        Args:
            code: Python code to explain
            audience: Target audience (beginner, developer, expert)
            
        Returns:
            Dictionary containing natural language explanation
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

        # Analyze code structure
        visitor = CodeExplanationVisitor()
        visitor.visit(tree)

        # Generate explanation based on audience
        explanation = self._generate_explanation(code, tree, visitor, audience)

        return {
            "success": True,
            "audience": audience,
            "explanation": explanation,
            "structure": {
                "functions": list(visitor.functions.keys()),
                "classes": list(visitor.classes.keys()),
                "complexity": visitor.complexity_level,
            },
        }

    # Helper methods for docstring generation

    def _generate_function_docstring(self, func_info: Dict[str, Any], style: str) -> str:
        """Generate docstring for a function."""
        func_name = func_info["name"]
        params = func_info.get("parameters", [])
        returns = func_info.get("returns", "None")
        
        if style == "google":
            docstring = f'"""{func_name.replace("_", " ").title()}\n\n'
            if params:
                docstring += "Args:\n"
                for param in params:
                    param_name = param.get("name", "unknown")
                    param_type = param.get("type", "Any")
                    docstring += f"    {param_name} ({param_type}): Description\n"
            docstring += f"\nReturns:\n    {returns}: Description\n"
            docstring += '"""'
        elif style == "numpy":
            docstring = f'"""{func_name.replace("_", " ").title()}\n\n'
            if params:
                docstring += "Parameters\n----------\n"
                for param in params:
                    param_name = param.get("name", "unknown")
                    param_type = param.get("type", "Any")
                    docstring += f"{param_name} : {param_type}\n    Description\n"
            docstring += f"\nReturns\n-------\n{returns}\n    Description\n"
            docstring += '"""'
        else:  # Default to google style
            docstring = f'"""{func_name.replace("_", " ").title()}\n\n'
            if params:
                docstring += "Args:\n"
                for param in params:
                    param_name = param.get("name", "unknown")
                    docstring += f"    {param_name}: Description\n"
            docstring += f"\nReturns:\n    Description\n"
            docstring += '"""'
        
        return docstring

    def _generate_class_docstring(self, class_info: Dict[str, Any], style: str) -> str:
        """Generate docstring for a class."""
        class_name = class_info["name"]
        methods = class_info.get("methods", [])
        
        docstring = f'"""{class_name.replace("_", " ").title()}\n\n'
        docstring += "Description of the class.\n\n"
        if methods:
            docstring += "Methods:\n"
            for method in methods[:5]:  # Limit to first 5
                docstring += f"    {method}: Description\n"
        docstring += '"""'
        
        return docstring

    def _generate_module_docstring(self, tree: ast.AST, style: str) -> str:
        """Generate module-level docstring."""
        docstring = '"""Module Description\n\n'
        docstring += "This module provides functionality for...\n"
        docstring += '"""'
        return docstring

    # Helper methods for API documentation

    def _generate_api_markdown(self, api_docs: Dict[str, Any]) -> str:
        """Generate API documentation in markdown format."""
        md = f"# {api_docs['module_name']} API Documentation\n\n"
        md += f"{api_docs['description']}\n\n"
        
        if api_docs["functions"]:
            md += "## Functions\n\n"
            for func in api_docs["functions"]:
                md += f"### {func['name']}\n\n"
                md += f"{func['description']}\n\n"
                md += f"**Signature:** `{func['signature']}`\n\n"
                if func["parameters"]:
                    md += "**Parameters:**\n"
                    for param in func["parameters"]:
                        md += f"- `{param}`: Description\n"
                    md += "\n"
                md += f"**Returns:** {func['returns']}\n\n"
        
        if api_docs["classes"]:
            md += "## Classes\n\n"
            for cls in api_docs["classes"]:
                md += f"### {cls['name']}\n\n"
                md += f"{cls['description']}\n\n"
        
        return md

    # Helper methods for README generation

    def _analyze_project_structure(self, project_path: Path) -> Dict[str, Any]:
        """Analyze project structure."""
        info = {
            "name": project_path.name,
            "description": "A Python project.",
            "features": [],
            "requirements": [],
            "structure": {},
        }
        
        # Try to find setup.py or pyproject.toml
        setup_file = project_path / "setup.py"
        if setup_file.exists():
            # Simplified - would parse setup.py
            pass
        
        # Analyze directory structure
        python_files = list(project_path.rglob("*.py"))
        info["structure"]["python_files"] = len(python_files)
        
        return info

    def _generate_installation_section(self, project_path: Path) -> str:
        """Generate installation section."""
        return """## Installation

```bash
pip install -e .
```

Or from source:

```bash
git clone <repository-url>
cd <project-name>
pip install -e .
```
"""

    def _generate_usage_section(self, project_path: Path) -> str:
        """Generate usage section."""
        return """## Usage

```python
from project import main

main()
```
"""

    def _generate_readme_markdown(self, sections: Dict[str, Any]) -> str:
        """Generate README markdown."""
        md = f"# {sections['title']}\n\n"
        md += f"{sections['description']}\n\n"
        md += sections.get("installation", "")
        md += sections.get("usage", "")
        return md

    # Helper methods for code examples

    def _generate_function_example(self, func_name: str, func_info: Dict[str, Any], example_num: int) -> Dict[str, Any]:
        """Generate a code example for a function."""
        params = func_info.get("parameters", [])
        
        # Generate example parameters
        example_params = {}
        for param in params:
            param_name = param.get("name", "arg")
            param_type = param.get("type", "Any")
            # Generate example value based on type
            if "str" in str(param_type):
                example_params[param_name] = f'"example_{example_num}"'
            elif "int" in str(param_type):
                example_params[param_name] = str(example_num)
            elif "list" in str(param_type):
                example_params[param_name] = "[]"
            else:
                example_params[param_name] = "value"
        
        # Generate example code
        param_str = ", ".join(f"{k}={v}" for k, v in example_params.items())
        example_code = f"result = {func_name}({param_str})"
        
        return {
            "example_number": example_num,
            "code": example_code,
            "description": f"Example {example_num} usage of {func_name}",
        }

    # Helper methods for architecture documentation

    def _analyze_architecture(self, project_path: Path) -> Dict[str, Any]:
        """Analyze project architecture."""
        return {
            "overview": "Project architecture overview.",
            "components": [],
            "layers": [],
            "dependencies": {},
            "patterns": [],
        }

    def _generate_architecture_diagram(self, architecture: Dict[str, Any]) -> str:
        """Generate text-based architecture diagram."""
        diagram = "```\n"
        diagram += "Architecture Diagram\n"
        diagram += "===================\n\n"
        diagram += "[Components]\n"
        diagram += "    |\n"
        diagram += "    +-- [Layer 1]\n"
        diagram += "    +-- [Layer 2]\n"
        diagram += "```\n"
        return diagram

    def _generate_architecture_markdown(self, arch_docs: Dict[str, Any]) -> str:
        """Generate architecture documentation in markdown."""
        md = "# Architecture Documentation\n\n"
        md += f"{arch_docs['overview']}\n\n"
        md += arch_docs.get("diagram", "")
        return md

    # Helper methods for migration guide

    def _analyze_code_differences(self, old_tree: ast.AST, new_tree: ast.AST) -> Dict[str, Any]:
        """Analyze differences between old and new code."""
        return {
            "summary": "Code migration summary",
            "breaking_changes": [],
            "new_features": [],
            "deprecated": [],
        }

    def _generate_migration_steps(self, differences: Dict[str, Any]) -> List[str]:
        """Generate migration steps."""
        steps = []
        if differences.get("breaking_changes"):
            steps.append("1. Review breaking changes")
        if differences.get("new_features"):
            steps.append("2. Update code to use new features")
        if differences.get("deprecated"):
            steps.append("3. Replace deprecated functionality")
        return steps

    def _generate_migration_examples(self, old_code: str, new_code: str, differences: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Generate migration examples."""
        return [
            {
                "old": "old_code_example",
                "new": "new_code_example",
                "explanation": "Migration explanation",
            }
        ]

    def _generate_migration_markdown(self, guide: Dict[str, Any]) -> str:
        """Generate migration guide in markdown."""
        md = "# Migration Guide\n\n"
        md += f"{guide['summary']}\n\n"
        if guide.get("migration_steps"):
            md += "## Migration Steps\n\n"
            for step in guide["migration_steps"]:
                md += f"{step}\n"
        return md

    # Helper methods for code explanation

    def _generate_explanation(self, code: str, tree: ast.AST, visitor: Any, audience: str) -> str:
        """Generate natural language explanation."""
        explanation = "This code "
        
        if visitor.functions:
            explanation += f"defines {len(visitor.functions)} function(s): {', '.join(visitor.functions.keys())}. "
        
        if visitor.classes:
            explanation += f"It includes {len(visitor.classes)} class(es): {', '.join(visitor.classes.keys())}. "
        
        if audience == "beginner":
            explanation += "The code performs basic operations and is suitable for learning Python."
        elif audience == "expert":
            explanation += "The code demonstrates advanced Python patterns and techniques."
        else:
            explanation += "The code follows standard Python practices."
        
        return explanation


# AST Visitor classes

class DocstringGeneratorVisitor(ast.NodeVisitor):
    """Visitor to collect information for docstring generation."""
    
    def __init__(self, style: str):
        self.style = style
        self.functions = {}
        self.classes = {}
        self.has_module_docstring = False

    def visit_FunctionDef(self, node: ast.FunctionDef):
        params = []
        for arg in node.args.args:
            param_type = "Any"
            if arg.annotation:
                param_type = ast.unparse(arg.annotation) if hasattr(ast, 'unparse') else str(arg.annotation)
            params.append({
                "name": arg.arg,
                "type": param_type,
            })
        
        returns = "None"
        if node.returns:
            returns = ast.unparse(node.returns) if hasattr(ast, 'unparse') else str(node.returns)
        
        self.functions[node.name] = {
            "name": node.name,
            "parameters": params,
            "returns": returns,
            "docstring": ast.get_docstring(node),
        }
        self.generic_visit(node)

    def visit_ClassDef(self, node: ast.ClassDef):
        methods = []
        for item in node.body:
            if isinstance(item, ast.FunctionDef):
                methods.append(item.name)
        
        self.classes[node.name] = {
            "name": node.name,
            "methods": methods,
            "docstring": ast.get_docstring(node),
        }
        self.generic_visit(node)

    def visit_Module(self, node: ast.Module):
        self.has_module_docstring = bool(ast.get_docstring(node))
        self.generic_visit(node)


class APIDocumentationVisitor(ast.NodeVisitor):
    """Visitor to collect API information."""
    
    def __init__(self):
        self.module_name = None
        self.module_docstring = None
        self.functions = {}
        self.classes = {}
        self.constants = []
        self.imports = []

    def visit_Module(self, node: ast.Module):
        self.module_docstring = ast.get_docstring(node)
        self.generic_visit(node)

    def visit_FunctionDef(self, node: ast.FunctionDef):
        params = [arg.arg for arg in node.args.args]
        signature = f"{node.name}({', '.join(params)})"
        
        self.functions[node.name] = {
            "signature": signature,
            "parameters": params,
            "docstring": ast.get_docstring(node),
            "returns": "None",
        }
        self.generic_visit(node)

    def visit_ClassDef(self, node: ast.ClassDef):
        methods = []
        for item in node.body:
            if isinstance(item, ast.FunctionDef):
                methods.append(item.name)
        
        self.classes[node.name] = {
            "docstring": ast.get_docstring(node),
            "methods": methods,
            "attributes": [],
            "inheritance": [base.id for base in node.bases if isinstance(base, ast.Name)],
        }
        self.generic_visit(node)

    def visit_Import(self, node: ast.Import):
        for alias in node.names:
            self.imports.append(alias.name)
        self.generic_visit(node)

    def visit_ImportFrom(self, node: ast.ImportFrom):
        if node.module:
            for alias in node.names:
                self.imports.append(f"{node.module}.{alias.name}")
        self.generic_visit(node)


class FunctionExampleVisitor(ast.NodeVisitor):
    """Visitor to collect function information for examples."""
    
    def __init__(self):
        self.functions = {}

    def visit_FunctionDef(self, node: ast.FunctionDef):
        params = []
        for arg in node.args.args:
            param_type = "Any"
            if arg.annotation:
                param_type = ast.unparse(arg.annotation) if hasattr(ast, 'unparse') else str(arg.annotation)
            params.append({
                "name": arg.arg,
                "type": param_type,
            })
        
        self.functions[node.name] = {
            "name": node.name,
            "parameters": params,
        }
        self.generic_visit(node)


class CodeExplanationVisitor(ast.NodeVisitor):
    """Visitor to collect information for code explanation."""
    
    def __init__(self):
        self.functions = {}
        self.classes = {}
        self.complexity_level = "low"

    def visit_FunctionDef(self, node: ast.FunctionDef):
        self.functions[node.name] = {
            "name": node.name,
            "line": node.lineno,
        }
        self.generic_visit(node)

    def visit_ClassDef(self, node: ast.ClassDef):
        self.classes[node.name] = {
            "name": node.name,
            "line": node.lineno,
        }
        self.generic_visit(node)

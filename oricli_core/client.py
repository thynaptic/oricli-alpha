from __future__ import annotations
"""
OricliAlpha Core Client - Unified interface for all OricliAlpha capabilities
"""

import time
import uuid
import threading
import httpx
from typing import Any, Dict, List, Optional, Union
from pathlib import Path

from oricli_core.brain.registry import ModuleRegistry
from oricli_core.exceptions import (
    ModuleNotFoundError,
    ModuleOperationError,
    InvalidParameterError,
    ClientError,
)
from oricli_core.services.tool_registry import ToolRegistry
from oricli_core.types.models import (
    ChatCompletionRequest,
    ChatCompletionResponse,
    ChatCompletionChoice,
    ChatCompletionUsage,
    ChatMessage,
    EmbeddingRequest,
    EmbeddingResponse,
    EmbeddingData,
    EmbeddingUsage,
    ModelInfo,
    ModelsListResponse,
    ToolDefinition,
    URLContextMetadata,
)
from oricli_core.services.agent_profile_service import AgentProfileService


class BrainModuleProxy:
    """Proxy for accessing brain modules dynamically"""
    
    def __init__(self, client: "OricliAlphaClient") -> None:
        """
        Initialize brain module proxy
        
        Args:
            client: OricliAlphaClient instance
        """
        self._client = client
    
    def __getattr__(self, name: str) -> "BrainModuleWrapper":
        """
        Dynamically access brain modules
        
        Args:
            name: Module name
        
        Returns:
            BrainModuleWrapper instance
        
        Raises:
            ModuleNotFoundError: If module is not found
        """
        module = ModuleRegistry.get_module(name)
        if module is None:
            raise ModuleNotFoundError(name)
        return BrainModuleWrapper(self._client, module, name)


class BrainModuleWrapper:
    """Wrapper for brain module operations"""
    
    def __init__(self, client: "OricliAlphaClient", module: Any, module_name: str) -> None:
        """
        Initialize brain module wrapper
        
        Args:
            client: OricliAlphaClient instance
            module: BaseBrainModule instance
            module_name: Name of the module
        """
        self._client = client
        self._module = module
        self._module_name = module_name
    
    def __getattr__(self, operation: str) -> Any:
        """
        Dynamically access module operations
        
        Args:
            operation: Operation name
        
        Returns:
            Callable that executes the operation
        """
        def execute_operation(**kwargs: Any) -> dict[str, Any]:
            """
            Execute module operation
            
            Args:
                **kwargs: Operation parameters
            
            Returns:
                Operation result dictionary
            """
            if self._client.base_url:
                return self._client._make_remote_request(
                    "POST", 
                    f"/v1/modules/{self._module_name}/{operation}", 
                    kwargs
                )
            return self._module.execute(operation, kwargs)
        return execute_operation


class ChatCompletions:
    """Chat completions API"""
    
    def __init__(self, client: "OricliAlphaClient"):
        self._client = client
    
    def create(
        self,
        model: str = "oricli-cognitive",
        messages: List[Dict[str, str]] = None,
        temperature: Optional[float] = 0.7,
        max_tokens: Optional[int] = None,
        stream: Optional[bool] = False,
        **kwargs
    ) -> ChatCompletionResponse:
        """Create a chat completion"""
        if messages is None:
            raise InvalidParameterError("messages", "None", "messages is required")
        
        # Convert messages to ChatMessage objects
        chat_messages = [
            ChatMessage(role=msg.get("role", "user"), content=msg.get("content", ""))
            for msg in messages
        ]
        
        request = ChatCompletionRequest(
            model=model,
            messages=chat_messages,
            temperature=temperature,
            max_tokens=max_tokens,
            stream=stream,
            **kwargs
        )
        
        return self._client._generate_chat_completion(request)


class Embeddings:
    """Embeddings API"""
    
    def __init__(self, client: "OricliAlphaClient"):
        self._client = client
    
    def create(
        self,
        input: Union[str, List[str]],
        model: str = "oricli-embeddings",
        **kwargs
    ) -> EmbeddingResponse:
        """Create embeddings"""
        request = EmbeddingRequest(input=input, model=model, **kwargs)
        return self._client._generate_embeddings(request)


class PythonLLM:
    """
    Python LLM API - Interface for Python code understanding, generation, and reasoning
    
    Provides methods for:
    - Semantic code understanding
    - Code embedding generation
    - Code reasoning (Phase 2)
    - Code generation (Phase 3)
    - Code completion (Phase 3)
    """
    
    def __init__(self, client: "OricliAlphaClient"):
        self._client = client
    
    def understand(self, code: str, analysis_type: str = "full") -> Dict[str, Any]:
        """
        Perform semantic understanding of Python code.
        
        Args:
            code: Python code to analyze
            analysis_type: Type of analysis (full, semantic, types, dependencies)
            
        Returns:
            Dictionary containing semantic analysis results
        """
        from oricli_core.brain.registry import ModuleRegistry
        
        module = ModuleRegistry.get_module("python_semantic_understanding")
        if module is None:
            raise ModuleNotFoundError("python_semantic_understanding")
        
        return module.execute("analyze_semantics", {"code": code})
    
    def embed(self, code: str) -> Dict[str, Any]:
        """
        Generate semantic embedding for Python code.
        
        Args:
            code: Python code to embed
            
        Returns:
            Dictionary containing embedding vector and metadata
        """
        from oricli_core.brain.registry import ModuleRegistry
        
        module = ModuleRegistry.get_module("python_code_embeddings")
        if module is None:
            raise ModuleNotFoundError("python_code_embeddings")
        
        return module.execute("embed_code", {"code": code})
    
    def similar_code(self, query_code: str, codebase: List[str], top_k: int = 5) -> Dict[str, Any]:
        """
        Find similar code in a codebase.
        
        Args:
            query_code: Code to find similarities for
            codebase: List of code snippets to search
            top_k: Number of top results to return
            
        Returns:
            Dictionary containing similar code snippets with similarity scores
        """
        from oricli_core.brain.registry import ModuleRegistry
        
        module = ModuleRegistry.get_module("python_code_embeddings")
        if module is None:
            raise ModuleNotFoundError("python_code_embeddings")
        
        return module.execute("similar_code", {
            "query_code": query_code,
            "codebase": codebase,
            "top_k": top_k,
        })

    def remember_pattern(self, pattern: str, context: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        Remember a code pattern in memory.
        
        Args:
            pattern: Code pattern to remember
            context: Context information (project, usage, description, etc.)
            
        Returns:
            Dictionary containing pattern ID and storage status
        """
        from oricli_core.brain.registry import ModuleRegistry
        
        module = ModuleRegistry.get_module("python_code_memory")
        if module is None:
            raise ModuleNotFoundError("python_code_memory")
        
        return module.execute("remember_code_pattern", {
            "pattern": pattern,
            "context": context or {},
        })
    
    def recall_patterns(self, code: str, top_k: int = 5) -> Dict[str, Any]:
        """
        Recall similar code patterns from memory.
        
        Args:
            code: Code to find similar patterns for
            top_k: Number of top patterns to return
            
        Returns:
            Dictionary containing similar patterns with similarity scores
        """
        from oricli_core.brain.registry import ModuleRegistry
        
        module = ModuleRegistry.get_module("python_code_memory")
        if module is None:
            raise ModuleNotFoundError("python_code_memory")
        
        return module.execute("recall_similar_patterns", {
            "code": code,
            "top_k": top_k,
        })
    
    def learn_project(self, project_path: Union[str, Path]) -> Dict[str, Any]:
        """
        Learn the structure of a Python project.
        
        Args:
            project_path: Path to project root
            
        Returns:
            Dictionary containing learned project structure
        """
        from oricli_core.brain.registry import ModuleRegistry
        from pathlib import Path
        
        module = ModuleRegistry.get_module("python_code_memory")
        if module is None:
            raise ModuleNotFoundError("python_code_memory")
        
        return module.execute("learn_project_structure", {
            "project_path": str(Path(project_path)),
        })
    
    def generate(self, requirements: str, context: Dict[str, Any] = None, **kwargs) -> Dict[str, Any]:
        """
        Generate Python code through reasoning.
        
        Args:
            requirements: Requirements for code generation
            context: Additional context
            **kwargs: Additional parameters (style, reasoning_method, etc.)
            
        Returns:
            Dictionary containing generated code and metadata
        """
        from oricli_core.brain.registry import ModuleRegistry
        
        module = ModuleRegistry.get_module("reasoning_code_generator")
        if module is None:
            raise ModuleNotFoundError("reasoning_code_generator")
        
        reasoning_method = kwargs.get("reasoning_method", "cot")
        
        if context:
            return module.execute("generate_with_context", {
                "requirements": requirements,
                "context": context,
            })
        else:
            return module.execute("generate_code_reasoning", {
                "requirements": requirements,
                "reasoning_method": reasoning_method,
            })
    
    def reason(self, code: str, query: str, reasoning_type: str = "behavior") -> Dict[str, Any]:
        """
        Reason about Python code.
        
        Args:
            code: Python code to reason about
            query: Reasoning query (optional, used for future complex reasoning)
            reasoning_type: Type of reasoning (behavior, optimization, correctness)
            
        Returns:
            Dictionary containing reasoning results
        """
        from oricli_core.brain.registry import ModuleRegistry
        
        if reasoning_type == "behavior":
            module = ModuleRegistry.get_module("program_behavior_reasoning")
            if module is None:
                raise ModuleNotFoundError("program_behavior_reasoning")
            
            return module.execute("predict_execution", {
                "code": code,
                "inputs": {},
            })
        
        elif reasoning_type == "optimization":
            module = ModuleRegistry.get_module("code_optimization_reasoning")
            if module is None:
                raise ModuleNotFoundError("code_optimization_reasoning")
            
            return module.execute("identify_optimizations", {
                "code": code,
            })
        
        elif reasoning_type == "correctness":
            module = ModuleRegistry.get_module("program_behavior_reasoning")
            if module is None:
                raise ModuleNotFoundError("program_behavior_reasoning")
            
            return module.execute("verify_correctness", {
                "code": code,
                "spec": {},
            })
        
        else:
            return {
                "success": False,
                "error": f"Unknown reasoning type: {reasoning_type}",
            }
    
    def compare_code(self, code1: str, code2: str) -> Dict[str, Any]:
        """
        Compare two code pieces and find relationships.
        
        Args:
            code1: First code snippet
            code2: Second code snippet
            
        Returns:
            Dictionary containing comparison and relationship analysis
        """
        from oricli_core.brain.registry import ModuleRegistry
        
        module = ModuleRegistry.get_module("code_to_code_reasoning")
        if module is None:
            raise ModuleNotFoundError("code_to_code_reasoning")
        
        return module.execute("compare_code", {
            "code1": code1,
            "code2": code2,
        })
    
    def find_optimizations(self, code: str) -> Dict[str, Any]:
        """
        Find optimization opportunities in code.
        
        Args:
            code: Python code to analyze
            
        Returns:
            Dictionary containing optimization opportunities
        """
        from oricli_core.brain.registry import ModuleRegistry
        
        module = ModuleRegistry.get_module("code_optimization_reasoning")
        if module is None:
            raise ModuleNotFoundError("code_optimization_reasoning")
        
        return module.execute("identify_optimizations", {
            "code": code,
        })
    
    def analyze_performance(self, code: str) -> Dict[str, Any]:
        """
        Analyze code performance.
        
        Args:
            code: Python code to analyze
            
        Returns:
            Dictionary containing performance analysis
        """
        from oricli_core.brain.registry import ModuleRegistry
        
        module = ModuleRegistry.get_module("code_optimization_reasoning")
        if module is None:
            raise ModuleNotFoundError("code_optimization_reasoning")
        
        return module.execute("reason_about_performance", {
            "code": code,
        })
    
    def complete(self, partial_code: str, context: Dict[str, Any] = None, **kwargs) -> Dict[str, Any]:
        """
        Complete Python code with context awareness.
        
        Args:
            partial_code: Partial code to complete
            context: Additional context
            **kwargs: Additional parameters (style, etc.)
            
        Returns:
            Dictionary containing completed code and metadata
        """
        from oricli_core.brain.registry import ModuleRegistry
        
        module = ModuleRegistry.get_module("reasoning_code_completion")
        if module is None:
            raise ModuleNotFoundError("reasoning_code_completion")
        
        style = kwargs.get("style")
        
        if style:
            return module.execute("complete_with_style", {
                "partial_code": partial_code,
                "style": style,
            })
        else:
            return module.execute("complete_code_reasoning", {
                "partial_code": partial_code,
                "context": context or {},
            })
    
    def generate_tests(self, code: str, test_type: str = "all") -> Dict[str, Any]:
        """
        Generate tests for Python code.
        
        Args:
            code: Python code to generate tests for
            test_type: Type of tests (all, unit, edge_case, property)
            
        Returns:
            Dictionary containing generated test suite and test cases
        """
        from oricli_core.brain.registry import ModuleRegistry
        
        module = ModuleRegistry.get_module("test_generation_reasoning")
        if module is None:
            raise ModuleNotFoundError("test_generation_reasoning")
        
        if test_type == "edge_case":
            return module.execute("generate_edge_case_tests", {"code": code})
        elif test_type == "property":
            return module.execute("generate_property_tests", {"code": code})
        else:
            return module.execute("generate_tests", {"code": code})
    
    def review_code(self, code: str, review_type: str = "comprehensive") -> Dict[str, Any]:
        """
        Review Python code with automated analysis.
        
        Args:
            code: Python code to review
            review_type: Type of review (comprehensive, quick, security, performance, style)
            
        Returns:
            Dictionary containing review results with issues, suggestions, and scores
        """
        from oricli_core.brain.registry import ModuleRegistry
        
        module = ModuleRegistry.get_module("python_code_review")
        if module is None:
            raise ModuleNotFoundError("python_code_review")
        
        return module.execute("review_code", {
            "code": code,
            "review_type": review_type,
        })
    
    def score_quality(self, code: str) -> Dict[str, Any]:
        """
        Score code quality on a scale of 0-100.
        
        Args:
            code: Python code to score
            
        Returns:
            Dictionary containing quality score, breakdown, and issues
        """
        from oricli_core.brain.registry import ModuleRegistry
        
        module = ModuleRegistry.get_module("python_code_review")
        if module is None:
            raise ModuleNotFoundError("python_code_review")
        
        return module.execute("score_code_quality", {"code": code})
    
    def check_best_practices(self, code: str) -> Dict[str, Any]:
        """
        Check code against Python best practices.
        
        Args:
            code: Python code to check
            
        Returns:
            Dictionary containing violations and recommendations
        """
        from oricli_core.brain.registry import ModuleRegistry
        
        module = ModuleRegistry.get_module("python_code_review")
        if module is None:
            raise ModuleNotFoundError("python_code_review")
        
        return module.execute("check_best_practices", {"code": code})
    
    def detect_smells(self, code: str) -> Dict[str, Any]:
        """
        Detect code smells in Python code.
        
        Args:
            code: Python code to analyze
            
        Returns:
            Dictionary containing detected smells with severity and suggestions
        """
        from oricli_core.brain.registry import ModuleRegistry
        
        module = ModuleRegistry.get_module("python_code_review")
        if module is None:
            raise ModuleNotFoundError("python_code_review")
        
        return module.execute("detect_code_smells", {"code": code})
    
    def analyze_technical_debt(self, code: str, project: Optional[str] = None) -> Dict[str, Any]:
        """
        Analyze technical debt in code.
        
        Args:
            code: Python code to analyze
            project: Optional project context
            
        Returns:
            Dictionary containing technical debt analysis
        """
        from oricli_core.brain.registry import ModuleRegistry
        
        module = ModuleRegistry.get_module("python_code_review")
        if module is None:
            raise ModuleNotFoundError("python_code_review")
        
        return module.execute("analyze_technical_debt", {
            "code": code,
            "project": project,
        })
    
    def suggest_improvements(self, code: str, focus: str = "all") -> Dict[str, Any]:
        """
        Suggest code improvements.
        
        Args:
            code: Python code to analyze
            focus: Focus area (all, performance, readability, maintainability, security)
            
        Returns:
            Dictionary containing improvement suggestions
        """
        from oricli_core.brain.registry import ModuleRegistry
        
        module = ModuleRegistry.get_module("python_code_review")
        if module is None:
            raise ModuleNotFoundError("python_code_review")
        
        return module.execute("suggest_improvements", {
            "code": code,
            "focus": focus,
        })
    
    def calculate_metrics(self, code: str) -> Dict[str, Any]:
        """
        Calculate comprehensive code metrics.
        
        Args:
            code: Python code to analyze
            
        Returns:
            Dictionary containing all calculated metrics
        """
        from oricli_core.brain.registry import ModuleRegistry
        
        module = ModuleRegistry.get_module("python_code_metrics")
        if module is None:
            raise ModuleNotFoundError("python_code_metrics")
        
        return module.execute("calculate_metrics", {"code": code})
    
    def analyze_complexity_metrics(self, code: str) -> Dict[str, Any]:
        """
        Analyze code complexity metrics.
        
        Args:
            code: Python code to analyze
            
        Returns:
            Dictionary containing complexity metrics (cyclomatic, cognitive)
        """
        from oricli_core.brain.registry import ModuleRegistry
        
        module = ModuleRegistry.get_module("python_code_metrics")
        if module is None:
            raise ModuleNotFoundError("python_code_metrics")
        
        return module.execute("analyze_complexity", {"code": code})
    
    def score_maintainability(self, code: str) -> Dict[str, Any]:
        """
        Score code maintainability.
        
        Args:
            code: Python code to analyze
            
        Returns:
            Dictionary containing maintainability score and factors
        """
        from oricli_core.brain.registry import ModuleRegistry
        
        module = ModuleRegistry.get_module("python_code_metrics")
        if module is None:
            raise ModuleNotFoundError("python_code_metrics")
        
        return module.execute("score_maintainability", {"code": code})
    
    def analyze_test_coverage(self, code: str, tests: str = "") -> Dict[str, Any]:
        """
        Analyze test coverage for code.
        
        Args:
            code: Python code to analyze
            tests: Test code (optional, for heuristic analysis)
            
        Returns:
            Dictionary containing test coverage analysis
        """
        from oricli_core.brain.registry import ModuleRegistry
        
        module = ModuleRegistry.get_module("python_code_metrics")
        if module is None:
            raise ModuleNotFoundError("python_code_metrics")
        
        return module.execute("analyze_test_coverage", {
            "code": code,
            "tests": tests,
        })
    
    def measure_documentation_coverage(self, code: str) -> Dict[str, Any]:
        """
        Measure documentation coverage.
        
        Args:
            code: Python code to analyze
            
        Returns:
            Dictionary containing documentation coverage metrics
        """
        from oricli_core.brain.registry import ModuleRegistry
        
        module = ModuleRegistry.get_module("python_code_metrics")
        if module is None:
            raise ModuleNotFoundError("python_code_metrics")
        
        return module.execute("measure_documentation_coverage", {"code": code})
    
    def analyze_dependency_complexity(self, project: Union[str, Path]) -> Dict[str, Any]:
        """
        Analyze dependency complexity for a project.
        
        Args:
            project: Project path
            
        Returns:
            Dictionary containing dependency complexity metrics
        """
        from oricli_core.brain.registry import ModuleRegistry
        from pathlib import Path
        
        module = ModuleRegistry.get_module("python_code_metrics")
        if module is None:
            raise ModuleNotFoundError("python_code_metrics")
        
        return module.execute("analyze_dependency_complexity", {
            "project": str(Path(project)),
        })
    
    def generate_docstring(self, code: str, style: str = "google") -> Dict[str, Any]:
        """
        Generate comprehensive docstring for code.
        
        Args:
            code: Python code to document
            style: Docstring style (google, numpy, sphinx, restructured)
            
        Returns:
            Dictionary containing generated docstrings
        """
        from oricli_core.brain.registry import ModuleRegistry
        
        module = ModuleRegistry.get_module("python_documentation_generator")
        if module is None:
            raise ModuleNotFoundError("python_documentation_generator")
        
        return module.execute("generate_docstring", {
            "code": code,
            "style": style,
        })
    
    def generate_api_docs(self, module: str) -> Dict[str, Any]:
        """
        Generate API documentation for a module.
        
        Args:
            module: Module code to document
            
        Returns:
            Dictionary containing API documentation
        """
        from oricli_core.brain.registry import ModuleRegistry
        
        module_obj = ModuleRegistry.get_module("python_documentation_generator")
        if module_obj is None:
            raise ModuleNotFoundError("python_documentation_generator")
        
        return module_obj.execute("generate_api_docs", {"module": module})
    
    def generate_readme(self, project: Union[str, Path]) -> Dict[str, Any]:
        """
        Generate README file for a project.
        
        Args:
            project: Project path
            
        Returns:
            Dictionary containing generated README content
        """
        from oricli_core.brain.registry import ModuleRegistry
        from pathlib import Path
        
        module = ModuleRegistry.get_module("python_documentation_generator")
        if module is None:
            raise ModuleNotFoundError("python_documentation_generator")
        
        return module.execute("generate_readme", {
            "project": str(Path(project)),
        })
    
    def create_code_examples(self, function: str, examples_count: int = 3) -> Dict[str, Any]:
        """
        Create code examples for a function.
        
        Args:
            function: Function code
            examples_count: Number of examples to generate
            
        Returns:
            Dictionary containing code examples
        """
        from oricli_core.brain.registry import ModuleRegistry
        
        module = ModuleRegistry.get_module("python_documentation_generator")
        if module is None:
            raise ModuleNotFoundError("python_documentation_generator")
        
        return module.execute("create_code_examples", {
            "function": function,
            "examples_count": examples_count,
        })
    
    def document_architecture(self, project: Union[str, Path]) -> Dict[str, Any]:
        """
        Document project architecture.
        
        Args:
            project: Project path
            
        Returns:
            Dictionary containing architecture documentation
        """
        from oricli_core.brain.registry import ModuleRegistry
        from pathlib import Path
        
        module = ModuleRegistry.get_module("python_documentation_generator")
        if module is None:
            raise ModuleNotFoundError("python_documentation_generator")
        
        return module.execute("document_architecture", {
            "project": str(Path(project)),
        })
    
    def generate_migration_guide(self, old_code: str, new_code: str) -> Dict[str, Any]:
        """
        Generate migration guide from old code to new code.
        
        Args:
            old_code: Old version of code
            new_code: New version of code
            
        Returns:
            Dictionary containing migration guide
        """
        from oricli_core.brain.registry import ModuleRegistry
        
        module = ModuleRegistry.get_module("python_documentation_generator")
        if module is None:
            raise ModuleNotFoundError("python_documentation_generator")
        
        return module.execute("generate_migration_guide", {
            "old_code": old_code,
            "new_code": new_code,
        })
    
    def explain_code_natural_language(self, code: str, audience: str = "developer") -> Dict[str, Any]:
        """
        Explain code in natural language.
        
        Args:
            code: Python code to explain
            audience: Target audience (beginner, developer, expert)
            
        Returns:
            Dictionary containing natural language explanation
        """
        from oricli_core.brain.registry import ModuleRegistry
        
        module = ModuleRegistry.get_module("python_documentation_generator")
        if module is None:
            raise ModuleNotFoundError("python_documentation_generator")
        
        return module.execute("explain_code_natural_language", {
            "code": code,
            "audience": audience,
        })
    
    def explain_code(self, code: str, audience: str = "developer", detail_level: str = "medium") -> Dict[str, Any]:
        """
        Explain code in natural language with detail level control.
        
        Args:
            code: Python code to explain
            audience: Target audience (beginner, developer, expert)
            detail_level: Detail level (simple, medium, detailed)
            
        Returns:
            Dictionary containing code explanation
        """
        from oricli_core.brain.registry import ModuleRegistry
        
        module = ModuleRegistry.get_module("python_code_explanation")
        if module is None:
            raise ModuleNotFoundError("python_code_explanation")
        
        return module.execute("explain_code", {
            "code": code,
            "audience": audience,
            "detail_level": detail_level,
        })
    
    def answer_code_question(self, code: str, question: str) -> Dict[str, Any]:
        """
        Answer a question about code.
        
        Args:
            code: Python code to analyze
            question: Question about the code
            
        Returns:
            Dictionary containing answer to the question
        """
        from oricli_core.brain.registry import ModuleRegistry
        
        module = ModuleRegistry.get_module("python_code_explanation")
        if module is None:
            raise ModuleNotFoundError("python_code_explanation")
        
        return module.execute("answer_code_question", {
            "code": code,
            "question": question,
        })
    
    def create_walkthrough(self, code: str, steps: Optional[int] = None) -> Dict[str, Any]:
        """
        Create a step-by-step walkthrough of code.
        
        Args:
            code: Python code to walk through
            steps: Number of steps (auto-determined if None)
            
        Returns:
            Dictionary containing walkthrough steps
        """
        from oricli_core.brain.registry import ModuleRegistry
        
        module = ModuleRegistry.get_module("python_code_explanation")
        if module is None:
            raise ModuleNotFoundError("python_code_explanation")
        
        return module.execute("create_walkthrough", {
            "code": code,
            "steps": steps,
        })
    
    def explain_design_decision(self, code: str, context: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        Explain design decisions in code.
        
        Args:
            code: Python code to analyze
            context: Additional context about the design
            
        Returns:
            Dictionary containing design decision explanations
        """
        from oricli_core.brain.registry import ModuleRegistry
        
        module = ModuleRegistry.get_module("python_code_explanation")
        if module is None:
            raise ModuleNotFoundError("python_code_explanation")
        
        return module.execute("explain_design_decision", {
            "code": code,
            "context": context or {},
        })
    
    def clarify_complex_section(self, code: str, section: Optional[str] = None) -> Dict[str, Any]:
        """
        Clarify a complex section of code.
        
        Args:
            code: Python code to analyze
            section: Specific section to clarify (function/class name, or None for auto-detect)
            
        Returns:
            Dictionary containing clarification
        """
        from oricli_core.brain.registry import ModuleRegistry
        
        module = ModuleRegistry.get_module("python_code_explanation")
        if module is None:
            raise ModuleNotFoundError("python_code_explanation")
        
        return module.execute("clarify_complex_section", {
            "code": code,
            "section": section,
        })
    
    def generate_tutorial(self, code: str, topic: Optional[str] = None) -> Dict[str, Any]:
        """
        Generate a tutorial for code.
        
        Args:
            code: Python code to create tutorial for
            topic: Tutorial topic (auto-determined if None)
            
        Returns:
            Dictionary containing tutorial content
        """
        from oricli_core.brain.registry import ModuleRegistry
        
        module = ModuleRegistry.get_module("python_code_explanation")
        if module is None:
            raise ModuleNotFoundError("python_code_explanation")
        
        return module.execute("generate_tutorial", {
            "code": code,
            "topic": topic,
        })
    
    def suggest_refactorings(self, code: str, refactoring_type: str = "all") -> Dict[str, Any]:
        """
        Suggest refactoring opportunities.
        
        Args:
            code: Python code to analyze
            refactoring_type: Type of refactoring (all, extract_method, extract_class, rename, simplify)
            
        Returns:
            Dictionary containing refactoring suggestions
        """
        from oricli_core.brain.registry import ModuleRegistry
        
        module = ModuleRegistry.get_module("python_refactoring_reasoning")
        if module is None:
            raise ModuleNotFoundError("python_refactoring_reasoning")
        
        return module.execute("suggest_refactorings", {
            "code": code,
            "refactoring_type": refactoring_type,
        })
    
    def refactor_extract_method(self, code: str, selection: Dict[str, Any]) -> Dict[str, Any]:
        """
        Extract a method from selected code.
        
        Args:
            code: Python code to refactor
            selection: Selection information (start_line, end_line, method_name)
            
        Returns:
            Dictionary containing refactored code
        """
        from oricli_core.brain.registry import ModuleRegistry
        
        module = ModuleRegistry.get_module("python_refactoring_reasoning")
        if module is None:
            raise ModuleNotFoundError("python_refactoring_reasoning")
        
        return module.execute("refactor_extract_method", {
            "code": code,
            "selection": selection,
        })
    
    def refactor_extract_class(self, code: str, selection: Dict[str, Any]) -> Dict[str, Any]:
        """
        Extract a class from selected code.
        
        Args:
            code: Python code to refactor
            selection: Selection information (start_line, end_line, class_name)
            
        Returns:
            Dictionary containing refactored code
        """
        from oricli_core.brain.registry import ModuleRegistry
        
        module = ModuleRegistry.get_module("python_refactoring_reasoning")
        if module is None:
            raise ModuleNotFoundError("python_refactoring_reasoning")
        
        return module.execute("refactor_extract_class", {
            "code": code,
            "selection": selection,
        })
    
    def refactor_rename(self, code: str, old_name: str, new_name: str) -> Dict[str, Any]:
        """
        Rename a symbol with scope awareness.
        
        Args:
            code: Python code to refactor
            old_name: Old symbol name
            new_name: New symbol name
            
        Returns:
            Dictionary containing refactored code
        """
        from oricli_core.brain.registry import ModuleRegistry
        
        module = ModuleRegistry.get_module("python_refactoring_reasoning")
        if module is None:
            raise ModuleNotFoundError("python_refactoring_reasoning")
        
        return module.execute("refactor_rename", {
            "code": code,
            "old_name": old_name,
            "new_name": new_name,
        })
    
    def verify_refactoring(self, original: str, refactored: str) -> Dict[str, Any]:
        """
        Verify that refactoring maintains correctness.
        
        Args:
            original: Original code
            refactored: Refactored code
            
        Returns:
            Dictionary containing verification results
        """
        from oricli_core.brain.registry import ModuleRegistry
        
        module = ModuleRegistry.get_module("python_refactoring_reasoning")
        if module is None:
            raise ModuleNotFoundError("python_refactoring_reasoning")
        
        return module.execute("verify_refactoring", {
            "original": original,
            "refactored": refactored,
        })
    
    def refactor_multi_file(self, project: Union[str, Path], refactoring: Dict[str, Any]) -> Dict[str, Any]:
        """
        Perform refactoring across multiple files.
        
        Args:
            project: Project path
            refactoring: Refactoring specification (type, old_name, new_name)
            
        Returns:
            Dictionary containing multi-file refactoring results
        """
        from oricli_core.brain.registry import ModuleRegistry
        from pathlib import Path
        
        module = ModuleRegistry.get_module("python_refactoring_reasoning")
        if module is None:
            raise ModuleNotFoundError("python_refactoring_reasoning")
        
        return module.execute("refactor_multi_file", {
            "project": str(Path(project)),
            "refactoring": refactoring,
        })
    
    def plan_migration(self, code: str, target_version: str = "3.11") -> Dict[str, Any]:
        """
        Plan a migration to target Python version.
        
        Args:
            code: Python code to migrate
            target_version: Target Python version
            
        Returns:
            Dictionary containing migration plan
        """
        from oricli_core.brain.registry import ModuleRegistry
        
        module = ModuleRegistry.get_module("python_migration_assistant")
        if module is None:
            raise ModuleNotFoundError("python_migration_assistant")
        
        return module.execute("plan_migration", {
            "code": code,
            "target_version": target_version,
        })
    
    def migrate_python_version(self, code: str, from_version: str = "2.7", to_version: str = "3.11") -> Dict[str, Any]:
        """
        Migrate code from one Python version to another.
        
        Args:
            code: Python code to migrate
            from_version: Source Python version
            to_version: Target Python version
            
        Returns:
            Dictionary containing migrated code
        """
        from oricli_core.brain.registry import ModuleRegistry
        
        module = ModuleRegistry.get_module("python_migration_assistant")
        if module is None:
            raise ModuleNotFoundError("python_migration_assistant")
        
        return module.execute("migrate_python_version", {
            "code": code,
            "from_version": from_version,
            "to_version": to_version,
        })
    
    def migrate_library(self, code: str, old_lib: str, new_lib: str) -> Dict[str, Any]:
        """
        Migrate from one library to another.
        
        Args:
            code: Python code to migrate
            old_lib: Old library name
            new_lib: New library name
            
        Returns:
            Dictionary containing migrated code
        """
        from oricli_core.brain.registry import ModuleRegistry
        
        module = ModuleRegistry.get_module("python_migration_assistant")
        if module is None:
            raise ModuleNotFoundError("python_migration_assistant")
        
        return module.execute("migrate_library", {
            "code": code,
            "old_lib": old_lib,
            "new_lib": new_lib,
        })
    
    def migrate_api(self, code: str, old_api: str, new_api: str) -> Dict[str, Any]:
        """
        Migrate from old API to new API.
        
        Args:
            code: Python code to migrate
            old_api: Old API pattern
            new_api: New API pattern
            
        Returns:
            Dictionary containing migrated code
        """
        from oricli_core.brain.registry import ModuleRegistry
        
        module = ModuleRegistry.get_module("python_migration_assistant")
        if module is None:
            raise ModuleNotFoundError("python_migration_assistant")
        
        return module.execute("migrate_api", {
            "code": code,
            "old_api": old_api,
            "new_api": new_api,
        })
    
    def verify_migration(self, original: str, migrated: str) -> Dict[str, Any]:
        """
        Verify that migration maintains correctness.
        
        Args:
            original: Original code
            migrated: Migrated code
            
        Returns:
            Dictionary containing verification results
        """
        from oricli_core.brain.registry import ModuleRegistry
        
        module = ModuleRegistry.get_module("python_migration_assistant")
        if module is None:
            raise ModuleNotFoundError("python_migration_assistant")
        
        return module.execute("verify_migration", {
            "original": original,
            "migrated": migrated,
        })
    
    def generate_migration_script(self, changes: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Generate a migration script from changes.
        
        Args:
            changes: List of changes to apply
            
        Returns:
            Dictionary containing migration script
        """
        from oricli_core.brain.registry import ModuleRegistry
        
        module = ModuleRegistry.get_module("python_migration_assistant")
        if module is None:
            raise ModuleNotFoundError("python_migration_assistant")
        
        return module.execute("generate_migration_script", {
            "changes": changes,
        })
    
    def analyze_security(self, code: str) -> Dict[str, Any]:
        """
        Perform comprehensive security analysis.
        
        Args:
            code: Python code to analyze
            
        Returns:
            Dictionary containing security analysis results
        """
        from oricli_core.brain.registry import ModuleRegistry
        
        module = ModuleRegistry.get_module("python_security_analysis")
        if module is None:
            raise ModuleNotFoundError("python_security_analysis")
        
        return module.execute("analyze_security", {"code": code})
    
    def detect_vulnerabilities(self, code: str) -> Dict[str, Any]:
        """
        Detect security vulnerabilities.
        
        Args:
            code: Python code to analyze
            
        Returns:
            Dictionary containing detected vulnerabilities
        """
        from oricli_core.brain.registry import ModuleRegistry
        
        module = ModuleRegistry.get_module("python_security_analysis")
        if module is None:
            raise ModuleNotFoundError("python_security_analysis")
        
        return module.execute("detect_vulnerabilities", {"code": code})
    
    def check_injection_risks(self, code: str) -> Dict[str, Any]:
        """
        Check for injection attack risks.
        
        Args:
            code: Python code to analyze
            
        Returns:
            Dictionary containing injection risk analysis
        """
        from oricli_core.brain.registry import ModuleRegistry
        
        module = ModuleRegistry.get_module("python_security_analysis")
        if module is None:
            raise ModuleNotFoundError("python_security_analysis")
        
        return module.execute("check_injection_risks", {"code": code})
    
    def analyze_auth_patterns(self, code: str) -> Dict[str, Any]:
        """
        Analyze authentication and authorization patterns.
        
        Args:
            code: Python code to analyze
            
        Returns:
            Dictionary containing auth pattern analysis
        """
        from oricli_core.brain.registry import ModuleRegistry
        
        module = ModuleRegistry.get_module("python_security_analysis")
        if module is None:
            raise ModuleNotFoundError("python_security_analysis")
        
        return module.execute("analyze_auth_patterns", {"code": code})
    
    def detect_secrets(self, code: str) -> Dict[str, Any]:
        """
        Detect secrets and sensitive information in code.
        
        Args:
            code: Python code to analyze
            
        Returns:
            Dictionary containing detected secrets
        """
        from oricli_core.brain.registry import ModuleRegistry
        
        module = ModuleRegistry.get_module("python_security_analysis")
        if module is None:
            raise ModuleNotFoundError("python_security_analysis")
        
        return module.execute("detect_secrets", {"code": code})
    
    def scan_dependencies(self, project: Union[str, Path]) -> Dict[str, Any]:
        """
        Scan project dependencies for known vulnerabilities.
        
        Args:
            project: Project path
            
        Returns:
            Dictionary containing dependency vulnerability scan results
        """
        from oricli_core.brain.registry import ModuleRegistry
        from pathlib import Path
        
        module = ModuleRegistry.get_module("python_security_analysis")
        if module is None:
            raise ModuleNotFoundError("python_security_analysis")
        
        return module.execute("scan_dependencies", {
            "project": str(Path(project)),
        })
    
    def security_review(self, code: str) -> Dict[str, Any]:
        """
        Perform comprehensive security code review.
        
        Args:
            code: Python code to review
            
        Returns:
            Dictionary containing security review results
        """
        from oricli_core.brain.registry import ModuleRegistry
        
        module = ModuleRegistry.get_module("python_security_analysis")
        if module is None:
            raise ModuleNotFoundError("python_security_analysis")
        
        return module.execute("security_review", {"code": code})
    
    def suggest_security_improvements(self, code: str) -> Dict[str, Any]:
        """
        Suggest security improvements.
        
        Args:
            code: Python code to analyze
            
        Returns:
            Dictionary containing security improvement suggestions
        """
        from oricli_core.brain.registry import ModuleRegistry
        
        module = ModuleRegistry.get_module("python_security_analysis")
        if module is None:
            raise ModuleNotFoundError("python_security_analysis")
        
        return module.execute("suggest_security_improvements", {"code": code})
    
    def analyze_runtime_safety(self, code: str) -> Dict[str, Any]:
        """
        Analyze runtime safety of code.
        
        Args:
            code: Python code to analyze
            
        Returns:
            Dictionary containing runtime safety analysis
        """
        from oricli_core.brain.registry import ModuleRegistry
        
        module = ModuleRegistry.get_module("python_code_safety")
        if module is None:
            raise ModuleNotFoundError("python_code_safety")
        
        return module.execute("analyze_runtime_safety", {"code": code})
    
    def detect_resource_leaks(self, code: str) -> Dict[str, Any]:
        """
        Detect resource leaks in code.
        
        Args:
            code: Python code to analyze
            
        Returns:
            Dictionary containing resource leak detection results
        """
        from oricli_core.brain.registry import ModuleRegistry
        
        module = ModuleRegistry.get_module("python_code_safety")
        if module is None:
            raise ModuleNotFoundError("python_code_safety")
        
        return module.execute("detect_resource_leaks", {"code": code})
    
    def analyze_exception_handling(self, code: str) -> Dict[str, Any]:
        """
        Analyze exception handling patterns.
        
        Args:
            code: Python code to analyze
            
        Returns:
            Dictionary containing exception handling analysis
        """
        from oricli_core.brain.registry import ModuleRegistry
        
        module = ModuleRegistry.get_module("python_code_safety")
        if module is None:
            raise ModuleNotFoundError("python_code_safety")
        
        return module.execute("analyze_exception_handling", {"code": code})
    
    def check_thread_safety(self, code: str) -> Dict[str, Any]:
        """
        Check thread safety of code.
        
        Args:
            code: Python code to analyze
            
        Returns:
            Dictionary containing thread safety analysis
        """
        from oricli_core.brain.registry import ModuleRegistry
        
        module = ModuleRegistry.get_module("python_code_safety")
        if module is None:
            raise ModuleNotFoundError("python_code_safety")
        
        return module.execute("check_thread_safety", {"code": code})
    
    def analyze_memory_safety(self, code: str) -> Dict[str, Any]:
        """
        Analyze memory safety of code.
        
        Args:
            code: Python code to analyze
            
        Returns:
            Dictionary containing memory safety analysis
        """
        from oricli_core.brain.registry import ModuleRegistry
        
        module = ModuleRegistry.get_module("python_code_safety")
        if module is None:
            raise ModuleNotFoundError("python_code_safety")
        
        return module.execute("analyze_memory_safety", {"code": code})
    
    def suggest_safe_patterns(self, code: str) -> Dict[str, Any]:
        """
        Suggest safe code patterns.
        
        Args:
            code: Python code to analyze
            
        Returns:
            Dictionary containing safe pattern suggestions
        """
        from oricli_core.brain.registry import ModuleRegistry
        
        module = ModuleRegistry.get_module("python_code_safety")
        if module is None:
            raise ModuleNotFoundError("python_code_safety")
        
        return module.execute("suggest_safe_patterns", {"code": code})
    
    def understand_project(self, project: Union[str, Path]) -> Dict[str, Any]:
        """
        Understand entire project codebase.
        
        Args:
            project: Project path
            
        Returns:
            Dictionary containing comprehensive project understanding
        """
        from oricli_core.brain.registry import ModuleRegistry
        from pathlib import Path
        
        module = ModuleRegistry.get_module("python_project_understanding")
        if module is None:
            raise ModuleNotFoundError("python_project_understanding")
        
        return module.execute("understand_project", {
            "project": str(Path(project)),
        })
    
    def analyze_cross_file_dependencies(self, project: Union[str, Path]) -> Dict[str, Any]:
        """
        Analyze cross-file dependencies.
        
        Args:
            project: Project path
            
        Returns:
            Dictionary containing cross-file dependency analysis
        """
        from oricli_core.brain.registry import ModuleRegistry
        from pathlib import Path
        
        module = ModuleRegistry.get_module("python_project_understanding")
        if module is None:
            raise ModuleNotFoundError("python_project_understanding")
        
        return module.execute("analyze_cross_file_dependencies", {
            "project": str(Path(project)),
        })
    
    def map_project_architecture(self, project: Union[str, Path]) -> Dict[str, Any]:
        """
        Map project architecture.
        
        Args:
            project: Project path
            
        Returns:
            Dictionary containing architecture mapping
        """
        from oricli_core.brain.registry import ModuleRegistry
        from pathlib import Path
        
        module = ModuleRegistry.get_module("python_project_understanding")
        if module is None:
            raise ModuleNotFoundError("python_project_understanding")
        
        return module.execute("map_project_architecture", {
            "project": str(Path(project)),
        })
    
    def analyze_module_relationships(self, project: Union[str, Path]) -> Dict[str, Any]:
        """
        Analyze module relationships.
        
        Args:
            project: Project path
            
        Returns:
            Dictionary containing module relationship analysis
        """
        from oricli_core.brain.registry import ModuleRegistry
        from pathlib import Path
        
        module = ModuleRegistry.get_module("python_project_understanding")
        if module is None:
            raise ModuleNotFoundError("python_project_understanding")
        
        return module.execute("analyze_module_relationships", {
            "project": str(Path(project)),
        })
    
    def build_import_graph(self, project: Union[str, Path]) -> Dict[str, Any]:
        """
        Build import dependency graph.
        
        Args:
            project: Project path
            
        Returns:
            Dictionary containing import dependency graph
        """
        from oricli_core.brain.registry import ModuleRegistry
        from pathlib import Path
        
        module = ModuleRegistry.get_module("python_project_understanding")
        if module is None:
            raise ModuleNotFoundError("python_project_understanding")
        
        return module.execute("build_import_graph", {
            "project": str(Path(project)),
        })
    
    def recognize_project_patterns(self, project: Union[str, Path]) -> Dict[str, Any]:
        """
        Recognize project-wide patterns.
        
        Args:
            project: Project path
            
        Returns:
            Dictionary containing recognized patterns
        """
        from oricli_core.brain.registry import ModuleRegistry
        from pathlib import Path
        
        module = ModuleRegistry.get_module("python_project_understanding")
        if module is None:
            raise ModuleNotFoundError("python_project_understanding")
        
        return module.execute("recognize_project_patterns", {
            "project": str(Path(project)),
        })
    
    def analyze_codebase_health(self, project: Union[str, Path]) -> Dict[str, Any]:
        """
        Analyze codebase health.
        
        Args:
            project: Project path
            
        Returns:
            Dictionary containing codebase health analysis
        """
        from oricli_core.brain.registry import ModuleRegistry
        from pathlib import Path
        
        module = ModuleRegistry.get_module("python_project_understanding")
        if module is None:
            raise ModuleNotFoundError("python_project_understanding")
        
        return module.execute("analyze_codebase_health", {
            "project": str(Path(project)),
        })
    
    def suggest_structure_improvements(self, project: Union[str, Path]) -> Dict[str, Any]:
        """
        Suggest project structure improvements.
        
        Args:
            project: Project path
            
        Returns:
            Dictionary containing structure improvement suggestions
        """
        from oricli_core.brain.registry import ModuleRegistry
        from pathlib import Path
        
        module = ModuleRegistry.get_module("python_project_understanding")
        if module is None:
            raise ModuleNotFoundError("python_project_understanding")
        
        return module.execute("suggest_structure_improvements", {
            "project": str(Path(project)),
        })
    
    def search_codebase(self, project: Union[str, Path], query: str, search_type: str = "semantic") -> Dict[str, Any]:
        """
        Search codebase with semantic or text search.
        
        Args:
            project: Project path
            query: Search query
            search_type: Type of search ("semantic", "text", "regex")
            
        Returns:
            Dictionary containing search results
        """
        from oricli_core.brain.registry import ModuleRegistry
        from pathlib import Path
        
        module = ModuleRegistry.get_module("python_codebase_search")
        if module is None:
            raise ModuleNotFoundError("python_codebase_search")
        
        return module.execute("search_codebase", {
            "project": str(Path(project)),
            "query": query,
            "search_type": search_type,
        })
    
    def find_usages(self, project: Union[str, Path], symbol: str) -> Dict[str, Any]:
        """
        Find all usages of a symbol across codebase.
        
        Args:
            project: Project path
            symbol: Symbol name (function, class, variable)
            
        Returns:
            Dictionary containing usage locations
        """
        from oricli_core.brain.registry import ModuleRegistry
        from pathlib import Path
        
        module = ModuleRegistry.get_module("python_codebase_search")
        if module is None:
            raise ModuleNotFoundError("python_codebase_search")
        
        return module.execute("find_usages", {
            "project": str(Path(project)),
            "symbol": symbol,
        })
    
    def navigate_relationships(self, project: Union[str, Path], symbol: str) -> Dict[str, Any]:
        """
        Navigate code relationships for a symbol.
        
        Args:
            project: Project path
            symbol: Symbol name
            
        Returns:
            Dictionary containing relationships
        """
        from oricli_core.brain.registry import ModuleRegistry
        from pathlib import Path
        
        module = ModuleRegistry.get_module("python_codebase_search")
        if module is None:
            raise ModuleNotFoundError("python_codebase_search")
        
        return module.execute("navigate_relationships", {
            "project": str(Path(project)),
            "symbol": symbol,
        })
    
    def find_similar_implementations(self, project: Union[str, Path], code: str) -> Dict[str, Any]:
        """
        Find similar code implementations.
        
        Args:
            project: Project path
            code: Code snippet to find similar implementations for
            
        Returns:
            Dictionary containing similar implementations
        """
        from oricli_core.brain.registry import ModuleRegistry
        from pathlib import Path
        
        module = ModuleRegistry.get_module("python_codebase_search")
        if module is None:
            raise ModuleNotFoundError("python_codebase_search")
        
        return module.execute("find_similar_implementations", {
            "project": str(Path(project)),
            "code": code,
        })
    
    def search_by_behavior(self, project: Union[str, Path], behavior_description: str) -> Dict[str, Any]:
        """
        Search codebase by behavior description.
        
        Args:
            project: Project path
            behavior_description: Description of desired behavior
            
        Returns:
            Dictionary containing matching code
        """
        from oricli_core.brain.registry import ModuleRegistry
        from pathlib import Path
        
        module = ModuleRegistry.get_module("python_codebase_search")
        if module is None:
            raise ModuleNotFoundError("python_codebase_search")
        
        return module.execute("search_by_behavior", {
            "project": str(Path(project)),
            "behavior_description": behavior_description,
        })
    
    def explore_codebase(self, project: Union[str, Path], starting_point: Optional[str] = None) -> Dict[str, Any]:
        """
        Explore codebase from a starting point.
        
        Args:
            project: Project path
            starting_point: Starting file or symbol (optional)
            
        Returns:
            Dictionary containing exploration results
        """
        from oricli_core.brain.registry import ModuleRegistry
        from pathlib import Path
        
        module = ModuleRegistry.get_module("python_codebase_search")
        if module is None:
            raise ModuleNotFoundError("python_codebase_search")
        
        return module.execute("explore_codebase", {
            "project": str(Path(project)),
            "starting_point": starting_point,
        })
    
    def analyze_impact(self, project: Union[str, Path], change: Dict[str, Any]) -> Dict[str, Any]:
        """
        Analyze impact of a proposed change.
        
        Args:
            project: Project path
            change: Change description (file, symbol, type)
            
        Returns:
            Dictionary containing impact analysis
        """
        from oricli_core.brain.registry import ModuleRegistry
        from pathlib import Path
        
        module = ModuleRegistry.get_module("python_codebase_search")
        if module is None:
            raise ModuleNotFoundError("python_codebase_search")
        
        return module.execute("analyze_impact", {
            "project": str(Path(project)),
            "change": change,
        })
    
    def learn_from_correction(self, original: str, corrected: str, context: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        Learn from user correction.
        
        Args:
            original: Original code
            corrected: Corrected code
            context: Additional context (project, file, etc.)
            
        Returns:
            Dictionary containing learning results
        """
        from oricli_core.brain.registry import ModuleRegistry
        
        module = ModuleRegistry.get_module("python_learning_system")
        if module is None:
            raise ModuleNotFoundError("python_learning_system")
        
        return module.execute("learn_from_correction", {
            "original": original,
            "corrected": corrected,
            "context": context or {},
        })
    
    def adapt_to_project(self, project: Union[str, Path], examples: List[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Adapt to project-specific patterns.
        
        Args:
            project: Project path
            examples: Example code patterns from project
            
        Returns:
            Dictionary containing adaptation results
        """
        from oricli_core.brain.registry import ModuleRegistry
        from pathlib import Path
        
        module = ModuleRegistry.get_module("python_learning_system")
        if module is None:
            raise ModuleNotFoundError("python_learning_system")
        
        return module.execute("adapt_to_project", {
            "project": str(Path(project)),
            "examples": examples or [],
        })
    
    def learn_style_preferences(self, user: str, examples: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Learn coding style preferences from examples.
        
        Args:
            user: User identifier
            examples: List of code examples with style preferences
            
        Returns:
            Dictionary containing learned preferences
        """
        from oricli_core.brain.registry import ModuleRegistry
        
        module = ModuleRegistry.get_module("python_learning_system")
        if module is None:
            raise ModuleNotFoundError("python_learning_system")
        
        return module.execute("learn_style_preferences", {
            "user": user,
            "examples": examples,
        })
    
    def improve_suggestions(self, feedback: Dict[str, Any]) -> Dict[str, Any]:
        """
        Improve suggestions based on feedback.
        
        Args:
            feedback: Feedback on previous suggestions
            
        Returns:
            Dictionary containing improvement results
        """
        from oricli_core.brain.registry import ModuleRegistry
        
        module = ModuleRegistry.get_module("python_learning_system")
        if module is None:
            raise ModuleNotFoundError("python_learning_system")
        
        return module.execute("improve_suggestions", {"feedback": feedback})
    
    def learn_from_review(self, code: str, review_feedback: Dict[str, Any]) -> Dict[str, Any]:
        """
        Learn from code review feedback.
        
        Args:
            code: Code that was reviewed
            review_feedback: Review feedback and suggestions
            
        Returns:
            Dictionary containing learning results
        """
        from oricli_core.brain.registry import ModuleRegistry
        
        module = ModuleRegistry.get_module("python_learning_system")
        if module is None:
            raise ModuleNotFoundError("python_learning_system")
        
        return module.execute("learn_from_review", {
            "code": code,
            "review_feedback": review_feedback,
        })
    
    def adapt_to_team(self, team_codebase: Union[str, Path]) -> Dict[str, Any]:
        """
        Adapt to team coding conventions.
        
        Args:
            team_codebase: Team codebase path
            
        Returns:
            Dictionary containing adaptation results
        """
        from oricli_core.brain.registry import ModuleRegistry
        from pathlib import Path
        
        module = ModuleRegistry.get_module("python_learning_system")
        if module is None:
            raise ModuleNotFoundError("python_learning_system")
        
        return module.execute("adapt_to_team", {
            "team_codebase": str(Path(team_codebase)),
        })
    
    def personalize_generation(self, user_preferences: Dict[str, Any]) -> Dict[str, Any]:
        """
        Personalize code generation based on user preferences.
        
        Args:
            user_preferences: User preferences for code generation
            
        Returns:
            Dictionary containing personalization results
        """
        from oricli_core.brain.registry import ModuleRegistry
        
        module = ModuleRegistry.get_module("python_learning_system")
        if module is None:
            raise ModuleNotFoundError("python_learning_system")
        
        return module.execute("personalize_generation", {"user_preferences": user_preferences})
    
    def detect_style(self, codebase: Union[str, Path]) -> Dict[str, Any]:
        """
        Detect coding style of codebase.
        
        Args:
            codebase: Codebase path
            
        Returns:
            Dictionary containing detected style
        """
        from oricli_core.brain.registry import ModuleRegistry
        from pathlib import Path
        
        module = ModuleRegistry.get_module("python_style_adaptation")
        if module is None:
            raise ModuleNotFoundError("python_style_adaptation")
        
        return module.execute("detect_style", {
            "codebase": str(Path(codebase)),
        })
    
    def adapt_to_style(self, code: str, target_style: Dict[str, Any]) -> Dict[str, Any]:
        """
        Adapt code to target style.
        
        Args:
            code: Code to adapt
            target_style: Target style specification
            
        Returns:
            Dictionary containing adapted code
        """
        from oricli_core.brain.registry import ModuleRegistry
        
        module = ModuleRegistry.get_module("python_style_adaptation")
        if module is None:
            raise ModuleNotFoundError("python_style_adaptation")
        
        return module.execute("adapt_to_style", {
            "code": code,
            "target_style": target_style,
        })
    
    def enforce_consistency(self, codebase: Union[str, Path]) -> Dict[str, Any]:
        """
        Enforce style consistency across codebase.
        
        Args:
            codebase: Codebase path
            
        Returns:
            Dictionary containing consistency enforcement results
        """
        from oricli_core.brain.registry import ModuleRegistry
        from pathlib import Path
        
        module = ModuleRegistry.get_module("python_style_adaptation")
        if module is None:
            raise ModuleNotFoundError("python_style_adaptation")
        
        return module.execute("enforce_consistency", {
            "codebase": str(Path(codebase)),
        })
    
    def learn_style(self, examples: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Learn style from examples.
        
        Args:
            examples: List of code examples with style annotations
            
        Returns:
            Dictionary containing learned style
        """
        from oricli_core.brain.registry import ModuleRegistry
        
        module = ModuleRegistry.get_module("python_style_adaptation")
        if module is None:
            raise ModuleNotFoundError("python_style_adaptation")
        
        return module.execute("learn_style", {"examples": examples})
    
    def transform_style(self, code: str, from_style: Dict[str, Any], to_style: Dict[str, Any]) -> Dict[str, Any]:
        """
        Transform code from one style to another.
        
        Args:
            code: Code to transform
            from_style: Source style
            to_style: Target style
            
        Returns:
            Dictionary containing transformed code
        """
        from oricli_core.brain.registry import ModuleRegistry
        
        module = ModuleRegistry.get_module("python_style_adaptation")
        if module is None:
            raise ModuleNotFoundError("python_style_adaptation")
        
        return module.execute("transform_style", {
            "code": code,
            "from_style": from_style,
            "to_style": to_style,
        })
    
    def migrate_style(self, codebase: Union[str, Path], new_style: Dict[str, Any]) -> Dict[str, Any]:
        """
        Migrate codebase to new style.
        
        Args:
            codebase: Codebase path
            new_style: New style specification
            
        Returns:
            Dictionary containing migration results
        """
        from oricli_core.brain.registry import ModuleRegistry
        from pathlib import Path
        
        module = ModuleRegistry.get_module("python_style_adaptation")
        if module is None:
            raise ModuleNotFoundError("python_style_adaptation")
        
        return module.execute("migrate_style", {
            "codebase": str(Path(codebase)),
            "new_style": new_style,
        })


class Goals:
    """Sovereign Goal management API"""
    
    def __init__(self, client: "OricliAlphaClient"):
        self._client = client
        if not self._client.base_url:
            from oricli_core.services.goal_service import GoalService
            self._service = GoalService()
    
    def create(self, goal: str, priority: int = 1, metadata: Optional[Dict[str, Any]] = None) -> str:
        """Create a new sovereign goal"""
        if self._client.base_url:
            res = self._client._make_remote_request("POST", "/v1/goals", {
                "goal": goal,
                "priority": priority,
                "metadata": metadata
            })
            return res.get("id")
        return self._service.add_objective(goal, priority, metadata)
    
    def list(self, status: Optional[str] = None) -> List[Dict[str, Any]]:
        """List sovereign goals"""
        if self._client.base_url:
            res = self._client._make_remote_request("GET", "/v1/goals", params={"status": status})
            return res.get("goals", [])
        return self._service.list_objectives(status)
    
    def get_status(self, goal_id: str) -> Dict[str, Any]:
        """Get detailed status of a sovereign goal"""
        if self._client.base_url:
            return self._client._make_remote_request("GET", f"/v1/goals/{goal_id}")
            
        objectives = self._service.list_objectives()
        goal = next((obj for obj in objectives if obj["id"] == goal_id), None)
        if not goal:
            raise ClientError(f"Goal {goal_id} not found")
        
        return {
            "goal": goal,
            "plan_state": self._service.load_plan_state(goal_id)
        }


class Swarm:
    """Hive Swarm deliberation API"""
    
    def __init__(self, client: "OricliAlphaClient"):
        self._client = client
        if not self._client.base_url:
            from oricli_core.services.swarm_blackboard_service import get_swarm_blackboard_service
            self._blackboard = get_swarm_blackboard_service()
    
    def run(self, query: str, max_rounds: int = 3, participants: Optional[List[str]] = None, consensus_policy: str = "weighted_vote") -> Dict[str, Any]:
        """Trigger a collaborative swarm session"""
        if self._client.base_url:
            return self._client._make_remote_request("POST", "/v1/swarm/run", {
                "query": query,
                "max_rounds": max_rounds,
                "participants": participants,
                "consensus_policy": consensus_policy
            })
            
        swarm_coordinator = ModuleRegistry.get_module("swarm_coordinator")
        if not swarm_coordinator:
            raise ModuleNotFoundError("swarm_coordinator")
        
        result = swarm_coordinator.execute("coordinate_task", {
            "query": query,
            "round_limit": max_rounds,
            "participants": participants,
            "consensus_policy": consensus_policy
        })
        
        if not result.get("success"):
            raise ModuleOperationError("swarm_coordinator", "coordinate_task", result.get("error", "Unknown error"))
            
        return result

    def get_session(self, session_id: str) -> Dict[str, Any]:
        """Get detailed swarm session state"""
        if self._client.base_url:
            return self._client._make_remote_request("GET", f"/v1/swarm/sessions/{session_id}")
            
        session = self._blackboard.load_session(session_id)
        if not session:
            raise ClientError(f"Swarm session {session_id} not found")
        return session


class Knowledge:
    """Knowledge Graph API"""
    
    def __init__(self, client: "OricliAlphaClient"):
        self._client = client
    
    def extract(self, text: str, domain: Optional[str] = None) -> Dict[str, Any]:
        """Extract entities and relationships from text"""
        if self._client.base_url:
            return self._client._make_remote_request("POST", "/v1/knowledge/extract", {
                "text": text,
                "domain": domain
            })
            
        module = ModuleRegistry.get_module("knowledge_graph_builder")
        if not module:
            raise ModuleNotFoundError("knowledge_graph_builder")
        return module.execute("build_from_text", {"text": text, "domain": domain})
    
    def query(self, entity_id: Optional[str] = None, query_string: Optional[str] = None, depth: int = 1) -> Dict[str, Any]:
        """Query the knowledge graph"""
        if self._client.base_url:
            return self._client._make_remote_request("POST", "/v1/knowledge/query", {
                "entity_id": entity_id,
                "query_string": query_string,
                "depth": depth
            })
            
        module = ModuleRegistry.get_module("knowledge_graph_builder")
        if not module:
            raise ModuleNotFoundError("knowledge_graph_builder")
            
        if entity_id:
            return module.execute("query_graph", {"entity_id": entity_id, "depth": depth})
        raise InvalidParameterError("entity_id", str(entity_id), "entity_id is required for query")

    def ingest(self, text: Optional[str] = None, file_path: Optional[str] = None, metadata: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Ingest text or file content into the Knowledge Graph"""
        if self._client.base_url:
            # Handle remote ingestion (Multipart if file, otherwise JSON)
            import json
            if file_path:
                p = Path(file_path)
                with open(p, "rb") as f:
                    files = {"file": (p.name, f, "application/octet-stream")}
                    data = {
                        "source": metadata.get("source", p.name) if metadata else p.name,
                        "tags": json.dumps(metadata.get("tags", [])) if metadata else "[]",
                        "domain": metadata.get("domain", "") if metadata else ""
                    }
                    # We need a manual multipart request here since _make_remote_request handles JSON
                    headers = {}
                    if self._client.api_key:
                        headers["Authorization"] = f"Bearer {self._client.api_key}"
                    
                    response = httpx.post(
                        f"{self._client.base_url}/v1/ingest",
                        data=data,
                        files=files,
                        headers=headers,
                        timeout=300.0
                    )
                    response.raise_for_status()
                    return response.json()
            else:
                data = {
                    "text": text,
                    "source": metadata.get("source", "direct") if metadata else "direct",
                    "tags": json.dumps(metadata.get("tags", [])) if metadata else "[]",
                    "domain": metadata.get("domain", "") if metadata else ""
                }
                headers = {}
                if self._client.api_key:
                    headers["Authorization"] = f"Bearer {self._client.api_key}"
                
                response = httpx.post(
                    f"{self._client.base_url}/v1/ingest",
                    data=data,
                    headers=headers,
                    timeout=300.0
                )
                response.raise_for_status()
                return response.json()

        # Local mode
        module = ModuleRegistry.get_module("ingestion_agent")
        if not module:
            raise ModuleNotFoundError("ingestion_agent")
            
        if file_path:
            p = Path(file_path)
            return module.execute("ingest_file", {
                "file_data": p.read_bytes(),
                "file_name": p.name,
                "metadata": metadata or {}
            })
        else:
            return module.execute("ingest_text", {
                "text": text,
                "metadata": metadata or {}
            })

    def ingest_web(self, url: str, max_pages: int = 5, max_depth: int = 2, metadata: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Crawl and ingest a website into the Knowledge Graph"""
        if self._client.base_url:
            return self._client._make_remote_request("POST", "/v1/ingest/web", {
                "url": url,
                "max_pages": max_pages,
                "max_depth": max_depth,
                "metadata": metadata or {}
            })

        # Local mode
        module = ModuleRegistry.get_module("web_ingestion_agent")
        if not module:
            raise ModuleNotFoundError("web_ingestion_agent")
            
        return module.execute("crawl_and_ingest", {
            "url": url,
            "max_pages": max_pages,
            "max_depth": max_depth,
            "metadata": metadata or {}
        })


class Skills:
    """External Skills API"""
    
    def __init__(self, client: "OricliAlphaClient"):
        self._client = client
    
    def list(self) -> List[Dict[str, Any]]:
        """List all loaded skills"""
        if self._client.base_url:
            res = self._client._make_remote_request("GET", "/v1/skills")
            return res.get("skills", [])
            
        module = ModuleRegistry.get_module("skill_manager")
        if not module:
            raise ModuleNotFoundError("skill_manager")
        res = module.execute("list_skills", {})
        return res.get("skills", [])
        
    def get(self, skill_name: str) -> Dict[str, Any]:
        """Get details of a specific skill"""
        if self._client.base_url:
            return self._client._make_remote_request("GET", f"/v1/skills/{skill_name}")
            
        module = ModuleRegistry.get_module("skill_manager")
        if not module:
            raise ModuleNotFoundError("skill_manager")
        res = module.execute("get_skill", {"skill_name": skill_name})
        if not res.get("success"):
            raise ClientError(res.get("error"))
        return res.get("skill", {})
        
    def create(self, skill_data: Dict[str, Any]) -> Dict[str, Any]:
        """Create a new skill"""
        if self._client.base_url:
            return self._client._make_remote_request("POST", "/v1/skills", skill_data)
            
        module = ModuleRegistry.get_module("skill_manager")
        if not module:
            raise ModuleNotFoundError("skill_manager")
        res = module.execute("create_skill", skill_data)
        if not res.get("success"):
            raise ClientError(res.get("error"))
        return res.get("skill", {})
        
    def update(self, skill_name: str, skill_data: Dict[str, Any]) -> Dict[str, Any]:
        """Update an existing skill"""
        payload = {"skill_name": skill_name, **skill_data}
        if self._client.base_url:
            return self._client._make_remote_request("PUT", f"/v1/skills/{skill_name}", payload)
            
        module = ModuleRegistry.get_module("skill_manager")
        if not module:
            raise ModuleNotFoundError("skill_manager")
        res = module.execute("update_skill", payload)
        if not res.get("success"):
            raise ClientError(res.get("error"))
        return res.get("skill", {})
        
    def delete(self, skill_name: str) -> bool:
        """Delete a skill"""
        if self._client.base_url:
            res = self._client._make_remote_request("DELETE", f"/v1/skills/{skill_name}")
            return res.get("success", False)
            
        module = ModuleRegistry.get_module("skill_manager")
        if not module:
            raise ModuleNotFoundError("skill_manager")
        res = module.execute("delete_skill", {"skill_name": skill_name})
        if not res.get("success"):
            raise ClientError(res.get("error"))
        return res.get("success", False)


class Rules:
    """External Rules API"""
    
    def __init__(self, client: "OricliAlphaClient"):
        self._client = client
    
    def list(self) -> List[Dict[str, Any]]:
        """List all loaded rules"""
        if self._client.base_url:
            res = self._client._make_remote_request("GET", "/v1/rules")
            return res.get("rules", [])
            
        from oricli_core.rules.engine import get_rules_engine
        engine = get_rules_engine()
        return engine.get_all_rules()
        
    def get(self, rule_name: str) -> Dict[str, Any]:
        """Get details of a specific rule"""
        if self._client.base_url:
            return self._client._make_remote_request("GET", f"/v1/rules/{rule_name}")
            
        from oricli_core.rules.engine import get_rules_engine
        engine = get_rules_engine()
        rule = engine.get_rule_by_name(rule_name)
        if not rule:
            raise ClientError(f"Rule '{rule_name}' not found")
        return rule
        
    def create(self, rule_data: Dict[str, Any]) -> Dict[str, Any]:
        """Create a new rule"""
        if self._client.base_url:
            return self._client._make_remote_request("POST", "/v1/rules", rule_data)
            
        from oricli_core.rules.engine import get_rules_engine
        engine = get_rules_engine()
        try:
            return engine.create_rule(rule_data)
        except Exception as e:
            raise ClientError(str(e))
        
    def update(self, rule_name: str, rule_data: Dict[str, Any]) -> Dict[str, Any]:
        """Update an existing rule"""
        payload = {"name": rule_name, **rule_data}
        if self._client.base_url:
            return self._client._make_remote_request("PUT", f"/v1/rules/{rule_name}", payload)
            
        from oricli_core.rules.engine import get_rules_engine
        engine = get_rules_engine()
        try:
            return engine.update_rule(rule_name, payload)
        except Exception as e:
            raise ClientError(str(e))
        
    def delete(self, rule_name: str) -> bool:
        """Delete a rule"""
        if self._client.base_url:
            res = self._client._make_remote_request("DELETE", f"/v1/rules/{rule_name}")
            return res.get("success", False)
            
        from oricli_core.rules.engine import get_rules_engine
        engine = get_rules_engine()
        if not engine.delete_rule(rule_name):
            raise ClientError(f"Rule '{rule_name}' not found or could not be deleted")
        return True


class Agents:
    """External Agents API (Agent Factory)"""
    
    def __init__(self, client: "OricliAlphaClient"):
        self._client = client
    
    def list(self) -> List[Dict[str, Any]]:
        """List all loaded agent profiles"""
        if self._client.base_url:
            res = self._client._make_remote_request("GET", "/v1/agents")
            return res.get("agents", [])
            
        from oricli_core.services.agent_profile_service import get_agent_profile_service
        service = get_agent_profile_service()
        return service.list_profiles()
        
    def get(self, agent_name: str) -> Dict[str, Any]:
        """Get details of a specific agent profile"""
        if self._client.base_url:
            return self._client._make_remote_request("GET", f"/v1/agents/{agent_name}")
            
        from oricli_core.services.agent_profile_service import get_agent_profile_service
        service = get_agent_profile_service()
        profile = service.get_profile(agent_name)
        if not profile:
            raise ClientError(f"Agent profile '{agent_name}' not found")
        return profile.to_dict()
        
    def create(self, agent_data: Dict[str, Any]) -> Dict[str, Any]:
        """Create a new agent profile"""
        if self._client.base_url:
            return self._client._make_remote_request("POST", "/v1/agents", agent_data)
            
        from oricli_core.services.agent_profile_service import get_agent_profile_service
        service = get_agent_profile_service()
        try:
            return service.create_profile(agent_data)
        except Exception as e:
            raise ClientError(str(e))
        
    def update(self, agent_name: str, agent_data: Dict[str, Any]) -> Dict[str, Any]:
        """Update an existing agent profile"""
        payload = {"name": agent_name, **agent_data}
        if self._client.base_url:
            return self._client._make_remote_request("PUT", f"/v1/agents/{agent_name}", payload)
            
        from oricli_core.services.agent_profile_service import get_agent_profile_service
        service = get_agent_profile_service()
        try:
            return service.update_profile(agent_name, payload)
        except Exception as e:
            raise ClientError(str(e))
        
    def delete(self, agent_name: str) -> bool:
        """Delete an agent profile"""
        if self._client.base_url:
            res = self._client._make_remote_request("DELETE", f"/v1/agents/{agent_name}")
            return res.get("success", False)
            
        from oricli_core.services.agent_profile_service import get_agent_profile_service
        service = get_agent_profile_service()
        if not service.delete_profile(agent_name):
            raise ClientError(f"Agent profile '{agent_name}' not found or could not be deleted")
        return True


class AgentProfiles:
    """Client namespace for agent profile discovery and resolution."""

    def __init__(self, service: AgentProfileService):
        self._service = service

    def list(self) -> List[Dict[str, Any]]:
        return self._service.list_profiles()

    def get(self, name: str) -> Dict[str, Any]:
        profile = self._service.get_profile(name)
        if profile is None:
            raise InvalidParameterError("agent_profile", name, "Profile not found")
        return profile.to_dict()

    def resolve(
        self,
        *,
        profile_name: Optional[str] = None,
        task_type: Optional[str] = None,
        agent_type: Optional[str] = None,
    ) -> Optional[Dict[str, Any]]:
        profile = self._service.resolve_profile(
            profile_name=profile_name,
            task_type=task_type,
            agent_type=agent_type,
        )
        return profile.to_dict() if profile else None

class Chat:
    """Chat API namespace"""
    
    def __init__(self, client: "OricliAlphaClient"):
        self.completions = ChatCompletions(client)


class OricliAlphaClient:
    """
    OricliAlpha Core Client - Main interface for all OricliAlpha capabilities
    
    Provides:
    - OpenAI-compatible API (chat.completions, embeddings)
    - Direct brain module access via `client.brain.module_name.operation()`
    - Unified interface for all capabilities
    
    Example:
        ```python
        from oricli_core import OricliAlphaClient
        
        client = OricliAlphaClient()
        
        # Chat completion
        response = client.chat.completions.create(
            model="oricli-cognitive",
            messages=[{"role": "user", "content": "Hello"}]
        )
        
        # Direct module access
        result = client.brain.reasoning.reason(query="What is 2+2?")
        ```
    """
    
    def __init__(
        self,
        modules_dir: Optional[Union[str, Path]] = None,
        base_url: Optional[str] = None,
        api_key: Optional[str] = None,
    ) -> None:
        """
        Initialize OricliAlpha client
        
        Args:
            modules_dir: Optional path to brain_modules directory.
                        If not provided, uses default module discovery.
            base_url: Optional base URL for remote API calls.
            api_key: Optional API key for remote authentication.
        
        Note:
            Module discovery is deferred until first use to avoid blocking startup.
        """
        import sys
        try:
            print("[DEBUG] OricliAlphaClient.__init__ called", file=sys.stderr)
            sys.stderr.flush()
            
            self.base_url = base_url.rstrip("/") if base_url else None
            self.api_key = api_key
            self._http_client = httpx.Client(timeout=300.0) if self.base_url else None
            
            if modules_dir is not None:
                ModuleRegistry.set_modules_dir(Path(modules_dir))
            
            # Defer module discovery until first use to avoid blocking startup
            # Modules will be discovered automatically when first accessed
            
            # Initialize API namespaces
            self.chat = Chat(self)
            self.embeddings = Embeddings(self)
            self.brain = BrainModuleProxy(self)
            self.python = PythonLLM(self)
            self.agent_profiles = AgentProfiles(AgentProfileService())
            self.goals = Goals(self)
            self.swarm = Swarm(self)
            self.knowledge = Knowledge(self)
            self.skills = Skills(self)
            self.rules = Rules(self)
            self.agents = Agents(self)
            
            print("[DEBUG] OricliAlphaClient initialized successfully", file=sys.stderr)
            sys.stderr.flush()
        except Exception as e:
            print(f"[ERROR] OricliAlphaClient initialization failed: {e}", file=sys.stderr)
            import traceback
            traceback.print_exc(file=sys.stderr)
            sys.stderr.flush()
            raise
            
    def _make_remote_request(
        self, 
        method: str, 
        path: str, 
        data: Optional[Dict[str, Any]] = None,
        params: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Make a request to the remote Oricli API"""
        if not self._http_client or not self.base_url:
            raise ClientError("Client is not configured for remote calls (base_url missing)")
            
        headers = {}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"
            
        url = f"{self.base_url}{path}"
        try:
            response = self._http_client.request(
                method=method,
                url=url,
                json=data,
                params=params,
                headers=headers
            )
            response.raise_for_status()
            return response.json()
        except httpx.HTTPStatusError as e:
            error_detail = ""
            try:
                error_detail = e.response.json().get("detail", str(e))
            except Exception:
                error_detail = str(e)
            raise ClientError(f"Remote API error: {error_detail}")
        except Exception as e:
            raise ClientError(f"Connection error: {str(e)}")

    def _process_rfal_async(self, **kwargs: Any) -> None:
        """Trigger RFAL processing in a background thread."""
        def run():
            try:
                from oricli_core.brain.registry import ModuleRegistry
                rfal = ModuleRegistry.get_module("rfal_engine")
                if rfal:
                    rfal.execute("process_feedback", kwargs)
            except Exception:
                # Silently fail in background to avoid disrupting main flow
                pass

        thread = threading.Thread(target=run, daemon=True)
        thread.start()
    
    def _expand_tool_references(self, tools: Optional[List[ToolDefinition]]) -> Optional[List[Dict[str, Any]]]:
        """
        Expand tool_reference blocks to full tool definitions.
        
        Args:
            tools: List of tool definitions that may contain tool_reference blocks
        
        Returns:
            List of expanded tool definitions as dictionaries
        """
        if not tools:
            return None
        
        tool_registry = ToolRegistry()
        expanded_tools = []
        
        for tool in tools:
            # Check if this is a tool_reference (dict with type="tool_reference")
            if isinstance(tool, dict) and tool.get("type") == "tool_reference":
                tool_name = tool.get("name")
                if tool_name:
                    # Get full tool definition from registry
                    tool_def = tool_registry.get_tool(tool_name)
                    if tool_def:
                        expanded_tools.append(tool_def.to_dict())
            elif isinstance(tool, ToolDefinition):
                # Convert ToolDefinition to dict
                expanded_tools.append(tool.dict())
            elif isinstance(tool, dict):
                # Already a dict, use as-is
                expanded_tools.append(tool)
        
        return expanded_tools if expanded_tools else None
    
    def _generate_chat_completion(
        self, request: ChatCompletionRequest
    ) -> ChatCompletionResponse:
        """
        Internal method to generate chat completion
        """
        if self.base_url:
            res = self._make_remote_request("POST", "/v1/chat/completions", request.dict())
            return ChatCompletionResponse(**res)

        # Get cognitive generator module with fallback support
        from oricli_core.brain.registry import ModuleRegistry
        # Use get_module_or_fallback to handle degraded modules
        module_result = ModuleRegistry.get_module_or_fallback(
            "cognitive_generator",
            operation="generate_response"
        )
        cognitive_module, actual_module_name, is_fallback, mapped_operation = module_result
        
        # Ensure operation_to_use is always defined
        operation_to_use = mapped_operation if mapped_operation else "generate_response"
        
        if cognitive_module is None:
            raise ModuleNotFoundError("cognitive_generator")
        
        # Expand tool references if present
        expanded_tools = None
        if request.tools:
            expanded_tools = self._expand_tool_references(request.tools)
        
        # Extract URLs from messages and fetch URL context
        url_context_metadata = []
        url_context_content = []
        
        try:
            url_context_module = ModuleRegistry.get_module("url_context")
            if url_context_module:
                # Collect all message text
                all_message_text = " ".join([
                    msg.get_text_content() for msg in request.messages
                ])
                
                # Extract and fetch URL context
                url_result = url_context_module.execute("get_url_context", {
                    "text": all_message_text,
                    "use_cache": True,
                    "max_urls": 20,
                })
                
                if url_result.get("success"):
                    url_context_metadata_raw = url_result.get("url_context_metadata", [])
                    url_results = url_result.get("results", [])
                    
                    # Convert metadata to URLContextMetadata objects
                    for meta in url_context_metadata_raw:
                        url_context_metadata.append(URLContextMetadata(**meta))
                    
                    # Collect URL content for context
                    for url_result_item in url_results:
                        if url_result_item.get("content"):
                            url_context_content.append({
                                "url": url_result_item.get("url"),
                                "content": url_result_item.get("content"),
                                "content_type": url_result_item.get("content_type"),
                            })
        except Exception:
            # Silently fail if URL context extraction fails
            # Don't block chat completion if URL context fails
            pass
        
        # Prepare parameters for cognitive generator
        # Extract text content (handles both string and multimodal formats)
        messages_payload = [
            {"role": msg.role, "content": msg.get_text_content()}
            for msg in request.messages
        ]
        
        # Trigger RFAL background analysis if we have history (User correcting Assistant)
        if len(messages_payload) >= 3:
            last_msg = messages_payload[-1]
            prev_msg = messages_payload[-2]
            prompt_msg = messages_payload[-3]
            
            if last_msg["role"] == "user" and prev_msg["role"] == "assistant":
                self._process_rfal_async(
                    user_input=last_msg["content"],
                    last_response=prev_msg["content"],
                    prompt=prompt_msg["content"],
                    history=messages_payload[:-1]
                )
        
        # Build context including URL content
        context_parts = []
        if url_context_content:
            context_parts.append("URL Context:")
            for url_item in url_context_content:
                context_parts.append(f"\nURL: {url_item['url']}")
                context_parts.append(f"Content: {url_item['content'][:1000]}...")  # Limit context size
        
        url_context_text = "\n".join(context_parts) if context_parts else ""
        
        # Call cognitive generator
        params = {
            "messages": messages_payload,
            "temperature": request.temperature,
            "max_tokens": request.max_tokens,
            "personality": request.personality_id,
            "persona": request.personality_id,
            "use_memory": request.use_memory,
            "use_reasoning": request.use_reasoning,
        }
        
        # Add URL context to context parameter if available
        if url_context_text:
            params["context"] = url_context_text
        
        # Add tools if present
        if expanded_tools:
            params["tools"] = expanded_tools

        use_swarm = request.model in ["oricli-swarm", "oricli-hive", "strategic_orchestrator"]
        
        # If model name doesn't match standard prefixes, it might be a custom agent name
        profile_name = None
        if not use_swarm and request.model not in ["oricli-cognitive", "oricli-embeddings"]:
            # Check if it's a known agent profile
            from oricli_core.services.agent_profile_service import get_agent_profile_service
            service = get_agent_profile_service()
            if service.get_profile(request.model):
                use_swarm = True
                profile_name = request.model

        if use_swarm:
            # Drop query onto the Swarm Bus via the broker
            broker = ModuleRegistry.get_module("swarm_broker")
            if broker:
                # The task is to "generate_response" which multiple agents might bid on
                result = broker.execute("delegate_task", {
                    "operation": "generate_response",
                    "profile_name": profile_name,
                    "params": params,
                    "timeout": 60.0,
                    "bid_timeout": 5.0
                })
                if result.get("success") and result.get("result", {}).get("success"):
                    result = result["result"]
                elif not result.get("success") and isinstance(result.get("result"), dict) and result["result"].get("method") == "broker_fallback":
                    # Special case: Broker fallback for simple prompts (no bids)
                    result = result["result"]
                else:
                    # Fallback to normal execution if swarm fails
                    result = cognitive_module.execute(operation_to_use, params)
            else:
                result = cognitive_module.execute(operation_to_use, params)
        else:
            # Adjust params for fallback modules if needed
            if is_fallback and actual_module_name == "text_generation_engine":
                # text_generation_engine might need different params
                if operation_to_use == "generate_response" or operation_to_use == "generate_full_response":
                    operation_to_use = "generate_with_neural"
                    
                input_val = params.get("messages", [{}])[-1].get("content", "") if params.get("messages") else params.get("input", "")
                fallback_params = {
                    "prompt": input_val,
                    "input": input_val,
                    "text": input_val,
                    "context": params.get("context", ""),
                }
                params = fallback_params
            
            result = cognitive_module.execute(operation_to_use, params)

        
        # Extract response - check multiple possible fields
        response_text = (
            result.get("response", "") or
            result.get("text", "") or
            result.get("generated_text", "")
        )
        if (not response_text or not str(response_text).strip()) and isinstance(result.get("result"), dict):
            response_text = (
                result["result"].get("text", "") or
                result["result"].get("response", "")
            )
        
        if not response_text or not str(response_text).strip():
            # Empty response detected - try fallback if we haven't already
            if not is_fallback:
                # Primary module returned empty, try fallback directly
                try:
                    import logging
                    logger = logging.getLogger(__name__)
                    from oricli_core.brain.degraded_classifier import get_degraded_classifier
                    classifier = get_degraded_classifier()
                    
                    # Get fallback module name
                    fallback_name = classifier.get_fallback_module(
                        actual_module_name or "cognitive_generator",
                        operation_to_use
                    )
                    
                    if fallback_name and fallback_name != (actual_module_name or "cognitive_generator"):
                        logger.info(
                            f"Primary module {actual_module_name or 'cognitive_generator'} returned empty response, "
                            f"trying fallback {fallback_name}"
                        )
                        
                        # Get mapped operation for fallback
                        fallback_op = classifier.get_fallback_operation(
                            actual_module_name or "cognitive_generator",
                            operation_to_use,
                            fallback_name
                        ) if operation_to_use else None
                        
                        # Get fallback module
                        fallback_module = ModuleRegistry.get_module(fallback_name, auto_discover=True)
                        
                        if fallback_module:
                            # Adjust params for fallback module
                            if fallback_name == "text_generation_engine":
                                # If we're doing direct text generation (no thoughts), use generate_with_neural
                                if operation_to_use == "generate_full_response" or not operation_to_use:
                                    fallback_op = "generate_with_neural"
                                
                                fallback_params = {
                                    "input": params.get("messages", [{}])[-1].get("content", "") if params.get("messages") else params.get("input", ""),
                                    "text": params.get("messages", [{}])[-1].get("content", "") if params.get("messages") else params.get("input", ""),
                                    "context": params.get("context", ""),
                                }
                            else:
                                fallback_params = params
                            
                            fallback_result = fallback_module.execute(
                                fallback_op if fallback_op else operation_to_use,
                                fallback_params
                            )
                            
                            # Extract response from fallback
                            response_text = (
                                fallback_result.get("text", "") or
                                fallback_result.get("generated_text", "") or
                                fallback_result.get("response", "")
                            )
                            if (not response_text or not str(response_text).strip()) and isinstance(fallback_result.get("result"), dict):
                                response_text = (
                                    fallback_result["result"].get("text", "") or
                                    fallback_result["result"].get("response", "")
                                )
                            
                            if response_text and str(response_text).strip():
                                # CLEANUP: Remove assistant chatter that breaks benchmarks
                                chatter_patterns = [
                                    r"^I'm here to help\. What would you like to know\?",
                                    r"^I'm here to help\.",
                                    r"^Hello! I'm OricliAlpha.*",
                                    r"^As an AI assistant.*",
                                ]
                                for pattern in chatter_patterns:
                                    response_text = re.sub(pattern, "", response_text, flags=re.IGNORECASE | re.MULTILINE).strip()
                                
                                # Fallback succeeded!
                                actual_module_name = fallback_name
                                operation_to_use = fallback_op if fallback_op else operation_to_use
                                is_fallback = True
                                result = fallback_result  # Update result for downstream use
                                logger.info(f"Fallback {fallback_name} succeeded with operation {operation_to_use}")
                except Exception as e:
                    logger.warning(f"Fallback attempt failed: {e}")
            
            # If we already used a fallback and it failed, try one more fallback
            if (is_fallback or not response_text or not str(response_text).strip()) and actual_module_name != "text_generation_engine":
                try:
                    text_gen = ModuleRegistry.get_module("text_generation_engine")
                    if text_gen:
                        input_val = params.get("input", params.get("messages", [{}])[-1].get("content", "") if params.get("messages") else "")
                        fallback_result = text_gen.execute(
                            "generate_with_neural",
                            {
                                "prompt": input_val,
                                "input": input_val,
                                "text": input_val,
                                "context": params.get("context", ""),
                            }
                        )
                        response_text = (
                            fallback_result.get("text", "") or
                            fallback_result.get("response", "") or
                            fallback_result.get("generated_text", "")
                        )
                        if response_text and str(response_text).strip():
                            # CLEANUP: Remove assistant chatter
                            chatter_patterns = [
                                r"^I'm here to help\. What would you like to know\?",
                                r"^I'm here to help\.",
                                r"^Hello! I'm OricliAlpha.*",
                                r"^As an AI assistant.*",
                            ]
                            for pattern in chatter_patterns:
                                response_text = re.sub(pattern, "", response_text, flags=re.IGNORECASE | re.MULTILINE).strip()
                            
                            result = fallback_result
                            actual_module_name = "text_generation_engine"
                except Exception:
                    pass
            
            # If still empty, raise error with the module's error message if available
            if not response_text or not str(response_text).strip():
                # LAST RESORT: Try to get any text from the result dictionary
                response_text = str(result.get("error") or result.get("message") or "The Hive processed your request but produced no visible output.")
                
                # If still actually failing, raise the error
                if not response_text or "no visible output" in response_text:
                    error_detail = result.get("error") or "Returned empty response"
                    raise ModuleOperationError(
                        actual_module_name or "cognitive_generator",
                        operation_to_use or "generate_response",
                        error_detail
                    )
        reasoning_steps = result.get("reasoning_steps")
        confidence = result.get("confidence")
        metadata = result.get("metadata") or {}
        if not isinstance(metadata, dict):
            metadata = {}

        trace_id = result.get("trace_id")
        if not trace_id and isinstance(result.get("trace_graph"), dict):
            trace_id = result["trace_graph"].get("trace_id")
        if trace_id:
            metadata.setdefault("trace_id", trace_id)
        
        # Create response
        response_id = f"chatcmpl-{uuid.uuid4().hex[:8]}"
        created = int(time.time())
        
        choice = ChatCompletionChoice(
            index=0,
            message=ChatMessage(role="assistant", content=response_text),
            finish_reason="stop"
        )
        
        # Estimate token usage (rough approximation)
        # Extract text content for token counting (handles both string and multimodal formats)
        prompt_tokens = sum(len(msg.get_text_content().split()) for msg in request.messages)
        completion_tokens = len(response_text.split())
        
        usage = ChatCompletionUsage(
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            total_tokens=prompt_tokens + completion_tokens
        )
        
        return ChatCompletionResponse(
            id=response_id,
            created=created,
            model=request.model,
            choices=[choice],
            usage=usage,
            reasoning_steps=reasoning_steps,
            confidence=confidence,
            metadata=metadata,
            url_context_metadata=url_context_metadata if url_context_metadata else None
        )
    
    def _generate_embeddings(
        self, request: EmbeddingRequest
    ) -> EmbeddingResponse:
        """
        Internal method to generate embeddings
        """
        if self.base_url:
            res = self._make_remote_request("POST", "/v1/embeddings", request.dict())
            return EmbeddingResponse(**res)

        # Get embeddings module
        from oricli_core.brain.registry import ModuleRegistry
        embeddings_module = ModuleRegistry.get_module("embeddings")

        if embeddings_module is None:
            raise ModuleNotFoundError("embeddings")
        
        # Handle single string or list of strings
        inputs = [request.input] if isinstance(request.input, str) else request.input
        
        # Generate embeddings for all inputs
        embedding_data = []
        total_tokens = 0
        
        for idx, text in enumerate(inputs):
            params = {
                "text": text,
                "model_name": request.model
            }
            
            result = embeddings_module.execute("generate", params)
            
            embedding = result.get("embedding", [])
            if not embedding:
                raise ModuleOperationError(
                    "embeddings",
                    "generate",
                    f"Failed to generate embedding for input {idx}"
                )
            
            embedding_data.append(
                EmbeddingData(
                    object="embedding",
                    embedding=embedding,
                    index=idx
                )
            )
            
            # Estimate tokens (rough approximation)
            total_tokens += len(text.split())
        
        usage = EmbeddingUsage(
            prompt_tokens=total_tokens,
            total_tokens=total_tokens
        )
        
        return EmbeddingResponse(
            object="list",
            data=embedding_data,
            model=request.model,
            usage=usage
        )
    
    def list_models(self) -> ModelsListResponse:
        """
        List available models/capabilities including dynamic agent profiles.
        """
        models = []
        now = int(time.time())
        
        # 1. Base Cognitive Models
        base_models = ["oricli-cognitive", "oricli-swarm", "oricli-hive"]
        for mid in base_models:
            models.append(ModelInfo(
                id=mid,
                created=now,
                owned_by="oricli",
                permission=[],
                root=mid,
                parent=None
            ))
        
        # 2. Dynamic Agent Profiles (Agent Factory)
        try:
            from oricli_core.services.agent_profile_service import get_agent_profile_service
            profile_service = get_agent_profile_service()
            for profile in profile_service.list_profiles():
                models.append(ModelInfo(
                    id=profile["name"],
                    created=now,
                    owned_by="oricli-factory",
                    permission=[],
                    root=profile["name"],
                    parent=None
                ))
        except Exception:
            pass

        # 3. Embeddings Model
        models.append(ModelInfo(
            id="oricli-embeddings",
            created=now,
            owned_by="oricli",
            permission=[],
            root="oricli-embeddings",
            parent=None
        ))
        
        # 4. Direct Module Access Models
        for module_name in ModuleRegistry.list_modules():
            metadata = ModuleRegistry.get_metadata(module_name)
            if metadata and metadata.enabled:
                models.append(ModelInfo(
                    id=f"oricli-{module_name}",
                    created=now,
                    owned_by="oricli-modules",
                    permission=[],
                    root=f"oricli-{module_name}",
                    parent=None
                ))
        
        return ModelsListResponse(object="list", data=models)
    
    def execute_module_operation(
        self, module_name: str, operation: str, params: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Execute a brain module operation directly
        
        Args:
            module_name: Name of the module to execute
            operation: Operation name to execute
            params: Operation parameters as dictionary
        
        Returns:
            Operation result dictionary
        
        Raises:
            ModuleNotFoundError: If module is not found
            InvalidParameterError: If parameter validation fails
            ModuleOperationError: If operation execution fails
        """
        # Try to use availability manager for ensuring modules are online
        try:
            from oricli_core.brain.availability import get_availability_manager
            availability_manager = get_availability_manager()
            
            if availability_manager._initialized:
                # If ensuring all online, wait for module to come online instead of using fallback
                if availability_manager._ensure_all_online:
                    # Wait for module to be available (with longer timeout when ensuring all online)
                    wait_timeout = float(os.getenv("MAVAIA_CLIENT_WAIT_FOR_MODULE", "60.0"))
                    
                    # Retry loop to wait for module to come online
                    max_retries = int(os.getenv("MAVAIA_CLIENT_MAX_RETRIES", "3"))
                    retry_delay = float(os.getenv("MAVAIA_CLIENT_RETRY_DELAY", "2.0"))
                    
                    for retry in range(max_retries):
                        try:
                            module, actual_module_name = availability_manager.ensure_module_available(
                                module_name,
                                timeout=wait_timeout,
                                use_fallback=False  # Don't use fallback when ensuring all online
                            )
                            
                            if module is not None:
                                if not module.validate_params(operation, params):
                                    raise InvalidParameterError(
                                        "params",
                                        str(params),
                                        f"Validation failed for operation '{operation}'"
                                    )
                                
                                return module.execute(operation, params)
                        except ModuleNotFoundError:
                            if retry < max_retries - 1:
                                import logging
                                logger = logging.getLogger(__name__)
                                logger.info(
                                    f"Module {module_name} not available yet, "
                                    f"retrying in {retry_delay}s (attempt {retry + 1}/{max_retries})"
                                )
                                import time
                                time.sleep(retry_delay)
                                continue
                            raise
                    
                    # If we get here, module still not available after retries
                    raise ModuleNotFoundError(
                        f"Module {module_name} not available after {max_retries} retries. "
                        f"System is ensuring it comes online in background."
                    )
                else:
                    # Use fallback support (legacy behavior)
                    result = availability_manager.get_module_or_fallback(module_name, operation)
                    module, actual_module_name, is_fallback, mapped_operation = result
                    
                    if module is None:
                        raise ModuleNotFoundError(module_name)
                    
                    # Use mapped operation if fallback was used
                    operation_to_use = mapped_operation if mapped_operation else operation
                    
                    if is_fallback:
                        # Log that fallback is being used
                        import logging
                        logger = logging.getLogger(__name__)
                        logger.info(
                            f"Using fallback module {actual_module_name} for {module_name} "
                            f"with operation mapping: {operation} -> {operation_to_use}"
                        )
                    
                    if not module.validate_params(operation_to_use, params):
                        raise InvalidParameterError(
                            "params",
                            str(params),
                            f"Validation failed for operation '{operation_to_use}'"
                        )
                    
                    return module.execute(operation_to_use, params)
        except ImportError:
            # Availability manager not available, use direct registry
            pass
        except Exception as e:
            # If availability manager fails, fall back to direct registry
            import logging
            logger = logging.getLogger(__name__)
            logger.debug(f"Availability manager failed, using direct registry: {e}")
        
        # Fallback to direct registry access
        module = ModuleRegistry.get_module(module_name)
        if module is None:
            raise ModuleNotFoundError(module_name)
        
        if not module.validate_params(operation, params):
            raise InvalidParameterError(
                "params",
                str(params),
                f"Validation failed for operation '{operation}'"
            )
        
        return module.execute(operation, params)

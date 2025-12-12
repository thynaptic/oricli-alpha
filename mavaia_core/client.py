"""
Mavaia Core Client - Unified interface for all Mavaia capabilities
"""

import time
import uuid
from typing import Any, Dict, List, Optional, Union
from pathlib import Path

from mavaia_core.brain.registry import ModuleRegistry
from mavaia_core.exceptions import (
    ModuleNotFoundError,
    ModuleOperationError,
    InvalidParameterError,
    ClientError,
)
from mavaia_core.services.tool_registry import ToolRegistry
from mavaia_core.types.models import (
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


class BrainModuleProxy:
    """Proxy for accessing brain modules dynamically"""
    
    def __init__(self, client: "MavaiaClient") -> None:
        """
        Initialize brain module proxy
        
        Args:
            client: MavaiaClient instance
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
        return BrainModuleWrapper(module, name)


class BrainModuleWrapper:
    """Wrapper for brain module operations"""
    
    def __init__(self, module: Any, module_name: str) -> None:
        """
        Initialize brain module wrapper
        
        Args:
            module: BaseBrainModule instance
            module_name: Name of the module
        """
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
            return self._module.execute(operation, kwargs)
        return execute_operation


class ChatCompletions:
    """Chat completions API"""
    
    def __init__(self, client: "MavaiaClient"):
        self._client = client
    
    def create(
        self,
        model: str = "mavaia-cognitive",
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
    
    def __init__(self, client: "MavaiaClient"):
        self._client = client
    
    def create(
        self,
        input: Union[str, List[str]],
        model: str = "mavaia-embeddings",
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
    
    def __init__(self, client: "MavaiaClient"):
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
        from mavaia_core.brain.registry import ModuleRegistry
        
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
        from mavaia_core.brain.registry import ModuleRegistry
        
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
        from mavaia_core.brain.registry import ModuleRegistry
        
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
        from mavaia_core.brain.registry import ModuleRegistry
        
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
        from mavaia_core.brain.registry import ModuleRegistry
        
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
        from mavaia_core.brain.registry import ModuleRegistry
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
        from mavaia_core.brain.registry import ModuleRegistry
        
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
        from mavaia_core.brain.registry import ModuleRegistry
        
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
        from mavaia_core.brain.registry import ModuleRegistry
        
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
        from mavaia_core.brain.registry import ModuleRegistry
        
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
        from mavaia_core.brain.registry import ModuleRegistry
        
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
        from mavaia_core.brain.registry import ModuleRegistry
        
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
        from mavaia_core.brain.registry import ModuleRegistry
        
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
        from mavaia_core.brain.registry import ModuleRegistry
        
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
        from mavaia_core.brain.registry import ModuleRegistry
        
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
        from mavaia_core.brain.registry import ModuleRegistry
        
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
        from mavaia_core.brain.registry import ModuleRegistry
        
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
        from mavaia_core.brain.registry import ModuleRegistry
        
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
        from mavaia_core.brain.registry import ModuleRegistry
        
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
        from mavaia_core.brain.registry import ModuleRegistry
        
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
        from mavaia_core.brain.registry import ModuleRegistry
        
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
        from mavaia_core.brain.registry import ModuleRegistry
        
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
        from mavaia_core.brain.registry import ModuleRegistry
        
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
        from mavaia_core.brain.registry import ModuleRegistry
        
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
        from mavaia_core.brain.registry import ModuleRegistry
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
        from mavaia_core.brain.registry import ModuleRegistry
        
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
        from mavaia_core.brain.registry import ModuleRegistry
        
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
        from mavaia_core.brain.registry import ModuleRegistry
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
        from mavaia_core.brain.registry import ModuleRegistry
        
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
        from mavaia_core.brain.registry import ModuleRegistry
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
        from mavaia_core.brain.registry import ModuleRegistry
        
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
        from mavaia_core.brain.registry import ModuleRegistry
        
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
        from mavaia_core.brain.registry import ModuleRegistry
        
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
        from mavaia_core.brain.registry import ModuleRegistry
        
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
        from mavaia_core.brain.registry import ModuleRegistry
        
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
        from mavaia_core.brain.registry import ModuleRegistry
        
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
        from mavaia_core.brain.registry import ModuleRegistry
        
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
        from mavaia_core.brain.registry import ModuleRegistry
        
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
        from mavaia_core.brain.registry import ModuleRegistry
        
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
        from mavaia_core.brain.registry import ModuleRegistry
        
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
        from mavaia_core.brain.registry import ModuleRegistry
        
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
        from mavaia_core.brain.registry import ModuleRegistry
        
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
        from mavaia_core.brain.registry import ModuleRegistry
        
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
        from mavaia_core.brain.registry import ModuleRegistry
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
        from mavaia_core.brain.registry import ModuleRegistry
        
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
        from mavaia_core.brain.registry import ModuleRegistry
        
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
        from mavaia_core.brain.registry import ModuleRegistry
        
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
        from mavaia_core.brain.registry import ModuleRegistry
        
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
        from mavaia_core.brain.registry import ModuleRegistry
        
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
        from mavaia_core.brain.registry import ModuleRegistry
        
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
        from mavaia_core.brain.registry import ModuleRegistry
        
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
        from mavaia_core.brain.registry import ModuleRegistry
        
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
        from mavaia_core.brain.registry import ModuleRegistry
        
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
        from mavaia_core.brain.registry import ModuleRegistry
        
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
        from mavaia_core.brain.registry import ModuleRegistry
        
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
        from mavaia_core.brain.registry import ModuleRegistry
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
        from mavaia_core.brain.registry import ModuleRegistry
        
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
        from mavaia_core.brain.registry import ModuleRegistry
        
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
        from mavaia_core.brain.registry import ModuleRegistry
        
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
        from mavaia_core.brain.registry import ModuleRegistry
        
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
        from mavaia_core.brain.registry import ModuleRegistry
        
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
        from mavaia_core.brain.registry import ModuleRegistry
        
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
        from mavaia_core.brain.registry import ModuleRegistry
        
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
        from mavaia_core.brain.registry import ModuleRegistry
        
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
        from mavaia_core.brain.registry import ModuleRegistry
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
        from mavaia_core.brain.registry import ModuleRegistry
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
        from mavaia_core.brain.registry import ModuleRegistry
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
        from mavaia_core.brain.registry import ModuleRegistry
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
        from mavaia_core.brain.registry import ModuleRegistry
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
        from mavaia_core.brain.registry import ModuleRegistry
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
        from mavaia_core.brain.registry import ModuleRegistry
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
        from mavaia_core.brain.registry import ModuleRegistry
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
        from mavaia_core.brain.registry import ModuleRegistry
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
        from mavaia_core.brain.registry import ModuleRegistry
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
        from mavaia_core.brain.registry import ModuleRegistry
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
        from mavaia_core.brain.registry import ModuleRegistry
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
        from mavaia_core.brain.registry import ModuleRegistry
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
        from mavaia_core.brain.registry import ModuleRegistry
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
        from mavaia_core.brain.registry import ModuleRegistry
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
        from mavaia_core.brain.registry import ModuleRegistry
        
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
        from mavaia_core.brain.registry import ModuleRegistry
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
        from mavaia_core.brain.registry import ModuleRegistry
        
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
        from mavaia_core.brain.registry import ModuleRegistry
        
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
        from mavaia_core.brain.registry import ModuleRegistry
        
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
        from mavaia_core.brain.registry import ModuleRegistry
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
        from mavaia_core.brain.registry import ModuleRegistry
        
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
        from mavaia_core.brain.registry import ModuleRegistry
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
        from mavaia_core.brain.registry import ModuleRegistry
        
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
        from mavaia_core.brain.registry import ModuleRegistry
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
        from mavaia_core.brain.registry import ModuleRegistry
        
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
        from mavaia_core.brain.registry import ModuleRegistry
        
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
        from mavaia_core.brain.registry import ModuleRegistry
        from pathlib import Path
        
        module = ModuleRegistry.get_module("python_style_adaptation")
        if module is None:
            raise ModuleNotFoundError("python_style_adaptation")
        
        return module.execute("migrate_style", {
            "codebase": str(Path(codebase)),
            "new_style": new_style,
        })


class Chat:
    """Chat API namespace"""
    
    def __init__(self, client: "MavaiaClient"):
        self.completions = ChatCompletions(client)


class MavaiaClient:
    """
    Mavaia Core Client - Main interface for all Mavaia capabilities
    
    Provides:
    - OpenAI-compatible API (chat.completions, embeddings)
    - Direct brain module access via `client.brain.module_name.operation()`
    - Unified interface for all capabilities
    
    Example:
        ```python
        from mavaia_core import MavaiaClient
        
        client = MavaiaClient()
        
        # Chat completion
        response = client.chat.completions.create(
            model="mavaia-cognitive",
            messages=[{"role": "user", "content": "Hello"}]
        )
        
        # Direct module access
        result = client.brain.reasoning.reason(query="What is 2+2?")
        ```
    """
    
    def __init__(self, modules_dir: Optional[Union[str, Path]] = None) -> None:
        """
        Initialize Mavaia client
        
        Args:
            modules_dir: Optional path to brain_modules directory.
                        If not provided, uses default module discovery.
        
        Note:
            Module discovery is deferred until first use to avoid blocking startup.
        """
        import sys
        try:
            print("[DEBUG] MavaiaClient.__init__ called", file=sys.stderr)
            sys.stderr.flush()
            
            if modules_dir is not None:
                ModuleRegistry.set_modules_dir(Path(modules_dir))
            
            # Defer module discovery until first use to avoid blocking startup
            # Modules will be discovered automatically when first accessed
            
            # Initialize API namespaces
            self.chat = Chat(self)
            self.embeddings = Embeddings(self)
            self.brain = BrainModuleProxy(self)
            self.python = PythonLLM(self)
            
            print("[DEBUG] MavaiaClient initialized successfully", file=sys.stderr)
            sys.stderr.flush()
        except Exception as e:
            print(f"[ERROR] MavaiaClient initialization failed: {e}", file=sys.stderr)
            import traceback
            traceback.print_exc(file=sys.stderr)
            sys.stderr.flush()
            raise
    
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
        
        Args:
            request: Chat completion request with messages and parameters
        
        Returns:
            ChatCompletionResponse with generated response
        
        Raises:
            ModuleNotFoundError: If cognitive_generator module is not available
            ModuleOperationError: If generation fails or returns empty response
        """
        # Get cognitive generator module
        cognitive_module = ModuleRegistry.get_module("cognitive_generator")
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
        
        result = cognitive_module.execute("generate_response", params)
        
        # Extract response
        response_text = result.get("response", "") or result.get("text", "")
        if not response_text or not str(response_text).strip():
            raise ModuleOperationError(
                "cognitive_generator",
                "generate_response",
                "Returned empty response"
            )
        reasoning_steps = result.get("reasoning_steps")
        confidence = result.get("confidence")
        metadata = result.get("metadata", {})
        
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
        
        Args:
            request: Embedding request with input text(s) and model
        
        Returns:
            EmbeddingResponse with embedding vectors
        
        Raises:
            ModuleNotFoundError: If embeddings module is not available
            ModuleOperationError: If embedding generation fails
        """
        # Get embeddings module
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
        List available models/capabilities
        
        Returns:
            ModelsListResponse containing all available models and modules
        """
        models = []
        
        # Add cognitive model
        models.append(ModelInfo(
            id="mavaia-cognitive",
            created=int(time.time()),
            owned_by="mavaia",
            permission=[],
            root="mavaia-cognitive",
            parent=None
        ))
        
        # Add embeddings model
        models.append(ModelInfo(
            id="mavaia-embeddings",
            created=int(time.time()),
            owned_by="mavaia",
            permission=[],
            root="mavaia-embeddings",
            parent=None
        ))
        
        # Add models for each available brain module
        for module_name in ModuleRegistry.list_modules():
            metadata = ModuleRegistry.get_metadata(module_name)
            if metadata and metadata.enabled:
                models.append(ModelInfo(
                    id=f"mavaia-{module_name}",
                    created=int(time.time()),
                    owned_by="mavaia",
                    permission=[],
                    root=f"mavaia-{module_name}",
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


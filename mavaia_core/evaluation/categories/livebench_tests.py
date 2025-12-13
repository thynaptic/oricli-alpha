"""
LiveBench Test Executor

Integrates LiveBench benchmark suite into Mavaia's evaluation framework.
Tests all brain modules against LiveBench's diverse tasks across 6 categories:
reasoning, math, coding, language, data analysis, and instruction following.
"""

import json
import re
import sys
import time
import traceback
from datetime import datetime
from typing import Any, Dict, List, Optional, Set, TYPE_CHECKING
from pathlib import Path

# LiveBench imports
# Add LiveBench directory to Python path if it exists
_LIVEBENCH_PATH = Path(__file__).parent.parent.parent.parent / "LiveBench"
if _LIVEBENCH_PATH.exists() and str(_LIVEBENCH_PATH) not in sys.path:
    sys.path.insert(0, str(_LIVEBENCH_PATH))

try:
    from livebench.common import (
        load_questions,
        load_questions_jsonl,
        get_categories_tasks,
        LIVE_BENCH_DATA_SUPER_PATH,
        LIVE_BENCH_RELEASES,
        MatchSingle,
    )
    from livebench.gen_ground_truth_judgment import play_a_match_gt
    from livebench.code_runner.eval.utils import (
        time_limit,
        create_tempdir,
        safe_environment,
        reliability_guard,
        TimeoutException,
    )
    LIVEBENCH_AVAILABLE = True
except ImportError as e:
    LIVEBENCH_AVAILABLE = False
    IMPORT_ERROR = str(e)
    # Define a placeholder for type checking
    if TYPE_CHECKING:
        from livebench.common import MatchSingle
    else:
        MatchSingle = None  # type: ignore

# Mavaia imports
from mavaia_core.brain.base_module import BaseBrainModule
from mavaia_core.exceptions import (
    ModuleNotFoundError,
    ModuleOperationError,
    InvalidParameterError,
)
from mavaia_core.evaluation.test_data_manager import TestCase
from mavaia_core.evaluation.test_results import TestResult, TestStatus


class LiveBenchTestRunner:
    """Runs LiveBench benchmark tests for brain modules"""
    
    def __init__(self):
        """Initialize LiveBench test executor"""
        if not LIVEBENCH_AVAILABLE:
            raise ImportError(
                f"LiveBench is not available. Import error: {IMPORT_ERROR}. "
                "Please ensure LiveBench is installed in your environment."
            )
        
        from mavaia_core.brain.registry import ModuleRegistry
        self.registry = ModuleRegistry
        
        # Cache for loaded questions
        self._questions_cache: Dict[str, List[Dict[str, Any]]] = {}
        
        # Module-to-task category mapping
        self._module_category_map: Dict[str, str] = {}
    
    def _check_release_date(
        self,
        release_date: Any,
        valid_releases: Set[str]
    ) -> bool:
        """
        Check if a release date matches any valid release
        
        Args:
            release_date: Release date (can be datetime, string, or None)
            valid_releases: Set of valid release date strings
            
        Returns:
            True if release date matches a valid release
        """
        if release_date is None:
            return False
        
        # Convert datetime to string if needed
        if isinstance(release_date, datetime):
            release_date_str = release_date.strftime('%Y-%m-%d')
        else:
            release_date_str = str(release_date)
        
        # Check if it matches any valid release
        return release_date_str in valid_releases
    
    def _map_module_to_category(self, module_name: str, metadata: Any) -> Optional[str]:
        """
        Map a Mavaia module to LiveBench category based on module metadata
        
        Args:
            module_name: Module name
            metadata: Module metadata
            
        Returns:
            LiveBench category name or None if no match
        """
        if module_name in self._module_category_map:
            return self._module_category_map[module_name]
        
        name_lower = module_name.lower()
        desc_lower = (metadata.description or "").lower()
        
        # Check module name and description for category indicators
        if any(keyword in name_lower or keyword in desc_lower 
               for keyword in ["reasoning", "cot", "mcts", "chain", "thought", 
                               "logic", "deduction", "inference", "zebra", "web_of_lies"]):
            category = "reasoning"
        elif any(keyword in name_lower or keyword in desc_lower 
                 for keyword in ["code", "programming", "coding", "generation", "completion"]):
            category = "coding"
        elif any(keyword in name_lower or keyword in desc_lower 
                 for keyword in ["math", "mathematical", "arithmetic", "calculation", 
                                 "olympiad", "competition"]):
            category = "math"
        elif any(keyword in name_lower or keyword in desc_lower 
                 for keyword in ["language", "linguistic", "text", "typos", "connections", 
                                 "plot", "writing"]):
            category = "language"
        elif any(keyword in name_lower or keyword in desc_lower 
                 for keyword in ["data", "analysis", "table", "cta", "join", "reformat"]):
            category = "data_analysis"
        elif any(keyword in name_lower or keyword in desc_lower 
                 for keyword in ["instruction", "following", "ifbench"]):
            category = "instruction_following"
        else:
            # Default: try to match based on operations
            if metadata.operations:
                ops_lower = " ".join(metadata.operations).lower()
                if any(keyword in ops_lower for keyword in ["reason", "think", "analyze", "deduce"]):
                    category = "reasoning"
                elif any(keyword in ops_lower for keyword in ["code", "generate", "program"]):
                    category = "coding"
                elif any(keyword in ops_lower for keyword in ["math", "calculate", "solve"]):
                    category = "math"
                else:
                    category = None
            else:
                category = None
        
        if category:
            self._module_category_map[module_name] = category
        
        return category
    
    def _load_livebench_questions(
        self,
        category: Optional[str] = None,
        task: Optional[str] = None,
        question_source: str = "huggingface"
    ) -> List[Dict[str, Any]]:
        """
        Load LiveBench questions
        
        Args:
            category: LiveBench category (reasoning, math, coding, etc.)
            task: Specific task name (optional)
            question_source: Source for questions ("huggingface" or "jsonl")
            
        Returns:
            List of question dictionaries
        """
        cache_key = f"{category}_{task}_{question_source}"
        if cache_key in self._questions_cache:
            return self._questions_cache[cache_key]
        
        questions = []
        
        try:
            if question_source == "jsonl":
                # Load from JSONL files
                # Try to find question files in LiveBench data directory
                livebench_root = Path(__file__).parent.parent.parent.parent / "LiveBench" / "livebench" / "data"
                if livebench_root.exists():
                    if category:
                        category_dir = livebench_root / category
                        if category_dir.exists():
                            if task:
                                question_file = category_dir / task / "question.jsonl"
                                if question_file.exists():
                                    questions = load_questions_jsonl(
                                        str(question_file),
                                        livebench_releases=LIVE_BENCH_RELEASES
                                    )
                            else:
                                # Load all tasks in category
                                for task_dir in category_dir.iterdir():
                                    if task_dir.is_dir():
                                        question_file = task_dir / "question.jsonl"
                                        if question_file.exists():
                                            task_questions = load_questions_jsonl(
                                                str(question_file),
                                                livebench_releases=LIVE_BENCH_RELEASES
                                            )
                                            questions.extend(task_questions)
                    else:
                        # Load all categories
                        for cat_dir in livebench_root.iterdir():
                            if cat_dir.is_dir():
                                for task_dir in cat_dir.iterdir():
                                    if task_dir.is_dir():
                                        question_file = task_dir / "question.jsonl"
                                        if question_file.exists():
                                            task_questions = load_questions_jsonl(
                                                str(question_file),
                                                livebench_releases=LIVE_BENCH_RELEASES
                                            )
                                            questions.extend(task_questions)
            else:
                # Load from HuggingFace
                # get_categories_tasks returns a tuple: (categories_dict, tasks_dict)
                categories_dict, tasks_dict = get_categories_tasks(LIVE_BENCH_DATA_SUPER_PATH)
                
                for cat_name, category_dataset in categories_dict.items():
                    if category and cat_name != category:
                        continue
                    
                    # Get tasks for this category
                    category_tasks = tasks_dict.get(cat_name, [])
                    
                    # If we have a specific task filter, use it
                    if task:
                        if task not in category_tasks:
                            continue
                        category_tasks = [task]
                    
                    # Load questions from the category dataset
                    # The dataset contains all questions for the category
                    try:
                        # Convert dataset to list of questions
                        if hasattr(category_dataset, 'to_list'):
                            category_questions = category_dataset.to_list()
                        elif hasattr(category_dataset, '__iter__'):
                            category_questions = list(category_dataset)
                        else:
                            category_questions = []
                        
                        # Filter by task if needed
                        if task:
                            category_questions = [
                                q for q in category_questions
                                if q.get('task') == task
                            ]
                        
                        # Filter by release if needed
                        if LIVE_BENCH_RELEASES:
                            from datetime import datetime
                            # Convert release dates to strings for comparison
                            # livebench_release_date can be datetime or string
                            category_questions = [
                                q for q in category_questions
                                if self._check_release_date(q.get('livebench_release_date'), LIVE_BENCH_RELEASES)
                            ]
                        
                        questions.extend(category_questions)
                    except Exception as e:
                        # Skip categories that fail to load
                        print(f"Warning: Failed to load questions for {cat_name}: {e}")
                        continue
            
            self._questions_cache[cache_key] = questions
            return questions
            
        except Exception as e:
            print(f"Error loading LiveBench questions: {e}")
            traceback.print_exc()
            return []
    
    def _convert_question_to_module_params(
        self,
        question: Dict[str, Any],
        module_name: str,
        operation: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Convert LiveBench question to Mavaia module execution parameters
        
        Args:
            question: LiveBench question dictionary
            module_name: Target module name
            operation: Target operation name (optional)
            
        Returns:
            Parameters dictionary for module execution
        """
        # Extract question text from turns
        question_text = ""
        if "turns" in question and question["turns"]:
            if isinstance(question["turns"], list):
                question_text = question["turns"][0] if question["turns"] else ""
            else:
                question_text = str(question["turns"])
        
        # Build parameters based on module type and operation
        params: Dict[str, Any] = {}
        
        # Common parameter mappings
        # Always set both query and text to ensure compatibility with different modules
        params["query"] = question_text
        params["text"] = question_text
        params["input"] = question_text
        
        # Operation-specific parameter mappings
        if "query" in (operation or "").lower() or "reason" in (operation or "").lower():
            # Already set above, but ensure query is present
            pass
        elif "text" in (operation or "").lower() or "input" in (operation or "").lower():
            # Already set above
            pass
        
        # Add task-specific parameters
        task = question.get("task", "")
        if "code" in task.lower() or "coding" in task.lower():
            # For coding tasks, include the full question context
            params["prompt"] = question_text
            params["code"] = question_text
            if "test_cases" in question:
                params["test_cases"] = question["test_cases"]
        elif "math" in task.lower():
            params["problem"] = question_text
            params["query"] = question_text
        elif "reasoning" in question.get("category", "").lower():
            params["query"] = question_text
            params["reasoning_type"] = "analytical"
        
        # Add system prompt if available
        if "system_prompt" in question:
            params["system_prompt"] = question["system_prompt"]
        
        # Add context from multiple turns if available
        if "turns" in question and isinstance(question["turns"], list) and len(question["turns"]) > 1:
            params["conversation_history"] = question["turns"][:-1]
            params["current_turn"] = question["turns"][-1]
        
        return params
    
    def _extract_module_response(
        self,
        module_result: Dict[str, Any],
        question: Dict[str, Any]
    ) -> str:
        """
        Extract text response from module execution result
        
        Args:
            module_result: Result from module execution
            question: Original LiveBench question
            
        Returns:
            Extracted response text
        """
        # Try different possible response fields
        response = None
        
        # Common response field names
        response_fields = [
            "response", "answer", "result", "output", "text",
            "reasoning", "conclusion", "final_answer", "generated_text"
        ]
        
        for field in response_fields:
            if field in module_result:
                value = module_result[field]
                if isinstance(value, str):
                    response = value
                    break
                elif isinstance(value, dict) and "text" in value:
                    response = value["text"]
                    break
                elif isinstance(value, list) and len(value) > 0:
                    # Try first element
                    if isinstance(value[0], str):
                        response = value[0]
                        break
                    elif isinstance(value[0], dict) and "text" in value[0]:
                        response = value[0]["text"]
                        break
        
        # If no response found, try to extract from result_data
        if not response and "result_data" in module_result:
            result_data = module_result["result_data"]
            if isinstance(result_data, dict):
                for field in response_fields:
                    if field in result_data:
                        value = result_data[field]
                        if isinstance(value, str):
                            response = value
                            break
        
        # If still no response, convert entire result to string
        if not response:
            # Try to find any string value in the result
            def find_string_value(obj, depth=0):
                if depth > 3:  # Limit recursion
                    return None
                if isinstance(obj, str) and len(obj) > 10:  # Meaningful string
                    return obj
                elif isinstance(obj, dict):
                    for v in obj.values():
                        result = find_string_value(v, depth + 1)
                        if result:
                            return result
                elif isinstance(obj, list) and obj:
                    return find_string_value(obj[0], depth + 1)
                return None
            
            response = find_string_value(module_result)
        
        # Final fallback: convert to JSON string
        if not response:
            try:
                response = json.dumps(module_result, indent=2)
            except Exception:
                response = str(module_result)
        
        return response or ""
    
    def _format_response_for_livebench(
        self,
        response: str,
        question: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Format module response in LiveBench answer format
        
        Args:
            response: Module response text
            question: Original LiveBench question
            
        Returns:
            Formatted answer dictionary in LiveBench format
        """
        # LiveBench expects answer format:
        # {
        #   "choices": [{
        #     "turns": [response_text]
        #   }]
        # }
        return {
            "choices": [{
                "turns": [response]
            }]
        }
    
    def _execute_with_code_runner(
        self,
        code: str,
        test_cases: Optional[List[Dict[str, Any]]] = None,
        timeout: float = 240.0
    ) -> Dict[str, Any]:
        """
        Execute code using LiveBench's code runner utilities
        
        Args:
            code: Python code to execute
            test_cases: Optional test cases to run
            timeout: Execution timeout in seconds
            
        Returns:
            Execution result dictionary
        """
        result = {
            "success": False,
            "output": None,
            "error": None,
            "test_results": []
        }
        
        try:
            # Apply reliability guard
            reliability_guard(
                max_as_limit=1024,  # 1GB
                max_data_limit=1024,
                max_stack_limit=64  # 64MB
            )
            
            # Execute in safe environment
            with safe_environment():
                with create_tempdir() as tempdir:
                    with time_limit(min(timeout, 240.0)):
                        # Execute code
                        namespace = {}
                        exec(code, namespace, namespace)
                        
                        # If test cases provided, run them
                        if test_cases:
                            test_results = []
                            for i, test_case in enumerate(test_cases):
                                test_input = test_case.get("input", {})
                                expected_output = test_case.get("output")
                                
                                try:
                                    # Try to find and call a function with test input
                                    # This is a simplified version - actual LiveBench
                                    # has more sophisticated test case execution
                                    if "function" in namespace:
                                        func = namespace["function"]
                                        if callable(func):
                                            actual_output = func(**test_input)
                                            passed = actual_output == expected_output
                                            test_results.append({
                                                "test_index": i,
                                                "passed": passed,
                                                "expected": expected_output,
                                                "actual": actual_output
                                            })
                                except Exception as e:
                                    test_results.append({
                                        "test_index": i,
                                        "passed": False,
                                        "error": str(e)
                                    })
                            
                            result["test_results"] = test_results
                            result["success"] = all(tr.get("passed", False) for tr in test_results)
                        else:
                            # No test cases - just check if code executed
                            result["success"] = True
                            result["output"] = namespace.get("result", None)
        
        except TimeoutException:
            result["error"] = f"Execution timed out after {timeout}s"
        except Exception as e:
            result["error"] = str(e)
        
        return result
    
    def run_test_case(
        self,
        test_case: TestCase,
        timeout: Optional[float] = None
    ) -> TestResult:
        """
        Run a LiveBench test case
        
        Args:
            test_case: Test case to run (should have LiveBench question data)
            timeout: Optional timeout override
            
        Returns:
            TestResult instance
        """
        test_timeout = timeout or test_case.timeout or 60.0
        start_time = time.time()
        
        result = TestResult(
            test_id=test_case.id,
            module=test_case.module,
            category=test_case.category or "livebench",
            operation=test_case.operation,
        )
        
        try:
            # Skip if marked as skip
            if test_case.skip:
                result.status = TestStatus.SKIPPED
                result.execution_time = time.time() - start_time
                return result
            
            # Get module
            if not test_case.module:
                result.status = TestStatus.ERROR
                result.error_message = "Test case missing module name"
                result.execution_time = time.time() - start_time
                return result
            
            # Get module instance
            try:
                module = self.registry.get_module(
                    test_case.module,
                    auto_discover=True,
                    wait_timeout=2.0
                )
            except ImportError as e:
                result.status = TestStatus.SKIPPED
                result.error_message = f"Missing dependency: {str(e)}"
                result.error_type = "ImportError"
                result.execution_time = time.time() - start_time
                return result
            
            if module is None:
                result.status = TestStatus.SKIPPED
                result.error_message = f"Module not available: {test_case.module}"
                result.error_type = "ModuleNotFoundError"
                result.execution_time = time.time() - start_time
                return result
            
            # Extract LiveBench question from test case params
            # Question should be in params["question"] or params directly
            question = test_case.params.get("question") or test_case.params
            
            if not question or "question_id" not in question:
                result.status = TestStatus.ERROR
                result.error_message = "Test case missing LiveBench question data"
                result.error_type = "InvalidTestCaseError"
                result.execution_time = time.time() - start_time
                return result
            
            # Convert question to module parameters
            module_params = self._convert_question_to_module_params(
                question,
                test_case.module,
                test_case.operation
            )
            
            # Execute module operation
            if test_timeout > 0:
                module_result = self._execute_with_timeout(
                    module,
                    test_case.operation,
                    module_params,
                    test_timeout * 0.8  # Use 80% for module execution
                )
            else:
                module_result = self._execute(
                    module,
                    test_case.operation,
                    module_params
                )
            
            # Extract response
            response_text = self._extract_module_response(module_result, question)
            
            if not response_text:
                result.status = TestStatus.FAILED
                result.error_message = "No response extracted from module result"
                result.error_type = "ResponseExtractionError"
                result.execution_time = time.time() - start_time
                result.result_data = {"module_result": module_result}
                return result
            
            # Format response for LiveBench evaluation
            answer = self._format_response_for_livebench(response_text, question)
            
            # Evaluate using LiveBench's scoring function
            match = MatchSingle(
                question=question,
                model=test_case.module,
                answer=answer
            )
            
            # Use remaining 20% of timeout for evaluation
            eval_timeout = test_timeout * 0.2
            evaluation_result = self._evaluate_with_timeout(match, eval_timeout)
            
            # Convert LiveBench score to TestResult
            score = evaluation_result.get("score", 0)
            category = evaluation_result.get("category", question.get("category", "unknown"))
            
            # LiveBench scores: 0 = failed, 1 = passed (or multi-score for some tasks)
            if isinstance(score, (int, float)):
                if score > 0:
                    result.status = TestStatus.PASSED
                else:
                    result.status = TestStatus.FAILED
            else:
                # Multi-score format - check if any score > 0
                if isinstance(score, list) and any(s > 0 for s in score):
                    result.status = TestStatus.PASSED
                else:
                    result.status = TestStatus.FAILED
            
            result.result_data = {
                "livebench_score": score,
                "livebench_category": category,
                "question_id": question.get("question_id"),
                "task": question.get("task"),
                "response": response_text[:500],  # Truncate long responses
                "evaluation_result": evaluation_result
            }
            
            if result.status == TestStatus.FAILED:
                result.error_message = f"LiveBench score: {score} (expected > 0)"
                result.error_type = "LiveBenchEvaluationError"
            
            result.execution_time = time.time() - start_time
            
        except TimeoutError:
            result.status = TestStatus.TIMEOUT
            result.error_message = f"Timeout after {test_timeout}s"
            result.error_type = "TimeoutError"
            result.execution_time = time.time() - start_time
            
        except Exception as e:
            result.status = TestStatus.ERROR
            result.error_message = str(e)
            result.error_type = type(e).__name__
            result.execution_time = time.time() - start_time
            if hasattr(e, "__traceback__"):
                result.error_message += f"\n{traceback.format_exc()}"
        
        return result
    
    def _execute(
        self,
        module: BaseBrainModule,
        operation: Optional[str],
        params: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Execute module operation"""
        if not operation:
            initialized = module.initialize()
            return {"initialized": initialized}
        return module.execute(operation, params)
    
    def _execute_with_timeout(
        self,
        module: BaseBrainModule,
        operation: Optional[str],
        params: Dict[str, Any],
        timeout: float
    ) -> Dict[str, Any]:
        """Execute module operation with timeout"""
        import threading
        
        result_container = [None]
        exception_container = [None]
        
        def execute():
            try:
                result_container[0] = self._execute(module, operation, params)
            except Exception as e:
                exception_container[0] = e
        
        thread = threading.Thread(target=execute, daemon=True)
        thread.start()
        thread.join(timeout=timeout)
        
        if thread.is_alive():
            raise TimeoutError(f"Operation exceeded timeout of {timeout}s")
        
        if exception_container[0]:
            raise exception_container[0]
        
        return result_container[0]
    
    def _evaluate_with_timeout(
        self,
        match: "MatchSingle",
        timeout: float
    ) -> Dict[str, Any]:
        """Evaluate LiveBench match with timeout"""
        import threading
        
        result_container = [None]
        exception_container = [None]
        
        def evaluate():
            try:
                result_container[0] = play_a_match_gt(match, output_file=None, debug=False)
            except Exception as e:
                exception_container[0] = e
        
        thread = threading.Thread(target=evaluate, daemon=True)
        thread.start()
        thread.join(timeout=timeout)
        
        if thread.is_alive():
            raise TimeoutError(f"Evaluation exceeded timeout of {timeout}s")
        
        if exception_container[0]:
            raise exception_container[0]
        
        return result_container[0] or {}
    
    def discover_livebench_tests(
        self,
        module: Optional[str] = None,
        category: Optional[str] = None,
        task: Optional[str] = None,
        max_questions: Optional[int] = None
    ) -> List[TestCase]:
        """
        Discover LiveBench questions and convert to TestCase objects
        
        Args:
            module: Optional module name to test
            category: Optional LiveBench category filter
            task: Optional task name filter
            max_questions: Maximum number of questions per task (for testing)
            
        Returns:
            List of TestCase objects
        """
        test_cases = []
        
        # Load questions
        questions = self._load_livebench_questions(
            category=category,
            task=task,
            question_source="huggingface"
        )
        
        if not questions:
            return test_cases
        
        # If module specified, filter questions by module's category
        if module:
            try:
                module_instance = self.registry.get_module(
                    module,
                    auto_discover=True,
                    wait_timeout=2.0
                )
                if module_instance:
                    metadata = module_instance.metadata
                    module_category = self._map_module_to_category(module, metadata)
                    
                    if module_category:
                        # Filter questions to module's category
                        questions = [q for q in questions if q.get("category") == module_category]
            except Exception:
                pass
        
        # Limit questions if specified
        if max_questions and len(questions) > max_questions:
            questions = questions[:max_questions]
        
        # Convert questions to test cases
        for question in questions:
            question_id = question.get("question_id", "unknown")
            question_category = question.get("category", "unknown")
            question_task = question.get("task", "unknown")
            
            # Determine target module
            target_module = module
            if not target_module:
                # Try to find a suitable module for this question category
                # This is a simplified heuristic - in practice, you might want
                # more sophisticated module selection
                try:
                    # Ensure modules are discovered
                    if not self.registry._discovered:
                        self.registry.discover_modules(background=False, verbose=False)
                    all_modules = self.registry.list_modules()
                except Exception:
                    all_modules = []
                
                for mod_name in all_modules:
                    try:
                        mod_metadata = self.registry.get_metadata(mod_name)
                        if mod_metadata:
                            mod_category = self._map_module_to_category(mod_name, mod_metadata)
                            if mod_category == question_category:
                                target_module = mod_name
                                break
                    except Exception:
                        continue
            
            if not target_module:
                # Skip if no suitable module found
                continue
            
            # Determine operation
            operation = None
            try:
                if target_module:
                    mod_metadata = self.registry.get_metadata(target_module)
                    if mod_metadata and mod_metadata.operations:
                        # Use first operation that seems relevant
                        for op in mod_metadata.operations:
                            op_lower = op.lower()
                            if any(keyword in op_lower for keyword in 
                                   ["reason", "think", "analyze", "generate", "execute", "solve"]):
                                operation = op
                                break
                        if not operation:
                            operation = mod_metadata.operations[0]
            except Exception:
                pass
            
            # Create test case
            test_case = TestCase(
                id=f"livebench_{question_category}_{question_task}_{question_id}",
                category="livebench",
                module=target_module,
                operation=operation,
                params={
                    "question": question
                },
                expected={
                    "validation": {
                        "type": "livebench_score",
                        "min_score": 1
                    }
                },
                timeout=60.0,
                description=f"LiveBench {question_category}/{question_task} question {question_id}"
            )
            
            test_cases.append(test_case)
        
        return test_cases
    
    def run_test_suite(
        self,
        test_cases: List[TestCase],
        timeout: Optional[float] = None
    ) -> List[TestResult]:
        """
        Run a suite of LiveBench test cases
        
        Args:
            test_cases: List of test cases to run
            timeout: Optional timeout override for all tests
            
        Returns:
            List of test results
        """
        results = []
        
        for test_case in test_cases:
            result = self.run_test_case(test_case, timeout)
            results.append(result)
        
        return results


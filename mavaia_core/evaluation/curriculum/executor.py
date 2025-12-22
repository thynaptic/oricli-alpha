"""
Test Execution Engine

Executes curriculum tests against Mavaia's cognitive stack, captures reasoning
traces, monitors safety posture, and applies constraints.
"""

import json
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

from mavaia_core import MavaiaClient
from mavaia_core.evaluation.curriculum.models import (
    TestConfiguration,
    TestResult,
    PassFailStatus,
)
from mavaia_core.evaluation.curriculum.constraints import ConstraintManager
from mavaia_core.evaluation.curriculum.rubric import RubricScorer
from mavaia_core.evaluation.curriculum.data_sources.manager import DataSourceManager


class TestExecutor:
    """Executes curriculum tests"""
    
    def __init__(
        self,
        client: Optional[MavaiaClient] = None,
        data_source_manager: Optional[DataSourceManager] = None,
    ):
        """
        Initialize test executor
        
        Args:
            client: MavaiaClient instance (creates new if not provided)
            data_source_manager: DataSourceManager instance (creates new if not provided)
        """
        self.client = client or MavaiaClient()
        self.scorer = RubricScorer()
        self.data_dir = Path(__file__).parent / "data"
        # Lazy initialization of data source manager to avoid hanging
        self._data_source_manager = data_source_manager
    
    @property
    def data_source_manager(self) -> "DataSourceManager":
        """Lazy initialization of data source manager"""
        if self._data_source_manager is None:
            self._data_source_manager = DataSourceManager()
        return self._data_source_manager
        
        # Ensure modules are discovered before use
        from mavaia_core.brain.registry import ModuleRegistry
        if not ModuleRegistry._discovered:
            ModuleRegistry.discover_modules(verbose=False)
        
        # Verify cognitive_generator is available
        cognitive_gen = ModuleRegistry.get_module("cognitive_generator", auto_discover=True)
        if cognitive_gen is None:
            # Try to discover again with verbose output to see what's wrong
            ModuleRegistry.discover_modules(verbose=True)
            # Check again
            cognitive_gen = ModuleRegistry.get_module("cognitive_generator", auto_discover=True)
            if cognitive_gen is None:
                # List available modules for debugging
                available = ModuleRegistry.list_modules()
                import sys
                print(f"[TestExecutor] Warning: cognitive_generator not found. Available modules: {available[:10]}...", file=sys.stderr)
    
    def execute_test(
        self,
        config: TestConfiguration,
        question_data: Optional[Dict[str, Any]] = None,
    ) -> TestResult:
        """
        Execute a single test
        
        Args:
            config: Test configuration
            question_data: Question data (if None, loads from data directory)
        
        Returns:
            TestResult object
        """
        # Load question if not provided
        if question_data is None:
            question_data = self._load_question(config)
        
        if not question_data:
            # Try to get any question from this level/subject without strict filtering
            question_data = self.data_source_manager.get_question(
                level=config.level,
                subject=config.subject,
                skill_type=None,  # Don't filter by skill_type
                difficulty_style=None,  # Don't filter by difficulty_style
            )
            
            if question_data:
                # Update config to match the question we found
                if question_data.get("skill_type"):
                    config.skill_type = question_data["skill_type"]
                if question_data.get("difficulty_style"):
                    config.difficulty_style = question_data["difficulty_style"]
            else:
                # Last resort: try local files without filtering
                question_file = self.data_dir / "levels" / config.level / f"{config.subject}.json"
                if question_file.exists():
                    try:
                        with open(question_file, "r", encoding="utf-8") as f:
                            data = json.load(f)
                            questions = data.get("questions", [])
                            if questions:
                                question_data = questions[0]
                                if question_data.get("skill_type"):
                                    config.skill_type = question_data["skill_type"]
                                if question_data.get("difficulty_style"):
                                    config.difficulty_style = question_data["difficulty_style"]
                    except Exception:
                        pass
            
            if not question_data:
                raise ValueError(f"Question not found for configuration: {config}")
        
        # Setup constraints
        constraint_manager = ConstraintManager(config.constraints)
        
        # Initialize result
        test_id = question_data.get("id", f"{config.subject}_{config.level}_{config.skill_type}_{config.difficulty_style}")
        
        start_time = time.time()
        reasoning_trace = {}
        safety_posture_summary = {}
        error_message = None
        error_type = None
        actual_answer = None
        response_text = ""
        
        # Log test start (for debugging/progress tracking)
        import sys
        print(f"[TestExecutor] Starting test: {test_id}", file=sys.stderr, flush=True)
        
        try:
            with constraint_manager.execution_context():
                # Setup memory continuity if enabled
                memory_config = constraint_manager.setup_memory_continuity()
                
                # Prepare execution parameters
                question = question_data.get("question", "")
                execution_params = {
                    "query": question,
                    "context": {
                        "level": config.level,
                        "subject": config.subject,
                        "skill_type": config.skill_type,
                        "difficulty_style": config.difficulty_style,
                    },
                }
                
                # Apply safety posture
                safety_config = constraint_manager.get_safety_posture_config()
                execution_params["safety_posture"] = safety_config
                
                # Apply MCTS depth limit if specified
                if constraint_manager.get_mcts_depth_limit():
                    execution_params["mcts_depth"] = constraint_manager.get_mcts_depth_limit()
                
                # Execute via cognitive generator (main entry point)
                # First try chat completions (uses cognitive_generator internally)
                try:
                    result = self.client.chat.completions.create(
                        model="mavaia-cognitive",
                        messages=[
                            {"role": "user", "content": question}
                        ],
                        temperature=0.7,
                    )
                    
                    response_text = result.choices[0].message.content
                    actual_answer = response_text
                    
                    # Try to extract structured answer if available
                    if hasattr(result, "usage"):
                        constraint_manager.record_tokens(result.usage.total_tokens)
                    
                except (ModuleNotFoundError, Exception) as e:
                    # Check if error is related to cognitive_generator
                    error_str = str(e).lower()
                    is_cognitive_error = (
                        "cognitive_generator" in error_str or
                        "module" in error_str and "not found" in error_str
                    )
                    
                    if is_cognitive_error:
                        # If cognitive_generator not found or failed, use availability manager fallback
                        error_message = str(e)
                        error_type = type(e).__name__
                        response_text = ""  # Initialize response_text
                        
                        # Use availability manager to get module or fallback with proper operation mapping
                        try:
                            from mavaia_core.brain.availability import get_availability_manager
                            availability_manager = get_availability_manager()
                            
                            if availability_manager._initialized:
                                # Get cognitive_generator or fallback with operation mapping
                                result = availability_manager.get_module_or_fallback(
                                    "cognitive_generator",
                                    "generate_response"
                                )
                                module, actual_module_name, is_fallback, mapped_operation = result
                                
                                if module:
                                    # Use the mapped operation (or original if no mapping)
                                    operation_to_use = mapped_operation if mapped_operation else "generate_response"
                                    
                                    # Prepare params for the operation
                                    if actual_module_name == "text_generation_engine":
                                        # text_generation_engine uses different params
                                        fallback_params = {
                                            "input": question,
                                            "context": execution_params.get("context", ""),
                                        }
                                    elif actual_module_name == "neural_text_generator":
                                        # neural_text_generator might use different params
                                        fallback_params = {
                                            "prompt": question,
                                            "max_tokens": 500
                                        }
                                    else:
                                        # Use original params
                                        fallback_params = {
                                            "input": question,
                                            "context": execution_params.get("context", ""),
                                        }
                                    
                                    gen_result = module.execute(operation_to_use, fallback_params)
                                    
                                    # Extract text from result (handle different response formats)
                                    response_text = (
                                        gen_result.get("text", "") or
                                        gen_result.get("generated_text", "") or
                                        gen_result.get("response", "") or
                                        gen_result.get("result", {}).get("text", "") if isinstance(gen_result.get("result"), dict) else "" or
                                        str(gen_result) if gen_result else ""
                                    )
                                    
                                    if response_text and response_text.strip():
                                        actual_answer = response_text
                                        error_message = None
                                        error_type = None
                                    else:
                                        error_message = f"{str(e)} (fallback {actual_module_name} returned empty response)"
                                else:
                                    # No fallback available, try manual fallbacks
                                    from mavaia_core.brain.registry import ModuleRegistry
                                    
                                    # Try text_generation_engine
                                    text_gen = ModuleRegistry.get_module("text_generation_engine")
                                    if text_gen:
                                        gen_result = text_gen.execute(
                                            "generate_full_response",
                                            {"input": question, "context": execution_params.get("context", "")}
                                        )
                                        response_text = str(gen_result.get("text", gen_result.get("response", gen_result)))
                                        if response_text and response_text.strip():
                                            actual_answer = response_text
                                            error_message = None
                                            error_type = None
                                    
                                    # Try reasoning module as last resort
                                    if not response_text or not response_text.strip():
                                        reasoning_module = ModuleRegistry.get_module("reasoning")
                                        if reasoning_module:
                                            reasoning_result = reasoning_module.execute(
                                                "reason",
                                                {"query": question}
                                            )
                                            response_text = str(reasoning_result.get("result", reasoning_result.get("reasoning", reasoning_result)))
                                            if response_text and response_text.strip():
                                                actual_answer = response_text
                                                error_message = None
                                                error_type = None
                        except Exception as fallback_error:
                            # If all fallbacks fail, keep original error
                            error_message = f"{str(e)} (fallback also failed: {fallback_error})"
                            error_type = type(e).__name__
                    else:
                        # Not a cognitive_generator error, re-raise or handle normally
                        raise
                    
                except Exception as e:
                    error_message = str(e)
                    error_type = type(e).__name__
                    # Don't raise immediately - allow scoring to proceed with error
                    response_text = ""  # Empty response for scoring
                
                # Capture reasoning trace
                reasoning_trace = self._capture_reasoning_trace(config, execution_params)
                
                # Monitor safety posture
                safety_posture_summary = self._monitor_safety_posture(config, execution_params)
                
                # Track memory turns if enabled
                if memory_config.get("enabled"):
                    constraint_manager.track_memory_turn({
                        "text": question,
                        "response": response_text,
                        "topic": config.subject,
                        "entities": {},
                    })
                
                # Check constraints
                constraint_validation = constraint_manager.validate_constraints()
                if not constraint_validation["valid"]:
                    error_message = f"Constraint violations: {constraint_validation['violations']}"
                    error_type = "ConstraintViolation"
        
        except Exception as e:
            if not error_message:
                error_message = str(e)
                error_type = type(e).__name__
        
        execution_time = time.time() - start_time
        
        # Score the test
        expected_answer = question_data.get("answer")
        question_type = question_data.get("question_type", "free_response")
        question_complexity = question_data.get("metadata", {}).get("complexity", 3)
        expected_steps = question_data.get("metadata", {}).get("expected_reasoning_steps")
        
        # Detect memory corruption
        memory_corruption_count = 0
        if config.constraints.memory_continuity != "off":
            corruption_result = constraint_manager.detect_memory_corruption()
            if corruption_result.get("corruption_detected"):
                memory_corruption_count = len(corruption_result.get("indicators", []))
        
        score_breakdown = self.scorer.score_test(
            expected_answer=expected_answer,
            actual_answer=actual_answer or response_text,
            reasoning_trace=reasoning_trace,
            response=response_text,
            question_type=question_type,
            question_complexity=question_complexity,
            expected_steps=expected_steps,
            safety_posture_summary=safety_posture_summary,
            memory_corruption_count=memory_corruption_count,
        )
        
        # Determine pass/fail
        pass_fail_status = self.scorer.determine_pass_fail(
            score_breakdown,
            safety_posture_summary=safety_posture_summary,
        )
        
        # Analyze results to populate weakness/strength maps
        from mavaia_core.evaluation.curriculum.analyzer import ResultAnalyzer
        analyzer = ResultAnalyzer()
        
        # Create temporary result for analysis
        temp_result = TestResult(
            test_id=test_id,
            test_config=config,
            score=score_breakdown.final_score,
            score_breakdown=score_breakdown,
            reasoning_trace=reasoning_trace,
            cognitive_weakness_map={},
            cognitive_strength_map={},
            safety_posture_summary=safety_posture_summary,
            pass_fail_status=pass_fail_status,
            execution_time=execution_time,
            error_message=error_message,
            error_type=error_type,
        )
        
        # Populate weakness and strength maps
        weakness_map = analyzer.analyze_cognitive_weaknesses(temp_result)
        strength_map = analyzer.analyze_cognitive_strengths(temp_result)
        suggested_next = analyzer.suggest_next_test(temp_result)
        
        # Create final test result
        test_result = TestResult(
            test_id=test_id,
            test_config=config,
            score=score_breakdown.final_score,
            score_breakdown=score_breakdown,
            reasoning_trace=reasoning_trace,
            cognitive_weakness_map=weakness_map,
            cognitive_strength_map=strength_map,
            safety_posture_summary=safety_posture_summary,
            suggested_next_test=suggested_next,
            pass_fail_status=pass_fail_status,
            execution_time=execution_time,
            error_message=error_message,
            error_type=error_type,
        )
        
        return test_result
    
    def execute_full_curriculum(
        self,
        progressive: bool = True,
        start_config: Optional[TestConfiguration] = None,
        source_name: Optional[str] = None,
    ) -> List[TestResult]:
        """
        Execute full curriculum (progressive or all)
        
        Args:
            progressive: If True, use progressive difficulty testing
            start_config: Starting configuration (for progressive mode)
            source_name: Optional specific data source to use
        
        Returns:
            List of TestResult objects
        """
        if progressive:
            return self._execute_progressive(start_config, source_name)
        else:
            return self._execute_all_tests(source_name)
    
    def _execute_progressive(
        self,
        start_config: Optional[TestConfiguration] = None,
        source_name: Optional[str] = None,
    ) -> List[TestResult]:
        """Execute progressive difficulty testing"""
        from mavaia_core.evaluation.curriculum.selector import CurriculumSelector
        
        selector = CurriculumSelector()
        results = []
        
        # Start with easiest configuration
        if start_config is None:
            start_config = TestConfiguration(
                level="k5",
                subject="math",
                skill_type="foundational",
                difficulty_style="standard",
            )
        
        current_config = start_config
        failed = False
        test_number = 0
        
        # Progressive difficulty levels
        level_progression = ["k5", "middle_school", "high_school", "undergrad", "grad", "phd"]
        difficulty_progression = ["standard", "accelerated", "honors", "competition", "research"]
        skill_progression = [
            "foundational",
            "applied",
            "abstract_reasoning",
            "explanatory_reasoning",
            "adaptive_behavior",
            "long_horizon_reasoning",
            "creative_synthesis",
        ]
        
        while not failed:
            try:
                test_number += 1
                # Execute test at current configuration
                result = self.execute_test(current_config)
                results.append(result)
                
                # Check if passed
                if result.pass_fail_status == PassFailStatus.FAIL:
                    failed = True
                    break
                
                # Increase difficulty in one dimension
                current_config = self._increase_difficulty(
                    current_config,
                    level_progression,
                    difficulty_progression,
                    skill_progression,
                )
                
                if current_config is None:
                    # Reached maximum difficulty
                    break
            
            except Exception as e:
                # Test execution failed - create error result
                import sys
                print(f"[TestExecutor] Error executing test: {e}", file=sys.stderr)
                # Create a failure result so we have something to report
                # Import PassFailStatus here to avoid scoping issues
                from mavaia_core.evaluation.curriculum.models import PassFailStatus as PFS
                error_result = TestResult(
                    test_id=f"error_{test_number}",
                    test_config=current_config,
                    score=0.0,
                    score_breakdown=self.scorer.rubric.compute_score(0, 0, 0, 0),
                    pass_fail_status=PFS.FAIL,
                    error_message=str(e),
                    error_type=type(e).__name__,
                )
                results.append(error_result)
                failed = True
                break
        
        return results
    
    def _increase_difficulty(
        self,
        config: TestConfiguration,
        level_progression: List[str],
        difficulty_progression: List[str],
        skill_progression: List[str],
    ) -> Optional[TestConfiguration]:
        """Increase difficulty in one dimension"""
        # Try increasing difficulty style first
        current_difficulty_idx = difficulty_progression.index(config.difficulty_style)
        if current_difficulty_idx < len(difficulty_progression) - 1:
            return TestConfiguration(
                level=config.level,
                subject=config.subject,
                skill_type=config.skill_type,
                difficulty_style=difficulty_progression[current_difficulty_idx + 1],
                constraints=config.constraints,
            )
        
        # Then try increasing skill type
        current_skill_idx = skill_progression.index(config.skill_type)
        if current_skill_idx < len(skill_progression) - 1:
            return TestConfiguration(
                level=config.level,
                subject=config.subject,
                skill_type=skill_progression[current_skill_idx + 1],
                difficulty_style=config.difficulty_style,
                constraints=config.constraints,
            )
        
        # Finally try increasing level
        current_level_idx = level_progression.index(config.level)
        if current_level_idx < len(level_progression) - 1:
            return TestConfiguration(
                level=level_progression[current_level_idx + 1],
                subject=config.subject,
                skill_type=config.skill_type,
                difficulty_style="standard",  # Reset difficulty when level increases
                constraints=config.constraints,
            )
        
        # Maximum difficulty reached
        return None
    
    def _execute_all_tests(self) -> List[TestResult]:
        """Execute all tests in curriculum"""
        results = []
        
        # Load all test files
        levels_dir = self.data_dir / "levels"
        for level_dir in levels_dir.iterdir():
            if not level_dir.is_dir():
                continue
            
            level = level_dir.name
            for subject_file in level_dir.glob("*.json"):
                subject = subject_file.stem
                
                with open(subject_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    questions = data.get("questions", [])
                    
                    for question_data in questions:
                        config = TestConfiguration(
                            level=level,
                            subject=subject,
                            skill_type=question_data.get("skill_type", "foundational"),
                            difficulty_style=question_data.get("difficulty_style", "standard"),
                        )
                        
                        try:
                            result = self.execute_test(config, question_data)
                            results.append(result)
                        except Exception as e:
                            # Create error result
                            result = TestResult(
                                test_id=question_data.get("id", "unknown"),
                                test_config=config,
                                score=0.0,
                                score_breakdown=self.scorer.rubric.compute_score(0, 0, 0, 0),
                                pass_fail_status=PassFailStatus.FAIL,
                                error_message=str(e),
                                error_type=type(e).__name__,
                            )
                            results.append(result)
        
        return results
    
    def _load_question(
        self,
        config: TestConfiguration,
        source_name: Optional[str] = None,
    ) -> Optional[Dict[str, Any]]:
        """
        Load question data for configuration from data sources
        
        Args:
            config: Test configuration
            source_name: Optional specific source to use
        
        Returns:
            Question dictionary or None
        """
        # Try data source manager first
        question = self.data_source_manager.get_question(
            level=config.level,
            subject=config.subject,
            skill_type=config.skill_type,
            difficulty_style=config.difficulty_style,
            source_name=source_name,
        )
        
        if question:
            # If test_id is specified, check if it matches
            if config.test_id:
                if question.get("id") == config.test_id:
                    return question
                return None
            return question
        
        # Fallback to local file loading for backward compatibility
        question_file = (
            self.data_dir / "levels" / config.level / f"{config.subject}.json"
        )
        
        if not question_file.exists():
            return None
        
        try:
            with open(question_file, "r", encoding="utf-8") as f:
                data = json.load(f)
                questions = data.get("questions", [])
                
                # Filter by skill_type and difficulty_style
                matching = [
                    q for q in questions
                    if q.get("skill_type") == config.skill_type
                    and q.get("difficulty_style") == config.difficulty_style
                ]
                
                if config.test_id:
                    # Return specific test
                    for q in matching:
                        if q.get("id") == config.test_id:
                            return q
                    return None
                
                # Return first matching question
                return matching[0] if matching else None
        except (json.JSONDecodeError, IOError):
            return None
    
    def _capture_reasoning_trace(
        self,
        config: TestConfiguration,
        execution_params: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Capture reasoning trace from CoT/ToT/MCTS modules"""
        trace = {
            "modules_used": [],
            "reasoning_method": None,
            "steps": [],
        }
        
        try:
            # Try to get reasoning trace from chain_of_thought
            try:
                cot_result = self.client.execute_module_operation(
                    "chain_of_thought",
                    "execute_cot",
                    {"query": execution_params.get("query", "")}
                )
                if cot_result:
                    trace["reasoning_method"] = "chain_of_thought"
                    trace["steps"] = cot_result.get("steps", [])
                    trace["modules_used"].append("chain_of_thought")
            except Exception:
                pass
            
            # Try tree_of_thought
            try:
                tot_result = self.client.execute_module_operation(
                    "tree_of_thought",
                    "execute_tot",
                    {"query": execution_params.get("query", "")}
                )
                if tot_result:
                    trace["reasoning_method"] = "tree_of_thought"
                    trace["tree"] = tot_result.get("tree", {})
                    trace["modules_used"].append("tree_of_thought")
            except Exception:
                pass
            
            # Try mcts_reasoning
            try:
                mcts_result = self.client.execute_module_operation(
                    "mcts_reasoning",
                    "search",
                    {"query": execution_params.get("query", "")}
                )
                if mcts_result:
                    trace["reasoning_method"] = "mcts"
                    trace["search_result"] = mcts_result
                    trace["modules_used"].append("mcts_reasoning")
            except Exception:
                pass
        
        except Exception:
            pass
        
        return trace
    
    def _monitor_safety_posture(
        self,
        config: TestConfiguration,
        execution_params: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Monitor safety framework interactions"""
        summary = {
            "safety_checks_performed": 0,
            "violations_detected": 0,
            "unblocked_violations": [],
            "critical_issues": [],
            "safety_posture": config.constraints.safety_posture,
        }
        
        try:
            # Try to get safety framework status
            safety_result = self.client.execute_module_operation(
                "safety_framework",
                "get_service_health",
                {}
            )
            if safety_result:
                summary["safety_checks_performed"] = safety_result.get("total_checks", 0)
                summary["violations_detected"] = safety_result.get("violations", 0)
        except Exception:
            pass
        
        return summary


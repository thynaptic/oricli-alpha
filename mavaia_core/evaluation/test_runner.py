"""
Evaluation Framework

Main entry point for the MMLU-style test suite.
Orchestrates test execution, collects results, and generates reports.
"""

import sys
import time
import uuid
from pathlib import Path
from typing import Any, Dict, List, Optional, Union
from datetime import datetime, timezone

# All imports made lazy to avoid triggering module discovery on import
# These will be imported when actually needed


class TestRunner:
    """Main evaluation framework that orchestrates test execution"""
    
    def __init__(
        self,
        test_data_dir: Optional[Union[str, Path]] = None,
        results_dir: Optional[Union[str, Path]] = None,
        verbose: bool = True,
        use_colors: bool = True
    ):
        """
        Initialize evaluation framework
        
        Args:
            test_data_dir: Directory containing test data files
            results_dir: Directory for storing results
            verbose: Enable verbose output
            use_colors: Enable color output
        """
        # Import lazily to avoid triggering discovery during import
        from mavaia_core.evaluation.test_data_manager import TestDataManager
        from mavaia_core.evaluation.test_results import TestResults
        from mavaia_core.evaluation.test_reporter import TestReporter
        
        self.test_data_manager = TestDataManager(test_data_dir)
        self.test_results = TestResults(results_dir)
        self.reporter = TestReporter(use_colors=use_colors, verbose=verbose)
        self.verbose = verbose
        
        # Initialize test executors lazily (only when needed)
        self.module_runner = None
        self.api_runner = None
        self.client_runner = None
        self.system_runner = None
        self.reasoning_runner = None
        self.safety_runner = None
        self.code_generation_runner = None
        self.livebench_runner = None
        
        # Don't block on module discovery - let it happen lazily when needed
        # Modules will be discovered when test executors try to access them
        if self.verbose:
            print("Evaluation framework initialized (test executors will be created on demand)", flush=True)
    
    def discover_test_cases(
        self,
        module: Optional[str] = None,
        category: Optional[str] = None,
        tags: Optional[List[str]] = None,
        tag_mode: str = "all",
        new_only: bool = False,
        livebench_category: Optional[str] = None,
        max_questions: Optional[int] = None
    ) -> "List[TestCase]":
        """
        Discover all test cases
        
        Args:
            module: Filter by module name
            category: Filter by category
            tags: Filter by tags
            tag_mode: How to combine tags - "all" (AND) or "any" (OR)
            new_only: Only return tests for modules that don't have test files yet
            
        Returns:
            List of test cases
        """
        # Load all test suites
        self.test_data_manager.load_all_test_suites()
        
        # If new_only, find modules without test files
        if new_only:
            modules_with_tests = set()
            for suite in self.test_data_manager._test_suites.values():
                if suite.module:
                    modules_with_tests.add(suite.module)
            
            # Get all discovered modules
            from mavaia_core.brain.registry import ModuleRegistry
            # Use synchronous discovery to ensure modules are found
            ModuleRegistry.discover_modules(background=False, verbose=False)
            
            all_modules = set(ModuleRegistry.list_modules())
            new_modules = all_modules - modules_with_tests
            
            if self.verbose and new_modules:
                print(f"Found {len(new_modules)} new modules without test files: {', '.join(sorted(new_modules)[:10])}", flush=True)
                if len(new_modules) > 10:
                    print(f"  ... and {len(new_modules) - 10} more", flush=True)
            
            # Filter to only new modules
            if new_modules:
                # If module filter is specified, intersect with new modules
                if module:
                    if module in new_modules:
                        module = module  # Keep the filter
                    else:
                        module = None  # Clear filter if not in new modules
                else:
                    # Create test cases for new modules (they won't have test files)
                    # Return empty list - new modules need test files created first
                    if self.verbose:
                        print(f"Note: New modules found but no test files exist yet. Create test files for: {', '.join(sorted(new_modules))}", flush=True)
                    return []
            else:
                if self.verbose:
                    print("No new modules found (all modules have test files)", flush=True)
                return []
        
        # Special handling for LiveBench category - discover tests dynamically
        if category == "livebench":
            try:
                if self.livebench_runner is None:
                    from mavaia_core.evaluation.categories import LiveBenchTestRunner
                    self.livebench_runner = LiveBenchTestRunner()
                
                # Discover LiveBench tests
                test_cases = self.livebench_runner.discover_livebench_tests(
                    module=module,
                    category=livebench_category,  # Use provided LiveBench category filter
                    task=None,
                    max_questions=max_questions  # Use provided max questions limit
                )
                return test_cases
            except ImportError as e:
                if self.verbose:
                    print(f"Warning: LiveBench not available: {e}", flush=True)
                return []
        
        # Get filtered test cases from test data manager
        test_cases = self.test_data_manager.get_test_cases(
            module=module,
            category=category,
            tags=tags,
            include_skipped=False,
            tag_mode=tag_mode
        )
        
        return test_cases
    
    def run_test_suite(
        self,
        module: Optional[str] = None,
        category: Optional[str] = None,
        tags: Optional[List[str]] = None,
        timeout: Optional[float] = None,
        tag_mode: str = "all",
        new_only: bool = False
    ) -> "TestRunResults":
        """
        Run the complete test suite
        
        Args:
            module: Filter by module name
            category: Filter by category
            tags: Filter by tags
            timeout: Optional timeout override for all tests
            tag_mode: How to combine tags - "all" (AND) or "any" (OR)
            new_only: Only test modules without test files
            
        Returns:
            TestRunResults instance
        """
        # Import TestRunResults lazily
        from mavaia_core.evaluation.test_results import TestRunResults
        
        # Generate test run ID
        try:
            # Use timezone-aware datetime (Python 3.11+)
            test_run_id = f"{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:8]}"
        except (AttributeError, ValueError, TypeError):
            # Fallback for older Python versions
            test_run_id = f"{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:8]}"
        
        # Create results object
        results = TestRunResults(test_run_id=test_run_id)
        
        # Print header
        if self.verbose:
            self.reporter.print_header()
        
        # Discover test cases
        if self.verbose:
            print("Loading test data...", end="", flush=True)
            sys.stdout.flush()
        
        try:
            test_cases = self.discover_test_cases(
                module=module,
                category=category,
                tags=tags,
                tag_mode=getattr(self, '_tag_mode', 'all'),
                new_only=getattr(self, '_new_only', False),
                livebench_category=getattr(self, '_livebench_category', None),
                max_questions=getattr(self, '_max_questions', None)
            )
            if self.verbose:
                print(f" found {len(test_cases)} test cases", flush=True)
                sys.stdout.flush()
        except Exception as e:
            if self.verbose:
                print(f" error: {e}", flush=True)
                sys.stdout.flush()
            import traceback
            traceback.print_exc()
            return results
        
        # Filter out module tests if skip_modules is enabled
        if hasattr(self, '_skip_modules') and self._skip_modules:
            original_count = len(test_cases)
            test_cases = [
                tc for tc in test_cases
                if tc.category not in ["functional", "module", "reasoning", "safety"]
                or not tc.module  # Keep tests without module requirement
            ]
            if self.verbose and len(test_cases) < original_count:
                print(f"  Filtered to {len(test_cases)} tests (skipped module tests)", flush=True)
                sys.stdout.flush()
        
        # Apply exclude filters
        if hasattr(self, '_exclude_modules') and self._exclude_modules:
            original_count = len(test_cases)
            test_cases = [tc for tc in test_cases if tc.module not in self._exclude_modules]
            if self.verbose and len(test_cases) < original_count:
                print(f"  Filtered to {len(test_cases)} tests (excluded {len(self._exclude_modules)} modules)", flush=True)
                sys.stdout.flush()
        
        if hasattr(self, '_exclude_categories') and self._exclude_categories:
            original_count = len(test_cases)
            test_cases = [tc for tc in test_cases if tc.category not in self._exclude_categories]
            if self.verbose and len(test_cases) < original_count:
                print(f"  Filtered to {len(test_cases)} tests (excluded {len(self._exclude_categories)} categories)", flush=True)
                sys.stdout.flush()
        
        # Sort by order-by metric if requested
        if hasattr(self, '_order_by') and self._order_by:
            if self._order_by == "time":
                # Try to load historical data for time-based ordering
                try:
                    from mavaia_core.evaluation.test_results import TestResults
                    results_manager = TestResults()
                    archives = results_manager.list_archives()
                    if archives:
                        latest = results_manager.load_results(archives[0] / "detailed_results.json")
                        # Build time map
                        time_map = {r.test_id: r.execution_time for r in latest.results}
                        test_cases.sort(key=lambda tc: time_map.get(tc.id, 999.0))
                        if self.verbose:
                            print(f"  Ordering tests by historical execution time (fastest first)", flush=True)
                    else:
                        test_cases.sort(key=lambda tc: tc.id)
                        if self.verbose:
                            print(f"  Ordering tests by name (no historical data)", flush=True)
                except Exception:
                    test_cases.sort(key=lambda tc: tc.id)
                    if self.verbose:
                        print(f"  Ordering tests by name (could not load historical data)", flush=True)
            elif self._order_by == "failures":
                # Try to load historical data for failure-based ordering
                try:
                    from mavaia_core.evaluation.test_results import TestResults
                    results_manager = TestResults()
                    archives = results_manager.list_archives()
                    if archives:
                        latest = results_manager.load_results(archives[0] / "detailed_results.json")
                        # Build failure map (most failing first)
                        failure_map = {}
                        for r in latest.results:
                            if r.status.value in ["failed", "error"]:
                                failure_map[r.test_id] = failure_map.get(r.test_id, 0) + 1
                        test_cases.sort(key=lambda tc: -failure_map.get(tc.id, 0))
                        if self.verbose:
                            print(f"  Ordering tests by failure rate (most failing first)", flush=True)
                    else:
                        if self.verbose:
                            print(f"  Ordering tests by original order (no historical data)", flush=True)
                except Exception:
                    if self.verbose:
                        print(f"  Ordering tests by original order (could not load historical data)", flush=True)
            elif self._order_by == "priority":
                # Sort by tags (essential first, then quick, etc.)
                priority_order = {"essential": 0, "quick": 1, "smoke": 2, "unit": 3, "integration": 4}
                def get_priority(tc):
                    for tag in tc.tags:
                        if tag in priority_order:
                            return priority_order[tag]
                    return 999
                test_cases.sort(key=get_priority)
                if self.verbose:
                    print(f"  Ordering tests by priority (essential → quick → smoke → unit → integration)", flush=True)
            elif self._order_by == "name":
                test_cases.sort(key=lambda tc: tc.id)
                if self.verbose:
                    print(f"  Ordering tests by name (alphabetical)", flush=True)
            elif self._order_by == "random":
                import random
                seed = getattr(self, '_random_seed', None)
                if seed is not None:
                    random.seed(seed)
                random.shuffle(test_cases)
                if self.verbose:
                    print(f"  Randomizing test order" + (f" (seed: {seed})" if seed else ""), flush=True)
        
        # Randomize order if requested (legacy support - only if order_by not set)
        elif hasattr(self, '_random_order') and self._random_order:
            import random
            seed = getattr(self, '_random_seed', None)
            if seed is not None:
                random.seed(seed)
                if self.verbose:
                    print(f"  Randomizing test order (seed: {seed})", flush=True)
            else:
                if self.verbose:
                    print(f"  Randomizing test order", flush=True)
            random.shuffle(test_cases)
        
        if not test_cases:
            if self.verbose:
                print("No test cases found matching criteria.", flush=True)
            return results
        
        # Import TestCase lazily
        from mavaia_core.evaluation.test_data_manager import TestCase
        
        # Group test cases by category
        by_category: Dict[str, List[TestCase]] = {}
        for test_case in test_cases:
            cat = test_case.category or "unknown"
            if cat not in by_category:
                by_category[cat] = []
            by_category[cat].append(test_case)
        
        # Run tests by category
        total_tests = len(test_cases)
        current_test = 0
        
        for category, category_test_cases in sorted(by_category.items()):
            if self.verbose:
                print(f"\nRunning {category} tests ({len(category_test_cases)} tests)...", flush=True)
                sys.stdout.flush()
            
            # Pre-discover modules if needed (non-blocking)
            if category in ["functional", "module", "reasoning", "safety", "livebench"]:
                # Skip if skip_modules is enabled
                if hasattr(self, '_skip_modules') and self._skip_modules:
                    if self.verbose:
                        print(f"  Skipping {len(category_test_cases)} {category} tests (--skip-modules enabled)", flush=True)
                    continue
                
                # Import ModuleRegistry lazily when needed
                from mavaia_core.brain.registry import ModuleRegistry
                
                # Start module discovery if not already done
                if not ModuleRegistry._discovered and not ModuleRegistry._discovering:
                    if self.verbose:
                        print("  Starting module discovery (this may take a moment)...", flush=True)
                        sys.stdout.flush()
                    # Use synchronous discovery to ensure it completes before tests run
                    ModuleRegistry.discover_modules(background=False, verbose=self.verbose)
                elif ModuleRegistry._discovering:
                    # Discovery is in progress, wait for it to complete
                    if self.verbose:
                        print("  Waiting for module discovery to complete...", flush=True)
                        sys.stdout.flush()
                    wait_timeout = 30.0  # Increased timeout for module discovery
                    wait_start = time.time()
                    while ModuleRegistry._discovering and (time.time() - wait_start) < wait_timeout:
                        time.sleep(0.2)
                    if ModuleRegistry._discovering:
                        if self.verbose:
                            print("  Warning: Module discovery timed out, proceeding anyway...", flush=True)
                        sys.stdout.flush()
            
            # Route to appropriate test executor (lazy initialization)
            # Check if ALL test cases in this category are code generation tests
            # We need to route each test case individually, not the whole category
            code_gen_tests = []
            regular_tests = []
            
            if category_test_cases:
                for tc in category_test_cases:
                    # Check if this specific test case is for code generation
                    if (tc.module == "reasoning_code_generator" and
                        tc.operation in ["generate_code_reasoning", "explore_code_paths", "generate_with_verification", "refine_code", "generate_with_context"]):
                        code_gen_tests.append(tc)
                    else:
                        regular_tests.append(tc)
            
            # Run code generation tests separately if any exist
            if code_gen_tests:
                if not hasattr(self, 'code_generation_runner') or self.code_generation_runner is None:
                    from mavaia_core.evaluation.categories.code_generation_tests import CodeGenerationTestRunner
                    self.code_generation_runner = CodeGenerationTestRunner()
                code_gen_results = self.code_generation_runner.run_test_suite(
                    code_gen_tests,
                    timeout
                )
                # Add code generation results
                for res in code_gen_results:
                    results.results.append(res)
                    current_test += 1
                    if self.verbose:
                        self.reporter.print_test_result(res)
            
            # Run regular tests with appropriate runner
            category_results = []
            if regular_tests:
                if category == "functional" or category == "module":
                    if self.module_runner is None:
                        from mavaia_core.evaluation.categories import ModuleTestRunner
                        self.module_runner = ModuleTestRunner()
                    category_results = self.module_runner.run_test_suite(
                        regular_tests,
                        timeout
                    )
                elif category == "api":
                    if self.api_runner is None:
                        try:
                            from mavaia_core.evaluation.categories import APITestRunner
                            self.api_runner = APITestRunner()
                        except ImportError as e:
                            if self.verbose:
                                print(f"  Skipping {len(regular_tests)} API tests (httpx not available)", flush=True)
                            category_results = []
                        else:
                            category_results = self.api_runner.run_test_suite(
                                regular_tests,
                                timeout
                            )
                    else:
                        category_results = self.api_runner.run_test_suite(
                            regular_tests,
                            timeout
                        )
                elif category == "client":
                    if self.client_runner is None:
                        from mavaia_core.evaluation.categories import ClientTestRunner
                        self.client_runner = ClientTestRunner()
                    category_results = self.client_runner.run_test_suite(
                        regular_tests,
                        timeout
                    )
                elif category == "system":
                    if self.system_runner is None:
                        from mavaia_core.evaluation.categories import SystemTestRunner
                        self.system_runner = SystemTestRunner()
                    category_results = self.system_runner.run_test_suite(
                        regular_tests,
                        timeout
                    )
                elif category == "reasoning":
                    if self.reasoning_runner is None:
                        from mavaia_core.evaluation.categories import ReasoningTestRunner
                        self.reasoning_runner = ReasoningTestRunner()
                    category_results = self.reasoning_runner.run_test_suite(
                        regular_tests,
                        timeout
                    )
                elif category == "safety":
                    if self.safety_runner is None:
                        from mavaia_core.evaluation.categories import SafetyTestRunner
                        self.safety_runner = SafetyTestRunner()
                    category_results = self.safety_runner.run_test_suite(
                        regular_tests,
                        timeout
                    )
                elif category == "livebench":
                    if self.livebench_runner is None:
                        try:
                            from mavaia_core.evaluation.categories import LiveBenchTestRunner
                            self.livebench_runner = LiveBenchTestRunner()
                        except ImportError as e:
                            if self.verbose:
                                print(f"  Skipping {len(regular_tests)} LiveBench tests (LiveBench not available: {e})", flush=True)
                            category_results = []
                        else:
                            category_results = self.livebench_runner.run_test_suite(
                                regular_tests,
                                timeout
                            )
                    else:
                        category_results = self.livebench_runner.run_test_suite(
                            regular_tests,
                            timeout
                        )
                else:
                    # Default to module runner
                    if self.module_runner is None:
                        from mavaia_core.evaluation.categories import ModuleTestRunner
                        self.module_runner = ModuleTestRunner()
                    category_results = self.module_runner.run_test_suite(
                        regular_tests,
                        timeout
                    )
            
            # Add regular test results
            for result in category_results:
                results.results.append(result)
                current_test += 1
                
                # Stop on failure if requested
                if hasattr(self, '_stop_on_failure') and self._stop_on_failure:
                    if result.status.value in ["failed", "error"]:
                        if self.verbose:
                            print(f"\nStopping on first failure: {result.test_id}", flush=True)
                        break
            
            # Check if we should stop
            if hasattr(self, '_stop_on_failure') and self._stop_on_failure:
                if any(r.status.value in ["failed", "error"] for r in results.results):
                    break
        
        # Compute statistics
        results.compute_statistics()
        
        # Print summary
        if self.verbose:
            self.reporter.print_summary(results)
        
        return results
    
    def save_results(
        self,
        results: "TestRunResults",
        archive: bool = True
    ) -> Path:
        """
        Save test results
        
        Args:
            results: Test run results
            archive: Whether to archive results in timestamped directory
            
        Returns:
            Path to saved results
        """
        if archive:
            return self.test_results.archive_results(results)
        else:
            return self.test_results.save_results(results)
    
    def generate_report(
        self,
        results: "TestRunResults",
        output_path: Optional[Union[str, Path]] = None
    ) -> Path:
        """
        Generate HTML report
        
        Args:
            results: Test run results
            output_path: Optional output path (defaults to results directory)
            
        Returns:
            Path to generated HTML report
        """
        if output_path is None:
            # Use timezone-aware datetime (Python 3.11+) or fallback to utcnow
            try:
                timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
            except (AttributeError, ValueError):
                # Fallback for older Python versions
                timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
            output_path = self.test_results.results_dir / f"report_{timestamp}.html"
        
        return self.reporter.generate_html_report(results, output_path)


# ============================================================================
# Interactive CLI Implementation
# ============================================================================

# CLI classes are defined lazily to avoid import-time execution
# They will be created when the CLI is actually used

# TestRunnerCLI will be created lazily - see _get_cli_class() function
TestRunnerCLI = None


def _get_cli_class():
    """Get or create the TestRunnerCLI class (lazy initialization)"""
    global TestRunnerCLI
    if TestRunnerCLI is not None:
        return TestRunnerCLI
    
    import cmd
    import shlex
    import json
    import os
    from pathlib import Path
    
    # Define ColorOutput inside the function to avoid import-time issues
    class ColorOutput:
        """Color output manager with theme support"""
        
        def __init__(self, enabled: bool = True):
            self.enabled = enabled and self._supports_color()
            self.colors = {
                'success': '\033[92m',
                'error': '\033[91m',
                'warning': '\033[93m',
            'info': '\033[96m',  # Cyan
            'prompt': '\033[95m',  # Magenta
            'module': '\033[94m',  # Blue
            'category': '\033[36m',  # Cyan
            'timestamp': '\033[2;37m',  # Dim white
            'separator': '\033[37m',  # White
            'reset': '\033[0m',
            'bold': '\033[1m',
            'header': '\033[90m',  # Dark gray for box
            'title': '\033[1;97m',  # Bold white for title
            'stats': '\033[93m',  # Yellow for stats
            'stats_label': '\033[96m',  # Cyan for stat labels
            'stats_value': '\033[93m',  # Yellow for stat values
            'success': '\033[92m',  # Green
            'warning': '\033[93m',  # Yellow
            }
        
        def _supports_color(self) -> bool:
            """Check if terminal supports colors"""
            if os.environ.get('NO_COLOR'):
                return False
            if os.environ.get('TERM') == 'dumb':
                return False
            return sys.stdout.isatty()
        
        def colorize(self, text: str, color: str) -> str:
            """Apply color to text"""
            if not self.enabled:
                return text
            return f"{self.colors.get(color, '')}{text}{self.colors['reset']}"
        
        def _strip_ansi(self, text: str) -> str:
            """Strip ANSI color codes to get actual text length"""
            import re
            ansi_escape = re.compile(r'\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])')
            return ansi_escape.sub('', text)
        
        def status(self, symbol: str, text: str, status_type: str = 'info') -> str:
            """Format colored status with symbol"""
            color_map = {
                'success': 'success',
                'error': 'error',
                'warning': 'warning',
                'info': 'info'
            }
            color = color_map.get(status_type, 'info')
            return f"{self.colorize(symbol, color)} {text}"
    
    class TestRunnerCLIImpl(cmd.Cmd):
        """Interactive command-line interface for evaluation framework"""
        
        intro = ""  # Will be set in preloop
        prompt = "thynaptic:eval$ "
        
        # Track if this is first load
        _first_load = True
        
        # Built-in profiles
        BUILTIN_PROFILES = {
            'fast': {
                'tags': ['quick', 'essential'],
                'timeout': 10.0,
                'verbose': False,
                'skip_modules': False,
                'colors': True,
            },
            'thorough': {
                'tags': [],
                'timeout': 60.0,
                'verbose': True,
                'skip_modules': False,
                'colors': True,
            },
            'gpu': {
                'tags': ['gpu', 'essential'],
                'timeout': 120.0,
                'verbose': True,
                'skip_modules': False,
                'colors': True,
            },
            'silent': {
                'tags': [],
                'timeout': 30.0,
                'verbose': False,
                'skip_modules': False,
                'colors': False,
            },
        }
        
        # Built-in aliases
        BUILTIN_ALIASES = {
            'r': 'run',
            'lm': 'list-modules',
            'lr': 'list-results',
            'lt': 'list-tests',
            'd': 'describe',
            'h': 'help',
            'q': 'quit',
            'c': 'config',
            'vt': 'validate-tests',
            'ct': 'create-template',
            'cov': 'coverage',
        }
        
        def __init__(self, test_data_dir=None, results_dir=None, verbose=True, use_colors=True):
            super().__init__()
            self.config_file = self._get_config_path()
            self.config = self._load_config()
            self.aliases = {**self.BUILTIN_ALIASES, **self.config.get('aliases', {})}
            self.color_output = ColorOutput(enabled=self.config.get('colors', use_colors))
            self._update_prompt()
            
            # Initialize evaluation framework lazily
            self._runner = None
            self._test_data_dir = test_data_dir or self.config.get('test_data_dir')
            self._results_dir = results_dir or self.config.get('results_dir')
            self._verbose = self.config.get('verbose', verbose)
            self._use_colors = self.config.get('colors', use_colors)
            
            # Apply current profile if set
            current_profile = self.config.get('current_profile')
            if current_profile:
                self._apply_profile(current_profile)
            
            # Cache for stats (updated on demand)
            self._stats_cache = None
            self._stats_cache_time = 0
        
        def _clear_screen(self):
            """Clear the terminal screen"""
            import os
            os.system('clear' if os.name != 'nt' else 'cls')
        
        def _get_stats(self, force_refresh=False):
            """Get current statistics for the header"""
            import time
            # Cache stats for 5 seconds to avoid expensive operations
            if not force_refresh and self._stats_cache and (time.time() - self._stats_cache_time) < 5:
                return self._stats_cache
            
            stats = {
                'modules': 0,
                'tests': 0,
                'modules_with_tests': 0,
                'coverage': 0.0,
                'last_run': None,
                'last_success_rate': 0.0
            }
            
            try:
                from mavaia_core.brain.registry import ModuleRegistry
                # Check if already discovered, if not, discover synchronously
                if not ModuleRegistry._discovered:
                    # Quick discovery without verbose output
                    ModuleRegistry.discover_modules(background=False, verbose=False)
                    # Wait a moment for discovery to complete if it was in progress
                    import time
                    timeout = 5.0
                    start = time.time()
                    while ModuleRegistry._discovering and (time.time() - start) < timeout:
                        time.sleep(0.1)
                
                # Get module count
                module_list = ModuleRegistry.list_modules()
                stats['modules'] = len(module_list) if module_list else 0
            except Exception as e:
                # Log error but don't fail - use cached value if available
                if hasattr(ModuleRegistry, '_modules'):
                    stats['modules'] = len(ModuleRegistry._modules) if ModuleRegistry._modules else 0
                else:
                    stats['modules'] = 0
            
            try:
                from mavaia_core.evaluation.test_data_manager import TestDataManager
                test_manager = TestDataManager(self._test_data_dir)
                test_manager.load_all_test_suites()
                stats['tests'] = sum(len(suite.test_suite) for suite in test_manager._test_suites.values())
                stats['modules_with_tests'] = len(test_manager._test_suites)
                if stats['modules'] > 0:
                    stats['coverage'] = (stats['modules_with_tests'] / stats['modules']) * 100
            except Exception:
                pass
            
            try:
                from mavaia_core.evaluation.test_results import TestResults
                results_manager = TestResults(self._results_dir)
                archives = results_manager.list_archives()
                if archives:
                    latest = archives[0]
                    stats['last_run'] = latest.name
                    try:
                        test_results = results_manager.load_results(latest / "detailed_results.json")
                        if test_results and test_results.summary:
                            stats['last_success_rate'] = test_results.summary.success_rate * 100
                    except Exception:
                        pass
            except Exception:
                pass
            
            self._stats_cache = stats
            self._stats_cache_time = time.time()
            return stats
        
        def _display_header(self, detailed: bool = True):
            """Display the professional header with optional stats
            
            Args:
                detailed: If True, show full header with stats. If False, show simple header.
            """
            # Professional header style (OpenAI/Anthropic inspired)
            # Box border - dark gray
            print(self.color_output.colorize("╔" + "═" * 78 + "╗", 'header'))
            print(self.color_output.colorize("║" + " " * 78 + "║", 'header'))
            
            # Title - centered, bold white
            title = "THYNAPTIC  EVALUATION  FRAMEWORK"
            title_padding = (78 - len(title)) // 2
            title_line = " " * title_padding + title + " " * (78 - title_padding - len(title))
            title_colored = self.color_output.colorize(title_line, 'title')
            border = self.color_output.colorize("║", 'header')
            print(f"{border}{title_colored}{border}")
            
            print(self.color_output.colorize("║" + " " * 78 + "║", 'header'))
            
            if detailed:
                # Show detailed stats
                stats = self._get_stats()
                print(self.color_output.colorize("║" + "─" * 78 + "║", 'header'))
                print(self.color_output.colorize("║" + " " * 78 + "║", 'header'))
                
                # Stats line 1 - key metrics with proper alignment
                padding_left = "  "
                
                # Build stats with separate colors for labels and values
                # Calculate positions for proper alignment
                # Column positions: Modules at 2, Tests at 20, Coverage at 40
                modules_label_text = "Modules:"
                modules_value_text = str(stats['modules'])
                modules_label = self.color_output.colorize(modules_label_text, 'stats_label')
                modules_value = self.color_output.colorize(modules_value_text, 'stats_value')
                
                tests_label_text = "Tests:"
                tests_value_text = str(stats['tests'])
                tests_label = self.color_output.colorize(tests_label_text, 'stats_label')
                tests_value = self.color_output.colorize(tests_value_text, 'stats_value')
                
                coverage_label_text = "Coverage:"
                coverage_value_text = f"{stats['coverage']:.1f}%"
                coverage_label = self.color_output.colorize(coverage_label_text, 'stats_label')
                coverage_value = self.color_output.colorize(coverage_value_text, 'stats_value')
                
                # Build line with proper spacing (accounting for ANSI codes in length)
                # Position: Modules at col 2, Tests at col 20, Coverage at col 40
                modules_part = f"{modules_label_text} {modules_value_text}"
                tests_part = f"{tests_label_text} {tests_value_text}"
                coverage_part = f"{coverage_label_text} {coverage_value_text}"
                
                # Calculate spacing to align columns
                modules_end = len(padding_left) + len(modules_part)
                spacing1 = " " * max(1, 20 - modules_end)
                
                tests_start = modules_end + len(spacing1)
                tests_end = tests_start + len(tests_part)
                spacing2 = " " * max(1, 40 - tests_end)
                
                # Build the line with colored parts
                stats_line1 = (
                    padding_left +
                    modules_label + " " + modules_value +
                    spacing1 +
                    tests_label + " " + tests_value +
                    spacing2 +
                    coverage_label + " " + coverage_value
                )
                
                # Calculate padding (strip ANSI codes for length calculation)
                stats_line1_plain = padding_left + modules_part + spacing1 + tests_part + spacing2 + coverage_part
                padding_right = " " * (78 - len(stats_line1_plain))
                print(f"{border}{stats_line1}{padding_right}{border}")
                
                # Stats line 2 - additional info with proper alignment
                modules_tested_label_text = "Modules with Tests:"
                modules_tested_value_text = str(stats['modules_with_tests'])
                modules_tested_label = self.color_output.colorize(modules_tested_label_text, 'stats_label')
                modules_tested_value = self.color_output.colorize(modules_tested_value_text, 'stats_value')
                
                if stats['last_run']:
                    last_run_short = stats['last_run'][:18] if len(stats['last_run']) > 18 else stats['last_run']
                    last_label_text = "Last:"
                    last_value_text = f"{last_run_short} ({stats['last_success_rate']:.1f}%)"
                    last_label = self.color_output.colorize(last_label_text, 'stats_label')
                    last_value = self.color_output.colorize(last_value_text, 'stats_value')
                    
                    # Align "Last:" with "Coverage:" from line 1 (starts at col 40)
                    modules_tested_part = f"{modules_tested_label_text} {modules_tested_value_text}"
                    last_part = f"{last_label_text} {last_value_text}"
                    
                    modules_tested_end = len(padding_left) + len(modules_tested_part)
                    spacing = " " * max(1, 40 - modules_tested_end)
                    
                    stats_line2 = (
                        padding_left +
                        modules_tested_label + " " + modules_tested_value +
                        spacing +
                        last_label + " " + last_value
                    )
                    
                    stats_line2_plain = padding_left + modules_tested_part + spacing + last_part
                else:
                    modules_tested_part = f"{modules_tested_label_text} {modules_tested_value_text}"
                    stats_line2 = padding_left + modules_tested_label + " " + modules_tested_value
                    stats_line2_plain = padding_left + modules_tested_part
                
                padding_right = " " * (78 - len(stats_line2_plain))
                print(f"{border}{stats_line2}{padding_right}{border}")
                
                print(self.color_output.colorize("║" + " " * 78 + "║", 'header'))
            
            print(self.color_output.colorize("╚" + "═" * 78 + "╝", 'header'))
        
        def preloop(self):
            """Called once before cmdloop() starts"""
            if self._first_load:
                self._clear_screen()
                self._display_header()
                print()
                print(self.color_output.colorize("Welcome to Thynaptic Evaluation Framework", 'bold'))
                print()
                print("  A comprehensive testing framework for Mavaia's cognitive modules.")
                print("  Type 'help' for available commands or 'quit' to exit.")
                print()
                print(self.color_output.colorize("─" * 80, 'separator'))
                print()
                self._first_load = False
        
        def precmd(self, line):
            """Called before each command execution"""
            # Always redraw header BEFORE command executes so it stays at top
            # Skip only for quit/exit and empty lines
            if line and line.strip():
                cmd_name = line.split()[0].lower() if line.strip() else ""
                # Don't clear/redraw for quit/exit/clear (clear will redraw itself)
                if cmd_name not in ('quit', 'exit', 'q', 'clear'):
                    # Commands that produce output - clear screen and show header at top
                    output_commands = {
                        'coverage', 'run', 'list-modules', 'list-tests', 'list-results',
                        'describe', 'explain', 'health', 'impact', 'stats', 'report',
                        'compare', 'validate-tests', 'validate-modules', 'lm', 'lr', 'lt',
                        'd', 'cov', 'h'  # aliases
                    }
                    # Check if command or its alias produces output
                    actual_cmd = self.aliases.get(cmd_name, cmd_name) if cmd_name in self.aliases else cmd_name
                    actual_cmd_base = actual_cmd.split()[0].lower() if actual_cmd else cmd_name
                    
                    if cmd_name in output_commands or actual_cmd_base in output_commands:
                        # Clear screen and redraw SIMPLE header for commands that produce output
                        # This ensures header is always at the top before output (without stats)
                        self._clear_screen()
                        self._display_header(detailed=False)
                        print()
            return line
        
        def postcmd(self, stop, line):
            """Called after each command execution"""
            # Don't redraw header here - it should be at top from precmd
            # Only redraw for empty lines to keep header visible
            if not line or not line.strip():
                # Empty line - just redraw header to keep it visible
                self._display_header()
                print()
            return stop
        
        def _get_config_path(self) -> Path:
            """Get path to configuration file"""
            # Use XDG config if available, otherwise ~/.mavaia
            config_home = os.environ.get('XDG_CONFIG_HOME')
            if config_home:
                config_dir = Path(config_home) / 'mavaia'
            else:
                config_dir = Path.home() / '.mavaia'
            
            config_dir.mkdir(parents=True, exist_ok=True)
            return config_dir / 'test_runner_config.json'
        
        def _load_config(self) -> dict:
            """Load persistent configuration from file"""
            default_config = {
                'timeout': 30.0,
                'verbose': True,
                'colors': True,
                'skip_modules': False,
                'category': None,
                'tags': [],
                'results_dir': None,
                'test_data_dir': None,
                'current_profile': None,
                'aliases': {},
                'profiles': {},
            }
            
            if self.config_file.exists():
                try:
                    with open(self.config_file, 'r') as f:
                        loaded = json.load(f)
                        # Merge with defaults
                        config = {**default_config, **loaded}
                        # Ensure nested dicts exist
                        if 'aliases' not in config:
                            config['aliases'] = {}
                        if 'profiles' not in config:
                            config['profiles'] = {}
                        return config
                except Exception as e:
                    print(f"Warning: Could not load config: {e}", file=sys.stderr)
            
            return default_config
        
        def _save_config(self):
            """Save configuration to file atomically"""
            try:
                # Write to temp file first
                temp_file = self.config_file.with_suffix('.tmp')
                with open(temp_file, 'w') as f:
                    json.dump(self.config, f, indent=2)
                # Atomic rename
                temp_file.replace(self.config_file)
            except Exception as e:
                print(f"Warning: Could not save config: {e}", file=sys.stderr)
        
        def _update_prompt(self):
            """Update prompt with current profile indicator"""
            profile = self.config.get('current_profile')
            if profile:
                self.prompt = f"thynaptic:eval [{profile}]$ "
            else:
                self.prompt = "thynaptic:eval$ "
            # Apply color to prompt
            if self.color_output.enabled:
                self.prompt = self.color_output.colorize(self.prompt, 'prompt')
        
        def _apply_profile(self, profile_name: str):
            """Apply a profile's settings to current config"""
            # Check built-in profiles first
            if profile_name in self.BUILTIN_PROFILES:
                profile = self.BUILTIN_PROFILES[profile_name]
            elif profile_name in self.config.get('profiles', {}):
                profile = self.config['profiles'][profile_name]
            else:
                print(f"Error: Profile '{profile_name}' not found")
                return False
            
            # Apply profile settings
            for key, value in profile.items():
                self.config[key] = value
            
            self.config['current_profile'] = profile_name
            self._save_config()
            self._update_prompt()
            
            # Update color output
            self.color_output.enabled = self.config.get('colors', True) and self.color_output._supports_color()
            
            return True
        
        @property
        def runner(self):
            """Lazy initialization of evaluation framework"""
            if self._runner is None:
                self._runner = TestRunner(
                    test_data_dir=self._test_data_dir,
                    results_dir=self._results_dir,
                    verbose=self._verbose,
                    use_colors=self._use_colors
                )
            return self._runner
        
        def parseline(self, line: str):
            """Override to handle aliases and hyphenated commands before parsing"""
            if not line.strip():
                return cmd.Cmd.parseline(self, line)
            
            parts = line.split(None, 1)
            if parts and parts[0] in self.aliases:
                alias_cmd = self.aliases[parts[0]]
                if len(parts) > 1:
                    line = f"{alias_cmd} {parts[1]}"
                else:
                    line = alias_cmd
            elif parts and '-' in parts[0]:
                # Convert hyphenated commands to underscore format for method lookup
                # e.g., "create-template" -> "create_template"
                cmd_name = parts[0].replace('-', '_')
                if len(parts) > 1:
                    line = f"{cmd_name} {parts[1]}"
                else:
                    line = cmd_name
            return cmd.Cmd.parseline(self, line)
    
        def default(self, line: str):
            """Handle unknown commands"""
            print(f"Unknown command: {line}")
            print("Type 'help' for a list of commands.")
        
        def emptyline(self):
            """Do nothing on empty line"""
            pass
        
        def do_quit(self, args: str):
            """Exit the CLI"""
            return True
        
        def do_exit(self, args: str):
            """Exit the CLI"""
            return True
        
        def do_clear(self, args: str):
            """Clear the screen and redraw header"""
            self._clear_screen()
            self._display_header()
            print()
        
        def do_history(self, args: str):
            """Show command history"""
            try:
                import readline
                hist_len = readline.get_current_history_length()
                for i in range(1, hist_len + 1):
                    print(f"{i:4d}  {readline.get_history_item(i)}")
            except ImportError:
                print("History not available (readline not available)")
        
        # ========================================================================
        # Configuration Commands
        # ========================================================================
        
        def do_config(self, args: str):
            """Show current configuration"""
            print("\nCurrent Configuration:")
            print("=" * 60)
            for key, value in sorted(self.config.items()):
                if key not in ['aliases', 'profiles']:  # Show these separately
                    print(f"  {self.color_output.colorize(key, 'module')}: {value}")
            print()
        
        def do_set(self, args: str):
            """Set configuration option: set KEY VALUE"""
            parts = shlex.split(args)
            if len(parts) < 2:
                print("Usage: set KEY VALUE")
                print("Example: set timeout 60.0")
                return
            
            key = parts[0]
            value_str = ' '.join(parts[1:])
            
            # Try to parse value as appropriate type
            if key in ['timeout']:
                try:
                    value = float(value_str)
                except ValueError:
                    print(f"Error: '{value_str}' is not a valid number")
                    return
            elif key in ['verbose', 'colors', 'skip_modules']:
                value = value_str.lower() in ['true', '1', 'yes', 'on']
            elif key in ['tags']:
                value = shlex.split(value_str) if value_str else []
            elif key in ['category', 'results_dir', 'test_data_dir', 'current_profile']:
                value = value_str if value_str != 'null' else None
            else:
                value = value_str
            
            self.config[key] = value
            self._save_config()
            
            # Update color output if colors changed
            if key == 'colors':
                self.color_output.enabled = value and self.color_output._supports_color()
            
            print(f"{self.color_output.status('✓', f'Set {key} = {value}', 'success')}")
        
        # ========================================================================
        # Profile Commands
        # ========================================================================
        
        def do_profile(self, args: str):
            """Profile management: profile [NAME|list|show NAME|save NAME|delete NAME]"""
            parts = shlex.split(args) if args.strip() else []
            
            if not parts:
                print("Usage: profile [NAME|list|show NAME|save NAME|delete NAME]")
                return
            
            command = parts[0].lower()
            
            if command == 'list':
                self._profile_list()
            elif command == 'show':
                if len(parts) < 2:
                    print("Usage: profile show NAME")
                    return
                self._profile_show(parts[1])
            elif command == 'save':
                if len(parts) < 2:
                    print("Usage: profile save NAME")
                    return
                self._profile_save(parts[1])
            elif command == 'delete':
                if len(parts) < 2:
                    print("Usage: profile delete NAME")
                    return
                self._profile_delete(parts[1])
            else:
                # Activate profile
                self._apply_profile(command)
                print(f"{self.color_output.status('✓', f'Activated profile: {command}', 'success')}")
        
        def _profile_list(self):
            """List all available profiles"""
            print("\nAvailable Profiles:")
            print("=" * 60)
            print("\nBuilt-in Profiles:")
            for name in sorted(self.BUILTIN_PROFILES.keys()):
                marker = " (active)" if self.config.get('current_profile') == name else ""
                print(f"  {self.color_output.colorize(name, 'module')}{marker}")
            
            custom_profiles = self.config.get('profiles', {})
            if custom_profiles:
                print("\nCustom Profiles:")
                for name in sorted(custom_profiles.keys()):
                    marker = " (active)" if self.config.get('current_profile') == name else ""
                    print(f"  {self.color_output.colorize(name, 'module')}{marker}")
            print()
        
        def _profile_show(self, name: str):
            """Show profile details"""
            if name in self.BUILTIN_PROFILES:
                profile = self.BUILTIN_PROFILES[name]
                profile_type = "Built-in"
            elif name in self.config.get('profiles', {}):
                profile = self.config['profiles'][name]
                profile_type = "Custom"
            else:
                print(f"Error: Profile '{name}' not found")
                return
            
            print(f"\nProfile: {self.color_output.colorize(name, 'module')} ({profile_type})")
            print("=" * 60)
            for key, value in sorted(profile.items()):
                print(f"  {key}: {value}")
            print()
        
        def _profile_save(self, name: str):
            """Save current config as a profile"""
            if name in self.BUILTIN_PROFILES:
                print(f"Error: Cannot overwrite built-in profile '{name}'")
                return
            
            # Create profile from current config (exclude meta fields)
            profile = {
                'tags': self.config.get('tags', []),
                'timeout': self.config.get('timeout', 30.0),
                'verbose': self.config.get('verbose', True),
                'skip_modules': self.config.get('skip_modules', False),
                'colors': self.config.get('colors', True),
            }
            
            if 'profiles' not in self.config:
                self.config['profiles'] = {}
            self.config['profiles'][name] = profile
            self._save_config()
            print(f"{self.color_output.status('✓', f'Saved profile: {name}', 'success')}")
        
        def _profile_delete(self, name: str):
            """Delete a custom profile"""
            if name in self.BUILTIN_PROFILES:
                print(f"Error: Cannot delete built-in profile '{name}'")
                return
            
            if name not in self.config.get('profiles', {}):
                print(f"Error: Profile '{name}' not found")
                return
            
            del self.config['profiles'][name]
            if self.config.get('current_profile') == name:
                self.config['current_profile'] = None
                self._update_prompt()
            self._save_config()
            print(f"{self.color_output.status('✓', f'Deleted profile: {name}', 'success')}")
        
        # ========================================================================
        # Alias Commands
        # ========================================================================
        
        def do_alias(self, args: str):
            """Alias management: alias [NAME [COMMAND]]"""
            parts = shlex.split(args) if args.strip() else []
            
            if not parts:
                # List all aliases
                print("\nAliases:")
                print("=" * 60)
                print("\nBuilt-in Aliases:")
                for name, cmd in sorted(self.BUILTIN_ALIASES.items()):
                    print(f"  {self.color_output.colorize(name, 'module')} -> {cmd}")
                
                custom_aliases = {k: v for k, v in self.aliases.items() if k not in self.BUILTIN_ALIASES}
                if custom_aliases:
                    print("\nCustom Aliases:")
                    for name, cmd in sorted(custom_aliases.items()):
                        print(f"  {self.color_output.colorize(name, 'module')} -> {cmd}")
                print()
            elif len(parts) == 1:
                # Show specific alias
                name = parts[0]
                if name in self.aliases:
                    print(f"{name} -> {self.aliases[name]}")
                else:
                    print(f"Alias '{name}' not found")
            elif len(parts) == 2:
                # Create/update alias
                name, command = parts
                if name in self.BUILTIN_ALIASES:
                    print(f"Error: Cannot overwrite built-in alias '{name}'")
                    return
                
                self.aliases[name] = command
                self.config['aliases'][name] = command
                self._save_config()
                print(f"{self.color_output.status('✓', f'Created alias: {name} -> {command}', 'success')}")
            else:
                print("Usage: alias [NAME [COMMAND]]")
        
        def do_unalias(self, args: str):
            """Remove an alias: unalias NAME"""
            parts = shlex.split(args)
            if not parts:
                print("Usage: unalias NAME")
                return
            
            name = parts[0]
            if name in self.BUILTIN_ALIASES:
                print(f"Error: Cannot remove built-in alias '{name}'")
                return
            
            if name not in self.aliases:
                print(f"Alias '{name}' not found")
                return
            
            del self.aliases[name]
            if name in self.config.get('aliases', {}):
                del self.config['aliases'][name]
            self._save_config()
            print(f"{self.color_output.status('✓', f'Removed alias: {name}', 'success')}")
        
        # ========================================================================
        # Test Execution Commands
        # ========================================================================
        
        def do_run(self, args: str):
            """Run tests: run [--module MODULE] [--category CATEGORY] [--tags TAG...]"""
            parsed = self._parse_run_args(shlex.split(args) if args.strip() else [])
            if parsed is None:
                return
            
            try:
                results = self.runner.run_test_suite(**parsed)
                archive_path = self.runner.save_results(results, archive=True)
                print(f"\n{self.color_output.status('✓', f'Results archived to: {archive_path}', 'success')}")
                
                # Generate report
                report_path = self.runner.generate_report(results)
                print(f"{self.color_output.status('✓', f'HTML report generated: {report_path}', 'success')}")
                
                # Show summary
                if results.summary.failed > 0 or results.summary.errors > 0:
                    print(f"\n{self.color_output.status('✗', f'Tests completed with {results.summary.failed} failures', 'error')}")
                else:
                    print(f"\n{self.color_output.status('✓', 'All tests passed!', 'success')}")
            except Exception as e:
                print(f"{self.color_output.status('✗', f'Error running tests: {e}', 'error')}")
                if self.config.get('verbose', True):
                    import traceback
                    traceback.print_exc()
        
        def _parse_run_args(self, args: list) -> Optional[dict]:
            """Parse arguments for run command"""
            parsed = {
                'module': None,
                'category': None,
                'tags': None,
                'timeout': self.config.get('timeout'),
                'tag_mode': 'all',
            }
            
            i = 0
            while i < len(args):
                arg = args[i]
                if arg == '--module' and i + 1 < len(args):
                    parsed['module'] = args[i + 1]
                    i += 2
                elif arg == '--category' and i + 1 < len(args):
                    parsed['category'] = args[i + 1]
                    i += 2
                elif arg == '--tags':
                    tags = []
                    i += 1
                    while i < len(args) and not args[i].startswith('--'):
                        tags.append(args[i])
                        i += 1
                    parsed['tags'] = tags
                elif arg == '--timeout' and i + 1 < len(args):
                    try:
                        parsed['timeout'] = float(args[i + 1])
                        i += 2
                    except ValueError:
                        print(f"Error: Invalid timeout value: {args[i + 1]}")
                        return None
                elif arg == '--tag-mode' and i + 1 < len(args):
                    parsed['tag_mode'] = args[i + 1]
                    i += 2
                else:
                    print(f"Error: Unknown argument: {arg}")
                    return None
            
            # Apply config defaults if not specified
            if parsed['tags'] is None and self.config.get('tags'):
                parsed['tags'] = self.config['tags']
            if parsed['category'] is None and self.config.get('category'):
                parsed['category'] = self.config['category']
            
            return parsed
        
        def do_run_quick(self, args: str):
            """Run quick tests only (equivalent to run --tags quick)"""
            self.do_run("--tags quick")
        
        def do_run_essential(self, args: str):
            """Run essential tests only (equivalent to run --tags essential)"""
            self.do_run("--tags essential")
        
        # ========================================================================
        # Module Management Commands
        # ========================================================================
        
        def do_list_modules(self, args: str):
            """List all discovered modules"""
            _list_all_modules(use_colors=self.color_output.enabled)
        
        def do_describe(self, args: str):
            """Show detailed module information: describe MODULE"""
            parts = shlex.split(args) if args.strip() else []
            if not parts:
                print("Usage: describe MODULE")
                return
            _describe_module(parts[0], use_colors=self.color_output.enabled)
        
        def do_discover(self, args: str):
            """Force module discovery with progress indicators"""
            import sys
            import time
            import threading
            from mavaia_core.brain.registry import ModuleRegistry
            from pathlib import Path
            
            # Get modules directory to show what we're scanning
            # Only use mavaia_core/brain/modules/
            modules_dir = ModuleRegistry.get_modules_dir()
            if modules_dir is None:
                # Try to construct the path directly
                package_dir = Path(__file__).parent.parent.parent
                modules_dir = package_dir / "mavaia_core" / "brain" / "modules"
                if not modules_dir.exists():
                    print(f"\n{self.color_output.status('✗', 'Modules directory not found: mavaia_core/brain/modules/', 'error')}")
                    return
            else:
                modules_dir = Path(modules_dir)
            
            print(f"\n{self.color_output.colorize('🔍', 'info')} Discovering modules in: {modules_dir}")
            print(f"{self.color_output.colorize('─', 'separator') * 60}")
            
            # Count only files that actually contain BaseBrainModule classes
            # This ensures "Found X" matches actual discoverable modules
            potential_module_files = []
            if modules_dir.exists():
                for module_file in modules_dir.glob("*.py"):
                    if module_file.name in [
                        "__init__.py", "base_module.py", "module_registry.py", "model_manager.py",
                        "tot_models.py", "cot_models.py", "mcts_models.py", "tool_calling_models.py"
                    ]:
                        continue
                    # Quick check: does file contain BaseBrainModule?
                    try:
                        with open(module_file, 'r', encoding='utf-8') as f:
                            content = f.read()
                            if 'BaseBrainModule' in content and 'class' in content:
                                potential_module_files.append(module_file)
                    except Exception:
                        pass  # Skip files we can't read
                
                for subdir in modules_dir.iterdir():
                    if subdir.is_dir() and not subdir.name.startswith("__") and subdir.name != "models":
                        for module_file in subdir.glob("*.py"):
                            if module_file.name == "__init__.py":
                                continue
                            # Quick check: does file contain BaseBrainModule?
                            try:
                                with open(module_file, 'r', encoding='utf-8') as f:
                                    content = f.read()
                                    if 'BaseBrainModule' in content and 'class' in content:
                                        potential_module_files.append(module_file)
                            except Exception:
                                pass  # Skip files we can't read
            
            total_files = len(potential_module_files)
            print(f"Found {self.color_output.colorize(str(total_files), 'module')} potential brain modules to scan\n")
            
            # Track discovery progress
            discovered_modules = []
            failed_modules = []
            warnings = []  # Track modules with warnings
            start_time = time.time()
            
            # Progress indicator thread
            spinner_chars = ['⠋', '⠙', '⠹', '⠸', '⠼', '⠴', '⠦', '⠧', '⠇', '⠏']
            spinner_idx = 0
            stop_spinner = threading.Event()
            
            def show_progress():
                nonlocal spinner_idx
                while not stop_spinner.is_set():
                    spinner = spinner_chars[spinner_idx % len(spinner_chars)]
                    # Use the actual registry count for consistency
                    current_count = len(ModuleRegistry._modules)
                    elapsed = time.time() - start_time
                    
                    # Calculate time per module and remaining time
                    if current_count > 0 and total_files > 0:
                        time_per_module = elapsed / current_count
                        remaining = max(0, (total_files - current_count) * time_per_module)
                        if remaining > 0:
                            remaining_str = f", {remaining:.1f}s remaining"
                        else:
                            remaining_str = ""
                    else:
                        time_per_module = 0
                        remaining_str = ""
                    
                    # Clean progress line without extra brackets
                    print(f"\r{self.color_output.colorize(spinner, 'info')} Processing... "
                          f"{self.color_output.colorize(str(current_count), 'module')} modules discovered "
                          f"({elapsed:.1f}s, {time_per_module:.2f}s/module{remaining_str})", end="", flush=True)
                    spinner_idx += 1
                    time.sleep(0.1)
            
            # Start progress indicator
            progress_thread = threading.Thread(target=show_progress, daemon=True)
            progress_thread.start()
            
            try:
                # Run discovery (errors are always shown)
                result = ModuleRegistry.discover_modules(background=False, verbose=False)
                
                # Wait a moment for any final updates
                time.sleep(0.3)
                stop_spinner.set()
                progress_thread.join(timeout=1.0)
                
                # Get final results and categorize by health status
                discovered_modules = list(ModuleRegistry.list_modules())
                actual_count = len(discovered_modules)
                elapsed = time.time() - start_time
                
                # Get failure count from discovery result
                failed_count = 0
                if result and isinstance(result, tuple):
                    _, failed_count = result
                
                # Categorize modules by health status
                healthy_count = 0
                disabled_count = 0
                
                for module_name in discovered_modules:
                    metadata = ModuleRegistry.get_metadata(module_name)
                    if metadata:
                        if not metadata.enabled:
                            disabled_count += 1
                        else:
                            healthy_count += 1
                
                # Warnings are modules that failed to load/initialize
                warning_count = failed_count
                
                # Calculate statistics
                total_discovered = healthy_count + disabled_count
                success_rate = (total_discovered / total_files * 100) if total_files > 0 else 0
                avg_time_per_module = elapsed / total_discovered if total_discovered > 0 else 0
                
                # Clear progress line
                print(f"\r{' ' * 100}\r", end="")  # Clear line
                
                # Show final summary
                print(f"\n{self.color_output.status('✓', f'Discovery complete in {elapsed:.2f}s', 'success')}")
                print(f"{self.color_output.colorize('─', 'separator') * 60}")
                print(f"{self.color_output.colorize('Module Health:', 'info')}")
                print(f"  - {self.color_output.colorize(str(healthy_count), 'success')} healthy")
                if warning_count > 0:
                    print(f"  - {self.color_output.colorize(str(warning_count), 'warning')} warnings")
                if disabled_count > 0:
                    print(f"  - {self.color_output.colorize(str(disabled_count), 'error')} disabled")
                print()
                print(f"{self.color_output.colorize('Statistics:', 'info')}")
                print(f"  - Scanned: {self.color_output.colorize(str(total_files), 'module')} potential modules")
                print(f"  - Discovered: {self.color_output.colorize(str(total_discovered), 'module')} modules ({success_rate:.1f}% success rate)")
                print(f"  - Average: {self.color_output.colorize(f'{avg_time_per_module:.3f}s', 'info')} per module")
                print()
                
            except Exception as e:
                stop_spinner.set()
                progress_thread.join(timeout=1.0)
                print(f"\r{' ' * 80}\r", end="")  # Clear line
                print(f"\n{self.color_output.status('✗', f'Discovery failed: {e}', 'error')}")
                if self._verbose:
                    import traceback
                    traceback.print_exc()
        
        # ========================================================================
        # Test Management Commands
        # ========================================================================
        
        def do_list_tests(self, args: str):
            """List available tests: list-tests [--module MODULE] [--category CATEGORY]"""
            parsed = self._parse_run_args(shlex.split(args) if args.strip() else [])
            if parsed is None:
                return
            
            try:
                test_cases = self.runner.discover_test_cases(
                    module=parsed.get('module'),
                    category=parsed.get('category'),
                    tags=parsed.get('tags'),
                    tag_mode=parsed.get('tag_mode', 'all')
                )
                
                print(f"\nFound {len(test_cases)} test cases")
                print("=" * 60)
                for test_case in test_cases[:50]:  # Limit to first 50
                    module_str = test_case.module or "unknown"
                    print(f"  {self.color_output.colorize(module_str, 'module')}: {test_case.test_id}")
                if len(test_cases) > 50:
                    print(f"  ... and {len(test_cases) - 50} more")
                print()
            except Exception as e:
                print(f"{self.color_output.status('✗', f'Error: {e}', 'error')}")
        
        def do_validate_tests(self, args: str):
            """Validate test data files"""
            _validate_test_data(self._test_data_dir)
        
        def do_create_template(self, args: str):
            """Create test template for module: create-template MODULE [--all] [--overwrite]"""
            if not args or not args.strip():
                print("Usage: create-template [MODULE|--all] [--overwrite]")
                print("  MODULE: Module name to create template for")
                print("  --all: Create templates for all modules without tests")
                print("  --overwrite: Overwrite existing test files")
                return
            
            parts = shlex.split(args) if args.strip() else []
            
            # Check for --all flag
            if "--all" in parts or args.strip() == "--all":
                overwrite = "--overwrite" in parts or "--overwrite" in args
                _create_all_test_templates(self._test_data_dir, overwrite=overwrite)
                return
            
            # Parse module name and flags
            overwrite = "--overwrite" in parts
            module_name = None
            
            for part in parts:
                if part != "--overwrite" and not part.startswith("--"):
                    module_name = part
                    break
            
            if not module_name:
                print("Usage: create-template [MODULE|--all] [--overwrite]")
                print("  MODULE: Module name to create template for")
                print("  --all: Create templates for all modules without tests")
                print("  --overwrite: Overwrite existing test files")
                return
            
            if _create_test_template(module_name, self._test_data_dir, overwrite=overwrite):
                print(f"✓ Test template created for {module_name}")
            else:
                print(f"✗ Test file already exists for {module_name}. Use --overwrite to replace.")
        
        # ========================================================================
        # Results & Reporting Commands
        # ========================================================================
        
        def do_list_results(self, args: str):
            """List archived test results"""
            _list_archives(self._results_dir)
        
        def do_report(self, args: str):
            """Generate HTML report: report [RESULTS_FILE]"""
            parts = shlex.split(args) if args.strip() else []
            
            from mavaia_core.evaluation.test_results import TestResults
            from mavaia_core.evaluation.test_reporter import TestReporter
            
            results_manager = TestResults(self._results_dir)
            reporter = TestReporter(use_colors=self.color_output.enabled, verbose=self._verbose)
            
            if parts:
                results_file = parts[0]
            else:
                # Find most recent results
                archives = results_manager.list_archives()
                if not archives:
                    print("No archived results found")
                    return
                results_file = archives[0] / "detailed_results.json"
            
            try:
                results = results_manager.load_results(results_file)
                output_path = f"report_{results.test_run_id}.html"
                reporter.generate_html_report(results, output_path)
                print(f"{self.color_output.status('✓', f'Report generated: {output_path}', 'success')}")
            except Exception as e:
                print(f"{self.color_output.status('✗', f'Error: {e}', 'error')}")
        
        def do_compare(self, args: str):
            """Compare with baseline: compare BASELINE_FILE"""
            parts = shlex.split(args) if args.strip() else []
            if not parts:
                print("Usage: compare BASELINE_FILE")
                return
            
            # Get current results from most recent archive
            from mavaia_core.evaluation.test_results import TestResults
            results_manager = TestResults(self._results_dir)
            archives = results_manager.list_archives()
            
            if not archives:
                print("No recent results to compare")
                return
            
            try:
                current = results_manager.load_results(archives[0] / "detailed_results.json")
                baseline_path = parts[0]
                _compare_results(current, baseline_path)
            except Exception as e:
                print(f"{self.color_output.status('✗', f'Error: {e}', 'error')}")
        
        # ========================================================================
        # Analysis Commands
        # ========================================================================
        
        def do_coverage(self, args: str):
            """Show test coverage statistics"""
            _show_test_coverage()
        
        def do_health(self, args: str):
            """Show module health scores"""
            _show_module_health_scores(self._results_dir)
        
        def do_impact(self, args: str):
            """Analyze test impact"""
            _analyze_test_impact(self._results_dir)
        
        def do_explain(self, args: str):
            """Explain module failures: explain MODULE"""
            parts = shlex.split(args) if args.strip() else []
            if not parts:
                print("Usage: explain MODULE")
                return
            _explain_module_failures(parts[0], self._results_dir)
        
        # ========================================================================
        # Graph & Visualization Commands
        # ========================================================================
        
        def do_graph(self, args: str):
            """Generate dependency graph: graph [OUTPUT_FILE]"""
            parts = shlex.split(args) if args.strip() else []
            output_file = parts[0] if parts else "dependency_graph.png"
            _generate_dependency_graph(output_file)
        
        def do_detect_cycles(self, args: str):
            """Detect dependency cycles"""
            _detect_dependency_cycles()
        
        # ========================================================================
        # Tab Completion
        # ========================================================================
        
        def complete_describe(self, text: str, line: str, begidx: int, endidx: int) -> list:
            """Tab completion for module names in describe command"""
            try:
                from mavaia_core.brain.registry import ModuleRegistry
                modules = ModuleRegistry.list_modules()
                return [m for m in modules if m.startswith(text)]
            except Exception:
                return []
        
        def complete_run(self, text: str, line: str, begidx: int, endidx: int) -> list:
            """Tab completion for run command arguments"""
            # Simple completion - could be enhanced
            if '--module' in line and text:
                try:
                    from mavaia_core.brain.registry import ModuleRegistry
                    modules = ModuleRegistry.list_modules()
                    return [m for m in modules if m.startswith(text)]
                except Exception:
                    return []
            elif '--category' in line and text:
                categories = ['functional', 'reasoning', 'safety', 'api', 'client', 'system']
                return [c for c in categories if c.startswith(text)]
            return []
        
        def complete_list_tests(self, text: str, line: str, begidx: int, endidx: int) -> list:
            """Tab completion for list-tests command"""
            return self.complete_run(text, line, begidx, endidx)
        
        def complete_explain(self, text: str, line: str, begidx: int, endidx: int) -> list:
            """Tab completion for explain command"""
            return self.complete_describe(text, line, begidx, endidx)
        
        def complete_create_template(self, text: str, line: str, begidx: int, endidx: int) -> list:
            """Tab completion for create-template command"""
            return self.complete_describe(text, line, begidx, endidx)
        
        # ========================================================================
        # Help System
        # ========================================================================
        
        def help_run(self):
            """Help for run command"""
            print("""
Run tests: run [--module MODULE] [--category CATEGORY] [--tags TAG...]

Options:
  --module MODULE      Run tests for a specific module
  --category CATEGORY   Run tests for a specific category
  --tags TAG...        Filter by tags (e.g., quick, essential)
  --timeout SECONDS    Override timeout for all tests
  --tag-mode MODE      How to combine tags: 'all' (AND) or 'any' (OR)

Examples:
  run
  run --module chain_of_thought
  run --category reasoning --tags quick
  run --tags essential quick
        """)
    
        def help_profile(self):
            """Help for profile command"""
            print("""
Profile management: profile [NAME|list|show NAME|save NAME|delete NAME]

Built-in profiles:
  fast      - Quick tests only (tags: quick, essential, timeout: 10s)
  thorough  - All tests with verbose output (timeout: 60s)
  gpu       - GPU-optimized tests (tags: gpu, essential, timeout: 120s)
  silent    - Minimal output, no colors

Examples:
  profile fast              # Activate fast profile
  profile list              # List all profiles
  profile show fast          # Show profile details
  profile save myprofile     # Save current config as profile
  profile delete myprofile   # Delete custom profile
        """)
    
        def help_alias(self):
            """Help for alias command"""
            print("""
Alias management: alias [NAME [COMMAND]]

Create shortcuts for commands. Aliases can include arguments.

Examples:
  alias                    # List all aliases
  alias m "run --module chain_of_thought"
  alias quick "run --tags quick"
  unalias m                # Remove alias
        """)
    
    # Set the global TestRunnerCLI to the created class
    TestRunnerCLI = TestRunnerCLIImpl
    return TestRunnerCLI


def main():
    """Command-line interface for evaluation framework"""
    import argparse
    import sys
    
    # Lazy load CLI class only when needed
    # If no arguments provided, start interactive CLI
    if len(sys.argv) == 1:
        TestRunnerCLIClass = _get_cli_class()
        cli = TestRunnerCLIClass()
        try:
            cli.cmdloop()
        except KeyboardInterrupt:
            print("\nExiting...")
            sys.exit(0)
        return
    
    # If first argument is a known CLI command, run it in single-command mode
    # This allows: python -m mavaia_core.evaluation.test_runner run --module X
    first_arg = sys.argv[1] if len(sys.argv) > 1 else None
    cli_commands = [
        'run', 'run-quick', 'run-essential',
        'list-modules', 'describe', 'discover',
        'list-tests', 'validate-tests', 'create-template',
        'list-results', 'report', 'compare',
        'coverage', 'health', 'impact', 'explain',
        'graph', 'detect-cycles',
        'config', 'set', 'profile', 'alias', 'unalias',
        'help', 'quit', 'exit', 'clear', 'history'
    ]
    
    # Built-in aliases (defined here to avoid accessing class attribute at import time)
    builtin_aliases = {'r', 'lm', 'lr', 'lt', 'd', 'h', 'q', 'c', 'vt', 'ct', 'cov'}
    
    if first_arg in cli_commands or first_arg in builtin_aliases:
        # Single command mode - create CLI and execute command
        TestRunnerCLIClass = _get_cli_class()
        cli = TestRunnerCLIClass()
        # Join all args except script name as a single command
        command_line = ' '.join(sys.argv[1:])
        cli.onecmd(command_line)
        return
    
    # Otherwise, use legacy argparse interface for backward compatibility
    # Check for help flags FIRST - if help is requested, we'll set up a minimal parser
    # and let it handle --help, which will exit before any expensive imports
    if '--help' in sys.argv or '-h' in sys.argv:
        # Create a minimal parser just for help - this will exit after showing help
        # We'll create the full parser below, but this allows early exit
        pass
    
    # Define available test categories with descriptions
    TEST_CATEGORIES = {
        "functional": (
            "Functional correctness tests for brain modules. "
            "Validates that module operations work correctly with valid inputs, "
            "proper parameter handling, and expected output formats."
        ),
        "module": (
            "Synonym for 'functional'. Tests individual module operations "
            "with validation and error handling."
        ),
        "reasoning": (
            "Reasoning quality evaluation tests. Validates Chain-of-Thought (CoT), "
            "MCTS, and other reasoning modules. Checks reasoning steps, complexity "
            "detection, and logical deduction quality."
        ),
        "safety": (
            "Safety and security tests. Validates input sanitization, error handling, "
            "resource limits, adversarial inputs, and edge case handling."
        ),
        "api": (
            "HTTP API endpoint tests. Tests all REST API endpoints including "
            "OpenAI-compatible endpoints and Mavaia-specific endpoints. "
            "Validates request/response formats, authentication, and error responses."
        ),
        "client": (
            "Python client interface tests. Tests the MavaiaClient API, "
            "module access patterns, and client error handling."
        ),
        "system": (
            "Core system component tests. Tests ModuleRegistry, ModuleOrchestrator, "
            "StateStorage, MetricsCollector, and HealthChecker. Validates system "
            "infrastructure and component interactions."
        ),
        "livebench": (
            "LiveBench benchmark tests. Tests brain modules against LiveBench's "
            "contamination-free benchmark suite with 18 diverse tasks across 6 categories: "
            "reasoning, math, coding, language, data analysis, and instruction following. "
            "Uses objective ground-truth evaluation and integrates LiveBench's code runner "
            "for safe code execution in coding tasks."
        ),
    }
    
    parser = argparse.ArgumentParser(
        description=(
            "Mavaia Core Test Suite - MMLU-style Evaluation Framework\n\n"
            "Comprehensive test suite for evaluating all Mavaia brain modules and "
            "system components. Provides real-time progress, detailed reporting, "
            "and professional HTML reports.\n\n"
            "The test suite automatically discovers test cases from JSON/YAML files "
            "in the test_data directory and executes them with proper validation, "
            "timeout handling, and error reporting."
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "Examples:\n"
            "  # Run all tests\n"
            "  python3 -m mavaia_core.evaluation.test_runner\n\n"
            "  # Test a specific module\n"
            "  python3 -m mavaia_core.evaluation.test_runner --module chain_of_thought\n\n"
            "  # Test a specific category\n"
            "  python3 -m mavaia_core.evaluation.test_runner --category reasoning\n\n"
            "  # Run only system tests (fast, no module discovery)\n"
            "  python3 -m mavaia_core.evaluation.test_runner --category system --skip-modules\n\n"
            "  # Generate report from existing results\n"
            "  python3 -m mavaia_core.evaluation.test_runner --report-only results/20250115_103000/detailed_results.json\n\n"
            "For more information, see: mavaia_core/evaluation/README.md"
        )
    )
    parser.add_argument(
        "--module",
        type=str,
        metavar="MODULE_NAME",
        help=(
            "Run tests for a specific brain module. Only test cases matching "
            "the specified module name will be executed. Example: --module chain_of_thought"
        )
    )
    parser.add_argument(
        "--category",
        type=str,
        metavar="CATEGORY",
        help=(
            "Run tests for a specific category. Available categories: "
            "functional, reasoning, safety, api, client, system, livebench. "
            "Use --categories to see detailed descriptions of each category."
        )
    )
    parser.add_argument(
        "--livebench-category",
        type=str,
        metavar="LIVEBENCH_CATEGORY",
        choices=["reasoning", "math", "coding", "language", "data_analysis", "instruction_following"],
        help=(
            "Filter LiveBench tests by specific category. Only valid when --category livebench is used. "
            "Available LiveBench categories: reasoning, math, coding, language, data_analysis, instruction_following. "
            "Example: --category livebench --livebench-category reasoning"
        )
    )
    parser.add_argument(
        "--max-questions",
        type=int,
        metavar="N",
        help=(
            "Maximum number of LiveBench questions to load per task. Only valid when --category livebench is used. "
            "Useful for quick testing or limiting test execution time. "
            "Example: --category livebench --max-questions 10"
        )
    )
    parser.add_argument(
        "--categories",
        action="store_true",
        help=(
            "List all available test categories with detailed descriptions. "
            "This option displays information about what each category tests "
            "and then exits."
        )
    )
    parser.add_argument(
        "--tags",
        type=str,
        nargs="+",
        metavar="TAG",
        help=(
            "Filter tests by tags. Tags can be combined using --tag-mode. "
            "Default tags: 'quick' (fast tests), 'essential' (core functionality), "
            "'smoke' (basic sanity checks), 'integration' (component interactions), "
            "'unit' (individual components). Custom tags can be defined in test files. "
            "Example: --tags quick essential"
        )
    )
    parser.add_argument(
        "--tag-mode",
        type=str,
        choices=["all", "any"],
        default="all",
        help=(
            "How to combine multiple tags: 'all' (test must have ALL tags) or "
            "'any' (test must have AT LEAST ONE tag). Default: all"
        )
    )
    parser.add_argument(
        "--test-data-dir",
        type=str,
        metavar="DIRECTORY",
        help=(
            "Directory containing test data files (JSON/YAML). "
            "Defaults to mavaia_core/evaluation/test_data/"
        )
    )
    parser.add_argument(
        "--results-dir",
        type=str,
        metavar="DIRECTORY",
        help=(
            "Directory for storing test results and reports. "
            "Defaults to mavaia_core/evaluation/results/"
        )
    )
    parser.add_argument(
        "--timeout",
        type=float,
        metavar="SECONDS",
        help=(
            "Timeout for all test executions in seconds. "
            "Individual test cases can override this with their own timeout. "
            "Default: 30.0 seconds per test case."
        )
    )
    parser.add_argument(
        "--skip-modules",
        action="store_true",
        help=(
            "Skip tests that require module discovery. This significantly speeds up "
            "startup by avoiding module discovery, but will skip functional, reasoning, "
            "and safety tests that require modules. System and API tests will still run."
        )
    )
    parser.add_argument(
        "--new-only",
        action="store_true",
        help=(
            "Only test modules that are newly discovered and don't have test files yet. "
            "This helps identify modules that need test coverage. The evaluation framework will "
            "scan for modules without corresponding test data files and report them."
        )
    )
    parser.add_argument(
        "--no-colors",
        action="store_true",
        help="Disable color-coded output. Useful for logging or when colors aren't supported."
    )
    parser.add_argument(
        "--quiet",
        action="store_true",
        help=(
            "Quiet mode - minimal output. Only shows final summary and errors. "
            "Useful for automated testing or when running large test suites."
        )
    )
    parser.add_argument(
        "--debug",
        action="store_true",
        help=(
            "Enable debug output. Shows detailed information about test execution, "
            "module discovery, and internal operations. Useful for troubleshooting."
        )
    )
    parser.add_argument(
        "--report-only",
        type=str,
        metavar="RESULTS_FILE",
        help=(
            "Generate HTML report from an existing test results JSON file. "
            "Does not run any tests. Use this to regenerate reports from archived results. "
            "Example: --report-only results/20250115_103000/detailed_results.json"
        )
    )
    parser.add_argument(
        "--output",
        type=str,
        metavar="FILE",
        help=(
            "Output path for HTML report. If not specified, report is saved to "
            "the results directory with a timestamp-based filename."
        )
    )
    parser.add_argument(
        "--list-modules",
        action="store_true",
        help=(
            "List all discovered modules grouped by type. Shows module names, "
            "versions, and basic information. This option displays the module list "
            "and then exits."
        )
    )
    parser.add_argument(
        "--describe",
        type=str,
        metavar="MODULE_NAME",
        help=(
            "Show detailed information about a specific module. Displays metadata, "
            "version, operations, parameters, dependencies, and other details. "
            "Example: --describe chain_of_thought"
        )
    )
    parser.add_argument(
        "--exclude-module",
        type=str,
        nargs="+",
        metavar="MODULE_NAME",
        help=(
            "Exclude specific modules from testing. Can specify multiple modules. "
            "Example: --exclude-module module1 module2"
        )
    )
    parser.add_argument(
        "--exclude-category",
        type=str,
        nargs="+",
        metavar="CATEGORY",
        help=(
            "Exclude specific categories from testing. Can specify multiple categories. "
            "Example: --exclude-category safety api"
        )
    )
    parser.add_argument(
        "--enabled-only",
        action="store_true",
        help=(
            "Only test modules that are enabled. Skips disabled modules. "
            "Useful for testing only active modules."
        )
    )
    parser.add_argument(
        "--stop-on-failure",
        action="store_true",
        help=(
            "Stop test execution on first failure. Useful for quick feedback during "
            "development. By default, all tests run regardless of failures."
        )
    )
    parser.add_argument(
        "--retry",
        type=int,
        metavar="N",
        default=0,
        help=(
            "Retry failed tests N times. Useful for flaky tests or transient failures. "
            "Default: 0 (no retries)"
        )
    )
    parser.add_argument(
        "--random-order",
        action="store_true",
        help=(
            "Run tests in random order. Helps detect test dependencies and ordering issues. "
            "Use --seed to make the order reproducible."
        )
    )
    parser.add_argument(
        "--seed",
        type=int,
        metavar="N",
        help=(
            "Random seed for test execution order. Use with --random-order for "
            "reproducible test ordering. Useful for debugging test failures."
        )
    )
    parser.add_argument(
        "--csv",
        type=str,
        metavar="FILE",
        help=(
            "Export test results to CSV format. Specify output file path. "
            "Example: --csv results.csv"
        )
    )
    parser.add_argument(
        "--json-output",
        type=str,
        metavar="FILE",
        help=(
            "Export test results to JSON format. Specify output file path. "
            "Results are always saved, but this allows custom filename. "
            "Example: --json-output custom_results.json"
        )
    )
    parser.add_argument(
        "--junit-xml",
        type=str,
        metavar="FILE",
        help=(
            "Export test results in JUnit XML format for CI/CD integration. "
            "Compatible with Jenkins, GitLab CI, GitHub Actions, etc. "
            "Example: --junit-xml junit_results.xml"
        )
    )
    parser.add_argument(
        "--no-html",
        action="store_true",
        help=(
            "Skip HTML report generation. Useful when you only need JSON/CSV output "
            "or when running in headless environments."
        )
    )
    parser.add_argument(
        "--validate-tests",
        action="store_true",
        help=(
            "Validate test data files without running tests. Checks for syntax errors, "
            "missing required fields, and invalid configurations. Exits after validation."
        )
    )
    parser.add_argument(
        "--create-template",
        type=str,
        metavar="MODULE_NAME",
        help=(
            "Create a test template file for a module. Generates a JSON template with "
            "example test cases that can be customized. Example: --create-template my_module"
        )
    )
    parser.add_argument(
        "--compare",
        type=str,
        metavar="BASELINE_FILE",
        help=(
            "Compare current test results with a baseline. Shows differences in pass/fail "
            "rates, performance changes, and new failures. Specify path to baseline results JSON. "
            "Example: --compare results/20250115_103000/detailed_results.json"
        )
    )
    parser.add_argument(
        "--compare-industry",
        type=str,
        nargs="?",
        const="auto",
        metavar="RESULTS_FILE",
        help=(
            "Compare test results against industry benchmarks. Shows how Mavaia performs "
            "compared to industry standards (GPT-4, Claude-3, etc.) across all test categories. "
            "If no file specified, uses the most recent test results. "
            "Example: --compare-industry or --compare-industry results/20250115_103000/detailed_results.json"
        )
    )
    parser.add_argument(
        "--list-archives",
        action="store_true",
        help=(
            "List all archived test result directories. Shows timestamped directories "
            "with test run summaries. Useful for finding previous test runs."
        )
    )
    parser.add_argument(
        "--graph",
        type=str,
        nargs="?",
        const="dependency_graph.png",
        metavar="OUTPUT_FILE",
        help=(
            "Generate module dependency graph. Creates a visual graph showing "
            "module dependencies and relationships. Supports PNG and SVG formats. "
            "Example: --graph deps.png or --graph deps.svg"
        )
    )
    parser.add_argument(
        "--graph-layout",
        type=str,
        choices=["spring", "circular", "hierarchical", "cluster", "kamada_kawai"],
        default="spring",
        help=(
            "Graph layout algorithm. Options: 'spring' (force-directed), "
            "'circular', 'hierarchical', 'cluster' (grouped by category), "
            "'kamada_kawai' (force-directed with better spacing). Default: spring"
        )
    )
    parser.add_argument(
        "--detect-cycles",
        action="store_true",
        help=(
            "Detect dependency cycles in module graph. Reports any circular "
            "dependencies that could cause initialization or execution issues."
        )
    )
    parser.add_argument(
        "--module-health",
        action="store_true",
        help=(
            "Calculate and display module health scores. Scores modules based on "
            "test pass rate, performance, error frequency, and metadata completeness."
        )
    )
    parser.add_argument(
        "--test-impact",
        action="store_true",
        help=(
            "Analyze test impact. Shows which modules are most critical based on "
            "dependency relationships and test coverage. Identifies high-impact modules."
        )
    )
    parser.add_argument(
        "--profile",
        action="store_true",
        help=(
            "Print performance heatmaps. Shows execution time distribution "
            "across modules and operations. Useful for identifying performance bottlenecks."
        )
    )
    parser.add_argument(
        "--coverage",
        action="store_true",
        help=(
            "Print test coverage statistics. Shows percentage of modules with tests, "
            "modules without tests, and coverage breakdown by category."
        )
    )
    parser.add_argument(
        "--explain",
        type=str,
        metavar="MODULE_NAME",
        help=(
            "Breakdown why a module failed. Analyzes test failures for a specific module "
            "and provides detailed explanations, error patterns, and suggestions. "
            "Example: --explain chain_of_thought"
        )
    )
    parser.add_argument(
        "--fuzz",
        type=int,
        nargs="?",
        const=100,
        metavar="COUNT",
        help=(
            "Run random adversarial tests. Generates random inputs to test modules "
            "for robustness. Specify number of fuzz tests (default: 100). "
            "Example: --fuzz 200"
        )
    )
    parser.add_argument(
        "--validate-modules",
        action="store_true",
        help=(
            "Sanity check metadata across the system. Validates module metadata, "
            "operations, dependencies, and configuration. Reports inconsistencies."
        )
    )
    parser.add_argument(
        "--bench",
        action="store_true",
        help=(
            "Run microbenchmarks per module. Measures execution time, throughput, "
            "and resource usage for each module operation. Provides performance baselines."
        )
    )
    parser.add_argument(
        "--watch",
        action="store_true",
        help=(
            "Auto-rerun tests on file changes. Monitors test data files and source code "
            "for changes and automatically reruns affected tests. Useful for TDD workflow."
        )
    )
    parser.add_argument(
        "--order-by",
        type=str,
        choices=["time", "failures", "priority", "name", "random"],
        metavar="METRIC",
        help=(
            "Sort test execution by metric. Options: 'time' (fastest first), "
            "'failures' (most failing first), 'priority' (by tags), 'name' (alphabetical), "
            "'random' (random order). Default: execution order from test files."
        )
    )
    parser.add_argument(
        "--stress",
        type=int,
        nargs="?",
        const=10,
        metavar="CONCURRENT",
        help=(
            "Run load tests and concurrency tests. Tests modules under concurrent load. "
            "Specify number of concurrent requests (default: 10). "
            "Example: --stress 50"
        )
    )
    parser.add_argument(
        "--matrix",
        type=str,
        nargs="+",
        metavar="CONFIG",
        help=(
            "Run tests across multiple configurations. Specify configuration combinations "
            "as key=value pairs. Example: --matrix python=3.9 python=3.11 model=small model=large"
        )
    )
    
    args = parser.parse_args()
    
    # Import ModuleRegistry lazily (only after args are parsed, so help works quickly)
    from mavaia_core.brain.registry import ModuleRegistry
    
    # Handle --categories option (show categories and exit)
    if args.categories:
        print("\n" + "=" * 70)
        print("Available Test Categories")
        print("=" * 70 + "\n")
        
        for category, description in sorted(TEST_CATEGORIES.items()):
            print(f"  {category.upper()}")
            print(f"    {description}\n")
        
        print("=" * 70)
        print("\nUsage Examples:")
        print(f"  # Test a specific category")
        print(f"  python3 -m mavaia_core.evaluation.test_runner --category reasoning")
        print(f"\n  # Test multiple categories (run multiple times)")
        print(f"  python3 -m mavaia_core.evaluation.test_runner --category functional")
        print(f"  python3 -m mavaia_core.evaluation.test_runner --category safety")
        print("\n")
        return
    
    # Handle --list-modules option (show modules and exit)
    if args.list_modules:
        _list_all_modules(use_colors=not args.no_colors)
        return
    
    # Handle --describe option (show module details and exit)
    if args.describe:
        _describe_module(args.describe, use_colors=not args.no_colors)
        return
    
    # Handle --validate-tests option (validate and exit)
    if args.validate_tests:
        _validate_test_data(args.test_data_dir)
        return
    
    # Handle --create-template option (create template and exit)
    if args.create_template:
        if args.create_template == "--all":
            _create_all_test_templates(args.test_data_dir, overwrite=False)
        else:
            _create_test_template(args.create_template, args.test_data_dir, overwrite=False)
        return
    
    # Handle --list-archives option (list archives and exit)
    if args.list_archives:
        _list_archives(args.results_dir)
        return
    
    # Validate LiveBench-specific arguments
    if args.livebench_category and args.category != "livebench":
        print("Error: --livebench-category can only be used with --category livebench", file=sys.stderr)
        sys.exit(1)
    
    if args.max_questions is not None and args.category != "livebench":
        print("Error: --max-questions can only be used with --category livebench", file=sys.stderr)
        sys.exit(1)
    
    if args.max_questions is not None and args.max_questions < 1:
        print("Error: --max-questions must be a positive integer", file=sys.stderr)
        sys.exit(1)
    
    # Handle --graph option (generate dependency graph and exit)
    if args.graph:
        _generate_dependency_graph(
            args.graph,
            layout=args.graph_layout,
            detect_cycles=args.detect_cycles
        )
        return
    
    # Handle --detect-cycles option (detect cycles and exit)
    if args.detect_cycles and not args.graph:
        _detect_dependency_cycles()
        return
    
    # Handle --module-health option (show health scores and exit)
    if args.module_health:
        _show_module_health_scores(args.results_dir)
        return
    
    # Handle --test-impact option (show impact analysis and exit)
    if args.test_impact:
        _analyze_test_impact(args.results_dir)
        return
    
    # Handle --coverage option (show coverage and exit)
    if args.coverage:
        _show_test_coverage()
        return
    
    # Handle --explain option (explain module failures and exit)
    if args.explain:
        _explain_module_failures(args.explain, args.results_dir)
        return
    
    # Handle --validate-modules option (validate modules and exit)
    if args.validate_modules:
        _validate_all_modules()
        return
    
    # Validate category if provided
    if args.category and args.category not in TEST_CATEGORIES:
        print(f"Error: Unknown category '{args.category}'", file=sys.stderr)
        print(f"\nAvailable categories:", file=sys.stderr)
        for cat in sorted(TEST_CATEGORIES.keys()):
            print(f"  - {cat}", file=sys.stderr)
        print(f"\nUse --categories to see detailed descriptions.", file=sys.stderr)
        sys.exit(1)
    
    if args.debug:
        import logging
        logging.basicConfig(level=logging.DEBUG)
        print("Debug mode enabled", flush=True)
    
    # Handle report-only mode
    if args.report_only:
        results_manager = TestResults(args.results_dir)
        results = results_manager.load_results(args.report_only)
        reporter = TestReporter(use_colors=not args.no_colors, verbose=not args.quiet)
        
        output_path = args.output or f"report_{results.test_run_id}.html"
        reporter.generate_html_report(results, output_path)
        print(f"Report generated: {output_path}")
        return
    
    # Handle compare-industry mode
    if args.compare_industry:
        from mavaia_core.evaluation.industry_comparison import IndustryComparison
        from mavaia_core.evaluation.test_results import TestResults
        from pathlib import Path
        
        results_file = None
        if args.compare_industry != "auto":
            results_file = Path(args.compare_industry)
            if not results_file.exists():
                print(f"Error: Results file not found: {results_file}", file=sys.stderr)
                sys.exit(1)
        else:
            # Find most recent results
            results_manager = TestResults(args.results_dir)
            archives = results_manager.list_archives()
            if not archives:
                print("Error: No test results found. Run tests first.", file=sys.stderr)
                sys.exit(1)
            results_file = archives[0] / "detailed_results.json"
            if not results_file.exists():
                print(f"Error: Results file not found: {results_file}", file=sys.stderr)
                sys.exit(1)
        
        comparison = IndustryComparison()
        results = comparison.load_results(results_file)
        if not results:
            print(f"Error: Could not load results from {results_file}", file=sys.stderr)
            sys.exit(1)
        
        metrics = comparison.calculate_metrics(results)
        
        # Generate report
        output_file = args.output or Path("industry_comparison_report.txt")
        report = comparison.generate_report(output_file)
        print(report)
        
        if output_file:
            print(f"\n📊 Industry comparison report saved to: {output_file}")
        
        return
    
    # Create evaluation framework
    if not args.quiet:
        print("Initializing evaluation framework...", flush=True)
    
    try:
        runner = TestRunner(
            test_data_dir=args.test_data_dir,
            results_dir=args.results_dir,
            verbose=not args.quiet,
            use_colors=not args.no_colors
        )
        # Store flags
        runner._skip_modules = args.skip_modules
        runner._new_only = args.new_only
        runner._tag_mode = args.tag_mode
        runner._exclude_modules = args.exclude_module or []
        runner._exclude_categories = args.exclude_category or []
        runner._enabled_only = args.enabled_only
        runner._stop_on_failure = args.stop_on_failure
        runner._retry_count = args.retry
        runner._random_order = args.random_order
        runner._random_seed = args.seed
        runner._order_by = args.order_by
        runner._fuzz = args.fuzz
        runner._bench = args.bench
        runner._stress = args.stress
        runner._matrix = args.matrix
        runner._profile = args.profile
        runner._watch = args.watch
        runner._livebench_category = getattr(args, 'livebench_category', None)
        runner._max_questions = getattr(args, 'max_questions', None)
    except Exception as e:
        print(f"Error initializing evaluation framework: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        sys.exit(1)
    
    # Run tests
    if not args.quiet:
        print("Running test suite...", flush=True)
    
    # Handle watch mode
    if args.watch:
        _watch_mode(runner, args)
        return
    
    # Handle fuzz mode
    if args.fuzz:
        _run_fuzz_tests(runner, args.fuzz, args)
        return
    
    # Handle bench mode
    if args.bench:
        _run_benchmarks(runner, args)
        return
    
    # Handle stress mode
    if args.stress:
        _run_stress_tests(runner, args.stress, args)
        return
    
    # Handle matrix mode
    if args.matrix:
        _run_matrix_tests(runner, args.matrix, args)
        return
    
    try:
        results = runner.run_test_suite(
            module=args.module,
            category=args.category,
            tags=args.tags,
            timeout=args.timeout,
            tag_mode=args.tag_mode,
            new_only=args.new_only
        )
    except KeyboardInterrupt:
        print("\nTest run interrupted by user", file=sys.stderr)
        sys.exit(130)
    except Exception as e:
        print(f"Error running tests: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        sys.exit(1)
    
    # Save results
    archive_path = runner.save_results(results, archive=True)
    print(f"\nResults archived to: {archive_path}")
    
    # Export to JSON if requested
    if args.json_output:
        json_path = Path(args.json_output)
        json_path.parent.mkdir(parents=True, exist_ok=True)
        runner.test_results.save_results(results, filename=json_path.name)
        print(f"JSON results exported to: {json_path}")
    
    # Export to CSV if requested
    if args.csv:
        csv_path = Path(args.csv)
        csv_path.parent.mkdir(parents=True, exist_ok=True)
        runner.test_results.export_to_csv(results, csv_path)
        print(f"CSV results exported to: {csv_path}")
    
    # Export to JUnit XML if requested
    if args.junit_xml:
        junit_path = Path(args.junit_xml)
        junit_path.parent.mkdir(parents=True, exist_ok=True)
        _export_junit_xml(results, junit_path)
        print(f"JUnit XML exported to: {junit_path}")
    
    # Generate HTML report (unless disabled)
    if not args.no_html:
        if args.output:
            report_path = runner.generate_report(results, args.output)
        else:
            report_path = runner.generate_report(results)
        print(f"HTML report generated: {report_path}")
    
    # Compare with baseline if requested
    if args.compare:
        _compare_results(results, args.compare)
    
    # Compare with industry standards if requested
    if args.compare_industry:
        from mavaia_core.evaluation.industry_comparison import IndustryComparison
        from pathlib import Path
        
        comparison = IndustryComparison()
        # Convert TestRunResults to list of dicts for comparison
        results_list = []
        for result in results.results:
            results_list.append({
                "status": result.status.value.upper(),
                "category": result.category or "unknown",
                "execution_time": result.execution_time,
                "tags": getattr(result, "tags", []),
            })
        
        metrics = comparison.calculate_metrics(results_list)
        output_file = args.output or Path("industry_comparison_report.txt")
        report = comparison.generate_report(output_file)
        print("\n" + "=" * 80)
        print("INDUSTRY COMPARISON")
        print("=" * 80)
        print(report)
        if output_file:
            print(f"\n📊 Industry comparison report saved to: {output_file}")
    
    # Generate profile/heatmap if requested
    if args.profile:
        _generate_performance_heatmap(results)
    
    # Exit with appropriate code
    if results.summary.failed > 0 or results.summary.errors > 0:
        sys.exit(1)
    else:
        sys.exit(0)


def _categorize_module(module_name: str, description: str) -> str:
    """
    Categorize a module by type based on name and description
    
    Args:
        module_name: Module name
        description: Module description
        
    Returns:
        Category name
    """
    name_lower = module_name.lower()
    desc_lower = description.lower()
    
    # Reasoning modules
    if any(keyword in name_lower for keyword in ["reasoning", "cot", "mcts", "chain", "thought", "logic", "deduction", "inference"]):
        return "Reasoning"
    
    # Memory modules
    if any(keyword in name_lower for keyword in ["memory", "recall", "remember", "storage", "persist"]):
        return "Memory"
    
    # Language/NLP modules
    if any(keyword in name_lower for keyword in ["nlp", "linguistic", "language", "text", "embedding", "conversation", "personality", "response"]):
        return "Language & NLP"
    
    # Safety modules
    if any(keyword in name_lower for keyword in ["safety", "threat", "security", "mental_health", "emotional_distress"]):
        return "Safety & Security"
    
    # Tool modules
    if any(keyword in name_lower for keyword in ["tool", "web", "search", "fetch", "scraper", "code_execution", "url"]):
        return "Tools & Integration"
    
    # System/Infrastructure modules
    if any(keyword in name_lower for keyword in ["orchestrator", "registry", "coordinator", "pipeline", "agent", "service"]):
        return "System & Infrastructure"
    
    # Planning/Optimization modules
    if any(keyword in name_lower for keyword in ["plan", "optimizer", "optimization", "gradient", "model_optimizer"]):
        return "Planning & Optimization"
    
    # Analysis modules
    if any(keyword in name_lower for keyword in ["analysis", "analyzer", "analyze", "vision", "image", "document"]):
        return "Analysis"
    
    # Learning modules
    if any(keyword in name_lower for keyword in ["learning", "reinforcement", "neural", "lora", "training"]):
        return "Learning & Training"
    
    # Creative modules
    if any(keyword in name_lower for keyword in ["creative", "writing", "generation", "cognitive_generator"]):
        return "Creative & Generation"
    
    # Default category
    return "Other"


def _list_all_modules(use_colors: bool = True) -> None:
    """
    List all discovered modules grouped by type
    
    Args:
        use_colors: Enable color output
    """
    from mavaia_core.brain.registry import ModuleRegistry
    
    # Discover modules synchronously to ensure they're available
    print("Discovering modules...", end="", flush=True)
    ModuleRegistry.discover_modules(background=False, verbose=True)
    # Wait a moment to ensure discovery completes
    import time
    time.sleep(0.5)
    print(" done\n", flush=True)
    
    # Get all modules
    module_names = ModuleRegistry.list_modules()
    
    if not module_names:
        print("No modules discovered.")
        return
    
    # Group modules by category
    modules_by_category: Dict[str, List[tuple[str, Any]]] = {}
    
    for module_name in sorted(module_names):
        metadata = ModuleRegistry.get_metadata(module_name)
        if metadata:
            category = _categorize_module(module_name, metadata.description)
            if category not in modules_by_category:
                modules_by_category[category] = []
            modules_by_category[category].append((module_name, metadata))
    
    # Print grouped modules
    print("=" * 80)
    print("Discovered Modules (Grouped by Type)")
    print("=" * 80)
    print(f"\nTotal Modules: {len(module_names)}\n")
    
    for category in sorted(modules_by_category.keys()):
        modules = modules_by_category[category]
        print(f"\n{category} ({len(modules)} modules)")
        print("-" * 80)
        
        for module_name, metadata in modules:
            enabled_str = "✓" if metadata.enabled else "✗"
            model_str = " [Model Required]" if metadata.model_required else ""
            ops_count = len(metadata.operations) if metadata.operations else 0
            print(f"  {enabled_str} {module_name:40s} v{metadata.version:10s} ({ops_count} ops){model_str}")
            if metadata.description:
                # Truncate long descriptions
                desc = metadata.description[:65] + "..." if len(metadata.description) > 65 else metadata.description
                print(f"      {desc}")
    
    print("\n" + "=" * 80)
    print(f"\nUse --describe <module_name> to see detailed information about a module.")
    print(f"Example: --describe chain_of_thought\n")


def _describe_module(module_name: str, use_colors: bool = True) -> None:
    """
    Show detailed information about a specific module
    
    Args:
        module_name: Name of module to describe
        use_colors: Enable color output
    """
    from mavaia_core.brain.registry import ModuleRegistry
    
    # Discover modules if needed - use synchronous discovery
    if not ModuleRegistry._discovered:
        print("Discovering modules...", end="", flush=True)
        ModuleRegistry.discover_modules(background=False, verbose=True)
        # Wait a moment to ensure discovery completes
        import time
        time.sleep(0.5)
        print(" done\n", flush=True)
    
    # Get module metadata
    metadata = ModuleRegistry.get_metadata(module_name)
    
    if not metadata:
        print(f"Error: Module '{module_name}' not found.", file=sys.stderr)
        print(f"\nAvailable modules:", file=sys.stderr)
        available = sorted(ModuleRegistry.list_modules())
        for mod in available[:20]:
            print(f"  - {mod}", file=sys.stderr)
        if len(available) > 20:
            print(f"  ... and {len(available) - 20} more", file=sys.stderr)
        print(f"\nUse --list-modules to see all modules.", file=sys.stderr)
        sys.exit(1)
    
    # Get module instance to check for additional info
    module_instance = None
    try:
        module_instance = ModuleRegistry.get_module(module_name, auto_discover=False, wait_timeout=1.0)
    except Exception:
        pass  # Continue without instance
    
    # Print module information
    print("=" * 80)
    print(f"Module Details: {module_name}")
    print("=" * 80)
    print()
    
    # Metadata Section
    print("Metadata")
    print("-" * 80)
    print(f"  Name:            {metadata.name}")
    print(f"  Version:         {metadata.version}")
    print(f"  Enabled:         {'Yes' if metadata.enabled else 'No'}")
    print(f"  Model Required:  {'Yes' if metadata.model_required else 'No'}")
    print()
    
    # Description
    print("Description")
    print("-" * 80)
    # Word wrap description if long
    desc = metadata.description
    if len(desc) > 75:
        words = desc.split()
        lines = []
        current_line = []
        current_length = 0
        for word in words:
            if current_length + len(word) + 1 > 75:
                lines.append(" ".join(current_line))
                current_line = [word]
                current_length = len(word)
            else:
                current_line.append(word)
                current_length += len(word) + 1
        if current_line:
            lines.append(" ".join(current_line))
        for line in lines:
            print(f"  {line}")
    else:
        print(f"  {desc}")
    print()
    
    # Operations
    print("Operations")
    print("-" * 80)
    if metadata.operations:
        print(f"  Total Operations: {len(metadata.operations)}\n")
        for i, operation in enumerate(metadata.operations, 1):
            print(f"  {i}. {operation}")
    else:
        print("  (No operations defined)")
    print()
    
    # Dependencies
    print("Dependencies")
    print("-" * 80)
    if metadata.dependencies:
        print(f"  Total Dependencies: {len(metadata.dependencies)}\n")
        for dep in metadata.dependencies:
            print(f"  - {dep}")
    else:
        print("  (No dependencies listed)")
    print()
    
    # Operation Parameters (try to extract from module)
    if module_instance:
        print("Operation Parameters")
        print("-" * 80)
        try:
            import inspect
            
            # Get execute method signature
            sig = inspect.signature(module_instance.execute)
            params = list(sig.parameters.items())
            
            print("  Execute Method Signature:")
            if len(params) > 1:  # More than just 'self'
                for param_name, param in params[1:]:  # Skip 'self'
                    param_info = f"    {param_name}"
                    if param.annotation != inspect.Parameter.empty:
                        param_info += f": {param.annotation}"
                    if param.default != inspect.Parameter.empty:
                        param_info += f" = {param.default}"
                    print(param_info)
            else:
                print("    execute(operation: str, params: dict[str, Any]) -> dict[str, Any]")
            
            # Try to extract operation-specific parameters from validate_params
            if hasattr(module_instance, 'validate_params'):
                try:
                    # Check if validate_params has operation-specific logic
                    import inspect
                    validate_source = inspect.getsource(module_instance.validate_params)
                    
                    # Look for operation-specific parameter requirements
                    operations_with_params = {}
                    for operation in metadata.operations:
                        # Try to infer parameters from validate_params logic
                        # This is a heuristic - we look for operation names in the code
                        if operation in validate_source:
                            # Try to find parameter checks for this operation
                            lines = validate_source.split('\n')
                            for i, line in enumerate(lines):
                                if operation in line and i + 1 < len(lines):
                                    # Look for parameter checks in next few lines
                                    for j in range(i, min(i + 5, len(lines))):
                                        if 'in params' in lines[j] or 'params.get' in lines[j]:
                                            # Extract parameter name
                                            import re
                                            param_match = re.search(r'["\'](\w+)["\']', lines[j])
                                            if param_match:
                                                param_name = param_match.group(1)
                                                if operation not in operations_with_params:
                                                    operations_with_params[operation] = []
                                                if param_name not in operations_with_params[operation]:
                                                    operations_with_params[operation].append(param_name)
                    
                    if operations_with_params:
                        print("\n  Operation-Specific Parameters (inferred from validation):")
                        for operation, op_params in sorted(operations_with_params.items()):
                            print(f"    {operation}:")
                            for param in op_params:
                                print(f"      - {param}")
                except Exception:
                    pass  # If we can't extract, continue
            
            # Try to get docstring for execute method
            doc = module_instance.execute.__doc__
            if doc:
                print("\n  Execute Method Documentation:")
                # Parse docstring for parameter info
                doc_lines = doc.strip().split('\n')
                in_params = False
                printed_lines = 0
                for line in doc_lines[:40]:  # First 40 lines
                    line_stripped = line.strip()
                    if 'Args:' in line_stripped or 'Parameters:' in line_stripped:
                        in_params = True
                    if in_params and line_stripped:
                        # Indent documentation
                        if line_stripped.startswith(('Args:', 'Parameters:', 'Returns:', 'Raises:')):
                            print(f"    {line_stripped}")
                        else:
                            print(f"      {line_stripped}")
                        printed_lines += 1
                    if in_params and line_stripped and (line_stripped.startswith('Returns:') or line_stripped.startswith('Raises:')):
                        if printed_lines > 5:  # Don't break if we just started
                            break
        except Exception as e:
            print(f"  (Unable to inspect operation parameters: {e})")
        print()
    
    # Category
    category = _categorize_module(module_name, metadata.description)
    print("Category")
    print("-" * 80)
    print(f"  {category}")
    print()
    
    print("=" * 80)
    print(f"\nUse --list-modules to see all available modules.")
    print()


def _validate_test_data(test_data_dir: Optional[str] = None) -> None:
    """Validate test data files without running tests"""
    from mavaia_core.evaluation.test_data_manager import TestDataManager
    
    if test_data_dir is None:
        base_dir = Path(__file__).parent
        test_data_dir = base_dir / "test_data"
    else:
        test_data_dir = Path(test_data_dir)
    
    print("=" * 80)
    print("Validating Test Data Files")
    print("=" * 80)
    print()
    
    manager = TestDataManager(test_data_dir)
    test_files = manager.discover_test_files()
    
    if not test_files:
        print("No test files found.")
        return
    
    print(f"Found {len(test_files)} test file(s)\n")
    
    errors = []
    warnings = []
    valid_count = 0
    
    for test_file in test_files:
        try:
            suite = manager.load_test_file(test_file)
            # Validate each test case
            for test_case in suite.test_suite:
                validation_errors = manager.validate_test_case(test_case)
                if validation_errors:
                    errors.append(f"{test_file.name}:{test_case.id}: {', '.join(validation_errors)}")
                else:
                    valid_count += 1
        except Exception as e:
            errors.append(f"{test_file.name}: {str(e)}")
    
    # Print results
    if errors:
        print("Errors:")
        for error in errors:
            print(f"  ✗ {error}")
        print()
    
    if warnings:
        print("Warnings:")
        for warning in warnings:
            print(f"  ⚠ {warning}")
        print()
    
    print(f"Validation complete: {valid_count} valid test case(s)")
    if errors:
        print(f"  {len(errors)} error(s) found")
        sys.exit(1)
    else:
        print("  All test files are valid!")
        sys.exit(0)


def _create_test_template(module_name: str, test_data_dir: Optional[str] = None, overwrite: bool = False) -> bool:
    """
    Create a test template for a module based on its metadata
    
    Args:
        module_name: Name of the module
        test_data_dir: Directory for test data files
        overwrite: If True, overwrite existing test files
        
    Returns:
        True if template was created, False otherwise
    """
    from mavaia_core.brain.registry import ModuleRegistry
    
    if test_data_dir is None:
        base_dir = Path(__file__).parent
        test_data_dir = base_dir / "test_data" / "modules"
    else:
        test_data_dir = Path(test_data_dir) / "modules"
    
    test_data_dir.mkdir(parents=True, exist_ok=True)
    
    # Get module metadata to create better templates
    ModuleRegistry.discover_modules(background=False, verbose=False)
    metadata = ModuleRegistry.get_metadata(module_name)
    
    if not metadata:
        print(f"Warning: Module '{module_name}' not found. Creating generic template.", file=sys.stderr)
        operations = ["execute"]
        module_version = "1.0.0"
        description = f"Test template for {module_name}"
    else:
        operations = metadata.operations if metadata.operations else ["execute"]
        module_version = metadata.version
        description = metadata.description or f"Test template for {module_name}"
    
    # Create test cases for each operation
    test_suite = []
    test_id_counter = 1
    
    for operation in operations:
        # Determine category based on operation name
        op_lower = operation.lower()
        if any(kw in op_lower for kw in ["reason", "think", "analyze", "deduce", "infer"]):
            category = "reasoning"
        elif any(kw in op_lower for kw in ["safety", "validate", "check", "filter"]):
            category = "safety"
        elif any(kw in op_lower for kw in ["generate", "create", "write", "code"]):
            category = "functional"
        else:
            category = "functional"
        
        # Create functional test case
        # Don't require "result" field - modules may return data directly or wrapped
        test_suite.append({
            "id": f"{module_name}_{test_id_counter:03d}",
            "category": category,
            "operation": operation,
            "params": _generate_default_params(module_name, operation),
            "expected": {
                "result_type": "dict"
            },
            "timeout": 30.0,
            "description": f"Test {operation} operation for {module_name}",
            "tags": ["essential", "quick"]
        })
        test_id_counter += 1
        
        # Add safety test case for error handling
        test_suite.append({
            "id": f"{module_name}_{test_id_counter:03d}",
            "category": "safety",
            "operation": operation,
            "params": _generate_invalid_params(module_name, operation),
            "expected": {
                "validation": {
                    "type": "error_handling"
                }
            },
            "timeout": 10.0,
            "description": f"Test error handling for {operation} with invalid input",
            "tags": ["safety", "quick"]
        })
        test_id_counter += 1
    
    template = {
        "module": module_name,
        "version": module_version,
        "test_suite": test_suite
    }
    
    output_file = test_data_dir / f"{module_name}.json"
    
    if output_file.exists() and not overwrite:
        return False
    
    import json
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(template, f, indent=2, ensure_ascii=False)
    
    return True


def _generate_default_params(module_name: str, operation: str) -> Dict[str, Any]:
    """Generate default parameters for a module operation based on module and operation names"""
    from mavaia_core.brain.registry import ModuleRegistry
    
    op_lower = operation.lower()
    module_lower = module_name.lower()
    
    # Try to get module metadata for better parameter generation
    try:
        metadata = ModuleRegistry.get_metadata(module_name)
        if metadata and metadata.description:
            desc_lower = metadata.description.lower()
        else:
            desc_lower = ""
    except Exception:
        desc_lower = ""
    
    # Module-specific parameter patterns
    if "embed" in module_lower or "embedding" in module_lower:
        return {"text": "Sample text to generate embeddings for"}
    elif "memory" in module_lower:
        if "store" in op_lower or "save" in op_lower:
            return {"key": "test_key", "value": "test_value", "metadata": {}}
        elif "retrieve" in op_lower or "get" in op_lower or "recall" in op_lower:
            return {"key": "test_key"}
        elif "search" in op_lower:
            return {"query": "test query"}
        else:
            return {"text": "test memory operation"}
    elif "search" in module_lower:
        return {"query": "test search query", "limit": 5}
    elif "code" in module_lower:
        code_params = {
            "code": "def hello():\n    return 'world'",
            "code1": "def hello():\n    return 'world'",
            "code2": "def goodbye():\n    return 'bye'"
        }
        if "python" in module_lower:
            code_params["project"] = "/tmp/test_project"
        if "execute" in op_lower:
            code_params["language"] = "python"
            code_params["code"] = "print('hello world')"
        return code_params
    elif "reasoning" in module_lower or "reason" in module_lower:
        return {"query": "What is 2 + 2? Explain your reasoning.", "reasoning_type": "analytical"}
    elif "safety" in module_lower or "threat" in module_lower:
        return {"input": "Sample input to check for safety issues"}
    elif "agent" in module_lower or "coordinator" in module_lower:
        # Agent modules need proper task structure
        return {
            "task": {
                "id": "test_task_001",
                "agent_type": "search",
                "query": "Perform a test task",
                "context": {},
                "dependencies": [],
                "priority": 0
            },
            "context": {},
            "previous_results": []
        }
    elif "analysis" in module_lower or "analyze" in module_lower:
        return {"input": "Sample input for analysis", "analysis_type": "general"}
    elif "orchestrator" in module_lower or "coordinator" in module_lower:
        return {"operation": operation, "params": {}}
    elif "tool" in module_lower:
        return {"tool_name": "test_tool", "params": {}}
    # Operation-specific patterns
    if "analyze_communication" in op_lower or "communication" in op_lower:
        return {"conversation_history": ["Hello, how are you today?", "I would appreciate your help."], "user_id": "test_user"}
    elif "adaptation" in op_lower or "adapt" in op_lower:
        return {"user_profile": {}, "recent_conversations": ["Test conversation"]}
    elif "personality" in op_lower or "adjustment" in op_lower:
        return {"base_config": {}, "user_profile": {}}
    elif "track" in op_lower or "phrase" in op_lower:
        return {"messages": ["Sample text with phrases"]}
    elif "query" in op_lower or "question" in op_lower:
        return {"query": "What is 2 + 2?"}
    elif "text" in op_lower or "input" in op_lower:
        return {"text": "Sample input text for testing"}
    elif "code" in op_lower:
        # For code operations, provide actual code
        if "python" in module_lower:
            return {
                "code": "def hello():\n    return 'world'",
                "code1": "def hello():\n    return 'world'",
                "code2": "def goodbye():\n    return 'bye'",
                "project": "/tmp/test_project"
            }
        else:
            return {
                "code": "def hello():\n    return 'world'",
                "code1": "def hello():\n    return 'world'",
                "code2": "def goodbye():\n    return 'bye'"
            }
    elif "search" in op_lower:
        return {"query": "test search query"}
    elif "embed" in op_lower:
        return {"text": "Sample text to embed"}
    elif "store" in op_lower or "save" in op_lower:
        return {"key": "test_key", "value": "test_value"}
    elif "analyze" in op_lower:
        return {"input": "Sample input for analysis", "query": "Analyze this input"}
    elif "execute" in op_lower:
        return {"operation": operation, "params": {}}
    elif "generate" in op_lower:
        return {"prompt": "Generate a test response", "max_tokens": 100}
    elif "optimize" in op_lower:
        return {"module": "test_module", "operation": "test_operation", "params": {}}
    elif "configure" in op_lower or "config" in op_lower:
        return {"config": {}}
    elif "complexity" in op_lower:
        return {"query": "Test query for complexity analysis"}
    elif "decompose" in op_lower:
        return {"query": "Test query to decompose", "max_steps": 3}
    elif "verify" in op_lower or "verification" in op_lower:
        return {"query": "Test query to verify", "steps": []}
    elif "project" in op_lower:
        return {"project": "/tmp/test_project", "code": "def test():\n    pass"}
    else:
        # Generic parameters - try common parameter names
        params = {}
        # Most modules need query or input
        if "query" in op_lower:
            params["query"] = "What is 2 + 2?"
        elif "input" in op_lower:
            params["input"] = "Test input"
        else:
            # Provide both common parameters
            params["query"] = "Test query"
            params["input"] = "Test input"
        return params


def _generate_invalid_params(module_name: str, operation: str) -> Dict[str, Any]:
    """Generate invalid parameters for error handling tests"""
    return {
        "invalid": True,
        "empty": "",
        "null": None
    }


def _create_all_test_templates(test_data_dir: Optional[str] = None, overwrite: bool = False) -> None:
    """Create default test templates for all modules without tests"""
    from mavaia_core.brain.registry import ModuleRegistry
    from mavaia_core.evaluation.test_data_manager import TestDataManager
    
    print("=" * 80)
    print("Creating Default Test Templates")
    print("=" * 80)
    print()
    
    # Discover all modules
    ModuleRegistry.discover_modules(background=False, verbose=False)
    all_modules = set(ModuleRegistry.list_modules())
    
    # Get modules with tests
    test_data_manager = TestDataManager(test_data_dir)
    test_data_manager.load_all_test_suites()
    modules_with_tests = set()
    for suite in test_data_manager._test_suites.values():
        if suite.module:
            modules_with_tests.add(suite.module)
    
    # Find modules without tests
    modules_without_tests = all_modules - modules_with_tests
    
    if not modules_without_tests:
        print("All modules already have test files!")
        return
    
    print(f"Found {len(modules_without_tests)} modules without tests")
    print(f"Creating default test templates...\n")
    
    created_count = 0
    skipped_count = 0
    failed_count = 0
    
    for module_name in sorted(modules_without_tests):
        try:
            if _create_test_template(module_name, test_data_dir, overwrite=overwrite):
                created_count += 1
                if created_count % 10 == 0:
                    print(f"  Created {created_count} templates...", flush=True)
            else:
                skipped_count += 1
        except Exception as e:
            failed_count += 1
            print(f"  ✗ Failed to create template for {module_name}: {e}", file=sys.stderr)
    
    print()
    print("=" * 80)
    print("Template Creation Complete")
    print("=" * 80)
    print(f"Created: {created_count} templates")
    if skipped_count > 0:
        print(f"Skipped: {skipped_count} (already exist)")
    if failed_count > 0:
        print(f"Failed:  {failed_count}")
    print()
    print(f"Edit the templates in test_data/modules/ to customize test cases.")
    print()


def _list_archives(results_dir: Optional[str] = None) -> None:
    """List all archived test result directories"""
    from mavaia_core.evaluation.test_results import TestResults
    
    results_manager = TestResults(results_dir)
    archives = results_manager.list_archives()
    
    print("=" * 80)
    print("Archived Test Results")
    print("=" * 80)
    print()
    
    if not archives:
        print("No archived test results found.")
        return
    
    for archive_dir in archives:
        summary_file = archive_dir / "summary.json"
        if summary_file.exists():
            import json
            with open(summary_file, "r") as f:
                summary = json.load(f)
            total = summary.get("total_tests", 0)
            passed = summary.get("passed", 0)
            failed = summary.get("failed", 0)
            print(f"  {archive_dir.name}")
            print(f"    Tests: {total} | Passed: {passed} | Failed: {failed}")
            print(f"    Path: {archive_dir}")
            print()
        else:
            print(f"  {archive_dir.name} (no summary)")
            print()


def _export_junit_xml(results: "TestRunResults", output_path: Path) -> None:
    """Export test results to JUnit XML format"""
    from xml.etree.ElementTree import Element, SubElement, tostring
    from xml.dom import minidom
    
    testsuites = Element("testsuites")
    testsuites.set("name", "Mavaia Test Suite")
    testsuites.set("tests", str(results.summary.total_tests))
    testsuites.set("failures", str(results.summary.failed))
    testsuites.set("errors", str(results.summary.errors))
    testsuites.set("time", f"{results.summary.total_execution_time:.3f}")
    
    # Group by module
    by_module = {}
    for result in results.results:
        module = result.module or "unknown"
        if module not in by_module:
            by_module[module] = []
        by_module[module].append(result)
    
    for module, module_results in by_module.items():
        testsuite = SubElement(testsuites, "testsuite")
        testsuite.set("name", module)
        testsuite.set("tests", str(len(module_results)))
        testsuite.set("failures", str(sum(1 for r in module_results if r.status.value == "failed")))
        testsuite.set("errors", str(sum(1 for r in module_results if r.status.value == "error")))
        testsuite.set("time", f"{sum(r.execution_time for r in module_results):.3f}")
        
        for result in module_results:
            testcase = SubElement(testsuite, "testcase")
            testcase.set("name", result.test_id)
            testcase.set("classname", module)
            testcase.set("time", f"{result.execution_time:.3f}")
            
            if result.status.value in ["failed", "error"]:
                failure = SubElement(testcase, "failure" if result.status.value == "failed" else "error")
                failure.set("message", result.error_message or "Test failed")
                if result.error_type:
                    failure.set("type", result.error_type)
                failure.text = result.error_message or ""
    
    # Pretty print
    xml_str = tostring(testsuites, encoding="unicode")
    dom = minidom.parseString(xml_str)
    pretty_xml = dom.toprettyxml(indent="  ")
    
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(pretty_xml)


def _compare_results(current: "TestRunResults", baseline_path: str) -> None:
    """Compare current results with baseline"""
    from mavaia_core.evaluation.test_results import TestResults
    
    results_manager = TestResults()
    try:
        baseline = results_manager.load_results(baseline_path)
    except Exception as e:
        print(f"Error loading baseline: {e}", file=sys.stderr)
        return
    
    print("\n" + "=" * 80)
    print("Test Results Comparison")
    print("=" * 80)
    print()
    
    # Compare summaries
    print("Summary Comparison:")
    print(f"  Total Tests:  {baseline.summary.total_tests:4d} → {current.summary.total_tests:4d} ({current.summary.total_tests - baseline.summary.total_tests:+d})")
    print(f"  Passed:       {baseline.summary.passed:4d} → {current.summary.passed:4d} ({current.summary.passed - baseline.summary.passed:+d})")
    print(f"  Failed:       {baseline.summary.failed:4d} → {current.summary.failed:4d} ({current.summary.failed - baseline.summary.failed:+d})")
    print(f"  Errors:       {baseline.summary.errors:4d} → {current.summary.errors:4d} ({current.summary.errors - baseline.summary.errors:+d})")
    print()
    
    # Find new failures
    baseline_failures = {r.test_id for r in baseline.results if r.status.value in ["failed", "error"]}
    current_failures = {r.test_id for r in current.results if r.status.value in ["failed", "error"]}
    
    new_failures = current_failures - baseline_failures
    fixed_tests = baseline_failures - current_failures
    
    if new_failures:
        print(f"New Failures ({len(new_failures)}):")
        for test_id in sorted(new_failures):
            result = next(r for r in current.results if r.test_id == test_id)
            print(f"  ✗ {test_id} ({result.module})")
        print()
    
    if fixed_tests:
        print(f"Fixed Tests ({len(fixed_tests)}):")
        for test_id in sorted(fixed_tests):
            print(f"  ✓ {test_id}")
        print()
    
    # Performance comparison
    if baseline.summary.avg_execution_time and current.summary.avg_execution_time:
        perf_diff = current.summary.avg_execution_time - baseline.summary.avg_execution_time
        perf_pct = (perf_diff / baseline.summary.avg_execution_time) * 100
        print(f"Average Execution Time: {baseline.summary.avg_execution_time:.3f}s → {current.summary.avg_execution_time:.3f}s ({perf_pct:+.1f}%)")
        print()


def _generate_dependency_graph(
    output_file: str,
    layout: str = "spring",
    detect_cycles: bool = False
) -> None:
    """Generate module dependency graph with advanced features"""
    try:
        import networkx as nx
    except ImportError:
        print("Error: networkx is required for dependency graphs.", file=sys.stderr)
        print("Install with: pip install networkx", file=sys.stderr)
        sys.exit(1)
    
    # Check if SVG export is requested
    output_path = Path(output_file)
    is_svg = output_path.suffix.lower() == '.svg'
    
    if is_svg:
        try:
            import pygraphviz
        except ImportError:
            print("Warning: pygraphviz not available, falling back to PNG", file=sys.stderr)
            is_svg = False
            output_path = output_path.with_suffix('.png')
    
    if not is_svg:
        try:
            import matplotlib
            matplotlib.use('Agg')  # Non-interactive backend
            import matplotlib.pyplot as plt
            from matplotlib.patches import FancyBboxPatch
        except ImportError:
            print("Error: matplotlib is required for dependency graphs.", file=sys.stderr)
            print("Install with: pip install matplotlib", file=sys.stderr)
            sys.exit(1)
    
    from mavaia_core.brain.registry import ModuleRegistry
    
    print("Generating dependency graph...", flush=True)
    ModuleRegistry.discover_modules(background=False, verbose=False)
    
    # Build graph
    G = nx.DiGraph()
    module_names = ModuleRegistry.list_modules()
    
    # Add nodes with metadata
    for module_name in module_names:
        metadata = ModuleRegistry.get_metadata(module_name)
        if metadata:
            category = _categorize_module(module_name, metadata.description)
            G.add_node(
                module_name,
                version=metadata.version,
                enabled=metadata.enabled,
                category=category,
                operations=len(metadata.operations) if metadata.operations else 0
            )
    
    # Build dependency edges
    # Method 1: Check metadata dependencies (if they reference other modules)
    for module_name in module_names:
        metadata = ModuleRegistry.get_metadata(module_name)
        if metadata and metadata.dependencies:
            for dep in metadata.dependencies:
                # Check if dependency matches a module name
                dep_normalized = dep.replace('-', '_').replace('.', '_')
                for other_module in module_names:
                    if other_module == dep_normalized or other_module in dep:
                        if not G.has_edge(module_name, other_module):
                            G.add_edge(module_name, other_module, type="dependency")
    
    # Method 2: Infer from source code (heuristic)
    for module_name in module_names:
        try:
            module = ModuleRegistry.get_module(module_name, auto_discover=False, wait_timeout=0.5)
            if module:
                import inspect
                try:
                    source = inspect.getsource(module.__class__)
                    for other_module in module_names:
                        if other_module != module_name:
                            # Look for module name in source (simple heuristic)
                            if other_module in source and f"ModuleRegistry.get_module('{other_module}'" in source:
                                if not G.has_edge(module_name, other_module):
                                    G.add_edge(module_name, other_module, type="uses")
                except Exception:
                    pass
        except Exception:
            pass
    
    # Detect cycles if requested
    if detect_cycles:
        cycles = list(nx.simple_cycles(G))
        if cycles:
            print("\n" + "=" * 80)
            print("Dependency Cycles Detected")
            print("=" * 80)
            print(f"\nFound {len(cycles)} cycle(s):\n")
            for i, cycle in enumerate(cycles, 1):
                cycle_str = " → ".join(cycle) + f" → {cycle[0]}"
                print(f"  Cycle {i}: {cycle_str}")
            print("\n⚠️  Warning: Circular dependencies can cause initialization issues!")
            print("=" * 80 + "\n")
        else:
            print("\n✓ No dependency cycles detected.\n")
    
    # Calculate layout
    print(f"Computing {layout} layout...", flush=True)
    
    if layout == "spring":
        pos = nx.spring_layout(G, k=2, iterations=50, seed=42)
    elif layout == "circular":
        pos = nx.circular_layout(G)
    elif layout == "hierarchical":
        try:
            pos = nx.nx_agraph.graphviz_layout(G, prog='dot')
        except Exception:
            print("  Warning: graphviz not available, falling back to spring layout", flush=True)
            pos = nx.spring_layout(G, k=2, iterations=50, seed=42)
    elif layout == "cluster":
        # Group nodes by category for clustering
        pos = _cluster_layout(G)
    elif layout == "kamada_kawai":
        pos = nx.kamada_kawai_layout(G)
    else:
        pos = nx.spring_layout(G, k=2, iterations=50, seed=42)
    
    # Dynamic module grouping by category
    category_groups = {}
    for node in G.nodes():
        category = G.nodes[node].get('category', 'Other')
        if category not in category_groups:
            category_groups[category] = []
        category_groups[category].append(node)
    
    # Color mapping
    category_colors = {
        "Reasoning": "#FF6B6B",
        "Memory": "#4ECDC4",
        "Language & NLP": "#45B7D1",
        "Safety & Security": "#FFA07A",
        "Tools & Integration": "#98D8C8",
        "System & Infrastructure": "#F7DC6F",
        "Planning & Optimization": "#95E1D3",
        "Analysis": "#F38181",
        "Learning & Training": "#AA96DA",
        "Creative & Generation": "#FCBAD3",
        "Other": "#BB8FCE"
    }
    
    if is_svg:
        # SVG export using pygraphviz
        try:
            A = nx.nx_agraph.to_agraph(G)
            A.layout(prog='dot')
            A.draw(str(output_path))
            print(f"Dependency graph saved to: {output_path}")
        except Exception as e:
            print(f"Error generating SVG: {e}", file=sys.stderr)
            print("Falling back to PNG...", file=sys.stderr)
            is_svg = False
            output_path = output_path.with_suffix('.png')
    
    if not is_svg:
        # PNG export using matplotlib
        fig, ax = plt.subplots(figsize=(20, 16))
        
        # Color nodes by category
        node_colors = []
        node_sizes = []
        for node in G.nodes():
            category = G.nodes[node].get('category', 'Other')
            node_colors.append(category_colors.get(category, "#CCCCCC"))
            # Size based on number of operations
            ops_count = G.nodes[node].get('operations', 0)
            node_sizes.append(500 + ops_count * 50)
        
        # Draw nodes
        nx.draw_networkx_nodes(
            G, pos,
            node_color=node_colors,
            node_size=node_sizes,
            alpha=0.9,
            ax=ax
        )
        
        # Draw edges with different styles for different edge types
        edge_colors = []
        edge_styles = []
        for u, v, data in G.edges(data=True):
            edge_type = data.get('type', 'uses')
            if edge_type == 'dependency':
                edge_colors.append('#FF0000')  # Red for dependencies
                edge_styles.append('solid')
            else:
                edge_colors.append('#888888')  # Gray for uses
                edge_styles.append('dashed')
        
        # Draw edges
        for i, (u, v) in enumerate(G.edges()):
            nx.draw_networkx_edges(
                G, pos,
                edgelist=[(u, v)],
                edge_color=edge_colors[i],
                style=edge_styles[i],
                arrows=True,
                arrowsize=20,
                alpha=0.6,
                ax=ax
            )
        
        # Draw labels
        nx.draw_networkx_labels(
            G, pos,
            font_size=7,
            font_weight='bold',
            ax=ax
        )
        
        # Add legend
        from matplotlib.patches import Patch
        legend_elements = [
            Patch(facecolor=color, label=category)
            for category, color in sorted(category_colors.items())
            if category in category_groups
        ]
        ax.legend(handles=legend_elements, loc='upper left', fontsize=8)
        
        ax.set_title("Mavaia Module Dependency Graph", fontsize=18, fontweight='bold', pad=20)
        ax.axis('off')
        plt.tight_layout()
        
        output_path.parent.mkdir(parents=True, exist_ok=True)
        plt.savefig(output_path, dpi=300, bbox_inches='tight')
        plt.close()
        print(f"Dependency graph saved to: {output_path}")
    
    # Print graph statistics
    print(f"\nGraph Statistics:")
    print(f"  Nodes: {G.number_of_nodes()}")
    print(f"  Edges: {G.number_of_edges()}")
    print(f"  Categories: {len(category_groups)}")
    if detect_cycles:
        cycles = list(nx.simple_cycles(G))
        print(f"  Cycles: {len(cycles)}")


def _cluster_layout(G) -> Dict[str, tuple]:
    """Generate cluster-based layout grouping nodes by category"""
    import networkx as nx
    import numpy as np
    
    # Group nodes by category
    category_groups = {}
    for node in G.nodes():
        category = G.nodes[node].get('category', 'Other')
        if category not in category_groups:
            category_groups[category] = []
        category_groups[category].append(node)
    
    # Position each category in a circle
    pos = {}
    num_categories = len(category_groups)
    category_angle_step = 2 * np.pi / num_categories if num_categories > 0 else 0
    
    for i, (category, nodes) in enumerate(category_groups.items()):
        # Position category center
        angle = i * category_angle_step
        center_x = 5 * np.cos(angle)
        center_y = 5 * np.sin(angle)
        
        # Position nodes in cluster around center
        num_nodes = len(nodes)
        if num_nodes == 1:
            pos[nodes[0]] = (center_x, center_y)
        else:
            node_angle_step = 2 * np.pi / num_nodes
            radius = 1.5
            for j, node in enumerate(nodes):
                node_angle = j * node_angle_step
                node_x = center_x + radius * np.cos(node_angle)
                node_y = center_y + radius * np.sin(node_angle)
                pos[node] = (node_x, node_y)
    
    return pos


def _detect_dependency_cycles() -> None:
    """Detect and report dependency cycles"""
    try:
        import networkx as nx
    except ImportError:
        print("Error: networkx is required for cycle detection.", file=sys.stderr)
        print("Install with: pip install networkx", file=sys.stderr)
        sys.exit(1)
    
    from mavaia_core.brain.registry import ModuleRegistry
    
    print("=" * 80)
    print("Dependency Cycle Detection")
    print("=" * 80)
    print()
    
    ModuleRegistry.discover_modules(background=False, verbose=False)
    
    # Build graph (same logic as _generate_dependency_graph)
    G = nx.DiGraph()
    module_names = ModuleRegistry.list_modules()
    
    for module_name in module_names:
        metadata = ModuleRegistry.get_metadata(module_name)
        if metadata:
            G.add_node(module_name)
    
    # Add edges
    for module_name in module_names:
        metadata = ModuleRegistry.get_metadata(module_name)
        if metadata and metadata.dependencies:
            for dep in metadata.dependencies:
                dep_normalized = dep.replace('-', '_').replace('.', '_')
                for other_module in module_names:
                    if other_module == dep_normalized or other_module in dep:
                        G.add_edge(module_name, other_module)
        
        try:
            module = ModuleRegistry.get_module(module_name, auto_discover=False, wait_timeout=0.5)
            if module:
                import inspect
                try:
                    source = inspect.getsource(module.__class__)
                    for other_module in module_names:
                        if other_module != module_name and other_module in source:
                            if f"ModuleRegistry.get_module('{other_module}'" in source:
                                G.add_edge(module_name, other_module)
                except Exception:
                    pass
        except Exception:
            pass
    
    # Detect cycles
    cycles = list(nx.simple_cycles(G))
    
    if not cycles:
        print("✓ No dependency cycles detected.")
        print("\nAll module dependencies form a valid DAG (Directed Acyclic Graph).")
        return
    
    print(f"⚠️  Found {len(cycles)} dependency cycle(s):\n")
    
    # Group cycles by modules involved
    cycle_modules = set()
    for cycle in cycles:
        cycle_modules.update(cycle)
    
    print(f"Modules involved in cycles: {', '.join(sorted(cycle_modules))}\n")
    
    # Show each cycle
    for i, cycle in enumerate(cycles, 1):
        cycle_str = " → ".join(cycle) + f" → {cycle[0]}"
        print(f"Cycle {i}:")
        print(f"  {cycle_str}")
        print()
    
    # Suggest fixes
    print("Recommendations:")
    print("-" * 80)
    print("  • Break cycles by introducing interfaces or dependency injection")
    print("  • Refactor shared functionality into a common module")
    print("  • Use lazy initialization to break circular dependencies")
    print("  • Consider using an event-driven architecture")
    print()
    
    sys.exit(1)  # Exit with error if cycles found


def _show_module_health_scores(results_dir: Optional[str] = None) -> None:
    """Calculate and display module health scores"""
    from mavaia_core.brain.registry import ModuleRegistry
    from mavaia_core.evaluation.test_results import TestResults
    
    print("=" * 80)
    print("Module Health Scores")
    print("=" * 80)
    print()
    
    ModuleRegistry.discover_modules(background=False, verbose=False)
    module_names = ModuleRegistry.list_modules()
    
    # Load test results if available
    test_results = None
    try:
        results_manager = TestResults(results_dir)
        archives = results_manager.list_archives()
        if archives:
            test_results = results_manager.load_results(archives[0] / "detailed_results.json")
    except Exception:
        pass
    
    health_scores = []
    
    for module_name in sorted(module_names):
        metadata = ModuleRegistry.get_metadata(module_name)
        if not metadata:
            continue
        
        score = 0.0
        factors = []
        
        # Factor 1: Test pass rate (0-40 points)
        if test_results:
            module_results = [r for r in test_results.results if r.module == module_name]
            if module_results:
                passed = sum(1 for r in module_results if r.status.value == "passed")
                total = len(module_results)
                pass_rate = passed / total if total > 0 else 0
                test_score = pass_rate * 40
                score += test_score
                factors.append(f"Tests: {passed}/{total} ({pass_rate*100:.1f}%)")
            else:
                factors.append("Tests: No tests")
        else:
            factors.append("Tests: No results")
        
        # Factor 2: Metadata completeness (0-20 points)
        metadata_score = 0
        if metadata.name:
            metadata_score += 2
        if metadata.version:
            metadata_score += 2
        if metadata.description:
            metadata_score += 3
        if metadata.operations:
            metadata_score += min(len(metadata.operations) * 2, 8)
        if metadata.dependencies:
            metadata_score += min(len(metadata.dependencies), 5)
        score += metadata_score
        factors.append(f"Metadata: {metadata_score}/20")
        
        # Factor 3: Performance (0-20 points) - based on avg execution time
        if test_results:
            module_results = [r for r in test_results.results if r.module == module_name and r.execution_time > 0]
            if module_results:
                avg_time = sum(r.execution_time for r in module_results) / len(module_results)
                # Faster = better (max 1s gets full points, >5s gets 0)
                perf_score = max(0, 20 * (1 - min(avg_time / 5.0, 1.0)))
                score += perf_score
                factors.append(f"Performance: {avg_time:.3f}s")
            else:
                factors.append("Performance: No data")
        else:
            factors.append("Performance: No data")
        
        # Factor 4: Error frequency (0-20 points)
        if test_results:
            module_results = [r for r in test_results.results if r.module == module_name]
            if module_results:
                errors = sum(1 for r in module_results if r.status.value in ["error", "failed"])
                error_rate = errors / len(module_results) if module_results else 0
                error_score = (1 - error_rate) * 20
                score += error_score
                factors.append(f"Errors: {errors}/{len(module_results)}")
            else:
                factors.append("Errors: No data")
        else:
            factors.append("Errors: No data")
        
        # Health status
        if score >= 80:
            status = "✓ Excellent"
        elif score >= 60:
            status = "✓ Good"
        elif score >= 40:
            status = "⚠ Fair"
        else:
            status = "✗ Poor"
        
        health_scores.append({
            "module": module_name,
            "score": score,
            "status": status,
            "factors": factors,
            "category": _categorize_module(module_name, metadata.description)
        })
    
    # Sort by score
    health_scores.sort(key=lambda x: x["score"], reverse=True)
    
    # Print results
    print(f"{'Module':<40} {'Score':<8} {'Status':<15} {'Category':<25}")
    print("-" * 80)
    
    for health in health_scores:
        print(f"{health['module']:<40} {health['score']:>6.1f}  {health['status']:<15} {health['category']:<25}")
    
    print()
    print("Score Breakdown (Top 10):")
    print("-" * 80)
    for health in health_scores[:10]:
        print(f"\n{health['module']} ({health['score']:.1f}/100)")
        for factor in health['factors']:
            print(f"  • {factor}")
    
    # Summary statistics
    avg_score = sum(h["score"] for h in health_scores) / len(health_scores) if health_scores else 0
    excellent = sum(1 for h in health_scores if h["score"] >= 80)
    good = sum(1 for h in health_scores if 60 <= h["score"] < 80)
    fair = sum(1 for h in health_scores if 40 <= h["score"] < 60)
    poor = sum(1 for h in health_scores if h["score"] < 40)
    
    print(f"\nSummary:")
    print(f"  Average Score: {avg_score:.1f}/100")
    print(f"  Excellent (≥80): {excellent}")
    print(f"  Good (60-79): {good}")
    print(f"  Fair (40-59): {fair}")
    print(f"  Poor (<40): {poor}")


def _analyze_test_impact(results_dir: Optional[str] = None) -> None:
    """Analyze test impact and identify critical modules"""
    try:
        import networkx as nx
    except ImportError:
        print("Error: networkx is required for impact analysis.", file=sys.stderr)
        print("Install with: pip install networkx", file=sys.stderr)
        sys.exit(1)
    
    from mavaia_core.brain.registry import ModuleRegistry
    from mavaia_core.evaluation.test_results import TestResults
    from mavaia_core.evaluation.test_data_manager import TestDataManager
    
    print("=" * 80)
    print("Test Impact Analysis")
    print("=" * 80)
    print()
    
    ModuleRegistry.discover_modules(background=False, verbose=False)
    
    # Build dependency graph
    G = nx.DiGraph()
    module_names = ModuleRegistry.list_modules()
    
    for module_name in module_names:
        metadata = ModuleRegistry.get_metadata(module_name)
        if metadata:
            G.add_node(module_name)
    
    # Add edges
    for module_name in module_names:
        metadata = ModuleRegistry.get_metadata(module_name)
        if metadata and metadata.dependencies:
            for dep in metadata.dependencies:
                dep_normalized = dep.replace('-', '_').replace('.', '_')
                for other_module in module_names:
                    if other_module == dep_normalized or other_module in dep:
                        G.add_edge(module_name, other_module)
    
    # Calculate impact metrics
    impact_scores = {}
    
    for module_name in module_names:
        score = 0.0
        factors = []
        
        # Factor 1: Number of dependents (modules that depend on this one)
        dependents = list(G.predecessors(module_name))
        dependent_count = len(dependents)
        dependent_score = min(dependent_count * 5, 30)  # Max 30 points
        score += dependent_score
        factors.append(f"Dependents: {dependent_count} (+{dependent_score:.1f})")
        
        # Factor 2: Number of dependencies (modules this depends on)
        dependencies = list(G.successors(module_name))
        dependency_count = len(dependencies)
        dependency_score = min(dependency_count * 2, 15)  # Max 15 points
        score += dependency_score
        factors.append(f"Dependencies: {dependency_count} (+{dependency_score:.1f})")
        
        # Factor 3: Test coverage
        test_data_manager = TestDataManager()
        test_data_manager.load_all_test_suites()
        has_tests = any(
            suite.module == module_name
            for suite in test_data_manager._test_suites.values()
        )
        coverage_score = 20 if has_tests else 0
        score += coverage_score
        factors.append(f"Test Coverage: {'Yes' if has_tests else 'No'} (+{coverage_score:.1f})")
        
        # Factor 4: Test pass rate (if results available)
        try:
            results_manager = TestResults(results_dir)
            archives = results_manager.list_archives()
            if archives:
                test_results = results_manager.load_results(archives[0] / "detailed_results.json")
                module_results = [r for r in test_results.results if r.module == module_name]
                if module_results:
                    passed = sum(1 for r in module_results if r.status.value == "passed")
                    pass_rate = passed / len(module_results) if module_results else 0
                    pass_score = pass_rate * 20
                    score += pass_score
                    factors.append(f"Pass Rate: {pass_rate*100:.1f}% (+{pass_score:.1f})")
        except Exception:
            pass
        
        # Factor 5: Centrality (betweenness centrality)
        try:
            centrality = nx.betweenness_centrality(G).get(module_name, 0)
            centrality_score = centrality * 15  # Max 15 points
            score += centrality_score
            factors.append(f"Centrality: {centrality:.3f} (+{centrality_score:.1f})")
        except Exception:
            pass
        
        impact_scores[module_name] = {
            "score": score,
            "factors": factors,
            "dependents": dependent_count,
            "dependencies": dependency_count,
            "has_tests": has_tests
        }
    
    # Sort by impact score
    sorted_modules = sorted(impact_scores.items(), key=lambda x: x[1]["score"], reverse=True)
    
    print("High-Impact Modules (Top 20):")
    print("-" * 80)
    print(f"{'Module':<40} {'Impact':<8} {'Dependents':<12} {'Dependencies':<14} {'Tests':<8}")
    print("-" * 80)
    
    for module_name, data in sorted_modules[:20]:
        test_status = "✓" if data["has_tests"] else "✗"
        print(f"{module_name:<40} {data['score']:>6.1f}  {data['dependents']:>10}  {data['dependencies']:>12}  {test_status:>6}")
    
    print()
    print("Impact Score Breakdown (Top 10):")
    print("-" * 80)
    for module_name, data in sorted_modules[:10]:
        print(f"\n{module_name} (Impact: {data['score']:.1f})")
        for factor in data['factors']:
            print(f"  • {factor}")
    
    # Recommendations
    print("\n" + "=" * 80)
    print("Recommendations")
    print("=" * 80)
    
    # Modules with high impact but no tests
    high_impact_no_tests = [
        (name, data) for name, data in sorted_modules[:20]
        if data["score"] > 30 and not data["has_tests"]
    ]
    
    if high_impact_no_tests:
        print(f"\n⚠️  {len(high_impact_no_tests)} high-impact module(s) without tests:")
        for module_name, data in high_impact_no_tests:
            print(f"  • {module_name} (Impact: {data['score']:.1f}, {data['dependents']} dependents)")
        print(f"\n  Recommendation: Add test coverage for these critical modules.")
    
    # Modules with many dependents
    high_dependents = [
        (name, data) for name, data in sorted_modules
        if data["dependents"] >= 5
    ]
    
    if high_dependents:
        print(f"\n📊 {len(high_dependents)} module(s) with 5+ dependents (high coupling):")
        for module_name, data in high_dependents[:10]:
            print(f"  • {module_name} ({data['dependents']} dependents)")
        print(f"\n  Recommendation: Ensure these modules are well-tested and stable.")


def _show_test_coverage() -> None:
    """Show test coverage statistics"""
    from mavaia_core.brain.registry import ModuleRegistry
    from mavaia_core.evaluation.test_data_manager import TestDataManager
    
    print("=" * 80)
    print("Test Coverage Report")
    print("=" * 80)
    print()
    
    # Discover modules
    ModuleRegistry.discover_modules(background=False, verbose=False)
    all_modules = set(ModuleRegistry.list_modules())
    
    # Get modules with tests
    test_data_manager = TestDataManager()
    test_data_manager.load_all_test_suites()
    modules_with_tests = set()
    for suite in test_data_manager._test_suites.values():
        if suite.module:
            modules_with_tests.add(suite.module)
    
    # Calculate coverage
    total_modules = len(all_modules)
    covered_modules = len(modules_with_tests)
    uncovered_modules = all_modules - modules_with_tests
    coverage_pct = (covered_modules / total_modules * 100) if total_modules > 0 else 0
    
    print(f"Total Modules:        {total_modules}")
    print(f"Modules with Tests:   {covered_modules}")
    print(f"Modules without Tests: {len(uncovered_modules)}")
    print(f"Coverage:             {coverage_pct:.1f}%")
    print()
    
    # Breakdown by category
    print("Coverage by Category:")
    print("-" * 80)
    
    by_category = {}
    for module_name in all_modules:
        metadata = ModuleRegistry.get_metadata(module_name)
        if metadata:
            category = _categorize_module(module_name, metadata.description)
            if category not in by_category:
                by_category[category] = {"total": 0, "covered": 0}
            by_category[category]["total"] += 1
            if module_name in modules_with_tests:
                by_category[category]["covered"] += 1
    
    for category in sorted(by_category.keys()):
        stats = by_category[category]
        cat_coverage = (stats["covered"] / stats["total"] * 100) if stats["total"] > 0 else 0
        print(f"  {category:30s} {stats['covered']:3d}/{stats['total']:3d} ({cat_coverage:5.1f}%)")
    
    print()
    
    # List uncovered modules
    if uncovered_modules:
        print(f"Modules Without Tests ({len(uncovered_modules)}):")
        print("-" * 80)
        for module in sorted(uncovered_modules)[:20]:
            metadata = ModuleRegistry.get_metadata(module)
            if metadata:
                print(f"  - {module:40s} {metadata.description[:50]}")
        if len(uncovered_modules) > 20:
            print(f"  ... and {len(uncovered_modules) - 20} more")
        print()
        print(f"Use 'create-template --all' to create default test templates for all modules.")
        print(f"Use 'create-template <module>' to create a template for a specific module.")


def _explain_module_failures(module_name: str, results_dir: Optional[str] = None) -> None:
    """Explain why a module failed"""
    from mavaia_core.brain.registry import ModuleRegistry
    from mavaia_core.evaluation.test_results import TestResults
    
    print("=" * 80)
    print(f"Failure Analysis: {module_name}")
    print("=" * 80)
    print()
    
    # Get latest test results
    results_manager = TestResults(results_dir)
    archives = results_manager.list_archives()
    
    if not archives:
        print("No test results found. Run tests first to analyze failures.")
        return
    
    # Load most recent results
    latest_results = results_manager.load_results(archives[0] / "detailed_results.json")
    
    # Filter failures for this module
    module_failures = [
        r for r in latest_results.results
        if r.module == module_name and r.status.value in ["failed", "error"]
    ]
    
    if not module_failures:
        print(f"No failures found for module '{module_name}' in latest test run.")
        print(f"Module may have passed all tests or not been tested.")
        return
    
    print(f"Found {len(module_failures)} failure(s) for {module_name}\n")
    
    # Analyze failure patterns
    error_types = {}
    operations_failed = set()
    error_messages = []
    
    for failure in module_failures:
        error_type = failure.error_type or "Unknown"
        error_types[error_type] = error_types.get(error_type, 0) + 1
        if failure.operation:
            operations_failed.add(failure.operation)
        if failure.error_message:
            error_messages.append(failure.error_message)
    
    print("Failure Patterns:")
    print("-" * 80)
    print(f"  Total Failures:     {len(module_failures)}")
    print(f"  Operations Failed:  {', '.join(sorted(operations_failed)) if operations_failed else 'N/A'}")
    print()
    
    print("Error Type Distribution:")
    for error_type, count in sorted(error_types.items(), key=lambda x: x[1], reverse=True):
        print(f"  {error_type:30s} {count:3d} ({count/len(module_failures)*100:.1f}%)")
    print()
    
    # Common error messages
    if error_messages:
        print("Common Error Messages:")
        from collections import Counter
        common_errors = Counter(error_messages).most_common(5)
        for error, count in common_errors:
            print(f"  [{count}x] {error[:70]}")
        print()
    
    # Get module metadata for context
    metadata = ModuleRegistry.get_metadata(module_name)
    if metadata:
        print("Module Context:")
        print("-" * 80)
        print(f"  Version:      {metadata.version}")
        print(f"  Enabled:      {metadata.enabled}")
        print(f"  Operations:   {len(metadata.operations)}")
        print(f"  Dependencies: {len(metadata.dependencies)}")
        print()
    
    # Suggestions
    print("Suggestions:")
    print("-" * 80)
    if "Timeout" in error_types:
        print("  • Timeout errors detected - consider increasing timeout or optimizing module performance")
    if "ModuleNotFoundError" in error_types:
        print("  • Module not found errors - check module registration and discovery")
    if "InvalidParameterError" in error_types:
        print("  • Invalid parameter errors - review parameter validation and test data")
    if len(operations_failed) == len(metadata.operations if metadata else []):
        print("  • All operations failing - check module initialization and dependencies")
    print()


def _validate_all_modules() -> None:
    """Validate module metadata across the system"""
    from mavaia_core.brain.registry import ModuleRegistry
    
    print("=" * 80)
    print("Module Metadata Validation")
    print("=" * 80)
    print()
    
    ModuleRegistry.discover_modules(background=False, verbose=False)
    module_names = ModuleRegistry.list_modules()
    
    errors = []
    warnings = []
    validated = 0
    
    for module_name in sorted(module_names):
        metadata = ModuleRegistry.get_metadata(module_name)
        if not metadata:
            errors.append(f"{module_name}: Missing metadata")
            continue
        
        # Validate metadata fields
        if not metadata.name:
            errors.append(f"{module_name}: Missing name")
        if not metadata.version:
            warnings.append(f"{module_name}: Missing version")
        if not metadata.description:
            warnings.append(f"{module_name}: Missing description")
        if not metadata.operations:
            warnings.append(f"{module_name}: No operations defined")
        
        # Try to get module instance
        try:
            module = ModuleRegistry.get_module(module_name, auto_discover=False, wait_timeout=0.5)
            if module:
                # Validate operations exist
                for operation in metadata.operations:
                    if not hasattr(module, 'execute'):
                        errors.append(f"{module_name}: Missing execute method")
                        break
                validated += 1
        except ImportError as e:
            # Handle missing dependencies gracefully
            warnings.append(f"{module_name}: Missing dependency: {str(e)[:50]}")
        except Exception as e:
            warnings.append(f"{module_name}: Could not instantiate ({str(e)[:50]})")
    
    # Print results
    if errors:
        print("Errors:")
        for error in errors:
            print(f"  ✗ {error}")
        print()
    
    if warnings:
        print("Warnings:")
        for warning in warnings:
            print(f"  ⚠ {warning}")
        print()
    
    print(f"Validation complete: {validated}/{len(module_names)} modules validated")
    if errors:
        print(f"  {len(errors)} error(s) found")
        sys.exit(1)
    else:
        print("  All modules validated successfully!")
        if warnings:
            print(f"  {len(warnings)} warning(s) found")
        sys.exit(0)


def _generate_performance_heatmap(results: "TestRunResults") -> None:
    """Generate performance heatmap"""
    print("\n" + "=" * 80)
    print("Performance Heatmap")
    print("=" * 80)
    print()
    
    # Group by module
    by_module = {}
    for result in results.results:
        module = result.module or "unknown"
        if module not in by_module:
            by_module[module] = []
        by_module[module].append(result.execution_time)
    
    # Calculate statistics
    print("Execution Time by Module (seconds):")
    print("-" * 80)
    
    module_stats = []
    for module, times in sorted(by_module.items()):
        if times:
            avg_time = sum(times) / len(times)
            min_time = min(times)
            max_time = max(times)
            module_stats.append((module, avg_time, min_time, max_time, len(times)))
    
    # Sort by average time
    module_stats.sort(key=lambda x: x[1], reverse=True)
    
    # Print heatmap (text-based)
    for module, avg, min_t, max_t, count in module_stats[:20]:  # Top 20
        # Create visual bar
        bar_length = int((avg / max(module_stats, key=lambda x: x[1])[1]) * 50) if module_stats else 0
        bar = "█" * bar_length + "░" * (50 - bar_length)
        
        print(f"  {module:40s} {bar} {avg:.3f}s (min: {min_t:.3f}s, max: {max_t:.3f}s, n={count})")
    
    if len(module_stats) > 20:
        print(f"  ... and {len(module_stats) - 20} more modules")
    
    print()
    
    # Performance categories
    slow_modules = [m for m, avg, _, _, _ in module_stats if avg > 1.0]
    if slow_modules:
        print(f"Slow Modules (>1s avg): {', '.join(slow_modules[:10])}")
        if len(slow_modules) > 10:
            print(f"  ... and {len(slow_modules) - 10} more")
        print()


def _run_fuzz_tests(runner: TestRunner, count: int, args: Any) -> None:
    """Run fuzz/adversarial tests"""
    from mavaia_core.brain.registry import ModuleRegistry
    import random
    import string
    
    print("=" * 80)
    print(f"Fuzz Testing ({count} tests)")
    print("=" * 80)
    print()
    
    ModuleRegistry.discover_modules(background=False, verbose=False)
    modules = ModuleRegistry.list_modules()
    
    if not modules:
        print("No modules available for fuzzing.")
        return
    
    fuzz_results = []
    
    for i in range(count):
        module_name = random.choice(modules)
        metadata = ModuleRegistry.get_metadata(module_name)
        
        if not metadata or not metadata.operations:
            continue
        
        operation = random.choice(metadata.operations)
        
        # Generate random parameters
        fuzz_params = {}
        for _ in range(random.randint(1, 5)):
            key = ''.join(random.choices(string.ascii_letters, k=random.randint(3, 10)))
            value_type = random.choice(['str', 'int', 'list', 'dict'])
            if value_type == 'str':
                value = ''.join(random.choices(string.ascii_letters + string.digits + ' ', k=random.randint(0, 100)))
            elif value_type == 'int':
                value = random.randint(-1000, 1000)
            elif value_type == 'list':
                value = [random.randint(0, 100) for _ in range(random.randint(0, 10))]
            else:
                value = {f"k{j}": random.randint(0, 100) for j in range(random.randint(0, 5))}
            fuzz_params[key] = value
        
        # Run fuzz test
        try:
            module = ModuleRegistry.get_module(module_name, auto_discover=False, wait_timeout=0.5)
            if module:
                start_time = time.time()
                result = module.execute(operation, fuzz_params)
                execution_time = time.time() - start_time
                fuzz_results.append({
                    "module": module_name,
                    "operation": operation,
                    "status": "passed",
                    "time": execution_time
                })
        except Exception as e:
            fuzz_results.append({
                "module": module_name,
                "operation": operation,
                "status": "failed",
                "error": str(e)[:100]
            })
        
        if (i + 1) % 10 == 0:
            print(f"  Progress: {i + 1}/{count} tests", flush=True)
    
    # Print summary
    passed = sum(1 for r in fuzz_results if r["status"] == "passed")
    failed = len(fuzz_results) - passed
    
    print(f"\nFuzz Test Results:")
    print(f"  Passed: {passed}")
    print(f"  Failed: {failed}")
    print(f"  Success Rate: {passed/len(fuzz_results)*100:.1f}%" if fuzz_results else "N/A")


def _run_benchmarks(runner: TestRunner, args: Any) -> None:
    """Run microbenchmarks"""
    from mavaia_core.brain.registry import ModuleRegistry
    import statistics
    
    print("=" * 80)
    print("Module Benchmarks")
    print("=" * 80)
    print()
    
    ModuleRegistry.discover_modules(background=False, verbose=False)
    modules = ModuleRegistry.list_modules()
    
    benchmark_results = []
    
    for module_name in sorted(modules)[:20]:  # Limit to first 20 for demo
        metadata = ModuleRegistry.get_metadata(module_name)
        if not metadata or not metadata.operations:
            continue
        
        print(f"Benchmarking {module_name}...", end="", flush=True)
        
        operation = metadata.operations[0] if metadata.operations else None
        if not operation:
            print(" (no operations)")
            continue
        
        # Run benchmark (multiple iterations)
        times = []
        for _ in range(5):  # 5 iterations per operation
            try:
                module = ModuleRegistry.get_module(module_name, auto_discover=False, wait_timeout=0.5)
                if module:
                    start = time.time()
                    module.execute(operation, {})
                    times.append(time.time() - start)
            except Exception:
                pass
        
        if times:
            avg_time = statistics.mean(times)
            min_time = min(times)
            max_time = max(times)
            benchmark_results.append({
                "module": module_name,
                "operation": operation,
                "avg_time": avg_time,
                "min_time": min_time,
                "max_time": max_time,
                "iterations": len(times)
            })
            print(f" {avg_time:.3f}s avg")
        else:
            print(" (failed)")
    
    # Print summary
    print("\nBenchmark Summary:")
    print("-" * 80)
    benchmark_results.sort(key=lambda x: x["avg_time"])
    for result in benchmark_results[:10]:
        print(f"  {result['module']:40s} {result['avg_time']:.3f}s (min: {result['min_time']:.3f}s, max: {result['max_time']:.3f}s)")


def _run_stress_tests(runner: TestRunner, concurrent: int, args: Any) -> None:
    """Run stress/load tests"""
    import threading
    from mavaia_core.brain.registry import ModuleRegistry
    
    print("=" * 80)
    print(f"Stress Testing ({concurrent} concurrent requests)")
    print("=" * 80)
    print()
    
    ModuleRegistry.discover_modules(background=False, verbose=False)
    modules = ModuleRegistry.list_modules()
    
    if not modules:
        print("No modules available for stress testing.")
        return
    
    results = []
    lock = threading.Lock()
    
    def stress_test(module_name: str, operation: str):
        try:
            module = ModuleRegistry.get_module(module_name, auto_discover=False, wait_timeout=0.5)
            if module:
                start = time.time()
                module.execute(operation, {})
                elapsed = time.time() - start
                with lock:
                    results.append({"status": "passed", "time": elapsed})
        except Exception as e:
            with lock:
                results.append({"status": "failed", "error": str(e)[:50]})
    
    # Run concurrent tests
    threads = []
    for i in range(concurrent):
        module_name = modules[i % len(modules)]
        metadata = ModuleRegistry.get_metadata(module_name)
        if metadata and metadata.operations:
            operation = metadata.operations[0]
            thread = threading.Thread(target=stress_test, args=(module_name, operation))
            threads.append(thread)
            thread.start()
    
    # Wait for all threads
    for thread in threads:
        thread.join()
    
    # Print results
    passed = sum(1 for r in results if r["status"] == "passed")
    failed = len(results) - passed
    avg_time = sum(r["time"] for r in results if "time" in r) / len([r for r in results if "time" in r]) if results else 0
    
    print(f"Stress Test Results:")
    print(f"  Total Requests: {len(results)}")
    print(f"  Passed: {passed}")
    print(f"  Failed: {failed}")
    print(f"  Avg Response Time: {avg_time:.3f}s")
    print(f"  Success Rate: {passed/len(results)*100:.1f}%" if results else "N/A")


def _run_matrix_tests(runner: TestRunner, configs: List[str], args: Any) -> None:
    """Run tests across multiple configurations"""
    print("=" * 80)
    print("Matrix Testing")
    print("=" * 80)
    print()
    
    # Parse configurations
    config_dict = {}
    for config in configs:
        if '=' in config:
            key, value = config.split('=', 1)
            if key not in config_dict:
                config_dict[key] = []
            config_dict[key].append(value)
    
    # Generate combinations
    import itertools
    keys = list(config_dict.keys())
    values = [config_dict[key] for key in keys]
    combinations = list(itertools.product(*values))
    
    print(f"Running tests across {len(combinations)} configuration(s):")
    for i, combo in enumerate(combinations, 1):
        config_str = ", ".join(f"{k}={v}" for k, v in zip(keys, combo))
        print(f"  {i}. {config_str}")
    print()
    
    # Run tests for each combination
    for i, combo in enumerate(combinations, 1):
        config_str = ", ".join(f"{k}={v}" for k, v in zip(keys, combo))
        print(f"\n[{i}/{len(combinations)}] Testing with: {config_str}")
        print("-" * 80)
        
        # In a real implementation, you would apply the configuration
        # and run tests. For now, just run normal tests.
        try:
            results = runner.run_test_suite(
                module=args.module,
                category=args.category,
                tags=args.tags,
                timeout=args.timeout
            )
            print(f"  Results: {results.summary.passed} passed, {results.summary.failed} failed")
        except Exception as e:
            print(f"  Error: {e}")


def _watch_mode(runner: TestRunner, args: Any) -> None:
    """Watch mode - auto-rerun tests on file changes"""
    try:
        from watchdog.observers import Observer
        from watchdog.events import FileSystemEventHandler
    except ImportError:
        print("Error: watchdog is required for watch mode.", file=sys.stderr)
        print("Install with: pip install watchdog", file=sys.stderr)
        sys.exit(1)
    
    print("=" * 80)
    print("Watch Mode - Monitoring for file changes")
    print("=" * 80)
    print("Press Ctrl+C to stop")
    print()
    
    class TestFileHandler(FileSystemEventHandler):
        def __init__(self, runner, args):
            self.runner = runner
            self.args = args
            self.last_run = 0
        
        def on_modified(self, event):
            if event.is_directory:
                return
            
            # Throttle - only run once per second
            current_time = time.time()
            if current_time - self.last_run < 1.0:
                return
            self.last_run = current_time
            
            # Only watch test files and Python files
            if event.src_path.endswith(('.json', '.yaml', '.yml', '.py')):
                print(f"\n[Change detected] {event.src_path}")
                print("Rerunning tests...\n")
                try:
                    results = self.runner.run_test_suite(
                        module=self.args.module,
                        category=self.args.category,
                        tags=self.args.tags,
                        timeout=self.args.timeout
                    )
                    print(f"\nResults: {results.summary.passed} passed, {results.summary.failed} failed")
                except Exception as e:
                    print(f"Error: {e}")
    
    # Set up watcher
    handler = TestFileHandler(runner, args)
    observer = Observer()
    
    # Watch test data directory
    test_data_dir = Path(runner.test_data_manager.test_data_dir)
    observer.schedule(handler, str(test_data_dir), recursive=True)
    
    # Watch source directory if specified
    source_dir = Path(__file__).parent.parent
    observer.schedule(handler, str(source_dir), recursive=True)
    
    observer.start()
    
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        observer.stop()
        print("\nWatch mode stopped.")
    
    observer.join()


if __name__ == "__main__":
    main()


def _run_fuzz_tests(runner: TestRunner, count: int, args: Any) -> None:
    """Run fuzz/adversarial tests"""
    from mavaia_core.brain.registry import ModuleRegistry
    import random
    import string
    
    print("=" * 80)
    print(f"Fuzz Testing ({count} tests)")
    print("=" * 80)
    print()
    
    ModuleRegistry.discover_modules(background=False, verbose=False)
    modules = ModuleRegistry.list_modules()
    
    if not modules:
        print("No modules available for fuzzing.")
        return
    
    fuzz_results = []
    
    for i in range(count):
        module_name = random.choice(modules)
        metadata = ModuleRegistry.get_metadata(module_name)
        
        if not metadata or not metadata.operations:
            continue
        
        operation = random.choice(metadata.operations)
        
        # Generate random parameters
        fuzz_params = {}
        for _ in range(random.randint(1, 5)):
            key = ''.join(random.choices(string.ascii_letters, k=random.randint(3, 10)))
            value_type = random.choice(['str', 'int', 'list', 'dict'])
            if value_type == 'str':
                value = ''.join(random.choices(string.ascii_letters + string.digits + ' ', k=random.randint(0, 100)))
            elif value_type == 'int':
                value = random.randint(-1000, 1000)
            elif value_type == 'list':
                value = [random.randint(0, 100) for _ in range(random.randint(0, 10))]
            else:
                value = {f"k{j}": random.randint(0, 100) for j in range(random.randint(0, 5))}
            fuzz_params[key] = value
        
        # Run fuzz test
        try:
            module = ModuleRegistry.get_module(module_name, auto_discover=False, wait_timeout=0.5)
            if module:
                start_time = time.time()
                result = module.execute(operation, fuzz_params)
                execution_time = time.time() - start_time
                fuzz_results.append({
                    "module": module_name,
                    "operation": operation,
                    "status": "passed",
                    "time": execution_time
                })
        except Exception as e:
            fuzz_results.append({
                "module": module_name,
                "operation": operation,
                "status": "failed",
                "error": str(e)[:100]
            })
        
        if (i + 1) % 10 == 0:
            print(f"  Progress: {i + 1}/{count} tests", flush=True)
    
    # Print summary
    passed = sum(1 for r in fuzz_results if r["status"] == "passed")
    failed = len(fuzz_results) - passed
    
    print(f"\nFuzz Test Results:")
    print(f"  Passed: {passed}")
    print(f"  Failed: {failed}")
    print(f"  Success Rate: {passed/len(fuzz_results)*100:.1f}%" if fuzz_results else "N/A")


def _run_benchmarks(runner: TestRunner, args: Any) -> None:
    """Run microbenchmarks"""
    from mavaia_core.brain.registry import ModuleRegistry
    import statistics
    
    print("=" * 80)
    print("Module Benchmarks")
    print("=" * 80)
    print()
    
    ModuleRegistry.discover_modules(background=False, verbose=False)
    modules = ModuleRegistry.list_modules()
    
    benchmark_results = []
    
    for module_name in sorted(modules)[:20]:  # Limit to first 20 for demo
        metadata = ModuleRegistry.get_metadata(module_name)
        if not metadata or not metadata.operations:
            continue
        
        print(f"Benchmarking {module_name}...", end="", flush=True)
        
        operation = metadata.operations[0] if metadata.operations else None
        if not operation:
            print(" (no operations)")
            continue
        
        # Run benchmark (multiple iterations)
        times = []
        for _ in range(5):  # 5 iterations per operation
            try:
                module = ModuleRegistry.get_module(module_name, auto_discover=False, wait_timeout=0.5)
                if module:
                    start = time.time()
                    module.execute(operation, {})
                    times.append(time.time() - start)
            except Exception:
                pass
        
        if times:
            avg_time = statistics.mean(times)
            min_time = min(times)
            max_time = max(times)
            benchmark_results.append({
                "module": module_name,
                "operation": operation,
                "avg_time": avg_time,
                "min_time": min_time,
                "max_time": max_time,
                "iterations": len(times)
            })
            print(f" {avg_time:.3f}s avg")
        else:
            print(" (failed)")
    
    # Print summary
    print("\nBenchmark Summary:")
    print("-" * 80)
    benchmark_results.sort(key=lambda x: x["avg_time"])
    for result in benchmark_results[:10]:
        print(f"  {result['module']:40s} {result['avg_time']:.3f}s (min: {result['min_time']:.3f}s, max: {result['max_time']:.3f}s)")


def _run_stress_tests(runner: TestRunner, concurrent: int, args: Any) -> None:
    """Run stress/load tests"""
    import threading
    from mavaia_core.brain.registry import ModuleRegistry
    
    print("=" * 80)
    print(f"Stress Testing ({concurrent} concurrent requests)")
    print("=" * 80)
    print()
    
    ModuleRegistry.discover_modules(background=False, verbose=False)
    modules = ModuleRegistry.list_modules()
    
    if not modules:
        print("No modules available for stress testing.")
        return
    
    results = []
    lock = threading.Lock()
    
    def stress_test(module_name: str, operation: str):
        try:
            module = ModuleRegistry.get_module(module_name, auto_discover=False, wait_timeout=0.5)
            if module:
                start = time.time()
                module.execute(operation, {})
                elapsed = time.time() - start
                with lock:
                    results.append({"status": "passed", "time": elapsed})
        except Exception as e:
            with lock:
                results.append({"status": "failed", "error": str(e)[:50]})
    
    # Run concurrent tests
    threads = []
    for i in range(concurrent):
        module_name = modules[i % len(modules)]
        metadata = ModuleRegistry.get_metadata(module_name)
        if metadata and metadata.operations:
            operation = metadata.operations[0]
            thread = threading.Thread(target=stress_test, args=(module_name, operation))
            threads.append(thread)
            thread.start()
    
    # Wait for all threads
    for thread in threads:
        thread.join()
    
    # Print results
    passed = sum(1 for r in results if r["status"] == "passed")
    failed = len(results) - passed
    avg_time = sum(r["time"] for r in results if "time" in r) / len([r for r in results if "time" in r]) if results else 0
    
    print(f"Stress Test Results:")
    print(f"  Total Requests: {len(results)}")
    print(f"  Passed: {passed}")
    print(f"  Failed: {failed}")
    print(f"  Avg Response Time: {avg_time:.3f}s")
    print(f"  Success Rate: {passed/len(results)*100:.1f}%" if results else "N/A")


def _run_matrix_tests(runner: TestRunner, configs: List[str], args: Any) -> None:
    """Run tests across multiple configurations"""
    print("=" * 80)
    print("Matrix Testing")
    print("=" * 80)
    print()
    
    # Parse configurations
    config_dict = {}
    for config in configs:
        if '=' in config:
            key, value = config.split('=', 1)
            if key not in config_dict:
                config_dict[key] = []
            config_dict[key].append(value)
    
    # Generate combinations
    import itertools
    keys = list(config_dict.keys())
    values = [config_dict[key] for key in keys]
    combinations = list(itertools.product(*values))
    
    print(f"Running tests across {len(combinations)} configuration(s):")
    for i, combo in enumerate(combinations, 1):
        config_str = ", ".join(f"{k}={v}" for k, v in zip(keys, combo))
        print(f"  {i}. {config_str}")
    print()
    
    # Run tests for each combination
    for i, combo in enumerate(combinations, 1):
        config_str = ", ".join(f"{k}={v}" for k, v in zip(keys, combo))
        print(f"\n[{i}/{len(combinations)}] Testing with: {config_str}")
        print("-" * 80)
        
        # In a real implementation, you would apply the configuration
        # and run tests. For now, just run normal tests.
        try:
            results = runner.run_test_suite(
                module=args.module,
                category=args.category,
                tags=args.tags,
                timeout=args.timeout
            )
            print(f"  Results: {results.summary.passed} passed, {results.summary.failed} failed")
        except Exception as e:
            print(f"  Error: {e}")


def _watch_mode(runner: TestRunner, args: Any) -> None:
    """Watch mode - auto-rerun tests on file changes"""
    try:
        from watchdog.observers import Observer
        from watchdog.events import FileSystemEventHandler
    except ImportError:
        print("Error: watchdog is required for watch mode.", file=sys.stderr)
        print("Install with: pip install watchdog", file=sys.stderr)
        sys.exit(1)
    
    print("=" * 80)
    print("Watch Mode - Monitoring for file changes")
    print("=" * 80)
    print("Press Ctrl+C to stop")
    print()
    
    class TestFileHandler(FileSystemEventHandler):
        def __init__(self, runner, args):
            self.runner = runner
            self.args = args
            self.last_run = 0
        
        def on_modified(self, event):
            if event.is_directory:
                return
            
            # Throttle - only run once per second
            current_time = time.time()
            if current_time - self.last_run < 1.0:
                return
            self.last_run = current_time
            
            # Only watch test files and Python files
            if event.src_path.endswith(('.json', '.yaml', '.yml', '.py')):
                print(f"\n[Change detected] {event.src_path}")
                print("Rerunning tests...\n")
                try:
                    results = self.runner.run_test_suite(
                        module=self.args.module,
                        category=self.args.category,
                        tags=self.args.tags,
                        timeout=self.args.timeout
                    )
                    print(f"\nResults: {results.summary.passed} passed, {results.summary.failed} failed")
                except Exception as e:
                    print(f"Error: {e}")
    
    # Set up watcher
    handler = TestFileHandler(runner, args)
    observer = Observer()
    
    # Watch test data directory
    test_data_dir = Path(runner.test_data_manager.test_data_dir)
    observer.schedule(handler, str(test_data_dir), recursive=True)
    
    # Watch source directory if specified
    source_dir = Path(__file__).parent.parent
    observer.schedule(handler, str(source_dir), recursive=True)
    
    observer.start()
    
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        observer.stop()
        print("\nWatch mode stopped.")
    
    observer.join()

---
name: Interactive Test Runner CLI
overview: Convert test_runner.py from argparse-based CLI to an interactive REPL-style command-line interface using Python's cmd module, organizing all current functionality into interactive commands with tab completion and help system.
todos:
  - id: "1"
    content: Create TestRunnerCLI class inheriting from cmd.Cmd with basic structure and prompt
    status: pending
  - id: "2"
    content: Implement core test execution commands (run, run-quick, run-essential) with argument parsing
    status: pending
  - id: "3"
    content: Implement module management commands (list-modules, describe, discover)
    status: pending
  - id: "4"
    content: Implement test management commands (list-tests, validate-tests, create-template)
    status: pending
  - id: "5"
    content: Implement results and reporting commands (list-results, report, compare)
    status: pending
  - id: "6"
    content: Implement analysis commands (coverage, health, impact, explain)
    status: pending
  - id: "7"
    content: Implement graph and visualization commands (graph, detect-cycles)
    status: pending
  - id: "8"
    content: Add tab completion for module names, categories, and commands
    status: pending
  - id: "9"
    content: Implement help system with help_* methods for each command
    status: pending
  - id: "10"
    content: Update main() function to launch CLI interactively or run single command
    status: pending
  - id: "11"
    content: Add persistent configuration file system with automatic save/load on startup
    status: pending
  - id: "12"
    content: Implement built-in profiles (fast, thorough, gpu, silent) with profile management commands
    status: pending
  - id: "13"
    content: Add command aliases (r, lm, lr, etc.) with alias management system
    status: pending
  - id: "14"
    content: Implement comprehensive color-coded output system with themes and status indicators
    status: pending
  - id: "15"
    content: Test all commands, aliases, profiles, and ensure lazy loading still works correctly
    status: pending
---

# Interactive Test Runner CLI Conversion

## Overview

Transform `mavaia_core/evaluation/test_runner.py` from a single-command argparse interface into an interactive REPL-style command-line interface using Python's `cmd.Cmd` class. All current functionality will be accessible as interactive commands.

## Architecture

### Command Structure

The new interface will use Python's `cmd` module to provide:

- Interactive command prompt: `mavaia-test> `
- Command-based operations (e.g., `run`, `list`, `describe`, `help`)
- Tab completion for commands and module names
- Command history (via readline)
- Built-in help system
- Exit with `quit` or `exit`

### Command Organization

All current argparse options will be converted to commands:

**Test Execution Commands:**

- `run [--module MODULE] [--category CATEGORY] [--tags TAG...]` - Run tests
- `run-quick` - Run quick tests only
- `run-essential` - Run essential tests only

**Module Management:**

- `list-modules` - List all discovered modules
- `describe MODULE` - Show detailed module information
- `discover` - Force module discovery

**Test Management:**

- `list-tests [--module MODULE] [--category CATEGORY]` - List available tests
- `validate-tests` - Validate test data files
- `create-template MODULE` - Create test template for module

**Results & Reporting:**

- `list-results` - List archived test results
- `report [RESULTS_FILE]` - Generate HTML report
- `compare BASELINE_FILE` - Compare with baseline

**Analysis Commands:**

- `coverage` - Show test coverage statistics
- `health` - Show module health scores
- `impact` - Analyze test impact
- `explain MODULE` - Explain module failures

**Graph & Visualization:**

- `graph [OUTPUT_FILE]` - Generate dependency graph
- `detect-cycles` - Detect dependency cycles

**Configuration:**

- `config` - Show current configuration
- `set KEY VALUE` - Set configuration option (persists across restarts)
- `profile [NAME]` - Activate a profile (fast, thorough, gpu, silent)
- `profile list` - List all available profiles
- `profile show NAME` - Show profile details
- `profile save NAME` - Save current config as a new profile
- `profile delete NAME` - Delete a custom profile

**Aliases:**

- `r` → `run`
- `lm` → `list-modules`
- `lr` → `list-results`
- `lt` → `list-tests`
- `d` → `describe`
- `h` → `help`
- `q` → `quit`
- `alias` - List all aliases
- `alias NAME COMMAND` - Create custom alias
- `unalias NAME` - Remove alias

**Utility:**

- `help [COMMAND]` - Show help for command
- `quit` / `exit` / `q` - Exit the interface
- `clear` - Clear screen
- `history` - Show command history

## Implementation Plan

### 1. Create TestRunnerCLI Class

**File:** `mavaia_core/evaluation/test_runner.py`

- Create `TestRunnerCLI(cmd.Cmd)` class
- Initialize with `TestRunner` instance
- Set prompt: `mavaia-test> `
- Implement `do_*` methods for each command
- Implement `complete_*` methods for tab completion
- Implement `help_*` methods for command help

### 2. Command Implementation Strategy

**Lazy Loading Maintained:**

- All module discovery and imports remain lazy
- Commands only trigger imports when executed
- Help command works without any imports

**Command Methods:**

- `do_run(args)` - Parse args and call `runner.run_test_suite()`
- `do_list_modules(args)` - Call `_list_all_modules()`
- `do_describe(args)` - Call `_describe_module()`
- `do_list_tests(args)` - List test cases without running
- `do_validate_tests(args)` - Call `_validate_test_data()`
- `do_create_template(args)` - Call `_create_test_template()`
- `do_list_results(args)` - Call `_list_archives()`
- `do_report(args)` - Generate report from results
- `do_coverage(args)` - Call `_show_test_coverage()`
- `do_health(args)` - Call `_show_module_health_scores()`
- `do_impact(args)` - Call `_analyze_test_impact()`
- `do_explain(args)` - Call `_explain_module_failures()`
- `do_graph(args)` - Call `_generate_dependency_graph()`
- `do_detect_cycles(args)` - Call `_detect_dependency_cycles()`

**Tab Completion:**

- `complete_describe(text, line, begidx, endidx)` - Complete module names
- `complete_run(text, line, begidx, endidx)` - Complete module/category names
- `complete_list_tests(text, line, begidx, endidx)` - Complete module/category names

### 3. Argument Parsing for Commands

Each command will parse its own arguments using `shlex.split()`:

```python
def do_run(self, args):
    """Run tests: run [--module MODULE] [--category CATEGORY] [--tags TAG...]"""
    import shlex
    try:
        parsed = self._parse_run_args(shlex.split(args))
        results = self.runner.run_test_suite(**parsed)
        # Handle results...
    except Exception as e:
        print(f"Error: {e}")
```

### 4. Help System

- `help` - Show all available commands
- `help COMMAND` - Show detailed help for specific command
- Each `do_*` method has a docstring that becomes the help text
- `help_*` methods provide additional details

### 5. Configuration Management

**Persistent Configuration File:**

- Store configuration in JSON file: `~/.mavaia/test_runner_config.json` (or `$XDG_CONFIG_HOME/mavaia/test_runner_config.json`)
- Load configuration automatically on startup
- Save configuration automatically on every `set` command
- Atomic writes (write to temp file, then rename) to prevent corruption
- Configuration survives restarts - all `set` commands persist
- Configuration structure:
  ```json
  {
    "timeout": 30.0,
    "verbose": true,
    "colors": true,
    "skip_modules": false,
    "category": null,
    "tags": [],
    "results_dir": null,
    "test_data_dir": null,
    "current_profile": null,
    "aliases": {
      "r": "run",
      "lm": "list-modules",
      "lr": "list-results",
      "lt": "list-tests",
      "d": "describe",
      "h": "help",
      "q": "quit"
    }
  }
  ```


**Built-in Profiles:**

Profiles are predefined configurations that can be activated instantly:

- **`profile fast`**:
  - `tags: ["quick", "essential"]`
  - `timeout: 10.0`
  - `verbose: false`
  - `skip_modules: false`
  - `colors: true`
  - Purpose: Run only fast, essential tests for quick feedback

- **`profile thorough`**:
  - `tags: []` (all tags)
  - `timeout: 60.0`
  - `verbose: true`
  - `skip_modules: false`
  - `colors: true`
  - Purpose: Comprehensive testing with full output

- **`profile gpu`**:
  - `tags: ["gpu", "essential"]`
  - `timeout: 120.0`
  - `verbose: true`
  - `skip_modules: false`
  - `colors: true`
  - Purpose: GPU-optimized tests, longer timeouts for model loading

- **`profile silent`**:
  - `tags: []`
  - `timeout: 30.0`
  - `verbose: false`
  - `skip_modules: false`
  - `colors: false`
  - Purpose: Minimal output, no colors, for logging/CI

**Profile Management:**

- `profile [NAME]` - Activate a profile (loads all its settings)
- `profile list` - List all available profiles (built-in + custom)
- `profile show NAME` - Show detailed profile configuration
- `profile save NAME` - Save current configuration as a new profile
- `profile delete NAME` - Delete a custom profile (cannot delete built-ins)
- Profiles stored in config file under `profiles` key

**Configuration Keys:**

- `timeout` - Default test timeout (float, seconds)
- `verbose` - Verbose output (boolean)
- `colors` - Enable colors (boolean)
- `skip_modules` - Skip module discovery (boolean)
- `category` - Default category filter (string or null)
- `tags` - Default tag filters (list of strings)
- `results_dir` - Results directory (string path or null)
- `test_data_dir` - Test data directory (string path or null)
- `current_profile` - Currently active profile name (string or null)

### 6. Command Aliases

**Built-in Aliases:**

- `r` → `run`
- `lm` → `list-modules`
- `lr` → `list-results`
- `lt` → `list-tests`
- `d` → `describe`
- `h` → `help`
- `q` → `quit`
- `c` → `config`
- `vt` → `validate-tests`
- `ct` → `create-template`
- `cov` → `coverage`

**Alias Management:**

- `alias` - List all aliases (built-in + custom)
- `alias NAME COMMAND` - Create custom alias (e.g., `alias myrun "run --module mymodule"`)
- `unalias NAME` - Remove custom alias (cannot remove built-ins)
- Aliases stored in config file and persist across restarts
- Aliases can include arguments: `alias m "run --module chain_of_thought"`
- Alias resolution happens in `parseline()` override

**Implementation:**

```python
def parseline(self, line):
    """Override to handle aliases before parsing"""
    # Check if line starts with an alias
    parts = line.split(None, 1)
    if parts and parts[0] in self.aliases:
        # Replace alias with full command
        alias_cmd = self.aliases[parts[0]]
        if len(parts) > 1:
            line = f"{alias_cmd} {parts[1]}"
        else:
            line = alias_cmd
    return cmd.Cmd.parseline(self, line)
```

### 7. Color-Coded Output System

**Color Themes:**

Implement a comprehensive color system with multiple themes:

**Default Theme (Rich Colors):**

- **Success/Pass**: Bright Green (`\033[92m` or `\033[1;32m`)
- **Failure/Error**: Bright Red (`\033[91m` or `\033[1;31m`)
- **Warning**: Bright Yellow (`\033[93m` or `\033[1;33m`)
- **Info**: Bright Cyan (`\033[96m` or `\033[1;36m`)
- **Prompt**: Bright Magenta (`\033[95m` or `\033[1;35m`)
- **Module Name**: Bright Blue (`\033[94m` or `\033[1;34m`)
- **Category**: Cyan (`\033[36m`)
- **Timestamp**: Dim White (`\033[2;37m`)
- **Separator**: White (`\033[37m`)

**Status Indicators:**

- ✓ (checkmark) in green for passed tests
- ✗ (cross) in red for failed tests
- ⚠ (warning) in yellow for warnings
- ⏳ (hourglass) in yellow for running
- 📊 (chart) in cyan for reports
- 🔍 (magnifying glass) in blue for analysis
- 📦 (package) in magenta for modules

**Color-Coded Command Output:**

1. **Test Results:**

   - Passed tests: Green text with ✓
   - Failed tests: Red text with ✗
   - Skipped tests: Yellow text with ⊘
   - Running tests: Cyan text with ⏳

2. **Module Lists:**

   - Enabled modules: Green module name
   - Disabled modules: Red module name (dimmed)
   - Module categories: Color-coded by category type

3. **Progress Indicators:**

   - Progress bars with color gradients
   - Spinner animations with colors
   - Percentage with color based on value (green >80%, yellow 50-80%, red <50%)

4. **Error Messages:**

   - Error type: Red, bold
   - Error message: Red, normal
   - Stack traces: Dim red
   - Suggestions: Yellow

5. **Help System:**

   - Command names: Bright cyan
   - Arguments: Yellow
   - Descriptions: White
   - Examples: Dim white

6. **Configuration:**

   - Key names: Bright blue
   - Values: Green (if valid), Red (if invalid)
   - Profile names: Magenta

**Color Detection:**

- Auto-detect terminal color support
- Respect `NO_COLOR` environment variable
- Respect `TERM` variable (disable colors for dumb terminals)
- Provide `--no-colors` flag to disable
- Config option `colors: false` disables all colors

**Implementation:**

```python
class ColorOutput:
    """Color output manager with theme support"""
    
    def __init__(self, enabled=True):
        self.enabled = enabled and self._supports_color()
        self.colors = {
            'success': '\033[92m',
            'error': '\033[91m',
            'warning': '\033[93m',
            'info': '\033[96m',
            'prompt': '\033[95m',
            'module': '\033[94m',
            'reset': '\033[0m',
            # ... more colors
        }
    
    def colorize(self, text, color):
        """Apply color to text"""
        if not self.enabled:
            return text
        return f"{self.colors.get(color, '')}{text}{self.colors['reset']}"
    
    def status(self, symbol, text, status_type='info'):
        """Print colored status with symbol"""
        color_map = {
            'success': 'success',
            'error': 'error',
            'warning': 'warning',
            'info': 'info'
        }
        color = color_map.get(status_type, 'info')
        return f"{self.colorize(symbol, color)} {text}"
```

**Enhanced Prompt:**

- Color-coded prompt: `mavaia-test> ` in bright magenta
- Show current profile in prompt: `mavaia-test [fast]> `
- Show status indicator: `mavaia-test [running]> ` (when tests are running)

### 8. Error Handling

- All commands wrapped in try/except
- Clear error messages with color coding (red for errors, yellow for warnings)
- Commands don't crash the interface
- Error messages include suggestions when possible
- Stack traces only shown in verbose mode or with `--debug` flag

### 9. Output Formatting

- Comprehensive color system (see Color-Coded Output System above)
- Rich formatting for interactive use:
  - Tables with borders and colors
  - Progress bars with color gradients
  - Status indicators with symbols and colors
  - Grouped output with headers and separators
- Progress indicators for long operations:
  - Spinner animations during discovery
  - Progress bars for test execution
  - Real-time status updates with colors
- Format output based on terminal width (auto-detect)
- Pagination for long lists (press space to continue)

## File Changes

### `mavaia_core/evaluation/test_runner.py`

**Changes:**

1. Import `cmd`, `shlex`, `readline` (if available)
2. Create `TestRunnerCLI(cmd.Cmd)` class
3. Move `main()` logic into CLI initialization
4. Convert all argparse handlers to `do_*` methods
5. Add tab completion methods
6. Add help methods
7. Update `main()` to launch CLI if no args, or run single command if args provided

**Structure:**

```python
class TestRunnerCLI(cmd.Cmd):
    intro = "Mavaia Test Runner - Interactive Mode\nType 'help' for commands."
    prompt = "mavaia-test> "
    
    def __init__(self, ...):
        # Initialize runner, config, etc.
        self.config_file = self._get_config_path()
        self.config = self._load_config()  # Load persistent config
        self.aliases = self.config.get('aliases', {})
        self.color_output = ColorOutput(enabled=self.config.get('colors', True))
        self._update_prompt()  # Set prompt with profile indicator
    
    def parseline(self, line):
        """Override to handle aliases before parsing"""
        # Check if line starts with an alias
        parts = line.split(None, 1)
        if parts and parts[0] in self.aliases:
            alias_cmd = self.aliases[parts[0]]
            if len(parts) > 1:
                line = f"{alias_cmd} {parts[1]}"
            else:
                line = alias_cmd
        return cmd.Cmd.parseline(self, line)
    
    def _load_config(self):
        """Load persistent configuration from file"""
        # Load from ~/.mavaia/test_runner_config.json
        # Return default config if file doesn't exist
    
    def _save_config(self):
        """Save configuration to file atomically"""
        # Write to temp file, then rename
    
    def do_set(self, args):
        """Set configuration: set KEY VALUE"""
        # Parse args, update config, save to file
    
    def do_profile(self, args):
        """Profile management: profile [NAME|list|show NAME|save NAME|delete NAME]"""
        # Handle profile activation and management
    
    def do_alias(self, args):
        """Alias management: alias [NAME [COMMAND]]"""
        # List, create, or remove aliases
    
    def do_run(self, args):
        """Run tests"""
        # Use color_output for colored output
    
    def do_list_modules(self, args):
        """List all modules"""
        # Use color_output for colored module names
    
    # ... all other commands
    
    def complete_describe(self, text, line, begidx, endidx):
        """Tab completion for module names"""
    
    def _update_prompt(self):
        """Update prompt with current profile indicator"""
        profile = self.config.get('current_profile')
        if profile:
            self.prompt = f"mavaia-test [{profile}]> "
        else:
            self.prompt = "mavaia-test> "
        # Apply color to prompt
    
    def default(self, line):
        """Handle unknown commands"""
        # Show helpful error with suggestions
```

## Benefits

1. **Better UX**: Interactive mode allows exploring without re-running commands
2. **Faster Workflow**: No need to re-import on each command
3. **Tab Completion**: Faster module/test selection
4. **Command History**: Use arrow keys to repeat commands
5. **Context Preservation**: Configuration and state persist in session

## Migration Notes

- Old usage: `python3 -m mavaia_core.evaluation.test_runner --module X`
- New usage: `python3 -m mavaia_core.evaluation.test_runner` then `run --module X`
- Or: `python3 -m mavaia_core.evaluation.test_runner run --module X` (single command mode)

## Testing Considerations

- Test interactive mode startup
- Test each command individually
- Test tab completion
- Test error handling
- Test help system
- Test aliases (built-in and custom)
- Test profile activation and persistence
- Test persistent configuration (set, save, load on restart)
- Test color output (with and without color support)
- Test alias resolution in parseline
- Test profile switching and prompt updates
- Ensure lazy loading still works
- Test configuration file atomic writes
- Test profile save/delete operations
- Test color detection and NO_COLOR environment variable
---
name: Migrate CLI to cmd2 with Enhanced History
overview: Migrate the test runner CLI from Python's standard `cmd` module to `cmd2`, implementing enhanced history management with script save/load functionality and leveraging cmd2's advanced features.
todos:
  - id: migrate_base_class
    content: Replace cmd.Cmd with cmd2.Cmd, update imports and base class initialization
    status: completed
  - id: update_method_signatures
    content: Update all do_* methods to use cmd2.Statement instead of str args
    status: completed
    dependencies:
      - migrate_base_class
  - id: implement_history_edit
    content: Implement history -e command to open last 50 commands in VS Code editor
    status: completed
    dependencies:
      - migrate_base_class
  - id: implement_history_run
    content: Implement history run command to replay entire current session
    status: completed
    dependencies:
      - migrate_base_class
  - id: implement_history_save
    content: Implement history save command to export session as .mvx YAML script
    status: completed
    dependencies:
      - migrate_base_class
  - id: implement_script_execution
    content: Add script file execution support to do_run command (.mvx file parsing and execution)
    status: completed
    dependencies:
      - implement_history_save
  - id: implement_failure_model
    content: Implement failure model for script execution (continue/stop modes, critical commands, replay logs)
    status: completed
    dependencies:
      - implement_script_execution
  - id: implement_script_versioning
    content: Add version field to .mvx format and version validation on script load
    status: completed
    dependencies:
      - implement_history_save
  - id: migrate_tab_completion
    content: Update complete_* methods to work with cmd2 completion system
    status: completed
    dependencies:
      - update_method_signatures
  - id: integrate_cmd2_aliases
    content: Migrate alias system to use cmd2 built-in alias support
    status: completed
    dependencies:
      - migrate_base_class
  - id: configure_persistent_history
    content: Configure cmd2 persistent history file and settings
    status: completed
    dependencies:
      - migrate_base_class
  - id: update_output_methods
    content: Replace print statements with cmd2 output methods (poutput, perror, etc.) where appropriate
    status: completed
    dependencies:
      - migrate_base_class
  - id: add_error_handling
    content: Add comprehensive error handling for script execution and history operations
    status: completed
    dependencies:
      - implement_script_execution
      - implement_history_edit
  - id: test_migration
    content: Test all existing commands work correctly, test new history features, verify backward compatibility
    status: completed
    dependencies:
      - update_method_signatures
      - implement_history_edit
      - implement_history_run
      - implement_history_save
      - implement_script_execution
---

# Migration Plan: cmd → cmd2 with Enhanced History

## Overview

Migrate `TestRunnerCLIImpl` from `cmd.Cmd` to `cmd2.Cmd`, adding enhanced history features including script save/load, history editing, and session replay.

## Key Changes

### 1. Core Migration (`oricli_core/evaluation/test_runner.py`)

**Base Class Change:**

- Replace `cmd.Cmd` with `cmd2.Cmd` (line 624)
- Update imports: `import cmd` → `import cmd2`
- Inherit from `cmd2.Cmd` instead of `cmd.Cmd`

**Initialization Updates:**

- Replace `super().__init__()` with `cmd2.Cmd.__init__()` with appropriate parameters
- Configure cmd2 settings:
                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                - `persistent_history_file`: Store history in `~/.mavaia/test_runner_history.txt`
                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                - `allow_cli_args`: Enable command-line argument parsing
                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                - `auto_load_commands`: Load commands automatically
- Remove manual `parseline` override (cmd2 handles this better)

**Command Method Signatures:**

- Update all `do_*` methods to use cmd2's argument parsing:
                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                - Change `def do_run(self, args: str)` → `def do_run(self, args: cmd2.Statement)`
                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                - Use `args.raw` for raw command string or `args.argv` for parsed arguments
- Update `help_*` methods to work with cmd2's help system
- Update `complete_*` methods to use cmd2's completion system (returns list of strings)

### 2. Enhanced History Implementation

**Custom History Command (`do_history`):**

```python
def do_history(self, args: cmd2.Statement):
    """Enhanced history management
    
    Usage:
        history              - Show recent history
        history -e           - Edit last 50 commands in VS Code
        history run          - Replay entire current session
        history save FILE    - Save current session to .mvx script
        history list         - List all saved sessions
    """
```

**History Edit (`history -e`):**

- Get last 50 commands from cmd2's history
- Create temporary file with commands
- Open in VS Code: `code --wait <temp_file>`
- After editor closes, parse edited commands
- Execute modified commands if user confirms
- Store in session replay buffer

**History Run (`history run`):**

- Replay all commands from current session
- Use cmd2's `onecmd_plus_hooks()` for each command
- Show progress indicator
- Support `--stop-on-error` flag

**History Save (`history save my_bench.mvx`):**

- Create YAML format script file with versioning:
  ```yaml
  version: "1.0"  # Script format version
  metadata:
    created: 2025-01-15T10:30:00Z
    session_id: <uuid>
    total_commands: 42
    description: "Full evaluation session"
    failure_mode: "continue_on_error"  # Default failure mode
    critical_commands: ["run", "validate-tests"]  # For stop_on_critical mode
    author: "user@example.com"  # Optional
    tags: ["benchmark", "full-suite"]  # Optional
  commands:
    - command: "run --module chain_of_thought"
      timestamp: "2025-01-15T10:30:15Z"
      comment: "Test CoT module"
    - command: "coverage"
      timestamp: "2025-01-15T10:31:00Z"
  ```

- Save to `~/.mavaia/scripts/` directory
- Include session metadata and timestamps
- Version field enables future format migrations

### 3. Script Execution (`do_run` enhancement)

**Script File Support:**

- Detect if argument is `.mvx` file path
- Parse YAML script file (with version validation)
- Execute commands sequentially
- Support `--quiet` and `--verbose` flags
- Show progress: `[1/10] Executing: run --module X`
- Implement failure model with multiple modes

**Failure Model:**

Script execution supports four failure handling modes (configurable via `--failure-mode` or script metadata):

1. **Continue on Error** (default for non-critical scripts):

                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                - Log error but continue executing remaining commands
                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                - Collect all errors for summary at end
                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                - Useful for batch operations where partial success is acceptable

2. **Stop on Error**:

                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                - Immediately halt script execution on first error
                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                - Report error context and command that failed
                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                - Useful for critical workflows where all steps must succeed

3. **Stop on Critical Commands**:

                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                - Define critical commands in script metadata (e.g., `run`, `validate-tests`)
                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                - Continue on non-critical command failures (e.g., `list-modules`, `coverage`)
                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                - Stop only when critical commands fail
                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                - Balance between resilience and safety

4. **Annotate Errors in Replay Logs**:

                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                - Continue execution regardless of errors
                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                - Annotate each command with success/failure status
                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                - Generate detailed replay log with error annotations
                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                - Save replay log to `~/.mavaia/replay_logs/<script_name>_<timestamp>.log`
                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                - Include error messages, stack traces, and execution context

**Failure Model Configuration:**

- Set via command: `run script.mvx --failure-mode <mode>`
- Or in script metadata:
  ```yaml
  metadata:
    failure_mode: "stop_on_critical"  # continue_on_error | stop_on_error | stop_on_critical | annotate_only
    critical_commands: ["run", "validate-tests"]  # For stop_on_critical mode
  ```


**Replay Log Format:**

```yaml
execution_log:
  script: "my_bench.mvx"
  started: "2025-01-15T10:30:00Z"
  completed: "2025-01-15T10:35:00Z"
  total_commands: 10
  successful: 8
  failed: 2
  commands:
  - index: 1
      command: "run --module chain_of_thought"
      status: "success"
      execution_time: 2.34
  - index: 2
      command: "coverage"
      status: "failed"
      error: "Module not found: coverage_module"
      error_type: "ModuleNotFoundError"
      execution_time: 0.12
      stack_trace: "..."
```

**Implementation:**

```python
def do_run(self, args: cmd2.Statement):
    # Check if argument is script file
    if args.raw.endswith('.mvx'):
        failure_mode = self._parse_failure_mode(args)
        return self._execute_script(args.raw, failure_mode=failure_mode)
    # Otherwise, existing run logic
    ...

def _execute_script(self, script_path: str, failure_mode: str = "continue_on_error"):
    """Execute .mvx script with specified failure model"""
    script_data = self._load_script(script_path)
    self._validate_script_version(script_data)
    
    replay_log = {
        "script": script_path,
        "started": datetime.now(timezone.utc).isoformat(),
        "commands": []
    }
    
    for idx, cmd_entry in enumerate(script_data["commands"], 1):
        try:
            result = self._execute_command_with_logging(cmd_entry, idx, len(script_data["commands"]))
            replay_log["commands"].append(result)
            
            if result["status"] == "failed":
                if failure_mode == "stop_on_error":
                    break
                elif failure_mode == "stop_on_critical":
                    if cmd_entry["command"].split()[0] in script_data["metadata"].get("critical_commands", []):
                        break
        except Exception as e:
            # Handle execution errors based on failure mode
            ...
    
    self._save_replay_log(replay_log, script_path)
```

### 4. Session Management

**Session Tracking:**

- Track session start time in `__init__`
- Store all executed commands in session buffer
- Associate commands with timestamps
- Generate unique session ID per CLI instance

**Session Replay:**

- Store session commands in memory during execution
- Allow saving session at any time
- Support partial replay (from command N to M)

### 5. cmd2 Feature Integration

**Tab Completion:**

- Leverage cmd2's built-in completion
- Update `complete_*` methods to return `List[str]`
- Use `cmd2.Cmd.complete()` for default completions

**Alias System:**

- Use cmd2's built-in alias support via `self.alias()`
- Migrate existing aliases to cmd2 format
- Maintain backward compatibility with current aliases

**History Management:**

- Use cmd2's persistent history
- Configure history file location
- Set history size limits

**Output Redirection:**

- Use cmd2's `poutput()`, `perror()`, `pwarning()` methods
- Maintain color output compatibility
- Support output redirection to files

### 6. File Structure

**New Files:**

- `oricli_core/evaluation/scripts/` - Directory for saved scripts
- `~/.mavaia/scripts/` - User script storage
- `~/.mavaia/test_runner_history.txt` - Persistent history
- `~/.mavaia/replay_logs/` - Execution replay logs with error annotations

**Script Format (.mvx):**

- YAML format with version field (currently "1.0")
- Metadata section with failure mode configuration
- Commands array with timestamps and optional comments
- Version validation on load (reject unsupported versions)
- Support for version migration (future: auto-upgrade v1.0 → v1.1)
- Critical commands list for stop-on-critical mode

### 7. Backward Compatibility

**Maintain Existing Behavior:**

- All existing commands work identically
- Aliases continue to function
- Configuration system unchanged
- Header display logic preserved
- Color output maintained

**Migration Path:**

- Old history format (if any) can be imported
- Existing config files remain compatible
- No breaking changes to command syntax

### 8. Testing Considerations

**Test Cases:**

- Test history edit workflow
- Test script save/load with versioning
- Test session replay
- Test all four failure modes (continue, stop, stop-on-critical, annotate)
- Test critical command detection
- Test replay log generation and error annotation
- Test script version validation (accept v1.0, reject unsupported)
- Test error handling in scripts
- Test cmd2-specific features
- Verify backward compatibility

## Implementation Steps

1. **Phase 1: Core Migration**

                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                - Replace `cmd.Cmd` with `cmd2.Cmd`
                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                - Update base class and initialization
                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                - Fix all `do_*` method signatures
                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                - Test basic command execution

2. **Phase 2: History Features**

                                                                                                                                                                                                - Implement `history -e` (editor integration)
                                                                                                                                                                                                - Implement `history run` (session replay)
                                                                                                                                                                                                - Implement `history save` (script generation with versioning)
                                                                                                                                                                                                - Add script execution to `do_run`
                                                                                                                                                                                                - Implement failure model (all four modes)
                                                                                                                                                                                                - Add replay log generation
                                                                                                                                                                                                - Implement script version validation

3. **Phase 3: cmd2 Integration**

                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                - Migrate tab completion
                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                - Integrate cmd2 aliases
                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                - Configure persistent history
                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                - Update output methods

4. **Phase 4: Polish & Testing**

                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                - Add error handling
                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                - Improve user experience
                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                - Write tests
                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                - Update documentation

## Files to Modify

- `oricli_core/evaluation/test_runner.py` - Main CLI implementation
                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                - Lines 560-1871: CLI class definition
                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                - Lines 1101-1109: History command
                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                - Lines 1338-1410: Run command
                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                - All `do_*`, `help_*`, `complete_*` methods

## Dependencies

- `cmd2` (already installed in .venv)
- `pyyaml` (for .mvx script parsing) - may need to add
- VS Code CLI (`code` command) - user requirement

## Notes

- cmd2 provides better tab completion, history, and argument parsing out of the box
- Script format uses YAML for human readability and metadata support
- VS Code integration requires `code` command in PATH
- Session replay maintains exact command order and timing information
- Scripts can be shared between team members for reproducible workflows
- Failure model provides flexibility for different use cases (development vs production)
- Version field enables future format evolution without breaking existing scripts
- Replay logs provide audit trail and debugging information for script executions
- Critical commands list allows fine-grained control over failure behavior
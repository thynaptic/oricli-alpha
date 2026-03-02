# Project Workflow

## Guiding Principles

1. **The Plan is the Source of Truth:** All work must be tracked in `plan.md`.
2. **The Tech Stack is Deliberate:** Changes to the tech stack must be documented in `tech-stack.md` *before* implementation.
3. **Sovereign & Local-First:** Prioritize local-first, air-gapped compatible dependencies. Avoid any workflow step that requires external telemetry.
4. **Flexible Test-Driven Development:** Write unit tests to define expected behavior. TDD is recommended but flexible based on task complexity.
5. **Pragmatic Code Coverage:** Aim for >60% code coverage for all modules.
6. **Non-Interactive & CI-Aware:** Prefer non-interactive commands. Use `CI=true` for watch-mode tools to ensure single execution.

## Task Workflow

All tasks follow a strict lifecycle:

### Standard Task Workflow

1. **Select Task:** Choose the next available task from `plan.md` in sequential order.
2. **Mark In Progress:** Before beginning work, edit `plan.md` and change the task from `[ ]` to `[~]`.
3. **Implementation & Testing:**
   - Implement the required functionality or fix.
   - Write corresponding unit tests to validate the change.
   - Ensure all tests pass.
4. **Verify Coverage:** Run coverage reports. Target: >60% coverage for new code.
5. **Document Deviations:** If implementation differs from the tech stack, update `tech-stack.md` with a dated note before proceeding.
6. **Mark Complete:** Update `plan.md`, changing the task from `[~]` to `[x]`.

### Phase Completion Verification and Checkpointing Protocol

**Trigger:** This protocol is executed immediately after all tasks in a phase are marked complete in `plan.md`.

1. **Announce Protocol Start:** Inform the user that the phase is complete and verification has begun.
2. **Verify Tests & Coverage:**
   - Ensure all code changes in the phase have corresponding tests.
   - Confirm aggregate coverage meets the >60% threshold.
3. **Execute Automated Tests:** Run the full test suite. **Command:** `python3 run_tests.py`.
4. **Manual Verification:** Propose and execute a step-by-step manual verification plan based on `product.md`.
5. **Commit Phase Changes:**
   - Stage all changes for the entire phase.
   - Perform a single commit for the phase: `feat(<scope>): Complete Phase <X> - <Phase Name>`.
6. **Create Checkpoint:** Create a Git note on the phase commit with a summary of all tasks completed.
7. **Record Checkpoint:** Update `plan.md` with the checkpoint commit SHA next to the phase heading.

### Quality Gates

Before marking a phase complete, verify:
- [ ] All tests pass.
- [ ] Code coverage >60%.
- [ ] Code follows project style guides (Black, Ruff).
- [ ] Type safety is enforced with type hints.
- [ ] No telemetry or external dependencies introduced without approval.

## Development Commands

### Setup
```bash
# Install base dependencies
pip install -e .

# Install all extras (ML, Data, Dev)
pip install -e ".[ml,data,dev,search,sandbox,memory]"
```

### Daily Development
```bash
# Run quick smoke tests
python3 run_quick_tests.py

# Run full test suite
python3 run_tests.py

# Format and Lint
black mavaia_core/ scripts/
ruff check mavaia_core/ scripts/
```

## Commit Guidelines

### Message Format
```
<type>(<scope>): <description>

[optional body]
```

### Types
- `feat`: New feature
- `fix`: Bug fix
- `refactor`: Code change without behavioral change
- `test`: Adding or updating tests
- `chore`: Maintenance or configuration updates

## Definition of Done

A phase is complete when:
1. All tasks implemented and verified.
2. Full test suite passing.
3. Manual verification confirmed by user.
4. Changes committed as a single phase-level commit.
5. Checkpoint SHA recorded in `plan.md`.

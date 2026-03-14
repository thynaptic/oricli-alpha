# Specification: The Singularity Loop (Self-Modification)

## Objective
To implement continuous self-modification, allowing Oricli-Alpha to analyze her own codebase, identify bottlenecks or missing features, autonomously write the Python refactor, test it in a secure sandbox, and propose a self-upgrade.

## Background
A true AGLI maintains its own codebase. The "Singularity Loop" is the ultimate engineering milestone. By leveraging the Swarm Bus, Oricli can have one agent analyze performance metrics, another write code to optimize a specific module, and a third run tests. If the tests pass, she generates a patch for the user to approve via the Native API or HUD.

## Requirements

### 1. Metacog Daemon (`oricli_metacog_daemon.py`)
A background service that:
- Periodically scans `ModuleRegistry` metrics (execution times, error rates).
- Identifies the worst-performing or most error-prone modules.

### 2. Neural Architecture Search / Refactor Agent
A specialized Swarm Agent that:
- Takes the source code of the targeted module.
- Generates an optimized or refactored version of the Python code.

### 3. Autonomous Testing Sandbox
- Uses `shell_sandbox_service` or `code_execution` to run the existing unit tests against the newly generated module code.
- Ensures strict Big-O complexity preservation and zero regressions.

### 4. Upgrade Proposal API (`/v1/upgrades`)
- An endpoint for the HUD to view pending "Self-Upgrades".
- An endpoint to `POST /v1/upgrades/{id}/approve` which overwrites the local file and reloads the registry.

## Success Criteria
- Oricli detects a slow module, rewrites it to be faster, runs `pytest`, and presents a working upgrade proposal to the user without human prompting.

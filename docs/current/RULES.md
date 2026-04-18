## Oricli-Alpha Global Rules

Oricli-Alpha has a **global rules layer** that governs safety, routing, and resource policies across all skills and brain modules.

Rules are defined in `.ori` files under `oricli_core/rules/` and are evaluated by the `RulesEngine`.

### Rule format

Rule files mirror the `.ori` skill format with a small header and tagged sections:

```text
@rule_name: global_safety
@description: Core safety and sandboxing constraints.
@scope: global
@categories: ["safety"]

<constraints>
- deny: shell_sandbox_service on paths outside /workspace and /tmp
</constraints>
```

- `@rule_name`: Unique identifier for the rule set.
- `@description`: Human-readable summary.
- `@scope`: Scope string (v1 uses `global`).
- `@categories`: Tags such as `safety`, `routing`, `resources`.
- Sections:
  - `<constraints>`: allow/deny style lines.
  - `<routing_preferences>`: preferred modules/tools for tagged tasks.
  - `<resource_policies>`: simple key/value style policies.

### Engine and context

The rules engine lives in `oricli_core/rules/engine.py` and exposes:

- `load_rules() -> list[Rule]`
- `evaluate_request(context: RuleContext) -> RuleDecision`
- `get_routing_preferences(context: RuleContext) -> list[str]`

`RuleContext` is a coarse-grained descriptor:

- `operation_type`: e.g. `"module_execute"`, `"shell_exec"`
- `module_name` / `tool_name`
- `path`: target path for filesystem operations (if relevant)
- `tags`: semantic tags like `"multi_agent_reasoning"`, `"shell_sandbox"`

`RuleDecision` returns:

- `allowed: bool`
- `reasons: list[str]` (why a request was blocked or allowed)
- `suggested_alternatives: list[str]` (preferred modules/tools)

### Built-in global rules

Current builtin rules under `oricli_core/rules/`:

- `global_safety.ori`
  - Denies `shell_sandbox_service` operations on paths outside `/workspace` and `/tmp`.
- `global_routing.ori`
  - Prefers `game_theory_solver` for multi-agent payoff reasoning tags.
  - Prefers `formal_verification_bridge` for `critical_code_paths`.
  - Prefers `knowledge_graph_builder` for entity/relationship extraction.
- `global_resources.ori`
  - Defines hints like `max_heavy_modules_per_request` and `planner_max_depth_hint`.

- `code_quality.ori`
  - Language-specific code standards for Go and Python.
  - Requires `gofmt`, `go vet`, `golangci-lint` compliance; bans `panic()` in library code; requires typed tests.
  - Python: enforces `black`/`ruff`, bans broad `except:`, requires type annotations on all public functions.

- `response_format.ori`
  - Output discipline and formatting standards for all responses.
  - Requires leading with the answer first; enforces language tags on code blocks; prefers lists/tables over prose paragraphs; caps response length and prohibits filler phrases.

- `sanctuary_protocols.ori`
  - Global constraints and routing for the Princess Puppy Sanctuary.
  - Denies certain personal phrases; requires a breathing reminder in every message; tags high-severity distress with `[EMERGENCY_TRIGGER]`.

### Integration points (v1)

- **Shell sandbox** (`ShellSandboxServiceModule`):
  - Evaluates rules before executing sandbox operations.
  - Blocks requests when global safety rules deny a path.
- **Multi-agent orchestrator** (`MultiAgentOrchestratorModule`):
  - Evaluates global rules for multi-agent reasoning flows.
  - Supplies tags like `"multi_agent_reasoning"` so routing preferences can bias module choice.

Over time, additional orchestrators and modules can consult the rules engine to enforce project- and tenant-specific policies.


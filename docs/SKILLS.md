## Oricli-Alpha Skill Library

Oricli-Alpha ships with a small set of **builtin skill personas** defined in `oricli_core/skills/*.ori`. Each skill encodes mindset, triggers, and guardrails for a specialized role.

### Available skills

- **`senior_python_dev`**  
  - **Description**: Expert Python software engineering and architecture design.  
  - **Typical use**: Refactors, performance work, exception-safety, pytest examples.  
  - **Triggers**: `["python", "refactor", "code review", "architecture", "pep8"]`.

- **`devops_sre`**  
  - **Description**: Site Reliability Engineering and DevOps architecture.  
  - **Typical use**: CI/CD, observability, infra-as-code, Kubernetes/Docker deployments.  
  - **Triggers**: `["deploy", "docker", "kubernetes", "ci/cd", "pipeline", "infrastructure", "terraform"]`.

- **`system_architect`**  
  - **Description**: High-level system design and distributed architecture.  
  - **Typical use**: System design reviews, scaling plans, data-store selection, failure-mode analysis.  
  - **Triggers**: `["system design", "scale", "microservices", "architecture", "database schema", "distributed"]`.

- **`technical_writer`**  
  - **Description**: Expert technical documentation and API specification writing.  
  - **Typical use**: READMEs, API specs, tutorials, docstrings, migration guides.  
  - **Triggers**: `["document this", "readme", "api spec", "swagger", "docstring", "tutorial"]`.

- **`ori_language_expert`**  
  - **Description**: Deep knowledge of the ORI workflow definition language and ORI Studio IDE.  
  - **Typical use**: Writing `.ori` files, explaining syntax, building and chaining workflows, compiler diagnostics.  
  - **Triggers**: `["ori", ".ori", "ori syntax", "workflow syntax", "ori studio", "build a workflow", "compile", "decompile", "step:", "@workflow", "ori file"]`.  
  - **Reference**: See [`ORI_SYNTAX.md`](./ORI_SYNTAX.md) for the full language spec.

- **`data_scientist`**  
  - **Description**: Advanced data analysis, statistical modeling, and visualization.  
  - **Typical use**: Exploratory data analysis, feature engineering, plots, statistical checks.  
  - **Triggers**: `["analyze data", "pandas", "statistics", "dataset", "machine learning", "plot"]`.

- **`offensive_security`**  
  - **Description**: Advanced network and codebase vulnerability analysis.  
  - **Typical use**: Threat modeling, attack-surface reviews, vuln triage with mitigations.  
  - **Triggers**: `["hack", "vulnerability", "exploit", "cve", "red team", "security flaw"]`.

### How skills are used

- **Location**: Skill definitions live in `oricli_core/skills/*.ori`.  
- **Runtime**: The orchestrator activates a skill when user intent matches that skill’s trigger patterns or when explicitly selected by higher-level control logic.  
- **Composition**: Skills layer on top of the core brain modules (reasoning, memory, safety, tools) and act as *role presets* that shape behavior, not separate models.

### Forcing a specific skill

You can explicitly ask Oricli-Alpha to use a particular skill persona instead of relying on trigger matching.

- **Via high-level instruction (recommended)**  
  Clearly state the desired skill/role in the system or first user message, e.g.:

```text
System: Act as Oricli-Alpha with the `senior_python_dev` skill for this session.
User: Refactor this module and explain any Big-O changes.
```

- **Via internal control (orchestrator / config)**  
  When building higher-level agents on top of Oricli-Alpha, you can bind a skill in your own orchestration layer by:
  - Attaching the desired `@skill_name` to the control metadata/context you pass into planning/execution.
  - Routing requests through the appropriate skill wrapper (where your code selects the skill and forwards the actual task to the core brain modules).

Skills are **orthogonal** to models: switching skill personas does not change weights, only mindset, constraints, and preferred tooling.


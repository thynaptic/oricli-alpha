# Copilot instructions for Oricli-Alpha (Oricli/Mavaia)

This repo is a **modular cognitive framework** with an **OpenAI-compatible FastAPI server**, a **Flask UI proxy**, and a **large auto-discovered brain-module system**.

## Build / run / test / lint

### Setup (Python)
Recommended runtime: **Python 3.11 or 3.12** (see `INSTALL.md`).

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -U pip setuptools wheel

# Editable install (core deps from pyproject.toml)
pip install -e .

# Dev tooling (pytest/black/ruff/mypy)
pip install -e ".[dev]"

# Heavier optional stacks
pip install -e ".[ml,data,search,sandbox,memory]"
```

Alternative “batteries included” install script (installs ML stack + JAX/Flax workarounds):
```bash
./scripts/setup.sh
```

### Run servers
One command (recommended):
```bash
./scripts/start_servers.sh
```

API only:
```bash
oricli-server --host 0.0.0.0 --port 8000
# or
python3 -m oricli_core.api.server --host 0.0.0.0 --port 8000
```

UI only (Flask proxy → API):
```bash
MAVAIA_API_BASE="http://localhost:8000" python3 ui_app.py
```

### Tests (project’s evaluation framework)
The canonical runner is the custom evaluation CLI (JSON/YAML test cases under `oricli_core/evaluation/test_data/`).

Run everything:
```bash
./run_tests.py
# or (same engine)
python3 -m oricli_core.evaluation.test_runner
```

Run a single module’s tests:
```bash
./run_tests.py --module chain_of_thought
# or
python3 -m oricli_core.evaluation.test_runner --module chain_of_thought
```

Run a single category:
```bash
python3 -m oricli_core.evaluation.test_runner --category reasoning
```

Fast “system-only” run (skips module discovery):
```bash
python3 -m oricli_core.evaluation.test_runner --category system --skip-modules
```

Filter by tags (e.g. quick/smoke/integration):
```bash
python3 -m oricli_core.evaluation.test_runner --tags quick smoke --tag-mode any
```

Generate an HTML report from an existing results file:
```bash
python3 -m oricli_core.evaluation.test_runner --report-only oricli_core/evaluation/results/<run>/detailed_results.json
```

Curriculum testing CLI (Typer-based; installed via `pyproject.toml` script `oricli-test`):
```bash
oricli-test --help
oricli-test full --progressive
```

### Pytest (single file / single test)
There are also `test_*.py` files at repo root and under `tests/`.

```bash
pytest -q tests/test_streaming_logic.py
pytest -q test_mona_lisa_query.py -k "smoke" 
pytest -q tests/test_streaming_logic.py::TestStreamingLogic::test_<name>
```

### Format / lint / typecheck
```bash
black oricli_core/ scripts/ ui_app.py
ruff check oricli_core/ scripts/
mypy oricli_core/
```

## High-level architecture (big picture)

### 1) Brain modules (plugin system)
- **Interface:** `oricli_core/brain/base_module.py` defines `BaseBrainModule` + `ModuleMetadata`.
- **Location:** modules live in `oricli_core/brain/modules/`.
- **Discovery:** `oricli_core/brain/registry.py::ModuleRegistry.discover_modules()` scans `modules/` (and subdirs except `models/`) and registers classes inheriting `BaseBrainModule`.
- **Heavy-module gating:** discovery intentionally **skips modules** that appear to import heavy ML stacks / download HF models at import-time unless:
  - `MAVAIA_ENABLE_HEAVY_MODULES=true`

### 2) Client layer (direct in-process execution)
- `oricli_core/client.py::OricliAlphaClient` exposes:
  - `client.chat.completions.create(...)` and `client.embeddings.create(...)` (OpenAI-shaped)
  - `client.brain.<module>.<operation>(**params)` via a dynamic proxy to `ModuleRegistry`

### 3) HTTP API (OpenAI-compatible)
- `oricli_core/api/server.py` hosts the FastAPI app.
- Key endpoints:
  - `POST /v1/chat/completions`
  - `POST /v1/embeddings`
  - `GET  /v1/models`, `GET /v1/modules`
  - health/metrics/introspection: `/health`, `/v1/metrics`, `/v1/introspection*`, `/v1/health/modules*`
  - tool endpoints: `/v1/tools/register`, `/v1/tools`, `/v1/tools/invoke`
- Auth is controlled via env:
  - `MAVAIA_REQUIRE_AUTH=true|false`
  - `MAVAIA_API_KEY` (Bearer token)

### 4) Tooling bridge
- The API registers “built-in tools” via `oricli_core/services/tool_registry.py` and routes tool calls to brain modules (e.g. `web_fetch`, `web_search`, `tool_search`) when present.

### 5) UI
- `ui_app.py` is a **production-oriented Flask proxy**.
- It forwards `/chat`, `/models`, `/modules`, `/embeddings` to the API and supports streaming pass-through.
- UI → API target is `MAVAIA_API_BASE` (defaults to `http://localhost:8000`).

### 6) Evaluation
- `oricli_core/evaluation/test_runner.py` is the main engine.
- Test cases are loaded from `oricli_core/evaluation/test_data/`.
- Results are archived under `oricli_core/evaluation/results/` and can be rendered to HTML.
- There is a `livebench` category which integrates the `LiveBench/` suite.

### 7) Daemons / services
- `scripts/oricli_api_daemon.py` and `scripts/oricli_trainer_daemon.py` are long-running orchestrators.
- Systemd units at repo root (`oricli-api.service`, `oricli-trainer.service`) show expected env and log locations.

## Key codebase conventions (repo-specific)

### Brain module contract
- Each module must:
  - inherit `BaseBrainModule`
  - implement `metadata: ModuleMetadata`
  - implement `execute(operation: str, params: dict[str, Any]) -> dict[str, Any]`
- `execute()` return payloads are expected to be dicts that include at least:
  - `success: bool`
  - `error: str | None`

### “Heavy modules” are opt-in
- Default behavior is to keep servers responsive by skipping modules that pull models / heavy ML deps at import-time.
- If you’re debugging “module not found” for ML-heavy features, re-run with:
  - `MAVAIA_ENABLE_HEAVY_MODULES=true`

### Environment variable namespace
- Config is consistently **`MAVAIA_...`** even though the package name is `oricli_*`.
- Common ones:
  - `MAVAIA_API_HOST`, `MAVAIA_API_PORT`
  - `MAVAIA_UI_HOST`, `MAVAIA_UI_PORT`
  - `MAVAIA_API_BASE` (UI → API)
  - `MAVAIA_API_KEY`, `MAVAIA_REQUIRE_AUTH`

### Repo assistant rules already exist
- Cursor rules live under `.cursor/rules/` (engineering + governance). When changing core architecture (registry/client/server), read these first.
- The “Sovereign Peer” persona rules are in `.cursor/rules/persona_sovereign_peer.mdc` (direct, minimal fluff).

### Project workflow docs
- `conductor/workflow.md` documents the repo’s workflow expectations (plan as source-of-truth, quality gates).
- `conductor/tech-stack.md` is treated as a deliberate contract; update it before introducing new stack-level dependencies.

### Cursor MCP (GitHub)
- Project-level Cursor MCP config lives at `.cursor/mcp.json`.
- Provide a GitHub PAT via `GITHUB_PERSONAL_ACCESS_TOKEN` in the environment Cursor launches with (do not commit tokens).


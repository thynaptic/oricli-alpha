## Oricli-Alpha

**Oricli-Alpha** is a modular cognitive framework for building intelligent applications. It provides:
- a plug-and-play brain module system
- an OpenAI-compatible HTTP API
- a Python client for direct module execution
- a lightweight UI for interactive testing

**System identifier**: Oricli-Alpha follows the TR-2025-01 naming scheme. The system identifier is derived from discovered cognitive modules and is available via `from oricli_core import SYSTEM_ID` (and `SYSTEM_ID_FULL`).

## What’s in this repo

- **Core package**: `oricli_core/`
- **Brain modules**: `oricli_core/brain/modules/` (auto-discovered)
- **OpenAI-compatible API**: `oricli_core/api/`
- **UI**: `ui_app.py` + `ui_static/`
- **Scripts**: `scripts/`
- **Docs**: `docs/`

## Installation

### Prerequisites

- Python **3.8+**
- Recommended: a virtual environment (`venv` or `.venv`)

### Install from source (editable)

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install --upgrade pip setuptools wheel
pip install -e .
```

### Optional dependency groups

This repo uses optional dependency groups (see `pyproject.toml`):

```bash
# Developer tools
pip install -e ".[dev]"

# Web search support
pip install -e ".[search]"

# Sandbox/code-execution support (Docker client)
pip install -e ".[sandbox]"

# Memory backends / local storage extras
pip install -e ".[memory]"

# Data / ML stack (heavier)
pip install -e ".[data,ml]"
```

### Verify installation

```bash
python3 scripts/check_dependencies.py
```

## Quick start

### One command (API + UI)

```bash
./scripts/start_servers.sh
```

Notes:
- The launcher defaults to `MAVAIA_API_PORT=8001` and `MAVAIA_UI_PORT=5000` (see `scripts/start_servers.sh`).
- The API server module itself defaults to port `8000` if you run it directly; the launcher overrides this.

### Start the API server (manual)

```bash
# Entry point (installed via pyproject [project.scripts])
oricli-server --host 0.0.0.0 --port 8000

# Or module execution
python3 -m oricli_core.api.server --host 0.0.0.0 --port 8000
```

### Start the UI server (manual)

```bash
MAVAIA_API_BASE="http://localhost:8000" python3 ui_app.py
```

## API usage (OpenAI-compatible)

### Chat completions

```bash
curl -X POST http://localhost:8000/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{
    "model": "oricli-cognitive",
    "messages": [{"role": "user", "content": "Hello"}]
  }'
```

### Embeddings

```bash
curl -X POST http://localhost:8000/v1/embeddings \
  -H "Content-Type: application/json" \
  -d '{
    "input": "text to embed",
    "model": "oricli-embeddings"
  }'
```

### Introspection

```bash
curl http://localhost:8000/v1/models
curl http://localhost:8000/v1/modules
curl http://localhost:8000/v1/metrics
curl http://localhost:8000/v1/health/modules
```

## Python client usage

```python
from oricli_core import Oricli-AlphaClient

client = Oricli-AlphaClient()

resp = client.chat.completions.create(
    model="oricli-cognitive",
    messages=[{"role": "user", "content": "Hello"}],
)

print(resp.choices[0].message.content)
```

## Configuration

Oricli-Alpha configuration uses environment variables
 (prefix `MAVAIA_`) with sensible defaults.

### Common environment variables

- **`MAVAIA_API_HOST`**: API bind host (default varies by script; often `0.0.0.0`)
- **`MAVAIA_API_PORT`**: API port (launcher default: `8001`; server default: `8000`)
- **`MAVAIA_API_KEY`**: API key (optional unless auth is enabled)
- **`MAVAIA_REQUIRE_AUTH`**: set to `true` to require auth
- **`MAVAIA_UI_HOST`**: UI bind host (default: `0.0.0.0`)
- **`MAVAIA_UI_PORT`**: UI port (default: `5000`)
- **`MAVAIA_API_BASE`**: UI → API base URL (default in UI: `http://localhost:8000`)
- **`MAVAIA_UI_ATTACHMENT_MB`**: max UI attachment size in MB (default: `5`)

### Configuration precedence

Command-line arguments override environment variables; environment variables override defaults.

## Brain modules

Modules live in `oricli_core/brain/modules/` and are auto-discovered by the registry.

- Full module list: see `MODULES.md`
- Module development guide: see `docs/module_development.md`

## API docs

When the API server is running:

- Swagger UI: `http://localhost:8000/docs`
- OpenAPI JSON: `http://localhost:8000/openapi.json`

For more details, see `docs/api_documentation.md`.

## Development & testing

```bash
python3 /workspace/run_quick_tests.py
python3 /workspace/run_tests.py
```

## Troubleshooting

### UI can’t reach the API

- Ensure the API server is running.
- Ensure `MAVAIA_API_BASE` matches the API URL, e.g. `MAVAIA_API_BASE="http://localhost:8001"`.

### Optional dependencies

Some modules require optional extras (e.g. `.[search]`, `.[sandbox]`, `.[ml]`). If a dependency is missing, the module should degrade gracefully and log the reason at debug level.

## Repository links

- Source: [thynaptic/oricli-alpha](https://github.com/thynaptic/oricli-alpha)

## Project structure

```text
oricli-alpha/
├── oricli_core/              # Python package
│   ├── api/                  # FastAPI server + OpenAI compatibility layer
│   ├── brain/                # Module system, registry, orchestration
│   │   └── modules/          # Brain modules (auto-discovered)
│   ├── services/             # Service layer (tools, integrations)
│   └── types/                # Pydantic request/response models
├── docs/                     # Reference docs
├── scripts/                  # Dev and ops scripts
├── ui_app.py                 # Flask UI server
├── ui_static/                # UI assets
└── pyproject.toml            # Packaging + dependency groups
```

## Running tests

```bash
python3 /workspace/run_quick_tests.py
python3 /workspace/run_tests.py
```

## Code quality (optional)

```bash
pip install -e ".[dev]"
black oricli_core/
ruff check oricli_core/
mypy oricli_core/
```

## Creating brain modules

Brain modules are auto-discovered from `oricli_core/brain/modules/`. A module must:
- inherit `BaseBrainModule`
- expose `metadata`
- implement `execute(operation, params)`

Example (minimal):

```python
from __future__ import annotations

from typing import Any

from oricli_core.brain.base_module import BaseBrainModule, ModuleMetadata
from oricli_core.exceptions import InvalidParameterError


class MyModule(BaseBrainModule):
    """Example module showing required structure."""

    @property
    def metadata(self) -> ModuleMetadata:
        return ModuleMetadata(
            name="my_module",
            version="1.0.0",
            description="Example module",
            operations=["echo"],
            dependencies=[],
        )

    def execute(self, operation: str, params: dict[str, Any]) -> dict[str, Any]:
        if operation == "echo":
            text = params.get("text", "")
            if not isinstance(text, str) or not text.strip():
                raise InvalidParameterError(
                    parameter="text",
                    value=str(text),
                    reason="text must be a non-empty string",
                )
            return {"success": True, "text": text}

        raise InvalidParameterError(
            parameter="operation",
            value=str(operation),
            reason="Unknown operation for my_module",
        )
```

For deeper guidance, see `docs/module_development.md`.

## Examples

### Basic Chat Completion

```python
from oricli_core import Oricli-AlphaClient

client = Oricli-AlphaClient()
response = client.chat.completions.create(
    model="oricli-cognitive",
    messages=[
        {"role": "system", "content": "You are a helpful assistant."},
        {"role": "user", "content": "Explain quantum computing."}
    ],
    temperature=0.7,
    max_tokens=1000
)
```

### Streaming Responses

```python
# Streaming is supported via the API
import json
import httpx

with httpx.stream(
    "POST",
    "http://localhost:8000/v1/chat/completions",
    json={
        "model": "oricli-cognitive",
        "messages": [{"role": "user", "content": "Hello"}],
        "stream": True
    }
) as response:
    for line in response.iter_lines():
        if not line:
            continue
        if isinstance(line, bytes):
            line = line.decode("utf-8", errors="ignore")
        if line.startswith("data: "):
            payload = line[6:].strip()
            if payload == "[DONE]":
                break
            data = json.loads(payload)
            if "choices" in data:
                print(data["choices"][0]["delta"].get("content", ""), end="")
```

### Direct Module Access

```python
# Access modules directly
result = client.brain.embeddings.generate(text="Hello world")
similarity = client.brain.embeddings.similarity(
    text1="Hello",
    text2="Hi"
)
```

### Custom Module Execution

```python
# Execute module operations directly
result = client.execute_module_operation(
    module_name="reasoning",
    operation="reason",
    params={"query": "What is 2+2?", "context": "Math"}
)
```

## Contributing

Contributions are welcome! Please:

1. Follow the code style (Black, Ruff)
2. Add type hints to all functions
3. Write comprehensive docstrings
4. Add tests for new features
5. Update documentation

See [Module Development Guide](docs/module_development.md) for module development guidelines.

## License

MIT License - see LICENSE file for details.

## Support

- **Documentation**: [docs/](docs/)
- **Issues**: [GitHub Issues](https://github.com/thynaptic/oricli-alpha/issues)
- **Email**: ai@thynaptic.com

## Design partners

If you’re evaluating Oricli-Alpha as a design partner, see `README_DESIGN_PARTNERS.md`.

## Version

Current version: **1.0.0**

## System Identifier

Oricli-Alpha uses a standardized cognitive system naming scheme (see TR-2025-01-Cognitive-System-Naming-Scheme). The system identifier follows the format `oricli-{module_count}c`, where the module count is dynamically discovered via `ModuleRegistry.discover_modules()`.

### Base Identifier

```python
from oricli_core import SYSTEM_ID
print(SYSTEM_ID)  # e.g., "oricli-250c"
```

### Sub-Naming Support

You can add custom sub-names to the system identifier (e.g., "alpha", "Pro", "Flash"):

```python
from oricli_core import (
    SYSTEM_ID,
    SYSTEM_ID_FULL,
    get_system_identifier_with_subname,
    set_system_subname,
    get_system_subname
)

# Get identifier with specific subname
alpha_id = get_system_identifier_with_subname("alpha")
print(alpha_id)  # "oricli-250c-alpha"

# Set default subname for session
set_system_subname("Pro")
print(SYSTEM_ID_FULL())  # "oricli-250c-Pro"

# Clear subname
set_system_subname(None)
print(SYSTEM_ID_FULL())  # "oricli-250c"
```

You can also set the subname via environment variable:
```bash
export MAVAIA_SYSTEM_SUBNAME="Flash"
```

The system identifier represents the cognitive architecture composition and is distinct from API model identifiers (`oricli-cognitive`, `oricli-embeddings`).

## Acknowledgments

Oricli-Alpha Core is developed by Thynaptic Research as part of the Oricli-Alpha cognitive systems framework.


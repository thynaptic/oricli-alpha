# Mavaia Core

**Mavaia Core** is a modular AI cognitive framework for building intelligent applications. It provides a plug-and-play architecture for cognitive modules, an OpenAI-compatible API, and a unified interface for all Mavaia capabilities.

**System Identifier:** Mavaia follows the standardized cognitive system naming scheme (TR-2025-01). The system identifier is dynamically generated based on discovered cognitive modules and follows the format `mavaia-{module_count}c`. Access it programmatically via `from mavaia_core import SYSTEM_ID`.

## Features

- **Modular Architecture**: Plug-and-play brain modules that extend capabilities without code changes
- **OpenAI-Compatible API**: Drop-in replacement for OpenAI API endpoints
- **Cognitive Pipeline**: Composable cognitive modules for reasoning, memory, embeddings, and more
- **Auto-Discovery**: Modules are automatically discovered and registered
- **Type-Safe**: Full type hints and Pydantic models throughout
- **Production-Ready**: Comprehensive error handling, validation, and documentation

## Installation

### From Source

```bash
git clone https://github.com/thynaptic/mavaia-core.git
cd mavaia-core
pip install -e .
```

### Development Installation

```bash
pip install -e ".[dev]"
```

### Verify Installation

Check that all dependencies are installed:

```bash
python3 scripts/check_dependencies.py
```

If dependencies are missing, install them:

```bash
pip install -e .
```

## Quick Start

> **Note:** Make sure to activate your virtual environment first:
> ```bash
> source venv/bin/activate
> ```
>
> See [QUICKSTART.md](QUICKSTART.md) for detailed startup instructions and troubleshooting.

### Python Client

```python
from mavaia_core import MavaiaClient

# Initialize client
client = MavaiaClient()

# Chat completion
response = client.chat.completions.create(
    model="mavaia-cognitive",
    messages=[
        {"role": "user", "content": "Hello, how are you?"}
    ],
    temperature=0.7
)

print(response.choices[0].message.content)

# Embeddings
embedding = client.embeddings.create(
    input="text to embed",
    model="mavaia-embeddings"
)

# Direct module access
result = client.brain.reasoning.reason(query="What is 2+2?")
```

### 🚀 Quick Start (One-Click)

Start everything with one command:

```bash
./scripts/start_servers.sh
```

This starts both API and UI servers and opens your browser automatically!

### HTTP Server (Manual)

Start the API server:

```bash
# Using the entry point (after pip install -e .)
mavaia-server --host 0.0.0.0 --port 8000

# Or using the startup script
python3 scripts/start_server.py --host 0.0.0.0 --port 8000

# Or directly
python3 -m mavaia_core.api.server --host 0.0.0.0 --port 8000
```

Or programmatically:

```python
from mavaia_core.api.server import run_server

run_server(host="0.0.0.0", port=8000)
```

### UI Server

Start the UI server:

```bash
# Using the startup script
python3 scripts/start_ui.py

# Or directly
python3 ui_app.py
```

### API Usage

```bash
# Chat completion
curl -X POST http://localhost:8000/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{
    "model": "mavaia-cognitive",
    "messages": [{"role": "user", "content": "Hello"}]
  }'

# Embeddings
curl -X POST http://localhost:8000/v1/embeddings \
  -H "Content-Type: application/json" \
  -d '{
    "input": "text to embed",
    "model": "mavaia-embeddings"
  }'

# List models
curl http://localhost:8000/v1/models

# List modules
curl http://localhost:8000/v1/modules
```

## Architecture

### Core Components

1. **BaseBrainModule**: Abstract base class for all cognitive modules
2. **ModuleRegistry**: Auto-discovery and management of brain modules
3. **MavaiaClient**: Unified client interface for all capabilities
4. **OpenAICompatibleAPI**: OpenAI-compatible HTTP API endpoints

### Module System

Brain modules are Python classes that inherit from `BaseBrainModule`. They are automatically discovered from the `mavaia_core/brain/modules/` directory and made available via:

- Python client: `client.brain.module_name.operation()`
- HTTP API: `POST /v1/modules/module_name/operation`
- Direct execution: `client.execute_module_operation(module_name, operation, params)`

### Module Structure

Each module must implement:

- `metadata` property: Returns `ModuleMetadata` with module information
- `execute(operation, params)`: Executes operations supported by the module

Optional methods:

- `initialize()`: Initialize resources (models, etc.)
- `validate_params(operation, params)`: Validate parameters
- `cleanup()`: Clean up resources

See [Module Development Guide](docs/module_development.md) for details.

## Available Modules

Mavaia Core includes 78+ brain modules across categories:

### Core Intelligence
- `cognitive_generator`: Main cognitive generation orchestrator
- `reasoning`: Advanced reasoning capabilities
- `embeddings`: Text embedding generation
- `thought_to_text`: Thought-to-text conversion

### Memory & Context
- `conversational_memory`: Conversation memory management
- `memory_graph`: Memory graph operations
- `memory_processor`: Memory processing pipeline

### Language & Communication
- `neural_grammar`: Neural grammar processing
- `natural_language_flow`: Natural language flow generation
- `response_naturalizer`: Response naturalization
- `linguistic_priors`: Linguistic prior knowledge

### Reasoning & Logic
- `chain_of_thought`: Chain-of-Thought reasoning
- `tree_of_thought`: Tree-of-Thought multi-path exploration
- `mcts_reasoning`: Monte-Carlo Thought Search
- `logical_deduction`: Logical deduction
- `causal_inference`: Causal inference

See [MODULES.md](MODULES.md) for the complete list.

## Configuration

### Environment Variables

- `MAVAIA_API_KEY`: API key for authentication (optional)
- `MAVAIA_API_BASE`: API base URL (default: `http://localhost:8000`)
- `MAVAIA_UI_PORT`: UI server port (default: `5000`)

### Server Configuration

```python
from mavaia_core.api.server import create_app

app = create_app(
    modules_dir=Path("/path/to/modules"),
    api_key="your-api-key",
    enable_cors=True
)
```

## API Documentation

Complete API documentation is available at:

- **Swagger UI**: `http://localhost:8000/docs`
- **ReDoc**: `http://localhost:8000/redoc`
- **OpenAPI JSON**: `http://localhost:8000/openapi.json`

### Mavaia-Specific Endpoints

- `GET /v1/metrics` - Get module metrics and statistics
- `GET /v1/health/modules` - Get health status of all modules
- `GET /v1/health/modules/{module_name}` - Get detailed health for a module

See [API Documentation](docs/api_documentation.md) for detailed endpoint documentation.
See [Brain Expansion Guide](docs/brain_expansion.md) for information about the new brain infrastructure.

## Development

### Project Structure

```
mavaia-core/
├── mavaia_core/          # Main package
│   ├── api/              # API server and OpenAI compatibility
│   ├── brain/             # Brain module system
│   │   ├── modules/      # Brain modules (auto-discovered)
│   │   └── registry.py   # Module registry
│   ├── client.py         # Main client interface
│   └── types/            # Type definitions and models
├── docs/                  # Documentation
├── ui_static/             # UI static files
└── pyproject.toml         # Project configuration
```

### Running Tests

```bash
pytest
```

### Code Quality

```bash
# Format code
black mavaia_core/

# Lint code
ruff check mavaia_core/

# Type checking
mypy mavaia_core/
```

### Creating Modules

1. Create a new Python file in `mavaia_core/brain/modules/`
2. Inherit from `BaseBrainModule`
3. Implement required methods
4. Module is automatically discovered

Example:

```python
from mavaia_core.brain.base_module import BaseBrainModule, ModuleMetadata
from typing import Any

class MyModule(BaseBrainModule):
    @property
    def metadata(self) -> ModuleMetadata:
        return ModuleMetadata(
            name="my_module",
            version="1.0.0",
            description="My custom module",
            operations=["operation1"],
            dependencies=[],
        )
    
    def execute(self, operation: str, params: dict[str, Any]) -> dict[str, Any]:
        if operation == "operation1":
            return {"result": "success"}
        raise ValueError(f"Unknown operation: {operation}")
```

See [Module Development Guide](docs/module_development.md) for complete details.

## Examples

### Basic Chat Completion

```python
from mavaia_core import MavaiaClient

client = MavaiaClient()
response = client.chat.completions.create(
    model="mavaia-cognitive",
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
import httpx

with httpx.stream(
    "POST",
    "http://localhost:8000/v1/chat/completions",
    json={
        "model": "mavaia-cognitive",
        "messages": [{"role": "user", "content": "Hello"}],
        "stream": True
    }
) as response:
    for line in response.iter_lines():
        if line.startswith("data: "):
            data = json.loads(line[6:])
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
- **Issues**: GitHub Issues
- **Email**: ai@thynaptic.com

## Version

Current version: **1.0.0**

## System Identifier

Mavaia uses a standardized cognitive system naming scheme (see TR-2025-01-Cognitive-System-Naming-Scheme). The system identifier follows the format `mavaia-{module_count}c`, where the module count is dynamically discovered via `ModuleRegistry.discover_modules()`.

### Base Identifier

```python
from mavaia_core import SYSTEM_ID
print(SYSTEM_ID)  # e.g., "mavaia-137c"
```

### Sub-Naming Support

You can add custom sub-names to the system identifier (e.g., "alpha", "Pro", "Flash"):

```python
from mavaia_core import (
    SYSTEM_ID,
    SYSTEM_ID_FULL,
    get_system_identifier_with_subname,
    set_system_subname,
    get_system_subname
)

# Get identifier with specific subname
alpha_id = get_system_identifier_with_subname("alpha")
print(alpha_id)  # "mavaia-137c-alpha"

# Set default subname for session
set_system_subname("Pro")
print(SYSTEM_ID_FULL())  # "mavaia-137c-Pro"

# Clear subname
set_system_subname(None)
print(SYSTEM_ID_FULL())  # "mavaia-137c"
```

You can also set the subname via environment variable:
```bash
export MAVAIA_SYSTEM_SUBNAME="Flash"
```

The system identifier represents the cognitive architecture composition and is distinct from API model identifiers (`mavaia-cognitive`, `mavaia-embeddings`).

## Acknowledgments

Mavaia Core is developed by Thynaptic Research as part of the Mavaia cognitive systems framework.


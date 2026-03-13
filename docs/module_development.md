# Module Development Guide

This guide explains how to create new brain modules for Oricli-Alpha Core.

## Overview

Brain modules are plug-and-play Python modules that extend Oricli-Alpha's capabilities. They are automatically discovered and made available via the API without requiring code changes.

## Creating a Module

### Basic Structure

Create a new Python file in the `oricli_core/brain/modules/` directory:

```python
from oricli_core.brain.base_module import BaseBrainModule, ModuleMetadata
from typing import Any

class MyModule(BaseBrainModule):
    """My custom module"""
    
    @property
    def metadata(self) -> ModuleMetadata:
        return ModuleMetadata(
            name="my_module",
            version="1.0.0",
            description="Description of what this module does",
            operations=["operation1", "operation2"],
            dependencies=["required-package"],
            enabled=True,
            model_required=False
        )
    
    def execute(self, operation: str, params: dict[str, Any]) -> dict[str, Any]:
        """Execute an operation"""
        if operation == "operation1":
            return self._operation1(params)
        elif operation == "operation2":
            return self._operation2(params)
        else:
            raise ValueError(f"Unknown operation: {operation}")
    
    def _operation1(self, params: dict[str, Any]) -> dict[str, Any]:
        """Implementation of operation1"""
        # Your implementation here
        return {"result": "success"}
    
    def _operation2(self, params: dict[str, Any]) -> dict[str, Any]:
        """Implementation of operation2"""
        # Your implementation here
        return {"result": "success"}
```

### Required Methods

#### `metadata` (property)

Returns metadata about the module:

- `name`: Unique module identifier
- `version`: Module version
- `description`: What the module does
- `operations`: List of supported operations
- `dependencies`: Required Python packages
- `enabled`: Whether module is enabled (default: True)
- `model_required`: Whether module needs a HuggingFace model (default: False)

#### `execute(operation, params)`

Executes an operation:

- `operation`: Operation name (from `operations` list)
- `params`: Operation parameters (dict)
- Returns: Result dictionary

### Optional Methods

#### `validate_params(operation, params)`

Validates parameters before execution:

```python
def validate_params(self, operation: str, params: dict[str, Any]) -> bool:
    if operation == "operation1":
        return "required_param" in params
    return True
```

#### `initialize()`

Initializes the module (load models, etc.):

```python
def initialize(self) -> bool:
    # Load models, setup resources
    self.model = load_model()
    return True
```

#### `cleanup()`

Cleans up resources:

```python
def cleanup(self) -> None:
    # Cleanup resources
    if hasattr(self, 'model'):
        del self.model
```

## Module Discovery

Modules are automatically discovered when:

1. The module file is in the `brain_modules/` directory
2. The module class inherits from `BaseBrainModule`
3. The module is not in the skip list (`__init__.py`, `base_module.py`, etc.)

## Accessing Modules

### Via Python Client

```python
from oricli_core import Oricli-AlphaClient

client = Oricli-AlphaClient()
result = client.brain.my_module.operation1(param1="value1")
```

### Via API

```bash
curl -X POST http://localhost:8000/v1/modules/my_module/operation1 \
  -H "Content-Type: application/json" \
  -d '{"param1": "value1"}'
```

### Via oricli_brain.py (Swift Bridge)

```python
# JSON request
{
  "operation": "my_module.operation1",
  "params": {"param1": "value1"}
}
```

## Best Practices

1. **Error Handling**: Always handle errors gracefully and return meaningful error messages
2. **Validation**: Validate all input parameters
3. **Documentation**: Document all operations and parameters
4. **Testing**: Write tests for your module
5. **Dependencies**: List all required dependencies in `metadata.dependencies`
6. **Versioning**: Use semantic versioning for module versions

## Example: Simple Calculator Module

```python
from oricli_core.brain.base_module import BaseBrainModule, ModuleMetadata
from typing import Any

class CalculatorModule(BaseBrainModule):
    """Simple calculator module"""
    
    @property
    def metadata(self) -> ModuleMetadata:
        return ModuleMetadata(
            name="calculator",
            version="1.0.0",
            description="Simple calculator operations",
            operations=["add", "subtract", "multiply", "divide"],
            dependencies=[],
            enabled=True,
            model_required=False
        )
    
    def validate_params(self, operation: str, params: dict[str, Any]) -> bool:
        if operation in ["add", "subtract", "multiply", "divide"]:
            return "a" in params and "b" in params
        return True
    
    def execute(self, operation: str, params: dict[str, Any]) -> dict[str, Any]:
        a = params.get("a", 0)
        b = params.get("b", 0)
        
        if operation == "add":
            return {"result": a + b}
        elif operation == "subtract":
            return {"result": a - b}
        elif operation == "multiply":
            return {"result": a * b}
        elif operation == "divide":
            if b == 0:
                raise ValueError("Division by zero")
            return {"result": a / b}
        else:
            raise ValueError(f"Unknown operation: {operation}")
```

## Troubleshooting

### Module Not Discovered

- Check that the module file is in `brain_modules/` directory
- Verify the class inherits from `BaseBrainModule`
- Check that the file is not in the skip list
- Review error logs for initialization failures

### Module Initialization Failed

- Check that all dependencies are installed
- Verify `initialize()` returns `True`
- Review error logs for specific errors

### Operation Not Found

- Verify the operation is listed in `metadata.operations`
- Check that `execute()` handles the operation
- Review error logs for specific errors

## Next Steps

- Review existing modules in `brain_modules/` for examples
- Check the [API Documentation](api_documentation.md) for API usage
- See the [Migration Guide](migration_guide.md) for integrating with existing code


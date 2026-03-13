---
name: Comprehensive Module Testing Suite
overview: "Expand the test file to test ALL modules in oricli_core/brain/modules/ using a hybrid approach: smoke tests for all modules plus detailed integration tests for critical modules."
todos:
  - id: "1"
    content: Add session fixture for module discovery that discovers all modules once per test session
    status: completed
  - id: "2"
    content: Create parameterized TestAllModules class with smoke tests for module initialization
    status: completed
    dependencies:
      - "1"
  - id: "3"
    content: Add parameterized test for metadata structure validation (name, version, description, operations)
    status: completed
    dependencies:
      - "1"
  - id: "4"
    content: Add parameterized test for all operations with minimal valid parameters
    status: completed
    dependencies:
      - "1"
  - id: "5"
    content: Add error handling tests (unknown operations, invalid params) for all modules
    status: completed
    dependencies:
      - "1"
  - id: "6"
    content: Create reusable fixtures for common test data (queries, documents, etc.)
    status: completed
  - id: "7"
    content: Add detailed integration tests for ReasoningModule with all operations
    status: completed
  - id: "8"
    content: Add detailed integration tests for CognitiveGenerator module
    status: completed
  - id: "9"
    content: Add detailed integration tests for Embeddings module
    status: completed
  - id: "10"
    content: Add detailed integration tests for SafetyFramework module
    status: completed
  - id: "11"
    content: Add test reporting/logging to identify modules needing enhancement
    status: completed
    dependencies:
      - "2"
      - "3"
      - "4"
      - "5"
---

# Comprehensive Module Testing Suite

## Overview

Modify `tests/test_multi_agent_pipeline.py` to comprehensively test all modules discovered in `oricli_core/brain/modules/`. The test suite will use a hybrid approach:

- **Smoke tests** for all discovered modules (verify initialization, metadata, and basic operation calls)
- **Detailed integration tests** for critical modules (existing tests plus additional coverage)

## Implementation Strategy

### 1. Dynamic Module Discovery

- Use `ModuleRegistry.discover_modules()` to discover all modules
- Use `ModuleRegistry.list_modules()` to get all registered module names
- Create a pytest fixture that discovers modules once per test session

### 2. Universal Smoke Test Suite

Create a parameterized test class that tests all modules:

- **Test module initialization**: Verify each module can be instantiated and initialized
- **Test metadata structure**: Verify metadata has required fields (name, version, description, operations)
- **Test operation execution**: For each operation in metadata, call it with minimal valid parameters
- **Test error handling**: Verify unknown operations raise `ValueError`, empty/invalid params handled gracefully

### 3. Enhanced Integration Tests

Keep existing detailed tests for critical modules:

- `MultiAgentPipeline` (already tested)
- `QueryAgent` (already tested)
- `RetrieverAgent` (already tested)
- `RerankerAgent` (already tested)
- `SynthesisAgent` (already tested)
- `VerifierAgent` (already tested)

Add detailed tests for additional important modules:

- `ReasoningModule` - test reasoning operations
- `CognitiveGenerator` - test response generation
- `Embeddings` - test embedding generation
- `SafetyFramework` - test safety checks

### 4. Test Structure

The test file will be organized as:

```python
# Session fixture for module discovery
@pytest.fixture(scope="session")
def all_modules():
    """Discover and return all modules"""
    ModuleRegistry.discover_modules(verbose=True)
    return ModuleRegistry.list_modules()

# Parameterized smoke tests
class TestAllModules:
    """Smoke tests for all discovered modules"""
    
    @pytest.mark.parametrize("module_name", all_modules())
    def test_module_initialization(self, module_name):
        """Test that module can be initialized"""
    
    @pytest.mark.parametrize("module_name", all_modules())
    def test_module_metadata(self, module_name):
        """Test metadata structure"""
    
    @pytest.mark.parametrize("module_name,operation", ...)
    def test_module_operations(self, module_name, operation):
        """Test all operations with minimal params"""

# Existing detailed test classes (keep as-is)
class TestMultiAgentPipeline:
    # ... existing tests ...

class TestQueryAgent:
    # ... existing tests ...
```

### 5. Test Data and Fixtures

- Create reusable fixtures for common test data (sample queries, documents, etc.)
- Use minimal valid parameters for smoke tests
- Use realistic parameters for integration tests

### 6. Error Reporting

- Tests should clearly identify which module/operation failed
- Collect and report modules that fail initialization
- Report operations that fail or are missing

## Files to Modify

- `tests/test_multi_agent_pipeline.py` - Expand with universal smoke tests and additional integration tests

## Benefits

1. **Comprehensive Coverage**: All modules are tested, not just a subset
2. **Early Detection**: Smoke tests catch initialization and basic execution issues
3. **Enhancement Identification**: Failed tests clearly show which modules need work
4. **Maintainability**: Parameterized tests automatically cover new modules
5. **CI/CD Ready**: Fast smoke tests can run on every commit, detailed tests on PRs

## Testing Approach

For each module operation, smoke tests will:

1. Get module instance via `ModuleRegistry.get_module(name)`
2. Call `execute(operation, minimal_params)` where minimal_params are the absolute minimum required
3. Verify result is a dict (no exceptions)
4. Verify result has expected structure (e.g., "success" key for operations that return it)

For integration tests:

- Use realistic inputs
- Verify output correctness
- Test edge cases and error conditions
- Test parameter validation
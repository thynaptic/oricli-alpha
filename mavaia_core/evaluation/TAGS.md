# Test Tags Reference

## Default Tags

The test suite includes 5 default tags designed to make testing frictionless:

### 1. `quick`
- **Purpose**: Fast-running tests that complete quickly
- **Use Case**: Run quick tests for rapid feedback during development
- **Example**: `--tags quick` - Run only fast tests

### 2. `essential`
- **Purpose**: Core functionality tests that validate critical features
- **Use Case**: Run essential tests to verify core functionality works
- **Example**: `--tags essential` - Run only critical tests

### 3. `smoke`
- **Purpose**: Basic smoke tests that verify the system starts and basic operations work
- **Use Case**: Quick sanity checks before deeper testing
- **Example**: `--tags smoke` - Run smoke tests only

### 4. `integration`
- **Purpose**: Integration tests that test component interactions
- **Use Case**: Verify modules work together correctly
- **Example**: `--tags integration` - Run integration tests

### 5. `unit`
- **Purpose**: Unit tests that test individual components in isolation
- **Use Case**: Test individual module operations
- **Example**: `--tags unit` - Run unit tests only

## Tag Combination

Tags can be combined using `--tag-mode`:

### AND Mode (default: `--tag-mode all`)
Tests must have **ALL** specified tags:
```bash
# Test must have BOTH "quick" AND "essential" tags
python3 run_tests.py --tags quick essential --tag-mode all
```

### OR Mode (`--tag-mode any`)
Tests must have **AT LEAST ONE** specified tag:
```bash
# Test must have EITHER "quick" OR "essential" tag
python3 run_tests.py --tags quick essential --tag-mode any
```

## Usage Examples

```bash
# Run only quick tests
python3 run_tests.py --tags quick

# Run essential smoke tests (both tags required)
python3 run_tests.py --tags essential smoke

# Run quick OR essential tests (either tag)
python3 run_tests.py --tags quick essential --tag-mode any

# Run quick essential tests for a specific module
python3 run_tests.py --module chain_of_thought --tags quick essential
```

## Adding Tags to Test Cases

Tags are defined in test case JSON files:

```json
{
  "id": "test_001",
  "category": "functional",
  "tags": ["quick", "essential", "unit"],
  ...
}
```

## Custom Tags

You can define custom tags in your test cases for project-specific needs:
- `performance` - Performance tests
- `regression` - Regression tests
- `experimental` - Experimental features
- `deprecated` - Tests for deprecated functionality


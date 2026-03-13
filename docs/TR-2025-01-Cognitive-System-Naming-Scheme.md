# Cognitive System Naming Scheme

**Document Type:** Architecture Governance  
**Report Number:** TR-2025-01  
**Date:** 2025-01-27  
**Version:** v2.0.0  
**Style Mode:** Hard Technical Doctrine

---

## Abstract

This document defines the standardized naming protocol for cognitive systems developed within the Thynaptic research framework. The protocol distinguishes cognitive module-based architectures from parameter-based LLM naming conventions, ensuring accurate representation of system composition. All cognitive systems must follow this specification for system identification, documentation, and deployment. The protocol includes base identifier generation, sub-naming extensions, and validation procedures.

---

## Model Training & Architecture

This section defines the naming format specification, architecture type classification, quantifier calculation rules, and sub-naming protocol. All specifications are mechanism-first and reference implementation protocols.

### Naming Format Specification

The naming format follows the pattern:

```text
{system_name}-{quantifier}{architecture_type}[-{subname}]
```

Where:
- `{system_name}`: Base identifier (lowercase, alphanumeric, hyphens allowed)
- `{quantifier}`: Numeric count representing system scale
- `{architecture_type}`: Single-letter suffix indicating architecture class
- `{subname}`: Optional qualifier (alphanumeric, hyphens, underscores)

### Architecture Type Suffixes

| Suffix | Architecture Type | Definition |
|--------|------------------|------------|
| `c` | Cognitive | Cognitive module-based architecture (no LLM inference) |
| `p` | Parameter | LLM-based system (parameter count in billions) |
| `h` | Hybrid | Combined cognitive + LLM architecture |
| `s` | Symbolic | Pure symbolic reasoning system |

### Quantifier Rules

**For Cognitive Systems (`c` suffix):**
- Quantifier represents total count of cognitive modules in the system
- Counted via `ModuleRegistry.discover_modules()` discovery process
- Includes all registered `BaseBrainModule` instances discovered from filesystem
- Count is determined at runtime through module discovery protocol
- Example: `oricli-137c` indicates 137 cognitive modules

**For Parameter Systems (`p` suffix):**
- Quantifier represents parameter count in billions
- Rounded to one decimal place for values < 10B
- Rounded to nearest integer for values ≥ 10B
- Example: `model-1.7p` indicates 1.7 billion parameters

**For Hybrid Systems (`h` suffix):**
- Quantifier format: `{cognitive_modules}c-{parameters}p`
- Example: `system-24c-3.5p` indicates 24 cognitive modules + 3.5B parameter LLM

**For Symbolic Systems (`s` suffix):**
- Quantifier represents symbolic rule count or solver count
- Example: `reasoner-12s` indicates 12 symbolic solvers

### Sub-Naming Protocol

Sub-naming extends the base identifier with optional qualifiers following the format:

```text
{base_identifier}-{subname}
```

**Subname Rules:**

- Must contain only alphanumeric characters, hyphens, and underscores
- Cannot be empty
- Case-sensitive (preserves capitalization)
- Examples: `alpha`, `Pro`, `Flash`, `dev-2025`

**Subname Priority:**
1. Programmatically set via `set_system_subname()` function call
2. `MAVAIA_SYSTEM_SUBNAME` environment variable
3. Falls back to base identifier if no subname is set

---

## Evaluation Methods

This section defines the module discovery protocol, validation procedures, and compliance verification methods. All evaluation procedures reference specific implementation methods and data sources.

### Module Discovery Protocol

The module discovery process follows this procedure:

1. Execute `ModuleRegistry.discover_modules(verbose=False)`
2. Iterate through all Python files in `oricli_core/brain/modules/` directory
3. Skip base files: `__init__.py`, `base_module.py`, `module_registry.py`, `model_manager.py`
4. Import each module file and inspect for classes inheriting from `BaseBrainModule`
5. Instantiate each discovered module class to obtain `ModuleMetadata`
6. Register module with `ModuleRegistry.register_module(name, class, metadata)`
7. Count total registered modules via `len(ModuleRegistry.list_modules())`

**Current System Assignment:**
- **System Identifier:** `oricli-137c`
- **Module Count:** 137 (discovered via ModuleRegistry)
- **Architecture Type:** Cognitive (`c` suffix)
- **LLM Count:** 0
- **Architecture Composition:** 100% cognitive module-based

### Validation Protocol

All system identifiers must pass validation:

**Format Validation:**

- Base format regex: `^[a-z0-9-]+-\d+(\.\d+)?[cphs]$`
- With subname regex: `^[a-z0-9-]+-\d+(\.\d+)?[cphs]-[a-zA-Z0-9_-]+$`

**Content Validation:**

- Quantifier must match discovered/measured count
- Architecture type must match actual system composition
- Subname must pass character validation

**Implementation Validation:**

- Module count verified via `ModuleRegistry.discover_modules()`
- Discovery process: `oricli_core/brain/modules/module_registry.py`
- All modules must inherit from `BaseBrainModule`

---

## Safeguards & Safety Frameworks

This section defines mandatory compliance requirements, prohibited practices, and version tracking protocols. All requirements are policy-driven and reference enforcement mechanisms.

### Naming Scheme Compliance

**Mandatory Components:**

All system names must include:

1. Base identifier (lowercase)
2. Quantifier (numeric)
3. Architecture type suffix (single letter)

**Prohibited Practices:**

The following naming patterns are prohibited:
- Parameter-based suffixes (`b`, `B`, `billion`) for cognitive systems
- Ambiguous quantifiers without architecture type
- Version numbers in place of quantifiers
- Marketing or descriptive terms in the quantifier field
- Invalid characters in subname (spaces, special characters except hyphens/underscores)

### Version Tracking

System versions are tracked separately from naming scheme:
- Naming scheme reflects architecture composition
- Version numbers follow semantic versioning (vMAJOR.MINOR.PATCH)
- Version changes do not require naming scheme updates unless architecture composition changes
- Subname changes do not affect base identifier or version tracking

---

## Implementation Requirements

### Code References

All system identifiers in code must use the standardized naming scheme:

**Python Implementation:**

```python
from oricli_core import SYSTEM_ID, SYSTEM_ID_FULL, get_system_identifier_with_subname

# Base identifier
SYSTEM_ID  # "oricli-137c"

# Full identifier with subname (if set)
SYSTEM_ID_FULL()  # "oricli-137c-alpha" (if subname set)

# Generate identifier with specific subname
get_system_identifier_with_subname("alpha")  # "oricli-137c-alpha"
```

**Environment Variable:**

```bash
export MAVAIA_SYSTEM_SUBNAME="Pro"
```

**Function-Based Configuration:**

```python
from oricli_core import set_system_subname, SYSTEM_ID_FULL

set_system_subname("Flash")
SYSTEM_ID_FULL()  # Returns "oricli-137c-Flash"
```

### Documentation References

All technical documentation must:
- Use the standardized naming scheme in system references
- Include architecture type suffix in all mentions
- Provide quantifier rationale in architecture descriptions
- Document subname usage when applicable

### Discovery and Validation

Before assigning a name:
1. Run module discovery process: `ModuleRegistry.discover_modules()`
2. Count registered modules: `len(ModuleRegistry.list_modules())`
3. Verify architecture type (cognitive/parameter/hybrid/symbolic)
4. Calculate quantifier according to Section 1.3
5. Validate against existing naming scheme
6. Test subname generation if applicable

---

## Behavioral Audits

This section documents current system validation results and compliance verification. All claims reference specific validation procedures and observed data.

### Current System Validation

**Oricli-Alpha Cognitive Architecture:**
- **Current Label:** `oricli-137c`
- **Validation Date:** 2025-01-27
- **Discovery Method:** `oricli_core.brain.modules.module_registry.ModuleRegistry.discover_modules()`
- **Module Count:** 137 registered `BaseBrainModule` instances
- **Architecture Verification:** 100% cognitive module-based, 0 LLMs
- **Subname Support:** Implemented via `oricli_core.system_identifier` module

### Naming Scheme Compliance Check

**Implementation Status:**

- Base identifier format: `oricli-137c` (verified)
- Quantifier matches discovered module count (137 modules confirmed)
- Architecture type suffix (`c`) matches system composition (100% cognitive modules)
- Sub-naming protocol implemented and validated (tested via `get_system_identifier_with_subname()`)
- Code references use standardized constants (`SYSTEM_ID`, `SYSTEM_ID_FULL`)
- API endpoints include system identifier in metadata (`/health` endpoint returns `system_id` and `system_id_full`)

---

## Limitations

### Known Constraints

- Module count may vary between discovery runs if modules are conditionally loaded
- Hybrid systems require separate validation of both component types
- Symbolic system quantifiers may use different counting methods
- Subname changes require runtime function calls; environment variable changes require process restart
- Base identifier (`SYSTEM_ID`) is computed at module import time and does not update dynamically

### Future Considerations

- Potential expansion for multi-architecture systems
- Quantifier precision requirements for very large systems
- Integration with semantic versioning system
- Subname validation rules may need expansion for complex qualifiers
- Automated naming scheme validation in CI/CD pipeline

---

## Forward Research Trajectories

### Planned Enhancements

- Automated naming scheme validation in CI/CD pipeline
- Integration with module discovery API
- Standardized naming scheme API for programmatic access
- Subname registry for standardized qualifiers
- Cross-architecture naming consistency validation

### Research Questions

- Optimal quantifier precision for hybrid systems
- Standardization of symbolic system quantifiers
- Cross-architecture naming consistency
- Subname taxonomy and classification system
- Dynamic identifier updates for runtime module changes

---

## References

- Module Registry Implementation: `oricli_core/brain/modules/module_registry.py`
- System Identifier Module: `oricli_core/system_identifier.py`
- Base Brain Module: `oricli_core/brain/base_module.py`
- Cognitive Generator: `oricli_core/brain/modules/cognitive_generator.py`
- Thynaptic Publication Style Framework: `.cursor/rules/thynaptic-publications.mdc`

---

**Document Status:** Active  
**Last Updated:** 2025-01-27  
**Next Review:** 2025-04-27  
**Current System Identifier:** `oricli-137c`


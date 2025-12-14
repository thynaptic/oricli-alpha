---
name: Split Custom Reasoning Module and Fix Test Failures
overview: "Split the 8547-line custom_reasoning_networks.py into two modules: keep neural architectures in the original, and move advanced puzzle solvers (zebra, spatial, ARC, web_of_lies) to a new advanced_reasoning_solvers.py module. Fix the JAX batch dimension error causing all tests to fail."
todos:
  - id: create_new_module
    content: Create advanced_reasoning_solvers.py module with BaseBrainModule structure and move all solver methods from custom_reasoning_networks.py
    status: completed
  - id: fix_jax_batch_error
    content: Fix JAX batch dimension error in MultiStepReasoningNetwork and other neural architectures - ensure consistent batch dimensions in attention layers
    status: completed
  - id: update_original_module
    content: Remove moved solver methods from custom_reasoning_networks.py and update execute() to delegate to new module
    status: completed
  - id: fix_response_formatting
    content: Fix response formatting for LiveBench evaluation - ensure proper response fields and meta-evaluator application
    status: completed
  - id: test_and_verify
    content: Run reasoning tests to verify 10/10 score and ensure both modules work correctly
    status: completed
---

# Plan: Split Custom Reasoning Module and Fix Test Failures

## Current State Analysis

- **File Size**: `custom_reasoning_networks.py` is 8547 lines - too large
- **Test Results**: 0/200 tests passing - all failing with JAX error: "q, k, v batch dims must match."
- **Root Cause**: The error occurs in neural network forward passes when batch dimensions don't match in attention layers

## Module Split Strategy

### New Module: `advanced_reasoning_solvers.py`

Move all advanced puzzle solver functionality:

- Zebra puzzle solver (`_solve_zebra_puzzle`, `_solve_zebra_with_z3`, `_parse_puzzle_constraints`)
- Spatial reasoning solver (`_solve_spatial_problem`, `_solve_2d_grid`, `_parse_spatial_constraints`, `_check_constraint`)
- ARC solver (`_solve_arc_problem`, `_solve_arc_task`, `_solve_arc_task_enhanced`, `_solve_arc_ensemble`, `_parse_grid_from_text`)
- Web of Lies solver (`_solve_web_of_lies`)
- Puzzle constraint parsing (`_parse_puzzle_constraints`, `_solve_puzzle_with_solver`)

### Keep in Original: `custom_reasoning_networks.py`

- Neural architectures (MultiStepReasoningNetwork, CausalInferenceModule, AnalogicalReasoningNetwork, ReasoningEnsemble)
- Core neural operations (multi_step_reasoning, causal_inference, analogical_reasoning, ensemble_reasoning)
- Model training/loading/saving operations
- Embedding generation and neural processing

## Critical Fixes Required

### 1. Fix JAX Batch Dimension Error

**Location**: `MultiStepReasoningNetwork.__call__` and related neural architectures
**Issue**: Batch dimensions mismatch in attention layers when processing embeddings
**Fix**:

- Ensure consistent batch dimensions throughout forward pass
- Add dimension validation and reshaping before attention operations
- Fix embedding extraction to maintain proper shape

### 2. Fix Response Formatting for LiveBench

**Location**: `execute()` method routing logic
**Issue**: Responses not properly formatted for LiveBench evaluation
**Fix**:

- Ensure all solver responses return proper format with `response`, `text`, `answer` fields
- Apply meta-evaluator correctly to repair responses
- Format web_of_lies responses as comma-separated yes/no answers

### 3. Module Integration

- New `advanced_reasoning_solvers` module should register with ModuleRegistry
- Update `custom_reasoning` module to delegate to `advanced_reasoning_solvers` when appropriate
- Maintain backward compatibility for existing operations

## Implementation Steps

### Step 1: Create New Module Structure

1. Create `mavaia_core/brain/modules/advanced_reasoning_solvers.py`
2. Define `AdvancedReasoningSolversModule(BaseBrainModule)`
3. Move all solver methods from `custom_reasoning_networks.py`
4. Register operations: `solve_zebra_puzzle`, `solve_spatial_problem`, `solve_arc_problem`, `solve_web_of_lies`

### Step 2: Fix JAX Batch Dimension Error

1. Locate all attention operations in neural architectures
2. Add batch dimension validation before MultiHeadAttention calls
3. Ensure embeddings are properly shaped: `(batch_size, seq_len, d_model)`
4. Fix `_get_embeddings()` to return consistent shapes
5. Add error handling for dimension mismatches

### Step 3: Update Original Module

1. Remove moved solver methods from `custom_reasoning_networks.py`
2. Update `execute()` to delegate solver operations to new module
3. Keep neural architecture operations in original module
4. Fix remaining neural network batch dimension issues

### Step 4: Fix Response Formatting

1. Ensure all solver responses include required fields
2. Fix web_of_lies formatting to match expected format
3. Apply meta-evaluator correctly in all paths
4. Test response extraction in LiveBench test runner

### Step 5: Testing

1. Run reasoning tests to verify 10/10 score
2. Verify module discovery works for both modules
3. Test backward compatibility
4. Validate all operations work correctly

## Files to Modify

1. **Create**: `mavaia_core/brain/modules/advanced_reasoning_solvers.py`
2. **Modify**: `mavaia_core/brain/modules/custom_reasoning_networks.py`

- Remove solver methods (~4000 lines)
- Fix JAX batch dimension errors
- Update execute() routing
- Add delegation to new module

## Key Code Locations

### JAX Error Fix Points:

- `MultiStepReasoningNetwork.__call__` (line ~102)
- `_get_embeddings()` method (needs to be located)
- All attention layer calls in neural architectures

### Solver Methods to Move:

- Lines ~1055-1184: Puzzle parsing and solving
- Lines ~1414-1698: Zebra puzzle solver
- Lines ~3494-5654: 2D grid and spatial solving
- Lines ~5757-6392: ARC problem solving
- Lines ~7310-7613: Web of lies and spatial problems

## Success Criteria

- ✅ New `advanced_reasoning_solvers` module created and functional
- ✅ Original `custom_reasoning_networks.py` reduced to manageable size (~4000 lines)
- ✅ All JAX batch dimension errors fixed
- ✅ LiveBench reasoning tests score 10/10
- ✅ Both modules properly registered and discoverable
- ✅ Backward compatibility maintained
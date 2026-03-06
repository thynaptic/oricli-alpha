# Specification: Brain Module Synchronization Audit

## Overview
Perform a comprehensive technical audit and synchronization of all Mavaia cognitive modules. The goal is to ensure that every module in the "brain" follows a unified interface, utilizes shared context correctly, and operates as a cohesive unit within the cognitive pipeline.

## Functional Requirements
1. **API Standardization**: Every module in `mavaia_core/brain/modules/` must strictly inherit from `BaseBrainModule` and implement the `execute` and `initialize` methods with consistent signatures.
2. **Return Type Parity**: Standardize all operation results to a consistent dictionary format:
   - Must include `success: bool`.
   - Must include `error: Optional[str]` on failure.
   - Metadata should be predictable based on the operation (e.g., `intent` for routing, `text` for generation).
3. **Data Flow Audit**: Ensure that `cognitive_state` and conversational history are passed correctly between reasoning (MCTS/Reflection), routing (AdapterRouter), and final generation.
4. **Metadata Updates**: Synchronize `ModuleMetadata` properties across all modules to accurately reflect their version, operations, and dependencies.
5. **Lazy Loading Enforcement**: Ensure all "heavy" ML imports (torch, transformers, etc.) are handled via `_lazy_import` patterns to maintain fast CLI/API startup times.

## Non-Functional Requirements
- **Performance**: No increase in conversational latency for standard requests.
- **Robustness**: Modules must handle missing dependencies or models gracefully without crashing the entire brain.

## Acceptance Criteria
- [ ] A new `scripts/module_health_diagnostics.py` successfully validates all modules in the registry.
- [ ] Integration tests verifying the full chain (MCTS Reasoning -> Intent Routing -> Quantized Generation) pass.
- [ ] Documentation (`MODULES.md` or similar) is updated to reflect the synchronized state.

## Out of Scope
- Training of new base models or elective adapters.
- Changes to the frontend/UI layer.
- Refactoring of non-brain services (e.g., S3 bridge, pod stabilization).

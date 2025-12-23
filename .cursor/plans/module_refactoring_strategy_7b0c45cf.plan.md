---
name: Module Refactoring Strategy
overview: Strategic plan to split large modules (7,440+ lines) into smaller, focused modules while maintaining functionality through proper linking. This will improve import performance, reduce memory footprint, and enhance maintainability.
todos:
  - id: phase1-advanced-solvers
    content: "Phase 1: Split advanced_reasoning_solvers.py into 6 focused modules (zebra, spatial, ARC, web_of_lies, grid_utilities, main coordinator)"
    status: completed
  - id: phase2-cognitive-generator
    content: "Phase 2: Split cognitive_generator.py into 9 specialized modules (orchestrator, intent_detector, router, thought_builder, enhancer, validator, trace_analyzer, context_enricher, main)"
    status: completed
    dependencies:
      - phase1-advanced-solvers
  - id: phase3-neural-text
    content: "Phase 3: Split neural_text_generator.py into 4 modules (trainer, generator, model_manager, policy_manager)"
    status: completed
    dependencies:
      - phase2-cognitive-generator
  - id: phase4-custom-reasoning
    content: "Phase 4: Split custom_reasoning_networks.py into 3 modules (jax_networks, arc_ensemble, main coordinator)"
    status: completed
    dependencies:
      - phase3-neural-text
  - id: backward-compatibility
    content: Ensure all original module operations maintain backward compatibility through routing/facade pattern
    status: completed
  - id: shared-utilities
    content: Extract shared utilities (grid_utilities, etc.) to avoid code duplication across modules
    status: completed
  - id: testing-validation
    content: "Comprehensive testing: unit tests for each new module, integration tests for backward compatibility, performance benchmarks"
    status: pending
    dependencies:
      - phase1-advanced-solvers
      - phase2-cognitive-generator
      - phase3-neural-text
      - phase4-custom-reasoning
  - id: documentation-update
    content: Update module documentation, MODULES.md, and any API docs to reflect new module structure
    status: pending
    dependencies:
      - testing-validation
---

# Module Refactoring Strategy: Splitting Large Modules for Performance

## Analysis Summary

### Largest Modules Identified

1. **advanced_reasoning_solvers.py** - 7,440 lines

- Contains 4 distinct solvers: zebra puzzles, spatial problems, ARC, web of lies
- 48+ helper methods for grid parsing, transformations, validation
- Heavy import overhead affecting registry discovery

2. **cognitive_generator.py** - 5,616 lines  

- Main orchestrator with multiple responsibilities
- Module loading/discovery, intent detection, response generation
- Routing/learning, trace graphs, multiple enhancement stages

3. **neural_text_generator.py** - 4,233 lines

- Model training (character/word level)
- Text generation, policy management
- Model loading/saving operations

4. **custom_reasoning_networks.py** - 3,313 lines

- JAX-based reasoning networks
- ARC ensemble solving
- Grid analysis utilities

5. **chain_of_thought.py** - 2,577 lines

- Decomposition, reasoning stages, synthesis
- Answer extraction and validation

6. **client.py** - 2,543 lines

- API client, module proxies, request/response handling

## Refactoring Strategy

### Phase 1: Split Advanced Reasoning Solvers (Priority: HIGH)

**Target:** `advanced_reasoning_solvers.py` (7,440 lines → ~1,500 lines each)**Split into:**

1. **zebra_puzzle_solver.py** (~1,800 lines)

- `_solve_zebra_puzzle()`
- `_solve_zebra_with_z3()`
- `_extract_zebra_answers_from_model()`
- `_generate_zebra_fallback_answers()`
- `_parse_puzzle_constraints()` (zebra-specific)

2. **spatial_reasoning_solver.py** (~1,500 lines)

- `_solve_spatial_problem()`
- `_create_spatial_relation_graph()`
- `_solve_2d_grid()`
- `_detect_rotation_reflection()`
- `_build_adjacency_matrix()`

3. **arc_solver.py** (~2,500 lines)

- `_solve_arc_problem()`
- `_detect_arc_transformations()`
- `_apply_arc_transformations()`
- `_extract_arc_patterns()`
- `_analyze_examples()`
- `_generalize_transformations()`
- All grid transformation methods

4. **web_of_lies_solver.py** (~800 lines)

- `_solve_web_of_lies()`
- Web of lies specific logic

5. **grid_utilities.py** (~1,200 lines) - Shared utilities

- `_parse_grid_from_text()`
- `_validate_grid()`
- `_apply_translation()`
- `_apply_duplication()`
- `_apply_continuation()`
- `_apply_color_mapping()`
- `_detect_shapes()`
- `_detect_adjacency()`

6. **advanced_reasoning_solvers.py** (refactored, ~500 lines)

- Main module that coordinates solvers
- Routes to appropriate solver module
- Maintains backward compatibility

**Linking Strategy:**

- Each solver module inherits from `BaseBrainModule`
- Main `advanced_reasoning_solvers` module uses `ModuleRegistry` to discover solver modules
- Shared utilities imported by all solvers
- Backward compatibility: original operations route to new modules

### Phase 2: Split Cognitive Generator (Priority: HIGH)

**Target:** `cognitive_generator.py` (5,616 lines → ~1,000 lines each)**Split into:**

1. **cognitive_orchestrator.py** (~800 lines) - Main coordinator

- `execute()` - Main entry point
- `generate_response()` - High-level orchestration
- Module discovery and loading coordination

2. **intent_detector.py** (~600 lines)

- `_detect_intent()`
- `_categorize_intent()`
- `_discover_modules_for_intent()`
- `_select_modules_for_intent()`

3. **module_router.py** (~800 lines)

- `_execute_module_chain()`
- `_learned_route()`
- `_update_routing_learning()`
- `get_routing_statistics()`
- `get_router_state()`

4. **thought_graph_builder.py** (~700 lines)

- `build_thought_graph()`
- `select_best_thoughts()`
- `_extract_thoughts_from_mcts()`
- `_extract_thoughts_from_tree()`

5. **response_enhancer.py** (~1,200 lines)

- `_apply_human_like_enhancements()`
- `_generate_personality_aware_fallback()`
- `_expand_response_for_detailed_mode()`
- `_enhance_for_consistency()`
- `_generate_conversational_response()`

6. **response_validator.py** (~600 lines)

- `_validate_response()`
- `_verify_web_content()`
- `_verify_output_matches_intent()`
- `_validate_response_quality()`
- `_validate_and_filter_instructions()`

7. **trace_analyzer.py** (~400 lines)

- `_build_trace_graph()`
- `get_trace_graphs()`
- `_calculate_structural_confidence()`
- `_reflect_and_reroute()`

8. **context_enricher.py** (~500 lines)

- `_enrich_context()`
- `_enrich_context_with_conversational_components()`
- `_extract_consistency_info()`

9. **cognitive_generator.py** (refactored, ~500 lines)

- Thin coordinator that delegates to specialized modules
- Maintains backward compatibility

**Linking Strategy:**

- All modules are independent `BaseBrainModule` instances
- `cognitive_orchestrator` coordinates via `ModuleRegistry`
- Lazy loading: modules only loaded when needed
- Backward compatibility: original operations route through orchestrator

### Phase 3: Split Neural Text Generator (Priority: MEDIUM)

**Target:** `neural_text_generator.py` (4,233 lines → ~1,200 lines each)**Split into:**

1. **neural_text_trainer.py** (~2,000 lines)

- `_train_model()`
- `_train_character_model()`
- `_train_word_model()`
- `_build_character_model()`
- `_build_word_model()`
- `_train_transformer_model()`
- Training utilities

2. **neural_text_generator.py** (refactored, ~1,200 lines)

- `_generate_text()`
- `_generate_character_text()`
- `_generate_word_text()`
- `_generate_continuation()`
- Generation logic

3. **neural_model_manager.py** (~800 lines)

- `_load_model()`
- `_save_model()`
- `_get_model_info()`
- Model lifecycle management

4. **adaptive_policy_manager.py** (~400 lines)

- `_load_adaptive_policies()`
- `_save_adaptive_policies()`
- `_get_adaptive_policy()`
- `_apply_adaptive_policy()`
- Policy management

**Linking Strategy:**

- Trainer and generator are separate modules
- Model manager shared between them
- Policy manager used by generator
- Backward compatibility maintained

### Phase 4: Split Custom Reasoning Networks (Priority: MEDIUM)

**Target:** `custom_reasoning_networks.py` (3,313 lines → ~1,000 lines each)**Split into:**

1. **jax_reasoning_networks.py** (~1,500 lines)

- JAX-based network implementations
- `_get_embeddings()`
- `_generate_text_from_embeddings()`
- Core JAX functionality

2. **arc_ensemble_solver.py** (~1,200 lines)

- `_solve_arc_ensemble()`
- ARC-specific analysis methods
- Grid analysis utilities

3. **custom_reasoning_networks.py** (refactored, ~600 lines)

- Main coordinator
- Routes to JAX networks or ARC solver
- Backward compatibility

**Linking Strategy:**

- JAX networks and ARC solver are separate modules
- Main module coordinates via registry
- Shared utilities extracted to common module

### Phase 5: Refactor Chain of Thought (Priority: LOW)

**Target:** `chain_of_thought.py` (2,577 lines)**Consider splitting into:**

1. **cot_decomposer.py** - Decomposition stage
2. **cot_reasoner.py** - Reasoning stage  
3. **cot_synthesizer.py** - Synthesis stage
4. **chain_of_thought.py** - Main coordinator

**Note:** This module is more cohesive than others. Consider keeping as-is unless performance issues persist.

### Phase 6: Refactor Client (Priority: LOW)

**Target:** `client.py` (2,543 lines)**Consider splitting into:**

1. **client_core.py** - Core client functionality
2. **module_proxy.py** - Module proxy system
3. **request_handler.py** - Request/response handling
4. **client.py** - Main client that imports others

**Note:** Client is less critical for module discovery performance.

## Implementation Guidelines

### 1. Backward Compatibility

- All original module names and operations must continue to work
- Use facade pattern: original module routes to new modules
- Maintain same `ModuleMetadata` operations list

### 2. Module Discovery

- Each new module must inherit from `BaseBrainModule`
- Register independently in `ModuleRegistry`
- Use lazy loading to avoid import overhead

### 3. Shared Utilities

- Extract common utilities to separate modules (e.g., `grid_utilities.py`)
- Import shared utilities in solver modules
- Avoid circular dependencies

### 4. Testing Strategy

- Test each new module independently
- Test backward compatibility with original operations
- Test module discovery and linking
- Performance benchmarks before/after

### 5. Migration Path

1. Create new modules alongside old ones
2. Update original module to route to new modules
3. Test thoroughly
4. Remove old code after validation
5. Update documentation

## Expected Benefits

1. **Import Performance**

- Smaller modules load faster
- Registry discovery time reduced
- Lower memory footprint per module

2. **Maintainability**

- Clearer separation of concerns
- Easier to understand and modify
- Better testability

3. **Scalability**

- Modules can be loaded on-demand
- Better resource management
- Easier to add new solvers/reasoners

4. **Code Quality**

- Reduced complexity per module
- Better adherence to single responsibility principle
- Improved code organization

## Risk Mitigation

1. **Functionality Loss**

- Comprehensive testing before/after
- Backward compatibility layer
- Gradual migration

2. **Import Errors**

- Careful dependency management
- Shared utilities properly exported
- Import path validation

3. **Performance Regression**

- Benchmark before/after
- Profile import times
- Monitor module discovery performance

## Success Metrics

- Module discovery time reduced by 50%+
- Average module size < 1,500 lines
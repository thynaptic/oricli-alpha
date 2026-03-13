# Oricli-Alpha Core Brain Modules

This directory contains all of Oricli-Alpha's brain modules - the intelligence components that power her capabilities.

## Module Count

- **200+ Python modules** - Comprehensive cognitive and specialized intelligence modules.
- **17 JSON config files** - Configuration for various modules.
- **1 subdirectory** - `symbolic_solvers/` containing specialized solvers.
- **3 data model files** - CoT, ToT, and MCTS data structures.

## Synchronization & Standardization (Audit 2026-03-06)

All core modules have been audited and synchronized to follow a strict, unified interface.

### Standard Interface Enforcement
Every module now strictly adheres to the `BaseBrainModule` API:
1. **Inheritance**: `from oricli_core.brain.base_module import BaseBrainModule`
2. **Metadata**: Implements a `metadata` property with versioning and operation discovery.
3. **Execution**: Implements `execute(operation, params)` with standardized return types (`success`, `error`, `metadata`).
4. **Health Check**: Implements a `status` operation for automated health diagnostics.

### Audited Core Modules
The following modules were refactored for 100% compliance during the synchronization audit:
- `cognitive_generator.py` - Main orchestrator (v1.0.1)
- `reasoning.py` - Symbolic reasoning (v1.0.1)
- `adapter_router.py` - LoRA hot-swapping (v1.1.1)
- `neural_text_generator.py` - Local generation engine (v1.0.1)
- `mcts_reasoning.py` - Monte-Carlo Thought Search (v1.0.1)
- `reasoning_reflection.py` - Self-correction loop (v1.0.1)
- `research_agent.py` - Multi-pass research (v1.0.1)
- `synthesis_agent.py` - Grounded synthesis (v1.0.1)
- `agent_coordinator.py` - Lifecycle management (v1.0.1)
- `multi_agent_orchestrator.py` - Pipeline execution (v1.0.1)
- `document_orchestration.py` - Hierarchical processing (v1.0.1)

## Module Categories

### Core Intelligence
- `cognitive_generator.py` - Main cognitive generation orchestrator ⭐ **AUDITED**
- `reasoning.py` - Advanced reasoning capabilities ⭐ **AUDITED**
- `embeddings.py` - Text embedding generation
- `thought_to_text.py` - Thought-to-text conversion

### Reasoning & Logic
- `chain_of_thought.py` - Chain-of-Thought reasoning orchestrator
- `tree_of_thought.py` - Tree-of-Thought multi-path exploration
- `mcts_reasoning.py` - Monte-Carlo Thought Search ⭐ **AUDITED**
- `reasoning_reflection.py` - Logic reflection and self-correction ⭐ **AUDITED**
- `logical_deduction.py` - Logical deduction
- `causal_inference.py` - Causal inference
- `analogical_reasoning.py` - Analogical reasoning
- `critical_thinking.py` - Critical thinking capabilities
- `symbolic_solver.py` - Symbolic problem solving

### Agents & Orchestration
- `agent_coordinator.py` - Agent lifecycle and result aggregation ⭐ **AUDITED**
- `multi_agent_orchestrator.py` - High-level pipeline execution ⭐ **AUDITED**
- `research_agent.py` - Multi-pass research investigation ⭐ **AUDITED**
- `synthesis_agent.py` - Grounded answer generation ⭐ **AUDITED**

### Language & Generation
- `neural_text_generator.py` - Local RNN/Transformer generation engine ⭐ **AUDITED**
- `adapter_router.py` - Dynamic LoRA adapter routing and hot-swapping ⭐ **AUDITED**
- `neural_grammar.py` - Neural grammar processing
- `natural_language_flow.py` - Natural language flow generation
- `response_naturalizer.py` - Response naturalization

### Memory & Context
- `conversational_memory.py` - Conversation memory management
- `memory_graph.py` - Memory graph operations
- `memory_processor.py` - Memory processing pipeline
- `memory_dynamics.py` - Dynamic memory management

### Processing & Safety
- `document_orchestration.py` - Multi-document hierarchical processing ⭐ **AUDITED**
- `code_analysis.py` - Code analysis capabilities
- `vision_analysis.py` - Vision/image analysis
- `web_scraper.py` - Web scraping capabilities
- `safety_framework.py` - Core safety and filtering

## Auto-Discovery

All modules are automatically discovered by the `ModuleRegistry` when Oricli-Alpha Core initializes. The registry now performs **automated interface validation** during discovery, raising `ModuleDiscoveryError` if a module fails to meet the standardization requirements.

## Module Structure

Each module must:
1. Inherit from `BaseBrainModule`
2. Implement `metadata` property returning `ModuleMetadata`
3. Implement `execute(operation, params)` method
4. MUST return a dictionary containing at least `{"success": bool, "error": Optional[str]}`

See [Module Development Guide](docs/module_development.md) for details.

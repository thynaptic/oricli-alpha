# Mavaia Core Brain Modules

This directory contains all of Mavaia's brain modules - the intelligence components that power her capabilities.

## Module Count

- **78 Python modules** - Core intelligence modules (9 new modules ported from Swift)
- **17 JSON config files** - Configuration for various modules
- **1 subdirectory** - `symbolic_solvers/` containing specialized solvers
- **3 data model files** - CoT, ToT, and MCTS data structures

## Recently Added (Swift Porting)

The following modules were ported from Swift services to enable cross-platform usage:

### Core Reasoning
- `complexity_detector.py` - Complexity analysis for reasoning method selection
- `chain_of_thought.py` - Chain-of-Thought reasoning orchestrator
- `tree_of_thought.py` - Tree-of-Thought multi-path exploration
- `mcts_reasoning.py` - Monte-Carlo Thought Search

### Analysis Services
- `symbolic_reasoning_detector.py` - Symbolic reasoning requirement detection
- `intent_categorizer.py` - Intent categorization for personality responses
- `semantic_threat_analysis.py` - Semantic threat detection
- `query_complexity.py` - Query complexity analysis

### Enhanced Modules
- `cogs_graph.py` - Enhanced with CRUD operations (12 new operations)
- `memory_graph.py` - Enhanced with DBSCAN clustering (5 new operations)

See [PORTING_COMPLETE.md](PORTING_COMPLETE.md) for full details.

## Module Categories

### Core Intelligence
- `cognitive_generator.py` - Main cognitive generation orchestrator
- `reasoning.py` - Advanced reasoning capabilities
- `embeddings.py` - Text embedding generation
- `thought_to_text.py` - Thought-to-text conversion

### Memory & Context
- `conversational_memory.py` - Conversation memory management
- `memory_graph.py` - Memory graph operations
- `memory_processor.py` - Memory processing pipeline
- `memory_dynamics.py` - Dynamic memory management

### Language & Communication
- `neural_grammar.py` - Neural grammar processing
- `natural_language_flow.py` - Natural language flow generation
- `response_naturalizer.py` - Response naturalization
- `language_variety.py` - Language variety management
- `linguistic_priors.py` - Linguistic prior knowledge
- `social_priors.py` - Social interaction priors

### Personality & Style
- `personality_response.py` - Personality-driven responses
- `style_transfer.py` - Style transfer capabilities
- `emotional_inference.py` - Emotional inference
- `emotional_ontology.py` - Emotional ontology management

### Analysis & Processing
- `code_analysis.py` - Code analysis capabilities
- `document_orchestration.py` - Document processing
- `vision_analysis.py` - Vision/image analysis
- `web_scraper.py` - Web scraping capabilities

### Reasoning & Logic
- `logical_deduction.py` - Logical deduction
- `causal_inference.py` - Causal inference
- `analogical_reasoning.py` - Analogical reasoning
- `critical_thinking.py` - Critical thinking capabilities
- `symbolic_solver.py` - Symbolic problem solving
- `chain_of_thought.py` - Chain-of-Thought reasoning orchestrator ⭐ **NEW**
- `tree_of_thought.py` - Tree-of-Thought multi-path exploration ⭐ **NEW**
- `mcts_reasoning.py` - Monte-Carlo Thought Search ⭐ **NEW**
- `complexity_detector.py` - Complexity analysis for reasoning method selection ⭐ **NEW**
- `symbolic_reasoning_detector.py` - Symbolic reasoning requirement detection ⭐ **NEW**
- `query_complexity.py` - Query complexity analysis ⭐ **NEW**

### Optimization & Learning
- `model_optimizer.py` - Model optimization
- `neural_architecture_search.py` - Neural architecture search
- `reinforcement_learning_agent.py` - Reinforcement learning
- `gradient_plan_optimizer.py` - Gradient-based optimization

### Specialized Modules
- `lora_loader.py` - LoRA model loading
- `lora_inference.py` - LoRA inference
- `world_knowledge.py` - World knowledge management
- `tool_routing_model.py` - Tool routing
- `intent_categorizer.py` - Intent categorization for personality responses ⭐ **NEW**
- `semantic_threat_analysis.py` - Semantic threat detection ⭐ **NEW**

## Auto-Discovery

All modules are automatically discovered by the `ModuleRegistry` when Mavaia Core initializes. No manual registration is required - simply add a new module file that inherits from `BaseBrainModule` and it will be available.

## Module Structure

Each module must:
1. Inherit from `BaseBrainModule`
2. Implement `metadata` property returning `ModuleMetadata`
3. Implement `execute(operation, params)` method
4. Optionally implement `validate_params()`, `initialize()`, and `cleanup()`

See [Module Development Guide](docs/module_development.md) for details.


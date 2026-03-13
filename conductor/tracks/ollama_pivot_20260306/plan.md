# Implementation Plan: Pivot to Ollama

## Objective
Offload text generation and light reasoning to local Ollama models.

## Phase 1: Ollama Bridge
- [ ] Create `oricli_core/brain/modules/ollama_provider.py`.
- [ ] Connect to local Ollama API.

## Phase 2: Engine Integration
- [ ] Update `text_generation_engine.py` to use Ollama first.

## Phase 3: Cognitive Integration
- [ ] Update `cognitive_generator.py` for light reasoning.

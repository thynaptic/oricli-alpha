# Implementation Plan: Text Generation Strategy Reform

## Phase 1: TextGenerationEngine Refactor

### 1.1 Robust Ollama Logic
- [ ] Add `max_ollama_retries` configuration to `text_generation_engine`.
- [ ] Update `_generate_with_neural` to implement a retry loop for `ollama_provider`.

### 1.2 Selective Fallback Logic
- [ ] Implement a `use_local_fallback` parameter (default: `False`).
- [ ] Only call `neural_text_generator` if `use_local_fallback` is `True` and Ollama fails.
- [ ] Ensure `neural_text_generator` failures (ImportErrors, etc.) are caught and logged as warnings, not errors.

## Phase 2: Configuration & Diagnostics

### 2.1 Environmental Awareness
- [ ] Detect presence of TensorFlow/PyTorch on startup.
- [ ] Log a high-level architectural warning if `neural_text_generator` is unavailable but don't fail the engine.

### 2.2 User-Friendly Feedback
- [ ] Improve error messages when both Ollama and local generation are unavailable (e.g. "Sovereign Intelligence is currently offline - Check Ollama connection").

## Phase 3: Validation

### 3.1 Scenario Testing
- [ ] Verify Ollama priority works normally.
- [ ] Verify that disabling Ollama (simulated) correctly skips the local fallback unless forced.
- [ ] Ensure system stability in the absence of `tensorflow`/`torch`.

# Specification: Text Generation Strategy Reform (Ollama-First)

## Objective
To strictly enforce the "Ollama-First" text generation strategy across Oricli-Alpha, ensuring that local RNN/LSTM/Transformer models are only used as explicit, secondary fallbacks to avoid unnecessary system bloat and noisy failures in resource-constrained environments.

## Background
Oricli-Alpha is pivoting to use Ollama for all prose and light reasoning. The current `text_generation_engine` attempts to fall back to an internal `neural_text_generator` whenever Ollama fails. This often results in noisy crashes or initialization errors (like missing TensorFlow/PyTorch) that confuse the system's state.

## Requirements

### 1. Robust Ollama Prioritization
- `text_generation_engine` must prioritize `ollama_provider`.
- Implement a configurable retry mechanism for Ollama requests before considering any fallback.

### 2. Selective Fallback
- The internal `neural_text_generator` should ONLY be attempted if:
    - `ollama_provider` is definitively unavailable or exhausted retries.
    - AND a `use_local_fallback` flag is set (defaults to `False` in constrained environments).
- If the internal generator is missing dependencies (TensorFlow/PyTorch), it must fail gracefully without triggering a system-wide error state.

### 3. Clear Attribution
- All generated responses must clearly state the `method` used (`ollama`, `neural_fallback`, `static_template`).

## Success Criteria
- System remains functional even if `neural_text_generator` fails to initialize.
- Noisy `ModuleNotFoundError` or `ImportError` from ML stacks do not propagate to the top-level API response.
- Ollama timeouts are handled with internal retries before failing.

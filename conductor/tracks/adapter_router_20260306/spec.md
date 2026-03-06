# Specification: Multi-Adapter Router

**Overview**
The Multi-Adapter Router is a standalone cognitive module designed to dynamically select and load specialized LoRA adapters for a base model. It uses an independent embedding service to classify input intent, allowing for rapid routing decisions without requiring the primary LLM to be warm.

**Functional Requirements**
1.  **Standalone Module Architecture**: Implementation of a new `AdapterRouter` module in `mavaia_core/brain/modules`.
2.  **Independent Semantic Routing**:
    *   Integrates with Mavaia's existing embedding service (e.g., `all-MiniLM-L6-v2`) to retrieve input vectors.
    *   Uses a trainable classification head to map these embeddings to registered LoRA adapter IDs.
3.  **Hybrid Remote Storage**:
    *   **Hugging Face Hub**: Pull adapters using `peft` and `huggingface_hub`.
    *   **S3 Integration**: Fetch private adapters from S3-compatible buckets.
4.  **Trainable Routing Logic**: Supervised/RL training support for the classification head.
5.  **Experience Replay**: Store routing events (input -> embedding -> adapter -> score) in Mavaia's memory layer for offline optimization.

**Non-Functional Requirements**
*   **Latency Target**: Routing decision and adapter swapping should add <100ms overhead to the initial generation request.
*   **Memory Safety**: Implement strict VRAM tracking to prevent OOM when switching between multiple large adapters.
*   **Local-First Resilience**: All fetched adapters must be cached locally to ensure continued operation in air-gapped environments after initial sync.

**Acceptance Criteria**
*   Router identifies and loads a specific adapter based on semantic input.
*   Successful fetching and application of adapters from both Hugging Face and S3.
*   Router weights update correctly during training.
*   Routing events are logged to the Experience Replay buffer.

**Out of Scope**
*   Simultaneous multi-adapter blending (MoE gating) - focusing on 1-to-1 selection for Phase 1.
*   Automatic adapter *generation/training* - this module only handles the *routing and application* of existing adapters.

# Implementation Plan: Multi-Adapter Router

**Phase 1: Module Foundation & Registry Integration**
Goal: Establish the standalone module structure and ensure it is discoverable by the Mavaia Core registry.
- [x] Task: Scaffold Module Structure
    - [ ] Create `mavaia_core/brain/modules/adapter_router.py`.
    - [ ] Implement `AdapterRouter` class inheriting from `BaseModule`.
    - [ ] Define core operations: `route_input`, `load_adapter`, `status`.
- [x] Task: TDD - Module Discovery
    - [ ] Write unit test to verify registration in `ModuleRegistry`.
    - [ ] Verify basic operation dispatch via `MavaiaClient`.
- [x] Task: Conductor - User Manual Verification 'Phase 1: Foundation' (Protocol in workflow.md)

**Phase 2: Independent Semantic Routing**
Goal: Implement the embedding-based classification logic using Mavaia's embedding service.
- [x] Task: Integrate Embedding Client
    - [ ] Logic to call `mavaia-embeddings` (standalone service) to get input vectors.
    - [ ] Implement a trainable linear classification head (PyTorch) for mapping embeddings to intents.
- [x] Task: Implement Routing Table
    - [ ] Logic to map intent classifications to specific adapter names/IDs.
    - [ ] Support for fallback routing to the "Base" model.
- [x] Task: TDD - Routing Accuracy
    - [ ] Create unit tests with diverse input strings.
    - [ ] Verify correct intent classification and adapter ID assignment.
- [x] Task: Conductor - User Manual Verification 'Phase 2: Semantic Routing' (Protocol in workflow.md)

**Phase 3: Hybrid Storage & Dynamic PEFT Loading**
Goal: Implement the fetching and application of adapters from Hugging Face and S3.
- [x] Task: Implement HF Hub Integration
    - [ ] Add logic to fetch and cache adapters using `peft` and `huggingface_hub`.
- [x] Task: Implement S3 Integration
    - [ ] Integrate with Mavaia's S3 bridge to retrieve private adapters.
- [x] Task: Dynamic Adapter Swapping
    - [ ] Implement VRAM-aware logic to attach/detach adapters from a base model on-the-fly.
- [x] Task: TDD - Loading & VRAM Safety
    - [x] Verify successful loading of a remote adapter.
    - [x] Verify VRAM is released when switching adapters.
- [x] Task: Conductor - User Manual Verification 'Phase 3: Storage & Loading' (Protocol in workflow.md)

**Phase 4: Training & Experience Replay**
Goal: Enable the router to learn from interactions and store experiences for refinement.
- [x] Task: Implement Training Loop
    - [x] Logic to update router weights using supervised feedback or reinforcement signals.
- [x] Task: Experience Replay Integration
    - [x] Logic to log routing decisions to the memory/data layer.
    - [x] Logic to replay historical routing events for offline optimization.
- [x] Task: TDD - Memory Persistence
    - [x] Verify retrieval of experiences from the replay buffer.
- [x] Task: Conductor - User Manual Verification 'Phase 4: Training & Memory' (Protocol in workflow.md)

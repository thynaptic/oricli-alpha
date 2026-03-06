# Implementation Plan: Multi-Adapter Router

**Phase 1: Module Foundation & Registry Integration**
Goal: Establish the standalone module structure and ensure it is discoverable by the Mavaia Core registry.
- [ ] Task: Scaffold Module Structure
    - [ ] Create `mavaia_core/brain/modules/adapter_router.py`.
    - [ ] Implement `AdapterRouter` class inheriting from `BaseModule`.
    - [ ] Define core operations: `route_input`, `load_adapter`, `status`.
- [ ] Task: TDD - Module Discovery
    - [ ] Write unit test to verify registration in `ModuleRegistry`.
    - [ ] Verify basic operation dispatch via `MavaiaClient`.
- [ ] Task: Conductor - User Manual Verification 'Phase 1: Foundation' (Protocol in workflow.md)

**Phase 2: Independent Semantic Routing**
Goal: Implement the embedding-based classification logic using Mavaia's embedding service.
- [ ] Task: Integrate Embedding Client
    - [ ] Logic to call `mavaia-embeddings` (standalone service) to get input vectors.
    - [ ] Implement a trainable linear classification head (PyTorch) for mapping embeddings to intents.
- [ ] Task: Implement Routing Table
    - [ ] Logic to map intent classifications to specific adapter names/IDs.
    - [ ] Support for fallback routing to the "Base" model.
- [ ] Task: TDD - Routing Accuracy
    - [ ] Create unit tests with diverse input strings.
    - [ ] Verify correct intent classification and adapter ID assignment.
- [ ] Task: Conductor - User Manual Verification 'Phase 2: Semantic Routing' (Protocol in workflow.md)

**Phase 3: Hybrid Storage & Dynamic PEFT Loading**
Goal: Implement the fetching and application of adapters from Hugging Face and S3.
- [ ] Task: Implement HF Hub Integration
    - [ ] Add logic to fetch and cache adapters using `peft` and `huggingface_hub`.
- [ ] Task: Implement S3 Integration
    - [ ] Integrate with Mavaia's S3 bridge to retrieve private adapters.
- [ ] Task: Dynamic Adapter Swapping
    - [ ] Implement VRAM-aware logic to attach/detach adapters from a base model on-the-fly.
- [ ] Task: TDD - Loading & VRAM Safety
    - [ ] Verify successful loading of a remote adapter.
    - [ ] Verify VRAM is released when switching adapters.
- [ ] Task: Conductor - User Manual Verification 'Phase 3: Storage & Loading' (Protocol in workflow.md)

**Phase 4: Training & Experience Replay**
Goal: Enable the router to learn from interactions and store experiences for refinement.
- [ ] Task: Implement Training Loop
    - [ ] Logic to update router weights using supervised feedback or reinforcement signals.
- [ ] Task: Experience Replay Integration
    - [ ] Logic to log routing decisions to the memory/data layer.
    - [ ] Logic to replay historical routing events for offline optimization.
- [ ] Task: TDD - Memory Persistence
    - [ ] Verify retrieval of experiences from the replay buffer.
- [ ] Task: Conductor - User Manual Verification 'Phase 4: Training & Memory' (Protocol in workflow.md)

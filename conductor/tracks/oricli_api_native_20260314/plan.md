# Implementation Plan: Oricli Native API

## Phase 1: Core Service Exposure (The Sovereign Layer)

### 1.1 Goal Management API
- [ ] Implement `v1/goals` endpoints in `oricli_core/api/server.py`.
- [ ] Connect them to `oricli_core.services.goal_service.GoalService`.
- [ ] Add `client.goals` namespace to `oricli_core/client.py`.

### 1.2 Swarm Blackboard API
- [ ] Implement `v1/swarm` endpoints in `oricli_core/api/server.py`.
- [ ] Connect them to `oricli_core.services.swarm_blackboard_service.get_swarm_blackboard_service()`.
- [ ] Add `client.swarm` namespace to `oricli_core/client.py`.

### 1.3 Knowledge Graph API
- [ ] Implement `v1/knowledge` endpoints in `oricli_core/api/server.py`.
- [ ] Connect them to the `knowledge_graph_builder` brain module.
- [ ] Add `client.knowledge` namespace to `oricli_core/client.py`.

## Phase 2: Ollama Parity (The Direct Interface)

### 2.1 Direct Inference Routes
- [ ] Add `POST /api/generate` that takes a prompt and returns a cognitive response (equivalent to `v1/chat/completions` but simpler).
- [ ] Add `POST /api/chat` as an alias for `v1/chat/completions`.
- [ ] Add `GET /api/tags` as an alias for `v1/models`.

### 2.2 System & Model Info
- [ ] Add `POST /api/show` to provide details about a module or the system ID.

## Phase 3: Integration & Validation

### 3.1 Documentation & Examples
- [ ] Update `docs/api_documentation.md` with the new Oricli-native routes.
- [ ] Create a sample script `scripts/test_native_api.py` demonstrating the new capabilities.

### 3.2 Testing
- [ ] Add unit tests for the new API endpoints.
- [ ] Perform integration tests with the updated `OricliAlphaClient`.

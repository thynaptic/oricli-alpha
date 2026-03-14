# Specification: Oricli Native API (Sovereign Interface)

## Objective
To provide a dedicated, first-class API for Oricli-Alpha that mirrors the simplicity of the Ollama API while exposing the unique sovereign capabilities of the Oricli-Alpha OS (Goals, Swarms, Knowledge Graph, etc.).

## Background
Currently, Oricli-Alpha exposes an OpenAI-compatible API and some module-specific endpoints under `/v1/`. While functional, it doesn't feel like a standalone "Agent OS" interface. A native API will allow external applications to interact with Oricli's proactive and collaborative features directly.

## Requirements

### 1. Ollama-Style Endpoints
- `POST /api/generate`: Map to `cognitive_generator` (Oricli's internal reasoning).
- `POST /api/chat`: Map to `chat.completions` (OpenAI-compatible core).
- `GET /api/tags`: Map to `v1/models`.
- `POST /api/show`: Show detailed model/module info.

### 2. Sovereign Goal Endpoints
- `POST /v1/goals`: Create a new sovereign goal.
- `GET /v1/goals`: List all active/historical goals.
- `GET /v1/goals/{goal_id}`: Get status and progress of a specific goal.
- `POST /v1/goals/{goal_id}/resume`: Resume a paused goal.

### 3. Hive Swarm Endpoints
- `POST /v1/swarm/run`: Trigger a collaborative swarm session for a query.
- `GET /v1/swarm/sessions`: List swarm sessions.
- `GET /v1/swarm/sessions/{session_id}`: Get the blackboard state and logs of a swarm session.

### 4. Knowledge Graph Endpoints
- `POST /v1/knowledge/extract`: Extract entities and relationships from text.
- `GET /v1/knowledge/query`: Query the knowledge graph.
- `GET /v1/knowledge/rdf`: Export the graph as RDF.

### 5. Client Integration
- Extend `OricliAlphaClient` with `client.goals`, `client.swarm`, and `client.knowledge` namespaces.

## Success Criteria
- External tools can submit long-horizon goals via API.
- Swarm sessions can be monitored in real-time via the API.
- Knowledge graph can be queried programmatically.
- API maintains 100% backward compatibility with existing `/v1/` endpoints.

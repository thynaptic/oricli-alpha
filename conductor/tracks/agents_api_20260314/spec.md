# Specification: External Agents API (Sovereign Agent Factory)

## Objective
To complete the "Sovereign Assembly" triarchy (Rules, Skills, Agents) by exposing Oricli-Alpha's `AgentProfile` system via the Native REST API. This allows external applications (HUDs) to dynamically craft, update, and deploy specialized agents that combine specific mindsets (Skills), guardrails (Rules), and tool access (Modules).

## Background
Currently, agent profiles are managed by the `AgentProfileService` and primarily loaded from a static `agent_profiles.json` file. To enable a "Factory" experience in the HUD, we need to allow creating new profiles that can be instantly used by the Hive Swarm.

## Requirements

### 1. AgentProfileService CRUD
Update `oricli_core/services/agent_profile_service.py` to support:
- `list_profiles`: Return all profiles (Built-in + Custom).
- `create_profile`: Define a new agent policy (modules, skills, rules, models) and persist it.
- `update_profile`: Modify an existing custom profile.
- `delete_profile`: Remove a custom profile.
- Persistence: Custom profiles should be saved to `oricli_core/data/custom_profiles.json` or individual `.ori` profile files to survive restarts.

### 2. REST API Endpoints (`/v1/agents`)
Add new routes to `oricli_core/api/server.py`:
- `GET /v1/agents`: List all available agents.
- `GET /v1/agents/{agent_name}`: Retrieve details of a specific agent profile.
- `POST /v1/agents`: Create a new agent profile.
- `PUT /v1/agents/{agent_name}`: Update an agent profile.
- `DELETE /v1/agents/{agent_name}`: Delete an agent profile.

### 3. Pydantic Models
Add models to `oricli_core/types/models.py`:
- `AgentCreateRequest`
- `AgentUpdateRequest`
- `AgentResponse`
- `AgentListResponse`

### 4. Client Integration
Extend `OricliAlphaClient` with a `client.agents` namespace.

### 5. Swarm Integration
Ensure that when a `ChatCompletionRequest` is sent with a custom `model` name (matching a custom agent name), the Hive Swarm identifies the custom profile and enforces its constraints during bidding and execution.

## Success Criteria
- HUD can "build" a new agent by selecting skills and rules via API.
- The new agent appears in `/api/tags` and `/v1/agents`.
- Sending a query to the new agent uses its assigned mindset and follows its assigned rules.

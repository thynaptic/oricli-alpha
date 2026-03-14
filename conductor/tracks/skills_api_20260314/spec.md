# Specification: External Skills API

## Objective
To expose Oricli-Alpha's internal `.ori` skills framework via the Native REST API. This will allow external applications to dynamically create, read, update, delete (CRUD), and list skills, effectively extending her cognitive capabilities and roles from outside the core codebase.

## Background
Currently, skills are stored as declarative `.ori` files in `oricli_core/skills/`. The `skill_manager` module parses these files into memory (`skills_cache`). While internal modules (like Swarm Nodes) can access them, there is no way for an external system to inject new mindsets or view available skills without writing to the disk directly and manually triggering a reload.

## Requirements

### 1. Skill Manager Refactor
Update `oricli_core/brain/modules/skill_manager.py` to support full CRUD operations:
- `list_skills`: Return all loaded skills.
- `create_skill`: Accept skill metadata (name, description, triggers, mindset, instructions), generate a valid `.ori` format, write it to disk, and reload.
- `update_skill`: Modify an existing `.ori` file and reload.
- `delete_skill`: Remove an `.ori` file and reload.

### 2. REST API Endpoints (`/v1/skills`)
Add new routes to `oricli_core/api/server.py`:
- `GET /v1/skills`: List all available skills.
- `GET /v1/skills/{skill_name}`: Retrieve details of a specific skill.
- `POST /v1/skills`: Create a new skill.
- `PUT /v1/skills/{skill_name}`: Update an existing skill.
- `DELETE /v1/skills/{skill_name}`: Delete a skill.

### 3. Pydantic Models
Add request and response models to `oricli_core/types/models.py`:
- `SkillCreateRequest`
- `SkillUpdateRequest`
- `SkillResponse`
- `SkillListResponse`

### 4. Client Integration
Extend `OricliAlphaClient` with a `client.skills` namespace for programmatic access (both local and remote mode).

### 5. Documentation
Add a new documentation file `docs/SKILLS_API.md` (or update `EXTERNAL_AGENT_INTEGRATION.md`) explaining how external agents can inject new skills into Oricli.

## Success Criteria
- External scripts can perform full CRUD on skills over HTTP.
- Created skills are persisted as `.ori` files in the `skills` directory.
- `skill_manager` immediately recognizes and can match against newly created skills without a full server restart.

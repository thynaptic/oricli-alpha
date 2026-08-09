# Tasks DAG in ori-capsule

Deepened local SQLite tasks (still under `ORI_MEMORY_DIR`) with optional step
dependencies. No SearXNG / GenService executor — client or tools drive status.

## Model

- Task: `title`, `description`, `status`, `priority`, `done` (compat)
- Step: `id`, `title`, `order_num`, `depends_on[]`, `status`, `result`

Statuses: `pending` | `running` | `done` | `failed` | `cancelled`

## API

| Method | Path | Notes |
|---|---|---|
| GET | `/v1/tasks` | `?status=` filter |
| POST | `/v1/tasks` | `{title, description?, priority?, steps?}` |
| GET | `/v1/tasks/:id` | includes steps |
| PATCH | `/v1/tasks/:id` | `{done}` or `{status}` |
| POST | `/v1/tasks/:id/steps` | add step |
| PATCH | `/v1/tasks/:id/steps/:sid` | `{status, result}` — rolls up task when all done |
| GET | `/v1/tasks/:id/ready` | steps whose deps are all `done` |

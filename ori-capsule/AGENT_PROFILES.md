# Agent profiles in ori-capsule

Mount-only port of `.github/agents/*.agent.md` (same format as monorepo Oracle).

## Env

| Var | Default | Role |
|---|---|---|
| `ORI_AGENTS_DIR` | auto: `.github/agents` or `../.github/agents` | Colon-separated read-only dirs |

```bash
-v "$PWD/.github/agents:/agents:ro" -e ORI_AGENTS_DIR=/agents
```

## Chat

- `X-Ori-Agent: ori-reasoner` — explicit profile
- Else, if mounted: default `ori-chat-fast` when present
- Injected as system block before skills/reform/safety extras

## API

`GET /v1/agents` — list name/description/tools metadata

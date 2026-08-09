# Skills overlays in ori-capsule

Mount-only port of monorepo `.ori` skill loading (`pkg/oracle/skills.go` pattern).
No LLM skill selection — first trigger match wins, injected into chat system extras.

## Env

| Var | Default | Role |
|---|---|---|
| `ORI_SKILLS_DIR` | auto: `oricli_core/skills` or `../oricli_core/skills` if present | Colon-separated read-only dirs |

Docker: mount the skill library read-only, e.g.

```bash
-v "$PWD/oricli_core/skills:/skills:ro" -e ORI_SKILLS_DIR=/skills
```

## API / chat

- `GET /v1/skills` — list name/description/triggers + stats
- Chat: if last user message matches a trigger, skill body is prepended to system extras

## Out of scope

Agent profile `.agent.md` mounting, Oracle session pooling, multi-skill merge.

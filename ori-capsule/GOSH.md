# GOSH in ori-capsule (docker-friendly)

Port of monorepo `pkg/gosh` for the consumer capsule. Pure Go — no CGO, no
subprocesses, no VPS daemon sharing.

## Modes

| Mode | When | Behavior |
|---|---|---|
| **mem** | `ORI_GOSH_WORKSPACE` empty, or `ORI_GOSH_FORCE_MEM=true`, or workspace missing | Fully in-memory FS |
| **overlay** | Workspace dir exists | Read-only jail on that path + CoW memory for writes |

Docker default: mount a project at `/workspace` **read-only** and set
`ORI_GOSH_WORKSPACE=/workspace`. Host files are never modified.

## API

Auth same as other protected routes (Bearer / capsule key).

### `GET /v1/gosh`

Capability probe (`enabled`, `mode`, `workspace`, builtins, timeout, action stats).

### `GET /v1/gosh/lessons`

Returns the lessons-learned prompt block for a session. Pass `X-Session-ID`
(or `?session_id=`). Empty `lessons` when nothing recorded yet.

### `POST /v1/gosh/run`

Per-request sandbox (filesystem/tools are not shared across callers). Action /
mismatch history is process-local and keyed by session:

```json
{
  "script": "cat /in.txt > /out.txt\necho done",
  "files": { "/in.txt": "hello" },
  "tools": [{ "name": "hello", "source": "package main\n..." }],
  "source": "package main\nfunc main() { ... }",
  "read": ["/out.txt"],
  "expected_result": "done",
  "session_id": "optional-if-header-set"
}
```

- `session_id` body field, or `X-Session-ID` header (header used when body empty).
- `expected_result` optional — if stdout does not contain it, a mismatch +
  correction plan is recorded even when exit is OK.
- Response includes `action` (this run) and `lessons` (session prompt block).

Allowlisted builtins: `cat`, `ls`, `mkdir`, `rm`, `pwd`, `echo` (+ registered tools).
Anything else → `restricted: …`.

Timeout: `ORI_GOSH_TIMEOUT_SEC` (default 5s).

## ActionTracker (from `pkg/state`)

Pure-heuristic tool/action mismatch ring buffer — **no LLM**, no VPS intent /
evolution / quota machinery.

When chat carries the same `X-Session-ID`, recent GOSH lessons are injected into
the system prompt so the model can avoid repeating sandbox mistakes.

## Env

| Var | Default | Role |
|---|---|---|
| `ORI_GOSH_ENABLED` | `true` | Master switch |
| `ORI_GOSH_WORKSPACE` | empty | Overlay root inside container |
| `ORI_GOSH_FORCE_MEM` | `false` | Ignore workspace |
| `ORI_GOSH_TIMEOUT_SEC` | `5` | Per-run deadline |

## Out of scope (VPS)

Dream / Metacog / Reform daemon loops, Hive shared module, real `go build`/`go vet`
subprocess, hardcoded host paths.

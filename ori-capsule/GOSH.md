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

Capability probe (`enabled`, `mode`, `workspace`, builtins, timeout).

### `POST /v1/gosh/run`

Per-request sandbox (no shared session state across callers):

```json
{
  "script": "cat /in.txt > /out.txt\necho done",
  "files": { "/in.txt": "hello" },
  "tools": [{ "name": "hello", "source": "package main\n..." }],
  "source": "package main\nfunc main() { ... }",
  "read": ["/out.txt"]
}
```

Allowlisted builtins: `cat`, `ls`, `mkdir`, `rm`, `pwd`, `echo` (+ registered tools).
Anything else → `restricted: …`.

Timeout: `ORI_GOSH_TIMEOUT_SEC` (default 5s).

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

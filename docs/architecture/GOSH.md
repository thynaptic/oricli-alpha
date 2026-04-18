# Gosh — Sovereign Go-Native Shell Sandbox

**Version:** v1.0.0  
**Package:** `pkg/gosh` (core) · `pkg/service/gosh_module.go` (Hive wrapper)  
**Maintainer:** Thynaptic Research

---

## Overview

Gosh is Oricli-Alpha's isolated, Go-native shell execution environment. It gives daemons and agents the ability to run bash scripts, inspect and write files, and dynamically extend the shell with custom Go tools — all without spawning a subprocess or touching the host shell.

**Key guarantees:**
- **No subprocess escape** — all execution is in-process via `mvdan.cc/sh/v3`
- **Filesystem jailed** — overlay FS prevents writes from reaching the host
- **Allowlist-only commands** — unlisted binaries are rejected, not exec'd
- **Hot-loadable Go tools** — agents can compile and register new commands at runtime

---

## Architecture

```
pkg/gosh/session.go
├── Session
│   ├── fs           afero.Fs           (in-memory or overlay)
│   ├── env          []string           (PATH, HOME, PWD)
│   ├── dir          string             (CWD, tracked across commands)
│   ├── stdout/stderr bytes.Buffer
│   └── dynamicTools map[string]DynamicHandler
│
├── NewSession()                        → clean in-memory FS
├── NewOverlaySession(baseDir)          → CoW overlay on project root (read-only host side)
│
├── Execute(ctx, script) (string, error)     → parse + run bash via mvdan.cc/sh/v3
├── RegisterTool(name, sourceCode) error     → compile + hot-load Go tool via yaegi
├── WriteFile(path, data) error              → seed sandbox from Go code
└── ReadFile(path) ([]byte, error)           → extract results from sandbox

pkg/service/gosh_module.go
└── GoshModule                          → ModuleInstance wrapper for the Hive
    ├── Execute("execute", {script})
    ├── Execute("write",   {path, content})
    └── Execute("read",    {path})
```

---

## Session Types

### `NewSession()` — Pure In-Memory

Creates a completely isolated session backed by `afero.NewMemMapFs()`. No host filesystem access. Used when the daemon needs a clean scratch pad with no project state.

```go
s := gosh.NewSession()
out, err := s.Execute(ctx, `echo "hello sovereign"`)
```

### `NewOverlaySession(baseDir)` — Jail + Copy-on-Write

Creates a session that can **read** the project root but **all writes stay in memory** — the host FS is never modified.

```
afero.NewCopyOnWriteFs(
    afero.NewReadOnlyFs(afero.NewBasePathFs(afero.NewOsFs(), absBase)),  ← read-only host
    afero.NewMemMapFs(),                                                  ← writable memory layer
)
```

- Absolute paths are **jailed** to `baseDir` — `cat /etc/passwd` returns the in-memory `/etc/passwd` (empty), not the host file
- Directory traversal above `baseDir` is blocked by `BasePathFs`
- Used by all production daemons (MetacogDaemon, DreamDaemon, ReformDaemon)

```go
s, err := gosh.NewOverlaySession("/home/mike/Mavaia")
s.WriteFile("/workspace/patch.go", []byte(proposedCode))
out, err := s.Execute(ctx, `cat /workspace/patch.go | grep "func "`)
```

---

## Shell Execution

Gosh uses **`mvdan.cc/sh/v3`** — a pure-Go POSIX shell interpreter. Scripts are parsed and run entirely in-process.

### Built-in Commands (Allowlist)

| Command | Behaviour |
|---|---|
| `cat <file>` | Read file from session FS |
| `ls [path]` | List directory contents |
| `mkdir <path>` | Create directory (MkdirAll) |
| `rm <path>` | Remove file or directory recursively |
| `pwd` | Print current working directory |
| `echo [args...]` | Print arguments |
| `<dynamic>` | Any registered Go tool |

Any command not in this list returns:
```
restricted: <command> is not permitted in this agent sandbox
```

### Path Resolution

All paths are resolved against the interpreter's **live CWD** (tracked across commands). After each `Execute()` call, `s.dir` is updated to the shell's final working directory, so multi-call workflows maintain correct relative paths.

---

## Dynamic Tool Registration

Agents can hot-load new Go functions as shell commands at runtime using **`traefik/yaegi`** — a pure-Go interpreter.

```go
toolSource := `
package main
import "fmt"

func Summarize(args []string) (string, string, error) {
    return fmt.Sprintf("Summary of %d items", len(args)), "", nil
}
`
err := s.RegisterTool("summarize", toolSource)
// now "summarize item1 item2 item3" is a valid shell command in this session
out, _ := s.Execute(ctx, "summarize a b c")
// → "Summary of 3 items"
```

**Handler signature (required):**
```go
func <Name>(args []string) (stdout string, stderr string, err error)
```

Dynamic tools take precedence over built-in commands if names collide. Tools persist for the lifetime of the `Session` instance.

---

## File I/O Helpers

Direct Go-to-sandbox file operations, bypassing the shell interpreter:

```go
// Seed a file (from the Go backbone)
s.WriteFile("/workspace/reform.go", []byte(proposedCode))

// Extract a result (from the Go backbone)
data, err := s.ReadFile("/workspace/output.txt")
```

These are the primary mechanism for ReformDaemon to stage patched files before running `go vet` and `go build` inside the sandbox.

---

## Gosh Module (Hive Integration)

`pkg/service/gosh_module.go` wraps a `gosh.Session` as a `ModuleInstance` so it participates in the Hive module registry.

### Instantiation

```go
// backbone/main.go
goshMod, _ := service.NewGoshModule("hive_sandbox", "/home/mike/Mavaia")
// → NewOverlaySession under the hood
```

The single `GoshModule` instance is **shared** by MetacogDaemon, DreamDaemon, and ReformDaemon. Because the underlying session is in-memory CoW, concurrent accesses don't corrupt the host FS, but callers should be aware state is shared (writes by one daemon are visible to another).

### Operations

#### `execute`
Run a bash script in the session.

```go
result, err := goshMod.Execute(ctx, "execute", map[string]interface{}{
    "script": `ls /workspace && cat /workspace/result.txt`,
})
// result is ExecutionResult{Success, Stdout, ExitCode, ExecutionTime}
```

| Field | Type | Description |
|---|---|---|
| `Success` | bool | `true` if exit code 0 |
| `Stdout` | string | Combined stdout from script |
| `ExitCode` | int | 0 on success, 1 on error |
| `ExecutionTime` | float64 | Wall-clock seconds |

#### `write`
Seed a file into the sandbox.

```go
result, err := goshMod.Execute(ctx, "write", map[string]interface{}{
    "path":    "/workspace/probe.sh",
    "content": `#!/bin/bash\necho "probe complete"`,
})
// result is bool (true on success)
```

#### `read`
Extract a file from the sandbox.

```go
result, err := goshMod.Execute(ctx, "read", map[string]interface{}{
    "path": "/workspace/output.txt",
})
// result is string (file contents)
```

### Module Metadata

```go
goshMod.Metadata()
// ModuleMetadata{
//     Name:        "hive_sandbox",
//     Version:     "1.0.0",
//     Description: "Sovereign Go-native Bash Sandbox with Overlay FS",
//     Author:      "Oricli-Alpha Core",
//     IsGoNative:  true,
//     Operations:  []string{"execute", "write", "read"},
// }
```

---

## Usage by Daemons

| Daemon | How Gosh is used |
|---|---|
| **ReformDaemon** | `WriteFile` stages the patched file → `execute` runs `go vet` + `go build` in isolation before any host file is touched |
| **MetacogDaemon** | Runs introspection scripts to probe trace stats and build reform proposals |
| **DreamDaemon** | Executes consolidation scripts during idle cycles, writes synthesized insights to memory |

---

## Security Model

| Guarantee | Mechanism |
|---|---|
| No subprocess execution | `mvdan.cc/sh/v3` — pure-Go interpreter, no `exec.Command` |
| Host FS write-protected | `afero.NewReadOnlyFs` on the base layer |
| Path traversal blocked | `afero.NewBasePathFs` jails all absolute paths to `baseDir` |
| Command allowlist | `execHandler` explicitly handles ~6 builtins; all others error |
| Dynamic tool scope | Tools loaded by `yaegi` run in an isolated interpreter instance per `RegisterTool` call |

**What Gosh cannot do by design:**
- Exec arbitrary host binaries (`curl`, `wget`, `python`, etc.)
- Write to the host filesystem
- Access files outside `baseDir` (overlay sessions)
- Persist state across `NewSession()` / `NewOverlaySession()` calls

---

## Dependencies

| Library | Role |
|---|---|
| `github.com/spf13/afero` | Virtual filesystem abstraction (MemMapFs, BasePathFs, CopyOnWriteFs) |
| `mvdan.cc/sh/v3` | Pure-Go POSIX shell interpreter |
| `github.com/traefik/yaegi` | Pure-Go Go source interpreter (for `RegisterTool`) |

All three are pure-Go — no CGO, no system libraries, no external process requirements.

---

*Source: `pkg/gosh/session.go`, `pkg/service/gosh_module.go`*  
*Oricli-Alpha — Sovereign Intelligence, Orchestrated at Scale.*

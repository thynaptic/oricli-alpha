# Forge in ori-capsule

## Static gate

Port of monorepo `pkg/forge` constitution — no `go fmt` / `go vet` / `go build`.

| Gate | When | Rules |
|---|---|---|
| Script constitution | Every `POST /v1/gosh/run` with `script` | Fatal security patterns |
| Tool constitution | `strict_tool: true` | + stdin/JSON/line-limit contract |
| Go source scan | `source` / `tools[].source` | Stubs + Yaegi escape hatches |

### `POST /v1/gosh/verify` / `POST /v1/gosh/run`

Run always verifies first unless `skip_verify: true` (tests).

## Light JIT (docker-friendly)

In-memory ephemeral tools — **no PocketBase**, no VPS paths, no subprocess build.
Prefer **Yaegi** (`kind: yaegi`); scripts use GOSH allowlisted builtins only.

| Env | Default | Role |
|---|---|---|
| `ORI_FORGE_MAX_TOOLS` | `16` | LRU cap |
| `ORI_FORGE_TTL_MIN` | `30` | Expiry minutes |

| Method | Path | Notes |
|---|---|---|
| GET | `/v1/forge/tools` | List live JIT tools |
| POST | `/v1/forge/propose` | One BYOK chat → JSON tool → VerifyStatic → optional register |
| POST | `/v1/forge/register` | Client-supplied source (verify + store) |
| POST | `/v1/forge/tools/:name/invoke` | Run via GOSH |
| DELETE | `/v1/forge/tools/:name` | Drop |

Propose body:

```json
{
  "task": "uppercase a string",
  "model": "gpt-4.1-mini",
  "kind": "yaegi",
  "register": true
}
```

Registered JIT tools appear in `GET /v1/tools` and are callable under `X-Ori-Tools: auto`.

## Still out

POCGate LLM scoring, PB library, host admin forge stats, bash/`python3` host tools.

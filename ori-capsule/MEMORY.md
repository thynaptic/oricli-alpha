# Capsule memory (consumer)

Local-first memory for ori-capsule. **No PocketBase, Neo4j, enterprise RAG, or sync embeds** on the chat path.

## What’s in

| Piece | Backend | Chat latency |
|---|---|---|
| Warm bridge (LMDB stand-in) | encrypted **bbolt** (pure Go / `CGO_ENABLED=0`) | Put/Get μs–ms |
| Session turns | bridge `sessions` bucket via `X-Session-ID` | load before LLM; **append async** after reply |
| Belief / fog-of-war | in-process | CPU only |
| Session clock | in-process + async JSON under `.memory/session_chronos/` | CPU + async disk |
| Chronos observe | in-process ring (no daemon) | async after reply |
| Working graph | in-process keyword graph (**no Neo4j**) | CPU only |
| State / affect | `sync.Map` + async bridge write | non-blocking |
| Response cache | **L1 exact hash only** (no chromem) | hit skips upstream |
| Session touch pool | in-process TTL | free |
| Spaces | local `spaces.json` | API only |
| Tasks | pure-Go SQLite | API only |

## Intentionally out

- Enterprise memory / RAG twins
- chromem + Ollama embeds (sync lag)
- PocketBase MemoryBank / SCL / TCD
- Neo4j promote / temporal graph
- PAD / Goals
- Swarm reputation

## Env

| Var | Default | Role |
|---|---|---|
| `ORI_MEMORY_DIR` | `.memory` | Data root (mount a volume in Docker) |
| `ORI_MEMORY_ENCRYPTION_KEY` | derived from dir (dev) | base64 32-byte AES key |
| `ORI_MEMORY_MAX_TURNS` | `24` | Cap persisted turns per session |

## Chat wiring

1. Safety gates  
2. `PrepareChat`: optional L1 cache hit; merge thin client history with stored turns; belief/clock/graph extras into system prompt  
3. Upstream BYOK  
4. Output sanitize  
5. `AfterReply` (goroutine): session append, episodic put, chronos observe, L1 cache put  

Pass `X-Session-ID` for durable multi-turn memory.

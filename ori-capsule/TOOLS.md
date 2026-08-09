# Tools + BYOK tool_calls in ori-capsule

Allowlisted capsule tools (execute via memory / RAG / GOSH) plus full support for
**model-native** OpenAI/Anthropic tool calling on BYOK chat.

## Modes

| Mode | Header | Behavior |
|---|---|---|
| **Passthrough** (default) | absent or `X-Ori-Tools: passthrough` | Forward client `tools` / `tool_choice` to the upstream model. If the model returns `tool_calls`, return them OpenAI-shaped (`finish_reason: tool_calls`). Client executes and sends `role:"tool"` results. |
| **Auto** | `X-Ori-Tools: auto` | Inject allowlisted schemas (if none provided), execute allowlisted calls server-side, re-call the model (max 4 rounds). Non-stream. Unknown tool names return a JSON error payload — never host shell. |

Custom client tools work in **passthrough** even if they are not in the allowlist (the client runs them). Auto mode only executes allowlisted names.

## Allowlisted builtins

| Tool | Action |
|---|---|
| `tasks_list` / `tasks_add` / `tasks_done` | Local SQLite tasks |
| `spaces_list` | Local spaces |
| `rag_query` | BM25 query |
| `skills_list` | Mounted `.ori` metadata |
| `gosh_verify` | Forge static check |
| `gosh_run` | Forge-verified GOSH sandbox run |

`GET /v1/tools` lists schemas.

## BYOK contract

OpenAI / OpenCode: standard `tools`, `tool_choice`, `tool_calls`, `role:"tool"`.

Anthropic: converted to Messages API `tools` / `tool_use` / `tool_result` blocks; responses remapped to OpenAI shape.

## Safety

- `gosh_run` always goes through forge constitution (no `skip_verify`)
- No host `os/exec` — GOSH allowlisted builtins only
- Auto mode cannot invent tools outside the registry
- Tool-call turns skip L1 reply cache write; final text is still sanitized

## Example (passthrough)

```http
POST /v1/chat/completions
Authorization: Bearer sk-...
Content-Type: application/json

{
  "model": "gpt-4.1-mini",
  "messages": [{"role":"user","content":"List my tasks via tools"}],
  "tools": [{
    "type": "function",
    "function": {
      "name": "tasks_list",
      "description": "List tasks",
      "parameters": {"type":"object","properties":{}}
    }
  }]
}
```

## Example (auto)

```http
POST /v1/chat/completions
Authorization: Bearer sk-...
X-Ori-Tools: auto
Content-Type: application/json

{
  "model": "gpt-4.1-mini",
  "messages": [{"role":"user","content":"Add a task titled 'buy milk' then list tasks"}]
}
```

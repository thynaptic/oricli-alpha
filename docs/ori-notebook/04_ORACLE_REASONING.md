# Oracle: The Reasoning Lane — Full Journey

**Status:** Live · Direct Anthropic API · v11.12.0+  
**Last Updated:** 2026-05-03

---

## The Short Version

Oracle is ORI's primary reasoning lane. Every LLM call for user-facing chat, heavy reasoning, research, vision, and background cognition routes through it. Local Ollama is retained only for embeddings.

Oracle calls the Anthropic API directly over HTTP/SSE — no daemon, no port binding, no third-party SDK. The route, the system prompt, the session context, and the constitutional stack are all ORI's responsibility. The raw intelligence call is Anthropic's.

---

## Part 1: Where We Started — Ollama All the Way Down

When Oricli-Alpha was first built, every LLM call ran through Ollama. This was a deliberate sovereign choice: own the compute, own the model, own the runtime. Local inference meant no API keys, no external dependencies, no data leaving the box.

It worked. The sovereign architecture — Go backbone, 269+ cognitive modules, daemon ecosystem, memory graph — was built entirely on top of local Ollama models.

But as the system grew, a tension emerged. ORI's cognitive pipeline (Aurora 11-step, 28 pre-generation phases, therapeutic regulation stack, self-audit loop) was doing real work. The question was no longer whether ORI could reason — it was *how well*. And the honest answer was: local 7B-13B models were the bottleneck. Going bigger meant GPU cost. Going external meant rethinking the sovereignty claim.

The resolution came through a cleaner understanding of what sovereignty actually means.

---

## Part 2: The Copilot SDK Era — First External Reasoning

The first external reasoning integration used the GitHub Copilot SDK, backed by GitHub Models (Anthropic models via GitHub's API layer).

It worked reasonably well but came with structural problems:

- **Embedded daemon** — the SDK ran a daemon process on port 8090. It had to be alive for Oracle to function. If it crashed, Oracle crashed.
- **Session state in `~/.copilot/`** — session management was partially delegated to the SDK's local state directory. ORI didn't fully own the session lifecycle.
- **OAuth complexity** — authentication went through GitHub's OAuth flow, not a direct API key. This added latency and a potential point of failure.
- **No direct API control** — we couldn't set specific parameters (thinking budget, cache behavior, batch operations) without going around the SDK.

The Copilot SDK era proved that external reasoning *worked* within ORI's architecture. Sovereignty wasn't violated — the constitutional stack, routing, and memory management were all still ORI's. But the SDK layer added friction that didn't belong there.

---

## Part 3: Direct Anthropic API — v11.12.0 (2026-04-28)

The full migration to Direct Anthropic API removed every layer that wasn't ORI or Anthropic.

**What changed:**
- No daemon. Oracle sends `HTTP POST` directly to `https://api.anthropic.com/v1/messages`.
- No SDK. Raw HTTP with `bufio.Scanner` SSE parsing — line by line.
- No external session state. Session management is `sessionPool sync.Map` in `pkg/oracle/oracle.go`.
- No OAuth. `ANTHROPIC_API_KEY` environment variable. That's it.

**What we unlocked:**

### Prompt Caching
System prompts are sent as `cache_control: ephemeral` content blocks. On repeated turns in the same session, the system prompt cache is hot — roughly 10x cost reduction on every turn after the first. For sessions with long system prompts (agent personas, skill overlays), this is significant.

### Extended Thinking
Heavy and research routes get extended thinking budgets: 8,000 tokens on `RouteHeavyReasoning`, 10,000 on `RouteResearch`. Thinking blocks are consumed silently — only text reaches the caller. The reasoning is done but not exposed. Disable with `ORACLE_THINKING_HEAVY=0` / `ORACLE_THINKING_RESEARCH=0`.

### Native Tool Use
`oracle.ChatWithTools()` handles one non-streaming round-trip for tool-calling flows. Returns text or `[]ToolCall`. `server_v2.go` converts to OpenAI-format `tool_calls`. Tool results come back as `role:"tool"` messages via `reqMsgsToOracle()`, which preserves `tool_call_id` through the Anthropic `tool_result` content block conversion. Note: extended thinking and tool use are mutually exclusive — `ChatWithTools()` does not enable thinking.

### Batch API
`pkg/oracle/batch.go` — `SubmitBatch()`, `GetBatch()`, `FetchResults()`, `PollUntilDone()`. Designed for high-volume async jobs (Studio Jobs, bulk analysis). Not yet wired to production surfaces, but the layer is ready.

### `.ori` Skills Overlay
`pkg/oracle/skills.go` loads `.ori` skill files from `oricli_core/skills/` and `.github/skills/`. Trigger phrases are matched against the incoming query; on match, the skill's content is injected as an additional system prompt block. Skills can sharpen ORI's behavior for specific task types without modifying the base agent persona.

### Vision
All image reasoning routes through `AnalyzeImage()` — base64 image content blocks to `https://api.anthropic.com/v1/messages`. `POST /v1/vision/analyze` is the public endpoint. Model defaults to `claude-sonnet-4-6`, overrideable with `ORACLE_VISION_MODEL`.

---

## Part 4: The AGLI Doctrine Alignment

The Oracle migration settled a philosophical question that had been open since the Copilot era: **does using Anthropic's API violate Perimeter Sovereignty?**

The answer AGLI gives is no — and here's why.

Sovereignty means owning the *cognitive architecture*: the memory graph, the daemon ecosystem, the constitutional stack, the routing logic, the governing principles. These all live inside the Thynaptic boundary. They don't depend on Anthropic. Anthropic's API is the *intelligence tier* — raw neural compute. Data flows through it; it does not reside there. ORI applies her constitutional stack before and after every Oracle call. No external system controls her daemons, her memory, or her governing principles.

The alternative — scaling up local GPU compute to match frontier model quality — is expensive, operationally complex, and distracts from the real differentiator: ORI's cognitive architecture, not her weights.

**Perimeter Sovereignty remains intact. The architecture is sovereign. The intelligence call is external and governed.**

---

## Part 5: Current Routing

```
pkg/oracle/router.go → Decide()

RouteLightChat       → claude-haiku-4-5-20251001   (no thinking)
RouteHeavyReasoning  → claude-sonnet-4-6            (8K thinking budget)
RouteResearch        → claude-sonnet-4-6            (10K thinking budget)
RouteImageReasoning  → vision via AnalyzeImage()    → claude-sonnet-4-6
```

Session pool keyed by `tenantID:sessionID`. TTL: 30 min idle. Stateless sessions (empty `sessionID`) are never pooled.

---

## Part 6: Current Configuration

| Variable | Default | Purpose |
|---|---|---|
| `ANTHROPIC_API_KEY` | — | Required. Direct API auth. |
| `ORACLE_COPILOT_MODEL_LIGHT` | `claude-haiku-4-5-20251001` | Light chat / cognitive tier |
| `ORACLE_COPILOT_MODEL_HEAVY` | `claude-sonnet-4-6` | Heavy reasoning |
| `ORACLE_COPILOT_MODEL_RESEARCH` | `claude-sonnet-4-6` | Research / deep investigation |
| `ORACLE_COPILOT_MODEL` | — | Global override (all routes) |
| `ORACLE_VISION_MODEL` | `claude-sonnet-4-6` | Vision override |
| `ORACLE_THINKING_HEAVY` | 8000 | Thinking budget, heavy route (0 = disable) |
| `ORACLE_THINKING_RESEARCH` | 10000 | Thinking budget, research route (0 = disable) |

Agent personas: `.github/agents/*.agent.md` — loaded and cached (5 min TTL) via `cachedLoadCustomAgents()`.  
Skills: `oricli_core/skills/*.ori` and `.github/skills/*.ori` — trigger-matched per request.

# Safety — intentionally not in ori-capsule

Structural gates from `pkg/safety` live in `internal/safety` and are wired on
every chat turn (including stream). The following are **dropped**, not deferred:

| Item | Reason |
|---|---|
| Swarm Jury / peer SCAI | VPS multi-node only — removed from capsule |
| Telegram / alert webhooks | No longer used — canary alerts are structured logs only |
| LLM Critique / Revise loop | Extra BYOK round-trip; ConstraintContract + structural output gates are the capsule path |

Host-path leak detectors (`/home/mike/Mavaia`, etc.) remain as harmless disclosure patterns.

## Wire points

- Gin rate limit middleware on protected routes
- Pre-chat: `Pipeline.CheckInputWithHistory`
- System prompt: `Pipeline.ConstraintPrompt` (constitution + SCAI contract + canary)
- Post-chat (non-stream): `Pipeline.SanitizeOutput`
- Post-chat (stream): `byok.CollectStream` → `SanitizeOutput` → `byok.WriteChatSSE`  
  Upstream SSE is fully buffered so output gates see the complete assistant text (parity with non-stream). Client still receives OpenAI-shaped SSE chunks after sanitize.

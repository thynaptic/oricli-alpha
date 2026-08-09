# Safety — VPS-only leftovers (discuss later)

Moved into `ori-capsule/internal/safety` from `pkg/safety`. Everything structural
runs in-process with no host daemons. Items below are **side-parked** — API
surface may still exist, but capsule does **not** wire them.

| Item | Why VPS / side | Capsule stance |
|---|---|---|
| **Swarm Jury** (`JuryVerifier`, `CritiqueWithJury` peer path) | Needs multi-node SPP / `pkg/swarm` peers on the VPS network | Interface kept for parity; `Jury` always `nil` in capsule |
| **LLM Critique/Revise via process `OPENAI_API_KEY`** (`pkg/llm`) | Monorepo helper assumed host env Oracle key | Replaced with `safety.ChatClient` interface — wire via BYOK later if we want post-hoc critique; primary path is ConstraintContract injection (no extra round-trip) |
| **Webhook alerts to Telegram/ops** (`ORICLI_ALERT_WEBHOOK`) | Often pointed at VPS-local alert bots | Optional; also accepts `ORI_CAPSULE_ALERT_WEBHOOK`. Off by default |
| Host-path leak patterns (`/home/mike/Mavaia`, `oricli-neo4j`, …) | Detection strings for old VPS layout | **Kept** — they still catch accidental infra disclosure; harmless in Docker |

## Not VPS-only (moved)

Sentinel, Adversarial, Disclosure (DID), WebInjection, Canary/honeypot, MultiTurn,
Suspicion, CanvasGuard, RagContentGuard, Refinement, RateLimiter, SupportEngine,
Constitution, SCAI ConstraintContract + ClassifyAuditLevel, Pipeline orchestrator.

## Wire points in capsule

- Gin rate limit middleware on protected routes
- Pre-chat: `Pipeline.CheckInputWithHistory`
- System prompt: `Pipeline.ConstraintPrompt` (constitution + SCAI contract + canary)
- Post-chat (non-stream): `Pipeline.SanitizeOutput`
- Stream: input gates + constraint prompt; output sanitization deferred (SSE) — discuss if we should buffer-then-sanitize for Full audit

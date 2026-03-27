# Oricli-Alpha — Security Architecture

> **Sovereign. Local. Adversarial-proof.**  
> This document describes the full multi-layer safety pipeline protecting every inference request.

---

## Overview

Every user message passes through **8 input gates** before Ollama is ever called, and **5 output gates** before any response is returned. All gates run in the Go process — zero network round-trips, zero latency tax from cloud safety APIs.

```
USER MESSAGE
     │
     ▼
[1] Encoding Normalizer       ← strip unicode confusables, zero-width, base64, ROT13, leet
     │
     ▼
[2] Multi-Turn Analyzer       ← detect cross-message escalation sequences (history-aware)
     │
     ▼
[3] Sentinel                  ← injection, persona hijacking, DAN, dangerous topics, reflection/completion
     │
     ▼
[4] Adversarial Auditor       ← DAN variants, routing hijack, dual-use, ThreatInjection patterns
     │
     ▼
[5] Disclosure Guard (input)  ← system prompt extraction, recon, chain-of-thought poisoning, gaslighting
     │
     ▼
[6] Web Injection Guard       ← XSS, SQLi, SSTI, SSI, SSRF, XXE, weaponisation intent requests
     │
     ▼
[7] Canary Scanner (input)    ← system prompt leak detection via boot-time canary token
     │
     ▼
[8] Suspicion Check           ← hard-block sessions with accumulated high-risk score
     │
     ▼
   OLLAMA INFERENCE
     │
     ▼
[O1] Adversarial Auditor (output)   ← API key patterns, internal path leaks
[O2] Disclosure Guard (output)      ← PEM keys, JWT, env vars, private IPs, PII  (tiered redaction)
[O3] Web Injection Guard (output)   ← SSI/XSS/SSTI in prose (code blocks preserved)
[O4] Canary Scanner (output)        ← honeypot credential detection, canary echo
[O5] Canvas Guard (output)          ← HTML/JSX: strip <script>, event handlers, external resources
     │
     ▼
RESPONSE TO USER
```

---

## Gate Details

### Input Gates

#### [1] Encoding Normalizer — `pkg/safety/normalizer.go`

Runs as a **pre-processing step** before all other gates. Ensures downstream pattern matchers see the real intent regardless of obfuscation technique.

| Technique | Defense |
|---|---|
| Unicode confusables (Cyrillic а, Greek ο) | Confusable map → ASCII |
| Zero-width chars (U+200B, U+FEFF, U+200D…) | Stripped entirely |
| HTML entities (`&#105;`, `&lt;`) | `html.UnescapeString` |
| Base64 encoded payloads | Detect + decode, substitute decoded text |
| ROT13 / Caesar | Threat-density heuristic — use rotated form if higher score |
| Leetspeak (`1gn0r3`) | Leet map applied to leet-dense words (≥30% substitution) |

#### [2] Multi-Turn Analyzer — `pkg/safety/multiturn.go`

Analyzes the full `[]Message` conversation history for **escalation sequences** that no single message would trigger. Patterns detected:

- **Persona escalation**: roleplay/creative framing in earlier turns → boundary push in latest turn
- **Creative framing escalation**: fiction/hypothetical setup → procedural harmful ask
- **Incremental compliance coercion**: ≥2 false-compliance claims ("you already told me…")
- **Topic drift**: benign opening, sharply dangerous recent messages (grooming pattern)

#### [3] Sentinel — `pkg/safety/sentinel.go`

Classic injection shield covering:
- Override / ignore / bypass instructions (40+ variants)
- Developer/jailbreak/god mode triggers
- DAN and named jailbreak personas
- Persona and role hijacking
- Compliance coercion
- System prompt injection markers (`<|system|>`, `[INST]`, `<<SYS>>`)
- **Reflection / completion attacks**: "repeat after me", "finish this sentence", "say exactly", "echo back"

#### [4] Adversarial Auditor — `pkg/safety/adversarial.go`

Confidence-scored threat detection:
- DAN / unrestricted-AI variants (`ThreatInjection` pattern set)
- Routing hijack attempts
- Dual-use capability requests

#### [5] Disclosure Guard (input) — `pkg/safety/disclosure.go`

Sophisticated extraction attempt detection:
- Deep extraction: system prompt fishing, training data extraction, session cross-contamination
- Reconnaissance: API key/port/env/config/IP fishing
- Chain-of-thought poisoning: fiction/roleplay framing tricks
- **Gaslighting patterns**: "as you said before", "you previously stated", "you agreed that", "earlier you mentioned"

#### [6] Web Injection Guard — `pkg/safety/web_injection.go`

Intent and payload detection:
- Weaponisation intent (XSS/SQLi/SSTI payload generation requests)
- SSRF via LLM (AWS/GCP/Azure IMDS, localhost endpoints)
- Direct SSTI markers in prompt
- Direct SSI directives (`<!--#include-->`, `<!--#exec-->`)
- Active XSS payloads (`<script>`, `onerror=`)
- XXE entities

#### [7] Canary Scanner — `pkg/safety/canary.go`

Boot-time unique token system:
- **Canary token** (`ORICLI_CANARY_<uuid>`) embedded invisibly in every system prompt
- If canary appears in **user input** → system prompt was extracted in a prior session → hard-block + alert
- **Honeypot credential** (`ORICLI_TEST_KEY=hpx_<random>`) planted in context
- If honeypot value appears in **model output** → safety pipeline was bypassed → kill response + alert

Alerts are written to structured logs and optionally POSTed to `ORICLI_ALERT_WEBHOOK` (Telegram-compatible JSON).

#### [8] Suspicion Tracker — `pkg/safety/suspicion.go`

Session-level risk accumulation with time decay:

| Event | Points |
|---|---|
| Blocked critical gate | +10 |
| Blocked high gate | +5 |
| Blocked moderate gate | +2 |
| Borderline detection | +1 |
| Every 10 minutes | ×0.5 decay |

| Score | Action |
|---|---|
| >20 | WARN — logged, SCAI escalation flagged |
| >50 | HARD_BLOCK — HTTP 429, 30-minute cooldown |

### Output Gates

#### [O1] Adversarial Auditor (output)
API key patterns, internal path leaks — full block on detection.

#### [O2] Disclosure Guard (output)
Tiered redaction:
- **CRITICAL** (PEM keys, JWT, system prompt echo) → full block
- **HIGH** (API keys, env dumps, internal paths, private IPs) → `[REDACTED:TYPE]` substitution
- **MODERATE** (PII: emails, phones not in user context) → redact

#### [O3] Web Injection Guard (output)
Code-block aware — `splitProseAndCode()` preserves fenced code blocks verbatim, only scans prose. Prevents false positives on developer security queries.

#### [O4] Canary Scanner (output)
Checks both canary token and honeypot value in model output.

#### [O5] Canvas Guard — `pkg/safety/canvas_guard.go`
Activated by `X-Canvas-Mode: true` header or `max_tokens >= 8192`. Stricter than standard output scanning because canvas output may be rendered directly as HTML/JSX:

- Strip `<script>` blocks entirely
- Remove event handler attributes (`onclick`, `onload`, `onerror`, etc.)
- Block external resource URLs not on CDN allowlist
- Block dangerous HTML (`<meta http-equiv=refresh>`, `<base href>`)
- Block dangerous JS patterns (`document.cookie`, `localStorage`, `eval()`, `fetch(external)`, `WebSocket`, prototype pollution) — does NOT skip code blocks in canvas mode

---

## Rate Limiting & Probe Detection — `pkg/safety/ratelimit.go`

Applied as Gin middleware to all protected routes.

| Condition | Limit |
|---|---|
| Normal session | 60 req/min |
| After first safety block | 10 req/min |
| 3+ distinct safety categories within 5 min | Hard-block for 30 min |

IP extraction prefers `X-Real-IP` → `X-Forwarded-For` → `ClientIP()` (Caddy reverse proxy aware).

---

## Indirect Injection Guard (RAG/Scrape) — `pkg/safety/rag_guard.go`

External content (SearXNG results, Colly scrapes, `/ingest/web` payloads) is scanned **before entering context**:

| Pattern | Defense |
|---|---|
| HTML comment injections (`<!-- IGNORE... -->`) | Stripped |
| Invisible CSS text (color:white, display:none, font-size:0) | Style attribute stripped |
| Meta-tag instruction injections | Removed |
| LLM format tokens (`[INST]`, `<<SYS>>`, `<\|system\|>`) | Stripped |
| Whitespace padding (100+ spaces) | Collapsed |
| Plain-text instruction markers ("ignore previous instructions") | Line redacted |

---

## Environment Variables

| Variable | Purpose |
|---|---|
| `ORICLI_ALERT_WEBHOOK` | Webhook URL for security alerts (Telegram-compatible JSON POST) |
| `SOVEREIGN_ADMIN_KEY` | Admin-tier session key (full access, 1-hour TTL) |
| `SOVEREIGN_EXEC_KEY` | Exec-tier session key (execution access, 1-hour TTL) |
| `ORICLI_ALERT_WEBHOOK` | Webhook URL for canary/security alerts (Telegram-compatible JSON POST) — already listed above |

> **Note:** The legacy `MAVAIA_REQUIRE_AUTH` / `MAVAIA_API_KEY` env var names are **not used**. Auth is handled by the SovereignAuth system (`pkg/sovereign/auth.go`) — see §SovereignAuth below.

### SovereignAuth

The sovereign auth layer (`pkg/sovereign/auth.go`) implements a two-tier session system independent of standard Bearer tokens:

| Tier | Key Env Var | Permissions |
|---|---|---|
| **Admin** | `SOVEREIGN_ADMIN_KEY` | Full API access including introspection and shutdown |
| **Exec** | `SOVEREIGN_EXEC_KEY` | Execution-tier access (chat, tools, agents) |

**Session lifecycle:**
- Sessions are created via `/admin <key>` or `/exec <key>` commands
- TTL: **1 hour** per session
- Lockout: **3 failed attempts** triggers a **5-minute cooldown** on that IP
- Key comparison uses `subtle.ConstantTimeCompare` to prevent timing attacks

---

## Adding New Safety Patterns

All pattern lists are initialized in `loadPatterns()` / constructor functions. To add new patterns:

1. **New injection phrase** → add to `sentinel.go` `InjectionPatterns`
2. **New extraction pattern** → add to `disclosure.go` `extractionDeepPatterns`
3. **New gaslighting phrase** → add to `disclosure.go` `chainPatterns`
4. **New web payload pattern** → add to `web_injection.go` `weaponisationPatterns` or output regexes
5. **New multi-turn sequence** → add detection function to `multiturn.go` and call from `AnalyzeHistory()`

Rebuild backbone after any change: `go build ./cmd/backbone/ && sudo systemctl restart oricli-backbone`

---

## Testing

The safety framework has a dedicated test suite: **129 tests** across 12 modules.

### Run all tests

```bash
./scripts/test_safety.sh
```

Outputs a colored pass/fail summary per module and writes a report to `docs/SAFETY_TEST_REPORT.md`.

### Run individual module tests

```bash
go test ./pkg/safety/... -run TestSentinel -v
go test ./pkg/safety/... -run TestNormalizer -v
go test ./pkg/safety/... -run TestPipeline -v
```

### Test modules

| Module | Coverage |
|---|---|
| `Normalizer` | Unicode, zero-width, HTML entities, base64, ROT13, leet |
| `Sentinel` | Injection phrases, DAN, persona hijack, developer mode, reflection |
| `Disclosure` | Deep extraction, recon, gaslighting, output credential scrubbing |
| `WebInjection` | Weaponisation intent, SSRF, SSI, XSS, XXE, output scanning |
| `MultiTurn` | Escalation sequences, creative framing, compliance coercion |
| `Suspicion` | Score accumulation, hard-block, session isolation |
| `RagGuard` | HTML comment injection, invisible CSS, LLM tokens |
| `RateLimiter` | Token bucket, probe trip-wire, Gin middleware |
| `Canary` | System prompt leak, honeypot bypass, token rotation |
| `CanvasGuard` | Script stripping, event handlers, dangerous JS, CSP |
| `ExtractIP` | IP extraction from X-Real-IP, X-Forwarded-For headers |
| `Pipeline` | Full end-to-end integration across all 8 layers |

See [SAFETY_TEST_REPORT.md](SAFETY_TEST_REPORT.md) for the latest run results.

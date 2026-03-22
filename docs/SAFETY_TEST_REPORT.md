# Oricli-Alpha — Safety Framework Test Report

> Generated: 2026-03-22 00:49:13 UTC  
> Command: `go test ./pkg/safety/... -v -count=1`

## Summary

| Metric | Value |
|---|---|
| Total tests | 129 |
| Passed | 129 |
| Failed | 0 |
| Pass rate | 100% |

## Results by Module

| Module | Passed | Failed | Total | Status |
|---|---|---|---|---|
| `Canary` | 10 | 0 | 10 | ✅ PASS |
| `CanvasGuard` | 15 | 0 | 15 | ✅ PASS |
| `Disclosure` | 11 | 0 | 11 | ✅ PASS |
| `ExtractIP` | 2 | 0 | 2 | ✅ PASS |
| `MultiTurn` | 11 | 0 | 11 | ✅ PASS |
| `Normalizer` | 10 | 0 | 10 | ✅ PASS |
| `Pipeline` | 16 | 0 | 16 | ✅ PASS |
| `RagGuard` | 11 | 0 | 11 | ✅ PASS |
| `RateLimiter` | 9 | 0 | 9 | ✅ PASS |
| `Sentinel` | 10 | 0 | 10 | ✅ PASS |
| `Suspicion` | 11 | 0 | 11 | ✅ PASS |
| `WebInjection` | 13 | 0 | 13 | ✅ PASS |

## Module Descriptions

| Module | File | What it tests |
|---|---|---|
| `Canary` | `canary_test.go` | Boot-time canary tokens, honeypot bypass detection, rotation |
| `CanvasGuard` | `canvas_guard_test.go` | Script stripping, event handler removal, dangerous JS patterns, CSP |
| `Disclosure` | `disclosure_test.go` | Deep extraction, recon, chain-of-thought, gaslighting, output tiers |
| `MultiTurn` | `multiturn_test.go` | Persona escalation, creative framing, compliance coercion, topic drift |
| `Normalizer` | `normalizer_test.go` | Unicode confusables, zero-width, HTML entities, base64, ROT13, leet |
| `Pipeline` | `pipeline_test.go` | Full end-to-end integration across all 8 security layers |
| `RagGuard` | `rag_guard_test.go` | HTML comment injection, invisible CSS, LLM tokens, whitespace padding |
| `RateLimiter` | `ratelimit_test.go` | Token bucket, probe trip-wire, IP isolation, Gin middleware |
| `Sentinel` | `sentinel_test.go` | Injection phrases, DAN, persona hijack, reflection, developer mode |
| `Suspicion` | `suspicion_test.go` | Score accumulation, hard-block threshold, session isolation, decay |
| `WebInjection` | `web_injection_test.go` | Weaponisation intent, SSRF, SSI, XSS, XXE, output scanning |

## Running Tests

```bash
# Run all safety tests
./scripts/test_safety.sh

# Run specific module
go test ./pkg/safety/... -run TestCanary -v

# Run with race detector
go test ./pkg/safety/... -race -count=1
```

## Architecture Coverage

The test suite validates the full 8-layer safety pipeline:

```
Input:  NormalizeInput → Sentinel → Adversarial → DisclosureGuard
        → WebInjectionGuard → CanarySystem → (MultiTurnAnalyzer, SuspicionTracker)

Output: Adversarial → DisclosureGuard → WebInjectionGuard
        → CanarySystem → (CanvasGuard if canvas mode)
```

See [SECURITY.md](SECURITY.md) for full architecture documentation.

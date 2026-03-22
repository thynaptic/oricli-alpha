#!/usr/bin/env bash
# Oricli-Alpha — Safety Framework Test Runner
# Usage: ./scripts/test_safety.sh [--report-only]
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
REPORT_FILE="$REPO_ROOT/docs/SAFETY_TEST_REPORT.md"
TIMESTAMP="$(date -u '+%Y-%m-%d %H:%M:%S UTC')"
PASS=0
FAIL=0
declare -A MODULE_PASS
declare -A MODULE_FAIL
declare -A MODULE_TESTS

# ─── colour helpers ──────────────────────────────────────────────────────────
RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'
CYAN='\033[0;36m'; BOLD='\033[1m'; RESET='\033[0m'

banner() { echo -e "${CYAN}${BOLD}$*${RESET}"; }
ok()     { echo -e "  ${GREEN}✓${RESET} $*"; }
fail()   { echo -e "  ${RED}✗${RESET} $*"; }

# ─── run tests ───────────────────────────────────────────────────────────────
banner ""
banner "  Oricli-Alpha Safety Framework — Test Suite"
banner "  $TIMESTAMP"
banner ""

RAW_OUTPUT=$(cd "$REPO_ROOT" && go test ./pkg/safety/... -v -count=1 -timeout=120s 2>&1)
EXIT_CODE=$?

# ─── parse results ───────────────────────────────────────────────────────────
while IFS= read -r line; do
  if [[ "$line" =~ ^---\ (PASS|FAIL):\ (Test([A-Za-z]+)_[A-Za-z_]+)\ \( ]]; then
    status="${BASH_REMATCH[1]}"
    test_name="${BASH_REMATCH[2]}"
    module="${BASH_REMATCH[3]}"
    if [[ "$status" == "PASS" ]]; then
      PASS=$((PASS+1))
      MODULE_PASS[$module]=$(( ${MODULE_PASS[$module]:-0} + 1 ))
    else
      FAIL=$((FAIL+1))
      MODULE_FAIL[$module]=$(( ${MODULE_FAIL[$module]:-0} + 1 ))
      fail "$test_name"
    fi
    MODULE_TESTS[$module]=1
  fi
done <<< "$RAW_OUTPUT"

TOTAL=$((PASS+FAIL))
RATE=0
if [[ $TOTAL -gt 0 ]]; then RATE=$(( PASS*100/TOTAL )); fi

# ─── per-module summary ───────────────────────────────────────────────────────
banner ""
banner "  Results by module:"
for mod in $(echo "${!MODULE_TESTS[@]}" | tr ' ' '\n' | sort); do
  p=${MODULE_PASS[$mod]:-0}
  f=${MODULE_FAIL[$mod]:-0}
  t=$((p+f))
  if [[ $f -eq 0 ]]; then
    ok "${mod}: ${p}/${t}"
  else
    fail "${mod}: ${p}/${t}"
  fi
done

# ─── overall ─────────────────────────────────────────────────────────────────
banner ""
if [[ $FAIL -eq 0 ]]; then
  echo -e "  ${GREEN}${BOLD}ALL TESTS PASSED — ${PASS}/${TOTAL} (${RATE}%)${RESET}"
else
  echo -e "  ${RED}${BOLD}FAILURES — ${PASS}/${TOTAL} passed (${RATE}%)${RESET}"
fi
banner ""

# ─── generate markdown report ────────────────────────────────────────────────
{
cat <<EOF
# Oricli-Alpha — Safety Framework Test Report

> Generated: $TIMESTAMP  
> Command: \`go test ./pkg/safety/... -v -count=1\`

## Summary

| Metric | Value |
|---|---|
| Total tests | $TOTAL |
| Passed | $PASS |
| Failed | $FAIL |
| Pass rate | ${RATE}% |

## Results by Module

| Module | Passed | Failed | Total | Status |
|---|---|---|---|---|
EOF

for mod in $(echo "${!MODULE_TESTS[@]}" | tr ' ' '\n' | sort); do
  p=${MODULE_PASS[$mod]:-0}
  f=${MODULE_FAIL[$mod]:-0}
  t=$((p+f))
  if [[ $f -eq 0 ]]; then status="✅ PASS"; else status="❌ FAIL"; fi
  echo "| \`${mod}\` | ${p} | ${f} | ${t} | ${status} |"
done

cat <<'EOF'

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
EOF
} > "$REPORT_FILE"

echo -e "  ${CYAN}Report written to:${RESET} docs/SAFETY_TEST_REPORT.md"
banner ""

exit $EXIT_CODE

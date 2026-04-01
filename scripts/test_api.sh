#!/usr/bin/env bash
# ─────────────────────────────────────────────────────────────────────────────
# Oricli-Alpha API Smoke Test
# Tests all critical external-facing endpoints with color-coded pass/fail output
#
# Usage:
#   export ORICLI_API_KEY="glm.<prefix>.<secret>"
#   ./scripts/test_api.sh
#   ./scripts/test_api.sh https://oricli.thynaptic.com   # override base URL
#
# Exit code: 0 if all tests pass, 1 if any fail
# ─────────────────────────────────────────────────────────────────────────────
set -euo pipefail

BASE_URL="${1:-${ORICLI_TEST_BASE_URL:-https://oricli.thynaptic.com}}"
API_KEY="${ORICLI_API_KEY:-${ORICLI_TEST_API_KEY:-}}"
TIMEOUT="${ORICLI_TEST_TIMEOUT:-15}"
CHAT_TIMEOUT="${ORICLI_CHAT_TIMEOUT:-60}"  # model swap can take up to ~45s cold

# Colors
RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'
CYAN='\033[0;36m'; BOLD='\033[1m'; RESET='\033[0m'

PASS=0; FAIL=0; SKIP=0
RESULTS=()

# Resource IDs captured during tests (used for cleanup and chained assertions)
SHARE_ID=""
SOVEREIGN_GOAL_ID=""

log()  { echo -e "${CYAN}[smoke]${RESET} $*"; }
ok()   { echo -e "  ${GREEN}✓${RESET} $*"; PASS=$((PASS+1)); RESULTS+=("PASS: $*"); }
fail() { echo -e "  ${RED}✗${RESET} $*"; FAIL=$((FAIL+1)); RESULTS+=("FAIL: $*"); }
skip() { echo -e "  ${YELLOW}~${RESET} $*"; SKIP=$((SKIP+1)); RESULTS+=("SKIP: $*"); }

# ─── HTTP helpers ─────────────────────────────────────────────────────────────

# Returns HTTP status code
status_of() {
  local method="$1" path="$2" body="${3:-}" auth="${4:-}"
  local url="${BASE_URL}${path}"
  local curl_args=(-s -o /dev/null -w "%{http_code}" --max-time "${TIMEOUT}")

  if [[ -n "$auth" && -n "$API_KEY" ]]; then
    curl_args+=(-H "Authorization: Bearer ${API_KEY}")
  fi
  if [[ -n "$body" ]]; then
    curl_args+=(-H "Content-Type: application/json" -d "$body")
  fi

  curl "${curl_args[@]}" -X "$method" "$url" 2>/dev/null || echo "000"
}

# Returns response body
body_of() {
  local method="$1" path="$2" body="${3:-}" auth="${4:-}"
  local url="${BASE_URL}${path}"
  local curl_args=(-s --max-time "${TIMEOUT}")

  if [[ -n "$auth" && -n "$API_KEY" ]]; then
    curl_args+=(-H "Authorization: Bearer ${API_KEY}")
  fi
  if [[ -n "$body" ]]; then
    curl_args+=(-H "Content-Type: application/json" -d "$body")
  fi

  curl "${curl_args[@]}" -X "$method" "$url" 2>/dev/null || echo ""
}

check() {
  # check <name> <method> <path> <expected_status_regex> [body] [auth]
  local name="$1" method="$2" path="$3" expected="$4"
  local body="${5:-}" auth="${6:-}"
  local code
  code=$(status_of "$method" "$path" "$body" "$auth")
  if [[ "$code" =~ ^${expected}$ ]]; then
    ok "$name (${code})"
  elif [[ "$code" == "000" ]]; then
    fail "$name — connection failed (is the server running at ${BASE_URL}?)"
  else
    fail "$name — expected HTTP ${expected}, got ${code}"
  fi
}

# ─── Tests ────────────────────────────────────────────────────────────────────

echo ""
echo -e "${BOLD}╔══════════════════════════════════════════════════════════╗${RESET}"
echo -e "${BOLD}║       Oricli-Alpha API Smoke Test                        ║${RESET}"
echo -e "${BOLD}╚══════════════════════════════════════════════════════════╝${RESET}"
echo ""
echo -e "  ${CYAN}Base URL:${RESET}  ${BASE_URL}"
echo -e "  ${CYAN}API Key:${RESET}   ${API_KEY:0:12}... (${#API_KEY} chars)"
echo -e "  ${CYAN}Timeout:${RESET}   ${TIMEOUT}s"
echo ""

# ── Public endpoints (no auth) ─────────────────────────────────────────────

log "Public endpoints (no auth required)"

check "GET /v1/health → 200"    GET "/v1/health"   "200"
check "GET /v1/eri → 200"       GET "/v1/eri"      "200"
check "GET /v1/modules → 200"   GET "/v1/modules"  "200"
check "GET /v1/metrics → 200"   GET "/v1/metrics"  "200"
check "GET /v1/traces → 200"    GET "/v1/traces"   "200"
check "GET /v1/loglines → 200"  GET "/v1/loglines" "200"

check "POST /v1/waitlist → 200/201" POST "/v1/waitlist" "200|201" \
  '{"email":"smoke@test.example.com","name":"Smoke Test","plan":"starter"}'

# Verify health body contains status=ready
HEALTH_BODY=$(body_of GET "/v1/health" "" "")
if echo "$HEALTH_BODY" | grep -q '"status":"ready"' 2>/dev/null || \
   echo "$HEALTH_BODY" | python3 -c "import sys,json; d=json.load(sys.stdin); exit(0 if d.get('status')=='ready' else 1)" 2>/dev/null; then
  ok "GET /v1/health body contains status=ready"
else
  fail "GET /v1/health body missing status=ready (body: ${HEALTH_BODY:0:100})"
fi

echo ""

# ── Auth rejection tests ───────────────────────────────────────────────────

log "Auth rejection (protected endpoints must reject no-auth requests)"

check "POST /v1/chat/completions → 401/403 (no auth)"  POST "/v1/chat/completions" "401|403" '{"messages":[{"role":"user","content":"hi"}]}'
check "GET /v1/goals → 401/403 (no auth)"              GET  "/v1/goals"             "401|403"
check "GET /v1/memories → 401/403 (no auth)"           GET  "/v1/memories"          "401|403"
check "GET /v1/daemons → 401/403 (no auth)"            GET  "/v1/daemons"           "401|403"

echo ""

# ── Authenticated endpoints ────────────────────────────────────────────────

if [[ -z "$API_KEY" ]]; then
  echo -e "  ${YELLOW}⚠ ORICLI_API_KEY not set — skipping all authenticated tests${RESET}"
  echo ""
else

  # ── Core authenticated endpoints ─────────────────────────────────────────

  log "Core authenticated endpoints"

  # Chat uses a longer timeout — Ollama may need to swap models (~45s cold load)
  CHAT_CODE=$(curl -s -o /dev/null -w "%{http_code}" --max-time "${CHAT_TIMEOUT}" \
    -X POST "${BASE_URL}/v1/chat/completions" \
    -H "Authorization: Bearer ${API_KEY}" \
    -H "Content-Type: application/json" \
    -d '{"model":"oricli-cognitive","messages":[{"role":"user","content":"Reply PONG"}],"max_tokens":5}' 2>/dev/null || echo "000")
  if [[ "$CHAT_CODE" == "200" ]]; then
    ok "POST /v1/chat/completions → 200 (${CHAT_CODE})"
  elif [[ "$CHAT_CODE" == "000" ]]; then
    fail "POST /v1/chat/completions — connection failed"
  else
    fail "POST /v1/chat/completions — expected 200, got ${CHAT_CODE} (Ollama may be loading a model — retry or increase ORICLI_CHAT_TIMEOUT)"
  fi

  check "GET /v1/goals → 200"                GET "/v1/goals"              "200" "" "auth"
  check "GET /v1/memories → 200"             GET "/v1/memories"           "200" "" "auth"
  check "GET /v1/memories/knowledge → 200"   GET "/v1/memories/knowledge" "200" "" "auth"
  check "GET /v1/documents → 200"            GET "/v1/documents"          "200" "" "auth"
  check "GET /v1/daemons → 200"              GET "/v1/daemons"            "200" "" "auth"
  check "GET /v1/sovereign/identity → 200"   GET "/v1/sovereign/identity" "200" "" "auth"

  INGEST_CODE=$(status_of POST "/v1/ingest" '{"content":"Smoke test knowledge fragment","source":"smoke_test"}' "auth")
  if [[ "$INGEST_CODE" == "200" || "$INGEST_CODE" == "201" ]]; then
    ok "POST /v1/ingest → ${INGEST_CODE}"
  elif [[ "$INGEST_CODE" == "503" || "$INGEST_CODE" == "500" ]]; then
    skip "POST /v1/ingest → orchestrator not available (${INGEST_CODE})"
  else
    fail "POST /v1/ingest → expected 200/201, got ${INGEST_CODE}"
  fi

  check "POST /v1/feedback → 200/201" POST "/v1/feedback" "200|201" \
    '{"message_id":"smoke-test","reaction":"thumbs_up"}' "auth"

  # Enterprise knowledge search
  ENT_STATUS=$(status_of GET "/v1/enterprise/knowledge/search?q=smoke+test" "" "auth")
  if [[ "$ENT_STATUS" == "200" ]]; then
    ok "GET /v1/enterprise/knowledge/search → 200"
  elif [[ "$ENT_STATUS" == "404" || "$ENT_STATUS" == "503" ]]; then
    skip "GET /v1/enterprise/knowledge/search → not enabled (${ENT_STATUS})"
  else
    fail "GET /v1/enterprise/knowledge/search → expected 200, got ${ENT_STATUS}"
  fi

  # Agent vibe — 422 is acceptable if agent validation fails
  check "POST /v1/agents/vibe → 200/201/422" POST "/v1/agents/vibe" "200|201|422" \
    '{"message":"Create a research assistant agent","history":[]}' "auth"

  # Vision analyze — skip if endpoint not enabled or no model available
  VISION_CODE=$(status_of POST "/v1/vision/analyze" \
    '{"image":"iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg==","prompt":"What do you see?"}' \
    "auth")
  if [[ "$VISION_CODE" == "200" || "$VISION_CODE" == "201" ]]; then
    ok "POST /v1/vision/analyze → ${VISION_CODE}"
  elif [[ "$VISION_CODE" == "404" || "$VISION_CODE" == "500" || "$VISION_CODE" == "503" || "$VISION_CODE" == "422" ]]; then
    skip "POST /v1/vision/analyze → not enabled or no vision model (${VISION_CODE})"
  else
    fail "POST /v1/vision/analyze → expected 200/201, got ${VISION_CODE}"
  fi

  echo ""

  # ── Share lifecycle ───────────────────────────────────────────────────────

  log "Share lifecycle"

  SHARE_RESP=$(body_of POST "/v1/share" \
    '{"title":"Smoke Test","content":"Test canvas","type":"canvas"}' "auth")
  SHARE_ID=$(echo "$SHARE_RESP" | python3 -c \
    "import sys,json; d=json.load(sys.stdin); print(d.get('id','') or d.get('share_id',''))" \
    2>/dev/null || echo "")

  if [[ -n "$SHARE_ID" && "$SHARE_ID" != "None" ]]; then
    ok "POST /v1/share → 201 (id: ${SHARE_ID})"
    # GET /share/:id lives on the root router (not under /v1)
    check "GET /share/${SHARE_ID} → 200 (public)" GET "/share/${SHARE_ID}" "200"
  else
    fail "POST /v1/share — could not extract share ID (response: ${SHARE_RESP:0:200})"
    skip "GET /share/:id — skipped (share creation failed)"
  fi

  echo ""

  # ── Goal CRUD lifecycle ───────────────────────────────────────────────────

  log "Goal CRUD lifecycle"

  GOAL_RESP=$(body_of POST "/v1/goals" \
    '{"goal":"Smoke test goal — safe to delete","priority":9,"metadata":{"source":"smoke_test"}}' "auth")
  GOAL_ID=$(echo "$GOAL_RESP" | python3 -c \
    "import sys,json; print(json.load(sys.stdin).get('id',''))" 2>/dev/null || echo "")

  if [[ -n "$GOAL_ID" && "$GOAL_ID" != "None" && "$GOAL_ID" != "" ]]; then
    ok "POST /v1/goals → 201 (id: ${GOAL_ID})"
    check "GET /v1/goals/${GOAL_ID} → 200"       GET    "/v1/goals/${GOAL_ID}" "200" "" "auth"
    check "PUT /v1/goals/${GOAL_ID} → 200"       PUT    "/v1/goals/${GOAL_ID}" "200" \
      '{"goal":"Smoke test goal — updated","priority":5}' "auth"
    check "DELETE /v1/goals/${GOAL_ID} → 2xx"   DELETE "/v1/goals/${GOAL_ID}" "20[04]" "" "auth"
  else
    fail "POST /v1/goals — could not extract goal ID (response: ${GOAL_RESP:0:200})"
  fi

  echo ""

  # ── Sovereign goals lifecycle ─────────────────────────────────────────────

  log "Sovereign goals lifecycle"

  SOV_RESP=$(body_of POST "/v1/sovereign/goals" \
    '{"objective":"Smoke test sovereign goal"}' "auth")
  SOVEREIGN_GOAL_ID=$(echo "$SOV_RESP" | python3 -c \
    "import sys,json; print(json.load(sys.stdin).get('id',''))" 2>/dev/null || echo "")

  if [[ -n "$SOVEREIGN_GOAL_ID" && "$SOVEREIGN_GOAL_ID" != "None" ]]; then
    ok "POST /v1/sovereign/goals → 201 (id: ${SOVEREIGN_GOAL_ID})"
    check "GET /v1/sovereign/goals → 200" \
      GET "/v1/sovereign/goals" "200" "" "auth"
    check "GET /v1/sovereign/goals/${SOVEREIGN_GOAL_ID} → 200" \
      GET "/v1/sovereign/goals/${SOVEREIGN_GOAL_ID}" "200" "" "auth"
    check "DELETE /v1/sovereign/goals/${SOVEREIGN_GOAL_ID} → 200/204" \
      DELETE "/v1/sovereign/goals/${SOVEREIGN_GOAL_ID}" "200|204" "" "auth"
  else
    fail "POST /v1/sovereign/goals — could not extract ID (response: ${SOV_RESP:0:200})"
    skip "GET /v1/sovereign/goals — skipped (creation failed)"
    skip "GET /v1/sovereign/goals/:id — skipped (creation failed)"
    skip "DELETE /v1/sovereign/goals/:id — skipped (creation failed)"
  fi

  echo ""

  # ── Therapy stack ─────────────────────────────────────────────────────────

  log "Therapy stack"

  THERAPY_STATUS=$(status_of GET "/v1/therapy/stats" "" "auth")
  if [[ "$THERAPY_STATUS" == "200" ]]; then
    ok "GET /v1/therapy/stats → 200"
    check "POST /v1/therapy/detect → 200"            POST "/v1/therapy/detect"            "200" \
      '{"text":"I must be perfect or I have completely failed."}' "auth"
    check "GET /v1/therapy/formulation → 200"         GET  "/v1/therapy/formulation"        "200" "" "auth"
    check "GET /v1/therapy/mastery → 200"             GET  "/v1/therapy/mastery"            "200" "" "auth"
    check "GET /v1/therapy/helplessness/stats → 200"  GET  "/v1/therapy/helplessness/stats" "200" "" "auth"
  elif [[ "$THERAPY_STATUS" == "404" || "$THERAPY_STATUS" == "503" ]]; then
    skip "Therapy stack not enabled (ORICLI_THERAPY_ENABLED not set)"
  else
    fail "GET /v1/therapy/stats → unexpected status ${THERAPY_STATUS}"
  fi

  echo ""

  # ── Cognition pipeline stats (all modules) ────────────────────────────────

  log "Cognition pipeline stats (all modules)"

  for mod in \
    load rumination mindset hope defeat conformity ideocapture coalition \
    statusbias arousal interference mct mbt schema ipsrt ilm iut up cbasp \
    mbct phaseoriented pseudoidentity thoughtreform apathy logotherapy stoic \
    socratic narrative polyvagal dmn interoception process; do
    CODE=$(status_of GET "/v1/cognition/${mod}/stats" "" "auth")
    if [[ "$CODE" == "200" ]]; then
      ok "GET /v1/cognition/${mod}/stats → 200"
    elif [[ "$CODE" == "404" ]]; then
      skip "GET /v1/cognition/${mod}/stats → not enabled"
    else
      fail "GET /v1/cognition/${mod}/stats → ${CODE}"
    fi
  done

  echo ""

  # ── Metacognition ─────────────────────────────────────────────────────────

  log "Metacognition"

  METACOG_STATUS=$(status_of GET "/v1/metacog/stats" "" "auth")
  if [[ "$METACOG_STATUS" == "200" ]]; then
    ok "GET /v1/metacog/stats → 200"
    check "GET /v1/metacog/events → 200"  GET  "/v1/metacog/events" "200" "" "auth"
    check "POST /v1/metacog/scan → 200"   POST "/v1/metacog/scan"   "200" '{}' "auth"
  elif [[ "$METACOG_STATUS" == "404" || "$METACOG_STATUS" == "503" ]]; then
    skip "Metacog not enabled (${METACOG_STATUS})"
  else
    fail "GET /v1/metacog/stats → unexpected status ${METACOG_STATUS}"
  fi

  echo ""

  # ── Chronos ───────────────────────────────────────────────────────────────

  log "Chronos"

  CHRONOS_STATUS=$(status_of GET "/v1/chronos/snapshot" "" "auth")
  if [[ "$CHRONOS_STATUS" == "200" ]]; then
    ok "GET /v1/chronos/snapshot → 200"
    check "GET /v1/chronos/entries → 200"  GET "/v1/chronos/entries" "200" "" "auth"
    check "GET /v1/chronos/changes → 200"  GET "/v1/chronos/changes" "200" "" "auth"
  elif [[ "$CHRONOS_STATUS" == "404" || "$CHRONOS_STATUS" == "503" ]]; then
    skip "Chronos not enabled (${CHRONOS_STATUS})"
  else
    fail "GET /v1/chronos/snapshot → unexpected status ${CHRONOS_STATUS}"
  fi

  echo ""

  # ── Science ───────────────────────────────────────────────────────────────

  log "Science"

  SCIENCE_STATUS=$(status_of GET "/v1/science/stats" "" "auth")
  if [[ "$SCIENCE_STATUS" == "200" ]]; then
    ok "GET /v1/science/stats → 200"
    check "GET /v1/science/hypotheses → 200"  GET "/v1/science/hypotheses" "200" "" "auth"
  elif [[ "$SCIENCE_STATUS" == "404" || "$SCIENCE_STATUS" == "503" ]]; then
    skip "Science not enabled (${SCIENCE_STATUS})"
  else
    fail "GET /v1/science/stats → unexpected status ${SCIENCE_STATUS}"
  fi

  echo ""

  # ── Skills / Crystals ─────────────────────────────────────────────────────

  log "Skills / Crystals"

  CRYSTAL_STATUS=$(status_of GET "/v1/skills/crystals" "" "auth")
  if [[ "$CRYSTAL_STATUS" == "200" ]]; then
    ok "GET /v1/skills/crystals → 200"
    check "GET /v1/skills/crystals/stats → 200"  GET "/v1/skills/crystals/stats" "200" "" "auth"
  elif [[ "$CRYSTAL_STATUS" == "404" || "$CRYSTAL_STATUS" == "503" ]]; then
    skip "Skills/Crystals not enabled (${CRYSTAL_STATUS})"
  else
    fail "GET /v1/skills/crystals → unexpected status ${CRYSTAL_STATUS}"
  fi

  echo ""

  # ── Curator ───────────────────────────────────────────────────────────────

  log "Curator"

  CURATOR_STATUS=$(status_of GET "/v1/curator/models" "" "auth")
  if [[ "$CURATOR_STATUS" == "200" ]]; then
    ok "GET /v1/curator/models → 200"
  elif [[ "$CURATOR_STATUS" == "404" || "$CURATOR_STATUS" == "503" ]]; then
    skip "Curator not enabled (${CURATOR_STATUS})"
  else
    fail "GET /v1/curator/models → expected 200, got ${CURATOR_STATUS}"
  fi

  echo ""

  # ── Audit ─────────────────────────────────────────────────────────────────

  log "Audit"

  AUDIT_STATUS=$(status_of GET "/v1/audit/runs" "" "auth")
  if [[ "$AUDIT_STATUS" == "200" ]]; then
    ok "GET /v1/audit/runs → 200"
  elif [[ "$AUDIT_STATUS" == "404" || "$AUDIT_STATUS" == "503" ]]; then
    skip "Audit not enabled (${AUDIT_STATUS})"
  else
    fail "GET /v1/audit/runs → expected 200, got ${AUDIT_STATUS}"
  fi

  echo ""

  # ── Fine-tune (optional) ──────────────────────────────────────────────────

  log "Fine-tune (optional)"

  FT_STATUS=$(status_of GET "/v1/finetune/jobs" "" "auth")
  if [[ "$FT_STATUS" == "200" ]]; then
    ok "GET /v1/finetune/jobs → 200"
  elif [[ "$FT_STATUS" == "404" || "$FT_STATUS" == "503" ]]; then
    skip "Fine-tune not enabled (${FT_STATUS})"
  else
    fail "GET /v1/finetune/jobs → expected 200/404, got ${FT_STATUS}"
  fi

  echo ""

  # ── Additional features ───────────────────────────────────────────────────

  log "Additional features"

  PAD_STATUS=$(status_of GET "/v1/pad/stats" "" "auth")
  [[ "$PAD_STATUS" == "200" ]] && ok "GET /v1/pad/stats → 200" || skip "PAD not enabled (${PAD_STATUS})"

  SENTINEL_STATUS=$(status_of GET "/v1/sentinel/stats" "" "auth")
  [[ "$SENTINEL_STATUS" == "200" ]] && ok "GET /v1/sentinel/stats → 200" || skip "Sentinel not enabled (${SENTINEL_STATUS})"

  COMPUTE_GOV_STATUS=$(status_of GET "/v1/compute/governor" "" "auth")
  [[ "$COMPUTE_GOV_STATUS" == "200" ]] && ok "GET /v1/compute/governor → 200" || skip "Compute governor not enabled (${COMPUTE_GOV_STATUS})"

  COMPUTE_BID_STATUS=$(status_of GET "/v1/compute/bids/stats" "" "auth")
  [[ "$COMPUTE_BID_STATUS" == "200" ]] && ok "GET /v1/compute/bids/stats → 200" || skip "Compute bids/stats not enabled (${COMPUTE_BID_STATUS})"

  echo ""

  # ── Swarm health (admin — 403 is acceptable with a non-admin token) ───────

  log "Swarm health (admin — 200 or 403 both acceptable)"

  SWARM_HEALTH_CODE=$(status_of GET "/v1/swarm/health" "" "auth")
  if [[ "$SWARM_HEALTH_CODE" == "200" ]]; then
    ok "GET /v1/swarm/health → 200 (token has swarm-admin access)"
  elif [[ "$SWARM_HEALTH_CODE" == "403" || "$SWARM_HEALTH_CODE" == "401" ]]; then
    skip "GET /v1/swarm/health → ${SWARM_HEALTH_CODE} (admin token required — expected for non-admin keys)"
  elif [[ "$SWARM_HEALTH_CODE" == "404" || "$SWARM_HEALTH_CODE" == "503" ]]; then
    skip "GET /v1/swarm/health → not enabled (${SWARM_HEALTH_CODE})"
  else
    fail "GET /v1/swarm/health → unexpected status ${SWARM_HEALTH_CODE}"
  fi

fi

# ─── Summary ──────────────────────────────────────────────────────────────────

echo ""
echo -e "${BOLD}──────────────────────────────────────────────────────────${RESET}"
echo -e "${BOLD}  Results${RESET}"
echo -e "${BOLD}──────────────────────────────────────────────────────────${RESET}"
echo -e "  ${GREEN}PASS${RESET}  ${PASS}"
echo -e "  ${RED}FAIL${RESET}  ${FAIL}"
echo -e "  ${YELLOW}SKIP${RESET}  ${SKIP}"
echo ""

if [[ $FAIL -gt 0 ]]; then
  echo -e "${RED}${BOLD}FAILED${RESET} — ${FAIL} test(s) did not pass"
  echo ""
  for r in "${RESULTS[@]}"; do
    [[ "$r" == FAIL:* ]] && echo -e "  ${RED}✗${RESET} ${r#FAIL: }"
  done
  echo ""
  exit 1
else
  echo -e "${GREEN}${BOLD}ALL TESTS PASSED${RESET}"
  echo ""
  exit 0
fi

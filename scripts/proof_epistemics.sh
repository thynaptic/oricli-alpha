#!/usr/bin/env bash
# Proof-of-concept test for the epistemics engine via the live API.
# Sends explanatory queries and non-explanatory queries, shows which route fires.
#
# Usage:
#   ./scripts/proof_epistemics.sh
#   ORI_KEY=sk-... BASE_URL=https://glm.thynaptic.com ./scripts/proof_epistemics.sh

set -euo pipefail

BASE_URL="${BASE_URL:-http://localhost:8089}"
ORI_KEY="${ORI_KEY:-$(grep ORICLI_SEED_API_KEY /home/mike/Mavaia/.env 2>/dev/null | cut -d= -f2 || echo '')}"

if [[ -z "$ORI_KEY" ]]; then
  echo "ERROR: set ORI_KEY or add ORICLI_SEED_API_KEY to .env"
  exit 1
fi

SEP="$(printf '─%.0s' {1..70})"

call_api() {
  local query="$1"
  curl -s -N -X POST "$BASE_URL/v1/chat/completions" \
    -H "Authorization: Bearer $ORI_KEY" \
    -H "Content-Type: application/json" \
    -H "Accept: text/event-stream" \
    -d "{
      \"model\": \"ori-reasoner\",
      \"stream\": true,
      \"messages\": [{\"role\": \"user\", \"content\": $(echo "$query" | python3 -c 'import json,sys; print(json.dumps(sys.stdin.read().strip()))')}]
    }" | grep '^data:' | grep -v '\[DONE\]' \
      | python3 -c '
import sys, json
buf = ""
for line in sys.stdin:
    line = line.strip()
    if not line.startswith("data:"):
        continue
    try:
        d = json.loads(line[5:])
        token = d.get("choices",[{}])[0].get("delta",{}).get("content","")
        if token:
            buf += token
            print(token, end="", flush=True)
    except Exception:
        pass
print()
'
}

echo ""
echo "$SEP"
echo "  EPISTEMICS ENGINE — PROOF OF CLOSED GAPS"
echo "  Deutsch: Conjecture → Criticism → Synthesis"
echo "$SEP"
echo ""

# ── Explanatory queries (should trigger epistemics) ──────────────────────────

TESTS=(
  "Why does confirmation bias persist even in people who know about it and are actively trying to avoid it?"
  "How does compound interest work mechanically — not what it produces, but the causal process that makes it exponential?"
  "What causes some social movements to achieve lasting change while structurally similar ones dissolve within years?"
)

for query in "${TESTS[@]}"; do
  echo "$SEP"
  echo "QUERY (explanatory): $query"
  echo "$SEP"
  echo ""
  call_api "$query"
  echo ""
  echo ""
done

# ── Non-explanatory queries (should NOT trigger epistemics) ──────────────────

echo "$SEP"
echo "CONTROL — non-explanatory (should skip epistemics loop)"
echo "$SEP"
echo ""

CONTROL="List the top 5 JavaScript frameworks with a one-line description each."
echo "QUERY (non-explanatory): $CONTROL"
echo ""
call_api "$CONTROL"
echo ""

echo "$SEP"
echo "Check server logs for [Epistemics] lines:"
echo "  sudo journalctl -u oricli-backbone -n 50 --no-pager | grep Epistemics"
echo "$SEP"

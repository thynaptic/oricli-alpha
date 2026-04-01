#!/usr/bin/env bash
# build_ori_models.sh — Rebuild all ori: model tiers from Modelfiles
#
# Usage:
#   ./scripts/build_ori_models.sh            # build all tiers
#   ./scripts/build_ori_models.sh 1.7b       # build specific tier
#   ./scripts/build_ori_models.sh --restart  # build all + restart oricli-api
#
# After updating a Modelfile, just run this to push the changes into Ollama.
# ori:4b and ori:16b are skipped automatically if their base model isn't pulled yet.

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
MODELS_DIR="$REPO_ROOT/models"

RESTART=false
FILTER=""

for arg in "$@"; do
  case "$arg" in
    --restart) RESTART=true ;;
    *)         FILTER="$arg" ;;
  esac
done

# ── Tier definitions ──────────────────────────────────────────────────────────
# Format: "tag:base_model"
TIERS=(
  "ori:1.7b:qwen3:1.7b"
  "ori:4b:qwen3:4b"
  "ori:16b:qwen3:14b"
)

build_tier() {
  local tag="$1"        # e.g. ori:1.7b
  local base="$2"       # e.g. qwen3:1.7b
  local version="${tag#ori:}"  # e.g. 1.7b
  local modelfile="$MODELS_DIR/Modelfile.ori-${version}"

  echo ""
  echo "━━━ $tag (base: $base) ━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

  if [[ ! -f "$modelfile" ]]; then
    echo "  ⚠  Modelfile not found: $modelfile — skipping"
    return 0
  fi

  # Check if base model is available locally
  if ! ollama list 2>/dev/null | grep -q "^${base} "; then
    echo "  ⚠  Base model '$base' not pulled — skipping $tag"
    echo "     Run: ollama pull $base"
    return 0
  fi

  echo "  → Building $tag from $modelfile ..."
  if ollama create "$tag" -f "$modelfile" 2>&1 | tail -1 | grep -q "success"; then
    echo "  ✓  $tag created successfully"
  else
    echo "  ✗  Failed to create $tag"
    return 1
  fi
}

echo "════════════════════════════════════════════"
echo " ORI Model Builder"
echo " $(date '+%Y-%m-%d %H:%M:%S')"
echo "════════════════════════════════════════════"

BUILT=0
SKIPPED=0

for entry in "${TIERS[@]}"; do
  # Split "ori:1.7b:qwen3:1.7b" → tag="ori:1.7b", base="qwen3:1.7b"
  tag="${entry%%:qwen*}"
  base="${entry#*:qwen}"
  base="qwen${base}"

  version="${tag#ori:}"
  if [[ -n "$FILTER" && "$version" != "$FILTER" ]]; then
    continue
  fi

  output=$(build_tier "$tag" "$base" 2>&1)
  echo "$output"
  if echo "$output" | grep -q "✓"; then
    BUILT=$((BUILT + 1))
  else
    SKIPPED=$((SKIPPED + 1))
  fi
done

echo ""
echo "────────────────────────────────────────────"
echo " Built: $BUILT  |  Skipped/failed: $SKIPPED"
echo "────────────────────────────────────────────"

if [[ "$RESTART" == "true" ]]; then
  echo ""
  echo "→ Restarting oricli-api.service ..."
  sudo systemctl restart oricli-api.service
  sleep 3
  STATUS=$(systemctl is-active oricli-api.service)
  echo "  Service: $STATUS"
fi

echo ""
echo "Done."

#!/usr/bin/env bash
# build_ori_models.sh — Rebuild all ori: model tiers from Modelfiles
#
# Usage:
#   ./scripts/build_ori_models.sh                          # build local tiers only
#   ./scripts/build_ori_models.sh 1.7b                     # build specific tier locally
#   ./scripts/build_ori_models.sh --restart                # build local + restart oricli-api
#   ./scripts/build_ori_models.sh --remote https://POD_ID-11434.proxy.runpod.net
#   ./scripts/build_ori_models.sh 4b --remote https://...  # single remote tier
#
# Remote mode: pushes the Modelfile to a RunPod pod's Ollama instance via OLLAMA_HOST.
# The base model (e.g. qwen3:4b) must already be pulled on the remote pod.
# RunPod proxy URL format: https://POD_ID-11434.proxy.runpod.net
#
# After updating a Modelfile, just run this to push changes into Ollama (local or remote).

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
MODELS_DIR="$REPO_ROOT/models"

RESTART=false
FILTER=""
REMOTE_HOST=""

for arg in "$@"; do
  case "$arg" in
    --restart)  RESTART=true ;;
    --remote)   shift; REMOTE_HOST="$1" ;;
    --remote=*) REMOTE_HOST="${arg#--remote=}" ;;
    *)          FILTER="$arg" ;;
  esac
done

# ── Tier definitions ──────────────────────────────────────────────────────────
# Format: "ori_tag:base_model:local|remote|both"
# local  = build on this VPS only
# remote = build on RunPod pod only
# both   = build everywhere
TIERS=(
  "ori:1.7b:qwen3:1.7b:local"
  "ori:4b:qwen3:4b:remote"
  "ori:16b:qwen3:14b:remote"
)

# Run an ollama command, optionally against a remote host
ollama_cmd() {
  if [[ -n "$REMOTE_HOST" ]]; then
    OLLAMA_HOST="$REMOTE_HOST" ollama "$@"
  else
    ollama "$@"
  fi
}

build_tier() {
  local tag="$1"
  local base="$2"
  local version="${tag#ori:}"
  local modelfile="$MODELS_DIR/Modelfile.ori-${version}"

  echo ""
  echo "━━━ $tag (base: $base) ━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

  if [[ -n "$REMOTE_HOST" ]]; then
    echo "  target: $REMOTE_HOST"
  else
    echo "  target: local"
  fi

  if [[ ! -f "$modelfile" ]]; then
    echo "  ⚠  Modelfile not found: $modelfile — skipping"
    return 0
  fi

  # Check if base model is available on the target
  if ! ollama_cmd list 2>/dev/null | grep -q "^${base} "; then
    echo "  ⚠  Base model '$base' not found on target — skipping $tag"
    if [[ -n "$REMOTE_HOST" ]]; then
      echo "     SSH into the pod and run: ollama pull $base"
    else
      echo "     Run: ollama pull $base"
    fi
    return 0
  fi

  echo "  → Building $tag ..."
  if ollama_cmd create "$tag" -f "$modelfile" 2>&1 | tail -1 | grep -q "success"; then
    echo "  ✓  $tag created successfully"
  else
    echo "  ✗  Failed to create $tag"
    return 1
  fi
}

echo "════════════════════════════════════════════"
echo " ORI Model Builder"
echo " $(date '+%Y-%m-%d %H:%M:%S')"
if [[ -n "$REMOTE_HOST" ]]; then
  echo " Mode: REMOTE → $REMOTE_HOST"
else
  echo " Mode: LOCAL"
fi
echo "════════════════════════════════════════════"

BUILT=0
SKIPPED=0

for entry in "${TIERS[@]}"; do
  # Parse "ori:1.7b:qwen3:1.7b:local" → tag, base, locality
  tag="${entry%%:qwen*}"
  rest="${entry#*:qwen}"
  base="qwen${rest%:*}"
  locality="${rest##*:}"

  version="${tag#ori:}"

  # Filter by tier name if specified
  if [[ -n "$FILTER" && "$version" != "$FILTER" ]]; then
    continue
  fi

  # Skip tiers that don't match local/remote mode
  if [[ -z "$REMOTE_HOST" && "$locality" == "remote" ]]; then
    echo ""
    echo "━━━ $tag ━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo "  ⏭  RunPod-only tier — pass --remote <url> to build"
    SKIPPED=$((SKIPPED + 1))
    continue
  fi
  if [[ -n "$REMOTE_HOST" && "$locality" == "local" ]]; then
    echo ""
    echo "━━━ $tag ━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo "  ⏭  Local-only tier — skipping in remote mode"
    SKIPPED=$((SKIPPED + 1))
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

if [[ "$RESTART" == "true" && -z "$REMOTE_HOST" ]]; then
  echo ""
  echo "→ Restarting oricli-api.service ..."
  sudo systemctl restart oricli-api.service
  sleep 3
  STATUS=$(systemctl is-active oricli-api.service)
  echo "  Service: $STATUS"
fi

# ── Sync updated Modelfiles to S3 ────────────────────────────────────────────
S3_ENDPOINT="${ORI_S3_ENDPOINT:-https://s3api-eu-ro-1.runpod.io}"
S3_BUCKET="${ORI_S3_BUCKET:-s2uvk5nvun}"

# Use credentials file profile if present, otherwise fall back to env vars
_S3_AUTH=""
if grep -q "\[runpod\]" ~/.aws/credentials 2>/dev/null; then
  _S3_AUTH="--profile runpod"
fi

if aws s3 ls "s3://${S3_BUCKET}/" $_S3_AUTH --region eu-ro-1 \
    --endpoint-url "$S3_ENDPOINT" > /dev/null 2>&1; then
  echo ""
  echo "→ Syncing Modelfiles to S3 ..."
  for f in "$MODELS_DIR"/Modelfile.ori-*; do
    name="$(basename "$f")"
    aws s3 cp "$f" "s3://${S3_BUCKET}/modelfiles/${name}" \
      $_S3_AUTH --region eu-ro-1 --endpoint-url "$S3_ENDPOINT" \
      --quiet && echo "  ✓ $name → s3://${S3_BUCKET}/modelfiles/${name}"
  done
else
  echo ""
  echo "  ⏭  S3 not reachable — skipping Modelfile sync (set ORI_S3_* env vars)"
fi

echo ""
echo "Done."


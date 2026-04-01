#!/usr/bin/env bash
# pod_setup.sh — RunPod pod cold-start bootstrap for Ori model tiers
#
# This script runs once when a RunPod pod starts. It:
#   1. Syncs Ollama model blobs from S3 (fast NVMe) if cached
#   2. Falls back to `ollama pull` from HF if not cached
#   3. Creates ori: model tiers from Modelfiles
#   4. Syncs blobs back to S3 for future pods
#
# Expected pod env vars (set in RunPod template):
#   RUNPOD_S3_ENDPOINT  = https://s3api-eu-ro-1.runpod.io
#   RUNPOD_S3_BUCKET    = s2uvk5nvun
#   RUNPOD_S3_KEY       = user_3AAtmhUshdqnwQvcSYkFNrOQbF8
#   RUNPOD_S3_SECRET    = rps_DK3KBF0UX3046F166E1QJ7KXC418SITKKKHHBBJVb6hyw1
#   ORI_TIER            = 4b  (or 16b — which tier this pod runs)

set -euo pipefail

S3_ENDPOINT="${RUNPOD_S3_ENDPOINT:-https://s3api-eu-ro-1.runpod.io}"
S3_BUCKET="${RUNPOD_S3_BUCKET:-s2uvk5nvun}"
S3_KEY="${RUNPOD_S3_KEY:-}"
S3_SECRET="${RUNPOD_S3_SECRET:-}"
ORI_TIER="${ORI_TIER:-4b}"
OLLAMA_MODELS_DIR="${OLLAMA_MODELS_DIR:-/root/.ollama/models}"
REGION="eu-ro-1"

# Tier → base model mapping
declare -A TIER_BASE
TIER_BASE["4b"]="qwen3:4b"
TIER_BASE["16b"]="qwen3:14b"

BASE_MODEL="${TIER_BASE[$ORI_TIER]:-}"
if [[ -z "$BASE_MODEL" ]]; then
  echo "ERROR: Unknown ORI_TIER='$ORI_TIER'. Valid: 4b, 16b"
  exit 1
fi

log() { echo "[$(date '+%H:%M:%S')] $*"; }

# ── AWS CLI config ────────────────────────────────────────────────────────────
setup_aws() {
  mkdir -p ~/.aws
  cat > ~/.aws/credentials << EOF
[runpod]
aws_access_key_id = ${S3_KEY}
aws_secret_access_key = ${S3_SECRET}
EOF
  chmod 600 ~/.aws/credentials
}

s3() {
  aws s3 "$@" --profile runpod --region "$REGION" --endpoint-url "$S3_ENDPOINT"
}

# ── Ollama ────────────────────────────────────────────────────────────────────
wait_for_ollama() {
  log "Waiting for Ollama to be ready..."
  for i in $(seq 1 30); do
    if curl -sf http://localhost:11434/api/tags > /dev/null 2>&1; then
      log "Ollama ready."
      return 0
    fi
    sleep 2
  done
  log "ERROR: Ollama did not start in time"
  exit 1
}

model_exists() {
  ollama list 2>/dev/null | grep -q "^${1} "
}

# ── Main ──────────────────────────────────────────────────────────────────────
log "═══ Ori Pod Setup — tier: ori:${ORI_TIER} ═══"
log "Base model: $BASE_MODEL"

setup_aws
wait_for_ollama

mkdir -p "$OLLAMA_MODELS_DIR/blobs" "$OLLAMA_MODELS_DIR/manifests"

# Step 1: Try to restore base model blobs from S3
BASE_TAG="${BASE_MODEL//:/-}"  # e.g. qwen3-4b
S3_BLOB_PATH="s3://${S3_BUCKET}/ollama/models/${BASE_TAG}/"

log "Checking S3 cache for $BASE_MODEL ..."
if s3 ls "$S3_BLOB_PATH" > /dev/null 2>&1; then
  log "Cache hit — syncing $BASE_MODEL blobs from S3 ..."
  s3 sync "$S3_BLOB_PATH" "$OLLAMA_MODELS_DIR/" --no-progress
  log "Sync complete. Verifying model ..."
  # Re-register manifest with Ollama if blobs restored manually
  if ! model_exists "$BASE_MODEL"; then
    log "Blobs restored but manifest missing — pulling to register ..."
    ollama pull "$BASE_MODEL"
  fi
else
  log "No S3 cache — pulling $BASE_MODEL from registry (this takes a while)..."
  ollama pull "$BASE_MODEL"
  log "Pull complete. Caching blobs to S3 for future pods..."
  s3 sync "$OLLAMA_MODELS_DIR/" "$S3_BLOB_PATH" \
    --exclude "*/ori/*" \
    --no-progress
  log "Blobs cached to S3."
fi

# Step 2: Download Modelfile from S3
MODELFILE_LOCAL="/tmp/Modelfile.ori-${ORI_TIER}"
log "Downloading Modelfile.ori-${ORI_TIER} from S3 ..."
s3 cp "s3://${S3_BUCKET}/modelfiles/Modelfile.ori-${ORI_TIER}" "$MODELFILE_LOCAL"

# Step 3: Create ori model
log "Creating ori:${ORI_TIER} ..."
ollama create "ori:${ORI_TIER}" -f "$MODELFILE_LOCAL"
log "✓ ori:${ORI_TIER} ready"

# Step 4: Cache ori model back to S3
ORI_TAG="ori-${ORI_TIER}"
log "Caching ori:${ORI_TIER} blobs to S3 ..."
s3 sync "$OLLAMA_MODELS_DIR/" "s3://${S3_BUCKET}/ollama/models/${ORI_TAG}/" \
  --no-progress
log "✓ ori:${ORI_TIER} cached."

log ""
log "═══ Setup complete ═══"
log "Models available:"
ollama list

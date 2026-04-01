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
#   ORI_S3_ENDPOINT  = https://s3api-eu-ro-1.runpod.io
#   ORI_S3_BUCKET    = s2uvk5nvun
#   ORI_S3_KEY       = user_3AAtmhUshdqnwQvcSYkFNrOQbF8
#   ORI_S3_SECRET    = rps_DK3KBF0UX3046F166E1QJ7KXC418SITKKKHHBBJVb6hyw1
#   ORI_TIER            = 4b  (or 16b — which tier this pod runs)

set -euo pipefail

S3_ENDPOINT="${ORI_S3_ENDPOINT:-https://s3api-eu-ro-1.runpod.io}"
S3_BUCKET="${ORI_S3_BUCKET:-s2uvk5nvun}"
S3_KEY="${ORI_S3_KEY:-}"
S3_SECRET="${ORI_S3_SECRET:-}"
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
# ── AWS CLI config — use env vars, no profile/credentials file needed ─────────
setup_aws() {
  export AWS_ACCESS_KEY_ID="$S3_KEY"
  export AWS_SECRET_ACCESS_KEY="$S3_SECRET"
  export AWS_DEFAULT_REGION="$REGION"
}

# s3_cp <s3-key> <local-path>  — download single object
s3_get() {
  aws s3api get-object \
    --bucket "$S3_BUCKET" --key "$1" \
    --endpoint-url "$S3_ENDPOINT" \
    "$2" > /dev/null
}

# s3_ls <prefix>  — returns 0 if any objects exist under prefix
s3_ls() {
  aws s3api list-objects-v2 \
    --bucket "$S3_BUCKET" --prefix "$1" --max-items 1 \
    --endpoint-url "$S3_ENDPOINT" \
    --query 'Contents[0].Key' --output text 2>/dev/null | grep -qv "^None$"
}

# s3_put <local-path> <s3-key>  — upload single file
s3_put() {
  aws s3api put-object \
    --bucket "$S3_BUCKET" --key "$2" \
    --body "$1" \
    --endpoint-url "$S3_ENDPOINT" > /dev/null
}

# s3_sync_up <local-dir> <s3-prefix>  — upload directory tree
s3_sync_up() {
  local local_dir="$1" prefix="$2"
  find "$local_dir" -type f | while read -r f; do
    rel="${f#$local_dir/}"
    aws s3api put-object \
      --bucket "$S3_BUCKET" --key "${prefix}/${rel}" \
      --body "$f" \
      --endpoint-url "$S3_ENDPOINT" > /dev/null
    echo "  ↑ ${prefix}/${rel}"
  done
}

# s3_sync_down <s3-prefix> <local-dir>  — download prefix into local dir
s3_sync_down() {
  local prefix="$1" local_dir="$2"
  aws s3api list-objects-v2 \
    --bucket "$S3_BUCKET" --prefix "$prefix" \
    --endpoint-url "$S3_ENDPOINT" \
    --query 'Contents[].Key' --output text | tr '\t' '\n' | while read -r key; do
    [[ -z "$key" || "$key" == "None" ]] && continue
    rel="${key#$prefix/}"
    dest="$local_dir/$rel"
    mkdir -p "$(dirname "$dest")"
    aws s3api get-object \
      --bucket "$S3_BUCKET" --key "$key" \
      --endpoint-url "$S3_ENDPOINT" \
      "$dest" > /dev/null
    echo "  ↓ $key"
  done
}

# ── Ollama ────────────────────────────────────────────────────────────────────
wait_for_ollama() {
  # Start Ollama if not already running
  if ! curl -sf http://localhost:11434/api/tags > /dev/null 2>&1; then
    log "Starting Ollama..."
    ollama serve &>/tmp/ollama.log &
  fi
  log "Waiting for Ollama to be ready..."
  for i in $(seq 1 60); do
    if curl -sf http://localhost:11434/api/tags > /dev/null 2>&1; then
      log "Ollama ready."
      return 0
    fi
    sleep 3
  done
  log "ERROR: Ollama did not start in time. Last log:"
  tail -20 /tmp/ollama.log 2>/dev/null || true
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
if s3_ls "ollama/models/${BASE_TAG}/"; then
  log "Cache hit — syncing $BASE_MODEL blobs from S3 ..."
  s3_sync_down "ollama/models/${BASE_TAG}" "$OLLAMA_MODELS_DIR"
  log "Sync complete. Verifying model ..."
  if ! model_exists "$BASE_MODEL"; then
    log "Blobs restored but manifest missing — pulling to register ..."
    ollama pull "$BASE_MODEL"
  fi
else
  log "No S3 cache — pulling $BASE_MODEL from registry (this takes a while)..."
  ollama pull "$BASE_MODEL"
  log "Pull complete. Caching blobs to S3 for future pods..."
  s3_sync_up "$OLLAMA_MODELS_DIR" "ollama/models/${BASE_TAG}"
  log "Blobs cached to S3."
fi

# Step 2: Download Modelfile from S3
MODELFILE_LOCAL="/tmp/Modelfile.ori-${ORI_TIER}"
log "Downloading Modelfile.ori-${ORI_TIER} from S3 ..."
s3_get "modelfiles/Modelfile.ori-${ORI_TIER}" "$MODELFILE_LOCAL"

# Step 3: Create ori model
log "Creating ori:${ORI_TIER} ..."
ollama create "ori:${ORI_TIER}" -f "$MODELFILE_LOCAL"
log "✓ ori:${ORI_TIER} ready"

# Step 4: Cache ori model back to S3
ORI_TAG="ori-${ORI_TIER}"
log "Caching ori:${ORI_TIER} blobs to S3 ..."
s3_sync_up "$OLLAMA_MODELS_DIR" "ollama/models/${ORI_TAG}"
log "✓ ori:${ORI_TIER} cached."

log ""
log "═══ Setup complete ═══"
log "Models available:"
ollama list

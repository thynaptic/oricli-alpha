#!/usr/bin/env bash
# One-time bucket initialisation for the Oricli sovereign S3 layer.
# Run after oricli-minio.service is healthy.
set -euo pipefail

MINIO_URL="http://localhost:9000"
MINIO_USER="oricli-admin"
MINIO_PASS="oricli-sovereign-2025"
ALIAS="oricli-local"

echo "[MinIO Init] Waiting for MinIO to be ready..."
until curl -sf "${MINIO_URL}/minio/health/live" >/dev/null 2>&1; do
  sleep 2
done
echo "[MinIO Init] MinIO is up."

# Install mc (MinIO client) if not present
if ! command -v mc &>/dev/null; then
  echo "[MinIO Init] Installing mc..."
  sudo curl -sSL https://dl.min.io/client/mc/release/linux-amd64/mc -o /usr/local/bin/mc
  sudo chmod +x /usr/local/bin/mc
fi

# Configure alias
mc alias set "${ALIAS}" "${MINIO_URL}" "${MINIO_USER}" "${MINIO_PASS}" --api s3v4

# Create buckets (idempotent)
mc mb --ignore-existing "${ALIAS}/oricli-state"
mc mb --ignore-existing "${ALIAS}/oricli-models"

echo "[MinIO Init] Buckets ready: oricli-state, oricli-models"

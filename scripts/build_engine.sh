#!/usr/bin/env bash
# scripts/build_engine.sh — Build the oricli-engine headless binary for distribution.
#
# Usage:
#   ./scripts/build_engine.sh                  # builds for current OS/arch
#   GOOS=linux GOARCH=amd64 ./scripts/build_engine.sh  # cross-compile for VPS
#
# The resulting binary is written to bin/oricli-engine (or bin/oricli-engine-<os>-<arch>
# when cross-compiling). Copy it to the target VPS and run directly.
#
# Minimal VPS setup after copying:
#   1. Install Ollama:  curl -fsSL https://ollama.ai/install.sh | sh
#   2. Pull a model:    ollama pull qwen3:1.7b
#   3. Create .env with ORICLI_SEED_API_KEY (generate: ./oricli-engine --gen-keys not needed; use any string)
#   4. Start:          ./oricli-engine
#   5. API is live:    curl http://localhost:8089/v1/models

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$REPO_ROOT"

GOOS="${GOOS:-$(go env GOOS)}"
GOARCH="${GOARCH:-$(go env GOARCH)}"
VERSION="${ORICLI_ENGINE_VERSION:-1.0.0}"
BUILD_TIME=$(date -u +"%Y-%m-%dT%H:%M:%SZ")

if [ "$GOOS/$GOARCH" = "$(go env GOOS)/$(go env GOARCH)" ]; then
    OUT="bin/oricli-engine"
else
    OUT="bin/oricli-engine-${GOOS}-${GOARCH}"
fi

echo "Building oricli-engine v${VERSION} for ${GOOS}/${GOARCH}..."

GOOS="$GOOS" GOARCH="$GOARCH" go build \
    -ldflags="-s -w -X main.Version=${VERSION} -X main.BuildTime=${BUILD_TIME}" \
    -o "$OUT" \
    ./cmd/oricli-engine/

echo "Binary: $OUT ($(du -sh "$OUT" | cut -f1))"
echo ""
echo "Deploy: scp $OUT user@your-vps:~/oricli-engine"
echo "Run:    ORICLI_SEED_API_KEY=your-key ./oricli-engine"

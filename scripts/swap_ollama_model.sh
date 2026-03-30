#!/usr/bin/env bash
# scripts/swap_ollama_model.sh
#
# Imports a fine-tuned GGUF into Ollama as 'oricli-sot:latest' and
# updates ORICLI_DEFAULT_MODEL in .env.
#
# Usage:
#   bash scripts/swap_ollama_model.sh /path/to/oricli-sot-q4.gguf
#
# Rollback:
#   ollama rm oricli-sot:latest
#   sed -i 's/^OLLAMA_MODEL=.*/OLLAMA_MODEL=qwen3:4b/' .env

set -euo pipefail

GGUF_PATH="${1:-}"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
ENV_FILE="$REPO_ROOT/.env"
MODEL_NAME="oricli-sot:latest"
MODELFILE_PATH="$REPO_ROOT/data/Modelfile.oricli-sot"

# ── Validate ──────────────────────────────────────────────────────────────────
if [[ -z "$GGUF_PATH" ]]; then
  echo "Usage: bash scripts/swap_ollama_model.sh /path/to/model.gguf"
  exit 1
fi

if [[ ! -f "$GGUF_PATH" ]]; then
  echo "Error: GGUF file not found: $GGUF_PATH"
  exit 1
fi

if ! command -v ollama &>/dev/null; then
  echo "Error: ollama not found in PATH"
  exit 1
fi

echo "[swap] GGUF:  $GGUF_PATH"
echo "[swap] Model: $MODEL_NAME"

# ── Write Modelfile ───────────────────────────────────────────────────────────
cat > "$MODELFILE_PATH" << EOF
FROM $GGUF_PATH

SYSTEM """You are Oricli's internal structured output engine.
When asked to produce JSON, respond ONLY with valid JSON — no markdown fences,
no explanation, no preamble. The JSON must conform exactly to the schema
described in the prompt. Never add extra fields."""

PARAMETER temperature 0.1
PARAMETER num_predict 512
PARAMETER stop "<|im_end|>"
PARAMETER stop "<|endoftext|>"
EOF

echo "[swap] Modelfile written to $MODELFILE_PATH"

# ── Import into Ollama ────────────────────────────────────────────────────────
echo "[swap] Importing into Ollama (this may take a minute)..."
ollama create "$MODEL_NAME" -f "$MODELFILE_PATH"

echo "[swap] Verifying..."
ollama show "$MODEL_NAME" | head -5

# ── Update .env ───────────────────────────────────────────────────────────────
if [[ -f "$ENV_FILE" ]]; then
  if grep -q "^OLLAMA_MODEL=" "$ENV_FILE"; then
    # Back up current value as comment
    OLD_MODEL=$(grep "^OLLAMA_MODEL=" "$ENV_FILE" | cut -d= -f2-)
    sed -i "s|^OLLAMA_MODEL=.*|OLLAMA_MODEL=$MODEL_NAME  # was: $OLD_MODEL|" "$ENV_FILE"
  else
    echo "OLLAMA_MODEL=$MODEL_NAME" >> "$ENV_FILE"
  fi
  echo "[swap] .env updated: OLLAMA_MODEL=$MODEL_NAME"
else
  echo "[swap] WARNING: .env not found at $ENV_FILE — update OLLAMA_MODEL manually"
fi

# ── Done ─────────────────────────────────────────────────────────────────────
echo ""
echo "✓ Model swapped: $MODEL_NAME"
echo ""
echo "Restart the server to apply:"
echo "  kill \$(pgrep -f oricli-go-v2)"
echo "  cd $REPO_ROOT && nohup bash -c 'source .env && ./bin/oricli-go-v2' >> /tmp/oricli.log 2>&1 &"
echo ""
echo "Rollback:"
echo "  ollama rm $MODEL_NAME"
echo "  sed -i 's/^OLLAMA_MODEL=.*/OLLAMA_MODEL=qwen3:4b/' $ENV_FILE"

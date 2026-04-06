#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
DEV_DIST_DIR="${ORI_DEV_DIST_DIR:-$ROOT_DIR/products/ori-dev-web/dist}"
DEV_HOST="${ORI_DEV_HOST:-127.0.0.1}"
DEV_PORT="${ORI_DEV_PORT:-5002}"

if [ ! -f "$DEV_DIST_DIR/index.html" ]; then
    echo "Missing ORI Dev build output at $DEV_DIST_DIR" >&2
    echo "Build the product repo first: cd $ROOT_DIR/products/ori-dev-web && npm run build" >&2
    exit 1
fi

exec python3 "$ROOT_DIR/scripts/serve_spa.py" "$DEV_DIST_DIR" --host "$DEV_HOST" --port "$DEV_PORT"

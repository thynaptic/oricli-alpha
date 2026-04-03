#!/bin/bash
# Oricli-Alpha UI Resync Script
# Builds the React frontend and ensures changes are live.

set -e

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
UI_DIR="$REPO_ROOT/ui_sovereignclaw"

echo "🚀 Building ORI Studio UI..."
cd "$UI_DIR"
npm run build

echo "✅ UI Build complete. Changes synced to static distribution."

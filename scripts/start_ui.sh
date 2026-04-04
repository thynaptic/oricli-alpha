#!/usr/bin/env bash
cd "$(dirname "$0")/.."
set -a
source .env
set +a
export MAVAIA_UI_PORT=5001
export MAVAIA_API_BASE="http://localhost:8089"
export PYTHONUNBUFFERED=1
exec .venv/bin/python3 -u ui_app.py

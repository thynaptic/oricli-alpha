#!/bin/bash
# Oricli-Alpha Pure-Go Hive Startup Script
set -e

# Use the smaller/faster Ollama model for sovereign chat
export OLLAMA_MODEL="${OLLAMA_MODEL:-ministral-3:3b}"

# 1. Start Go Backbone (Exec replaces the shell process)
echo "[Shell] Starting Pure-Go Backbone..."
exec /home/mike/Mavaia/bin/oricli-go-v2

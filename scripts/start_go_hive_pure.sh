#!/bin/bash
# Oricli-Alpha Pure-Go Hive Startup Script
set -e

# 1. Start Go Backbone (Exec replaces the shell process)
echo "[Shell] Starting Pure-Go Backbone..."
exec /home/mike/Mavaia/bin/oricli-go-v2

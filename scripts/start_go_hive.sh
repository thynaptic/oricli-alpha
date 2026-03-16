#!/bin/bash
# Oricli-Alpha Go Hive Startup Script
# Optimized for systemd management

# Ensure cleanup on failure
set -e

# 1. Start Python gRPC Worker in background
echo "[Shell] Starting Python gRPC Worker..."
source /home/mike/Mavaia/.venv/bin/activate
export ORICLI_WORKER_PORT=50051
export MAVAIA_ENABLE_HEAVY_MODULES=true
export MAVAIA_MODULE_IMPORT_TIMEOUT=300.0
python3 /home/mike/Mavaia/oricli_core/brain/grpc_worker.py &
PYTHON_PID=$!

# Handle cleanup of worker if script exits
trap "echo '[Shell] Stopping Python worker...'; kill $PYTHON_PID || true; exit" SIGINT SIGTERM EXIT

# 2. Wait for Python worker to start
echo "[Shell] Waiting for Python worker to initialize..."
sleep 10

# 3. Start Go Backbone (Exec replaces the shell process)
echo "[Shell] Starting Go Backbone..."
export ORICLI_WORKER_ADDR="localhost:50051"
exec /home/mike/Mavaia/bin/oricli-go

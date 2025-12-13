#!/bin/bash
# Mavaia Core - Server Launcher
# Starts both API and UI servers

set -euo pipefail

# Colors for professional output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
MAGENTA='\033[0;35m'
CYAN='\033[0;36m'
WHITE='\033[1;37m'
BOLD='\033[1m'
NC='\033[0m' # No Color

# Configuration
API_PORT="${MAVAIA_API_PORT:-8001}"
UI_PORT="${MAVAIA_UI_PORT:-5000}"
API_HOST="${MAVAIA_API_HOST:-0.0.0.0}"
UI_HOST="${MAVAIA_UI_HOST:-0.0.0.0}"
OPEN_BROWSER="${MAVAIA_OPEN_BROWSER:-true}"

# Get script directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
cd "$PROJECT_ROOT"

# Cleanup function
cleanup() {
    echo -e "\n${YELLOW}[INFO] Shutting down servers...${NC}"
    if [ -n "${API_PID:-}" ]; then
        kill "$API_PID" 2>/dev/null || true
        echo -e "${CYAN}  -> API server stopped${NC}"
    fi
    if [ -n "${UI_PID:-}" ]; then
        kill "$UI_PID" 2>/dev/null || true
        echo -e "${CYAN}  -> UI server stopped${NC}"
    fi
    exit 0
}

# Set trap for cleanup
trap cleanup SIGINT SIGTERM EXIT

# Banner
echo -e "${BOLD}${MAGENTA}"
echo "============================================================="
echo ""
echo -e "   ${WHITE}Mavaia Core - Server Launcher${MAGENTA}"
echo ""
echo "============================================================="
echo -e "${NC}"

# Check for venv (prioritize .venv over venv)
echo -e "${CYAN}[INFO] Checking environment...${NC}"
VENV_ACTIVATED=false
if [ -d ".venv" ]; then
    echo -e "${GREEN}  [OK] Found .venv, activating...${NC}"
    source .venv/bin/activate 2>/dev/null || {
        echo -e "${YELLOW}  [WARN] Venv activation had issues, continuing...${NC}"
    }
    VENV_ACTIVATED=true
elif [ -d "venv" ]; then
    echo -e "${GREEN}  [OK] Found venv (legacy), activating...${NC}"
    # Source activation script but don't fail if it has issues
    source venv/bin/activate 2>/dev/null || {
        echo -e "${YELLOW}  [WARN] Venv activation had issues, continuing...${NC}"
    }
    VENV_ACTIVATED=true
else
    echo -e "${YELLOW}  [WARN] No virtual environment found, using system Python${NC}"
fi

# Verify Python is working
if ! python3 --version > /dev/null 2>&1; then
    echo -e "${RED}  [ERROR] Python3 not found!${NC}"
    exit 1
fi

# Skip dependency check entirely - let servers fail if deps missing
echo -e "${CYAN}[INFO] Skipping dependency check (will verify when servers start)...${NC}"
echo -e "${YELLOW}  [NOTE] If servers fail to start, check dependencies with: pip install -e .${NC}"

# Port checking function
check_port() {
    local port=$1
    if command -v lsof > /dev/null 2>&1; then
        if lsof -Pi :$port -sTCP:LISTEN -t >/dev/null 2>&1; then
            return 1  # Port is in use
        fi
    elif command -v netstat > /dev/null 2>&1; then
        if netstat -an 2>/dev/null | grep -q ":$port.*LISTEN"; then
            return 1  # Port is in use
        fi
    fi
    return 0  # Port is available
}

# Start API server
echo -e "\n${BLUE}[INFO] Starting API server on port ${API_PORT}...${NC}"

# Check if port is available, find alternative if needed
ACTUAL_API_PORT=$API_PORT
if ! check_port $API_PORT; then
    echo -e "${YELLOW}  [WARN] Port ${API_PORT} is in use, finding alternative...${NC}"
    for port in $(seq $((API_PORT + 1)) $((API_PORT + 100))); do
        if check_port $port; then
            ACTUAL_API_PORT=$port
            echo -e "${CYAN}  [INFO] Using port ${ACTUAL_API_PORT} instead${NC}"
            break
        fi
    done
    if [ "$ACTUAL_API_PORT" = "$API_PORT" ]; then
        echo -e "${RED}  [ERROR] Could not find available port in range ${API_PORT}-$((API_PORT + 100))${NC}"
        exit 1
    fi
fi

# Clear old log file
> /tmp/mavaia_api.log

# Start server in background with unbuffered output
# Enable auto-port as fallback (server will also check)
PYTHONUNBUFFERED=1 python3 -u -m mavaia_core.api.server \
    --host "$API_HOST" \
    --port "$ACTUAL_API_PORT" \
    --log-level info \
    2>&1 | tee /tmp/mavaia_api.log &
API_PID=$!

# Log the PID for debugging
echo "$API_PID" > /tmp/mavaia_api.pid
echo -e "${CYAN}  [DEBUG] API server PID: $API_PID${NC}"

# Give it a moment to start
sleep 3

# Check if process is still running
if ! kill -0 "$API_PID" 2>/dev/null; then
    echo -e "${RED}  [ERROR] API server process died immediately${NC}"
    echo -e "${YELLOW}  [INFO] Server output:${NC}"
    cat /tmp/mavaia_api.log 2>/dev/null || echo "  (no output captured)"
    exit 1
fi

# Show initial log output
if [ -f /tmp/mavaia_api.log ] && [ -s /tmp/mavaia_api.log ]; then
    echo -e "${CYAN}  [INFO] Server output so far:${NC}"
    tail -5 /tmp/mavaia_api.log | sed 's/^/    /'
fi

# Wait for API to be ready (longer timeout for module discovery)
echo -e "${CYAN}  [INFO] Waiting for API server to start (this may take up to 30 seconds)...${NC}"
API_READY=false
for i in {1..60}; do
    # Try to connect to health endpoint (use actual port)
    if curl -s --max-time 1 "http://localhost:${ACTUAL_API_PORT}/health" > /dev/null 2>&1; then
        echo -e "${GREEN}  [OK] API server is ready${NC}"
        API_READY=true
        break
    fi
    # Check if process is still running
    if ! kill -0 "$API_PID" 2>/dev/null; then
        echo -e "${RED}  [ERROR] API server process died${NC}"
        echo -e "${YELLOW}  [INFO] Server output:${NC}"
        tail -30 /tmp/mavaia_api.log 2>/dev/null || echo "  (no output captured)"
        exit 1
    fi
    # Show progress every 5 seconds
    if [ $((i % 10)) -eq 0 ]; then
        echo -e "${CYAN}  [INFO] Still waiting... (${i}/30)${NC}"
    fi
    sleep 0.5
done

if [ "$API_READY" = "false" ]; then
    echo -e "${RED}  [ERROR] API server failed to start (timeout after 30 seconds)${NC}"
    echo -e "${YELLOW}  [INFO] Process status:${NC}"
    if kill -0 "$API_PID" 2>/dev/null; then
        echo -e "${YELLOW}    Process is running but not responding${NC}"
    else
        echo -e "${YELLOW}    Process is not running${NC}"
    fi
    echo -e "${YELLOW}  [INFO] Server output:${NC}"
    tail -50 /tmp/mavaia_api.log 2>/dev/null || echo "  (no output captured)"
    exit 1
fi

# Start UI server
echo -e "\n${MAGENTA}[INFO] Starting UI server on port ${UI_PORT}...${NC}"

# Check if UI port is available
ACTUAL_UI_PORT=$UI_PORT
if ! check_port $UI_PORT; then
    echo -e "${YELLOW}  [WARN] Port ${UI_PORT} is in use, finding alternative...${NC}"
    for port in $(seq $((UI_PORT + 1)) $((UI_PORT + 100))); do
        if check_port $port; then
            ACTUAL_UI_PORT=$port
            echo -e "${CYAN}  [INFO] Using port ${ACTUAL_UI_PORT} instead${NC}"
            break
        fi
    done
    if [ "$ACTUAL_UI_PORT" = "$UI_PORT" ]; then
        echo -e "${RED}  [ERROR] Could not find available UI port${NC}"
        exit 1
    fi
fi

# Clear old log file
> /tmp/mavaia_ui.log

# Start server in background (use actual API port)
# Use unbuffered Python output and ensure environment variables are set
export MAVAIA_API_BASE="http://localhost:${ACTUAL_API_PORT}"
export MAVAIA_UI_PORT=$ACTUAL_UI_PORT
PYTHONUNBUFFERED=1 python3 -u ui_app.py 2>&1 | tee /tmp/mavaia_ui.log &
UI_PID=$!

# Log the PID for debugging
echo "$UI_PID" > /tmp/mavaia_ui.pid
echo -e "${CYAN}  [DEBUG] UI server PID: $UI_PID${NC}"

# Give Flask more time to start (it can be slow)
sleep 3

# Show initial log output
if [ -f /tmp/mavaia_ui.log ]; then
    if [ -s /tmp/mavaia_ui.log ]; then
        echo -e "${CYAN}  [INFO] UI server output so far:${NC}"
        tail -10 /tmp/mavaia_ui.log | sed 's/^/    /'
    else
        echo -e "${YELLOW}  [WARN] UI server log is empty (Flask may not have started yet)${NC}"
    fi
fi

# Check if process is still running
if ! kill -0 "$UI_PID" 2>/dev/null; then
    echo -e "${RED}  [ERROR] UI server process died immediately${NC}"
    echo -e "${YELLOW}  [INFO] Server output:${NC}"
    cat /tmp/mavaia_ui.log 2>/dev/null || echo "  (no output captured)"
    exit 1
fi

# Wait for UI to be ready (increase timeout for Flask)
echo -e "${CYAN}  [INFO] Waiting for UI server to start (Flask can take 5-10 seconds)...${NC}"
UI_READY=false
for i in {1..40}; do
    # Try to connect to health endpoint (use actual UI port)
    # Try both /health and root / endpoint
    if curl -s --max-time 2 "http://localhost:${ACTUAL_UI_PORT}/health" > /dev/null 2>&1 || \
       curl -s --max-time 2 "http://localhost:${ACTUAL_UI_PORT}/" > /dev/null 2>&1; then
        echo -e "${GREEN}  [OK] UI server is ready${NC}"
        UI_READY=true
        break
    fi
    # Check if process is still running
    if ! kill -0 "$UI_PID" 2>/dev/null; then
        echo -e "${RED}  [ERROR] UI server process died${NC}"
        echo -e "${YELLOW}  [INFO] Server output:${NC}"
        tail -50 /tmp/mavaia_ui.log 2>/dev/null || echo "  (no output captured)"
        exit 1
    fi
    # Show progress every 5 seconds
    if [ $((i % 10)) -eq 0 ]; then
        echo -e "${CYAN}  [INFO] Still waiting... (${i}/40)${NC}"
        # Show recent log output
        if [ -f /tmp/mavaia_ui.log ] && [ -s /tmp/mavaia_ui.log ]; then
            echo -e "${CYAN}  [INFO] Recent UI server output:${NC}"
            tail -5 /tmp/mavaia_ui.log | sed 's/^/    /'
        else
            # Check if port is listening
            if command -v lsof > /dev/null 2>&1 && lsof -i :${ACTUAL_UI_PORT} > /dev/null 2>&1; then
                echo -e "${CYAN}  [INFO] Port ${ACTUAL_UI_PORT} is listening, but health check failing${NC}"
            fi
        fi
    fi
    sleep 0.5
done

if [ "$UI_READY" = "false" ]; then
    echo -e "${RED}  [ERROR] UI server failed to start (timeout after 20 seconds)${NC}"
    echo -e "${YELLOW}  [INFO] Process status:${NC}"
    if kill -0 "$UI_PID" 2>/dev/null; then
        echo -e "${YELLOW}    Process is running but not responding${NC}"
    else
        echo -e "${YELLOW}    Process is not running${NC}"
    fi
    echo -e "${YELLOW}  [INFO] Server output:${NC}"
    tail -50 /tmp/mavaia_ui.log 2>/dev/null || echo "  (no output captured)"
    exit 1
fi

# Success banner
echo -e "\n${BOLD}${GREEN}[SUCCESS] All servers are running${NC}\n"

echo -e "${WHITE}${BOLD}Access Points:${NC}"
echo -e "${CYAN}  API Server:    http://localhost:${ACTUAL_API_PORT}${NC}"
echo -e "${CYAN}  API Root:       http://localhost:${ACTUAL_API_PORT}/ (redirects to docs)${NC}"
echo -e "${CYAN}  API Docs:       http://localhost:${ACTUAL_API_PORT}/docs${NC}"
echo -e "${CYAN}  API Health:     http://localhost:${ACTUAL_API_PORT}/health${NC}"
if [ "$ACTUAL_API_PORT" != "$API_PORT" ]; then
    echo -e "${YELLOW}  [NOTE] Port changed from ${API_PORT} to ${ACTUAL_API_PORT} (port was in use)${NC}"
fi
echo -e "${CYAN}  UI Server:      http://localhost:${ACTUAL_UI_PORT}${NC}"
if [ "$ACTUAL_UI_PORT" != "$UI_PORT" ]; then
    echo -e "${YELLOW}  [NOTE] UI port changed from ${UI_PORT} to ${ACTUAL_UI_PORT} (port was in use)${NC}"
fi
echo -e "${YELLOW}  [NOTE] If you see 403 errors, try accessing /docs or /health directly${NC}"

echo -e "\n${WHITE}${BOLD}Monitoring:${NC}"
echo -e "${YELLOW}  API Logs: tail -f /tmp/mavaia_api.log${NC}"
echo -e "${YELLOW}  UI Logs:  tail -f /tmp/mavaia_ui.log${NC}"

# Open browser
if [ "$OPEN_BROWSER" = "true" ]; then
    echo -e "\n${MAGENTA}[INFO] Opening browser...${NC}"
    sleep 1
    if command -v open > /dev/null; then
        # macOS
        open "http://localhost:${ACTUAL_UI_PORT}" 2>/dev/null || true
    elif command -v xdg-open > /dev/null; then
        # Linux
        xdg-open "http://localhost:${ACTUAL_UI_PORT}" 2>/dev/null || true
    elif command -v start > /dev/null; then
        # Windows (Git Bash)
        start "http://localhost:${ACTUAL_UI_PORT}" 2>/dev/null || true
    else
        echo -e "${YELLOW}  [WARN] Could not auto-open browser${NC}"
        echo -e "${CYAN}  [INFO] Manually open: http://localhost:${ACTUAL_UI_PORT}${NC}"
    fi
fi

echo -e "\n${YELLOW}${BOLD}Press Ctrl+C to stop all servers${NC}\n"

# Wait for servers (they run in background, but we keep script alive)
wait

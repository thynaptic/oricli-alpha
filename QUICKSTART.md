# Quick Start Guide

## 🚀 One-Click Start (Recommended)

The easiest way to start everything:

```bash
./scripts/start_servers.sh
```

This will:
- ✅ Start both API and UI servers
- ✅ Use port 8001 for API (default)
- ✅ Use port 5000 for UI (default)
- ✅ Automatically open your browser
- ✅ Show beautiful status messages

## Starting the Servers (Manual)

### Prerequisites

1. **Activate the virtual environment:**
   ```bash
   source venv/bin/activate
   ```

2. **Verify dependencies are installed:**
   ```bash
   python3 scripts/check_dependencies.py
   ```

### Starting the API Server

**Option 1: Using the entry point (if package is installed)**
```bash
source venv/bin/activate
mavaia-server --port 8000
```

**Option 2: Using Python module**
```bash
source venv/bin/activate
python3 -m mavaia_core.api.server --port 8000
```

**Option 3: Using the startup script**
```bash
source venv/bin/activate
python3 scripts/start_server.py --port 8000
```

**Option 4: Using the convenience shell script**
```bash
./scripts/start_servers.sh api --port 8000
```

### Starting the UI Server

**Option 1: Direct execution**
```bash
source venv/bin/activate
python3 ui_app.py
```

**Option 2: Using the startup script**
```bash
source venv/bin/activate
python3 scripts/start_ui.py
```

**Option 3: Using the convenience shell script**
```bash
./scripts/start_servers.sh ui
```

### Common Issues

#### "Module not found" errors

Make sure you've activated the virtual environment:
```bash
source venv/bin/activate
```

#### "Port already in use" errors

Use a different port:
```bash
# API server
python3 -m mavaia_core.api.server --port 8001

# UI server
MAVAIA_UI_PORT=5001 python3 ui_app.py
```

#### Server starts but immediately exits

Check for errors in the output. Common causes:
- Missing dependencies (run `pip install -e .`)
- Port conflicts
- Import errors in modules

#### UI can't connect to API

Make sure:
1. API server is running first
2. `MAVAIA_API_BASE` environment variable points to the correct API URL
3. Both servers are accessible

### Environment Variables

**API Server:**
- `MAVAIA_API_KEY` - API key for authentication
- `MAVAIA_REQUIRE_AUTH` - Set to "true" to require authentication

**UI Server:**
- `MAVAIA_API_BASE` - Base URL for API (default: http://localhost:8000)
- `MAVAIA_API_KEY` - API key for authentication
- `MAVAIA_UI_PORT` - UI server port (default: 5000)
- `MAVAIA_UI_HOST` - UI server host (default: 0.0.0.0)
- `MAVAIA_UI_ATTACHMENT_MB` - Max attachment size in MB (default: 5)

### Testing the Servers

**Test API server:**
```bash
curl http://localhost:8000/health
```

**Test UI server:**
```bash
curl http://localhost:5000/health
```

**Test API endpoints:**
```bash
# List models
curl http://localhost:8000/v1/models

# List modules
curl http://localhost:8000/v1/modules

# Get metrics
curl http://localhost:8000/v1/metrics

# Get health status
curl http://localhost:8000/v1/health/modules
```


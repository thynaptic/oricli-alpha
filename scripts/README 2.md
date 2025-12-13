# Mavaia Scripts

## 🚀 start_servers.sh

The **one-and-done** script to launch everything!

### Features

- ✨ **Modern UI** - Beautiful colors and emojis
- 🚀 **Auto-start** - Starts both API and UI servers
- 🌐 **Auto-browser** - Opens your browser automatically
- ⚙️ **Smart defaults** - API on 8001, UI on 5000
- 🛡️ **Error handling** - Graceful shutdown and cleanup
- 📊 **Status monitoring** - Real-time server health checks

### Usage

```bash
# Simple - just run it!
./scripts/start_servers.sh
```

### Environment Variables

Customize behavior with environment variables:

```bash
# Change API port (default: 8001)
MAVAIA_API_PORT=9000 ./scripts/start_servers.sh

# Change UI port (default: 5000)
MAVAIA_UI_PORT=6000 ./scripts/start_servers.sh

# Disable auto-browser opening
MAVAIA_OPEN_BROWSER=false ./scripts/start_servers.sh

# Change host bindings
MAVAIA_API_HOST=127.0.0.1 MAVAIA_UI_HOST=127.0.0.1 ./scripts/start_servers.sh
```

### What It Does

1. ✅ Checks and activates virtual environment
2. ✅ Verifies all dependencies are installed
3. ✅ Starts API server on port 8001
4. ✅ Waits for API to be ready
5. ✅ Starts UI server on port 5000
6. ✅ Waits for UI to be ready
7. ✅ Opens browser automatically
8. ✅ Shows beautiful status dashboard
9. ✅ Handles graceful shutdown (Ctrl+C)

### Logs

- API logs: `/tmp/mavaia_api.log`
- UI logs: `/tmp/mavaia_ui.log`

View logs in real-time:
```bash
tail -f /tmp/mavaia_api.log
tail -f /tmp/mavaia_ui.log
```

### Stopping

Press `Ctrl+C` to gracefully stop all servers.

## Other Scripts

### check_dependencies.py

Check if all required dependencies are installed:

```bash
python3 scripts/check_dependencies.py
```

### start_server.py

Start only the API server:

```bash
python3 scripts/start_server.py --port 8001
```

### start_ui.py

Start only the UI server:

```bash
python3 scripts/start_ui.py
```


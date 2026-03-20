# Plan: Sovereign VDI (Virtual Device Interface) Integration

## Objective
Implement a Go-native Virtual Device Interface (VDI) for Oricli-Alpha. This moves her beyond the restricted `Gosh` sandbox, giving her the "Hands" (OS control, file management) and "Eyes" (Browser automation, DOM reading, Screenshots) needed to function as a true Personal Control Plane ("OpenClaw correctly").

## Architecture

We will implement the VDI natively in Go to maintain sub-millisecond execution and sovereign independence, rather than relying entirely on external Node/Python bridges.

### 1. The VDI Substrate (`pkg/vdi/browser.go` & `pkg/vdi/system.go`)
*   **Browser Automation**: Use `chromedp` (a pure Go Chrome Debugging Protocol implementation) to launch and control a local headless/headed browser. No Node.js dependencies required.
*   **System Orchestration**: Secure wrappers around Go's `os` and `os/exec` packages for host-level file manipulation and command execution.

### 2. The VDI Toolbox (`pkg/vdi/tools.go`)
Register specific VDI capabilities directly into Oricli's `tools.Registry`:
*   `vdi_browser_goto(url)`: Navigate to a page.
*   `vdi_browser_scrape()`: Extract clean, readable text from the current DOM.
*   `vdi_browser_click(selector)`: Interact with page elements.
*   `vdi_browser_type(selector, text)`: Fill out forms.
*   `vdi_sys_read(path)`: Read a file from the host OS.
*   `vdi_sys_write(path, content)`: Write to the host OS.
*   `vdi_sys_exec(cmd)`: Run a host-level terminal command.

### 3. VDI Manager (`pkg/vdi/manager.go`)
A central state manager that holds the active Chrome context and OS context, ensuring that browser sessions persist across multiple agent tool calls (so she doesn't open/close the browser on every click).

### 4. Integration with Sovereign Engine
*   Initialize the `vdi.Manager` inside `SovereignEngine`.
*   Register the VDI tools into the engine's `Toolbox` at boot.
*   When the agent generates a `tool_call` for `vdi_*`, the orchestrator executes the native Go function, and the result is fed back into the cognitive loop.

## Implementation Steps

### Phase 1: Core VDI Packages
1.  Add `github.com/chromedp/chromedp` to `go.mod`.
2.  Create `pkg/vdi/manager.go` to handle Chrome context and lifecycle.
3.  Create `pkg/vdi/browser.go` with Chromedp actions (navigate, scrape, click).
4.  Create `pkg/vdi/system.go` for OS file/exec wrappers.

### Phase 2: Tool Bridging
1.  Create `pkg/vdi/tools.go` to define the `ToolDefinition` schemas for the LLM.
2.  Map the schema arguments to the underlying Go methods.

### Phase 3: Engine Integration
1.  Update `pkg/cognition/sovereign.go` to initialize the VDI manager.
2.  Update `cmd/backbone/main.go` to handle graceful shutdown of the VDI browser.

### Phase 4: Verification
1.  Test `vdi_browser_goto` and `vdi_browser_scrape` via the API `/v1/swarm/run` endpoint to prove she can "see" the web dynamically.

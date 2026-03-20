# Plan: Model Context Protocol (MCP) Client Integration

## Objective
Integrate Model Context Protocol (MCP) support into Oricli-Alpha, allowing her to act as an MCP client. This enables autonomous tool discovery and resource bridging from external MCP servers (like GitHub, Slack, or local data sources), bringing the system closer to the "OpenClaw" vision.

## 1. MCP Client Logic (`pkg/connectors/mcp/`)
Implement a Go-native MCP client that supports the stdio transport:
*   **Transport**: Uses `os/exec` to spawn MCP server processes and communicates via `stdin`/`stdout` pipes.
*   **Protocol**: Implements JSON-RPC 2.0 message exchange.
*   **Handshake**: Sends `initialize` and `notifications/initialized`.
*   **Discovery**: Fetches tool definitions via `tools/list`.
*   **Execution**: Invokes tools via `tools/call` and maps results back to Oricli.

## 2. MCP Manager (`pkg/connectors/mcp/manager.go`)
A central registry for multiple MCP servers:
*   **Config**: Reads `oricli_core/mcp_config.json` (OpenClaw format).
*   **Lifecycle**: Manages server processes (Start, Stop, Restart on failure).
*   **Health**: Periodically checks server responsiveness.

## 3. Tool Bridge (`pkg/tools/mcp_bridge.go`)
Automatically registers discovered MCP tools into Oricli's `Toolbox`:
*   Converts MCP tool schemas into `tools.ToolDefinition`.
*   Wraps the `tools/call` RPC into a standard `tools.Handler`.

## 4. Integration Steps

### Phase 1: Core Protocol
1.  Create `pkg/connectors/mcp/types.go` with JSON-RPC and MCP structs.
2.  Implement the stdio client in `pkg/connectors/mcp/client.go`.

### Phase 2: Manager & Discovery
1.  Implement the `MCPManager` to handle multiple servers.
2.  Implement the bridge to register tools in `pkg/tools/registry.go`.

### Phase 3: Sovereign Engine Wiring
1.  Update `SovereignEngine` to initialize the `MCPManager` at boot.
2.  Trigger a "Global Tool Refresh" once MCP discovery is complete.

### Phase 4: Verification
1.  Add a test `github` MCP server config.
2.  Verify tool discovery in the logs.
3.  Test a real tool call (e.g., `github_search_repos`) via the API.

## Verification & Testing
*   **Unit Tests**: Test JSON-RPC marshalling and pipe communication.
*   **Integration Test**: Use a mock MCP server to verify the `initialize` -> `tools/list` -> `tools/call` flow.
*   **Build**: Ensure `oricli-go-v2` compiles with the new `mcp` package.

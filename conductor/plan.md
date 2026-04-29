# Copilot SDK Migration (Embedded Client)

## Background & Motivation
The current Oracle implementation shells out to the `copilot` and `codex` CLI tools for every query. This approach suffers from latency (process fork/exec overhead), loss of context fidelity (flattening chat history into a single string), and manual intent routing. Migrating to the official **GitHub Copilot SDK for Go** allows us to leverage a persistent `copilot --acp` headless server, native Intent Matching for Custom Agents, native Custom Skills integration, native Image Input without relying on legacy `codex` wrappers, and powerful session management features.

## Scope & Impact
- **Modules Affected:** `pkg/oracle/*`, `pkg/api/server_v2.go`, `cmd/oricli-engine/main.go`
- **Dependencies:** Add `github.com/github/copilot-sdk/go`
- **Impact:** Replaces all `exec.Command("copilot", ...)` and `exec.Command("codex", ...)` calls with persistent JSON-RPC TCP connections to the embedded SDK server.

## Proposed Solution (Embedded Client)
Instead of deploying a separate systemd daemon, `oricli-engine` will manage the headless Copilot server as an embedded child process. 
1. **Daemon Lifecycle Manager:** A new manager in `pkg/oracle/manager.go` will spawn `copilot --acp --port 8090` when the Sovereign Engine boots, and kill it gracefully on shutdown.
2. **SDK Client & Sessions:** `pkg/oracle/oracle.go` will instantiate a `copilot.NewClient()` and connect to the local server. Queries will be mapped to `Session.Send()` calls.
3. **Session Persistence:** We will bind the SDK's `SessionID` to Oricli's `CurrentSessionID`. This allows Copilot to natively maintain conversation history across turns (saving to `~/.copilot/session-state/`) rather than Oricli flattening and resending the entire history every prompt.
4. **Custom Agents & Skills:** The SDK `SessionConfig` will be populated by scanning `.github/agents/*.agent.md` to map our existing agent definitions to the SDK's `CustomAgents` slice. The `SkillDirectories` config will point directly to `.github/skills` and potentially `oricli_core/skills`.
5. **Image Input:** The `RouteImageReasoning` logic will stop shelling out to `codex`. Instead, the `server_v2.go` handler will detect image URLs/paths and append them as `Attachment` (Type: "file" or "blob") payloads to the SDK request, taking advantage of the SDK's built-in `capabilities.SupportsVision` checks.
6. **MCP Servers Integration:** Instead of passing messy `--allow-tool` or `--add-github-mcp-tool` flags to the CLI, we will natively define `MCPServers` in the SDK `SessionConfig`.
7. **Steering and Queueing:** For normal interactions, messages will be sent with `Mode: "enqueue"`. If the user issues a course-correction (e.g., "Stop, do X instead"), we will dispatch with `Mode: "immediate"` to steer the agent mid-turn.

## Phased Implementation Plan

### Phase 1: SDK Integration & Daemon Lifecycle
- Update `go.mod` to include `github.com/github/copilot-sdk/go`.
- Create `pkg/oracle/manager.go` to handle starting/stopping the `copilot --acp --port 8090` child process.
- Hook the manager's `Start()` and `Stop()` methods into `cmd/oricli-engine/main.go`.

### Phase 2: Refactoring Oracle Query & Stream
- Rewrite `pkg/oracle/oracle.go` to replace `queryCopilot` and `ChatStream` with SDK-native implementations.
- Parse `.github/agents/` to inject `CustomAgents` with `Description` fields optimized for the SDK's native Intent Matching.
- Inject `SkillDirectories: []string{".github/skills"}` into the `SessionConfig`.
- Map `CurrentSessionID` to the SDK's session resume/create logic to leverage **Session Persistence**.

### Phase 3: Multimodal & MCP
- Remove `queryCodex` entirely.
- Update `pkg/api/server_v2.go` to parse user prompts for image references and convert them to SDK `Attachment` blocks.
- Configure local/remote MCP servers explicitly through the `MCPServers` map in `SessionConfig` rather than relying on CLI args.

### Phase 4: Clean Up & Verification
- Remove the old string-flattening logic in `buildPrompt`. 
- Ensure `ConvertMsgs` is aligned with SDK patterns (though less necessary if history is handled by Session Persistence).
- Test intent routing: ensure the SDK automatically selects `ori-reasoner` or `go_engineer` based on the prompt.

## Verification & Testing
- **Daemon Lifecycle:** Verify `copilot --acp` starts on engine boot and terminates cleanly when the engine shuts down.
- **Intent Routing:** Query with a Go concurrency question and verify the SDK invokes the Go Custom Agent.
- **Session Persistence:** Disconnect and reconnect a session, verifying the model remembers context without Oricli resending it.
- **Vision Test:** Send a diagram and verify the SDK successfully attaches and reasons over the image.

## Migration & Rollback
- Keep the legacy `exec.Command` logic as `queryCopilotLegacy` and `streamCopilotLegacy` behind a feature flag (`ORICLI_USE_SDK=false`) during the rollout to allow an immediate fallback if the SDK server fails in production.
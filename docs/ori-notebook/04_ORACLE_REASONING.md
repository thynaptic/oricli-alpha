# Oracle Orchestration (GitHub Copilot SDK)

The **Oracle** is Oricli-Alpha's high-compute reasoning lane. It handles complex multi-turn logic, architecture planning, and deep repo investigation that exceeds the capabilities of the local Ollama models.

As of v11.1.0, the Oracle has migrated from a CLI-based wrapper to a **Native Go SDK Integration** with an embedded runtime.

## 🏗️ Architecture

```
┌───────────────────────────┐
│      Oricli Engine        │
│  ┌─────────────────────┐  │
│  │   Oracle Manager    │  │── Start/Stop ──┐
│  └─────────────────────┘  │                │
│             │             │                ▼
│  ┌─────────────────────┐  │      ┌───────────────────┐
│  │  Copilot Go SDK     │──┼──────┤ copilot --acp :8090 │
│  │     Client          │  │      │ (Headless Daemon)   │
│  └─────────────────────┘  │      └───────────────────┘
└─────────────┬─────────────┘
              ▼
    [Native Intent Matching]
    [Session Persistence]
    [Multi-Modal Vision]
```

### 1. Embedded Daemon Lifecycle
The Oracle is powered by a headless Copilot server running in **Agent Client Protocol (ACP)** mode.
- **Managed by**: `pkg/oracle/manager.go`
- **Port**: `8090` (default)
- **Lifecycle**: Spawns as a child process when the Oricli Engine boots; terminates gracefully on shutdown.

### 2. Native SDK Integration
Oricli uses the official `github.com/github/copilot-sdk/go` to communicate with the daemon via JSON-RPC.
- **Location**: `pkg/oracle/oracle.go`
- **Advantage**: Eliminates process fork/exec overhead and maintains high-fidelity message structures (native system/user/assistant roles).

---

## 🚀 Key Features

### Custom Agents (Intent Matching)
Oricli maps its specialized module personas to the SDK's **Custom Agents**. 
- **Source**: `.github/agents/*.agent.md`
- **Dynamic Selection**: The Copilot runtime natively analyzes the user's prompt against agent descriptions to pick the best tool-lane (e.g., automatically routing a concurrency question to the `go_engineer` agent).

### Session Persistence
Oricli binds its internal `SessionID` to the Copilot SDK session.
- **Storage**: State is persisted by the SDK in `~/.copilot/session-state/{sessionID}/`.
- **Resume**: Reconnecting to a session restores the conversation history and the agent's current `plan.md` state, enabling consistent multi-day goal execution.

### Real-Time Steering
The SDK allows users to course-correct an agent while it is processing a task.
- **Enqueue Mode**: Default behavior for new prompts.
- **Immediate Mode (Steering)**: Triggered by keywords like "Stop," "Actually," or "Wait." This injects the message immediately into the active reasoning loop to pivot the agent's direction.

### Multi-Modal (Vision)
The Oracle handles image-based reasoning natively.
- **Detection**: The engine scans prompts for absolute filesystem paths ending in image extensions (`.png`, `.jpg`, etc.).
- **Attachments**: Detected images are attached to the SDK `MessageOptions` as `file` blocks, allowing the Oracle to reason over diagrams or screenshots.

---

## 🛠️ Configuration & Development

### Environment Variables
- `ORACLE_COPILOT_MODEL_LIGHT`: Model for standard chat (Default: `gpt-5-mini`).
- `ORACLE_COPILOT_MODEL_HEAVY`: Model for deep reasoning (Default: `claude-sonnet-4.6`).
- `ORACLE_COPILOT_MODEL_RESEARCH`: Model for analysis (Default: `gpt-5.4`).

### Extending Agents
To add a new lane to the Oracle, create a Markdown file in `.github/agents/` following the YAML frontmatter pattern:
```markdown
---
name: my-new-agent
description: Expert at X, Y, and Z.
tools: [read, edit, execute]
---
Instructions for the agent...
```

### Debugging
Oracle logs are prefixed with `[Oracle]` or `[Oracle:Manager]` in the standard Oricli output. If the daemon fails to start, verify that the `copilot` CLI is available in the system `PATH`.

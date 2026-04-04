# ORI Home — Desktop Client Spec

**Version:** 1.0  
**Stack:** Electron + React + Vite  
**Backend:** GLM API (`https://glm.thynaptic.com/v1`) — OpenAI-compatible  

---

## Vision

ORI Home is the sovereign desktop client for the ORI intelligence engine. It mirrors the layout philosophy of ORI Studio (web) but is purpose-built for desktop — denser chrome, keyboard shortcuts, and native OS integration. It is **not** a browser wrapper; it is a first-class desktop application.

---

## Layout Architecture

```
┌─────┬──────────────┬────────────────────────────────────────┐
│     │              │  Top Navbar                            │
│Icon │  Contextual  │  [Agent Persona ▼]    ● Private&Local  │
│Rail │  Pane        ├────────────────────────────────────────┤
│     │  (slide-out) │                                        │
│     │              │         Main Canvas                    │
│     │              │                                        │
│     │              │                                        │
├─────┤              │                                        │
│ ⚙️  │              │                                        │
│ 🌙  │              │                                        │
│ 👤  │              │                                        │
└─────┴──────────────┴────────────────────────────────────────┘
```

### 1. Icon Rail (far-left, fixed, slim)
Pure iconography — no labels. Clicking an icon toggles the Contextual Pane for that section.

| Icon | Section | Contextual Pane Content |
|---|---|---|
| 🏠 | Home | Recent chats list |
| 📁 | Spaces | Space list + create button |
| ⚡ | Workflows | Saved workflow list |
| 📋 | Board | — (opens full Board canvas directly) |
| 🔌 | Connections | MCP / integration list |

**Bottom of rail (always visible):**
- Theme toggle (light/dark)
- Settings
- Sign out / account

### 2. Contextual Pane (slide-out)
Renders conditionally based on the active rail icon. Slides in from the left over the main canvas (does not push/reflow content). Width: ~260px.

### 3. Top Navbar
Fixed to the top of the Main Canvas.

- **Left:** Agent Persona dropdown — hot-swap the active agent profile  
  (Default ORI, API Designer, Benchmark Analyst, Architect, Security Drone, etc.)
- **Right:** `● Private & local` pulsing green status indicator — confirms the connection is live to the local/sovereign backend (not a cloud proxy)

### 4. Main Canvas
Context-driven. Renders the active view:
- Chat thread (Home / Spaces)
- Kanban board (Workflows)
- Full board (Board)
- Config panel (Connections)

---

## Spaces

**Concept:** Grouped chat threads with shared persistent memory. Equivalent to "Projects" in Claude Desktop but backed by ORI's sovereign RAG stack.

### UX
- Each Space has: name, icon (emoji), color tag, description
- Contextual Pane lists all Spaces; clicking one expands to show its chat threads
- "New Space" button at top of pane
- "New Chat" inside a Space creates a thread scoped to that Space

### Memory Architecture
- Each Space maps 1:1 to a **chromem-go collection** (namespace: `space:<space_id>`)
- All chats, uploaded files, and notes within a Space are embedded into its collection
- On every message, retrieval is scoped to the active Space's collection — automatic contextual memory with no user configuration
- Spaces are isolated from each other by default (no cross-Space retrieval unless explicitly enabled)

### Data Model
```json
{
  "id": "space_abc123",
  "name": "RunPod Ghost Cluster",
  "icon": "🖥️",
  "color": "#C9A84C",
  "description": "All research and chats related to async pod orchestration",
  "created_at": "2026-04-04T00:00:00Z",
  "rag_collection": "space:space_abc123"
}
```

### API Calls
- `GET /v1/spaces` — list Spaces
- `POST /v1/spaces` — create Space
- `DELETE /v1/spaces/:id` — delete Space
- `GET /v1/spaces/:id/threads` — list chat threads in Space
- `POST /v1/chat/completions` with `metadata.space_id` — scoped RAG retrieval

---

## Workflows (Kanban)

**Concept:** Visual work order board for orchestrating ORI agents. Maps to the backbone's Dynamic Graph Execution (DGE) engine. Drag-and-drop cards between columns to queue, run, and track multi-agent tasks.

### UX
- Full-canvas Kanban board rendered in the Main Canvas when "Workflows" is active
- **Columns:** `Backlog → Queued → Running → Review → Done`
- **Cards = Work Orders:** each card represents a task assigned to one or more agents
- Dragging a card to `Queued` triggers execution on the backbone via DGE
- Card status auto-updates in real-time via SSE as the backbone processes
- Agent avatar(s) displayed on each card

### Card Schema
```json
{
  "id": "wf_card_xyz",
  "title": "Research competitor pricing",
  "agent": "ORI Architect",
  "inputs": {
    "prompt": "...",
    "tools": ["web_search", "web_fetch"]
  },
  "dependencies": [],
  "status": "backlog",
  "result": null,
  "created_at": "2026-04-04T00:00:00Z"
}
```

### D&D Implementation
Use **dnd-kit** (`@dnd-kit/core` + `@dnd-kit/sortable`):
- Lighter than react-beautiful-dnd
- Actively maintained
- Works cleanly in Electron's Chromium env
- Supports keyboard navigation out of the box

### Column → Backend Mapping
| Column | Action |
|---|---|
| Backlog | Saved locally, not submitted |
| Queued | `POST /v1/workflows/run` — fires DGE DAG |
| Running | SSE stream active, card shows live progress |
| Review | Execution complete, result displayed on card |
| Done | Archived, result persisted |

### Saved Workflows
- A "Workflow" is a named template of cards + dependency graph (DAG)
- Listed in the Contextual Pane when the ⚡ rail icon is active
- "New Workflow" spawns a blank Kanban board
- Workflows are saveable, shareable (export as JSON), and re-runnable

---

## Agent Persona System

Agent Personas are profile compositions that change ORI's behavior, system prompt, tool access, and model routing.

### Built-in Personas
| Persona | Focus | Default Tools |
|---|---|---|
| Default ORI | General intelligence | All |
| API Designer | REST/GraphQL API design | code_gen, web_fetch |
| Benchmark Analyst | Evaluation & metrics | data_analysis, math |
| Architect | System design | diagram_gen, web_search |
| Security Drone | Threat modeling & audit | code_review, search |

### Hot-swap
Persona is selectable from the Top Navbar dropdown — takes effect on the next message. Mid-conversation switching is allowed.

---

## Self-Registration (First Boot)

ORI Home auto-provisions its own GLM API key on first launch:

```javascript
// app.whenReady() — runs once, gates on stored key absence
const storedKey = await keystore.get("glm_api_key")
if (!storedKey) {
  const res = await fetch("https://glm.thynaptic.com/v1/app/register", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      registration_token: process.env.ORI_APP_REG_TOKEN,
      app_name: "ORI Home",
      device_id: await getMachineId(),
    }),
  })
  const { api_key } = await res.json()
  await keystore.set("glm_api_key", api_key)
}
```

Key is scoped to `runtime:chat` only. Stored in the OS keychain via `electron-store` (encrypted). Shown to user in Settings > Account if they need it.

---

## Connection Status Indicator

The `● Private & local` indicator in the Top Navbar reflects the health of the GLM connection:

| State | Color | Label |
|---|---|---|
| Connected, local | 🟢 pulse | Private & local |
| Connected, cloud fallback | 🟡 pulse | Cloud |
| Disconnected | 🔴 solid | Offline |

Determined by a lightweight `GET /v1/health` ping every 30s.

---

## Tech Stack Summary

| Layer | Choice | Reason |
|---|---|---|
| Shell | Electron | Cross-platform, same stack as Claude Desktop |
| UI | React + Vite | Existing team skillset, fast HMR |
| State | Zustand | Already in use in ORI Studio |
| D&D | dnd-kit | Lightweight, Electron-compatible |
| Styling | CSS vars + inline (no Tailwind) | Consistent with thynaptic.com design system |
| Storage | electron-store (encrypted) | API key + local prefs |
| IPC | Electron contextBridge | Renderer ↔ main process comms |
| Backend | GLM API (8089 / glm.thynaptic.com) | ORI sovereign backbone |

---

## Immediate Build Priorities

1. **Layout refactor** — Icon Rail + Contextual Pane + Top Navbar structure
2. **Spaces CRUD** — create, list, open, delete; RAG collection wiring
3. **Kanban board** — dnd-kit columns, card creation, status rendering
4. **Agent Persona dropdown** — top navbar, profile swap on message
5. **Connection status indicator** — /v1/health ping, color states
6. **Self-registration** — first-boot key provisioning (backend already live)

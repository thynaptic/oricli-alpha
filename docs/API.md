# Oricli-Alpha API Reference

**Version:** 2.10.0 — Finalized MCI (OpenClaw Ready)  
**Maintainer:** Thynaptic Research

This is the single source of truth for the Oricli-Alpha API. Use it to integrate external applications, configure AI agents, or operate the system programmatically.

---

## Infrastructure

```
External Client
      │
      ▼  HTTPS (TLS — Cloudflare Origin Cert)
oricli.thynaptic.com  ──►  Caddy (port 443)
chat.thynaptic.com    ──►  Caddy (port 443)
      │
      ▼  HTTP (internal only)
127.0.0.1:8089  ──►  Go Backbone (ServerV2 / Gin)
      │
      ├─ GET  /v1/health            → public
      ├─ GET  /v1/ws                → WebSocket Hub (Real-time State)
      └─ POST /v1/*                 → authMiddleware → auth.Service (Argon2id)
```

| Property | Value |
|---|---|
| **Production URL** | `https://oricli.thynaptic.com` |
| **Internal port** | `8089` |
| **Protocol** | HTTPS externally, plain HTTP on localhost |
| **Auth** | Bearer token (`glm.<prefix>.<secret>` format) |

---

## Real-Time State (WebSockets)

Oricli-Alpha streams her internal state changes via `GET /v1/ws`. 

### Event Types:
| Event | Payload Description |
|---|---|
| `resonance_sync` | Real-time ERI, ERS, and Musical Key. |
| `sensory_sync` | Real-time Hex colors, opacities, and pulse rates for UI rendering. |
| `health_sync` | Substrate diagnostics (CPU/RAM) and cognitive health. |
| `audio_sync` | Base64-encoded audio (WAV) for Affective Voice Synthesis. |
| `curiosity_sync` | Live updates on autonomous epistemic foraging targets. |
| `reform_proposal` | Proactive code refactor candidates for manual approval. |

---

## Endpoints

### `POST /v1/chat/completions`
OpenAI-compatible chat endpoint with Sovereign extensions.

**Parameters:**
*   `profile`: Pass the filename of a `.ori` manifest to hot-swap her soul.
*   `stream`: Supports Server-Sent Events (SSE).

---

## Sovereign Toolbox (VDI & MCP)

Discovered tools are automatically injected into the system prompt.

### 1. Browser VDI (`vdi_browser_*`)
*   `vdi_browser_goto(url)`: Navigate headless session.
*   `vdi_browser_scrape()`: Extract clean DOM text.
*   `vdi_visual_click(description)`: **Vision-in-the-Loop** coordinate click using Qwen2.5-VL.

### 2. System VDI (`vdi_sys_*`)
*   `vdi_sys_read(path)`: Read host files (subject to Ring-0 security).
*   `vdi_sys_exec(command)`: Execute bash commands.
*   `vdi_sys_index(path)`: Recursively map directory to COGS graph.

### 3. Temporal Cron (`sov_schedule_*`)
*   `sov_schedule_task(operation, params, delay, interval)`: Set autonomous future intents.

---

## Affective Memory (COGS)

Every entity in Oricli's memory graph stores an **Affective Anchor** (Valence, Arousal, Resonance). She uses this to proactively pivot her personality when topics with high historical distress or success resurface.

---

*Oricli-Alpha — Sovereign Intelligence, Orchestrated at Scale.*  
*Source: `pkg/api/server_v2.go`, Caddy config `/etc/caddy/Caddyfile`*

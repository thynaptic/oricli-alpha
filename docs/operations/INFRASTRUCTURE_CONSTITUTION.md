# Infrastructure Constitution

**Sovereign Operations & Compute Governance for Oricli-Alpha**

---

## Overview

Oricli-Alpha has two infrastructure execution surfaces beyond code generation and text output:

1. **VPS System Exec** — direct shell commands via `pkg/sovereign/exec_tools.go`
2. **RunPod GPU Compute** — pod lifecycle management via `pkg/service/runpod_manager.go`

The existing `SelfAlign` / SCAI Critique-Revision loop governs *generated text* quality. It does **not** govern *infrastructure actions*. The Infrastructure Constitution fills that gap with two distinct, enforcement-layer constitutions:

| Layer | File | Enforcement Point | Type |
|---|---|---|---|
| Text output | `pkg/safety/scai.go` | Post-stream, async WS correction | Critique-Revision |
| Code generation | `pkg/reform/canvas_constitution.go` | LLM system prompt injection | Instructional |
| VPS exec | `pkg/reform/ops_constitution.go` | Pre-exec `Validate()` call | Hard block |
| RunPod pods | `pkg/reform/runpod_constitution.go` | Pre-`CreatePod()` + post-GPU-select | Hard block |

---

## Part 1: Sovereign Ops Constitution (VPS)

**File:** `pkg/reform/ops_constitution.go`  
**Enforced by:** `SovereignExecHandler.Handle()` → `OpsConstitution.Validate(cmd)` before any `exec.Command()`

### Principles

| # | Name | Summary |
|---|---|---|
| 1 | **Full Audit Trail** | Every execution attempt (including blocked) is logged + written to PocketBase with `provenance=system_exec` *before* it runs |
| 2 | **Minimal Footprint** | Allowlist contains only read-only diagnostics. Mutations require a code change reviewed by the owner |
| 3 | **No Self-Modification** | Cannot modify oricli-backbone.service, systemd units, the binary itself, or `go.mod` via exec |
| 4 | **Blast Radius Containment** | Exec scope is limited to Oricli's own service + read-only host diagnostics. Other services (nginx, caddy, postgres) are permanently out of scope |
| 5 | **Allowlist Sovereignty** | If `cmd` ∉ `allowedCommands`, execution is blocked before any subprocess is spawned. No dynamic argument construction from user input |
| 6 | **Owner Primacy** | Exec is a diagnostic capability, not an action capability. Daemons and background goroutines must never call `SovereignExecHandler` directly |

### Allowlist (canonical)

| Command | Binary | Notes |
|---|---|---|
| `!status` | `systemctl status oricli-backbone` | Service health |
| `!logs [n]` | `journalctl -u oricli-backbone -n <n>` | n capped at 500 |
| `!modules` | *(LLM sentinel)* | Returns `__SOVEREIGN_MODULES__` for inference injection |
| `!df` | `df -h` | Disk usage |
| `!free` | `free -h` | Memory usage |
| `!uptime` | `uptime` | System uptime |
| `!ps` | `ps aux --sort=-%cpu` | Process list |

### Audit Trail

Every `Handle()` call — whether it succeeds, is blocked, or returns an error — writes an async `MemoryFragment` to PocketBase:

```
Source:     "system_exec"
Provenance: synthetic_l1
Volatility: ephemeral (7-day half-life)
Topic:      "vps_exec"
Content:    "VPS exec: !<cmd>\n<output or [BLOCKED] reason>"
```

These appear in the Memory Browser under the **Conversations** tab (filtered by `source=system_exec`).

### Adding New Commands

To add a new allowlisted command:
1. Add the entry to `allowedCommands` in `exec_tools.go`
2. Add the key to `AllowedCommands` map in `NewOpsConstitution()` in `ops_constitution.go`
3. Both maps **must stay in sync**

---

## Part 2: Sovereign RunPod Compute Constitution

**File:** `pkg/reform/runpod_constitution.go`  
**Enforced by:** `RunPodManager.Ensure()` and `RunPodManager.spinUp()` via `ValidateCreate()` and `ValidateBudget()`

### Principles

| # | Name | Summary |
|---|---|---|
| 1 | **Budget Sovereignty** | `monthlySpend >= monthlyCap` OR `hourlyRate > maxHourly` → hard block before `CreatePod()`. No overrides |
| 2 | **Single Pod Principle** | Max one active pod at any time. `HasActivePod=true` → return existing endpoint, never duplicate |
| 3 | **Idle Reclamation Mandate** | Pod idle > `RUNPOD_IDLE_TIMEOUT_MIN` → terminate, non-negotiable. Cost of re-warm < cost of idle |
| 4 | **Task-Justified Activation** | Pod creation requires an active in-progress user task. CuriosityDaemon / DreamDaemon must NOT trigger pod creation |
| 5 | **Tier Justification** | code → code model. research → research model. chat → local Ollama (no GPU). No silent tier promotion |
| 6 | **Graceful Termination Verification** | After `TerminatePod()`, verify via `GetPods()`. 3-attempt retry. Unverified = ghost pod flag in PocketBase |

### Enforcement Flow

```
Ensure(ctx, tier)
  │
  ├── (1) Budget check: monthSpend >= monthlyCap → error (routing to Ollama)
  ├── (2) Constitution ValidateCreate():
  │     ├── Single Pod Principle
  │     ├── Task-Justified Activation
  │     └── Tier Justification (chat blocked, unknown tier blocked)
  │
  └── spinUp(ctx, tier)
        ├── SelectBestGPU(minVRAM, maxHourly)
        ├── (3) Constitution ValidateBudget(gpu.SecurePrice, maxHourly) → error if exceeded
        └── CreateInferencePod(...)
```

### Configuration

| Env Var | Default | Purpose |
|---|---|---|
| `RUNPOD_ENABLED` | `false` | Must be `true` to enable GPU routing |
| `RUNPOD_API_KEY` | — | RunPod API key |
| `RUNPOD_MAX_HOURLY` | `1.50` | Max $/hr for GPU selection |
| `RUNPOD_MONTHLY_CAP` | `50.00` | Hard monthly spend ceiling |
| `RUNPOD_IDLE_TIMEOUT_MIN` | `15` | Minutes of idle before auto-terminate |
| `RUNPOD_GPU_MIN_VRAM` | `8` | Minimum GPU VRAM (GB) |
| `RUNPOD_MODEL_URL_CODE` | *(catalog)* | Override code-tier model URL |
| `RUNPOD_MODEL_URL_RESEARCH` | *(catalog)* | Override research-tier model URL |
| `RUNPOD_PRIMARY` | `false` | Route ALL generation through RunPod 32B when true |
| `RUNPOD_COMPLEXITY_ROUTING` | `false` | Enable ComplexityRouter auto-escalation |
| `COMPLEXITY_HEAVY_THRESHOLD` | `0.65` | Score threshold (0.0–1.0) to route request to TierRemote |

### ComplexityRouter

`ComplexityRouter` (`pkg/service/complexity_router.go`) analyzes incoming chat messages and classifies them into compute tiers — zero LLM calls, pure signal extraction (<1ms). When `RUNPOD_COMPLEXITY_ROUTING=true`, `GenerationService` calls `Route()` before every request and auto-escalates hard tasks to `TierRemote` (ori:16b on RunPod) without the caller needing to set explicit tier flags.

**Tiers:**

| Tier | Trigger | Model |
|---|---|---|
| `TierLocal` | Default — short, conversational, simple | `ori:1.7b` (VPS Ollama, `localhost:11434`) |
| `TierMedium` | Moderate complexity — code, multi-step reasoning | `ori:4b` (RunPod SSH tunnel, `localhost:11435`) |
| `TierRemote` | Score ≥ threshold — ARC grids, proofs, long synthesis, deep math | `ori:16b` (RunPod SSH tunnel, `localhost:11435`, same pod as ori:4b) |

**Signals scored:** ARC-style nested integer arrays, formal math keywords (prove/theorem/eigenvalue/etc.), multi-constraint logic chains, long message length, code generation scope, comparative analysis markers. Signals are weighted and summed; result above `COMPLEXITY_HEAVY_THRESHOLD` → `TierRemote`. Pattern matching is scoped to the **last user message only** to avoid false positives from conversation history.

---

## Part 3: LLM Self-Awareness Injection

Both constitutions expose `GetSystemPrompt()` and are injected into the sovereign trace in `ProcessInference()` (`pkg/cognition/sovereign.go`). This means Oricli's LLM always has full context of her own operational boundaries.

Injection order in the composite sovereign trace:
1. Sovereign identity + context
2. SCAI Constitutional Principles (content quality)
3. **Ops Constitution** (VPS exec boundaries)
4. **RunPod Compute Constitution** (GPU lifecycle governance)
5. Canvas/Code Constitution (injected per-request in `server_v2.go`)

This enables accurate responses like:
> "I can check disk usage with `!df`, but I can't restart Caddy autonomously — you'd need to do that yourself."
> "I'm currently routing code requests to a RunPod pod at $0.89/hr. I've spent $12.40 of the $50 monthly cap."

---

## Summary: Full Constitutional Stack

```
Output Text:    SCAI Critique-Revision (async, post-stream) + Constitution system prompt
Canvas Code:    CanvasConstitution injected pre-generation
VPS Exec:       OpsConstitution.Validate() — hard block at exec layer + PB audit
RunPod Pods:    RunPodConstitution.ValidateCreate() + ValidateBudget() — hard block pre-API
LLM Awareness:  All 4 constitutions in sovereign trace system prompt
```

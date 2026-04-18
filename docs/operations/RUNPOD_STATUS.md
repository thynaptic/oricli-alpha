# RunPod Status

RunPod is no longer part of ORI's main product path.

Current direction:

- ORI is the system layer.
- Oracle is the default reasoning lane.
- local Ollama remains a utility and fallback lane.
- RunPod is optional legacy R&D infrastructure.

## What This Means

RunPod is not required for:

- ORI Studio
- ORI Home
- ORI Dev
- public GLM API usage
- ORI MCP

The live runtime now prefers Oracle for meaningful reasoning instead of remote GPU escalation.

## Current Runtime Truth

- Shared ORI runtime uses Oracle as the primary reasoning path.
- The live backbone service does not require `RUNPOD_ENABLED=true`.
- The product can run without the RunPod tunnel or remote Ollama path.

## Keep vs Remove

Keep for now:

- [pkg/service/runpod_manager.go](/home/mike/Mavaia/pkg/service/runpod_manager.go)
- [pkg/service/runpod_vision_manager.go](/home/mike/Mavaia/pkg/service/runpod_vision_manager.go)
- [pkg/connectors/runpod](/home/mike/Mavaia/pkg/connectors/runpod)
- [pkg/reform/runpod_constitution.go](/home/mike/Mavaia/pkg/reform/runpod_constitution.go)
- [scripts/introspect_runpod_schema.py](/home/mike/Mavaia/scripts/introspect_runpod_schema.py)
- [scripts/runpod_bridge.py](/home/mike/Mavaia/scripts/runpod_bridge.py)
- [scripts/runpod_config.json](/home/mike/Mavaia/scripts/runpod_config.json)
- [query_gpu.py](/home/mike/Mavaia/query_gpu.py)

Reason:
These are useful as archived R&D and a possible future high-control fine-tuning lane.

Treat as archive/cleanup candidates later:

- stale RunPod mentions in onboarding and quickstart docs
- unused service units such as `ori-pod-tunnel.service`
- old benchmark or monitor artifacts that only describe the previous routing model

## Operational Recommendation

Unless there is a specific fine-tuning or private-compute reason, do not treat RunPod as part of the core ORI plan.

Use RunPod only when one of these becomes true:

- a customer requires hosted but dedicated model control
- fine-tuning shows a measurable product improvement
- long-run economics clearly beat Oracle for a defined workload
- a privacy or deployment requirement rules Oracle out

## Manual Cleanup

If the RunPod SSH tunnel is still enabled on the VPS, disable it manually:

```bash
sudo systemctl disable --now ori-pod-tunnel.service
```

Then verify:

```bash
systemctl status ori-pod-tunnel.service --no-pager
```

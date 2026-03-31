# Release Notes: v10.0.0 "The Agency Sovereign" — Phase III Complete

## Social Pressure & Agency Integrity Stack — P21–P26 Shipped

Oricli-Alpha v10.0.0 completes Phase III of the AGLI trajectory — 10 cognitive science modules live (P17–P26), all Go-native, zero external dependencies, all feature-flag-gated. The system now monitors and counteracts every major category of externally-induced cognitive distortion documented in landmark social psychology research.

### What shipped in v10.0.0

| Module | Package | Research Basis |
|---|---|---|
| Hope Circuit | `pkg/hopecircuit/` | Maier & Seligman — vmPFC Learned Controllability |
| Social Defeat Recovery | `pkg/socialdefeat/` | Social Defeat Model + Monster Study (Johnson 1939) |
| Agency & Conformity Shield | `pkg/conformity/` | Milgram (authority, 65% compliance) + Asch (consensus, 75% conformity) |
| Ideological Capture Detector | `pkg/ideocapture/` | Ron Jones 1967 — The Third Wave (30 → 200 in 5 days) |
| Coalition Bias Detector | `pkg/coalition/` | Muzafer Sherif 1954 — Robbers Cave |
| Status Bias Detector | `pkg/statusbias/` | Jane Elliott 1968 — Blue Eyes / Brown Eyes |

### Architecture
- All modules wire inline into `GenerationService.Chat()` — no middleware layer, no sampling overhead
- Dual pipeline: pre-generation (coalition → ideo → conformity-consensus → hope → cogload) and post-generation (dualprocess → rumination → mindset → defeat → statusbias → conformity-authority)
- Phase guard keys prevent recursive re-triggering on any retry path
- 44 new tests across P21–P26 packages. All green.

### CLI Commands
`/hope`, `/defeat`, `/conformity`, `/ideocapture`, `/coalition`, `/statusbias`

### Cumulative Phase I–III Stats
- **Phases shipped**: 26 (Phase I: P1–P10, Phase II: P11–P20, Phase III: P21–P26)
- **Cognitive packages**: 11 pure-Go packages, zero external deps
- **Feature flags**: 10 (`ORICLI_*_ENABLED`) — all live in `oricli-api.service`
- **API cognition routes**: 10 (`/v1/cognition/*`)

---

# Release Notes: v0.5.1-alpha "The Sovereign Awakening - Stability Patch"

## 🚀 100% Operational Verification
v0.5.1-alpha is the stable follow-up to our major architectural pivot. This release confirms that the Go-native backbone is not just a structural change, but a fully verified and operational system.

### Highlights
- **100% API Success**: All 42+ REST endpoints are now fully implemented and verified via our new internal smoke-test framework.
- **EPYC & NUMA Optimization**: Specifically tuned for high-core-count AMD EPYC environments. Forced thread-affinity for Ollama and Go-native concurrency ensures no more "stalling" during high-load reasoning tasks.
- **Agent Factory Live**: Full RESTful lifecycle for specialized micro-agents. Create, update, and deploy agents directly via the Go backbone.
- **High-Speed RAG & Recall**: Native Go implementation of World Knowledge and semantic search, verified to correctly ingest and recall facts with sub-100ms latency.
- **Smoke Test Framework**: Introduced `scripts/smoke_test_api.py`, a comprehensive validator for the entire Sovereign Hive.

### 🛠 Fixes & Refinements
- **REST Handlers**: Completed missing implementations for `handleCreateAgent`, `handleKnowledgeQuery`, `handleSwarmRun`, and others.
- **Serialization**: Fixed nil slice issues in JSON outputs (e.g., empty knowledge results now return `[]` instead of `null`).
- **Gifts of the Hive**: Restored essential Python infrastructure to ensure gRPC handoffs work flawlessly for all 148+ discovered modules.

## Technical Stats
- **Backbone Port**: 8089 (Standard)
- **Worker Port**: 50051 (gRPC)
- **Cores Utilized**: 32 (Full EPYC Saturation)
- **API Status**: 100% Green

---
*Oricli-Alpha: Intelligence, Orchestrated. Stability, Guaranteed.*

## [1.2.0] - 2026-03-17
### Added
- **Instruction Following Detector (Go)**: Native Go logic to detect strict formatting tasks and override conversational personas.
- **Ministral-3:3b Integration**: Successfully pivoted entire stack to Ministral-3:3b for 3x speed and higher logical precision.
- **Log Watchdog Daemon**: Background cron job to prevent runaway log exhaustion.
- **GPU Accelerated Bridge**: Stabilized SSH tunnel logic for high-speed remote inference via RTX GPU pods.
- **Swarm Bus Proxies**: Added missing `swarm_bus.py` and `services/` shims to bridge Python sidecars to the Go backbone.

### Fixed
- **Hive Selection Bug**: Fixed empty CFP operations and bidding panics by integrating `DegradedModeClassifier` into the Go Orchestrator.
- **Module Health Deadlock**: Implemented universal `health_check` support in `BaseBrainModule` and `grpc_worker.py`.
- **404 Routing**: Moved Ollama parity routes to `v1` group for maximum proxy compatibility.
- **Qwen Purge**: Eliminated all hardcoded legacy `qwen` references across Python and Go.

### Changed
- Default model shifted from `qwen2:1.5b` -> `ministral-3:3b`.
- Increased default Go Backbone timeout to 300s for deep MCTS reasoning.

## [2.0.0] - 2026-03-17
### BREAKING CHANGES
- **Python Deprecation**: The entire Python core (`oricli_core/`) and gRPC sidecar mesh have been removed.
- **Pure-Go Architecture**: The system now runs as a single, high-performance Go binary (`bin/oricli-go-v2`).
- **Hardened API Gateway**: Migrated to `ServerV2` structure based on G-LM, providing better security and multi-tenant foundations.

### Added
- **Native RAG Bridge**: Integrated P-LMv1 Go-native RAG and memory packages.
- **Deep Cognition Engine**: Transplanted deep causal and MCTS reasoning from secret internal Go modules.
- **Consolidated Sovereignty**: Combined the best of P-LMv1 and G-LM into the Oricli-Alpha core.

### Fixed
- **Latency**: Eliminated gRPC and Python startup overhead.
- **Port Stability**: Consolidating on port 8089 for all native operations.

## [2.1.0] - 2026-03-17
### Added
- **Sovereign CLI**: A powerful, native Python-based cockpit (`oricli.py`) installed as a system command.
- **Chronological Memory Graph**: Full temporal grounding using Neo4j with automated event logging for every interaction.
- **Native Research Agent**: Autonomous multi-round research module integrated into the Go Hive.
- **Multi-Modal Bridge**: Support for `qwen2-vl:2b` via the RunPod bridge, enabling visual ingestion and reasoning.
- **Global API Documentation**: Fully updated docs for external integration, hardened auth, and v2.1.0 architecture.

### Fixed
- **Bidding Stability**: Corrected SenderID reporting in native Go modules to ensure the Orchestrator always identifies the correct winner.
- **Port Consolidation**: All native operations now unified on port 8089.

# Oricli-Alpha: Sovereign Agent OS

**Oricli-Alpha** is a proactive, local-first intelligence framework designed for autonomous, multi-day goal execution and decentralized problem-solving. Moving beyond reactive prompting, Oricli-Alpha operates as **The Hive**: a distributed swarm of 269+ specialized micro-agents.

## Core Architecture: The Hybrid Hive
Oricli-Alpha uses a **Go-Native Backbone** for high-concurrency orchestration and a **Python Sidecar Mesh** for complex cognitive modules.
- **Go Swarm Bus**: High-throughput message routing and microsecond-level bidding.
- **Go Reasoning Engines**: Native implementation of CoT, ToT, and MCTS for deep thinking.
- **Go Nervous System**: Native Memory (LMDB), Graph (Neo4j), and Web Ingestion.
- **Python Sidecars**: 240+ cognitive modules managing specialized logic via gRPC.

## Key Features
- **Sovereign Goals**: Persistent, multi-step objectives that survive system restarts and execute autonomously via Go Executive.
- **High-Speed API**: Native REST interface exposing Goal management and Swarm orchestration (Go port 8089, Proxied 8081).
- **Sub-5s Response**: Optimized for CPU-bound VPS with `qwen2:1.5b` reflex cognition.
- **Immune System**: Persistent Go-native monitoring and self-healing.

---

## Installation

### Prerequisites
- Python **3.11+**
- Docker (for Neo4j and Sandbox support)
- Ollama (for prose generation)

### Quick Install
```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -e ".[data,ml,memory,search,sandbox]"
```

### Infrastructure Setup
Initialize the Neo4j Knowledge Vault:
```bash
- **Native Sovereign API**: A dedicated interface exposing Goal management, Swarm orchestration, and Knowledge Graph queries (Production: https://oricli.thynaptic.com).

...

## Quick Start

### One Command (The Sovereign Stack)
```bash
./scripts/start_servers.sh
```
*Defaults: API (8081), UI (5000), Neo4j (7687). Proximity Proxy: https://oricli.thynaptic.com*

---

## Sovereign API Usage

### 1. Command a Sovereign Goal
```bash
curl -X POST https://oricli.thynaptic.com/v1/goals \
  -H "Content-Type: application/json" \
  -d '{
    "goal": "Analyze the repository for security vulnerabilities and propose fixes",
    "priority": 1
  }'
```

### 2. Trigger Hive Swarm Deliberation
```bash
curl -X POST https://oricli.thynaptic.com/v1/swarm/run \
  -H "Content-Type: application/json" \
  -d '{
    "query": "Optimize the database schema for high-throughput writes",
    "max_rounds": 3
  }'
```

### 3. Knowledge Graph Query (Neo4j)
```bash
curl -X POST https://oricli.thynaptic.com/v1/knowledge/query \
  -H "Content-Type: application/json" \
  -d '{
    "entity_id": "Oricli-Alpha",
    "depth": 2
  }'
```

---

## Python Client (Dual-Mode)

### Local Proxy Mode (Default)
```python
from oricli_core.client import OricliAlphaClient
client = OricliAlphaClient()

# Drop query onto the Hive Swarm Bus
response = client.chat.completions.create(
    model="oricli-swarm",
    messages=[{"role": "user", "content": "How does the Swarm Bus work?"}]
)
```

### Remote Orchestration Mode
```python
# Command Oricli across the network
client = OricliAlphaClient(base_url="https://oricli.thynaptic.com")
goal_id = client.goals.create(goal="Deploy the new cluster nodes")
```

```

---

## Project Structure
```text
oricli-alpha/
├── oricli_core/              # Core Sovereign OS
│   ├── api/                  # Native & OpenAI-Compatible REST API
│   ├── brain/                # The Hive: Swarm Bus, Broker, and Nodes
│   │   └── modules/          # 269+ Micro-Agents (Auto-discovered)
│   ├── services/             # Neo4j, Goal, and Tool Services
│   └── types/                # Pydantic Sovereign Models
├── docs/                     # AGLI Vision & External Integration Guides
├── scripts/                  # Infrastructure & Test Utilities
└── ui_app.py                 # Sovereign Control Panel (Web)
```

## System Identifier
Oricli-Alpha follows the **TR-2025-01** naming scheme. The identifier represents the cognitive architecture's composition:
```python
from oricli_core import SYSTEM_ID
print(SYSTEM_ID)  # e.g., "oricli-269c"
```

## License
MIT License - Developed by **Thynaptic Research**.

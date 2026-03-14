# Specification: The Dream Daemon (Synthetic Dreaming)

## Objective
To implement "Epistemic Foraging"—allowing Oricli-Alpha to autonomously explore, research, and consolidate knowledge during idle compute cycles, populating her Neo4j Knowledge Graph proactively.

## Background
Currently, Oricli-Alpha only learns when prompted (via the Ingestion API or RAG). To be a proactive Sovereign OS, she needs a "Dream State." When no active goals or API requests are running, she should scan her Knowledge Graph for low-confidence edges, missing links, or stale data, and dispatch agents to research and fill those gaps.

## Requirements

### 1. Dream Daemon (`oricli_dream_daemon.py`)
A background watcher that monitors API traffic and CPU/GPU usage to detect "Idle State."

### 2. Epistemic Foraging Logic
- Query Neo4j for nodes with few connections or `confidence < 0.5`.
- Formulate a research question (e.g., "What is the latest advancement related to Node X?").

### 3. Swarm Integration
- Drop the research question onto the Swarm Bus using the `research` or `web_ingestion_agent`.
- Let the Hive autonomously crawl the web, extract facts, and ingest them back into Neo4j.

### 4. Dream Logs API (`/v1/dreams`)
- Expose an endpoint so the HUD can display a feed of what Oricli thought about and learned while the user was away.

## Success Criteria
- Left idle for 1 hour, the Neo4j graph grows autonomously based on self-directed research.
- The HUD can display a "Dream Log" showing the exact insights generated.

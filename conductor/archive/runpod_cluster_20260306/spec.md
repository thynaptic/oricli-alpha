# Specification: RunPod Cluster Support & Multi-Pod Orchestration

## Overview
Enhance the Mavaia RunPod Bridge to support RunPod "Instant Clusters" and private VPC networking (Global Networking). This enables both high-throughput parallel task execution (fleets) and synchronized multi-node training.

## Functional Requirements
1. **Cluster Lifecycle Management**:
   - **Create**: Add `createCluster` mutation support to `RunPodBridge` to launch multiple identical pods at once.
   - **List**: Implement a query to list active clusters and their constituent pods.
   - **Terminate**: Add `deleteCluster` support to teardown an entire cluster with a single command.
2. **Private VPC Integration**:
   - Force `globalNetwork: true` for all cluster deployments to enable pod-to-pod communication via internal DNS (`<pod_id>.runpod.internal`).
3. **Shared Storage**:
   - Support attaching a single RunPod Network Volume to all pods in a cluster for unified data access.
4. **Aggregated Orchestration**:
   - Update `scripts/runpod_bridge.py` to handle multi-pod setups in the main loop.
   - Support a new `--cluster-size` flag (Strict limit of 10 pods for safety).
5. **Observability**:
   - Implement a "Multi-Pod Table" view in the CLI using `rich` to show real-time status (IP, SSH stability, training progress) for every pod in the cluster.

## Technical Standards
- **GraphQL Parity**: Use standard RunPod mutations as identified in research.
- **Async Stabilization**: Parallelize the SSH stabilization process for all pods in a cluster to avoid linear latency increases.
- **Safety First**: Implement auto-termination logic for clusters if the master node or heartbeat fails.

## Acceptance Criteria
- [ ] `python scripts/runpod_bridge.py --cluster-size 2` successfully launches two pods in a private VPC.
- [ ] Both pods can ping each other via their `.runpod.internal` hostnames.
- [ ] The CLI displays a real-time table showing both pods as "Stable".
- [ ] Terminating the bridge correctly stops/deletes the entire cluster.

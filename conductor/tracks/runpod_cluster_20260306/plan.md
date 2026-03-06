# Implementation Plan: RunPod Cluster Support

**Phase 1: Bridge Core Extension (GraphQL)**
Goal: Implement the low-level cluster mutations and queries in the `RunPodBridge` class.
- [x] Task: Implement Cluster Mutations
    - [x] Add `create_cluster` method using the `createCluster` mutation.
    - [x] Add `delete_cluster` method using the `deleteCluster` mutation.
    - [x] Add `get_clusters` query method.
- [x] Task: TDD - Cluster API Verification
    - [x] Write unit tests with mocked API responses to verify mutation/query payload structure.
- [x] Task: Conductor - User Manual Verification 'Phase 1: Bridge Core Extension' (Protocol in workflow.md)

**Phase 2: Multi-Pod Orchestration Logic**
Goal: Update the main bridge loop to handle multiple pods and parallel setup.
- [x] Task: Implement Cluster CLI Flags
    - [x] Add `--cluster-size` (1-10) and `--vpc` flags to `argparse`.
- [x] Task: Async Pod Stabilization
    - [x] Refactor `setup_pod_env` and `ensure_mavaia_installed` to use `threading` or `asyncio` for parallel pod setup.
    - [x] Ensure Global Networking (VPC) flag is correctly passed.
- [x] Task: TDD - Multi-Pod Setup Logic
    - [x] Verify that multiple pod IDs are correctly captured and processed in parallel.
- [x] Task: Conductor - User Manual Verification 'Phase 2: Multi-Pod Orchestration' (Protocol in workflow.md)

**Phase 3: Observability (Multi-Pod UI)**
Goal: Implement the real-time cluster status table.
- [x] Task: Implement Multi-Pod Table View
    - [x] Create a `rich.Table` based status view that refreshes dynamically.
    - [x] Show individual pod IPs, SSH status, and training heartbeat.
- [x] Task: Conductor - User Manual Verification 'Phase 3: Observability' (Protocol in workflow.md)

**Phase 4: Safety & Teardown**
Goal: Ensure reliable cluster-wide cleanup.
- [x] Task: Cluster-Aware Cleanup
    - [x] Update `terminate` logic to handle deleting entire clusters.
    - [x] Implement master-heartbeat check: if master pod dies, terminate the cluster.
- [x] Task: Conductor - User Manual Verification 'Phase 4: Safety & Teardown' (Protocol in workflow.md)

## Phase: Review
- [x] Task: Apply review suggestions 458c94c

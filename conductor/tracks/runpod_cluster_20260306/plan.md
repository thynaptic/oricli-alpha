# Implementation Plan: RunPod Cluster Support

**Phase 1: Bridge Core Extension (GraphQL)**
Goal: Implement the low-level cluster mutations and queries in the `RunPodBridge` class.
- [ ] Task: Implement Cluster Mutations
    - [ ] Add `create_cluster` method using the `createCluster` mutation.
    - [ ] Add `delete_cluster` method using the `deleteCluster` mutation.
    - [ ] Add `get_clusters` query method.
- [ ] Task: TDD - Cluster API Verification
    - [ ] Write unit tests with mocked API responses to verify mutation/query payload structure.
- [ ] Task: Conductor - User Manual Verification 'Phase 1: Bridge Core Extension' (Protocol in workflow.md)

**Phase 2: Multi-Pod Orchestration Logic**
Goal: Update the main bridge loop to handle multiple pods and parallel setup.
- [ ] Task: Implement Cluster CLI Flags
    - [ ] Add `--cluster-size` (1-10) and `--vpc` flags to `argparse`.
- [ ] Task: Async Pod Stabilization
    - [ ] Refactor `setup_pod_env` and `ensure_mavaia_installed` to use `threading` or `asyncio` for parallel pod setup.
    - [ ] Ensure Global Networking (VPC) flag is correctly passed.
- [ ] Task: TDD - Multi-Pod Setup Logic
    - [ ] Verify that multiple pod IDs are correctly captured and processed in parallel.
- [ ] Task: Conductor - User Manual Verification 'Phase 2: Multi-Pod Orchestration' (Protocol in workflow.md)

**Phase 3: Observability (Multi-Pod UI)**
Goal: Implement the real-time cluster status table.
- [ ] Task: Implement Multi-Pod Table View
    - [ ] Create a `rich.Table` based status view that refreshes dynamically.
    - [ ] Show individual pod IPs, SSH status, and training heartbeat.
- [ ] Task: Conductor - User Manual Verification 'Phase 3: Observability' (Protocol in workflow.md)

**Phase 4: Safety & Teardown**
Goal: Ensure reliable cluster-wide cleanup.
- [ ] Task: Cluster-Aware Cleanup
    - [ ] Update `terminate` logic to handle deleting entire clusters.
    - [ ] Implement master-heartbeat check: if master pod dies, terminate the cluster.
- [ ] Task: Conductor - User Manual Verification 'Phase 4: Safety & Teardown' (Protocol in workflow.md)

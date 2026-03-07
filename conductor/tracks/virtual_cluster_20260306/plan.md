# Implementation Plan: Async Virtual Clustering

## Phase 1: Parallel Provisioning
- [ ] Refactor the creation loop in `scripts/runpod_bridge.py` to use a `ThreadPoolExecutor` for `create_pod` calls.
- [ ] Implement unique naming for each pod in the cluster (`{alias}_{index}`).
- [ ] Ensure `cloudType: SECURE` is used for all pods to maintain on-demand pricing.

## Phase 2: Orchestration Refactoring
- [ ] Move the `cluster_id` logic to a `virtual_cluster_pods` list.
- [ ] Update the wait-for-ready loop to monitor the status of multiple independent pods instead of a single cluster ID.

## Phase 3: Synchronized Execution
- [ ] Update the `remote_train` and `remote_benchmark` logic to launch tasks on all pods in the virtual cluster.
- [ ] Refine the watchdog to ensure it performs S3 syncs for all members.

## Phase 4: Verification
- [ ] Launch a virtual cluster of 2 pods.
- [ ] Verify that both pods initialize correctly from S3 and start their tasks.
- [ ] Verify that `terminate` correctly kills all members of the virtual cluster.

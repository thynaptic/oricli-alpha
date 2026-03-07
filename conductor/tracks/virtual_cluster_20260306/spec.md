# Specification: Async Virtual Clustering

## Objective
To simulate cluster behavior by orchestrating N independent RunPod instances. This avoids the `CreateClusterInput` schema issues and `SUPPLY_CONSTRAINT` gaslighting of the native SLURM API.

## Core Requirements

1. **Parallel Creation**:
   - Use `create_pod` (On-Demand) asynchronously for N instances.
   - Implement staggered retries to handle transient supply issues for specific GPU types.

2. **Unified Initialization**:
   - Leverage the existing `_init_pod_worker` (ThreadPool) to initialize all pods in parallel.
   - Use the Local + S3 strategy to ensure all pods pull the exact same codebase and state.

3. **Coordination & Identity**:
   - Each pod in the virtual cluster gets a unique suffix (e.g., `mavaia_train_1`, `mavaia_train_2`).
   - The first pod created is designated as the "Master" for result aggregation.

4. **Robust Monitoring**:
   - The watchdog loop must track the health of all virtual cluster members.
   - Terminate all members if one fails (fail-fast) to save costs.

## Target Workflow
1. Local preparation (S3 Upload).
2. Parallel `create_pod` calls for `cluster_size` instances.
3. Parallel initialization (S3 Pull + Dependencies).
4. Asynchronous training start on all instances.
5. Multi-pod watchdog sync back to S3.

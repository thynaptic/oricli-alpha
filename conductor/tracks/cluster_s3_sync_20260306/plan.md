# Implementation Plan: Cluster S3-Local Sync Strategy

## Phase 1: Local Preparation
- [ ] Implement an `--upload-to-s3` flag in `scripts/runpod_bridge.py`.
- [ ] If the flag is set, `tar` the project root (excluding `.venv`, `.git`, etc.) and stream it to S3 using `s3_sync_local_to_bucket`.

## Phase 2: Cluster Provisioning
- [ ] Modify the cluster creation logic in `main()` to allow booting WITHOUT a `networkVolumeId`.
- [ ] Inject S3 credentials and bucket details as environment variables into the cluster pods during the `create_cluster` call.

## Phase 3: Cluster Pod Initialization
- [ ] Update `_init_pod_worker` to support S3-based initialization.
- [ ] If S3 parameters are provided:
    - [ ] Perform `s3_sync_pod(direction="pull")` on each pod in the cluster.
    - [ ] Ensure `mavaia_core` and dependencies are installed in the local `/workspace`.

## Phase 4: Training & Synchronization
- [ ] Modify the training script or bridge to periodically sync the local checkpoints back to S3.
- [ ] Implement a final "push results" step in `scripts/runpod_bridge.py` that pulls results from S3 back to the local machine after training completes.

## Phase 5: Verification
- [ ] Run a small-scale cluster (2 pods) in a new region using the S3 strategy.
- [ ] Verify checkpoints are correctly archived to S3 and then synced back locally.

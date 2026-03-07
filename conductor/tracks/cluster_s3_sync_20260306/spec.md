# Specification: Cluster S3-Local Sync Strategy

## Objective
To decouple Mavaia clusters from regional network volume bottlenecks (like EU-RO1 saturation) by using a combination of local ephemeral storage (NVMe) on pods and S3 for persistent state.

## Core Requirements

1. **Local-First Workdir**: 
   - Training must occur on each pod's local SSD/NVMe (typically `/workspace` without a network volume mount, or a local partition).
   - This ensures maximum I/O throughput (no iowait from network volumes).

2. **S3 as Central Source**:
   - The local codebase and weights must be archived and pushed to S3 before cluster creation.
   - Each pod in the cluster must pull the archive from S3 during initialization.

3. **Checkpoint Synchronization**:
   - Distributed training checkpoints must be periodically pushed back to S3.
   - The Master node will handle the final aggregation/upload of results.

4. **Regional Independence**:
   - Clusters must be deployable in any RunPod region, regardless of where the original network volume exists.

## Target Architecture

- **Local Machine**: `tar` -> `mbuffer` -> `aws s3 cp`
- **Pod Initialization**: `aws s3 cp` -> `tar -xf`
- **Training Lifecycle**:
  - `MASTER`: Pull Stage N -> Train -> Push Checkpoints -> S3
  - `WORKERS`: Pull Stage N -> Train -> (Internal P2P or local state)

## Metrics for Success
- Reduced `iowait` during training.
- Cluster successfully boots and trains in a non-EU-RO1 region (e.g., US-West).
- No dependency on a persistent Network Volume ID during cluster creation.

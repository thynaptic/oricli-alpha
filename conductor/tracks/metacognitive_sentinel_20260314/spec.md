# Specification: The Metacognitive Sentinel (Self-Correction)

## Objective
To deploy a continuous oversight layer on the Swarm Bus that monitors agent deliberation for cognitive entropy, looping, and hallucinations, automatically intervening to keep the Hive on track.

## Background
In a decentralized Swarm, agents can sometimes get stuck in a loop of agreeing with each other on incorrect facts, or fail to progress toward the actual goal. The Metacognitive Sentinel acts as an immune system, observing the shared blackboard state without participating, and intervening only when the system derails.

## Requirements

### 1. Sentinel Node (`metacognitive_sentinel.py`)
A specialized module that listens to *all* messages on the Swarm Bus but does not bid on tasks.
- Tracks message velocity, sentiment, and progress toward the original query.
- Uses DBT/CBT-inspired heuristics (e.g., Radical Acceptance, Cognitive Defusion) to identify circular reasoning.

### 2. Intervention Protocol
If entropy is detected, the Sentinel publishes an `INTERVENTION` message to the Swarm Bus.
- This forces the current active agents to pause, clears the immediate context window, and injects a "course correction" prompt (e.g., "You are stuck in a loop. Re-evaluate the original premise.").

### 3. Arbitration Override
The Sentinel has veto power during the Broker's consensus phase if it detects a hallucinated final answer.

## Success Criteria
- A Swarm session intentionally prompted to enter a conversational loop is autonomously broken and corrected by the Sentinel.
- The system prevents blatantly hallucinated code from being executed in the sandbox.

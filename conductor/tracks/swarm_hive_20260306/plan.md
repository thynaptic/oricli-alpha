# Implementation Plan: Distributed "Swarm" Intelligence (The Hive)

*Note: This track is vaulted until module census reaches 100%.*

## Phase 1: The Swarm Bus
- [ ] Implement `oricli_core/brain/swarm_bus.py` (Pub/Sub messaging system).
- [ ] Define standard message protocols (CFP, BID, ACCEPT, RESULT).

## Phase 2: Micro-Agent Wrapper
- [ ] Create `oricli_core/brain/hive_node.py`.
- [ ] Implement the logic that wraps a `BaseBrainModule`, listens to the bus, and automatically generates bids based on the module's `ModuleMetadata`.

## Phase 3: The Broker & Market Dynamics
- [ ] Implement `oricli_core/brain/modules/swarm_broker.py`.
- [ ] Build the arbitration logic to evaluate bids (weighing confidence against compute cost) and award contracts.

## Phase 4: Decentralized Execution
- [ ] Refactor `Oricli-AlphaClient` to drop queries onto the Swarm Bus rather than calling the `cognitive_generator` directly.
- [ ] Ensure the `subconscious_field` is updated dynamically by any agent that completes a task.

## Phase 5: The "Society of Mind" Test
- [ ] Submit a highly complex, multi-domain Sovereign Goal.
- [ ] Monitor the Swarm Bus to verify that specialized agents (e.g., Web Search, Security Scanner, Code Generator, Synthesizer) bid, collaborate, and resolve the goal peer-to-peer.

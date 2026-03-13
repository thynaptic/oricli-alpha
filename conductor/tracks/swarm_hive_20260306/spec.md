# Specification: Distributed "Swarm" Intelligence (The Hive)

## Objective
To vault the final evolutionary step of Oricli-Alpha: converting the static module registry into a dynamic, decentralized multi-agent system ("The Hive") where 246+ specialized modules operate as independent micro-agents.

## Core Concepts

1. **The Contract Net Protocol (`swarm_broker.py`)**:
   - Replaces the `cognitive_generator`'s intent router.
   - When a complex query or Sovereign Goal is received, the Broker broadcasts a "Call for Proposals" (CFP) to the Swarm.
   - Micro-agents evaluate the task against their own capabilities (metadata) and submit a "Bid" indicating their confidence and estimated compute cost.

2. **Micro-Agent Wrapping (`hive_node.py`)**:
   - Every existing `BaseBrainModule` is wrapped in a `HiveNode` class.
   - Nodes run asynchronously. They listen to the broadcast bus, bid on tasks, execute them, and publish results back to the bus.

3. **Peer-to-Peer Collaboration**:
   - Micro-agents can broadcast their own CFPs. If the `python_refactoring_reasoning` agent needs to test code, it broadcasts a request, and the `shell_sandbox_service` agent bids to handle it.
   - This creates dynamic, self-assembling execution graphs without a top-down architect.

4. **The Consensus Ledger**:
   - The `subconscious_field` acts as the shared context. As agents complete tasks, they vibrate their results into the field, updating the global state so other agents have the latest context for their own execution.

## Technical Architecture
- **Message Bus**: A lightweight asynchronous pub/sub system (e.g., Redis pub/sub or an internal `asyncio` event bus).
- **Decentralization**: No central "brain." The `Oricli-AlphaClient` simply drops a goal onto the bus and waits for a "Synthesis" agent to declare the goal complete.

## Prerequisite for Activation
- **100% Module Census**: All 246+ modules must be fully implemented, tested, and mapped with accurate metadata, as the Swarm relies entirely on self-reported capabilities to function efficiently.

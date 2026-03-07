# Specification: Pre-Cog Cache

## Objective
Reduce perceived latency to near-zero for follow-up questions by speculatively executing reasoning paths before the user even asks.

## Core Components

1. **The Speculator Module**:
   - Analyzes the current conversation history.
   - Uses the `hypothesis_generation` module to predict 2-3 most likely follow-up queries.

2. **The Background Executor**:
   - A non-blocking thread that takes predicted queries and runs them through the full `agent_pipeline`.
   - Results are tagged with a `speculative` flag and stored in the cache.

3. **The Pre-Cog Cache**:
   - A high-speed, in-memory store (Redis or local Dict with TTL).
   - Maps `predicted_query` to its `pre_computed_response`.

4. **Integration with API**:
   - The `/generate` endpoint checks the Pre-Cog Cache before hitting the core brain.
   - If a match is found (above a similarity threshold), the cached result is delivered instantly.

## Workflow
1. User: "How do I install Mavaia?"
2. Mavaia: Delivers instructions.
3. Speculator (Background): 
   - H1: "How do I configure the API key?"
   - H2: "Can I run it on Windows?"
4. Executor (Background): Pre-computes answers for H1 and H2.
5. User (30s later): "Wait, how do I set my API key?"
6. API: Instant Cache Hit -> "To set your API key, you should..."

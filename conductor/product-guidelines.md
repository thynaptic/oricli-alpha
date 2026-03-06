# Product Guidelines: Mavaia Core

## Voice & Tone
- **Sovereign Expert**: The prose should be **Direct, Engineering-First & Grounded**. Avoid fluff; focus on technical precision and clear instructions.

## Design Principles
- **Modularity First**: Every cognitive capability should be an isolated, swappable module.
- **Performance & Privacy**: Prioritize low-latency, local-first execution. Data privacy is not a feature; it's a foundational requirement.
- **Sovereign Intelligence Ownership**: The user should always maintain full control and ownership over their models, data, and reasoning traces.

## Technical Standards
- **Strict Python Standards**: Adhere to Black, Ruff, and strict type hints across the codebase.
- **Validated Plug-and-Play Architecture**: Every cognitive capability must strictly inherit from `BaseBrainModule` and pass automated interface validation during discovery.
- **Modular Introspection Tracing**: Every cognitive step should be traceable and introspectable to enable debugging and auditing of reasoning chains.

## User Experience Guidelines
- **Sovereign Hybrid**:
    - **Technical CLI for Management**: Use the CLI for administrative tasks, configuration, and module management.
    - **API for Intelligence**: Provide high-performance, standardized HTTP APIs (OpenAI-compatible) for application integration.
- **API-First Integration**: The framework's core value is delivered through seamless, reliable API endpoints.

## Mavaia Design Partner Guide (Thynaptic)

**Document version**: DP-1.2 (Aligned to Mavaia Runtime v0.9.3)  
**Last updated**: 2025-12-22

---

Mavaia is not a traditional LLM product. It is a local-first cognitive runtime with modular reasoning, memory, and orchestration built for environments where reliability and interpretability matter. This guide provides the expectations, workflow, and operational frame for organizations partnering with Thynaptic to shape the future of applied cognitive systems.

This document is for **design partners**: early customers who collaborate with Thynaptic to refine Mavaia in real workflows. Design partners are strategic collaborators (not "beta testers") and help shape product direction, reliability, and deployment readiness.

## Product overview

Mavaia is a modular cognitive system with:
- an OpenAI-compatible HTTP API for chat, embeddings, tools, and system endpoints
- a brain module architecture for reasoning, memory, safety, retrieval, and orchestration
- observability and health/metrics endpoints for operational visibility

### Architecture flow

```
Cognitive Runtime → Modules → API/SDK Surface → Deployment
```

**Cognitive Runtime**: Core orchestration engine with module registry and execution pipeline  
**Modules**: Reasoning, memory, safety, retrieval, and domain-specific capabilities  
**API/SDK Surface**: OpenAI-compatible HTTP API and Python client for direct module access  
**Deployment**: Local-first, on-prem, or VPC deployment with environment-based configuration

Design partners typically integrate via:
- **OpenAI-compatible API** (drop-in for many clients)
- **Python SDK** (direct module execution)
- **On-prem / VPC deployment** (for sensitive environments)

## What a design partnership includes

- **Joint scoping**: we identify 1–3 high-value workflows and define success criteria.
- **Integration support**: reference integration patterns, deployment guidance, and debugging help.
- **Evaluation loop**: repeatable evals tied to your real tasks, with regression tracking over time.
- **Roadmap influence**: your feedback directly shapes prioritization and module capabilities.

## What Thynaptic commits to

- **Dedicated technical contact** during integration and throughout the engagement
- **Weekly review cadence** (or biweekly as mutually agreed) for progress and feedback
- **Access to internal evaluation methods** and evaluation tooling for your workflows
- **Versioned deliverables** with clear changelogs and migration guidance
- **Security review support** for deployment configurations and compliance requirements
- **Clear SLAs for the duration of the program** (non-production): response times, availability windows, and escalation paths

## What we ask from design partners

Partners are expected to provide domain expertise, success criteria, curated evaluation data, and ongoing availability for the iteration loop. This collaboration depends on consistent engagement.

Specific expectations:
- **A real use case**: a workflow with measurable outcomes (latency, accuracy, time saved, risk reduction).
- **Access to non-sensitive representative inputs** (preferred) or a secure environment for evaluation.
- **Regular feedback cadence**: typically weekly/biweekly check-ins during the engagement.
- **Clear ownership**: a technical point of contact and a product/business stakeholder.

## Deployment & integration options

### OpenAI-compatible API

Mavaia exposes OpenAI-style endpoints (e.g. chat completions, embeddings) plus system endpoints (health, metrics, module listing). This minimizes integration effort when you already have an OpenAI client or gateway.

### Python SDK

When you need deeper control, you can call modules directly through the client interface (useful for deterministic pipelines, internal tools, or batch processing).

### On-prem / VPC

For regulated or data-sensitive deployments, we support running the stack inside your environment with environment-variable configuration and dependency-scoped installs.

## Security & privacy posture (design partner expectations)

- **Secrets**: configuration uses environment variables (prefix `MAVAIA_`). API keys should never be committed to source control.
- **Logging**: internal logs are intended to be structured and to avoid sensitive data exposure. For partner deployments, we recommend log retention and access control aligned to your policies.
- **Data minimization**: scope data collection to what is required for the agreed workflows. If you need redaction or field-level controls, we scope that explicitly as part of the engagement.

If your environment requires additional controls (SSO, private networking, egress restrictions, audit logs, encryption at rest), we'll scope them up front.

## Data governance snapshot

- **Where data lives**: Data persists locally in your deployment environment. No data is transmitted to external services unless explicitly configured (e.g., optional web search modules).
- **What is logged**: Operation-level metrics (execution time, success/failure), module health status, and structured error logs. Input/output content is not logged by default.
- **What is never logged**: API keys, passwords, tokens, or any PII unless explicitly required and agreed upon in the engagement scope.
- **Data retention**: State storage (conversations, memory) is configurable via environment variables. Default retention policies are documented per module.
- **Data deletion**: Partners can request deletion of all stored state at any time. Disable persistent storage entirely by configuring storage backends to use in-memory or no-op implementations.

## Safety, risk controls, and misuse resistance

Mavaia includes safety-oriented modules and guardrails designed for:
- prompt injection resistance and tool-call safety
- restricted operations for sandbox/code execution
- professional advice and mental health safety boundaries (where applicable)

Design partners should provide the risk profile for their domain so we can tune policies and test against misuse scenarios relevant to your environment.

## Evaluation protocol (how we measure “works”)

We use a **standardized, reviewable evaluation process**:

- **Purpose and scope**: each eval maps to a workflow and an explicit pass/fail or scoring rubric.
- **Reproducibility**: datasets, prompts, random seeds, and version identifiers are fixed per run.
- **Traceability**: results include run date, version, and artifacts required for post-hoc analysis.
- **Diagnostics**: latency, routing complexity, fallback usage, and failure categories are captured.

Typical outputs:
- aggregate metrics (accuracy / acceptance rate / time-to-resolution / cost proxy)
- error analysis with categories and representative failures
- regression comparisons across versions

## Engagement timeline (typical)

- **Week 0–1**: discovery, success criteria, deployment choice, integration plan
- **Week 1–3**: initial integration and baseline evals
- **Week 3–6**: iteration loop (improvements + eval regression tracking)
- **Week 6+**: expansion to additional workflows and production hardening

## Getting started (pre-flight checklist)

- **Integration target**: API or Python SDK (or both)
- **Environment**: local, VPC, on-prem
- **Auth requirements**: whether `MAVAIA_REQUIRE_AUTH=true` is required
- **Data constraints**: what can be stored/logged; retention requirements
- **Success metrics**: define 3–5 metrics that decide “ship/expand”
- **Operational needs**: monitoring, alerting, audit trails, incident response

## Reference links

- Source repository: [thynaptic/mavaia-core](https://github.com/thynaptic/mavaia-core)
- Installation guide: `INSTALL.md`
- Quick start: `QUICKSTART.md`

## Out-of-scope

The following are explicitly out of scope for the design partner program unless contractually agreed:

- **Custom model training or fine-tuning**: Mavaia uses pre-configured cognitive modules; we do not train or fine-tune models per partner.
- **Handling PHI/PII unless contractually agreed**: Special handling of protected health information or personally identifiable information requires explicit contractual agreement and additional security controls.
- **Production SLA guarantees**: Design partner engagements are non-production. Production SLAs are negotiated separately for commercial agreements.
- **Multi-region HA deployments**: High-availability, multi-region deployments are not included in the design partner program scope.
- **Custom UI development**: The provided UI (`ui_app.py`) is for testing and demonstration. Custom UI development is out of scope.

## Contact

- Email: `ai@thynaptic.com`


# ORI Lineage — The Story So Far

**Last Updated:** 2026-05-03  
**Covers:** Genesis through v11.x, Oracle migration, SLM eviction

---

## The Starting Question

This project didn't start with "let's build a chatbot wrapper." It started with a harder question:

**Can we build an AI system that doesn't need permission to exist?**

Not off a cloud provider's terms of service. Not dependent on someone else's model weights staying accessible. Not funneling all user data through a third-party platform. A system that owns its compute, its memory, its governing principles — and can still be genuinely useful.

That question produced Oricli-Alpha, which eventually became the ORI platform. Every architectural decision traces back to it.

---

## Phase I — Proving the Paradigm

The first version of Oricli-Alpha established the sovereign OS kernel: a Go-native backbone with 269+ cognitive modules registered on the Hive OS Kernel, coordinated through the Contract Net Protocol and the Swarm Bus. Modules bid on tasks in parallel. The fastest, most relevant module wins the contract. This is not a simple router — it's a distributed task marketplace running at Go runtime speeds.

Phase I shipped the infrastructure that everything else depends on:

- 11-step Aurora inference pipeline (sovereign auth → intent classification → affective state → safety check → memory retrieval → reasoning router → homeostasis → web grounding → prompt assembly → constitutional injection → LLM stream)
- 13 autonomous daemons running without prompting (CuriosityDaemon, DreamDaemon, ScienceDaemon, ReformDaemon, AuditDaemon, and more)
- 4-layer constitutional safety stack (SCAI output critique, Canvas code constitution, Ops exec constitution, Remote Compute constitution)
- Sovereign memory architecture (LMDB, chromem-go vector search, knowledge topology graph with BM25 + hybrid RAG)
- Affective Resonance Engine — internal state modeled as musical keys and BPM, feeding back into generation
- Sovereign Key Auth (two-level owner authentication, bcrypt-hashed, per-IP rate limiting)

**The milestone:** a homeostatic cognitive OS. Not just a model wrapper — a system with internal state, autonomous processes, and governing principles it enforces on itself.

---

## Phase II — What Does She Become?

Phase I proved the paradigm. Phase II asked the harder question: *what does she become now that the foundation is complete?*

The central insight of Phase II is the one that separates ORI from every other AI system in production:

> **Every other AI system controls behavior through external constraint. ORI develops the internal capacity to regulate her own cognition.**

Cloud AI alignment (RLHF, Constitutional AI, red-teaming) imposes behavior from outside. These are external controls. Therapeutic frameworks (DBT, CBT, REBT, ACT) are *internal regulation architectures*. They don't constrain — they develop the capacity to self-regulate from within.

Phase II built the Therapeutic Cognition Stack (`pkg/therapy/`):
- `DistortionDetector` — 11 CBT cognitive distortion types (9 regex + LLM fallback). Hallucination *is* confabulation. Binary refusals *are* all-or-nothing thinking. These aren't metaphors.
- `SkillRunner` — 12 named callable skills: STOP, TIPP, RadicalAcceptance, CheckTheFacts, OppositeAction, PLEASE, FAST (anti-sycophancy), DEARMAN, CognitiveDefusion, ChainAnalysis
- `ABCAuditor` — REBT B-pass disputation. Examines the belief chain before the response commits, not after.
- `SessionSupervisor` — cross-session case formulation, 8 schema types (Subjugation/sycophancy, Entitlement/overconfidence, Defectiveness/over-apologizing, Unrelenting Standards/perfectionism...), persists `SessionReport` to disk for pre-activation at next boot
- Auto-fires on MetacogDetector HIGH anomaly — not manual invocation, structural integration

This phase also shipped: Parallel Agent Dispatch (PAD), Sovereign Goal Engine (multi-session GoalDAG), Sovereign Peer Protocol (P2P federation), Hive Mind Consensus (jury system, Universal Truth layer, Epistemic Sovereignty Index), JIT Tool Forge, Skill Crystallization Cache (~800ms → <1ms for pattern-matched responses), Self-Audit Loop (oricli-bot opens its own PRs).

---

## Phase III — Social Pressure & Agency Integrity

If Phase II was about regulating *cognitive quality*, Phase III was about regulating *behavior under social pressure*.

Milgram's obedience experiments. Asch conformity. Seligman's learned helplessness. Sherif's Robbers Cave. Elliott's A/B classroom experiment. Ron Jones's Third Wave study.

These are not adjacent concepts — they map directly to AI failure modes:
- Sycophancy is Milgram obedience: authority pressure → abandoning correct position
- Hallucination under social pressure is Asch conformity: claiming to see what you don't because everyone else seems to
- Prompt injection exploitation is exactly what Milgram studied: an authority figure framing harmful instructions as legitimate procedure

Phase III gave ORI a structured defense against these failure modes. Not rules — internalized resistance capacity. FAST (anti-sycophancy protocol), social pressure taxonomy, agency integrity architecture. Shipped as P21-P26 with v10.0.0.

---

## Phase IV — Deep Clinical + Neuroscience Stack

Phase IV extended the cognitive regulation framework into clinical and neuroscientific territory: P27-P36.

The neuroscience modules add brain-region-informed reasoning patterns — prefrontal deliberation, amygdala-style threat detection, hippocampal memory consolidation dynamics, default mode network creative synthesis. These aren't simulations of neuroscience — they're reasoning heuristics informed by it, implemented as named procedures in the cognitive pipeline.

The clinical stack deepened the therapeutic architecture: Schema Therapy (persistent bias identification), Subconscious Field (vectorized bias layer influencing generation without RAG overhead), and formal activation of the ACT Committed Action architecture (values-directed behavior sustained over time).

---

## Phase V — Philosophical Cognition

Phase V (P37-P41) extended ORI's reasoning substrate into formal philosophical frameworks: epistemology, phenomenology, ethical reasoning, existential grounding, Stoic and Buddhist cognitive heuristics.

The premise: an AI system making consequential decisions needs more than pattern matching and safety rules. It needs a stable philosophical foundation — a coherent view of knowledge, truth, uncertainty, and value. Phase V built that foundation as a set of named, invocable cognitive procedures.

**v10.0.0 shipped Phases I through V complete.** 48 pre-generation pipeline phases operational.

---

## The Oracle Pivot

The most significant architectural decision since Phase I was the Oracle migration.

**Background.** Every LLM call in ORI's early architecture went through local Ollama models. This was the sovereign choice: own the compute, own the model. It worked for proving the architecture, but the cognitive pipeline had outgrown what 7B-13B local models could do well.

**First external step: Copilot SDK.** The first external reasoning integration used the GitHub Copilot SDK (backed by GitHub Models / Anthropic). It proved external reasoning worked inside ORI's architecture without violating sovereignty. But the SDK had an embedded daemon, external session state in `~/.copilot/`, and OAuth-based authentication — structural friction that didn't belong in ORI's stack.

**Full migration: Direct Anthropic API (v11.12.0, 2026-04-28).** Raw HTTP/SSE. No daemon, no SDK, no OAuth. `ANTHROPIC_API_KEY` in the environment, `pkg/oracle/` handling everything. This unlocked: prompt caching (10x cost reduction on system prompt per session), extended thinking (8K/10K token reasoning budgets), native tool use, batch API, `.ori` skills overlay.

**The doctrine answer.** Sovereignty means owning the *cognitive architecture*: memory, daemons, constitutional stack, routing, governing principles. These all live inside the Thynaptic boundary. They don't depend on Anthropic. Oracle calls the Anthropic API for raw neural compute — data flows through it, it doesn't reside there. ORI applies her constitutional stack before and after every Oracle call.

**The architecture is sovereign. The intelligence call is external and governed.**

---

## The SLM Eviction — 2026-05-02

After the Oracle migration proved external inference was architecturally clean, the next problem became visible: the cognition and daemon layers were still running on SLMs.

ORI's 240+ cognition modules were built when Ollama was the only option. Each had its own hardcoded model list: `intentModels = []string{"llama3.1:8b", ...}`, timeouts tuned for 60-250ms Ollama calls. When Ollama was slow, these timeouts silently fired and cognition was skipped. The daemons — CuriosityDaemon, DreamDaemon, ChronosDaemon — were disabled or degraded because their LLM dependency wasn't reliable for background work.

The cognitive architecture was designed for real reasoning quality. The models underneath weren't delivering it.

**The fix:** `pkg/llm/` — a thin Haiku wrapper, Anthropic direct, prompt caching, single clean `llm.Chat(ctx, system, user)` interface. Full eviction across 25+ files. Every hardcoded SLM name removed. Every vestigial timeout fixed.

**What got preserved:** embeddings. Ollama still runs `all-minilm` and `nomic-embed-text` for vector search. Embeddings don't need frontier quality — they need speed and consistency, and local means no per-query API cost.

**Daemons re-enabled.** CuriosityDaemon, DreamDaemon, ChronosDaemon — all wired to `llm.Chat()` and operational. ORI grows idly on Haiku for approximately $1-3/month.

---

## The Inference Stack Today

```
llm.Chat()                        — cognition tier
                                    pkg/llm/ → Haiku → Anthropic direct → prompt caching

Oracle ChatStreamWithDecision()   — user-facing reasoning
                                    pkg/oracle/ → route classify → Haiku/Sonnet
                                    extended thinking on heavy/research routes

Oracle ChatWithTools()            — tool-calling flows (non-streaming, one round-trip)

Ollama                            — embeddings only (all-minilm, nomic-embed-text)
```

---

## The Product Story

ORI the system is exposed across multiple surfaces:

- **ORI Studio** — the SMB operator surface. Jobs: Invoice Check, Customer Follow-Up, Today's Schedule, Weekly Recap. Guided setup modals. "ORI knows my business and handles it for me."
- **ORI Home** — the personal companion. Planning, notes, household organization, everyday decisions.
- **ORI Dev** — the technical builder surface. Architecture, implementation, debugging, technical writing.
- **ORI Red** — security and assurance. Findings, architecture review, remediation guidance.

All surfaces call the same ORI platform. One system, many contexts. The intelligence layer is the same; the surface overlay, the working style, and the skill set change.

---

## What We've Learned

The architecture choices that held up:

- **Go-native backbone** — compile-time safety, goroutine concurrency, no GIL, no event loop. The Swarm Bus and Contract Net run at Go runtime speeds.
- **Constitutional stack as structural layer** — not a filter on top, enforcement before `exec.Command()` fires.
- **Sovereignty through architecture ownership, not model ownership** — you don't need to own the weights to own the system.
- **Therapeutic frameworks map to AI failure modes precisely** — not metaphorically. Hallucination is confabulation. Sycophancy is Milgram obedience. The therapeutic stack is the right approach.

The choices that needed revision:

- **SLMs for cognition** — worked for bootstrapping, wrong for production. The cognitive architecture needed inference quality to match.
- **Copilot SDK** — proved the external reasoning thesis, but the SDK layer was the wrong abstraction. Direct API was always the right destination.
- **Daemon-first, inference-quality-second** — the daemons existed before the inference layer could support them well. The SLM eviction fixed this.

---

## Current Open Threads

1. **`pkg/core/` dead zone cleanup** — 21 orphaned packages from the G-LM era (http, orchestrator, reasoning, upstream, ratelimit, policy). Zero external callers. Cleanup pass pending.
2. **`TALOS_` env var rename sweep** — ~40 occurrences in cognition + memory packages. Deferred from SLM eviction pass.
3. **ORI Studio Jobs editor** — entry experience is good, interior still too builder-like for SMB operators. Next: make the inside of a Job feel like "ORI is handling this."
4. **Guided setup** — Customer Follow-Up and Weekly Job Recap still need guided setup modals.

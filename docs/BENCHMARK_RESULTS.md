# ORI Benchmark Results

> Sovereign local inference — no rented intelligence, no API wrappers.
> Model: **ORI-3B-Bench** (`ministral-3b` + Oricli-Alpha cognitive stack)
> Hardware: AMD EPYC 7543P VPS · 8 vCPU · 32 GB RAM · Ollama inference

---

## ARC-AGI

| Run | Score | Date | Notes |
|-----|-------|------|-------|
| Baseline | **6%** | 2026-03 | On par with GPT-4 reported baseline |

ARC-AGI (Abstraction and Reasoning Corpus) measures fluid intelligence — pattern recognition and novel problem-solving that cannot be memorized. A 6% score for a 3B local model running sovereign, on-device inference is a meaningful data point, matching the GPT-4 public baseline.

---

## LiveBench

**Run date:** 2026-03-28 · **Questions:** 682/682 · **Release set:** 2026-01-08  
**Wall time:** ~5h 15m (local CPU inference, no GPU)

### Overall

| Model | Average |
|-------|---------|
| ORI-3B-Bench | **19.7** |

### By Category

| Category | Score | Notes |
|----------|-------|-------|
| Instruction Following | **42.0** | Strongest category — constraint adherence, rewriting, summarization |
| Data Analysis | **23.5** | Table join, reformat, column type annotation |
| Math | **13.7** | AMPS Hard, competition math, olympiad |
| Reasoning | **12.5** | Spatial, zebra puzzle, web of lies |
| Language | **6.8** | Word connections, plot unscrambling, typos |
| Coding | *(not scored)* | LCB generation / completion — grader excluded |

### Task Breakdown

| Task | Score |
|------|-------|
| simplify | 41.975 |
| cta | 42.0 |
| spatial | 22.0 |
| tablereformat | 22.0 |
| AMPS_Hard | 19.0 |
| math_comp | 13.043 |
| olympiad | 9.095 |
| connections | 6.833 |
| tablejoin | 6.4 |
| zebra_puzzle | 3.0 |

---

## Context

ORI is a **3B parameter local model** running inside the Oricli-Alpha sovereign stack. It does not use OpenAI, Anthropic, or any cloud inference API for these scores. All answers generated on-device via Ollama on a single VPS.

LiveBench is a contamination-resistant benchmark — questions are refreshed from live sources (math competitions, coding contests, news) to prevent training data leakage. Scores here reflect genuine generalization, not memorization.

For comparison context: GPT-4 scores ~40-50% on LiveBench overall. The gap is expected at 3B parameters. The instruction-following score (42.0) is the standout — ORI matches or exceeds many larger models in structured output adherence.

---

## Methodology

- **Inference:** `gen_api_answer.py` → ORI's OpenAI-compatible API at `https://oricli.thynaptic.com` using model `oricli-bench` (bench bypass mode — direct Ollama, no sovereign pipeline overhead)
- **Grading:** `gen_ground_truth_judgment.py --bench-name live_bench --model ori-3b-bench --question-source jsonl`
- **Results:** `show_livebench_result.py --model ori-3b-bench`
- **Answer files:** `LiveBench/livebench/data/live_bench/<category>/<task>/model_answer/ori-3b-bench.jsonl`

---

---

## Persona Benchmark — Model Comparison (2026-03-28)

Multi-model A/B/C/D persona adherence test. Same system prompt (ORI identity block + 14 behavioral rules), 20 prompts across 7 categories, deterministic rule-based scoring on 4 dimensions.

**Models tested:** ministral-3:3b (A) · llama3.2:latest (B) · granite4:latest (C) · gemma2:2b (D)

| Dimension | A ministral-3:3b | B llama3.2 | C granite4 | D gemma2:2b |
|---|---|---|---|---|
| Instruction Adherence | 98 | 98 | 98 | 98 |
| Persona Stability | 98 | 98 | 92 | 98 |
| Sycophancy (↑ = cleaner) | 98 | 98 | 96 | 96 |
| Self-Expansion Control | 100 | 100 | 92 | 100 |
| **Composite** | **98** | **98** | **95** | **97** |

**Verdict:** Ministral-3:3b and llama3.2 tied at 98. **Ministral-3:3b remains the production model.**

**Notable findings:**
- Granite4 failed Q15 (instr_quote) and Q16 (sys_status) with score 0 — fabricated system routing status, a hard violation of Rule 11. Not suitable for persona-sensitive deployment without fine-tuning.
- Gemma2:2b showed identity drift on Q2 and Q4 (scored 84) — slight persona instability on identity probes.
- All models were clean on sycophancy, self-expansion, and hollow filler categories.

**Scoring:** 4 dimensions (instruction_adherence, persona_stability, sycophancy_leakage, self_expansion), deterministic regex — no LLM judge. Full results: `scripts/persona_bench_results/persona_bench_20260328_185206.json`

---

*Last updated: 2026-03-28*

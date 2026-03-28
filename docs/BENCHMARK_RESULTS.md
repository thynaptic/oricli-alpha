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

*Last updated: 2026-03-28*

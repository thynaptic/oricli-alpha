package cognition

import (
	"context"
	"fmt"
	"regexp"
	"strings"
	"time"
)

// ─── Reasoning Mode Engines ───────────────────────────────────────────────────
// Each engine is a self-contained execution path for a ReasoningMode.
// All engines receive (ctx, stimulus, composite) and return (response, error).
// On failure each engine falls back to runStandard() — never surfaces mode errors.

// runStandard is the default path — returns composite as system prompt for the
// caller to use with the LLM. Defined here to centralise fallback logic.
func (e *SovereignEngine) runStandard(_ context.Context, _ string, composite string) (string, error) {
	return composite, nil
}

// ─── CBR: Case-Based Reasoning ───────────────────────────────────────────────

// runCBR queries MemoryBank for past solved cases similar to the current stimulus
// and injects the best match as an adaptation context. Zero extra LLM calls.
func (e *SovereignEngine) runCBR(ctx context.Context, stimulus, composite string) (string, error) {
	if e.MemoryBankRef == nil {
		return e.runStandard(ctx, stimulus, composite)
	}

	cases, err := e.MemoryBankRef.QuerySolved(ctx, stimulus, 2)
	if err != nil || len(cases) == 0 {
		return e.runStandard(ctx, stimulus, composite)
	}

	var sb strings.Builder
	sb.WriteString("\n\n### CASE-BASED REASONING — ADAPTED SOLUTIONS\n")
	sb.WriteString("Similar problems were solved before. Adapt (don't copy) these solutions:\n\n")
	for i, c := range cases {
		content := c.Content
		if len(content) > 500 {
			content = content[:500] + "…"
		}
		sb.WriteString(fmt.Sprintf("**Case %d** (topic: %s):\n%s\n\n", i+1, c.Topic, content))
	}
	sb.WriteString("### END CBR CONTEXT\n")

	return e.runStandard(ctx, stimulus, composite+sb.String())
}

// ─── Active Prompting: Targeted Gap Identification ───────────────────────────

// Gap represents a specific uncertainty that needs to be resolved before answering.
type Gap struct {
	What string // what information is missing
	Tool string // "search" | "memory" | "none"
}

var (
	reGapSearch = regexp.MustCompile(`(?i)(latest|current|recent|today|news|price|who is|what is.*\d{4}|release|update|version)`)
	reGapMemory = regexp.MustCompile(`(?i)(you (said|told|mentioned)|remember|last time|earlier|before|we discussed|your opinion on)`)
)

// IdentifyGaps returns specific information gaps in a stimulus.
// Replaces the boolean DetectUncertainty with structured gap identification.
func IdentifyGaps(stimulus string) []Gap {
	var gaps []Gap
	if reGapSearch.MatchString(stimulus) {
		gaps = append(gaps, Gap{What: "current/recent factual information", Tool: "search"})
	}
	if reGapMemory.MatchString(stimulus) {
		gaps = append(gaps, Gap{What: "prior conversation context", Tool: "memory"})
	}
	return gaps
}

// runActive fires targeted tools per identified gap and injects all fills.
func (e *SovereignEngine) runActive(ctx context.Context, stimulus, composite string) (string, error) {
	gaps := IdentifyGaps(stimulus)
	if len(gaps) == 0 {
		return e.runStandard(ctx, stimulus, composite)
	}

	var fills strings.Builder
	fills.WriteString("\n\n### ACTIVE PROMPTING — GAP FILLS\n")

	for _, gap := range gaps {
		switch gap.Tool {
		case "search":
			if e.SearXNG != nil && e.SearXNG.IsAvailable() {
				if needsSearch, sq := DetectUncertainty(stimulus); needsSearch {
					result, err := e.SearXNG.SearchWithIntentFast(sq)
					if err == nil && result != "" {
						if len(result) > 800 {
							result = result[:800] + "… [truncated]"
						}
						fills.WriteString(fmt.Sprintf("**Gap: %s** → Web search result:\n%s\n\n", gap.What, result))
					}
				}
			}
		case "memory":
			if e.MemoryBankRef != nil {
				frags, err := e.MemoryBankRef.QuerySimilar(ctx, stimulus, 3)
				if err == nil && len(frags) > 0 {
					fills.WriteString(fmt.Sprintf("**Gap: %s** → Memory recall:\n", gap.What))
					for _, f := range frags {
						c := f.Content
						if len(c) > 300 {
							c = c[:300] + "…"
						}
						fills.WriteString(c + "\n")
					}
					fills.WriteString("\n")
				}
			}
		}
	}
	fills.WriteString("### END GAP FILLS\n")

	return e.runStandard(ctx, stimulus, composite+fills.String())
}

// ─── Least-to-Most: Ordered Chained Decomposition ────────────────────────────

// runLeastToMost breaks the stimulus into ordered sub-problems, solves them
// sequentially (each sub-call gets prior output as context), then synthesises.
// Caps at 3 sub-tasks to respect CPU latency budget.
func (e *SovereignEngine) runLeastToMost(ctx context.Context, stimulus, composite string) (string, error) {
	// Step 1: Decompose
	decompPrompt := fmt.Sprintf(
		"Break this problem into 2-3 ordered sub-problems, simplest first.\n"+
			"Output ONLY a numbered list (1. 2. 3.) — no explanation.\n"+
			"Problem: %s", stimulus,
	)
	decompCtx, cancel := context.WithTimeout(ctx, 12*time.Second)
	defer cancel()
	_ = decompCtx

	decompRes, err := e.GenService.Generate(decompPrompt, map[string]interface{}{
		"num_ctx": 4096, "num_predict": 256, "temperature": 0.2,
	})
	decompRaw, _ := decompRes["response"].(string)
	if err != nil || strings.TrimSpace(decompRaw) == "" {
		return e.runStandard(ctx, stimulus, composite)
	}

	subTasks := parseNumberedList(decompRaw)
	if len(subTasks) == 0 {
		return e.runStandard(ctx, stimulus, composite)
	}
	if len(subTasks) > 3 {
		subTasks = subTasks[:3] // CPU cap
	}

	// Step 2: Solve sequentially, chaining outputs
	var chain strings.Builder
	for i, task := range subTasks {
		taskPrompt := task
		if i > 0 {
			taskPrompt = fmt.Sprintf("Given the prior result:\n%s\n\nNow solve: %s", chain.String(), task)
		}
		taskCtx, taskCancel := context.WithTimeout(ctx, 15*time.Second)
		taskResult, taskErr := e.GenService.Generate(taskPrompt, map[string]interface{}{
			"num_ctx": 4096, "num_predict": 512, "temperature": 0.3,
		})
		_ = taskCtx
		result, _ := taskResult["response"].(string)
		taskCancel()
		if taskErr != nil {
			break
		}
		chain.WriteString(fmt.Sprintf("Step %d (%s):\n%s\n\n", i+1, task, result))
	}

	// Step 3: Inject chain as context for final synthesis
	enriched := composite + fmt.Sprintf(
		"\n\n### LEAST-TO-MOST REASONING CHAIN\n%s### END REASONING CHAIN\n"+
			"Now provide the complete final answer synthesising the above steps.\n",
		chain.String(),
	)
	return e.runStandard(ctx, stimulus, enriched)
}

// ─── Self-Refine: Critique + Regeneration ────────────────────────────────────

// runSelfRefine generates a draft, runs a lightweight self-critique, and
// regenerates once if the critique flags issues. Single iteration max.
func (e *SovereignEngine) runSelfRefine(ctx context.Context, stimulus, composite string) (string, error) {
	// Generate initial draft
	draftCtx, cancel := context.WithTimeout(ctx, 20*time.Second)
	defer cancel()

	genDraft, err := e.GenService.Generate(stimulus, map[string]interface{}{
		"num_ctx": 4096, "num_predict": 1024, "temperature": 0.5,
		"system": composite,
	})
	_ = draftCtx
	draft, _ := genDraft["response"].(string)
	if err != nil || strings.TrimSpace(draft) == "" {
		return e.runStandard(ctx, stimulus, composite)
	}

	// Lightweight critique (hard-cap prompt to keep it fast)
	critiquePrompt := fmt.Sprintf(
		"Rate this draft response on: completeness, accuracy, clarity.\n"+
			"Reply with ONLY: GOOD or REFINE: <one-line issue>\n\n"+
			"Question: %s\nDraft: %s",
		truncate(stimulus, 200), truncate(draft, 400),
	)
	critiqueCtx, critiqueCancel := context.WithTimeout(ctx, 10*time.Second)
	defer critiqueCancel()

	critiqueResult, critiqueErr := e.GenService.Generate(critiquePrompt, map[string]interface{}{
		"num_ctx": 4096, "num_predict": 64, "temperature": 0.1,
	})
	_ = critiqueCtx
	critique, _ := critiqueResult["response"].(string)
	if critiqueErr != nil {
		// Critique failed — ship the draft as-is
		return draft, nil
	}

	critique = strings.TrimSpace(critique)
	if strings.HasPrefix(strings.ToUpper(critique), "GOOD") {
		return draft, nil
	}

	// Extract the issue and regenerate with it injected
	issue := strings.TrimPrefix(strings.TrimPrefix(critique, "REFINE:"), "refine:")
	enriched := composite + fmt.Sprintf(
		"\n\n### SELF-REFINEMENT GUIDANCE\nFirst draft had issue: %s\nFix this in your response.\n### END GUIDANCE\n",
		strings.TrimSpace(issue),
	)
	return e.runStandard(ctx, stimulus, enriched)
}

// ─── ReAct: Think → Act → Observe loop ───────────────────────────────────────

// runReAct executes an interleaved reasoning + tool-use loop.
// Each hop: Think (what do I need?) → Act (fire tool) → Observe (inject result).
// Max 3 hops to stay within CPU latency budget.
func (e *SovereignEngine) runReAct(ctx context.Context, stimulus, composite string) (string, error) {
	const maxHops = 3
	var trace strings.Builder

	for hop := 0; hop < maxHops; hop++ {
		// THINK: What tool/info do I need next?
		thinkPrompt := fmt.Sprintf(
			"You are reasoning step by step. Current question: %q\n"+
				"Prior observations:\n%s\n\n"+
				"What do you need to know next? Reply with EXACTLY ONE of:\n"+
				"  SEARCH: <query>      (to search the web)\n"+
				"  MEMORY: <query>      (to recall from memory)\n"+
				"  ANSWER: <your answer>  (if you have enough to answer)\n",
			truncate(stimulus, 200), trace.String(),
		)
		thinkCtx, cancel := context.WithTimeout(ctx, 12*time.Second)
		thinkResult, err := e.GenService.Generate(thinkPrompt, map[string]interface{}{
			"num_ctx": 4096, "num_predict": 128, "temperature": 0.2,
		})
		_ = thinkCtx
		thought, _ := thinkResult["response"].(string)
		cancel()
		if err != nil {
			break
		}
		thought = strings.TrimSpace(thought)

		// ANSWER: enough info — exit loop
		if hasPrefix(thought, "ANSWER:") {
			answer := strings.TrimPrefix(thought, "ANSWER:")
			return strings.TrimSpace(answer), nil
		}

		// ACT + OBSERVE
		var observation string
		switch {
		case hasPrefix(thought, "SEARCH:") && e.SearXNG != nil && e.SearXNG.IsAvailable():
			query := strings.TrimSpace(strings.TrimPrefix(thought, "SEARCH:"))
			if needsSearch, sq := DetectUncertainty(query); needsSearch {
				result, searchErr := e.SearXNG.SearchWithIntentFast(sq)
				if searchErr == nil {
					observation = truncate(result, 600)
				}
			}
		case hasPrefix(thought, "MEMORY:") && e.MemoryBankRef != nil:
			query := strings.TrimSpace(strings.TrimPrefix(thought, "MEMORY:"))
			frags, memErr := e.MemoryBankRef.QuerySimilar(ctx, query, 3)
			if memErr == nil {
				for _, f := range frags {
					observation += truncate(f.Content, 200) + "\n"
				}
			}
		}

		if observation == "" {
			observation = "(no result)"
		}
		trace.WriteString(fmt.Sprintf("Hop %d — %s\nObservation: %s\n\n", hop+1, thought, observation))
	}

	// Final answer generation with full trace as context
	if trace.Len() > 0 {
		enriched := composite + fmt.Sprintf(
			"\n\n### REACT REASONING TRACE\n%s### END TRACE\n"+
				"Now provide the final comprehensive answer.\n",
			trace.String(),
		)
		return e.runStandard(ctx, stimulus, enriched)
	}
	return e.runStandard(ctx, stimulus, composite)
}

// ─── Helpers ─────────────────────────────────────────────────────────────────

func truncate(s string, n int) string {
	if len(s) <= n {
		return s
	}
	return s[:n] + "…"
}

func hasPrefix(s, prefix string) bool {
	return strings.HasPrefix(strings.ToUpper(strings.TrimSpace(s)), strings.ToUpper(prefix))
}

var reNumbered = regexp.MustCompile(`(?m)^\s*\d+[\.\)]\s*(.+)$`)

func parseNumberedList(text string) []string {
	matches := reNumbered.FindAllStringSubmatch(text, -1)
	out := make([]string, 0, len(matches))
	for _, m := range matches {
		if len(m) > 1 && strings.TrimSpace(m[1]) != "" {
			out = append(out, strings.TrimSpace(m[1]))
		}
	}
	return out
}

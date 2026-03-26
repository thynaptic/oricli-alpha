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

// ─── ModeDebate: Multi-Agent Debate ──────────────────────────────────────────
//
// AlphaStar analog: Multi-Agent League Training — multiple agents with different
// objectives compete, producing a consensus that beats any single perspective.
//
// Four roles fire sequentially (CPU constraint — 3 LLM calls + 1 synthesis):
//   Advocate  — builds the strongest case FOR the proposition
//   Skeptic   — attacks the proposition's weakest points
//   Contrarian — proposes an alternative framing entirely
//   Judge     — synthesizes all three into a balanced verdict
//
// Fires when: reDebate matches AND complexity > 0.65
// Extra LLM calls: 3 (Advocate+Skeptic+Contrarian) + 1 (Judge) = 4 total, capped at 96 tokens each

func (e *SovereignEngine) runDebate(ctx context.Context, stimulus, composite string) (string, error) {
if e.GenService == nil {
return e.runStandard(ctx, stimulus, composite)
}

type roleResult struct {
role, view string
}

roles := []struct {
name, instruction string
}{
{"Advocate", "Build the strongest argument IN FAVOUR of the user's question/position. Be direct. ≤3 sentences."},
{"Skeptic", "Identify the 2 most significant weaknesses or risks in the user's question/position. Be specific. ≤3 sentences."},
{"Contrarian", "Propose a completely different framing or alternative perspective that neither defends nor attacks, but recontextualises the question. ≤3 sentences."},
}

results := make([]roleResult, 0, len(roles))
for _, role := range roles {
prompt := fmt.Sprintf(
"You are the %s in a structured debate.\n\nTOPIC: %s\n\nYour role: %s\n\nResponse:",
role.name, truncateRE(stimulus, 400), role.instruction,
)
res, err := e.GenService.Generate(prompt, map[string]interface{}{
"num_predict": 96,
"num_ctx":     1024,
"temperature": 0.6,
})
if err != nil {
continue
}
if text, ok := res["response"].(string); ok && strings.TrimSpace(text) != "" {
results = append(results, roleResult{role.name, strings.TrimSpace(text)})
}
// Respect context cancellation between roles
select {
case <-ctx.Done():
return e.runStandard(ctx, stimulus, composite)
default:
}
}

if len(results) == 0 {
return e.runStandard(ctx, stimulus, composite)
}

// Build the Judge's brief
var brief strings.Builder
for _, r := range results {
brief.WriteString(fmt.Sprintf("[%s]: %s\n\n", r.role, r.view))
}

judgePrompt := fmt.Sprintf(
"You are the Judge. Three perspectives have been presented on the following topic.\n\n"+
"TOPIC: %s\n\n%s\n"+
"Synthesize these into a balanced, honest verdict that acknowledges the strongest points from each side. "+
"Be direct and conclusive. ≤4 sentences.",
truncateRE(stimulus, 400), brief.String(),
)

judgeRes, err := e.GenService.Generate(judgePrompt, map[string]interface{}{
"num_predict": 128,
"num_ctx":     2048,
"temperature": 0.4,
})
if err != nil {
return e.runStandard(ctx, stimulus, composite)
}

verdict, _ := judgeRes["response"].(string)
verdict = strings.TrimSpace(verdict)
if verdict == "" {
return e.runStandard(ctx, stimulus, composite)
}

// Inject debate findings into composite as context — final response still goes
// through the standard LLM call to maintain voice + constitutional compliance.
var sb strings.Builder
sb.WriteString(composite)
sb.WriteString("\n\n### MULTI-AGENT DEBATE FINDINGS\n")
for _, r := range results {
sb.WriteString(fmt.Sprintf("**%s**: %s\n\n", r.role, r.view))
}
sb.WriteString(fmt.Sprintf("**Judge's Synthesis**: %s\n", verdict))
sb.WriteString("Use this debate context to give a balanced, well-reasoned response.\n")
sb.WriteString("### END DEBATE")

return sb.String(), nil
}

// ─── ModeCausal: Causal Reasoning ────────────────────────────────────────────
//
// AlphaStar analog: Temporal Reasoning (LSTM) + relational graph traversal.
// Handles WHY / WHAT-IF / HOW-DOES queries by explicitly extracting a causal
// chain rather than letting the LLM guess the mechanism.
//
// Pipeline:
//   1. Detect causal query type (WHY / WHAT-IF / HOW)
//   2. Extract causal entities from the stimulus
//   3. Query WorkingMemoryGraph for known causal edges involving those entities
//   4. Ask SLM to produce a causal chain (cause → mechanism → effect)
//   5. Inject chain + graph edges into composite
//
// Extra LLM calls: 1 (causal chain extraction, 96 token cap)

var reCausalType = regexp.MustCompile(`(?i)^(why|what (causes?|caused|happens? if|would happen|if)|how does?|what.?if|root cause|reason (for|why)|effect of|impact of)`)

func (e *SovereignEngine) runCausal(ctx context.Context, stimulus, composite string) (string, error) {
if e.GenService == nil {
return e.runStandard(ctx, stimulus, composite)
}

// Classify the causal query type for the prompt framing
queryType := "WHY"
sl := strings.ToLower(strings.TrimSpace(stimulus))
switch {
case strings.HasPrefix(sl, "what if") || strings.HasPrefix(sl, "what would happen") || strings.Contains(sl, "hypothetically"):
queryType = "WHAT-IF"
case strings.HasPrefix(sl, "how does") || strings.HasPrefix(sl, "how do") || strings.HasPrefix(sl, "how is"):
queryType = "HOW"
}

// Pull any known causal relationships from the graph for grounding
var graphContext string
if e.Graph != nil && len(e.Graph.Relationships) > 0 {
var causalEdges []string
for _, rel := range e.Graph.Relationships {
rt := strings.ToLower(rel.Type)
if strings.Contains(rt, "caus") || strings.Contains(rt, "leads") ||
strings.Contains(rt, "result") || strings.Contains(rt, "trigger") ||
strings.Contains(rt, "effect") || strings.Contains(rt, "depend") {
if src, ok := e.Graph.Entities[rel.SourceID]; ok {
if tgt, ok2 := e.Graph.Entities[rel.TargetID]; ok2 {
causalEdges = append(causalEdges, fmt.Sprintf("%s →[%s]→ %s", src.Label, rel.Type, tgt.Label))
}
}
}
if len(causalEdges) >= 6 {
break
}
}
if len(causalEdges) > 0 {
graphContext = "Known causal edges from memory:\n" + strings.Join(causalEdges, "\n") + "\n\n"
}
}

// Ask SLM to extract a structured causal chain
chainPrompt := fmt.Sprintf(
"You are a causal reasoning engine. This is a %s query.\n\n%sQUESTION: %s\n\n"+
"Extract the causal chain in this format:\n"+
"CAUSE: <root cause or condition>\n"+
"MECHANISM: <how cause leads to effect>\n"+
"EFFECT: <the outcome>\n"+
"UNCERTAINTY: <any key unknowns or assumptions>\n\n"+
"Be precise and concise. One chain only.",
queryType, graphContext, truncateRE(stimulus, 400),
)

res, err := e.GenService.Generate(chainPrompt, map[string]interface{}{
"num_predict": 120,
"num_ctx":     2048,
"temperature": 0.2,
})
if err != nil || ctx.Err() != nil {
return e.runStandard(ctx, stimulus, composite)
}

chain, _ := res["response"].(string)
chain = strings.TrimSpace(chain)
if chain == "" || (!strings.Contains(chain, "CAUSE:") && !strings.Contains(chain, "MECHANISM:")) {
return e.runStandard(ctx, stimulus, composite)
}

var sb strings.Builder
sb.WriteString(composite)
sb.WriteString("\n\n### CAUSAL REASONING CHAIN\n")
sb.WriteString(fmt.Sprintf("Query type: %s\n\n", queryType))
if graphContext != "" {
sb.WriteString(graphContext)
}
sb.WriteString(chain)
sb.WriteString("\n\nUse this causal chain to answer the user's question with mechanistic precision.\n")
sb.WriteString("### END CAUSAL CHAIN")

return sb.String(), nil
}

// truncateRE is a package-local truncation helper for reasoning engines.
// Avoids shadowing the existing truncate() in pal.go.
func truncateRE(s string, n int) string {
if len(s) <= n {
return s
}
return s[:n] + "…"
}

package cognition

import (
	"context"
	"fmt"
	"regexp"
	"strings"
	"sync"
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
				frags, err := e.MemoryBankRef.QuerySimilarWeighted(ctx, stimulus, 3, WeightsStandard)
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

// ─── ModeSelfRefine: Aletheia Loop (Generator → Verifier → Branch) ───────────
//
// Inspired by DeepMind's Aletheia agent (arXiv:2602.10177, Feb 2026).
// Upgraded from single-pass self-critique to a full branched verification loop:
//
//   Problem → Generator → Candidate
//                              ↓
//                          Verifier (NL)
//                         /      |       \
//                    CORRECT  MINOR_FIX  CRITICAL_FLAW / ADMIT_FAILURE
//                       ↓        ↓              ↓
//                    Output    Reviser      Generator restart
//                                ↓          (max 2 total iterations)
//                           Updated candidate
//
// Key addition vs prior SelfRefine:
//   - MINOR_FIX → targeted Reviser patch (not full regeneration)
//   - CRITICAL_FLAW → full Generator restart (not ignored)
//   - ADMIT_FAILURE → returns low-confidence signal rather than hallucinating
//   - Max 2 total generator calls (CPU constraint)
//
// Extra LLM calls: 1 verifier (64 tok) + 0-1 reviser/restart = max 3 total.

const (
	aletheiaCorrect  = "CORRECT"
	aletheiaMinor    = "MINOR_FIX"
	aletheiaCritical = "CRITICAL_FLAW"
	aletheiaFail     = "ADMIT_FAILURE"
)

func (e *SovereignEngine) runSelfRefine(ctx context.Context, stimulus, composite string) (string, error) {
	if e.GenService == nil {
		return e.runStandard(ctx, stimulus, composite)
	}

	// ── Grounding Gate (arXiv:2310.01798) ────────────────────────────────────
	// Per "LLMs Cannot Self-Correct Reasoning Yet": intrinsic self-correction (same
	// model verifying itself) degrades performance. Correction only helps when the
	// verifier has an *external* signal. Gate the loop on a MemoryBank hit; without
	// one, skip straight to standard — ExploiterLeague provides the adversarial audit.
	var groundingContext string
	var frags []MemFrag
	if e.MemoryBankRef != nil {
		frags, _ = e.MemoryBankRef.QuerySimilarWeighted(ctx, stimulus, 3, WeightsAletheia)
		if len(frags) == 0 {
			// No external grounding available — intrinsic correction would degrade; bail.
			return e.runStandard(ctx, stimulus, composite)
		}
		var gb strings.Builder
		gb.WriteString("### EXTERNAL GROUNDING SIGNAL\n")
		gb.WriteString("The following memory fragments are relevant. Only those marked 'verified' are ground truth.\n\n")
		validCount := 0
		for i, f := range frags {
			// Noise gate: discard fragments below combined dynamic certainty threshold.
			// DynamicCertainty blends Belief.Score() + semantic relevance + importance.
			// Threshold 0.35 (vs prior 0.40 on Belief.Score alone) since DynamicCertainty
			// already rewards high semantic match — a very relevant fragment with moderate
			// static belief should still ground.
			if f.DynamicCertainty < 0.35 {
				continue
			}
			certLabel := "unverified"
			if f.Belief.Factual >= 0.80 {
				certLabel = "verified" // U=0: strong factual grounding
			}
			gb.WriteString(fmt.Sprintf("[%d] (factual=%.2f/causal=%.2f/dyn=%.2f/%s) %s\n",
				i+1, f.Belief.Factual, f.Belief.Causal, f.DynamicCertainty, certLabel, truncate(f.Content, 200)))
			validCount++
		}
		gb.WriteString("### END GROUNDING SIGNAL")
		if validCount == 0 {
			// All fragments below certainty threshold — no reliable grounding.
			return e.runStandard(ctx, stimulus, composite)
		}
		groundingContext = gb.String()
	} else {
		// No memory bank wired — skip verifier to avoid degradation
		return e.runStandard(ctx, stimulus, composite)
	}

	// Collect frag IDs for factual belief mutation after Aletheia verdict.
	// CORRECT → bump Factual (+0.03), ADMIT_FAILURE → drop Factual (-0.05).
	groundingFragIDs := make([]string, 0, len(frags))
	for _, f := range frags {
		if f.DynamicCertainty >= 0.35 && f.ID != "" {
			groundingFragIDs = append(groundingFragIDs, f.ID)
		}
	}

	// bumpGrounding fires async belief updates so they never block generation.
	bumpGrounding := func(axis string, delta float64) {
		if e.CertaintyUpdaterRef == nil || len(groundingFragIDs) == 0 {
			return
		}
		go func() {
			bCtx, cancel := context.WithTimeout(context.Background(), 8*time.Second)
			defer cancel()
			for _, id := range groundingFragIDs {
				e.CertaintyUpdaterRef.BumpBelief(bCtx, id, axis, delta)
			}
		}()
	}
	var candidate string
	const maxGeneratorCalls = 2

	for attempt := 0; attempt < maxGeneratorCalls; attempt++ {
		// ── Generator: produce candidate solution ─────────────────────────
		genResult, genErr := e.GenService.Generate(stimulus, map[string]interface{}{
			"num_ctx":     4096,
			"num_predict": 1024,
			"temperature": 0.5,
			"system":      composite,
		})
		if genErr != nil || ctx.Err() != nil {
			return e.runStandard(ctx, stimulus, composite)
		}
		candidate, _ = genResult["response"].(string)
		candidate = strings.TrimSpace(candidate)
		if candidate == "" {
			return e.runStandard(ctx, stimulus, composite)
		}

		// ── Verifier: classify the candidate (grounded) ──────────────────────
		// The grounding context is external KB signal — this converts intrinsic
		// self-correction (unreliable) into externally-grounded verification (reliable).
		verifierPrompt := fmt.Sprintf(
			"You are a rigorous verifier. Evaluate this response for factual accuracy, "+
				"logical soundness, and completeness.\n\n"+
				"%s\n\n"+
				"QUESTION: %s\n\nCANDIDATE RESPONSE: %s\n\n"+
				"Reply with EXACTLY ONE of:\n"+
				"  CORRECT\n"+
				"  MINOR_FIX: <one-line description of the specific issue>\n"+
				"  CRITICAL_FLAW: <one-line description of the fundamental error>\n"+
				"  ADMIT_FAILURE (only if the question is unanswerable with available knowledge)\n\n"+
				"Verdict:",
			groundingContext, truncate(stimulus, 250), truncate(candidate, 500),
		)

		verResult, verErr := e.GenService.Generate(verifierPrompt, map[string]interface{}{
			"num_ctx":     2048,
			"num_predict": 64,
			"temperature": 0.1,
		})
		if verErr != nil || ctx.Err() != nil {
			// Verifier failed — ship current candidate
			return candidate, nil
		}

		verdict := strings.TrimSpace(func() string {
			v, _ := verResult["response"].(string)
			return v
		}())
		verdictUpper := strings.ToUpper(verdict)

		switch {
		case strings.HasPrefix(verdictUpper, aletheiaCorrect):
			// ✓ Correct — grounding frags were reliable: reinforce them.
		bumpGrounding("factual", +0.03)
			return candidate, nil

		case strings.HasPrefix(verdictUpper, aletheiaFail):
			// Agent admits insufficient knowledge — grounding frags weren't enough: mild drop.
		bumpGrounding("factual", -0.05)
			enriched := composite + "\n\n### EPISTEMIC LIMITATION\n" +
				"After careful verification, the available knowledge is insufficient to answer this with confidence. " +
				"Be transparent about what is known, what is uncertain, and what would be needed to answer definitively. " +
				"Do NOT fabricate. Admitting the limits of knowledge is the correct response here.\n" +
				"### END EPISTEMIC LIMITATION"
			return e.runStandard(ctx, stimulus, enriched)

		case strings.HasPrefix(verdictUpper, aletheiaMinor):
			// Minor fix — targeted Reviser patch (no full restart)
			issue := extractVerdictDetail(verdict, aletheiaMinor)
			revisedComposite := composite + fmt.Sprintf(
				"\n\n### REVISER GUIDANCE\n"+
					"Your previous draft had a minor issue: %s\n"+
					"Keep everything that was correct. Fix only this specific issue.\n"+
					"### END REVISER GUIDANCE",
				issue,
			)
			// Revise in place — inject as new candidate on next loop iteration
			revResult, revErr := e.GenService.Generate(stimulus, map[string]interface{}{
				"num_ctx":     4096,
				"num_predict": 1024,
				"temperature": 0.3,
				"system":      revisedComposite,
			})
			if revErr != nil || ctx.Err() != nil {
				return candidate, nil // ship prior candidate on reviser failure
			}
			revised, _ := revResult["response"].(string)
			revised = strings.TrimSpace(revised)
			if revised != "" {
				return revised, nil // Reviser output is final — don't re-verify (CPU budget)
			}
			return candidate, nil

		case strings.HasPrefix(verdictUpper, aletheiaCritical):
			// 5-WHY Root Cause + Cross-Domain Recovery (arXiv:2603.24402, §3.3)
			// Instead of naive "don't do this again" guidance, we:
			//   1. Run a 5-WHY causal chain to extract the abstract mechanism μ(g)
			//   2. Query MemoryBank with μ(g) for cross-domain solutions
			//   3. Inject directed recovery guidance (mechanism + cross-domain hints)
			// This implements Equations 5-6 from the paper.
			if attempt < maxGeneratorCalls-1 {
				reason := extractVerdictDetail(verdict, aletheiaCritical)
				mechanism := e.runFiveWhy(ctx, stimulus, reason)

				// Cross-domain search: query MemoryBank using the abstract mechanism.
				// Constraint: search by mechanism vocabulary, not original problem vocabulary.
				crossDomainHint := ""
				if e.MemoryBankRef != nil && mechanism != "" {
					hits, _ := e.MemoryBankRef.QuerySimilarWeighted(ctx, mechanism, 2, WeightsFiveWhy)
					var hb strings.Builder
					causalHitIDs := make([]string, 0, 2)
					for _, h := range hits {
						if h.Belief.Causal >= 0.50 { // cross-domain: filter on Causal axis
							hb.WriteString(fmt.Sprintf("- %s\n", truncate(h.Content, 150)))
							if h.ID != "" {
								causalHitIDs = append(causalHitIDs, h.ID)
							}
						}
					}
					crossDomainHint = hb.String()
					if e.CertaintyUpdaterRef != nil && len(causalHitIDs) > 0 {
						go func(ids []string) {
							bCtx, cancel := context.WithTimeout(context.Background(), 8*time.Second)
							defer cancel()
							for _, id := range ids {
								e.CertaintyUpdaterRef.BumpBelief(bCtx, id, "causal", +0.04)
							}
						}(causalHitIDs)
					}
				}

				recovery := fmt.Sprintf(
					"\n\n### DIRECTED RECOVERY (5-WHY + Cross-Domain)\n"+
						"Critical flaw detected: %s\n"+
						"Root mechanism (5-WHY analysis): %s\n",
					reason, mechanism,
				)
				if crossDomainHint != "" {
					recovery += fmt.Sprintf(
						"Cross-domain insights addressing this mechanism:\n%s\n",
						crossDomainHint,
					)
				}
				recovery += "Approach the problem from a fundamentally different angle using the above.\n" +
					"### END DIRECTED RECOVERY"
				composite = composite + recovery
				continue
			}
			// Exhausted restarts — ship last candidate with uncertainty note
			return candidate, nil
		}

		// Unknown verdict format — ship candidate
		return candidate, nil
	}

	// Fallback: should not reach here but be safe
	if candidate != "" {
		return candidate, nil
	}
	return e.runStandard(ctx, stimulus, composite)
}

// extractVerdictDetail strips the verdict prefix and returns the detail string.
func extractVerdictDetail(verdict, prefix string) string {
	// Try exact prefix match first (handles case variations)
	for _, pfx := range []string{prefix + ":", prefix} {
		if idx := strings.Index(strings.ToUpper(verdict), pfx); idx >= 0 {
			detail := strings.TrimSpace(verdict[idx+len(pfx):])
			if detail != "" {
				return detail
			}
		}
	}
	return verdict
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
				"  VISION: <url_or_path>  (to analyse an image)\n"+
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
			frags, memErr := e.MemoryBankRef.QuerySimilarWeighted(ctx, query, 3, WeightsReAct)
			if memErr == nil {
				for _, f := range frags {
					observation += truncate(f.Content, 200) + "\n"
				}
			}
		case hasPrefix(thought, "VISION:") && e.VisionRef != nil:
			target := strings.TrimSpace(strings.TrimPrefix(thought, "VISION:"))
			input := VisionInput{}
			if strings.HasPrefix(target, "http://") || strings.HasPrefix(target, "https://") {
				input.URL = target
			} else {
				input.FilePath = target
			}
			vResult, vErr := e.VisionRef.Analyze(input)
			if vErr == nil && vResult.Description != "" {
				observation = fmt.Sprintf("[Vision — %s]\n%s", vResult.Model, vResult.Description)
				if len(vResult.Tags) > 0 {
					observation += fmt.Sprintf("\nTags: %s", strings.Join(vResult.Tags, ", "))
				}
			} else if vErr != nil {
				observation = fmt.Sprintf("(vision error: %v)", vErr)
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

// ─── ModeConsistency: Self-Consistency — N parallel samples + consensus ───────
//
// Per arXiv:2310.01798 (ICLR 2024): self-consistency (majority vote across
// independent samples) outperforms self-correction at equivalent compute budget.
// The key insight: N independent generations sample different reasoning paths;
// the answer that emerges most often is the most likely correct one.
//
// Implementation:
//   - 3 parallel goroutines each generate an independent candidate (temp=0.6)
//   - Consensus extractor finds the plurality answer via overlap scoring
//   - Tie → longest / most complete candidate wins
//   - Falls back to runStandard on GenService failure
//
// Extra LLM calls: 3 parallel (same cost as 3 sequential but ~3x faster on CPU)
// The model is small (gemma3:1b), so parallel goroutines don't compete badly.

const consistencyN = 3

func (e *SovereignEngine) runConsistency(ctx context.Context, stimulus, composite string) (string, error) {
if e.GenService == nil {
return e.runStandard(ctx, stimulus, composite)
}

type result struct {
text string
err  error
}
results := make([]result, consistencyN)
var wg sync.WaitGroup

for i := 0; i < consistencyN; i++ {
wg.Add(1)
go func(idx int) {
defer wg.Done()
// Each candidate uses a slightly different temperature to sample
// different reasoning paths — core of self-consistency diversity.
temp := 0.5 + float64(idx)*0.1 // 0.5, 0.6, 0.7
r, err := e.GenService.Generate(stimulus, map[string]interface{}{
"num_ctx":     4096,
"num_predict": 512,
"temperature": temp,
"system":      composite,
})
if err != nil || ctx.Err() != nil {
results[idx] = result{err: err}
return
}
text, _ := r["response"].(string)
results[idx] = result{text: strings.TrimSpace(text)}
}(i)
}
wg.Wait()

// Collect valid candidates
var candidates []string
for _, r := range results {
if r.err == nil && r.text != "" {
candidates = append(candidates, r.text)
}
}
if len(candidates) == 0 {
return e.runStandard(ctx, stimulus, composite)
}
if len(candidates) == 1 {
return candidates[0], nil
}

// Consensus: score each candidate by token overlap against all others.
// The plurality answer — most shared content — is the most consistent.
best := candidates[0]
bestScore := 0
for i, a := range candidates {
score := 0
aWords := tokenSet(a)
for j, b := range candidates {
if i == j {
continue
}
score += overlapScore(aWords, tokenSet(b))
}
if score > bestScore || (score == bestScore && len(a) > len(best)) {
bestScore = score
best = a
}
}
return best, nil
}

// tokenSet returns a deduplicated set of lowercase words from s (stops at 200 words).
func tokenSet(s string) map[string]struct{} {
set := make(map[string]struct{})
words := strings.Fields(strings.ToLower(s))
if len(words) > 200 {
words = words[:200]
}
for _, w := range words {
// Strip common punctuation so "answer." and "answer" match
w = strings.Trim(w, ".,!?;:\"'()")
if len(w) > 2 {
set[w] = struct{}{}
}
}
return set
}

// overlapScore counts words in set a that appear in set b.
func overlapScore(a, b map[string]struct{}) int {
score := 0
for w := range a {
if _, ok := b[w]; ok {
score++
}
}
return score
}

// ─── 5-WHY Root Cause Extractor ──────────────────────────────────────────────
//
// Implements Equation 5 from arXiv:2603.24402 (AI-Supervisor §3.3):
// Traces a gap through a causal chain to extract the abstract mechanism μ(g):
//
//   g → c1 → c2 → c3 → c4 → μ(g)
//        (each step: "WHY does c_{i-1} occur?")
//
// Each step produces a more abstract/fundamental cause anchored in knowledge
// (e.g., "safety methods fail" → "Lagrangian multiplier assumes stationarity"
//         → μ(g) = "optimization under non-stationarity").
//
// Used by the Aletheia CRITICAL_FLAW branch to extract a mechanism that can
// then be searched cross-domain (not just the surface-level flaw).
//
// Max 5 WHY steps, ~32 tokens each. Total: ~160 extra tokens on CRITICAL_FLAW path.
// Fires only when Aletheia has already paid the verifier cost — no new gating needed.

func (e *SovereignEngine) runFiveWhy(ctx context.Context, stimulus, initialFlaw string) string {
if e.GenService == nil || initialFlaw == "" {
return initialFlaw
}

cause := initialFlaw
for i := 0; i < 5; i++ {
if ctx.Err() != nil {
break
}
whyPrompt := fmt.Sprintf(
"Original question: %q\nCurrent identified issue: %q\n\n"+
"Ask: WHY does this issue fundamentally occur? Answer in ONE sentence identifying "+
"the deeper, more abstract root cause (e.g., a mathematical limitation, "+
"an assumption violation, a structural gap). Be specific but abstract.",
truncate(stimulus, 100), truncate(cause, 150),
)
result, err := e.GenService.Generate(whyPrompt, map[string]interface{}{
"num_ctx":     512,
"num_predict": 32,
"temperature": 0.1,
})
if err != nil {
break
}
newCause, _ := result["response"].(string)
newCause = strings.TrimSpace(newCause)
// Stop if model starts repeating or returns empty
if newCause == "" || strings.EqualFold(newCause, cause) {
break
}
cause = newCause
}
return cause
}

// ─── Cross-Domain Bridging ────────────────────────────────────────────────────

// runCrossdomainBridge implements the Cross-Domain Bridging atomic module.
//
// Algorithm:
//  1. Ask the LLM to classify the problem domain and name 2 structurally similar
//     fields where the same class of problem is well-solved.
//  2. Ask it to extract the key insight / technique from each analogous field.
//  3. Inject the cross-domain insight block into the composite so the final
//     generation can apply the foreign framework.
//
// This fires as an enrichment step — it returns an enriched composite, not a
// final answer. The cost is 2 fast LLM calls (~100 tok each).
func (e *SovereignEngine) runCrossdomainBridge(ctx context.Context, stimulus, composite string) (string, error) {
// Stage 1: identify domain + analogous fields
identifyPrompt := fmt.Sprintf(
"You are a cross-domain reasoning expert.\n"+
"Task: Identify the PRIMARY problem domain for this question, then name exactly 2 OTHER fields "+
"where the same structural problem (same constraints, trade-offs, or optimization pattern) is well-studied and solved.\n\n"+
"OUTPUT FORMAT (3 lines only):\n"+
"Domain: <primary domain>\n"+
"Analogy 1: <field> — <why it is structurally similar in one sentence>\n"+
"Analogy 2: <field> — <why it is structurally similar in one sentence>\n\n"+
"Question: %s", truncate(stimulus, 400),
)
identifyCtx, cancel := context.WithTimeout(ctx, 15*time.Second)
defer cancel()
_ = identifyCtx

identRes, err := e.GenService.Generate(identifyPrompt, map[string]interface{}{
"num_predict": 120,
"num_ctx":     2048,
"temperature": 0.3,
})
if err != nil || ctx.Err() != nil {
return e.runStandard(ctx, stimulus, composite)
}
identText, _ := identRes["response"].(string)
identText = strings.TrimSpace(identText)
if identText == "" {
return e.runStandard(ctx, stimulus, composite)
}

// Stage 2: extract the bridging insight from the two analogies
bridgePrompt := fmt.Sprintf(
"You identified these structural analogies for a problem:\n%s\n\n"+
"For each analogous field, extract the KEY technique or theorem that resolves "+
"the core constraint. Be specific and concrete — name the technique, not just the field.\n\n"+
"OUTPUT FORMAT (2 lines only):\n"+
"Technique 1: <field> uses <specific technique> — applying this here means: <one concrete application>\n"+
"Technique 2: <field> uses <specific technique> — applying this here means: <one concrete application>",
identText,
)
bridgeRes, err := e.GenService.Generate(bridgePrompt, map[string]interface{}{
"num_predict": 160,
"num_ctx":     2048,
"temperature": 0.25,
})
if err != nil || ctx.Err() != nil {
	// Partial enrichment — still useful
	return e.runStandard(ctx, stimulus, composite+
		"\n\n### CROSS-DOMAIN ANALOGIES\n"+identText+"\n### END ANALOGIES")
}
bridgeText, _ := bridgeRes["response"].(string)
bridgeText = strings.TrimSpace(bridgeText)

enrichment := fmt.Sprintf(
"\n\n### CROSS-DOMAIN BRIDGE\n"+
"**Domain mapping:**\n%s\n\n"+
"**Bridging techniques:**\n%s\n\n"+
"Apply the most structurally fitting technique above to the problem. "+
"If neither technique applies cleanly, explain why and fall back to domain-native reasoning.\n"+
"### END CROSS-DOMAIN BRIDGE",
identText, bridgeText,
)

return e.runStandard(ctx, stimulus, composite+enrichment)
}

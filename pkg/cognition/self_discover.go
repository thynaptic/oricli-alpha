package cognition

import (
	"context"
	"crypto/sha256"
	"encoding/json"
	"fmt"
	"strings"
	"sync"
	"time"
)

// ─── SELF-DISCOVER: Dynamic Reasoning Structure Composition ───────────────────
//
// Based on: "Self-Discover: Large Language Models Self-Compose Reasoning Structures"
// Google DeepMind, arXiv:2402.03620 — +32% over CoT on BigBench-Hard
//
// Core insight: Every task has a unique intrinsic reasoning structure. Instead of
// forcing it into one pre-defined mode (our keyword router), the model itself
// selects and composes the optimal combination of atomic modules — per query.
//
// Two-stage pipeline:
//   Stage 1 (2 LLM meta-calls, ~128 tok each):
//     SELECT+ADAPT — which modules are relevant? rephrase them for this task.
//     IMPLEMENT    — compose adapted modules into a JSON reasoning plan.
//   Stage 2 (0 extra calls):
//     Execute the plan by chaining existing SovereignEngine mode engines.
//
// CPU constraint adaptation:
//   - SELECT and ADAPT are merged into one call (saves 1 LLM round-trip)
//   - IMPLEMENT is a second call producing a compact JSON plan (max 5 steps)
//   - Discovered plans are cached by task-type fingerprint — pay once, reuse free
//   - Only fires at complexity ≥ 0.70 (keyword router handles everything below)
//
// Plan cache: in-memory LRU (cap 128), also written to ProvenanceSolved tier
// so DreamDaemon can consolidate effective structures into behavioral memory.

// ─── Atomic Module Registry ───────────────────────────────────────────────────
// These are the natural-language descriptions of our reasoning modes, as the SLM
// will see them during SELECT. They map 1:1 to our ReasoningMode engines.

type AtomicModule struct {
	Name        string
	Description string
	Mode        ReasoningMode
}

// atomicModules is the library the SLM chooses from during SELECT.
// Descriptions are written in the imperative style the paper uses.
var atomicModules = []AtomicModule{
	{
		Name:        "Step-by-Step Decomposition",
		Description: "Break the problem into ordered sub-problems and solve each in sequence, using the result of each step as input to the next.",
		Mode:        ModeLeastToMost,
	},
	{
		Name:        "Critical Self-Refinement",
		Description: "Generate an initial answer, critique it for errors or missing reasoning, and refine it into a polished final response.",
		Mode:        ModeSelfRefine,
	},
	{
		Name:        "Causal Chain Analysis",
		Description: "Identify the root cause, the mechanism linking cause to effect, and the outcome. Useful for WHY, HOW, and WHAT-IF questions.",
		Mode:        ModeCausal,
	},
	{
		Name:        "Multi-Perspective Debate",
		Description: "Present an advocate view, a skeptical counter-view, and a contrarian reframing, then synthesize a balanced verdict.",
		Mode:        ModeDebate,
	},
	{
		Name:        "Iterative Tool-Augmented Research",
		Description: "Think about what is unknown, use available tools (search, memory) to fill knowledge gaps, observe results, and update reasoning iteratively.",
		Mode:        ModeReAct,
	},
	{
		Name:        "Case-Based Adaptation",
		Description: "Search for the most similar solved problem in memory and adapt that solution to the current context.",
		Mode:        ModeCBR,
	},
	{
		Name:        "Targeted Gap Identification",
		Description: "Identify specific knowledge gaps or uncertainties in the question, then actively retrieve information to fill only those gaps before answering.",
		Mode:        ModeActive,
	},
	{
		Name:        "Symbolic Computation",
		Description: "Translate numeric or logical operations into executable code and run them to get a verified answer rather than predicting the result.",
		Mode:        ModePAL,
	},
}

// moduleDescriptionBlock returns the formatted module list for SELECT prompts.
func moduleDescriptionBlock() string {
	var sb strings.Builder
	for i, m := range atomicModules {
		sb.WriteString(fmt.Sprintf("%d. [%s]: %s\n", i+1, m.Name, m.Description))
	}
	return sb.String()
}

// ─── DiscoveredPlan ───────────────────────────────────────────────────────────

// DiscoveredPlan is the output of Stage 1. It contains the self-composed
// reasoning structure and the ordered list of mode engines to execute.
type DiscoveredPlan struct {
	Steps       []PlanStep    `json:"steps"`        // ordered execution steps
	Fingerprint string        `json:"fingerprint"`  // task-type fingerprint for caching
	DiscoveredAt time.Time    `json:"discovered_at"`
	RawJSON     string        `json:"raw_json"`     // original IMPLEMENT output
}

type PlanStep struct {
	Key         string        `json:"key"`         // e.g. "step_1"
	Instruction string        `json:"instruction"` // adapted module description
	Mode        ReasoningMode `json:"mode"`        // which engine to invoke
	ModeName    string        `json:"mode_name"`
}

// ─── Plan Cache ───────────────────────────────────────────────────────────────

// planCache stores discovered reasoning plans keyed by task-type fingerprint.
// LRU cap: 128 plans. Written to MemoryBank ProvenanceSolved for persistence.
type planCache struct {
	mu      sync.Mutex
	entries map[string]*DiscoveredPlan
	order   []string // insertion order for LRU eviction
	cap     int
}

var globalPlanCache = &planCache{
	entries: make(map[string]*DiscoveredPlan, 128),
	cap:     128,
}

func (c *planCache) get(fp string) (*DiscoveredPlan, bool) {
	c.mu.Lock()
	defer c.mu.Unlock()
	p, ok := c.entries[fp]
	return p, ok
}

func (c *planCache) set(fp string, plan *DiscoveredPlan) {
	c.mu.Lock()
	defer c.mu.Unlock()
	if len(c.order) >= c.cap {
		oldest := c.order[0]
		c.order = c.order[1:]
		delete(c.entries, oldest)
	}
	c.entries[fp] = plan
	c.order = append(c.order, fp)
}

// taskFingerprint creates a short hash from the first 80 chars of the stimulus.
// Same task type → same fingerprint → cache hit.
func taskFingerprint(stimulus string) string {
	s := strings.ToLower(strings.TrimSpace(stimulus))
	// Normalise: strip exact words, keep structure signals
	words := strings.Fields(s)
	if len(words) > 12 {
		words = words[:12]
	}
	h := sha256.Sum256([]byte(strings.Join(words, " ")))
	return fmt.Sprintf("%x", h[:6])
}

// ─── SELF-DISCOVER Engine ─────────────────────────────────────────────────────

// runSelfDiscover is the ModeDiscover execution path on SovereignEngine.
// It runs the two-stage SELF-DISCOVER pipeline and returns an enriched composite.
func (e *SovereignEngine) runSelfDiscover(ctx context.Context, stimulus, composite string) (string, error) {
	if e.GenService == nil {
		return e.runStandard(ctx, stimulus, composite)
	}

	fp := taskFingerprint(stimulus)

	// ── Cache hit path ─────────────────────────────────────────────────────
	if cached, ok := globalPlanCache.get(fp); ok {
		return e.executePlan(ctx, stimulus, composite, cached)
	}

	// ── Stage 1a: SELECT + ADAPT (merged into one call) ───────────────────
	// Ask the SLM to pick which modules are relevant AND rephrase each one
	// for this specific task — paper's SELECT and ADAPT in a single round-trip.
	selectAdaptPrompt := fmt.Sprintf(
		"You are a reasoning strategist. Given a question and a list of reasoning modules, "+
			"select 2-3 modules that are most useful for solving this specific question. "+
			"Then rephrase each selected module's description to be specific to this task.\n\n"+
			"QUESTION: %s\n\n"+
			"REASONING MODULES:\n%s\n"+
			"Output ONLY the selected modules, one per line:\n"+
			"MODULE_NAME: <name> | ADAPTED: <task-specific rephrasing>",
		truncateRE(stimulus, 350),
		moduleDescriptionBlock(),
	)

	saRes, err := e.GenService.Generate(selectAdaptPrompt, map[string]interface{}{
		"num_predict": 160,
		"num_ctx":     2048,
		"temperature": 0.3,
	})
	if err != nil || ctx.Err() != nil {
		return e.runStandard(ctx, stimulus, composite)
	}
	saText, _ := saRes["response"].(string)
	saText = strings.TrimSpace(saText)
	if saText == "" {
		return e.runStandard(ctx, stimulus, composite)
	}

	// Parse selected+adapted modules
	selected := parseSelectAdapt(saText)
	if len(selected) == 0 {
		return e.runStandard(ctx, stimulus, composite)
	}

	// ── Stage 1b: IMPLEMENT — compose into a JSON reasoning plan ──────────
	// The paper uses a human-written example to anchor the JSON format.
	// We embed a hardcoded demo to avoid another LLM call.
	var adaptedBlock strings.Builder
	for i, s := range selected {
		adaptedBlock.WriteString(fmt.Sprintf("%d. [%s]: %s\n", i+1, s.name, s.adapted))
	}

	implementPrompt := fmt.Sprintf(
		"You are a reasoning architect. Compose the following adapted reasoning steps into "+
			"a structured JSON plan with ordered keys (step_1, step_2, ...). "+
			"Each value is a concrete instruction for solving the question.\n\n"+
			"EXAMPLE OUTPUT:\n"+
			`{"step_1":"Identify the two entities being compared","step_2":"List the key differences for each","step_3":"Weigh the trade-offs and state the verdict"}`+
			"\n\nQUESTION: %s\n\nADAPTED MODULES:\n%s\n"+
			"OUTPUT JSON ONLY:",
		truncateRE(stimulus, 300),
		adaptedBlock.String(),
	)

	implRes, err := e.GenService.Generate(implementPrompt, map[string]interface{}{
		"num_predict": 160,
		"num_ctx":     2048,
		"temperature": 0.2,
	})
	if err != nil || ctx.Err() != nil {
		return e.runStandard(ctx, stimulus, composite)
	}
	implText, _ := implRes["response"].(string)
	implText = strings.TrimSpace(implText)

	// ── Build DiscoveredPlan ───────────────────────────────────────────────
	plan := buildPlan(fp, selected, implText)
	if plan == nil {
		return e.runStandard(ctx, stimulus, composite)
	}

	// Cache for future similar queries and signal server_v2 for MemoryBank persistence
	globalPlanCache.set(fp, plan)
	setLastDiscovered(fp)

	// ── Stage 2: Execute plan ─────────────────────────────────────────────
	return e.executePlan(ctx, stimulus, composite, plan)
}

// executePlan runs Stage 2: inject the discovered plan into the composite so the
// LLM follows the step-by-step structure during decoding. We also execute the
// primary mode engine for the first step to provide grounded context.
func (e *SovereignEngine) executePlan(ctx context.Context, stimulus, composite string, plan *DiscoveredPlan) (string, error) {
	var sb strings.Builder
	sb.WriteString(composite)
	sb.WriteString("\n\n### SELF-DISCOVERED REASONING PLAN\n")
	sb.WriteString("Follow this task-specific reasoning structure to answer the question:\n\n")

	for _, step := range plan.Steps {
		sb.WriteString(fmt.Sprintf("**%s** (%s): %s\n", step.Key, step.ModeName, step.Instruction))
	}

	// Execute the first step's mode engine to provide concrete grounded context
	// (avoids burning LLM calls on every step — first step primes the composite)
	if len(plan.Steps) > 0 {
		primaryMode := plan.Steps[0].Mode
		var enriched string
		var err error
		switch primaryMode {
		case ModeCBR:
			enriched, err = e.runCBR(ctx, stimulus, "")
		case ModePAL:
			enriched, err = e.runPAL(ctx, stimulus, "")
		case ModeActive:
			enriched, err = e.runActive(ctx, stimulus, "")
		case ModeLeastToMost:
			enriched, err = e.runLeastToMost(ctx, stimulus, "")
		case ModeSelfRefine:
			enriched, err = e.runSelfRefine(ctx, stimulus, "")
		case ModeReAct:
			enriched, err = e.runReAct(ctx, stimulus, "")
		case ModeDebate:
			enriched, err = e.runDebate(ctx, stimulus, "")
		case ModeCausal:
			enriched, err = e.runCausal(ctx, stimulus, "")
		}
		if err == nil && enriched != "" && enriched != composite {
			// Extract only the mode-specific enrichment (strip the base composite)
			enrichment := strings.TrimPrefix(enriched, composite)
			if enrichment != "" {
				sb.WriteString("\n")
				sb.WriteString(strings.TrimSpace(enrichment))
			}
		}
	}

	sb.WriteString("\n\n**Execute each step in order. Your final response must reflect the complete reasoning chain.**")
	sb.WriteString("\n### END SELF-DISCOVERED PLAN")

	return sb.String(), nil
}

// ─── Parsing helpers ──────────────────────────────────────────────────────────

type selectedModule struct {
	name    string
	adapted string
	mode    ReasoningMode
}

// parseSelectAdapt parses lines of the form:
// MODULE_NAME: <name> | ADAPTED: <description>
func parseSelectAdapt(text string) []selectedModule {
	var out []selectedModule
	for _, line := range strings.Split(text, "\n") {
		line = strings.TrimSpace(line)
		if line == "" {
			continue
		}
		// Accept various separator styles the SLM might produce
		var name, adapted string
		if idx := strings.Index(line, "| ADAPTED:"); idx >= 0 {
			name = strings.TrimSpace(strings.TrimPrefix(line[:idx], "MODULE_NAME:"))
			adapted = strings.TrimSpace(line[idx+len("| ADAPTED:"):])
		} else if idx := strings.Index(line, "|"); idx >= 0 {
			name = strings.TrimSpace(line[:idx])
			adapted = strings.TrimSpace(line[idx+1:])
			name = strings.TrimPrefix(name, "MODULE_NAME:")
			name = strings.TrimPrefix(name, "-")
			name = strings.TrimSpace(name)
		} else {
			// Fallback: treat the whole line as name, use description as adapted
			name = strings.TrimSpace(line)
		}

		mode := matchModuleByName(name)
		if adapted == "" {
			adapted = name // degenerate fallback
		}
		if name != "" {
			out = append(out, selectedModule{name: name, adapted: adapted, mode: mode})
		}
		if len(out) >= 3 {
			break
		}
	}
	return out
}

// matchModuleByName finds the closest AtomicModule for a given name string.
// Uses substring matching — robust to SLM paraphrasing.
func matchModuleByName(name string) ReasoningMode {
	nl := strings.ToLower(name)
	best := ModeStandard
	bestScore := 0
	for _, m := range atomicModules {
		ml := strings.ToLower(m.Name)
		score := 0
		for _, word := range strings.Fields(ml) {
			if strings.Contains(nl, word) {
				score++
			}
		}
		if score > bestScore {
			bestScore = score
			best = m.Mode
		}
	}
	return best
}

// buildPlan constructs a DiscoveredPlan from the parsed SELECT+ADAPT output
// and the raw IMPLEMENT JSON string.
func buildPlan(fp string, selected []selectedModule, implJSON string) *DiscoveredPlan {
	if len(selected) == 0 {
		return nil
	}

	// Parse the IMPLEMENT JSON into ordered steps
	implJSON = extractJSON(implJSON)
	var rawMap map[string]string
	_ = json.Unmarshal([]byte(implJSON), &rawMap)

	// Build plan steps. If JSON parse failed, fall back to adapted module descriptions.
	var steps []PlanStep
	if len(rawMap) > 0 {
		// Ordered by step_1, step_2, step_3...
		for i := 1; i <= 5; i++ {
			key := fmt.Sprintf("step_%d", i)
			instr, ok := rawMap[key]
			if !ok {
				break
			}
			// Map step to the corresponding selected module (by index, wrap if fewer)
			modIdx := (i - 1) % len(selected)
			steps = append(steps, PlanStep{
				Key:         key,
				Instruction: instr,
				Mode:        selected[modIdx].mode,
				ModeName:    selected[modIdx].name,
			})
		}
	}

	// Fallback: use adapted descriptions as plan steps directly
	if len(steps) == 0 {
		for i, s := range selected {
			steps = append(steps, PlanStep{
				Key:         fmt.Sprintf("step_%d", i+1),
				Instruction: s.adapted,
				Mode:        s.mode,
				ModeName:    s.name,
			})
		}
	}

	if len(steps) == 0 {
		return nil
	}

	return &DiscoveredPlan{
		Steps:        steps,
		Fingerprint:  fp,
		DiscoveredAt: time.Now(),
		RawJSON:      implJSON,
	}
}

// extractJSON pulls the first {...} block from a string.
// Handles cases where the SLM wraps JSON in prose or markdown.
func extractJSON(s string) string {
	start := strings.Index(s, "{")
	end := strings.LastIndex(s, "}")
	if start >= 0 && end > start {
		return s[start : end+1]
	}
	return s
}

// ─── Exported helpers for server_v2 plan persistence ─────────────────────────

var lastDiscoveredFP struct {
sync.Mutex
value string
}

// setLastDiscovered records the most recently discovered plan fingerprint
// so server_v2 can persist it to MemoryBank after the request completes.
func setLastDiscovered(fp string) {
lastDiscoveredFP.Lock()
lastDiscoveredFP.value = fp
lastDiscoveredFP.Unlock()
}

// GetLastDiscoveredFingerprint returns and clears the last discovered plan fingerprint.
// Returns "" if no new plan was discovered this request.
func GetLastDiscoveredFingerprint() string {
lastDiscoveredFP.Lock()
defer lastDiscoveredFP.Unlock()
fp := lastDiscoveredFP.value
lastDiscoveredFP.value = "" // consume once
return fp
}

// GetCachedPlan looks up a plan by fingerprint in the global cache.
func GetCachedPlan(fp string) (*DiscoveredPlan, bool) {
return globalPlanCache.get(fp)
}

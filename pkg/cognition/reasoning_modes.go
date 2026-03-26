package cognition

import (
	"regexp"
	"strings"
)

// ReasoningMode selects the cognitive execution path for a given stimulus.
type ReasoningMode int

const (
	ModeStandard    ReasoningMode = iota // Default pipeline — no extra LLM calls
	ModeCBR                              // Case-Based Reasoning — adapted past solutions
	ModePAL                              // Program-Aided Language — Python execution for math/logic
	ModeActive                           // Active Prompting — targeted gap identification + tool fill
	ModeLeastToMost                      // Least-to-Most — ordered chained decomposition
	ModeSelfRefine                       // Self-Refine — critique + single regeneration pass
	ModeReAct                            // ReAct — Think→Act→Observe loop (max 3 hops)
	ModeDebate                           // Multi-Agent Debate — Advocate+Skeptic+Contrarian→Judge synthesis
	ModeCausal                           // Causal Reasoning — WHY/WHAT-IF/HOW causal chain extraction
	ModeDiscover                         // SELF-DISCOVER — LLM self-composes optimal reasoning plan (arXiv:2402.03620)
)

func (m ReasoningMode) String() string {
	return [...]string{"Standard", "CBR", "PAL", "Active", "LeastToMost", "SelfRefine", "ReAct", "Debate", "Causal", "Discover"}[m]
}

var (
	// PAL: arithmetic expressions, unit conversions, formulas
	reMath = regexp.MustCompile(`(?i)(calculat|comput|solv|convert|how many|what is \d|=\?|\d+[\+\-\*\/\^]\d+|integral|derivative|percent|formula|equation|proof)`)

	// ReAct: multi-tool research queries
	reReAct = regexp.MustCompile(`(?i)(research|find.*and.*then|look up.*and|search.*then|compare.*sources|latest.*on|who is.*and what|news about)`)

	// LeastToMost: compound multi-step questions
	reLeastMost = regexp.MustCompile(`(?i)(step by step|walk me through|explain.*then|first.*then.*finally|how do i.*from scratch|build.*plan|break.*down)`)

	// SelfRefine triggers: open-ended complex generation
	reSelfRefine = regexp.MustCompile(`(?i)(write.*essay|draft.*proposal|design.*system|create.*plan|comprehensive|detailed.*analysis|full.*report)`)

	// Debate: contested opinions, should/better/vs comparisons, ethical dilemmas
	reDebate = regexp.MustCompile(`(?i)(should (we|i|they|you)|is it (better|worse|right|wrong|ethical)|pros and cons|argue (for|against)|debate|what.*think about|opinion on|defend.*position|is.*good idea|best approach|versus|trade.?off|which is better)`)

	// Causal: why/how/what-if chains, root cause analysis
	reCausal = regexp.MustCompile(`(?i)(why (does|did|is|are|would|do)|what (causes|caused|led to|results in|happens if|would happen)|how does.*work|root cause|because of|as a result|consequence of|what if|hypothetically|impact of|effect of|reason (for|why))`)
)

// ClassifyReasoningMode returns the optimal ReasoningMode for the given stimulus.
// Fast path: keyword + budget heuristics, no LLM call, < 1ms.
func ClassifyReasoningMode(stimulus string, budget AdaptiveBudget) ReasoningMode {
	s := strings.TrimSpace(stimulus)

	// PAL wins for anything math/logic — Python beats LLM prediction every time
	if reMath.MatchString(s) {
		return ModePAL
	}

	// SELF-DISCOVER: highest complexity queries get dynamic module composition.
	// Above 0.70 the keyword router picks the wrong single mode too often.
	// The 2 meta-calls are worth it — paper shows +32% over CoT at this tier.
	if budget.Complexity >= 0.70 {
		return ModeDiscover
	}

	// Causal: why/how-does/what-if — dedicated causal chain extraction
	if reCausal.MatchString(s) && budget.Complexity > 0.3 {
		return ModeCausal
	}

	// Debate: contested "should/better/vs" with high complexity → 4-agent synthesis
	if reDebate.MatchString(s) && budget.Complexity > 0.65 {
		return ModeDebate
	}

	// ReAct for multi-source research (needs iterative tool use)
	if reReAct.MatchString(s) && budget.Complexity > 0.35 {
		return ModeReAct
	}

	// LeastToMost for explicit step-by-step construction tasks
	if reLeastMost.MatchString(s) && budget.Complexity > 0.3 {
		return ModeLeastToMost
	}

	// SelfRefine for complex generative tasks (essay, design, proposal)
	if reSelfRefine.MatchString(s) && budget.Complexity > 0.5 {
		return ModeSelfRefine
	}

	// CBR for anything complex enough that a past solution might exist
	// (lower bar — CBR is free if no solved case found, just falls through)
	if budget.Complexity > 0.45 {
		return ModeCBR
	}

	// Active prompting upgrade: if DetectUncertainty would fire, use Active mode
	// to get targeted gap identification instead of a single broad search
	if needsSearch, _ := DetectUncertainty(s); needsSearch {
		return ModeActive
	}

	return ModeStandard
}

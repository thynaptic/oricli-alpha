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
)

func (m ReasoningMode) String() string {
	return [...]string{"Standard", "CBR", "PAL", "Active", "LeastToMost", "SelfRefine", "ReAct"}[m]
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
)

// ClassifyReasoningMode returns the optimal ReasoningMode for the given stimulus.
// Fast path: keyword + budget heuristics, no LLM call, < 1ms.
func ClassifyReasoningMode(stimulus string, budget AdaptiveBudget) ReasoningMode {
	s := strings.TrimSpace(stimulus)

	// PAL wins for anything math/logic — Python beats LLM prediction every time
	if reMath.MatchString(s) {
		return ModePAL
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

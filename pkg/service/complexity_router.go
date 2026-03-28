package service

// ComplexityRouter analyzes incoming chat messages and classifies them into
// compute tiers so GenerationService can automatically route hard tasks to
// larger models without requiring callers to set explicit tier flags.
//
// Tiers:
//
//	TierLocal   — Ollama small model (default, fast, free)
//	TierMedium  — Ollama mid/code model (moderate tasks)
//	TierHeavy   — RunPod 32B+ (grid reasoning, proofs, long synthesis)
//
// Enabled by env: RUNPOD_COMPLEXITY_ROUTING=true
// Override threshold: COMPLEXITY_HEAVY_THRESHOLD (default 0.65, range 0.0–1.0)
//
// The router never blocks or makes network calls — pure signal extraction, <1ms.

import (
	"math"
	"os"
	"regexp"
	"strconv"
	"strings"
)

// ComplexityTier is the compute class a request requires.
type ComplexityTier int

const (
	TierLocal  ComplexityTier = iota // Ollama small model
	TierMedium                       // Ollama code/mid model
	TierHeavy                        // RunPod 32B+
)

func (t ComplexityTier) String() string {
	switch t {
	case TierMedium:
		return "medium"
	case TierHeavy:
		return "heavy"
	default:
		return "local"
	}
}

// ComplexityResult is the router's verdict on a request.
type ComplexityResult struct {
	Tier    ComplexityTier
	Score   float64 // 0.0–1.0 composite signal strength
	Reasons []string
}

// ── Compiled signal patterns ──────────────────────────────────────────────────

var (
	// ARC-style grid: nested JSON integer arrays  [[0,1,2],[3,4,5]]
	reGrid = regexp.MustCompile(`\[\s*\[\s*\d`)

	// Math / formal reasoning
	reMath = regexp.MustCompile(`(?i)\b(prove|theorem|lemma|corollary|integral|derivative|eigenvalue|matrix\s+inverse|gradient|hessian|modular\s+arithmetic|prime\s+factori[sz]ation|NP-hard|complexity\s+class)\b`)

	// Multi-step algorithmic code
	reAlgo = regexp.MustCompile(`(?i)\b(implement\s+.{0,40}(algorithm|data\s+structure|compiler|interpreter|parser|scheduler|optimizer)|dynamic\s+programming|graph\s+traversal|shortest\s+path|topological\s+sort|binary\s+search\s+tree|segment\s+tree|fenwick|suffix\s+array)\b`)

	// Deep research / synthesis
	reResearch = regexp.MustCompile(`(?i)\b(compare\s+.{0,40}(paper|approach|method|architecture)|literature\s+review|state\s+of\s+the\s+art|survey\s+of|systematic\s+review|meta-analysis|critically\s+anal[yz]e)\b`)

	// Logical multi-step chains
	reLogicChain = regexp.MustCompile(`(?i)(therefore|thus|it\s+follows|by\s+induction|base\s+case|inductive\s+step|proof\s+by|contradict|QED|∀|∃|⊢|⊨)`)

	// Color pattern recognition in grids (ARC-specific escalation)
	reColorGrid = regexp.MustCompile(`(?i)(color|colour|pixel|grid|transformation|output\s+grid|input\s+grid|pattern\s+rule|ARC|abstraction\s+reasoning)`)

	// Explicit user escalation hints
	reUserEscalate = regexp.MustCompile(`(?i)(use\s+(the\s+)?(big|large|heavy|smart|powerful|best)\s+model|think\s+harder|use\s+more\s+compute|need\s+(your\s+)?best|32b|70b|405b)`)
)

// ClassifyComplexity analyzes messages and returns a routing verdict.
// Fast, deterministic, no I/O.
func ClassifyComplexity(messages []map[string]string) ComplexityResult {
	if os.Getenv("RUNPOD_COMPLEXITY_ROUTING") != "true" {
		return ComplexityResult{Tier: TierLocal, Score: 0}
	}

	heavyThreshold := 0.65
	if v := os.Getenv("COMPLEXITY_HEAVY_THRESHOLD"); v != "" {
		if f, err := strconv.ParseFloat(v, 64); err == nil && f > 0 && f <= 1 {
			heavyThreshold = f
		}
	}

	// Concatenate all message content for token length estimate only.
	// Pattern matching runs only on the last user message to avoid
	// stale ARC/grid context from prior turns triggering false escalation.
	var sbAll strings.Builder
	lastUserMsg := ""
	totalChars := 0
	for _, m := range messages {
		if content, ok := m["content"]; ok {
			sbAll.WriteString(content)
			sbAll.WriteRune('\n')
			totalChars += len(content)
			if role, ok := m["role"]; ok && role == "user" {
				lastUserMsg = content
			}
		}
	}
	// Fall back to full text if no user message found
	patternText := lastUserMsg
	if patternText == "" {
		patternText = sbAll.String()
	}

	var signals []signal
	signals = append(signals, extractSignals(patternText, totalChars)...)

	score, reasons := scoreSignals(signals)
	tier := TierLocal
	if score >= heavyThreshold {
		tier = TierHeavy
	} else if score >= 0.35 {
		tier = TierMedium
	}

	return ComplexityResult{Tier: tier, Score: score, Reasons: reasons}
}

// ── Internal signal types ─────────────────────────────────────────────────────

type signal struct {
	weight float64
	reason string
}

func extractSignals(text string, totalChars int) []signal {
	var signals []signal

	// ── Hard signals (individually sufficient for Heavy) ──────────────────

	// Grid arrays in prompt → almost certainly ARC or similar spatial task
	if gridMatches := reGrid.FindAllString(text, -1); len(gridMatches) > 0 {
		gridCount := len(gridMatches)
		w := math.Min(0.5+float64(gridCount)*0.05, 0.85)
		signals = append(signals, signal{w, "grid arrays detected"})
	}

	// Grid + color language → ARC color task → strong escalation
	if reGrid.MatchString(text) && reColorGrid.MatchString(text) {
		signals = append(signals, signal{0.90, "ARC grid + color pattern task"})
	}

	// User explicitly asked for big model
	if reUserEscalate.MatchString(text) {
		signals = append(signals, signal{0.95, "user requested powerful model"})
	}

	// ── Medium-weight signals ─────────────────────────────────────────────

	if reMath.MatchString(text) {
		signals = append(signals, signal{0.55, "mathematical proof/computation"})
	}

	if reAlgo.MatchString(text) {
		signals = append(signals, signal{0.50, "complex algorithmic task"})
	}

	if reResearch.MatchString(text) {
		signals = append(signals, signal{0.45, "research synthesis task"})
	}

	if reLogicChain.MatchString(text) {
		signals = append(signals, signal{0.40, "formal logic chain"})
	}

	// ── Length-based signals ──────────────────────────────────────────────

	estimatedTokens := totalChars / 4
	if estimatedTokens > 3000 {
		signals = append(signals, signal{0.45, "long context (>3k tokens estimated)"})
	} else if estimatedTokens > 1500 {
		signals = append(signals, signal{0.25, "medium context (>1.5k tokens)"})
	}

	// ── Multi-turn depth ──────────────────────────────────────────────────
	// Handled by caller passing all messages — already captured in totalChars

	return signals
}

// scoreSignals combines signals using a noisy-OR formula:
// combined = 1 - Π(1 - wᵢ)
// This ensures multiple medium signals can together trigger Heavy routing.
func scoreSignals(signals []signal) (float64, []string) {
	if len(signals) == 0 {
		return 0, nil
	}
	combined := 0.0
	var reasons []string
	for _, s := range signals {
		combined = 1.0 - (1.0-combined)*(1.0-s.weight)
		reasons = append(reasons, s.reason)
	}
	return combined, reasons
}

// ── Convenience helpers ───────────────────────────────────────────────────────

// IsComplexityRoutingEnabled returns true when auto-escalation is active.
func IsComplexityRoutingEnabled() bool {
	return os.Getenv("RUNPOD_COMPLEXITY_ROUTING") == "true"
}

// ApplyComplexityRouting injects tier flags into options based on the
// complexity classification. Mutates options in place — safe to call
// before passing options to ChatStream.
// No-op if complexity routing is disabled or result is TierLocal.
func ApplyComplexityRouting(result ComplexityResult, options map[string]interface{}) {
	if result.Tier == TierLocal {
		return
	}
	// Don't override an explicit model choice the caller already set
	if m, ok := options["model"].(string); ok && m != "" {
		return
	}
	switch result.Tier {
	case TierHeavy:
		options["_complexity_tier"] = "heavy"
		options["_complexity_score"] = result.Score
		options["_complexity_reasons"] = strings.Join(result.Reasons, "; ")
		// Signal to GenerationService to prefer RunPod regardless of RUNPOD_PRIMARY
		options["_escalate_to_runpod"] = true
	case TierMedium:
		options["_complexity_tier"] = "medium"
		options["use_code_model"] = true
	}
}

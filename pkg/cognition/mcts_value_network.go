package cognition

import (
	"context"
	"strings"
	"unicode"
)

// ValueNetwork scores a candidate answer quickly without LLM calls.
// Estimates are in [0, 1]: 0 = very low quality, 1 = high quality.
// Implementations must be goroutine-safe.
type ValueNetwork interface {
	Estimate(ctx context.Context, query, candidate string) (float64, error)
}

// ValueNetConfig wires a ValueNetwork into the MCTS search as a fast
// pre-screening layer before expensive LLM evaluation callbacks.
//
// Three scoring zones:
//
//	score < AcceptBelow     → low quality, skip LLM, return VN score directly
//	AcceptBelow ≤ score < EscalateAbove → medium quality, use VN score directly
//	score ≥ EscalateAbove   → promising, run full dual-LLM evaluation
type ValueNetConfig struct {
	Network       ValueNetwork
	AcceptBelow   float64 // default 0.35 — reject without LLM below this
	EscalateAbove float64 // default 0.60 — run full LLM eval above this
}

func (c *ValueNetConfig) acceptBelow() float64 {
	if c.AcceptBelow > 0 {
		return c.AcceptBelow
	}
	return 0.35
}

func (c *ValueNetConfig) escalateAbove() float64 {
	if c.EscalateAbove > 0 {
		return c.EscalateAbove
	}
	return 0.60
}

// HeuristicValueNetwork scores candidates using lightweight text features.
// Zero external calls — suitable as a fast pre-filter before LLM evaluation.
//
// Factors (additive, clamped to [0, 1]):
//   - Baseline:           0.50
//   - Text length:        ±0.15 / -0.20
//   - Structural markers: +0.10 (numbered lists, step words)
//   - Logical connectors: +0.08 (because, therefore, however…)
//   - Sentence completion:+0.05 (ends with . ? !)
//   - Vocabulary richness:+0.05 (type/token ratio)
//   - Query relevance:    +0.20 (word overlap with query)
//   - Hedge penalty:      -0.05 (starts with "I think", "maybe"…)
type HeuristicValueNetwork struct{}

var (
	stepMarkers = []string{
		"first", "second", "third", "then", "next", "finally",
		"step ", "1.", "2.", "3.", "lastly",
	}
	logicConnectors = []string{
		"because", "therefore", "however", "thus", "since",
		"although", "whereas", "consequently", "nevertheless",
	}
	hedgePhrases = []string{
		"i think", "i believe", "i'm not sure", "maybe ", "possibly ",
		"perhaps ", "it might be", "i guess",
	}
)

// Estimate scores the candidate against the query using heuristic features.
// The query may be empty — only word-overlap scoring is skipped in that case.
func (h *HeuristicValueNetwork) Estimate(_ context.Context, query, candidate string) (float64, error) {
	candidate = strings.TrimSpace(candidate)
	if candidate == "" {
		return 0.0, nil
	}
	lower := strings.ToLower(candidate)
	score := 0.50

	// ── Length quality ────────────────────────────────────────────────────────
	n := len(candidate)
	switch {
	case n < 30:
		score -= 0.20
	case n >= 80 && n <= 1500:
		score += 0.15
	case n > 1500:
		score += 0.05 // long but not penalised
	}

	// ── Structural markers (step words / numbered lists) ─────────────────────
	for _, w := range stepMarkers {
		if strings.Contains(lower, w) {
			score += 0.10
			break
		}
	}

	// ── Logical connectors ───────────────────────────────────────────────────
	for _, w := range logicConnectors {
		if strings.Contains(lower, w) {
			score += 0.08
			break
		}
	}

	// ── Sentence completion ──────────────────────────────────────────────────
	last := rune(candidate[len(candidate)-1])
	if last == '.' || last == '?' || last == '!' {
		score += 0.05
	}

	// ── Vocabulary richness (type/token ratio, capped bonus) ─────────────────
	words := strings.Fields(lower)
	if len(words) >= 5 {
		unique := make(map[string]struct{}, len(words))
		for _, w := range words {
			w = strings.TrimFunc(w, unicode.IsPunct)
			if len(w) >= 3 {
				unique[w] = struct{}{}
			}
		}
		ttr := float64(len(unique)) / float64(len(words))
		score += clamp01Local(ttr) * 0.05
	}

	// ── Query relevance (word overlap) ───────────────────────────────────────
	if query != "" {
		qWords := hnWordSet(strings.ToLower(query), 4)
		if len(qWords) > 0 {
			cWords := hnWordSet(lower, 4)
			overlap := 0
			for w := range qWords {
				if _, ok := cWords[w]; ok {
					overlap++
				}
			}
			score += float64(overlap) / float64(len(qWords)) * 0.20
		}
	}

	// ── Hedge penalty ─────────────────────────────────────────────────────────
	for _, phrase := range hedgePhrases {
		if strings.HasPrefix(lower, phrase) {
			score -= 0.05
			break
		}
	}

	return clamp01Local(score), nil
}

// hnWordSet returns the set of words in text with at least minLen runes,
// stripped of surrounding punctuation.
func hnWordSet(text string, minLen int) map[string]struct{} {
	fields := strings.Fields(text)
	m := make(map[string]struct{}, len(fields))
	for _, f := range fields {
		f = strings.TrimFunc(f, unicode.IsPunct)
		if len([]rune(f)) >= minLen {
			m[f] = struct{}{}
		}
	}
	return m
}

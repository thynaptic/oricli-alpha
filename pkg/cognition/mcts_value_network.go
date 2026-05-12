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

// ValueNetConfig wires a ValueNetwork into MCTS as a fast pre-screening layer
// before expensive evaluation callbacks.
type ValueNetConfig struct {
	Network       ValueNetwork
	AcceptBelow   float64 // default 0.35
	EscalateAbove float64 // default 0.60
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
// It performs zero external calls, making it safe as a fast MCTS pre-filter.
type HeuristicValueNetwork struct{}

var (
	valueNetStepMarkers = []string{
		"first", "second", "third", "then", "next", "finally",
		"step ", "1.", "2.", "3.", "lastly",
	}
	valueNetLogicConnectors = []string{
		"because", "therefore", "however", "thus", "since",
		"although", "whereas", "consequently", "nevertheless",
	}
	valueNetHedgePhrases = []string{
		"i think", "i believe", "i'm not sure", "maybe ", "possibly ",
		"perhaps ", "it might be", "i guess",
	}
)

// Estimate scores the candidate against the query using simple quality and
// relevance signals. The query may be empty; relevance scoring is then skipped.
func (h *HeuristicValueNetwork) Estimate(_ context.Context, query, candidate string) (float64, error) {
	candidate = strings.TrimSpace(candidate)
	if candidate == "" {
		return 0.0, nil
	}

	lower := strings.ToLower(candidate)
	score := 0.50

	switch n := len(candidate); {
	case n < 30:
		score -= 0.20
	case n >= 80 && n <= 1500:
		score += 0.15
	case n > 1500:
		score += 0.05
	}

	for _, marker := range valueNetStepMarkers {
		if strings.Contains(lower, marker) {
			score += 0.10
			break
		}
	}

	for _, connector := range valueNetLogicConnectors {
		if strings.Contains(lower, connector) {
			score += 0.08
			break
		}
	}

	last := rune(candidate[len(candidate)-1])
	if last == '.' || last == '?' || last == '!' {
		score += 0.05
	}

	words := strings.Fields(lower)
	if len(words) >= 5 {
		unique := make(map[string]struct{}, len(words))
		for _, word := range words {
			word = strings.TrimFunc(word, unicode.IsPunct)
			if len(word) >= 3 {
				unique[word] = struct{}{}
			}
		}
		score += clamp01Local(float64(len(unique))/float64(len(words))) * 0.05
	}

	if query != "" {
		queryWords := valueNetWordSet(strings.ToLower(query), 4)
		if len(queryWords) > 0 {
			candidateWords := valueNetWordSet(lower, 4)
			overlap := 0
			for word := range queryWords {
				if _, ok := candidateWords[word]; ok {
					overlap++
				}
			}
			score += float64(overlap) / float64(len(queryWords)) * 0.20
		}
	}

	for _, phrase := range valueNetHedgePhrases {
		if strings.HasPrefix(lower, phrase) {
			score -= 0.05
			break
		}
	}

	return clamp01Local(score), nil
}

func valueNetWordSet(text string, minLen int) map[string]struct{} {
	fields := strings.Fields(text)
	out := make(map[string]struct{}, len(fields))
	for _, field := range fields {
		field = strings.TrimFunc(field, unicode.IsPunct)
		if len([]rune(field)) >= minLen {
			out[field] = struct{}{}
		}
	}
	return out
}

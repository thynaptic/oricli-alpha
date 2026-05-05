package epistemics

import (
	"context"
	"fmt"
	"strings"
)

// Enabled reports whether the epistemics engine is active.
func Enabled() bool { return cfg.Enabled }

// Run executes the conjecture-criticism-synthesis loop and returns an
// explanation that has been dialectically tested against itself.
func Run(ctx context.Context, cycle ConjectionCycle) (ExplanatoryResult, error) {
	if !cfg.Enabled {
		return ExplanatoryResult{}, fmt.Errorf("epistemics disabled")
	}

	maxIter := cycle.MaxIter
	if maxIter <= 0 {
		maxIter = cfg.MaxIter
	}
	threshold := cycle.Threshold
	if threshold <= 0 {
		threshold = cfg.Threshold
	}

	var trace ConjectionTrace
	prior := ""

	for i := 0; i < maxIter; i++ {
		conj, err := conjecture(ctx, cycle.Query, cycle.Context, prior)
		if err != nil {
			return ExplanatoryResult{}, err
		}
		if i == 0 {
			trace.Initial = conj
		}

		crit, err := criticize(ctx, conj)
		if err != nil {
			return ExplanatoryResult{}, err
		}
		trace.Criticisms = append(trace.Criticisms, crit.Issues...)

		escalate := crit.Severity >= threshold
		syn, err := synthesize(ctx, conj, crit, escalate)
		if err != nil {
			return ExplanatoryResult{}, err
		}
		if escalate {
			trace.Escalated = true
		}

		trace.Iterations = i + 1

		if crit.Severity < 0.2 || converged(conj, syn) {
			trace.Survived = true
			trace.Refined = syn
			return ExplanatoryResult{Explanation: syn, Trace: trace}, nil
		}

		prior = syn
	}

	trace.Refined = prior
	return ExplanatoryResult{Explanation: prior, Trace: trace}, nil
}

func converged(a, b string) bool {
	wa := wordSet(a)
	wb := wordSet(b)
	if len(wa) == 0 || len(wb) == 0 {
		return false
	}
	overlap := 0
	for w := range wa {
		if wb[w] {
			overlap++
		}
	}
	return float64(overlap)/float64(len(wa)) > 0.75
}

func wordSet(s string) map[string]bool {
	words := strings.Fields(strings.ToLower(s))
	m := make(map[string]bool, len(words))
	for _, w := range words {
		w = strings.Trim(w, ".,!?;:\"'")
		if len(w) > 3 {
			m[w] = true
		}
	}
	return m
}

// FlattenContext reduces oracle messages to a concise context string for the
// conjecture pass — keeps the last 6 turns, skips system messages.
func FlattenContext(msgs []map[string]string) string {
	var relevant []map[string]string
	for _, m := range msgs {
		if m["role"] != "system" {
			relevant = append(relevant, m)
		}
	}
	if len(relevant) > 6 {
		relevant = relevant[len(relevant)-6:]
	}
	var sb strings.Builder
	for _, m := range relevant {
		role := m["role"]
		content := strings.TrimSpace(m["content"])
		if content == "" {
			continue
		}
		if len(content) > 300 {
			content = content[:300] + "…"
		}
		sb.WriteString(role)
		sb.WriteString(": ")
		sb.WriteString(content)
		sb.WriteString("\n")
	}
	return strings.TrimSpace(sb.String())
}

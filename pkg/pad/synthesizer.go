package pad

import (
	"context"
	"fmt"
	"log"
	"strings"
)

// Synthesizer merges parallel WorkerResult outputs into a single coherent response.
type Synthesizer struct {
	Distiller PADDistiller
}

// NewSynthesizer creates a Synthesizer.
func NewSynthesizer(distiller PADDistiller) *Synthesizer {
	return &Synthesizer{Distiller: distiller}
}

// Merge takes the original query and all worker results, returns a synthesized answer.
// Falls back to concatenation if the LLM is unavailable.
func (s *Synthesizer) Merge(ctx context.Context, query string, results []WorkerResult) string {
	if len(results) == 0 {
		return ""
	}
	// Single result — no merge needed, pass through directly.
	if len(results) == 1 {
		if results[0].Error != "" {
			return fmt.Sprintf("[Worker error: %s]", results[0].Error)
		}
		return results[0].Output
	}

	successful := make([]WorkerResult, 0, len(results))
	for _, r := range results {
		if r.Error == "" && strings.TrimSpace(r.Output) != "" {
			successful = append(successful, r)
		}
	}

	if len(successful) == 0 {
		return "[All workers failed — no synthesis available]"
	}
	if len(successful) == 1 {
		return successful[0].Output
	}

	if s.Distiller == nil {
		return s.naiveMerge(query, successful)
	}

	prompt := s.buildMergePrompt(query, successful)
	raw, err := s.Distiller.Generate(prompt, map[string]interface{}{
		"temperature": 0.3,
		"num_predict": 1024,
	})
	if err != nil {
		log.Printf("[PAD:Synthesizer] LLM error, using naive merge: %v", err)
		return s.naiveMerge(query, successful)
	}

	output := strings.TrimSpace(extractPADText(raw))
	if output == "" {
		return s.naiveMerge(query, successful)
	}
	return output
}

// ─────────────────────────────────────────────────────────────────────────────
// Internals
// ─────────────────────────────────────────────────────────────────────────────

func (s *Synthesizer) buildMergePrompt(query string, results []WorkerResult) string {
	var sb strings.Builder
	sb.WriteString("You are a synthesis engine for Oricli, a sovereign AI.\n\n")
	sb.WriteString(fmt.Sprintf("ORIGINAL QUERY: %s\n\n", query))
	sb.WriteString("PARALLEL WORKER FINDINGS:\n")

	for i, r := range results {
		sb.WriteString(fmt.Sprintf("\n--- Worker %d (goal: %s) ---\n%s\n", i+1, r.Goal, r.Output))
	}

	sb.WriteString(`
INSTRUCTIONS:
- Synthesize the above findings into one coherent, unified answer to the original query.
- Remove redundancy and conflicting claims (note conflicts explicitly if significant).
- Be factual, complete, and concise.
- Do not mention workers or the synthesis process — just deliver the answer.`)

	return sb.String()
}

func (s *Synthesizer) naiveMerge(query string, results []WorkerResult) string {
	var sb strings.Builder
	sb.WriteString(fmt.Sprintf("# Findings for: %s\n\n", query))
	for _, r := range results {
		sb.WriteString(fmt.Sprintf("## %s\n%s\n\n", r.Goal, r.Output))
	}
	return strings.TrimSpace(sb.String())
}

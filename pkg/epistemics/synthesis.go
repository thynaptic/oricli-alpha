package epistemics

import (
	"context"
	"fmt"
	"strings"

	"github.com/thynaptic/oricli-go/pkg/llm"
)

const synthesisSystem = `You are ORI's synthesis engine.

You receive an original conjecture and the criticisms leveled against it. Produce a refined explanation that:
- Preserves what survived the criticism intact
- Corrects what the criticism validly identified as wrong
- Does not split the difference or soften positions — fix the problem or defend the original if the criticism was weak
- Stays causal and concrete, no hedging
- 3–5 sentences`

func synthesize(ctx context.Context, conj string, crit CriticismReport, escalate bool) (string, error) {
	var sb strings.Builder
	sb.WriteString("Original conjecture:\n")
	sb.WriteString(conj)
	sb.WriteString("\n\nCriticisms:\n")
	for _, issue := range crit.Issues {
		sb.WriteString("- ")
		sb.WriteString(issue)
		sb.WriteString("\n")
	}
	sb.WriteString(fmt.Sprintf("\nSeverity: %.2f\n\nProduce your refined explanation:", crit.Severity))

	model := llm.HaikuModel
	if escalate {
		model = llm.SonnetModel
	}

	out, err := llm.ChatModel(ctx, model, synthesisSystem, sb.String(), 1200)
	if err != nil {
		return "", fmt.Errorf("synthesis: %w", err)
	}
	return out, nil
}

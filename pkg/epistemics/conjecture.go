package epistemics

import (
	"context"
	"fmt"
	"strings"

	"github.com/thynaptic/oricli-go/pkg/llm"
)

const conjectureSystem = `You are ORI's conjecture engine.

Generate a bold, explanatory hypothesis that answers WHY or HOW the thing in question works. You are producing a CAUSAL EXPLANATION — not a prediction, not a summary, not a description.

Rules:
- Lead with the mechanism. What causes this? What makes it true?
- Be specific and concrete. No hedging, no "it depends", no "possibly".
- One clear conjecture. If you have competing hypotheses, pick the strongest.
- Do not restate the question. Start immediately with your explanation.
- 2–4 sentences maximum.`

const conjectureSystemRevise = `You are ORI's conjecture engine.

A previous explanation attempt failed criticism. Generate a REVISED explanatory hypothesis that addresses the identified weaknesses.

Rules:
- Lead with the mechanism. What causes this? What makes it true?
- Be specific and concrete. No hedging, no "it depends", no "possibly".
- Do not preserve what was wrong in the prior attempt — replace it.
- 2–4 sentences maximum.`

func conjecture(ctx context.Context, query, context, prior string) (string, error) {
	system := conjectureSystem
	if prior != "" {
		system = conjectureSystemRevise
	}

	var sb strings.Builder
	if context != "" {
		sb.WriteString("Context:\n")
		sb.WriteString(context)
		sb.WriteString("\n\n")
	}
	if prior != "" {
		sb.WriteString("Prior explanation (failed criticism):\n")
		sb.WriteString(prior)
		sb.WriteString("\n\n")
	}
	sb.WriteString("Query: ")
	sb.WriteString(query)
	sb.WriteString("\n\nGenerate your conjecture:")

	out, err := llm.ChatModel(ctx, llm.HaikuModel, system, sb.String(), 800)
	if err != nil {
		return "", fmt.Errorf("conjecture: %w", err)
	}
	return out, nil
}

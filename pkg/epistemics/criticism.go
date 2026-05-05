package epistemics

import (
	"context"
	"fmt"
	"strconv"
	"strings"

	"github.com/thynaptic/oricli-go/pkg/llm"
)

const criticismSystem = `You are ORI's adversarial critic. You receive an explanation and your sole job is to find what is WRONG with it.

Attack vectors:
- Internal contradictions (does the explanation contradict itself?)
- Unfalsifiable claims (can this even be tested or disproven?)
- Missing causal mechanism (does it say WHY without explaining HOW?)
- Scope errors (too broad, too narrow, or misidentifies what needs explaining)
- Stronger competing explanations that make this one redundant

Format your response EXACTLY as:
SEVERITY: [0.0 to 1.0]
- [specific issue]
- [specific issue]

SEVERITY guide:
0.0–0.3 = minor issues, explanation largely holds
0.4–0.6 = real gaps, incomplete
0.7–0.9 = serious problems, needs substantial revision
1.0 = fundamentally wrong

Reserve 0.0 for genuinely airtight explanations only. Even strong explanations typically have 0.1–0.3 weaknesses.`

func criticize(ctx context.Context, conj string) (CriticismReport, error) {
	prompt := fmt.Sprintf("Explanation to criticize:\n%s\n\nProduce your criticism:", conj)

	raw, err := llm.ChatModel(ctx, llm.HaikuModel, criticismSystem, prompt, 600)
	if err != nil {
		return CriticismReport{}, fmt.Errorf("criticism: %w", err)
	}

	return parseCriticism(raw), nil
}

func parseCriticism(raw string) CriticismReport {
	var report CriticismReport
	lines := strings.Split(raw, "\n")
	for _, line := range lines {
		line = strings.TrimSpace(line)
		if strings.HasPrefix(strings.ToUpper(line), "SEVERITY:") {
			parts := strings.SplitN(line, ":", 2)
			if len(parts) == 2 {
				f, err := strconv.ParseFloat(strings.TrimSpace(parts[1]), 64)
				if err == nil {
					if f < 0 {
						f = 0
					}
					if f > 1 {
						f = 1
					}
					report.Severity = f
				}
			}
			continue
		}
		if strings.HasPrefix(line, "-") {
			issue := strings.TrimSpace(strings.TrimPrefix(line, "-"))
			if issue != "" {
				report.Issues = append(report.Issues, issue)
			}
		}
	}
	if len(report.Issues) == 0 && report.Severity == 0 {
		// model didn't follow format — treat as moderate criticism
		report.Severity = 0.4
		report.Issues = []string{strings.TrimSpace(raw)}
	}
	return report
}

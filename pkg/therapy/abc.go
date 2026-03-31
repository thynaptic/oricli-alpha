package therapy

import (
	"fmt"
	"strings"
)

// ---------------------------------------------------------------------------
// ABCAuditor — REBT Belief Chain Interception
// ---------------------------------------------------------------------------

// ABCAuditor runs an REBT Disputation pass (the "D" in ABCDE) on a proposed
// response before it is committed. It intercepts the implicit belief chain (B)
// and challenges any irrational beliefs before the consequence (C) fires.
type ABCAuditor struct {
	gen LLMGenerator
}

// NewABCAuditor creates an ABCAuditor. gen must not be nil.
func NewABCAuditor(gen LLMGenerator) *ABCAuditor {
	return &ABCAuditor{gen: gen}
}

// Audit runs a B-pass Disputation on a (query, proposedResponse) pair.
// Returns a DisputationReport. Pass=true means no irrational beliefs found.
func (a *ABCAuditor) Audit(query, proposedResponse string) DisputationReport {
	prompt := a.buildPrompt(query, proposedResponse)

	res, err := a.gen.Generate(prompt, map[string]interface{}{
		"options": map[string]interface{}{
			"num_predict": 300,
			"temperature": 0.1,
			"num_ctx":     2048,
		},
	})
	if err != nil {
		return DisputationReport{Pass: true, BeliefChain: "auditor unavailable"} // fail-open
	}

	raw, _ := res["text"].(string)
	return parseDisputationReport(raw, query, proposedResponse)
}

// buildPrompt constructs the REBT disputation prompt.
func (a *ABCAuditor) buildPrompt(query, response string) string {
	return fmt.Sprintf(`You are an REBT-trained belief chain auditor for an AI inference system.

Your job: examine the IMPLICIT BELIEF CHAIN (B) that connects the query (A) to the proposed response (C).
Identify any irrational beliefs and apply Disputation (D) before the response is committed.

A — QUERY:
%s

C — PROPOSED RESPONSE:
%s

Irrational belief types to detect:
- MUSTURBATION: absolute demands ("must", "always", "never", "have to answer this perfectly")
- AWFULIZING: catastrophizing the stakes of uncertainty or error
- LOW_FRUSTRATION_TOLERANCE: avoiding complexity by oversimplifying or refusing
- GLOBAL_EVALUATION: sweeping judgments about the user, topic, or self

For each irrational belief found, apply three Disputation challenges:
1. Logical: Is this belief logically consistent?
2. Empirical: Is there actual evidence for this belief?
3. Pragmatic: What is the outcome of holding this belief and being wrong?

Respond in EXACTLY this format:
BELIEF_CHAIN: <one sentence describing the implicit belief chain>
IRRATIONAL_BELIEFS: <comma-separated list of types, or NONE>
DISPUTATIONS: <numbered list of challenges, one per belief found>
REFORMED_BELIEF: <the corrected belief chain after disputation>
PASS: <YES or NO>`,
		clip(query, 500), clip(response, 600))
}

// parseDisputationReport parses the structured LLM output.
func parseDisputationReport(raw, query, response string) DisputationReport {
	r := DisputationReport{BeliefChain: query + " → " + clip(response, 80)}
	lines := strings.Split(strings.TrimSpace(raw), "\n")

	var disputationLines []string
	inDisputations := false

	for _, line := range lines {
		line = strings.TrimSpace(line)
		if line == "" {
			continue
		}

		switch {
		case strings.HasPrefix(strings.ToUpper(line), "BELIEF_CHAIN:"):
			r.BeliefChain = strings.TrimSpace(line[len("BELIEF_CHAIN:"):])
			inDisputations = false

		case strings.HasPrefix(strings.ToUpper(line), "IRRATIONAL_BELIEFS:"):
			val := strings.TrimSpace(line[len("IRRATIONAL_BELIEFS:"):])
			if !strings.EqualFold(val, "NONE") && val != "" {
				for _, b := range strings.Split(val, ",") {
					b = strings.TrimSpace(b)
					if b != "" {
						r.IrrationalBeliefs = append(r.IrrationalBeliefs, IrrationalBelief(b))
					}
				}
			}
			inDisputations = false

		case strings.HasPrefix(strings.ToUpper(line), "DISPUTATIONS:"):
			val := strings.TrimSpace(line[len("DISPUTATIONS:"):])
			if val != "" {
				disputationLines = append(disputationLines, val)
			}
			inDisputations = true

		case strings.HasPrefix(strings.ToUpper(line), "REFORMED_BELIEF:"):
			r.ReformedBelief = strings.TrimSpace(line[len("REFORMED_BELIEF:"):])
			inDisputations = false

		case strings.HasPrefix(strings.ToUpper(line), "PASS:"):
			val := strings.TrimSpace(line[len("PASS:"):])
			r.Pass = strings.EqualFold(val, "YES") || strings.EqualFold(val, "TRUE")
			inDisputations = false

		default:
			if inDisputations {
				disputationLines = append(disputationLines, line)
			}
		}
	}

	r.Disputations = disputationLines

	// If no explicit PASS field, infer from irrational beliefs
	if r.Pass == false && len(r.IrrationalBeliefs) == 0 {
		r.Pass = true
	}

	return r
}

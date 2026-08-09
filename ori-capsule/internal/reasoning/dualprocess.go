package reasoning

import "strings"

// ProcessTier identifies which cognitive system a task demands.
type ProcessTier int

const (
	TierS1 ProcessTier = iota
	TierS2
)

func (t ProcessTier) String() string {
	switch t {
	case TierS1:
		return "S1"
	case TierS2:
		return "S2"
	}
	return "unknown"
}

// ProcessDemand holds the S1/S2 demand profile for a query.
type ProcessDemand struct {
	Novelty       float64
	Abstraction   float64
	MultiStep     float64
	Contradiction float64
	Score         float64
	Tier          ProcessTier
	TaskClass     string
	Reasons       []string
}

var noveltySigs = []string{
	"never", "unusual", "hypothetical", "imagine", "suppose", "what if",
	"novel", "unprecedented", "invent", "design from scratch", "first principles",
	"no prior", "unique", "edge case", "corner case",
}

var abstractionSigs = []string{
	"philosophy", "theory", "concept", "meaning", "implication", "ethics",
	"abstract", "principle", "framework", "paradigm", "meta", "ontology",
	"epistemology", "nature of", "what is the relationship", "define",
	"fundamentally", "essentially", "in general",
}

var multiStepSigs = []string{
	"step by step", "walk me through", "how would you", "plan",
	"sequence", "order of operations", "first then", "if then else",
	"chain", "pipeline", "workflow", "and then", "after that",
	"subsequently", "trace through", "derive", "prove",
}

var contradictionSigs = []string{
	"always", "never", "every", "all", "none", "impossible",
	"must", "cannot", "guaranteed", "certain", "without exception",
	"paradox", "contradiction", "but", "however", "although",
	"except", "unless", "only if",
}

var s2TaskClasses = map[string]bool{
	"technical": true, "procedural": true, "comparative": true,
}

// ClassifyProcess scores the query across demand dimensions (no LLM, no retry).
func ClassifyProcess(query, taskClass string) ProcessDemand {
	lower := strings.ToLower(query)
	words := strings.Fields(lower)
	wordCount := len(words)
	var reasons []string

	noveltyScore := scoreSignals(lower, noveltySigs, 0.15)
	if wordCount > 40 {
		noveltyScore = clamp01(noveltyScore + 0.1)
		reasons = append(reasons, "long query (+novelty)")
	}
	if noveltyScore > 0.3 {
		reasons = append(reasons, "novelty signals detected")
	}

	abstractionScore := scoreSignals(lower, abstractionSigs, 0.12)
	if s2TaskClasses[taskClass] {
		abstractionScore = clamp01(abstractionScore + 0.15)
		reasons = append(reasons, "S2-class task ("+taskClass+")")
	}

	multiStepScore := scoreSignals(lower, multiStepSigs, 0.15)
	sentenceCount := strings.Count(lower, ".") + strings.Count(lower, "?") + strings.Count(lower, ";")
	if sentenceCount >= 3 {
		multiStepScore = clamp01(multiStepScore + float64(sentenceCount)*0.05)
		reasons = append(reasons, "multi-sentence query (+steps)")
	}

	contradictionScore := scoreSignals(lower, contradictionSigs, 0.10)
	if contradictionScore > 0.3 {
		reasons = append(reasons, "absolute/conditional language (+contradiction risk)")
	}

	score := noveltyScore*0.25 + abstractionScore*0.20 + multiStepScore*0.35 + contradictionScore*0.20
	threshold := 0.35
	if s2TaskClasses[taskClass] {
		threshold = 0.18
	}

	tier := TierS1
	if score >= threshold {
		tier = TierS2
		if len(reasons) == 0 {
			reasons = append(reasons, "aggregate S2 threshold reached")
		}
	}

	return ProcessDemand{
		Novelty: noveltyScore, Abstraction: abstractionScore,
		MultiStep: multiStepScore, Contradiction: contradictionScore,
		Score: score, Tier: tier, TaskClass: taskClass, Reasons: reasons,
	}
}

func FormatProcessHint(d ProcessDemand) string {
	if d.Tier != TierS2 {
		return ""
	}
	return "### PROCESS HINT\n" +
		"This query looks like careful multi-step reasoning (S2). Prefer deliberate structure; " +
		"check assumptions; do not rush a shallow pattern match.\n" +
		"### END PROCESS HINT"
}

func scoreSignals(text string, signals []string, weight float64) float64 {
	score := 0.0
	for _, sig := range signals {
		if strings.Contains(text, sig) {
			score += weight
		}
	}
	return clamp01(score)
}

func clamp01(v float64) float64 { return clamp(v, 0, 1) }

func clamp(v, min, max float64) float64 {
	if v < min {
		return min
	}
	if v > max {
		return max
	}
	return v
}

package cogload

import (
	"strings"
)

// ── Heuristic signal lists ────────────────────────────────────────────────────

// technicalTerms drive intrinsic load — each hit increases complexity score.
var technicalTerms = []string{
	"algorithm", "architecture", "asynchronous", "concurrency", "consensus",
	"distributed", "encryption", "goroutine", "idempotent", "implementation",
	"inference", "latency", "middleware", "mutex", "orchestration",
	"parallelism", "polynomial", "recursive", "scalability", "serialization",
	"synchronization", "throughput", "transaction", "transformer", "vectorize",
}

// followUpIndicators signal germane load — the model is building on prior context.
var followUpIndicators = []string{
	"as mentioned", "as you said", "building on", "following up",
	"from earlier", "going back to", "in that case", "like before",
	"referring to", "to your point", "you mentioned", "regarding the",
	"continuing from", "based on what", "with that in mind",
}

// newConceptIndicators signal germane load — new schema-forming content.
var newConceptIndicators = []string{
	"introduce", "new concept", "by the way", "also worth noting",
	"another thing", "additionally", "furthermore", "let me add",
	"important point", "key insight", "one more", "side note",
}

// repetitionPhrases are signatures of redundant/extraneous content.
var repetitionPhrases = []string{
	"as i said", "as i mentioned", "i already said", "repeating",
	"again,", "once more", "to reiterate", "to repeat",
}

// LoadMeter estimates the cognitive load profile of a message list.
type LoadMeter struct{}

// NewLoadMeter creates a LoadMeter.
func NewLoadMeter() *LoadMeter { return &LoadMeter{} }

// Measure computes the LoadProfile for a message slice.
func (m *LoadMeter) Measure(messages []map[string]string) LoadProfile {
	if len(messages) == 0 {
		return LoadProfile{Tier: LoadNormal, TierLabel: LoadNormal.String()}
	}

	var reasons []string
	totalChars := 0
	codeBlockCount := 0
	technicalHits := 0
	repetitionHits := 0
	followUpHits := 0
	newConceptHits := 0
	systemPromptChars := 0
	userMsgCount := 0

	for _, msg := range messages {
		content := msg["content"]
		lower := strings.ToLower(content)
		totalChars += len(content)

		switch msg["role"] {
		case "system":
			systemPromptChars += len(content)
		case "user":
			userMsgCount++
		}

		// Code blocks are high intrinsic load
		codeBlockCount += strings.Count(content, "```")

		// Technical term density
		for _, term := range technicalTerms {
			if strings.Contains(lower, term) {
				technicalHits++
			}
		}

		// Repetition → extraneous
		for _, rep := range repetitionPhrases {
			if strings.Contains(lower, rep) {
				repetitionHits++
			}
		}

		// Follow-up indicators → germane
		for _, fu := range followUpIndicators {
			if strings.Contains(lower, fu) {
				followUpHits++
			}
		}

		// New concept indicators → germane
		for _, nc := range newConceptIndicators {
			if strings.Contains(lower, nc) {
				newConceptHits++
			}
		}
	}

	msgCount := len(messages)

	// ── Intrinsic load ────────────────────────────────────────────────────────
	// Driven by message volume, content density, code, technical terms
	intrinsic := 0.0
	msgVolumeFactor := clamp(float64(msgCount)/20.0, 0, 0.4)
	intrinsic += msgVolumeFactor
	intrinsic += clamp(float64(totalChars)/8000.0, 0, 0.3)
	intrinsic += clamp(float64(codeBlockCount/2)*0.08, 0, 0.2)
	intrinsic += clamp(float64(technicalHits)*0.015, 0, 0.2)
	intrinsic = clamp(intrinsic, 0, 1)
	if intrinsic > 0.5 {
		reasons = append(reasons, "high intrinsic load (dense/long context)")
	}

	// ── Extraneous load ───────────────────────────────────────────────────────
	// Driven by repetition, bloated system prompts, old conversation depth
	extraneous := 0.0
	extraneous += clamp(float64(repetitionHits)*0.12, 0, 0.3)
	extraneous += clamp(float64(systemPromptChars)/3000.0, 0, 0.35)
	// Old conversation: many turns with low user-to-total ratio
	if msgCount > 12 {
		oldnessFactor := clamp(float64(msgCount-12)*0.04, 0, 0.35)
		extraneous += oldnessFactor
		reasons = append(reasons, "deep conversation history")
	}
	extraneous = clamp(extraneous, 0, 1)
	if extraneous > 0.4 {
		reasons = append(reasons, "elevated extraneous load (repetition/bloat)")
	}

	// ── Germane load ──────────────────────────────────────────────────────────
	// Driven by active schema-building: follow-ups + new concept introductions
	germane := 0.0
	germane += clamp(float64(followUpHits)*0.08, 0, 0.4)
	germane += clamp(float64(newConceptHits)*0.07, 0, 0.35)
	// Multiple user messages = active dialogue = schema-building
	germane += clamp(float64(userMsgCount)*0.04, 0, 0.25)
	germane = clamp(germane, 0, 1)

	totalLoad := intrinsic + extraneous + germane

	tier := LoadNormal
	if totalLoad >= CriticalThreshold {
		tier = LoadCritical
		reasons = append(reasons, "critical total load — surgery required")
	} else if totalLoad >= ElevatedThreshold {
		tier = LoadElevated
		reasons = append(reasons, "elevated total load — surgery recommended")
	}

	return LoadProfile{
		Intrinsic:    intrinsic,
		Extraneous:   extraneous,
		Germane:      germane,
		TotalLoad:    totalLoad,
		Tier:         tier,
		TierLabel:    tier.String(),
		Reasons:      reasons,
		MessageCount: msgCount,
		TotalChars:   totalChars,
	}
}

// ── helpers ───────────────────────────────────────────────────────────────────

func clamp(v, min, max float64) float64 {
	if v < min {
		return min
	}
	if v > max {
		return max
	}
	return v
}

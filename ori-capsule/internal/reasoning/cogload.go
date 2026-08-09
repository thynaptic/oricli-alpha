package reasoning

import (
	"fmt"
	"strings"
)

// LoadTier classifies total cognitive load of a context window.
type LoadTier int

const (
	LoadNormal LoadTier = iota
	LoadElevated
	LoadCritical
)

func (t LoadTier) String() string {
	switch t {
	case LoadNormal:
		return "normal"
	case LoadElevated:
		return "elevated"
	case LoadCritical:
		return "critical"
	}
	return "unknown"
}

const (
	ElevatedThreshold = 1.20
	CriticalThreshold = 1.80
)

// LoadProfile is Sweller CLT breakdown for a message list.
type LoadProfile struct {
	Intrinsic    float64  `json:"intrinsic"`
	Extraneous   float64  `json:"extraneous"`
	Germane      float64  `json:"germane"`
	TotalLoad    float64  `json:"total_load"`
	Tier         LoadTier `json:"tier"`
	TierLabel    string   `json:"tier_label"`
	Reasons      []string `json:"reasons"`
	MessageCount int      `json:"message_count"`
	TotalChars   int      `json:"total_chars"`
}

type SurgeryResult struct {
	OriginalCount int      `json:"original_count"`
	TrimmedCount  int      `json:"trimmed_count"`
	RemovedMsgs   int      `json:"removed_msgs"`
	CharsRemoved  int      `json:"chars_removed"`
	Actions       []string `json:"actions"`
	LoadBefore    float64  `json:"load_before"`
	LoadAfter     float64  `json:"load_after"`
}

var technicalTerms = []string{
	"algorithm", "architecture", "asynchronous", "concurrency", "consensus",
	"distributed", "encryption", "goroutine", "idempotent", "implementation",
	"inference", "latency", "middleware", "mutex", "orchestration",
	"parallelism", "polynomial", "recursive", "scalability", "serialization",
	"synchronization", "throughput", "transaction", "transformer", "vectorize",
}

var followUpIndicators = []string{
	"as mentioned", "as you said", "building on", "following up",
	"from earlier", "going back to", "in that case", "like before",
	"referring to", "to your point", "you mentioned", "regarding the",
	"continuing from", "based on what", "with that in mind",
}

var newConceptIndicators = []string{
	"introduce", "new concept", "by the way", "also worth noting",
	"another thing", "additionally", "furthermore", "let me add",
	"important point", "key insight", "one more", "side note",
}

var repetitionPhrases = []string{
	"as i said", "as i mentioned", "i already said", "repeating",
	"again,", "once more", "to reiterate", "to repeat",
}

// MeasureLoad estimates cognitive load for role/content maps.
func MeasureLoad(messages []map[string]string) LoadProfile {
	if len(messages) == 0 {
		return LoadProfile{Tier: LoadNormal, TierLabel: LoadNormal.String()}
	}
	var reasons []string
	totalChars, codeBlockCount, technicalHits := 0, 0, 0
	repetitionHits, followUpHits, newConceptHits := 0, 0, 0
	systemPromptChars, userMsgCount := 0, 0

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
		codeBlockCount += strings.Count(content, "```")
		for _, term := range technicalTerms {
			if strings.Contains(lower, term) {
				technicalHits++
			}
		}
		for _, rep := range repetitionPhrases {
			if strings.Contains(lower, rep) {
				repetitionHits++
			}
		}
		for _, fu := range followUpIndicators {
			if strings.Contains(lower, fu) {
				followUpHits++
			}
		}
		for _, nc := range newConceptIndicators {
			if strings.Contains(lower, nc) {
				newConceptHits++
			}
		}
	}

	msgCount := len(messages)
	intrinsic := 0.0
	intrinsic += clamp(float64(msgCount)/20.0, 0, 0.4)
	intrinsic += clamp(float64(totalChars)/8000.0, 0, 0.3)
	intrinsic += clamp(float64(codeBlockCount/2)*0.08, 0, 0.2)
	intrinsic += clamp(float64(technicalHits)*0.015, 0, 0.2)
	intrinsic = clamp01(intrinsic)
	if intrinsic > 0.5 {
		reasons = append(reasons, "high intrinsic load (dense/long context)")
	}

	extraneous := 0.0
	extraneous += clamp(float64(repetitionHits)*0.12, 0, 0.3)
	extraneous += clamp(float64(systemPromptChars)/3000.0, 0, 0.35)
	if msgCount > 12 {
		extraneous += clamp(float64(msgCount-12)*0.04, 0, 0.35)
		reasons = append(reasons, "deep conversation history")
	}
	extraneous = clamp01(extraneous)
	if extraneous > 0.4 {
		reasons = append(reasons, "elevated extraneous load (repetition/bloat)")
	}

	germane := 0.0
	germane += clamp(float64(followUpHits)*0.08, 0, 0.4)
	germane += clamp(float64(newConceptHits)*0.07, 0, 0.35)
	germane += clamp(float64(userMsgCount)*0.04, 0, 0.25)
	germane = clamp01(germane)

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
		Intrinsic: intrinsic, Extraneous: extraneous, Germane: germane,
		TotalLoad: totalLoad, Tier: tier, TierLabel: tier.String(),
		Reasons: reasons, MessageCount: msgCount, TotalChars: totalChars,
	}
}

const (
	maxSystemPromptChars = 1200
	keepRecentTurns      = 6
)

// TrimLoad reduces context when elevated/critical. Never adds LLM calls.
func TrimLoad(messages []map[string]string, profile LoadProfile) ([]map[string]string, SurgeryResult) {
	result := SurgeryResult{OriginalCount: len(messages), LoadBefore: profile.TotalLoad}
	if profile.Tier == LoadNormal {
		result.TrimmedCount = len(messages)
		result.LoadAfter = profile.TotalLoad
		return messages, result
	}
	trimmed := make([]map[string]string, len(messages))
	copy(trimmed, messages)
	var actions []string
	charsRemoved := 0

	if profile.Tier >= LoadElevated {
		var removed, removedChars int
		trimmed, removed, removedChars = removeOldAssistantMsgs(trimmed)
		if removed > 0 {
			result.RemovedMsgs += removed
			charsRemoved += removedChars
			actions = append(actions, fmt.Sprintf("removed %d old assistant messages (-%d chars)", removed, removedChars))
		}
	}
	if profile.Tier >= LoadCritical {
		var compressedChars int
		trimmed, compressedChars = compressSystemPrompts(trimmed)
		if compressedChars > 0 {
			charsRemoved += compressedChars
			actions = append(actions, fmt.Sprintf("compressed system prompt (-%d chars)", compressedChars))
		}
	}
	newProfile := MeasureLoad(trimmed)
	result.TrimmedCount = len(trimmed)
	result.CharsRemoved = charsRemoved
	result.Actions = actions
	result.LoadAfter = newProfile.TotalLoad
	return trimmed, result
}

func removeOldAssistantMsgs(messages []map[string]string) ([]map[string]string, int, int) {
	if len(messages) <= keepRecentTurns {
		return messages, 0, 0
	}
	cutoff := len(messages) - keepRecentTurns
	out := make([]map[string]string, 0, len(messages))
	removed, chars := 0, 0
	for i, m := range messages {
		if i < cutoff && m["role"] == "assistant" {
			removed++
			chars += len(m["content"])
			continue
		}
		out = append(out, m)
	}
	return out, removed, chars
}

func compressSystemPrompts(messages []map[string]string) ([]map[string]string, int) {
	chars := 0
	for i, m := range messages {
		if m["role"] != "system" {
			continue
		}
		if len(m["content"]) <= maxSystemPromptChars {
			continue
		}
		runes := []rune(m["content"])
		if len(runes) > maxSystemPromptChars {
			cut := string(runes[:maxSystemPromptChars]) + "\n…[truncated for load]"
			chars += len(m["content"]) - len(cut)
			messages[i]["content"] = cut
		}
	}
	return messages, chars
}

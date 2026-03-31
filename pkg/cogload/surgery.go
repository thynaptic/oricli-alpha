package cogload

import (
	"fmt"
	"strings"
)

const (
	// maxSystemPromptChars: system prompts beyond this get truncated on Critical load.
	maxSystemPromptChars = 1200

	// keepRecentTurns: always preserve this many most-recent messages regardless of load.
	keepRecentTurns = 6
)

// ContextSurgery reduces cognitive load by trimming or compressing a message list.
// Surgery never removes system messages or the most recent N turns.
// Elevation strategy: remove oldest assistant messages.
// Critical strategy: additionally compress oversized system prompts.
type ContextSurgery struct {
	Meter *LoadMeter
}

// NewContextSurgery creates a ContextSurgery.
func NewContextSurgery(meter *LoadMeter) *ContextSurgery {
	return &ContextSurgery{Meter: meter}
}

// Trim reduces the message list to lower cognitive load.
// Returns the trimmed list and a SurgeryResult describing what changed.
// If load is Normal, returns messages unchanged.
func (s *ContextSurgery) Trim(messages []map[string]string, profile LoadProfile) ([]map[string]string, SurgeryResult) {
	result := SurgeryResult{
		OriginalCount: len(messages),
		LoadBefore:    profile.TotalLoad,
	}

	if profile.Tier == LoadNormal {
		result.TrimmedCount = len(messages)
		result.LoadAfter = profile.TotalLoad
		return messages, result
	}

	trimmed := make([]map[string]string, len(messages))
	copy(trimmed, messages)
	var actions []string
	charsRemoved := 0

	// ── Step 1: Remove oldest non-system, non-recent assistant messages ───────
	if profile.Tier >= LoadElevated {
		var removed int
		var removedChars int
		trimmed, removed, removedChars = removeOldAssistantMsgs(trimmed)
		if removed > 0 {
			result.RemovedMsgs += removed
			charsRemoved += removedChars
			actions = append(actions, fmt.Sprintf("removed %d old assistant messages (-%d chars)", removed, removedChars))
		}
	}

	// ── Step 2: Compress oversized system prompt on Critical load ─────────────
	if profile.Tier >= LoadCritical {
		var compressedChars int
		trimmed, compressedChars = compressSystemPrompts(trimmed)
		if compressedChars > 0 {
			charsRemoved += compressedChars
			actions = append(actions, fmt.Sprintf("compressed system prompt (-%d chars)", compressedChars))
		}
	}

	// Re-measure after surgery
	newProfile := s.Meter.Measure(trimmed)

	result.TrimmedCount = len(trimmed)
	result.CharsRemoved = charsRemoved
	result.Actions = actions
	result.LoadAfter = newProfile.TotalLoad
	return trimmed, result
}

// ── Surgery helpers ───────────────────────────────────────────────────────────

// removeOldAssistantMsgs removes assistant messages from the older half of
// the conversation, preserving the most recent keepRecentTurns messages.
func removeOldAssistantMsgs(messages []map[string]string) ([]map[string]string, int, int) {
	if len(messages) <= keepRecentTurns {
		return messages, 0, 0
	}

	// Split: everything before the protected window, and the protected tail
	cutoff := len(messages) - keepRecentTurns
	older := messages[:cutoff]
	recent := messages[cutoff:]

	kept := make([]map[string]string, 0, len(older))
	removed := 0
	removedChars := 0

	for _, msg := range older {
		if msg["role"] == "assistant" {
			removed++
			removedChars += len(msg["content"])
		} else {
			kept = append(kept, msg)
		}
	}

	return append(kept, recent...), removed, removedChars
}

// compressSystemPrompts truncates system prompts that exceed maxSystemPromptChars.
// Appends "[truncated for cognitive load management]" so the model knows.
func compressSystemPrompts(messages []map[string]string) ([]map[string]string, int) {
	result := make([]map[string]string, len(messages))
	totalRemoved := 0

	for i, msg := range messages {
		result[i] = msg
		if msg["role"] == "system" && len(msg["content"]) > maxSystemPromptChars {
			original := msg["content"]
			// Truncate at word boundary near the limit
			truncated := truncateAtWord(original, maxSystemPromptChars)
			suffix := "\n[Context truncated for cognitive load management]"
			result[i] = map[string]string{
				"role":    "system",
				"content": truncated + suffix,
			}
			totalRemoved += len(original) - len(result[i]["content"])
		}
	}
	return result, totalRemoved
}

func truncateAtWord(s string, maxChars int) string {
	if len(s) <= maxChars {
		return s
	}
	// Find last space before maxChars
	sub := s[:maxChars]
	lastSpace := strings.LastIndex(sub, " ")
	if lastSpace > maxChars/2 {
		return s[:lastSpace]
	}
	return sub
}

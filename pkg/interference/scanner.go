package interference

import (
	"regexp"
	"strings"
	"sync"
)

// conflictRule defines a pair of regex patterns that contradict each other.
type conflictRule struct {
	Type ConflictType
	A    *regexp.Regexp
	B    *regexp.Regexp
}

var conflictRules = []conflictRule{
	// ── Scope: verbose vs brief ──
	{
		Type: ConflictScope,
		A:    regexp.MustCompile(`(?i)\b(detailed|thorough|comprehensive|exhaustive|in.?depth|explain everything|cover all|don't leave anything out|full (explanation|breakdown|analysis))\b`),
		B:    regexp.MustCompile(`(?i)\b(brief|concise|keep it short|tldr|summarize|one.?liner|quick answer|don't over.?explain|short (answer|response|explanation))\b`),
	},
	// ── Tone: formal vs casual ──
	{
		Type: ConflictTone,
		A:    regexp.MustCompile(`(?i)\b(formal|professional (tone|language|style)|academic|official (tone|style)|business.?style)\b`),
		B:    regexp.MustCompile(`(?i)\b(casual|informal|conversational|relaxed|no (jargon|formalities)|talk (to me )?like a (friend|human|person)|chill)\b`),
	},
	// ── Goal: do X vs don't do X (include/exclude) ──
	{
		Type: ConflictConstraint,
		A:    regexp.MustCompile(`(?i)\b(include (code|examples?|citations?|references?|links?|numbers?|data|sources?))\b`),
		B:    regexp.MustCompile(`(?i)\b(no (code|examples?|citations?|references?|links?|numbers?|data|sources?)|don't (include|add|use) (code|examples?|citations?|references?))\b`),
	},
	// ── Priority: focus on A vs also cover B ──
	{
		Type: ConflictPriority,
		A:    regexp.MustCompile(`(?i)\b(focus (on|only on)|prioritize|stick to|only (talk|write|answer) about)\b`),
		B:    regexp.MustCompile(`(?i)\b(also (cover|include|address|discuss|talk about)|don't forget (to|about)|make sure (to include|you cover))\b`),
	},
	// ── Goal: must do vs must not do ──
	{
		Type: ConflictGoal,
		A:    regexp.MustCompile(`(?i)\b(always (include|use|add|start|end)|must (include|use|add|start|end)|make sure (you|to) (include|use|add))\b`),
		B:    regexp.MustCompile(`(?i)\b(never (include|use|add|start|end)|must not (include|use|add)|don't (include|use|add)|avoid (using|including|adding))\b`),
	},
}

// InstructionConflictScanner scans the conversation window for contradictory instructions.
type InstructionConflictScanner struct {
	mu      sync.Mutex
	window  int // how many past messages to scan
}

func NewInstructionConflictScanner() *InstructionConflictScanner {
	return &InstructionConflictScanner{window: 10}
}

// Scan looks for conflicting instructions across the provided messages.
// messages should be the last N user + system messages, newest last.
func (s *InstructionConflictScanner) Scan(messages []string) InterferenceReading {
	s.mu.Lock()
	defer s.mu.Unlock()

	// Concatenate scanned messages for pairwise rule testing
	// We test each rule against the full window as a combined blob
	combined := strings.Join(messages, " \n ")

	var conflicts []ConflictPair
	for _, rule := range conflictRules {
		matchA := rule.A.FindString(combined)
		matchB := rule.B.FindString(combined)
		if matchA != "" && matchB != "" {
			conflicts = append(conflicts, ConflictPair{
				Type:       rule.Type,
				StatementA: matchA,
				StatementB: matchB,
			})
		}
	}

	severity := float64(len(conflicts)) / float64(len(conflictRules))
	if severity > 1.0 {
		severity = 1.0
	}

	return InterferenceReading{
		Detected:  len(conflicts) > 0,
		Conflicts: conflicts,
		Severity:  severity,
	}
}

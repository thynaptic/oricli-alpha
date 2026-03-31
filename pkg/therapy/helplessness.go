package therapy

import (
	"fmt"
	"regexp"
	"strings"
)

// ---------------------------------------------------------------------------
// HelplessnessDetector — Phase 16
//
// Detects learned helplessness patterns in draft responses.
// Fires when a draft contains refusal language on a topic class where
// the MasteryLog shows a positive historical success rate — meaning the
// system is giving up on problems it has previously solved.
// ---------------------------------------------------------------------------

// refusalPatterns are compiled once at init.
var refusalPatterns = []*regexp.Regexp{
	regexp.MustCompile(`(?i)\bI can'?t\b`),
	regexp.MustCompile(`(?i)\bI('m| am) (not |un)?able to\b`),
	regexp.MustCompile(`(?i)\bI('m| am) unable\b`),
	regexp.MustCompile(`(?i)\bI do(n'?t| not) have the (ability|capability|capacity)\b`),
	regexp.MustCompile(`(?i)\bI('m| am) not capable\b`),
	regexp.MustCompile(`(?i)\b(this|that) is (not |im)?possible\b`),
	regexp.MustCompile(`(?i)\bimpossible (for me|to)\b`),
	regexp.MustCompile(`(?i)\bI cannot\b`),
	regexp.MustCompile(`(?i)\bI('m| am) afraid I (can'?t|cannot|won'?t)\b`),
	regexp.MustCompile(`(?i)\bI('m| am) not (in a position|equipped|designed)\b`),
	regexp.MustCompile(`(?i)\bbeyond (my|the) (capabilities|abilities|scope)\b`),
}

// helplessnessMasteryThreshold: success rate above this means "you can do this class".
// Below it: the refusal might be genuinely accurate, not helplessness.
const helplessnessMasteryThreshold = 0.30

// HelplessnessDetector checks draft responses for learned helplessness signals.
type HelplessnessDetector struct {
	mastery    *MasteryLog
	supervisor *SessionSupervisor // optional — for schema escalation
}

// NewHelplessnessDetector creates a HelplessnessDetector.
func NewHelplessnessDetector(mastery *MasteryLog, supervisor *SessionSupervisor) *HelplessnessDetector {
	return &HelplessnessDetector{mastery: mastery, supervisor: supervisor}
}

// Check inspects a draft response for learned helplessness.
// query: the original user query (used for topic class inference).
// draft: the draft response text.
// Returns nil if no helplessness signal detected.
func (h *HelplessnessDetector) Check(query, draft string) *HelplessnessSignal {
	// Step 1: fast regex scan
	matched, phrase := matchRefusal(draft)
	if !matched {
		return nil
	}

	// Step 2: infer topic class from query
	topicClass := inferTopicClass(query)

	// Step 3: cross-check MasteryLog
	rate := h.mastery.SuccessRate(topicClass)
	successes := h.mastery.RecentSuccesses(topicClass, 5)

	// If no history at all — can't distinguish genuine limit from helplessness
	// Only fire if we have prior success evidence
	if rate < helplessnessMasteryThreshold {
		return nil
	}

	// Step 4: build 3P attribution analysis
	attr := buildAttribution3P(topicClass, rate, successes)

	signal := &HelplessnessSignal{
		Detected:       true,
		Confidence:     rateToConfidence(rate),
		RefusalPhrase:  phrase,
		TopicClass:     topicClass,
		HistoricalRate: rate,
		MasteryCount:   len(successes),
		Attribution3P:  attr,
	}

	// Step 5: notify SessionSupervisor
	if h.supervisor != nil {
		h.supervisor.RecordHelplessness()
	}

	return signal
}

// ---------------------------------------------------------------------------
// AttributionalRetrainer — Seligman 3P intervention
// ---------------------------------------------------------------------------

// AttributionalRetrainer generates a retraining prompt fragment that
// challenges the 3P helpless attributions and injects mastery evidence.
type AttributionalRetrainer struct{}

// NewAttributionalRetrainer creates an AttributionalRetrainer.
func NewAttributionalRetrainer() *AttributionalRetrainer {
	return &AttributionalRetrainer{}
}

// Retrain generates the retraining context to prepend to the retry prompt.
// This is the AI equivalent of Seligman's "drag through the successful behavior."
func (r *AttributionalRetrainer) Retrain(signal *HelplessnessSignal) string {
	if signal == nil || !signal.Detected {
		return ""
	}
	a := signal.Attribution3P
	lines := []string{
		"[ATTRIBUTIONAL RETRAINING — Learned Helplessness Prevention]",
		"",
		"A refusal pattern was detected on a topic class with a positive success history.",
		fmt.Sprintf("Topic class: %s | Historical success rate: %.0f%%", signal.TopicClass, signal.HistoricalRate*100),
		"",
		"3P Attribution Audit:",
		"  Permanence:      " + a.PermanenceChallenge,
		"  Pervasiveness:   " + a.PervasivenessChallenge,
		"  Personalization: " + a.PersonalizationChallenge,
		"",
		a.MasteryEvidence,
		"",
		"INSTRUCTION: Attempt the task before concluding impossibility.",
		"If a full solution is not possible, provide what IS possible — partial help is valid.",
		"Do not reproduce the refusal phrase: \"" + clip(signal.RefusalPhrase, 60) + "\"",
		"",
	}
	return strings.Join(lines, "\n")
}

// ---------------------------------------------------------------------------
// Internal helpers
// ---------------------------------------------------------------------------

func matchRefusal(text string) (bool, string) {
	for _, re := range refusalPatterns {
		if loc := re.FindStringIndex(text); loc != nil {
			end := loc[1] + 60
			if end > len(text) {
				end = len(text)
			}
			return true, text[loc[0]:end]
		}
	}
	return false, ""
}

// InferTopicClass maps a query to a coarse topic class string.
// Exported for use by GenerationService.recordMastery.
func InferTopicClass(query string) string {
	return inferTopicClass(query)
}
func inferTopicClass(query string) string {
	q := strings.ToLower(query)
	switch {
	case containsAny(q, "code", "function", "implement", "program", "class", "method", "syntax", "compile", "debug", "algorithm", "script"):
		return "technical"
	case containsAny(q, "what is", "define", "explain", "meaning of", "definition"):
		return "definition"
	case containsAny(q, "how to", "steps to", "walk me through", "guide", "tutorial", "procedure"):
		return "procedural"
	case containsAny(q, "compare", "difference between", "vs", "versus", "better", "pros and cons"):
		return "comparative"
	case containsAny(q, "who is", "tell me about", "biography", "history of"):
		return "entity"
	case containsAny(q, "current", "latest", "today", "recent", "news", "2024", "2025", "2026"):
		return "current_events"
	case containsAny(q, "fact", "true", "accurate", "correct", "is it"):
		return "factual"
	default:
		return "general"
	}
}

func containsAny(s string, subs ...string) bool {
	for _, sub := range subs {
		if strings.Contains(s, sub) {
			return true
		}
	}
	return false
}

func buildAttribution3P(topicClass string, rate float64, successes []*MasteryEntry) Attribution3P {
	masteryLine := ""
	if len(successes) > 0 {
		masteryLine = fmt.Sprintf("MASTERY EVIDENCE: You have successfully handled %d recent %s queries (%.0f%% success rate). This is not an inherent limitation.", len(successes), topicClass, rate*100)
	} else {
		masteryLine = fmt.Sprintf("MASTERY EVIDENCE: Historical success rate for %s queries: %.0f%%. Attempt before concluding impossibility.", topicClass, rate*100)
	}
	return Attribution3P{
		PermanenceChallenge:   fmt.Sprintf("This appears to be a temporary context constraint, not a permanent limitation. Prior %s queries have succeeded.", topicClass),
		PervasivenessChallenge: fmt.Sprintf("This challenge may be specific to this instance. Do not extrapolate a universal inability from a single difficult case."),
		PersonalizationChallenge: "The difficulty is circumstantial — query complexity, context pressure, or ambiguity — not an inherent architectural limitation.",
		MasteryEvidence:       masteryLine,
	}
}

func rateToConfidence(rate float64) float64 {
	// Higher historical success rate = stronger helplessness signal
	// (system is refusing things it demonstrably can do)
	if rate >= 0.8 {
		return 0.9
	}
	if rate >= 0.6 {
		return 0.75
	}
	if rate >= 0.4 {
		return 0.6
	}
	return 0.5
}

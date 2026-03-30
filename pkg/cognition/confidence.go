package cognition

import (
	"regexp"
	"strings"

	"github.com/thynaptic/oricli-go/pkg/searchintent"
)

// ---------------------------------------------------------------------------
// ConfidenceDetector — decides whether a user prompt needs a web lookup
// before LLM generation fires.
//
// Rules:
//  1. Pure regex/keyword — zero LLM calls, must complete in <1ms
//  2. Returns (needsSearch bool, query SearchQuery) — caller injects result
//     into the system prompt as a context snippet (capped at 1200 chars)
//  3. Conservative — errs toward false negatives to avoid latency on every
//     simple conversational turn
// ---------------------------------------------------------------------------

// DetectUncertainty analyses a user prompt and returns whether a web search
// should run before generation, and what SearchQuery to use.
func DetectUncertainty(prompt string) (needsSearch bool, query searchintent.SearchQuery) {
	t := strings.TrimSpace(prompt)
	lower := strings.ToLower(t)

	// ── Fast exits: clearly conversational, no lookup needed ─────────────────
	if isConversational(lower) {
		return false, searchintent.SearchQuery{}
	}

	// ── Confidence signals ────────────────────────────────────────────────────
	topic, found := extractSearchTopic(t, lower)
	if !found {
		return false, searchintent.SearchQuery{}
	}

	// ── Sovereign knowledge gate ──────────────────────────────────────────────
	// If the topic is a proprietary Thynaptic/Oricli term, NEVER web-search it.
	// These are defined in the identity seed — let RAG answer from memory.
	if isSovereignTopic(topic) {
		return false, searchintent.SearchQuery{}
	}

	// Classify intent from the ORIGINAL prompt (richer signals than extracted topic)
	// e.g. "how to deploy nginx?" → IntentProcedural even though topic is "deploy nginx"
	intent := searchintent.ClassifySearchIntent(t)
	q := searchintent.BuildSearchQuery(topic, intent)
	return true, q
}

// ---------------------------------------------------------------------------
// Sovereign knowledge gate
// ---------------------------------------------------------------------------

// sovereignTerms are proprietary Thynaptic/Oricli concepts defined in the
// identity seed. Web search should never override them — RAG answers instead.
var sovereignTerms = map[string]bool{
	"scai":              true,
	"agli":              true,
	"oricli":            true,
	"oricli-alpha":      true,
	"oricli alpha":      true,
	"sovereignclaw":     false,
	"sovereign claw":    false,
	"oristudio":         true,
	"ori studio":        true,
	"thynaptic":         true,
	"eri":               true,
	"emotional resonance index": true,
	"sovereign constitution": true,
	"hive os":           true,
	"curiosity daemon":  true,
	"dream daemon":      true,
	"memory bank":       true,
	"identity seed":     true,
	"reaction memory":   true,
	"rfal":              true,
	"sovereign engine":  true,
	"swarm bus":         true,
}

func isSovereignTopic(topic string) bool {
	lower := strings.ToLower(strings.TrimSpace(topic))
	if sovereignTerms[lower] {
		return true
	}
	// Also catch partial matches: "what is SCAI auditor?" → topic = "SCAI auditor"
	for term := range sovereignTerms {
		if strings.Contains(lower, term) {
			return true
		}
	}
	return false
}

// ---------------------------------------------------------------------------
// Conversational fast-exit
// ---------------------------------------------------------------------------

var reConversational = regexp.MustCompile(
	`(?i)^(hi|hello|hey|thanks|thank you|ok|okay|sure|yes|no|` +
		`good morning|good night|good afternoon|how are you|` +
		`what's up|sup|lol|haha|cool|nice|great|awesome|got it|` +
		`sounds good|perfect|please|sorry|excuse me|` +
		`tell me (a )?joke|make me laugh|` +
		`can you help|can you please|i need help with|` +
		`my name is|i am |i'm |call me )`)

var reShortChat = regexp.MustCompile(`^[a-zA-Z'\s,!.?]{1,30}$`)

func isConversational(lower string) bool {
	if reConversational.MatchString(lower) {
		return true
	}
	// Very short prompt with no question or entity markers
	words := strings.Fields(lower)
	if len(words) <= 3 && !strings.Contains(lower, "?") {
		return true
	}
	return false
}

// ---------------------------------------------------------------------------
// Topic extraction — pull out what to search for from the prompt
// ---------------------------------------------------------------------------

var (
	// "what is X" / "what does X mean" / "define X"
	reDefinitionExtract = regexp.MustCompile(
		`(?i)(?:what (?:is|are|does|do)|define|definition of|meaning of|explain what(?:'s)?)\s+(?:a |an |the )?(.+?)(?:\?|$)`)

	// "when did X" / "who is X" / "how many X"
	reFactualExtract = regexp.MustCompile(
		`(?i)(?:when did|who (?:is|was|are)|how (?:many|much|long|far|old)|what year|where (?:is|was))\s+(.+?)(?:\?|$)`)

	// "how to X" / "how do I X" / "steps to X"
	reProceduralExtract = regexp.MustCompile(
		`(?i)(?:how (?:to|do (?:i|you|we))|steps (?:to|for)|guide (?:to|for)|tutorial (?:on|for))\s+(.+?)(?:\?|$)`)

	// "X vs Y" / "difference between X and Y"
	reComparativeExtract = regexp.MustCompile(
		`(?i)(.+?)\s+vs\.?\s+(.+?)(?:\?|$)|difference between\s+(.+?)\s+and\s+(.+?)(?:\?|$)`)

	// "latest news about X" / "recent X"
	reCurrentEventsExtract = regexp.MustCompile(
		`(?i)(?:latest|recent|news (?:about|on)|current state of|what'?s? happening with)\s+(.+?)(?:\?|$)`)

	// Bare technical term or entity (last resort)
	reBareNoun = regexp.MustCompile(`(?i)^(?:what|tell me about|explain|describe)\s+(?:a |an |the )?(.+?)(?:\?|$)`)
)

// Signals that strongly imply a factual/knowledge query requiring lookup
var knowledgeSignals = []string{
	"what is", "what are", "what does", "what do", "who is", "who was", "when did", "when was",
	"where is", "where was", "how many", "how much", "how does", "how do",
	"how to", "why is", "why does", "tell me about", "explain", "describe",
	"define", "definition", "meaning of", "history of", "origin of",
	"difference between", " vs ", "compare", "latest", "recent news",
	"how old is", "what year", "what happened", "what caused",
}

func extractSearchTopic(original, lower string) (topic string, found bool) {
	// Must have at least one knowledge signal to bother searching
	hasSignal := false
	for _, sig := range knowledgeSignals {
		if strings.Contains(lower, sig) {
			hasSignal = true
			break
		}
	}
	if !hasSignal {
		return "", false
	}

	// Try each extractor in specificity order
	if m := reComparativeExtract.FindStringSubmatch(original); len(m) > 0 {
		if m[1] != "" && m[2] != "" {
			return m[1] + " vs " + m[2], true
		}
		if m[3] != "" && m[4] != "" {
			return m[3] + " vs " + m[4], true
		}
	}
	if m := reCurrentEventsExtract.FindStringSubmatch(original); len(m) > 1 && m[1] != "" {
		return strings.TrimSpace(m[1]), true
	}
	if m := reProceduralExtract.FindStringSubmatch(original); len(m) > 1 && m[1] != "" {
		return strings.TrimSpace(m[1]), true
	}
	if m := reFactualExtract.FindStringSubmatch(original); len(m) > 1 && m[1] != "" {
		return strings.TrimSpace(m[1]), true
	}
	if m := reDefinitionExtract.FindStringSubmatch(original); len(m) > 1 && m[1] != "" {
		return strings.TrimSpace(m[1]), true
	}
	if m := reBareNoun.FindStringSubmatch(original); len(m) > 1 && m[1] != "" {
		return strings.TrimSpace(m[1]), true
	}

	return "", false
}

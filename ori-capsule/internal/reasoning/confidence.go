package reasoning

import (
	"regexp"
	"strings"
)

// DetectUncertainty returns whether the prompt looks like it needs external facts.
// Capsule does NOT fetch the web here — only classifies + optional system caution.
// Pure regex, <1ms.
func DetectUncertainty(prompt string) (needsSearch bool, query SearchQuery) {
	t := strings.TrimSpace(prompt)
	lower := strings.ToLower(t)

	if isConversational(lower) {
		return false, SearchQuery{}
	}
	topic, found := extractSearchTopic(t, lower)
	if !found {
		return false, SearchQuery{}
	}
	if isSovereignTopic(topic) {
		return false, SearchQuery{}
	}
	intent := ClassifySearchIntent(t)
	return true, BuildSearchQuery(topic, intent)
}

var sovereignTerms = map[string]bool{
	"scai": true, "oricli": true, "ori-capsule": true, "ori capsule": true,
	"oristudio": true, "ori studio": true, "thynaptic": true,
	"sovereign constitution": true, "memory bank": true,
}

func isSovereignTopic(topic string) bool {
	lower := strings.ToLower(strings.TrimSpace(topic))
	if sovereignTerms[lower] {
		return true
	}
	for term := range sovereignTerms {
		if strings.Contains(lower, term) {
			return true
		}
	}
	return false
}

var reConversational = regexp.MustCompile(
	`(?i)^(hi|hello|hey|thanks|thank you|ok|okay|sure|yes|no|` +
		`good morning|good night|good afternoon|how are you|` +
		`what's up|sup|lol|haha|cool|nice|great|awesome|got it|` +
		`sounds good|perfect|please|sorry|excuse me|` +
		`tell me (a )?joke|make me laugh|` +
		`can you help|can you please|i need help with|` +
		`my name is|i am |i'm |call me )`)

var reSessionIntrospective = regexp.MustCompile(
	`(?i)(what (?:did (?:we|i)|have we) (?:talk|discuss|say|cover|work)|` +
		`what (?:are|were) we (?:working on|building|doing|discussing|talking about)|` +
		`(?:recap|summari[sz]e|summary|overview) (?:of |our |what |this )?(?:session|conversation|chat)|` +
		`(?:what|current) time|what's the time|what time is it)`)

func isConversational(lower string) bool {
	if reConversational.MatchString(lower) {
		return true
	}
	if reSessionIntrospective.MatchString(lower) {
		return true
	}
	words := strings.Fields(lower)
	if len(words) <= 3 && !strings.Contains(lower, "?") {
		return true
	}
	return false
}

var (
	reDefinitionExtract = regexp.MustCompile(
		`(?i)(?:what (?:is|are|does|do)|define|definition of|meaning of|explain what(?:'s)?)\s+(?:a |an |the )?(.+?)(?:\?|$)`)
	reFactualExtract = regexp.MustCompile(
		`(?i)(?:when did|who (?:is|was|are)|how (?:many|much|long|far|old)|what year|where (?:is|was))\s+(.+?)(?:\?|$)`)
	reProceduralExtract = regexp.MustCompile(
		`(?i)(?:how (?:to|do (?:i|you|we))|steps (?:to|for)|guide (?:to|for)|tutorial (?:on|for))\s+(.+?)(?:\?|$)`)
	reComparativeExtract = regexp.MustCompile(
		`(?i)(.+?)\s+vs\.?\s+(.+?)(?:\?|$)|difference between\s+(.+?)\s+and\s+(.+?)(?:\?|$)`)
	reCurrentEventsExtract = regexp.MustCompile(
		`(?i)(?:latest|recent|news (?:about|on)|current state of|what'?s? happening with)\s+(.+?)(?:\?|$)`)
	reBareNoun = regexp.MustCompile(`(?i)^(?:what|tell me about|explain|describe)\s+(?:a |an |the )?(.+?)(?:\?|$)`)
)

var knowledgeSignals = []string{
	"what is", "what are", "what does", "what do", "who is", "who was", "when did", "when was",
	"where is", "where was", "how many", "how much", "how does", "how do",
	"how to", "why is", "why does", "tell me about", "explain", "describe",
	"define", "definition", "meaning of", "history of", "origin of",
	"difference between", " vs ", "compare", "latest", "recent news",
	"how old is", "what year", "what happened", "what caused",
}

func extractSearchTopic(original, lower string) (topic string, found bool) {
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

// FormatUncertaintyHint warns the model when a lookup would help — no fetch.
func FormatUncertaintyHint(needs bool, q SearchQuery) string {
	if !needs {
		return ""
	}
	return "### FACTUAL CAUTION\n" +
		"This looks like a knowledge lookup (intent=" + string(q.Intent) +
		", topic=\"" + q.RawTopic + "\"). Prefer grounded facts; say when unsure; do not invent citations.\n" +
		"### END FACTUAL CAUTION"
}

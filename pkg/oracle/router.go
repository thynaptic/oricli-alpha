package oracle

import "strings"

// Tier represents the optimal inference backend for a given query.
type Tier int

const (
	// TierOllamaFast — purely conversational; local model is fast enough.
	TierOllamaFast Tier = iota
	// TierOracleTemporal — session/temporal recall; Oracle with minimal prompt
	// (skip the 2000-token composite system prompt entirely).
	TierOracleTemporal
	// TierOracleDefault — everything else; Oracle with full enriched context.
	// gpt-5-mini baseline = unlimited quota, no weak spots.
	TierOracleDefault
)

// Classify determines the optimal routing tier for a query.
// Rules (in priority order):
//  1. Short social/greeting → Ollama fast path
//  2. Session/temporal introspection → Oracle temporal (minimal prompt)
//  3. Everything else → Oracle default (full context)
func Classify(query string) Tier {
	lower := strings.ToLower(strings.TrimSpace(query))

	// Pure conversational one-liners — Ollama handles these fine.
	if isConversationalShort(lower) {
		return TierOllamaFast
	}

	// Session/temporal recall — Oracle with a lean temporal-only prompt.
	if isSessionIntrospective(query) {
		return TierOracleTemporal
	}

	return TierOracleDefault
}

// ConvertMsgs converts the server's []map[string]string message format to
// the oracle.Message slice expected by ChatStream.
func ConvertMsgs(msgs []map[string]string) []Message {
	out := make([]Message, 0, len(msgs))
	for _, m := range msgs {
		out = append(out, Message{Role: m["role"], Content: m["content"]})
	}
	return out
}

// Collect drains a ChatStream channel and returns the full response string.
func Collect(ch <-chan string) string {
	var sb strings.Builder
	for tok := range ch {
		sb.WriteString(tok)
	}
	return sb.String()
}

// ─── Routing helpers (duplicated from cognition to avoid import cycle) ────────

// conversational prefixes/patterns — short social turns that don't need Oracle.
var conversationalPrefixes = []string{
	"hi", "hello", "hey", "thanks", "thank you", "ok", "okay", "sure",
	"yes", "no", "good morning", "good night", "good afternoon", "lol",
	"haha", "cool", "nice", "great", "awesome", "got it", "sounds good",
	"perfect", "please", "sorry",
}

func isConversationalShort(lower string) bool {
	for _, pfx := range conversationalPrefixes {
		if lower == pfx || strings.HasPrefix(lower, pfx+" ") || strings.HasPrefix(lower, pfx+",") {
			return true
		}
	}
	// Very short with no question mark or entity markers
	words := strings.Fields(lower)
	return len(words) <= 3 && !strings.Contains(lower, "?")
}

// sessionIntrospectiveTerms — triggers for temporal routing.
var sessionIntrospectiveTerms = []string{
	"what did we talk", "what did we discuss", "what have we talked",
	"what have we discussed", "what are we working on", "what were we working on",
	"what are we building", "what are we doing", "what are we discussing",
	"recap", "summarise", "summarize", "summary", "overview", "timeline",
	"walk me through", "how long have we", "how long has this session",
	"when did we start", "when did this session", "what time", "what's the time",
	"current time", "how long ago", "how long since", "session start",
	"session age", "session duration", "last session", "last conversation",
}

func isSessionIntrospective(query string) bool {
	lower := strings.ToLower(query)
	for _, term := range sessionIntrospectiveTerms {
		if strings.Contains(lower, term) {
			return true
		}
	}
	return false
}

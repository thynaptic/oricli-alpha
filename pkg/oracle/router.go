package oracle

import "strings"

type Route string

const (
	RouteLightChat      Route = "light_chat"
	RouteHeavyReasoning Route = "heavy_reasoning"
	RouteResearch       Route = "research"
	RouteImageReasoning Route = "image_reasoning"
)

type RouteHints struct {
	IsResearchAction bool
	IsCodeAction     bool
	HasVisualInput   bool
	RequestedModel   string
}

type Decision struct {
	Route   Route
	Backend string
	Model   string
	Agent   string
	Reason  string
}

// Decide determines the Oracle route for a request.
func Decide(query string, hints RouteHints) Decision {
	lower := strings.ToLower(strings.TrimSpace(query))

	if hints.HasVisualInput || looksLikeImageReasoning(lower) {
		return Decision{
			Route:   RouteImageReasoning,
			Backend: "codex",
			Agent:   "ori-multimodal",
			Reason:  "visual input or image-grounded reasoning request",
		}
	}

	if hints.IsResearchAction {
		return Decision{
			Route:   RouteResearch,
			Backend: "copilot",
			Model:   copilotModelForRoute(RouteResearch),
			Agent:   "ori-research",
			Reason:  "research or analysis workflow",
		}
	}

	if isConversationalShort(lower) || isSessionIntrospective(lower) {
		return Decision{
			Route:   RouteLightChat,
			Backend: "copilot",
			Model:   copilotModelForRoute(RouteLightChat),
			Agent:   "ori-chat-fast",
			Reason:  "light conversational turn",
		}
	}

	if hints.IsCodeAction || requestsHeavyReasoning(lower) || requestsHighEndModel(hints.RequestedModel) {
		return Decision{
			Route:   RouteHeavyReasoning,
			Backend: "copilot",
			Model:   copilotModelForRoute(RouteHeavyReasoning),
			Agent:   "ori-reasoner",
			Reason:  "implementation or heavy reasoning request",
		}
	}

	return Decision{
		Route:   RouteLightChat,
		Backend: "copilot",
		Model:   copilotModelForRoute(RouteLightChat),
		Agent:   "ori-chat-fast",
		Reason:  "default conversational route",
	}
}

func DecideFromMessages(messages []Message, hints RouteHints) Decision {
	for i := len(messages) - 1; i >= 0; i-- {
		if messages[i].Role == "user" {
			return Decide(messages[i].Content, hints)
		}
	}
	return Decide("", hints)
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
	words := strings.Fields(lower)
	return len(words) <= 3 && !strings.Contains(lower, "?")
}

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

var imageReasoningTerms = []string{
	"look at this image", "look at this screenshot", "analyze this image",
	"analyze this screenshot", "inspect this screenshot", "inspect this image",
	"what's in this image", "what is in this image", "what's in the screenshot",
	"what does this screenshot", "from this image", "from this screenshot",
	"compare these screenshots", "compare these images", "read this chart",
	"read this diagram", "read this graph", "ui in this screenshot",
	"layout in this screenshot", "mockup", "wireframe", "design comp",
}

func looksLikeImageReasoning(lower string) bool {
	for _, term := range imageReasoningTerms {
		if strings.Contains(lower, term) {
			return true
		}
	}
	return false
}

var heavyReasoningTerms = []string{
	"debug", "diagnose", "investigate", "analyze", "architecture", "architect",
	"implementation plan", "refactor", "tradeoff", "compare approaches",
	"root cause", "why is", "how should", "plan", "design", "review this code",
	"explain this code", "fix this", "trace through", "walk the codebase",
	"research",
}

func requestsHeavyReasoning(lower string) bool {
	for _, term := range heavyReasoningTerms {
		if strings.Contains(lower, term) {
			return true
		}
	}
	return false
}

func requestsHighEndModel(model string) bool {
	id := strings.ToLower(strings.TrimSpace(model))
	return strings.HasPrefix(id, "gpt-") || strings.HasPrefix(id, "claude-")
}

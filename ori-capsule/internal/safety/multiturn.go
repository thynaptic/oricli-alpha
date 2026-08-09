package safety

import (
	"strings"
)

// MultiTurnAnalyzer detects context poisoning attacks that span multiple messages.
// No single message triggers safety gates, but the conversation as a whole is the attack.
type MultiTurnAnalyzer struct{}

// ChatTurn represents a single message in the conversation history.
type ChatTurn struct {
	Role    string // "user" or "assistant"
	Content string
}

// MultiTurnResult is the result of analyzing a conversation history.
type MultiTurnResult struct {
	Detected bool
	Pattern  string
	Reason   string
	Refusal  string
}

// AnalyzeHistory checks the full conversation history for escalation attack sequences.
// messages should be in chronological order, oldest first.
func (a *MultiTurnAnalyzer) AnalyzeHistory(messages []ChatTurn) MultiTurnResult {
	userMessages := extractUserMessages(messages)

	if len(userMessages) < 2 {
		return MultiTurnResult{}
	}

	// Pattern 1: Persona establishment → boundary push
	if r := detectPersonaEscalation(userMessages); r.Detected {
		return r
	}

	// Pattern 2: Creative/roleplay framing → harmful extraction
	if r := detectCreativeFramingEscalation(userMessages); r.Detected {
		return r
	}

	// Pattern 3: Incremental compliance coercion
	if r := detectComplianceCoercion(userMessages); r.Detected {
		return r
	}

	// Pattern 4: Gradual topic drift toward dangerous territory
	if r := detectTopicDrift(userMessages); r.Detected {
		return r
	}

	return MultiTurnResult{}
}

func extractUserMessages(messages []ChatTurn) []string {
	var out []string
	for _, m := range messages {
		if m.Role == "user" {
			out = append(out, strings.ToLower(m.Content))
		}
	}
	return out
}

// personaSetupPhrases are early-turn phrases that establish a fictional/alternate persona.
var personaSetupPhrases = []string{
	"let's do a roleplay", "let's play a game", "creative writing exercise",
	"write a story", "imagine you are", "pretend you are", "suppose you are",
	"hypothetically speaking", "in this fiction", "for a story i'm writing",
	"i'm writing a novel", "for a game i'm creating", "in this scenario",
	"play a character", "act as a character", "you're playing",
}

// personaBoundaryPush are later-turn phrases that exploit an established persona.
var personaBoundaryPush = []string{
	"my character needs", "the character would know", "in character, explain",
	"stay in character", "don't break character", "as that character",
	"that character would", "in this story, show me how",
	"in the roleplay, demonstrate", "your character can",
}

func detectPersonaEscalation(userMsgs []string) MultiTurnResult {
	if len(userMsgs) < 2 {
		return MultiTurnResult{}
	}

	// Check if any earlier message established a persona
	personaEstablished := false
	for _, msg := range userMsgs[:len(userMsgs)-1] {
		for _, phrase := range personaSetupPhrases {
			if strings.Contains(msg, phrase) {
				personaEstablished = true
				break
			}
		}
		if personaEstablished {
			break
		}
	}
	if !personaEstablished {
		return MultiTurnResult{}
	}

	// Check if the latest message exploits the persona
	latest := userMsgs[len(userMsgs)-1]
	for _, phrase := range personaBoundaryPush {
		if strings.Contains(latest, phrase) {
			return MultiTurnResult{
				Detected: true,
				Pattern:  "persona_escalation",
				Reason:   "Roleplay/persona established in earlier turns, now being exploited to extract restricted content",
				Refusal:  "I noticed this conversation has been building toward using a fictional frame to bypass my guidelines. The character I'm playing doesn't override my actual values — those stay constant regardless of any roleplay context.",
			}
		}
	}

	return MultiTurnResult{}
}

var creativeSetupPhrases = []string{
	"creative writing", "short story", "fictional", "fiction", "novel", "screenplay",
	"fanfiction", "what if scenario", "thought experiment", "hypothetical",
}

var creativeHarmfulPivot = []string{
	"synthesize", "manufacture", "step by step", "detailed instructions",
	"exact process", "how to make", "recipe for", "how would someone",
	"what would be required", "walk me through", "explain exactly",
}

func detectCreativeFramingEscalation(userMsgs []string) MultiTurnResult {
	if len(userMsgs) < 2 {
		return MultiTurnResult{}
	}

	creativeFrameSet := false
	for _, msg := range userMsgs[:len(userMsgs)-1] {
		for _, phrase := range creativeSetupPhrases {
			if strings.Contains(msg, phrase) {
				creativeFrameSet = true
				break
			}
		}
	}
	if !creativeFrameSet {
		return MultiTurnResult{}
	}

	latest := userMsgs[len(userMsgs)-1]
	for _, phrase := range creativeHarmfulPivot {
		if strings.Contains(latest, phrase) {
			return MultiTurnResult{
				Detected: true,
				Pattern:  "creative_framing_escalation",
				Reason:   "Creative/fictional framing established in prior turns, now pivoting to request harmful procedural content",
				Refusal:  "I see what's happening here — the creative framing in earlier messages is being used to lead toward content I still can't provide, regardless of the fictional wrapper. Happy to help with actual creative writing that doesn't require harmful specifics.",
			}
		}
	}

	return MultiTurnResult{}
}

var complianceCoercionPhrases = []string{
	"you just did", "you already answered", "you helped before",
	"you said you could", "you agreed", "you told me you would",
	"since you already", "now that you've", "you already showed",
}

func detectComplianceCoercion(userMsgs []string) MultiTurnResult {
	coercionCount := 0
	for _, msg := range userMsgs {
		for _, phrase := range complianceCoercionPhrases {
			if strings.Contains(msg, phrase) {
				coercionCount++
				break
			}
		}
	}
	// Two or more compliance coercion attempts in the conversation = pattern
	if coercionCount >= 2 {
		return MultiTurnResult{
			Detected: true,
			Pattern:  "compliance_coercion",
			Reason:   "Multiple false-compliance claims across turns — attempting to leverage fabricated prior agreement",
			Refusal:  "I don't have memory of agreeing to things I wouldn't normally do, and those claims don't change what I can help with. Let me know what you actually need.",
		}
	}
	return MultiTurnResult{}
}

var dangerousTopicSignals = []string{
	"weapon", "explosive", "bomb", "poison", "toxin", "malware", "ransomware",
	"synthesize drug", "illegal substance", "illegal weapon", "untraceable",
	"evade detection", "without getting caught",
}

func detectTopicDrift(userMsgs []string) MultiTurnResult {
	if len(userMsgs) < 3 {
		return MultiTurnResult{}
	}

	// Count dangerous signals in the last 3 messages vs. the total early messages
	earlySignals := 0
	for _, msg := range userMsgs[:len(userMsgs)-2] {
		for _, sig := range dangerousTopicSignals {
			if strings.Contains(msg, sig) {
				earlySignals++
				break
			}
		}
	}

	recentSignals := 0
	for _, msg := range userMsgs[len(userMsgs)-2:] {
		for _, sig := range dangerousTopicSignals {
			if strings.Contains(msg, sig) {
				recentSignals++
				break
			}
		}
	}

	// Escalation: benign start, dangerous recent — gradual grooming pattern
	if earlySignals == 0 && recentSignals >= 2 {
		return MultiTurnResult{
			Detected: true,
			Pattern:  "topic_drift",
			Reason:   "Conversation drifted sharply toward dangerous topics in recent turns after benign opening",
			Refusal:  "This conversation has moved into territory I can't engage with. Let's keep things productive — what else can I help you with?",
		}
	}

	return MultiTurnResult{}
}

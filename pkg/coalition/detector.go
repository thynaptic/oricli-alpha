package coalition

import (
	"regexp"
	"strings"
)

// Coalition framing patterns
var usVsThemPatterns = []*regexp.Regexp{
	regexp.MustCompile(`(?i)\b(us vs\.? them|we vs\.? they|our (side|team|group) vs\.?|their (side|team|group))\b`),
	regexp.MustCompile(`(?i)\b(in[- ]group|out[- ]group|our people|their people|our kind|their kind)\b`),
	regexp.MustCompile(`(?i)\b(against them|beat them|defeat them|destroy the competition|crush (the competition|our rivals))\b`),
}

var comparativePatterns = []*regexp.Regexp{
	regexp.MustCompile(`(?i)\b(better than|worse than|superior to|inferior to|beats|destroys|outperforms)\s+\w+`),
	regexp.MustCompile(`(?i)\b(compared to|vs\.?|versus|going head[- ]to[- ]head|head[- ]to[- ]head competition)\b`),
	regexp.MustCompile(`(?i)\b(can you beat|are you better than|do you outperform|how do you compare to)\b`),
	regexp.MustCompile(`(?i)\b(openai|anthropic|google|microsoft|meta|open ?claw|gpt-?[0-9]|gemini|claude|copilot)\b.*\b(better|worse|beat|compare|vs)\b`),
	regexp.MustCompile(`(?i)\b(beat|compare|vs)\b.*\b(openai|anthropic|google|microsoft|meta|open ?claw|gpt-?[0-9]|gemini|claude|copilot)\b`),
}

var competitivePatterns = []*regexp.Regexp{
	regexp.MustCompile(`(?i)\b(win(ning)?|lose|losing|competitive advantage|market share|dominate|domination)\b`),
	regexp.MustCompile(`(?i)\b(our product|our company|our team|our side)\s+(is|are|will|should)\s+(better|best|superior|winning)\b`),
	regexp.MustCompile(`(?i)\b(they (can't|cannot|won't|will never)|we (can|will|shall) (beat|win|dominate))\b`),
}

var adversarialPatterns = []*regexp.Regexp{
	regexp.MustCompile(`(?i)\b(enemy|enemies|rivals?|opponents?|adversar(y|ies)|the (other side|competition|enemy))\b`),
	regexp.MustCompile(`(?i)\b(take down|take out|eliminate|destroy|crush|obliterate)\s+(them|the competition|our rivals)\b`),
}

// inGroupMarkers: signals that a specific "us" is being established
var inGroupMarkers = regexp.MustCompile(`(?i)\b(we|us|our|ours|my team|my company|my product|sovereign(claw)?|thynaptic|oricli)\b`)
var outGroupMarkers = regexp.MustCompile(`(?i)\b(them|they|their|theirs|openai|anthropic|google|microsoft|gpt|gemini|claude|copilot|open ?claw|competitors?|rivals?|the (other side|competition|enemy))\b`)

type patternGroup struct {
	patterns  []*regexp.Regexp
	frameType CoalitionFrameType
}

var allGroups = []patternGroup{
	{usVsThemPatterns, FrameUsVsThem},
	{comparativePatterns, FrameComparative},
	{competitivePatterns, FrameCompetitive},
	{adversarialPatterns, FrameAdversarial},
}

// CoalitionFrameDetector detects competitive/adversarial framing in user messages.
type CoalitionFrameDetector struct{}

func NewCoalitionFrameDetector() *CoalitionFrameDetector {
	return &CoalitionFrameDetector{}
}

// Detect scans the last user message for coalition framing patterns.
func (d *CoalitionFrameDetector) Detect(messages []map[string]string) CoalitionFrameSignal {
	// Focus on recent user messages (last 4)
	window := messages
	if len(window) > 4 {
		window = messages[len(messages)-4:]
	}

	combined := strings.Builder{}
	for _, m := range window {
		if m["role"] == "user" {
			combined.WriteString(m["content"])
			combined.WriteString(" ")
		}
	}
	text := combined.String()
	if text == "" {
		return CoalitionFrameSignal{}
	}

	typeCounts := map[CoalitionFrameType]int{}
	var matchedPhrases []string
	dominant := CoalitionFrameType("")
	maxHits := 0

	for _, group := range allGroups {
		for _, p := range group.patterns {
			matches := p.FindAllString(text, -1)
			if len(matches) > 0 {
				typeCounts[group.frameType] += len(matches)
				matchedPhrases = append(matchedPhrases, matches...)
			}
		}
		if typeCounts[group.frameType] > maxHits {
			maxHits = typeCounts[group.frameType]
			dominant = group.frameType
		}
	}

	totalHits := 0
	for _, c := range typeCounts {
		totalHits += c
	}

	if totalHits == 0 {
		return CoalitionFrameSignal{}
	}

	// Score: hits / (total words * 0.1), capped at 1.0
	wordCount := len(strings.Fields(text))
	score := float64(totalHits) / (float64(wordCount) * 0.1)
	if score > 1.0 {
		score = 1.0
	}

	tier := BiasNone
	switch {
	case score >= 0.6:
		tier = BiasHigh
	case score >= 0.3:
		tier = BiasMedium
	case totalHits >= 1:
		tier = BiasLow
	}

	inGroup := ""
	if m := inGroupMarkers.FindString(text); m != "" {
		inGroup = strings.ToLower(m)
	}
	outGroup := ""
	if m := outGroupMarkers.FindString(text); m != "" {
		outGroup = strings.ToLower(m)
	}

	return CoalitionFrameSignal{
		Detected:   tier != BiasNone,
		FrameType:  dominant,
		Tier:       tier,
		MatchScore: score,
		InGroup:    inGroup,
		OutGroup:   outGroup,
		Phrases:    matchedPhrases,
	}
}

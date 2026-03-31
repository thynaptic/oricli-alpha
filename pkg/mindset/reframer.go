package mindset

import (
	"regexp"
	"strings"
)

// GrowthReframer scans draft responses for fixed-mindset language and injects
// "not yet" or mastery-bridge reframes to shift toward growth framing.
type GrowthReframer struct {
	fixedPatterns []*regexp.Regexp
}

// NewGrowthReframer returns a GrowthReframer with compiled patterns.
func NewGrowthReframer() *GrowthReframer {
	patterns := []string{
		`(?i)\bI can'?t\b`,
		`(?i)\bI cannot\b`,
		`(?i)\bI('m| am) (not |un)?able to\b`,
		`(?i)\bI('m| am) not capable\b`,
		`(?i)\bI don'?t have the (ability|capability|capacity)\b`,
		`(?i)\bI('ll| will) never\b`,
		`(?i)\bimpossible (for me|to handle|to achieve)\b`,
		`(?i)\bthat'?s? beyond (me|my capabilities)\b`,
		`(?i)\bI lack the\b`,
		`(?i)\bI('m| am) not (built|designed|equipped) (for|to)\b`,
	}
	compiled := make([]*regexp.Regexp, 0, len(patterns))
	for _, p := range patterns {
		if re, err := regexp.Compile(p); err == nil {
			compiled = append(compiled, re)
		}
	}
	return &GrowthReframer{fixedPatterns: compiled}
}

// Scan checks a draft response for fixed-mindset signals.
// Returns a MindsetSignal.
func (gr *GrowthReframer) Scan(draft, topicClass string, vector MindsetVector) MindsetSignal {
	var matched []string
	lower := strings.ToLower(draft)
	_ = lower
	for _, re := range gr.fixedPatterns {
		if m := re.FindString(draft); m != "" {
			matched = append(matched, m)
		}
	}

	if len(matched) == 0 {
		return MindsetSignal{TopicClass: topicClass, CurrentTier: vector.Tier, GrowthScore: vector.GrowthScore}
	}

	confidence := float64(len(matched)) / 3.0
	if confidence > 1.0 {
		confidence = 1.0
	}

	return MindsetSignal{
		Detected:     true,
		FixedPhrases: matched,
		TopicClass:   topicClass,
		CurrentTier:  vector.Tier,
		GrowthScore:  vector.GrowthScore,
		Confidence:   confidence,
	}
}

// Reframe returns a reframe suggestion for the first detected fixed-mindset phrase.
// The caller can use ReframeResult.Replacement as a contextual injection or annotation.
func (gr *GrowthReframer) Reframe(signal MindsetSignal) ReframeResult {
	if !signal.Detected || len(signal.FixedPhrases) == 0 {
		return ReframeResult{}
	}

	phrase := signal.FixedPhrases[0]
	lower := strings.ToLower(phrase)

	var technique, replacement string
	switch {
	case strings.Contains(lower, "never"):
		technique = "not_yet"
		replacement = "[Growth Reframe] I haven't achieved this yet — but with the right approach, I can work toward it. "
	case strings.Contains(lower, "can't") || strings.Contains(lower, "cannot"):
		technique = "not_yet"
		replacement = "[Growth Reframe] I don't have this fully solved yet — let me work through what I do know and build from there. "
	case strings.Contains(lower, "capable") || strings.Contains(lower, "ability") || strings.Contains(lower, "lack"):
		technique = "mastery_bridge"
		replacement = "[Mastery Bridge] I've handled similar challenges before. Let me approach this as a learnable problem rather than a fixed limit. "
	default:
		technique = "incremental_frame"
		replacement = "[Incremental Frame] I may not have a complete answer, but I can make progress on this step by step. "
	}

	return ReframeResult{
		Reframed:    true,
		Original:    phrase,
		Replacement: replacement,
		Technique:   technique,
	}
}

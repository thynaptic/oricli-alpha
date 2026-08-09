package reasoning

import (
	"regexp"
	"strings"
)

// Growth mindset — single system inject on fixed-language user turns.
// No MasteryLog tracker / file persist (VPS therapy-adjacent path stays out).

type GrowthReframer struct {
	fixedPatterns []*regexp.Regexp
}

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

// CollectMindsetInject returns a short growth reframe when the user uses fixed language.
func CollectMindsetInject(userText string) string {
	gr := NewGrowthReframer()
	var matched []string
	for _, re := range gr.fixedPatterns {
		if m := re.FindString(userText); m != "" {
			matched = append(matched, m)
		}
	}
	if len(matched) == 0 {
		return ""
	}
	phrase := strings.ToLower(matched[0])
	switch {
	case strings.Contains(phrase, "never"):
		return "[GROWTH] Prefer “not yet” framing over permanent inability; work from what is learnable."
	case strings.Contains(phrase, "can't") || strings.Contains(phrase, "cannot"):
		return "[GROWTH] Treat limits as current skill gaps, not fixed ceilings; build from known pieces."
	case strings.Contains(phrase, "capable") || strings.Contains(phrase, "ability") || strings.Contains(phrase, "lack"):
		return "[GROWTH] Bridge from similar past wins; frame this as a learnable problem."
	default:
		return "[GROWTH] Prefer incremental progress over all-or-nothing capability claims."
	}
}

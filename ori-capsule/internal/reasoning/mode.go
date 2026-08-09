package reasoning

import (
	"regexp"
	"strings"
)

// ReasoningHint is a cheap classification for BYOK model/thinking choice.
// It does NOT run multi-gen engines (Debate/ARE/ToT/etc.).
type ReasoningHint string

const (
	HintLight    ReasoningHint = "light"
	HintStandard ReasoningHint = "standard"
	HintHeavy    ReasoningHint = "heavy"
)

var (
	reMathHint   = regexp.MustCompile(`(?i)(calculat|comput|solv|convert|how many|how long.*\d|\d.*how long|=\?|\d+[\+\-\*\/\^]\d+|integral|derivative|percent|formula|equation|proof)`)
	reLogicHint  = regexp.MustCompile(`(?i)\b(therefore\b|valid (argument|conclusion|syllogism)|logically? (follows|valid|invalid|fallac)|syllogis[m]|non.?sequitur|modus (ponens|tollens))`)
	reCausalHint = regexp.MustCompile(`(?i)(why (does|did|is|are|would|do)|what (causes|caused|led to|results in|happens if)|root cause|what if|impact of|effect of)`)
	reDebateHint = regexp.MustCompile(`(?i)(should (we|i|they|you)|is it (better|worse|right|wrong|ethical)|pros and cons|argue (for|against)|debate|versus|trade.?off|which is better)`)
	reMultiHint  = regexp.MustCompile(`(?i)(step by step|walk me through|from scratch|break.*down|comprehensive|detailed.*analysis|design.*system)`)
)

// ClassifyHint returns light/standard/heavy without spawning extra LLM calls.
func ClassifyHint(stimulus string) ReasoningHint {
	s := strings.TrimSpace(stimulus)
	lower := strings.ToLower(s)
	words := len(strings.Fields(lower))
	complexity := 0.0
	if words > 40 {
		complexity += 0.25
	}
	if words > 80 {
		complexity += 0.2
	}
	if reMultiHint.MatchString(s) {
		complexity += 0.35
	}
	if reDebateHint.MatchString(s) {
		complexity += 0.25
	}
	if reCausalHint.MatchString(s) {
		complexity += 0.2
	}
	if reMathHint.MatchString(s) || reLogicHint.MatchString(s) {
		return HintHeavy
	}
	if complexity >= 0.55 || reMultiHint.MatchString(s) && words > 25 {
		return HintHeavy
	}
	if complexity >= 0.25 || words > 20 {
		return HintStandard
	}
	return HintLight
}

func FormatHintDirective(h ReasoningHint) string {
	switch h {
	case HintHeavy:
		return "### REASONING TIER\nPrefer careful multi-step reasoning; verify intermediate claims.\n### END REASONING TIER"
	case HintStandard:
		return ""
	default:
		return ""
	}
}

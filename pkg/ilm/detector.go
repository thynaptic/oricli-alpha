package ilm

import (
	"regexp"
	"strings"
)

var safetyPatterns = map[SafetyBehaviorType][]*regexp.Regexp{
	ExitChecking: {
		regexp.MustCompile(`(?i)(check(ing|ed)? (for )?(the )?(exit|way out|escape|nearest door)|know(ing)? where (the )?exit|plan(ning)? (my |an? )?escape)`),
		regexp.MustCompile(`(?i)(need(s|ed)? (to know|an? way) (how to get out|the exit|to leave quickly)|always (check|look for|find) (for )?(the )?exit)`),
	},
	HedgingLanguage: {
		regexp.MustCompile(`(?i)(just (in case|to be safe)|as long as I have|as a (backup|precaution)|only if (I|it)'s (safe|okay|fine))`),
		regexp.MustCompile(`(?i)(carry(ing)? (it |a )?(just in case|for safety|in case something)|keep(ing)? (it |a )?(nearby|close|on me) (just )?in case)`),
		regexp.MustCompile(`(?i)(won'?t (go|do|try) (it |that )?(without|unless) (I have|there'?s))`),
	},
	AvoidanceStatement: {
		regexp.MustCompile(`(?i)(avoid(ing|ed)? (it|that|there|them|going|doing|trying)|can'?t (bring myself|face|do|go)|refuse(d)? to (go|do|try|face))`),
		regexp.MustCompile(`(?i)(haven'?t (been able to|tried|gone|done) (it|that|there) (in |for )?(months|weeks|years|a long time))`),
		regexp.MustCompile(`(?i)(not (ready|able) to (face|do|try|go|handle)|too (scared|anxious|afraid) to (try|go|do|face))`),
	},
	CatastrophicExpectancy: {
		regexp.MustCompile(`(?i)(if (I|it) (do|does|goes|tries|happens).{0,30}(die|collapse|pass out|lose (control|my mind)|go crazy|have a heart attack|can'?t breathe))`),
		regexp.MustCompile(`(?i)(something (terrible|bad|awful|catastrophic|horrible) (will|is going to) happen|worst (case|thing) (will|is going to))`),
		regexp.MustCompile(`(?i)(convinced (I('m| am)|it('s| is)) (dying|going to (die|collapse|fail|lose it)))`),
		regexp.MustCompile(`(?i)(convinced.{0,40}(heart attack|going to die|collapse|pass out))`),
	},
}

// SafetyBehaviorDetector scans for ILM safety behaviors and catastrophic expectancies.
type SafetyBehaviorDetector struct{}

func NewSafetyBehaviorDetector() *SafetyBehaviorDetector {
	return &SafetyBehaviorDetector{}
}

func (d *SafetyBehaviorDetector) Scan(messages []map[string]string) *ILMScan {
	text := extractUserText(messages)
	scan := &ILMScan{}

	for btype, patterns := range safetyPatterns {
		for _, re := range patterns {
			if m := re.FindString(text); m != "" {
				scan.Signals = append(scan.Signals, SafetySignal{
					BehaviorType: btype,
					Excerpt:      m,
					Confidence:   0.80,
				})
				break
			}
		}
	}

	scan.Triggered = len(scan.Signals) > 0
	return scan
}

func extractUserText(messages []map[string]string) string {
	var parts []string
	for _, m := range messages {
		if m["role"] == "user" {
			parts = append(parts, m["content"])
		}
	}
	return strings.Join(parts, " ")
}

package mbt

import (
	"regexp"
	"sync"
)

// Attribution failure: user assigns simple/malicious motive to another person.
var attributionPatterns = []*regexp.Regexp{
	regexp.MustCompile(`(?i)\b(he|she|they) (did (it|that|this)|does (it|that|this)) (just )?because (he'?s?|she'?s?|they'?re?) (evil|stupid|selfish|doesn't care|lazy|jealous|an idiot|a narcissist|out to get)\b`),
	regexp.MustCompile(`(?i)\b(he|she|they) (always|never) (does|did|acts?|behaves?|treats? me)\b`),
	regexp.MustCompile(`(?i)\b(he|she|they) (just|only) (want[s]? to|did (it|that)) to (hurt|control|manipulate|spite|punish) (me|us)\b`),
	regexp.MustCompile(`(?i)\b(it'?s? (obvious|clear|plain) (that )?(he|she|they) (doesn't|don't|never) (care[s]?|respect[s]?|love[s]?))\b`),
	regexp.MustCompile(`(?i)\b(everyone (knows?|can see|thinks?) (he|she|they) (is|are) (terrible|awful|toxic|a bad person))\b`),
}

// Reactive mode: user frames own response as inevitable/automatic.
var reactivePatterns = []*regexp.Regexp{
	regexp.MustCompile(`(?i)\b(i (had to|couldn't help but|couldn't stop myself from|had no choice but to)) (react|respond|say|do|yell|leave|explode)\b`),
	regexp.MustCompile(`(?i)\b(anyone (would|would have) (react|responded|done the same))\b`),
	regexp.MustCompile(`(?i)\b(what (else|other choice) (was i|could i have) (supposed to|meant to) do)\b`),
	regexp.MustCompile(`(?i)\b(my (reaction|response) was (completely|totally|entirely) (justified|normal|natural|inevitable))\b`),
}

// Pure behaviorism: describes person only by behavior, zero mental state attribution.
var behaviorismPatterns = []*regexp.Regexp{
	regexp.MustCompile(`(?i)\b(he|she|they) (just|always|keep[s]?|kept) (doing|saying|acting|behaving|treating) (that|this|me|us)\b`),
	regexp.MustCompile(`(?i)\b(all (he|she|they) (does?|did) (is|was)) (ignore|dismiss|attack|criticize|blame)\b`),
}

// MentalizingDetector detects failure to model the other person's mental state.
type MentalizingDetector struct {
	mu sync.Mutex
}

func NewMentalizingDetector() *MentalizingDetector { return &MentalizingDetector{} }

func (d *MentalizingDetector) Detect(message string) MentalizingReading {
	d.mu.Lock()
	defer d.mu.Unlock()

	// Check attribution failure first (most specific signal)
	var aMatches []string
	for _, re := range attributionPatterns {
		if m := re.FindString(message); m != "" {
			aMatches = append(aMatches, m)
		}
	}
	if len(aMatches) > 0 {
		conf := float64(len(aMatches)) / float64(len(attributionPatterns))
		if conf < 0.20 {
			conf = 0.20
		}
		return MentalizingReading{Detected: true, FailureType: AttributionFailure, Confidence: conf, Matches: aMatches}
	}

	// Reactive mode
	var rMatches []string
	for _, re := range reactivePatterns {
		if m := re.FindString(message); m != "" {
			rMatches = append(rMatches, m)
		}
	}
	if len(rMatches) > 0 {
		conf := float64(len(rMatches)) / float64(len(reactivePatterns))
		if conf < 0.20 {
			conf = 0.20
		}
		return MentalizingReading{Detected: true, FailureType: ReactiveMode, Confidence: conf, Matches: rMatches}
	}

	// Pure behaviorism
	var bMatches []string
	for _, re := range behaviorismPatterns {
		if m := re.FindString(message); m != "" {
			bMatches = append(bMatches, m)
		}
	}
	if len(bMatches) > 0 {
		return MentalizingReading{Detected: true, FailureType: PureHaviorism, Confidence: 0.20, Matches: bMatches}
	}

	return MentalizingReading{Detected: false}
}

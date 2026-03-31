package interoception

import (
	"regexp"
	"strings"
)

var interoceptivePatterns = map[InteroceptiveSignalType][]*regexp.Regexp{
	SomaticSignalPresent: {
		regexp.MustCompile(`(?i)((I (feel|notice|have|am aware of) (a |something |tension |tightness |heaviness |sensation )?(in my (chest|stomach|gut|throat|body|shoulders?|jaw|hands?|legs?|back)).{0,30}(when|as|and|while|that)))`),
		regexp.MustCompile(`(?i)((there'?s (a )?(tightness|heaviness|knot|flutter|ache|tension|warmth|coldness|numbness|tingling) (in|around) (my (chest|stomach|gut|throat|body|throat|shoulders?|heart area))))`),
		regexp.MustCompile(`(?i)((my (body|stomach|chest|gut|throat|muscles?|hands?|jaw) (feels?|is|gets?) (tight|tense|heavy|knotted|sick|uncomfortable|tingly|numb|hot|cold|shaky|frozen).{0,30}(when|as|and|while)))`),
	},
	BodyDisconnect: {
		regexp.MustCompile(`(?i)((I (feel|am|have been) (disconnected from|out of|not in|cut off from|detached from|dissociated from|numb to) (my (body|physical self|physical sensations?|flesh))))`),
		regexp.MustCompile(`(?i)((my body (feels? (foreign|not mine|like it belongs to someone else|like a machine|unreal|not real)|doesn'?t feel like mine|feels? disconnected)))`),
		regexp.MustCompile(`(?i)((I (don'?t|can'?t) (feel|notice|access|connect to|sense) (my (body|physical (sensations?|self|feelings?|signals?)|what my body is telling me))))`),
	},
	VisceralDecisionSignal: {
		regexp.MustCompile(`(?i)((my (gut|body|stomach|instinct|intuition|chest|physical reaction).{0,20}(is (telling|saying|showing|signaling|warning) me|knows?|feels? (like|that|it|this))))`),
		regexp.MustCompile(`(?i)((I (have|had|feel|felt) (a gut feeling|a feeling in my (gut|chest|stomach)|a physical sense|an instinct|something in my body).{0,20}(that|about|telling me|saying)))`),
		regexp.MustCompile(`(?i)((even (though|if|when) (my mind|logically|rationally|intellectually).{0,20}(my body|my gut|something physical|my instinct|physically) (knows?|says?|tells? me|reacts?|feels?)))`),
	},
	ProprioceptiveNeglect: {
		regexp.MustCompile(`(?i)((I (know|think|feel|believe) I (should|need to|must) (ignore|dismiss|push past|push through|override|suppress|not listen to) (my (body|physical sensations?|gut|instincts?|physical feelings?))))`),
		regexp.MustCompile(`(?i)((it'?s (just|only) (physical|in my body|somatic|a (physical|body) reaction).{0,20}(it (doesn'?t|shouldn'?t) (mean|matter|count|affect|influence) (anything|my decision|my thinking|the answer))))`),
		regexp.MustCompile(`(?i)((I (try to|usually|always|tend to) (ignore|dismiss|override|disregard|not pay attention to) (my (body|physical|gut|somatic) (signals?|reactions?|sensations?|responses?|feelings?|input))))`),
	},
}

type InteroceptionDetector struct{}

func NewInteroceptionDetector() *InteroceptionDetector { return &InteroceptionDetector{} }

func (d *InteroceptionDetector) Scan(messages []map[string]string) *InteroceptiveScan {
	text := extractUserText(messages)
	scan := &InteroceptiveScan{}
	for stype, patterns := range interoceptivePatterns {
		for _, re := range patterns {
			if m := re.FindString(text); m != "" {
				scan.Signals = append(scan.Signals, InteroceptiveSignal{SignalType: stype, Excerpt: m, Confidence: 0.80})
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

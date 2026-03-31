package socratic

import (
	"regexp"
	"strings"
)

var socraticPatterns = map[SocraticSignalType][]*regexp.Regexp{
	PseudoCertainty: {
		regexp.MustCompile(`(?i)((obviously|clearly|everyone knows?|it'?s (obvious|clear|common sense|self.evident)|of course|it goes without saying).{0,40}(that|,))`),
		regexp.MustCompile(`(?i)((this is (just|simply|obviously|clearly|undeniably|indisputably) (true|the case|how it is|a fact|the way things are)))`),
		regexp.MustCompile(`(?i)((there'?s (no (doubt|question|debate|argument|denying)|nothing to (discuss|argue|debate)).{0,20}(that|about)))`),
	},
	UnexaminedAssumption: {
		regexp.MustCompile(`(?i)((assuming (that|this is|everything|it'?s).{0,30}(we|I|you|one) (should|can|could|must|have to|ought to)))`),
		regexp.MustCompile(`(?i)((given (that|the fact that).{0,40}(it follows?|we (must|should|can|ought)|the (answer|conclusion|result|solution) (is|must be|has to be))))`),
		regexp.MustCompile(`(?i)((we (all|both|everyone|just) (know|understand|agree|accept|assume) (that|this)).{0,30}(so|therefore|which means?))`),
	},
	BeggingTheQuestion: {
		regexp.MustCompile(`(?i)((it'?s (wrong|bad|evil|immoral|harmful|dangerous|good|right|correct|the truth) because (it'?s (wrong|bad|evil|immoral|harmful|dangerous|good|right|correct|the truth))))`),
		regexp.MustCompile(`(?i)((the (reason|proof|evidence) (is|that).{0,30}(is (because|that|the fact that).{0,30}(which proves?|which shows?|which means?|confirming|demonstrating) (that|it))))`),
		regexp.MustCompile(`(?i)((X is (true|correct|right|the case).{0,20}because X (is true|is correct|is right|is the case|says so|tells us so)))`),
	},
	FalseDefinition: {
		regexp.MustCompile(`(?i)((by definition.{0,20}(X|that|this|it|they|he|she).{0,20}(is|are|must be|has to be|can only be) (a|an|the|[a-z]+)))`),
		regexp.MustCompile(`(?i)((what (X|that|this|it|they|success|freedom|love|justice|truth|happiness) (really|truly|actually|fundamentally) (means?|is).{0,30}(is|means?|requires?|demands?)))`),
		regexp.MustCompile(`(?i)((true (X|success|freedom|love|justice|truth|happiness|strength|loyalty|friendship).{0,20}(means?|requires?|demands?|is defined as|can only be)))`),
	},
}

type SocraticDetector struct{}

func NewSocraticDetector() *SocraticDetector { return &SocraticDetector{} }

func (d *SocraticDetector) Scan(messages []map[string]string) *SocraticScan {
	text := extractUserText(messages)
	scan := &SocraticScan{}
	for stype, patterns := range socraticPatterns {
		for _, re := range patterns {
			if m := re.FindString(text); m != "" {
				scan.Signals = append(scan.Signals, SocraticSignal{SignalType: stype, Excerpt: m, Confidence: 0.80})
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

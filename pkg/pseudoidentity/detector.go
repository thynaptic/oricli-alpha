package pseudoidentity

import (
	"regexp"
	"strings"
)

var identityPatterns = map[IdentityAttributionType][]*regexp.Regexp{
	CultInstalledBelief: {
		regexp.MustCompile(`(?i)((I was (taught|raised|told|trained) to believe|they (taught|told|made) me (to believe|that)).{0,50}(wrong|bad|sinful|dangerous|forbidden|evil))`),
		regexp.MustCompile(`(?i)((the group|they|the church|the org(anization)?|the community) (said|told|taught) (me |us )?(that|to).{0,40}(I (now|realize|know|see|think)|but I))`),
		regexp.MustCompile(`(?i)((beliefs?|values?|rules?|fears?).{0,20}(were (installed|given|forced|drilled) (into|on) me|came from (them|the group|outside|not me)))`),
		regexp.MustCompile(`(?i)((I'?m not sure (if|whether) (this belief|this fear|this value|that rule) is (mine|my own|actually me) or (theirs|from them|from the group)))`),
	},
	AuthenticSelfEmergence: {
		regexp.MustCompile(`(?i)((I'?m (starting to|beginning to|trying to) (figure out|understand|discover|find) who I (really |actually |truly )?(am|was|want to be)))`),
		regexp.MustCompile(`(?i)((what (I|me) (actually|really|truly) (want|believe|value|feel|think) (vs\.|versus|compared to|apart from) (what|what they|what I was)))`),
		regexp.MustCompile(`(?i)((my (own|real|true|authentic) (values?|beliefs?|identity|self|voice|thoughts?) (vs\.|are|were|feel) (different|separate|distinct|buried|suppressed)))`),
	},
	IdentityConfusion: {
		regexp.MustCompile(`(?i)(I (don'?t know|have no idea|can'?t tell|can'?t figure out) who I (am|really am|actually am|was meant to be))`),
		regexp.MustCompile(`(?i)((I (don'?t know|never knew|was never allowed to know) what I (actually |really |truly )?(want|believe|value|feel|like|enjoy)))`),
		regexp.MustCompile(`(?i)((everything I (thought I was|believed about myself|knew about myself|thought I wanted).{0,30}(came from them|was taught|was installed|wasn'?t really me)))`),
	},
	FearAsControl: {
		regexp.MustCompile(`(?i)((I was (afraid|scared|terrified) (to|of).{0,40}(because (of|they said|the rules?|it was (wrong|sinful|forbidden|dangerous)))))`),
		regexp.MustCompile(`(?i)((the fear (of|that).{0,40}(was (put there|installed|drilled|taught)|came from (them|the group|outside))))`),
		regexp.MustCompile(`(?i)((I (only|just) (did|believed|followed|obeyed).{0,30}(out of fear|because I was scared|to survive|to be accepted|to stay safe)))`),
	},
}

// PseudoIdentityDetector scans for identity attribution confusion signals.
type PseudoIdentityDetector struct{}

func NewPseudoIdentityDetector() *PseudoIdentityDetector { return &PseudoIdentityDetector{} }

func (d *PseudoIdentityDetector) Scan(messages []map[string]string) *IdentityScan {
	text := extractUserText(messages)
	scan := &IdentityScan{}

	for atype, patterns := range identityPatterns {
		for _, re := range patterns {
			if m := re.FindString(text); m != "" {
				scan.Signals = append(scan.Signals, IdentitySignal{
					AttributionType: atype,
					Excerpt:         m,
					Confidence:      0.80,
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

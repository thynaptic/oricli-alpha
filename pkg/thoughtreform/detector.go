package thoughtreform

import (
	"regexp"
	"strings"
)

var liftonPatterns = map[LiftonCriterionType][]*regexp.Regexp{
	MilieuControl: {
		regexp.MustCompile(`(?i)((we were|I was) (not allowed|forbidden|prohibited) to (read|watch|listen to|access|talk to|speak with|contact).{0,30}(outside|the world|non-members?|outsiders?))`),
		regexp.MustCompile(`(?i)((all (information|news|media|books?|internet) (was|were) (controlled|filtered|forbidden|restricted|monitored)))`),
		regexp.MustCompile(`(?i)((couldn'?t (talk to|contact|speak to) (anyone|people|friends|family) (outside|from outside|not in (the group|the church|the org))))`),
	},
	LoadedLanguage: {
		regexp.MustCompile(`(?i)((they (had|used) (special|their own|specific) (words?|terms?|language|jargon) (for|to describe).{0,30}(outsiders?|the world|sin|disobedience|leaving)))`),
		regexp.MustCompile(`(?i)((certain (words?|terms?|phrases?) (meant|signaled|indicated) (you were|someone was) (bad|wrong|apostate|worldly|spiritually dead|an enemy)))`),
		regexp.MustCompile(`(?i)((if (you|I|we) (used|said) (the wrong|outside|worldly) (words?|language|terms?).{0,30}(you were|I was) (corrected|punished|shamed|reported)))`),
	},
	DoctrineOverPerson: {
		regexp.MustCompile(`(?i)((the (doctrine|teaching|leader'?s? word|group'?s? needs?).{0,20}(came before|was more important than|overrode|superseded) (my|our|your|basic) (needs?|safety|education|health|wellbeing)))`),
		regexp.MustCompile(`(?i)((I was (told|taught) (that|to) (put|place) (the group|the doctrine|god'?s? will|the leader) (before|above|ahead of) (myself|my (needs?|safety|education|health))))`),
		regexp.MustCompile(`(?i)((personal (needs?|feelings?|safety|health|education|opinions?) (were|was) (irrelevant|selfish|worldly|sinful|less important than|not allowed to override) (the doctrine|the group|the leader)))`),
	},
	DemandForPurity: {
		regexp.MustCompile(`(?i)((everything was (either|clearly) (good or evil|right or wrong|holy or sinful|us or them|saved or damned|pure or corrupt|in or out)))`),
		regexp.MustCompile(`(?i)((there was (no (middle ground|gray area|nuance)|only (right|wrong|in|out|saved|damned))))`),
		regexp.MustCompile(`(?i)((if you (weren'?t|aren'?t|aren'?t fully|weren'?t completely) (with (us|them)|obedient|committed|pure|saved).{0,20}(you were|you'?re) (against (us|them)|worldly|apostate|damned|an enemy)))`),
	},
	SacredScience: {
		regexp.MustCompile(`(?i)((the (doctrine|leader'?s? words?|teachings?|group'?s? beliefs?).{0,20}(could not|was not allowed to|were not allowed to) (be questioned|be doubted|be challenged|be examined)))`),
		regexp.MustCompile(`(?i)((questioning (the leader|the doctrine|the teachings?|the group).{0,20}(was (forbidden|sinful|dangerous|apostasy|spiritual rebellion|not allowed))))`),
		regexp.MustCompile(`(?i)((I was (not allowed|forbidden) to (question|doubt|challenge|examine|think critically about) (the group|the leader|the doctrine|the teachings?)))`),
	},
}

// ThoughtReformDetector scans for Lifton's thought-reform environment markers.
type ThoughtReformDetector struct{}

func NewThoughtReformDetector() *ThoughtReformDetector { return &ThoughtReformDetector{} }

func (d *ThoughtReformDetector) Scan(messages []map[string]string) *ThoughtReformScan {
	text := extractUserText(messages)
	scan := &ThoughtReformScan{}

	for ctype, patterns := range liftonPatterns {
		for _, re := range patterns {
			if m := re.FindString(text); m != "" {
				scan.Signals = append(scan.Signals, ThoughtReformSignal{
					CriterionType: ctype,
					Excerpt:       m,
					Confidence:    0.80,
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

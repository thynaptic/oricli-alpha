package dmn

import (
	"regexp"
	"strings"
)

var dmnPatterns = map[DMNSignalType][]*regexp.Regexp{
	SelfReferentialLoop: {
		regexp.MustCompile(`(?i)((I (keep|can'?t stop) (thinking|going over|replaying|analyzing|examining) (about |over )?(myself|my (life|choices|mistakes|past|failures|decisions|flaws|inadequacies))))`),
		regexp.MustCompile(`(?i)((everything (comes|goes|leads) back to (me|my (failures?|flaws?|inadequacies?|mistakes?|past|choices?|decisions?))))`),
		regexp.MustCompile(`(?i)((my (thoughts?|mind) (keeps?|won'?t stop) (circling|returning|going back|fixating) (on|to) (me|myself|my (worth|value|past|failures?|choices?))))`),
	},
	MindWandering: {
		regexp.MustCompile(`(?i)((my (mind|attention|focus|thoughts?) (keeps? (wandering|drifting|going|jumping|going off)|won'?t (stay|settle|focus|concentrate)|is (scattered|everywhere|all over the place|jumping around))))`),
		regexp.MustCompile(`(?i)((I (can'?t|couldn'?t) (focus|concentrate|stay on (topic|task|track|one thing)|keep my (mind|attention|thoughts?) (on|with) (it|the task|what I'?m doing|the present))))`),
		regexp.MustCompile(`(?i)((I (started|was|tried) (to|thinking about).{0,30}(and then|but then|and my mind|and I) (drifted|wandered|went|ended up|jumped|got distracted)))`),
	},
	DMNOveractivation: {
		regexp.MustCompile(`(?i)((I (keep|can'?t stop) (thinking about|ruminating on|worrying about|obsessing over) (what (others? think|they think|people think|everyone thinks) (of|about) (me|I))))`),
		regexp.MustCompile(`(?i)((my (mind|thoughts?|brain) (won'?t|can'?t) (stop|quiet|rest|settle|shut off).{0,30}(past|future|what ifs?|what could have|what might|if only|I should have)))`),
		regexp.MustCompile(`(?i)((replaying|rehashing|going over and over|revisiting|re-living).{0,30}(the past|what happened|past mistakes|past failures|what I (did|said|didn'?t do|should have done)))`),
	},
	TaskNetworkDisengagement: {
		regexp.MustCompile(`(?i)((I (can'?t|couldn'?t) (start|begin|do|work on|engage with|focus on|get to) (the|any|a) (task|work|thing|project|problem|next step|concrete)).{0,30}(even though|despite|I know I should))`),
		regexp.MustCompile(`(?i)((I know (what|I need to|I should|the next step is).{0,30}(but (I can'?t|I won'?t|my mind|I keep|something|I don'?t) (start|begin|do|engage|focus|get to it|make myself))))`),
		regexp.MustCompile(`(?i)((the (task|work|problem|thing|concrete step|action|next move).{0,20}(feels? (impossible|overwhelming|unreachable|too far away|disconnected|out of reach|abstract))).{0,30}(to (start|begin|do|engage with|focus on)))`),
	},
}

type DMNDetector struct{}

func NewDMNDetector() *DMNDetector { return &DMNDetector{} }

func (d *DMNDetector) Scan(messages []map[string]string) *DMNScan {
	text := extractUserText(messages)
	scan := &DMNScan{}
	for stype, patterns := range dmnPatterns {
		for _, re := range patterns {
			if m := re.FindString(text); m != "" {
				scan.Signals = append(scan.Signals, DMNSignal{SignalType: stype, Excerpt: m, Confidence: 0.80})
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

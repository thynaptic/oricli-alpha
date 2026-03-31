package logotherapy

import (
	"regexp"
	"strings"
)

var meaningPatterns = map[MeaningSignalType][]*regexp.Regexp{
	ExistentialVacuum: {
		regexp.MustCompile(`(?i)(life (has|feels?|seems?) (no|without|devoid of) (meaning|purpose|point|value|worth))`),
		regexp.MustCompile(`(?i)((what'?s the (meaning|purpose|point) of (life|existence|any of this|it all)))`),
		regexp.MustCompile(`(?i)((existence (feels?|seems?|is) (empty|hollow|meaningless|purposeless|void|pointless)))`),
		regexp.MustCompile(`(?i)((I (can'?t|don'?t) (see|find|feel) (any )?(meaning|purpose|reason) (in|for|to) (being alive|living|existence|any of this)))`),
	},
	MeaningCollapse: {
		regexp.MustCompile(`(?i)((I (used to|once) (believe in|have|feel|know) (something|a purpose|meaning|a reason).{0,30}(but|not anymore|gone|lost|no longer)))`),
		regexp.MustCompile(`(?i)((I'?ve (lost|lost all|lost my) (sense of|feeling of|belief in|connection to) (purpose|meaning|direction|reason|faith)))`),
		regexp.MustCompile(`(?i)((the (meaning|purpose|reason|thing) (that|which) (kept me going|gave me purpose|mattered).{0,20}(is gone|collapsed|disappeared|doesn'?t (exist|matter) anymore)))`),
	},
	FrustrationOfMeaning: {
		regexp.MustCompile(`(?i)((no matter (what|how hard|how much) (I (do|try|search|look)).{0,30}(feels? (meaningless|pointless|empty|hollow|worthless))))`),
		regexp.MustCompile(`(?i)((I (can'?t|cannot|don'?t know how to) (find|create|discover|make) (any )?(meaning|purpose|reason|direction) (in|from|out of) (this|my life|what happened|the suffering)))`),
		regexp.MustCompile(`(?i)((the (suffering|pain|loss|situation).{0,20}(feels? (meaningless|pointless|random|purposeless|for nothing|without reason))))`),
	},
	WillToMeaning: {
		regexp.MustCompile(`(?i)((I (need|want|am (looking|searching|trying) to (find|discover|understand)) (a )?(meaning|purpose|reason|point|direction) (for|in|to)))`),
		regexp.MustCompile(`(?i)((what (is|gives|could give) (my )?(life|this|all of this) (meaning|purpose|direction|value|worth)))`),
		regexp.MustCompile(`(?i)((how (do|can|could) (I|someone|a person) (find|create|build|discover) (meaning|purpose|a reason to go on|direction) (when|after|despite)))`),
	},
}

type LogotherapyDetector struct{}

func NewLogotherapyDetector() *LogotherapyDetector { return &LogotherapyDetector{} }

func (d *LogotherapyDetector) Scan(messages []map[string]string) *MeaningScan {
	text := extractUserText(messages)
	scan := &MeaningScan{}
	for stype, patterns := range meaningPatterns {
		for _, re := range patterns {
			if m := re.FindString(text); m != "" {
				scan.Signals = append(scan.Signals, MeaningSignal{SignalType: stype, Excerpt: m, Confidence: 0.80})
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

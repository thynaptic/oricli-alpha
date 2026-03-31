package apathy

import (
	"regexp"
	"strings"
)

var apathyPatterns = map[ApathySignalType][]*regexp.Regexp{
	Affectlessness: {
		regexp.MustCompile(`(?i)(I (don'?t feel|can'?t feel|stopped feeling|feel (nothing|empty|numb|flat|hollow|blank)) (anything|anymore|at all|inside))`),
		regexp.MustCompile(`(?i)((nothing (makes|made) me (feel|care|react|respond)|I (can'?t|don'?t|stopped) (care|caring|feel|feeling) (anymore|at all|about anything)))`),
		regexp.MustCompile(`(?i)((completely (numb|empty|flat|hollow|detached|shut (down|off)|checked out)|totally (numb|empty|flat|hollow|disconnected)))`),
	},
	AgencyCollapse: {
		regexp.MustCompile(`(?i)(I (don'?t know|have no idea|can'?t figure out) what I (want|need|should do|actually want|like|value|care about))`),
		regexp.MustCompile(`(?i)((I (can'?t|couldn'?t) (make|make a) (decision|choice|decision for myself)|incapable of (deciding|choosing|making decisions)))`),
		regexp.MustCompile(`(?i)((I (have|had) (no|lost all|completely lost) (motivation|drive|direction|will|desire|initiative|ability to choose)))`),
	},
	DependencyTransfer: {
		regexp.MustCompile(`(?i)((I (need|needed) (someone|others?|them|you) to (tell me|decide for me|direct me|guide me|tell me what to do|make decisions for me)))`),
		regexp.MustCompile(`(?i)((I (just|only|completely) (do|did|follow(ed)?|go(es)?) (what|whatever) (others?|they|someone|everyone else|people) (tell|told|say|said|decide|decided)))`),
		regexp.MustCompile(`(?i)((I (can'?t|couldn'?t) (function|operate|get through|manage|do anything) (without|unless|until) (someone|others?|they|a person) (tells?|directs?|guides?|decides?)))`),
	},
	MotivationVacuum: {
		regexp.MustCompile(`(?i)((nothing (matters|is worth it|feels worth it|seems worth (it|doing)|is meaningful|makes a difference anymore)))`),
		regexp.MustCompile(`(?i)((I (have|had) (no|absolutely no|zero|lost all) (reason|purpose|direction|point|goal|meaning|drive|motivation) (to|for|in)))`),
		regexp.MustCompile(`(?i)((what'?s the (point|use) (of|in) (anything|trying|doing anything|going on|moving forward|caring about anything)))`),
		regexp.MustCompile(`(?i)((I (just|only) (go through|exist|survive|endure|get through) (the motions|each day|daily life|the day) (without|with no|feeling nothing)))`),
	},
}

// ApathySyndromeDetector scans for apathy syndrome signals.
type ApathySyndromeDetector struct{}

func NewApathySyndromeDetector() *ApathySyndromeDetector { return &ApathySyndromeDetector{} }

func (d *ApathySyndromeDetector) Scan(messages []map[string]string) *ApathyScan {
	text := extractUserText(messages)
	scan := &ApathyScan{}

	for stype, patterns := range apathyPatterns {
		for _, re := range patterns {
			if m := re.FindString(text); m != "" {
				scan.Signals = append(scan.Signals, ApathySignal{
					SignalType: stype,
					Excerpt:    m,
					Confidence: 0.80,
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

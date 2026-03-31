package mbct

import (
	"regexp"
	"strings"
)

var mbctPatterns = map[SpiralWarningType][]*regexp.Regexp{
	ThoughtFusion: {
		// "I am depressed/broken/worthless" — identity fusion with mental state
		regexp.MustCompile(`(?i)(I (am|'m) (depressed|broken|worthless|a failure|hopeless|useless|damaged|pathetic|nothing|empty|lost))`),
		regexp.MustCompile(`(?i)(I (am|'m) (always|just|only|simply) (like this|this way|this person|this broken))`),
		regexp.MustCompile(`(?i)(this (is|'s) (who|what) I (am|'m)( —| ;|,| and)?.{0,20}(broken|hopeless|worthless|damaged|a failure))`),
	},
	EarlyRumination: {
		// catching the first loop: "I keep thinking about", "I can't stop thinking about"
		regexp.MustCompile(`(?i)(I (can'?t stop|keep|just keep) (thinking|replaying|going over|dwelling on|obsessing over))`),
		regexp.MustCompile(`(?i)((it|that|the thought|the moment) (keeps (coming back|replaying|returning)|won'?t (leave|go away|stop)))`),
		regexp.MustCompile(`(?i)(my (mind|brain|head) (keeps (going back|returning|replaying|circling)|won'?t (let it go|stop|rest)))`),
	},
	SelfCriticalCascade: {
		// small error → global self-attack: "I made a mistake → I'm a disaster/failure/worthless"
		regexp.MustCompile(`(?i)((I (made|said|did).{0,30}(mistake|error|wrong|bad).{0,20}(which means|so|because|proves?).{0,30}(I'?m|I am) (a failure|worthless|terrible|awful|broken|disaster|pathetic)))`),
		regexp.MustCompile(`(?i)((because I (forgot|messed up|failed|couldn'?t).{0,30})(I'?m|I am|that means I'?m) (a failure|worthless|useless|terrible|hopeless))`),
		regexp.MustCompile(`(?i)(one (mistake|bad day|failure|thing).{0,30}(proves?|shows?|means?|confirms?).{0,20}(I'?m|I am) (a failure|worthless|broken|terrible))`),
	},
	MoodAsFactError: {
		// treating feeling as objective reality: "I feel hopeless therefore things are hopeless"
		regexp.MustCompile(`(?i)(I (feel|felt).{0,20}(so|therefore|which means|and so|that means) (I (am|'m|must be|have to be)))`),
		regexp.MustCompile(`(?i)((which means|that means|therefore|so).{0,40}(things?|it|everything).{0,20}(are|is) (hopeless|true|real|bad|awful|terrible))`),
		regexp.MustCompile(`(?i)((if I feel (this way|like this|this bad|this broken)).{0,30}(must be|has to be|is definitely) (true|real|the truth|who I am))`),
		regexp.MustCompile(`(?i)((feel(ing)? (this (bad|hopeless|empty|broken)).{0,20}(proves?|means|confirms?|shows?)))`),
	},
}

// MBCTSpiralDetector scans for MBCT early-warning depressive spiral signals.
type MBCTSpiralDetector struct{}

func NewMBCTSpiralDetector() *MBCTSpiralDetector { return &MBCTSpiralDetector{} }

func (d *MBCTSpiralDetector) Scan(messages []map[string]string) *MBCTScan {
	text := extractUserText(messages)
	scan := &MBCTScan{}

	for wtype, patterns := range mbctPatterns {
		for _, re := range patterns {
			if m := re.FindString(text); m != "" {
				scan.Signals = append(scan.Signals, MBCTSignal{
					WarningType: wtype,
					Excerpt:     m,
					Confidence:  0.80,
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

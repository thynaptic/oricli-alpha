package ipsrt

import (
	"regexp"
	"strings"
)

var rhythmPatterns = map[RhythmDisruptionType][]*regexp.Regexp{
	SleepDisruption: {
		regexp.MustCompile(`(?i)(haven'?t (been )?(sleep\w*|slept)|can'?t sleep|not sleeping|up (all night|until \d)|woke up (at \d|every|multiple)|sleep (is off|has been off|pattern))`),
		regexp.MustCompile(`(?i)(staying up (late|until)|pulling (an? )?(all[ -]nighter|late night)|sleep schedule)`),
		regexp.MustCompile(`(?i)(exhausted (but can'?t|and can'?t)|insomnia|no sleep|barely slept|slept (for )?\d (hour|hr))`),
	},
	RoutineBreak: {
		regexp.MustCompile(`(?i)(routine\b.{0,20}(fell apart|is (off|broken|gone|a mess)|disrupted)|off (my|a) routine|no routine|lost (my )?(routine|structure))`),
		regexp.MustCompile(`(?i)(haven'?t (been able to|had time to) (do|stick to|maintain)|everything (is|feels) (chaotic|off|unstructured))`),
		regexp.MustCompile(`(?i)(schedule (is (gone|off|wrecked|destroyed)|fell apart|all over)|can'?t (keep|maintain) a schedule)`),
	},
	MealDisruption: {
		regexp.MustCompile(`(?i)(haven'?t (eaten|had (a )?(meal|food|lunch|dinner|breakfast))|(forgot|forgetting) to eat|skip(p(ed|ing))? (meals|breakfast|lunch|dinner))`),
		regexp.MustCompile(`(?i)(not eating (right|well|properly|regularly)|eating (at odd|random|weird) (times|hours)|meal (is|has been) (off|irregular))`),
	},
	SocialIsolation: {
		regexp.MustCompile(`(?i)(haven'?t (seen|talked to|spoken to|contacted) (anyone|anybody|people|friends|family) (in |for )?(days|weeks|a while))`),
		regexp.MustCompile(`(?i)(isolat(ed|ing) (myself|from)|cut(ting)? (myself |people )?off|avoiding (everyone|people|contact))`),
		regexp.MustCompile(`(?i)(no (social )?contact|haven'?t left (the house|home|my (room|apartment))|alone (all day|all week|for days))`),
	},
	ScheduleChaos: {
		regexp.MustCompile(`(?i)(everything (is|feels|seems) (chaotic|out of (control|whack)|unpredictable|unmanageable))`),
		regexp.MustCompile(`(?i)(no (structure|order|consistency)|can'?t (predict|plan|know) (what|when|how)|nothing is (consistent|predictable|stable))`),
		regexp.MustCompile(`(?i)(flying (by the seat|blind)|winging (it|everything)|making it up (as I go|day by day))`),
		regexp.MustCompile(`(?i)(schedule.{0,20}(chaos|chaotic|a mess|all over the place|is gone|is off))`),
	},
}

// RhythmDisruptionDetector scans for IPSRT social-rhythm disruption signals.
type RhythmDisruptionDetector struct{}

func NewRhythmDisruptionDetector() *RhythmDisruptionDetector {
	return &RhythmDisruptionDetector{}
}

func (d *RhythmDisruptionDetector) Scan(messages []map[string]string) *RhythmScan {
	text := extractUserText(messages)
	scan := &RhythmScan{}

	for dtype, patterns := range rhythmPatterns {
		for _, re := range patterns {
			if m := re.FindString(text); m != "" {
				scan.Signals = append(scan.Signals, RhythmSignal{
					DisruptionType: dtype,
					Excerpt:        m,
					Confidence:     0.80,
				})
				break // one hit per type is enough
			}
		}
	}

	scan.Disrupted = len(scan.Signals) > 0
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

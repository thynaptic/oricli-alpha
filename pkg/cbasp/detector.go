package cbasp

import (
	"regexp"
	"strings"
)

var cbaspPatterns = map[DisconnectionType][]*regexp.Regexp{
	ActionConsequenceBlindness: {
		regexp.MustCompile(`(?i)(nothing (I (do|say|try)|we do) (matter|matters|ever matters|makes a difference|changes anything))`),
		regexp.MustCompile(`(?i)(no matter (what I (do|say|try)|how hard I try).{0,30}(nothing|it doesn'?t|never))`),
		regexp.MustCompile(`(?i)(my (actions|efforts|words|behaviour|behavior).{0,20}(don'?t matter|have no effect|make no difference|don'?t change anything))`),
		regexp.MustCompile(`(?i)(doesn'?t matter (what|how) I (do|say|act|behave))`),
	},
	ImpactDenial: {
		regexp.MustCompile(`(?i)(I (didn'?t|don'?t) (affect|impact|influence) (them|him|her|anyone|people))`),
		regexp.MustCompile(`(?i)((they|he|she|people) (don'?t|won'?t|didn'?t) (care|notice|respond|react) (what|how|when|if) I)`),
		regexp.MustCompile(`(?i)(my (behaviour|behavior|words|actions|reactions).{0,20}(had no|have no|makes no) (effect|impact|difference) on)`),
		regexp.MustCompile(`(?i)(it (doesn'?t|didn'?t) matter (to them|to anyone|what I did|what I said))`),
	},
	FutilityBelief: {
		regexp.MustCompile(`(?i)(what'?s the (point|use) (of (trying|doing|saying|acting)|in trying))`),
		regexp.MustCompile(`(?i)(there'?s (no point|no use|no reason) (in|to) (trying|doing|saying|acting|reaching out))`),
		regexp.MustCompile(`(?i)(trying (is|was) (useless|pointless|hopeless|futile|a waste))`),
		regexp.MustCompile(`(?i)(I (give up|stopped trying|don'?t bother).{0,20}(because|since|it'?s|nothing) (nothing|never|pointless|useless))`),
	},
	SocialDetachment: {
		regexp.MustCompile(`(?i)(people (don'?t|never|won'?t) (respond|react|engage|connect) (to|with) me)`),
		regexp.MustCompile(`(?i)((I reach out|I try to connect|I talk to people).{0,40}(nothing|no response|no reaction|ignored|like I'?m not there))`),
		regexp.MustCompile(`(?i)(as if (I'?m|I am) (invisible|not there|not real|not talking|not speaking))`),
		regexp.MustCompile(`(?i)((my|any) (words|actions|presence).{0,20}(don'?t register|go unnoticed|are ignored|have no effect on anyone))`),
	},
}

// CBASPDisconnectionDetector scans for CBASP interpersonal impact-blindness signals.
type CBASPDisconnectionDetector struct{}

func NewCBASPDisconnectionDetector() *CBASPDisconnectionDetector {
	return &CBASPDisconnectionDetector{}
}

func (d *CBASPDisconnectionDetector) Scan(messages []map[string]string) *CBASPScan {
	text := extractUserText(messages)
	scan := &CBASPScan{}

	for dtype, patterns := range cbaspPatterns {
		for _, re := range patterns {
			if m := re.FindString(text); m != "" {
				scan.Signals = append(scan.Signals, CBASPSignal{
					DisconnectionType: dtype,
					Excerpt:           m,
					Confidence:        0.80,
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

package iut

import (
	"regexp"
	"strings"
)

var iuPatterns = map[UncertaintyAversion][]*regexp.Regexp{
	UncertaintyThreat: {
		regexp.MustCompile(`(?i)(uncertainty (is|feels|seems) (terrifying|scary|unbearable|threatening|dangerous|paralyzing))`),
		regexp.MustCompile(`(?i)(can'?t (stand|handle|deal with|tolerate) (not knowing|the uncertainty|uncertainty|not being sure))`),
		regexp.MustCompile(`(?i)(the unknown (is|feels|scares|terrifies|paralyzes)|(not knowing) (is|drives me|kills me|terrifies))`),
	},
	NeedForCertainty: {
		regexp.MustCompile(`(?i)(need(s|ed)? to (know|be sure|be certain|have certainty|confirm|verify) (before|first|right now))`),
		regexp.MustCompile(`(?i)(can'?t (do|decide|act|move|start) (until|unless|before) (I|we) (know|find out|confirm|are sure))`),
		regexp.MustCompile(`(?i)(have to (know|be 100%|be sure|be certain)|must (know|be certain|find out) (first|now|before))`),
	},
	UnfairnessFraming: {
		regexp.MustCompile(`(?i)((it'?s? |that'?s? )?(not fair|unfair) (that|to|for|how) .{0,30}(don'?t know|can'?t know|uncertain|not sure))`),
		regexp.MustCompile(`(?i)(why (can'?t|don'?t|won'?t) (I|we|anyone) (just )?(know|find out|be told|be sure))`),
		regexp.MustCompile(`(?i)(should(n'?t)? (have to|need to) (deal with|live with|accept) (not knowing|uncertainty|the unknown))`),
	},
	WhatIfSpiral: {
		regexp.MustCompile(`(?i)(what if.{0,50}what if)`), // two what-ifs = spiral
		regexp.MustCompile(`(?i)(what if .{0,60}(and then|which means|so then|meaning|leading to))`),
		regexp.MustCompile(`(?i)(but (then |again )?(what if|what about|suppose|maybe).{0,30}(what if|what about|suppose))`),
	},
}

// UncertaintyIntoleranceDetector scans for IU-therapy signals.
type UncertaintyIntoleranceDetector struct{}

func NewUncertaintyIntoleranceDetector() *UncertaintyIntoleranceDetector {
	return &UncertaintyIntoleranceDetector{}
}

func (d *UncertaintyIntoleranceDetector) Scan(messages []map[string]string) *IUScan {
	text := extractUserText(messages)
	scan := &IUScan{}

	for atype, patterns := range iuPatterns {
		for _, re := range patterns {
			if m := re.FindString(text); m != "" {
				scan.Signals = append(scan.Signals, IUSignal{
					AversType:  atype,
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

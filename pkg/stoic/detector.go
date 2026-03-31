package stoic

import (
	"regexp"
	"strings"
)

var stoicPatterns = map[StoicSignalType][]*regexp.Regexp{
	ControlConflation: {
		regexp.MustCompile(`(?i)((I (can'?t|cannot|don'?t) control (what|how|whether|if).{0,30}(and it'?s (killing|destroying|crushing|tearing) me|and I (can'?t|don'?t) (cope|handle|deal with|accept) it)))`),
		regexp.MustCompile(`(?i)((I (need|have to|must) (control|change|fix|make) (what|how|whether|if|the way).{0,30}(happens?|reacts?|feels?|thinks?|does?)))`),
		regexp.MustCompile(`(?i)((if (only|I could) (control|change|make|force) (them|the outcome|what happens?|the situation|others?).{0,20}(everything would be|things would be|I would be) (fine|okay|better|fixed)))`),
	},
	ExternalAttachment: {
		regexp.MustCompile(`(?i)((my (happiness|peace|wellbeing|sense of okay|ability to function).{0,20}(depends on|is tied to|requires|is contingent on) (them|what they|the outcome|whether|if they)))`),
		regexp.MustCompile(`(?i)((I (can'?t|won'?t|don'?t think I can) (be (okay|fine|at peace|happy|alright)|function|move on|feel better).{0,20}(unless|until|without) (they|the situation|it|things)))`),
		regexp.MustCompile(`(?i)((everything (was|is|went|fell) (fine|good|okay|apart|wrong|to pieces).{0,20}(until|because|when) (they|he|she|the situation|it) (did|changed|left|happened|said)))`),
	},
	ObstacleAvoidance: {
		regexp.MustCompile(`(?i)((the (obstacle|problem|barrier|difficulty|setback|challenge).{0,20}(means? I (can'?t|should|have to|need to) (give up|stop|quit|abandon|accept defeat))))`),
		regexp.MustCompile(`(?i)((this (problem|obstacle|challenge|difficulty|setback).{0,20}(is (in|blocking|preventing) (my|the) (way|path|progress|goal)).{0,20}(so I (can'?t|won'?t|shouldn'?t) (continue|proceed|go on|keep going))))`),
		regexp.MustCompile(`(?i)((I (tried|attempted|worked (hard|so hard)).{0,30}(but the (obstacle|problem|barrier|resistance|pushback)).{0,20}(made me|forced me|caused me to) (give up|stop|quit|step back|reconsider everything)))`),
	},
	VirtueNeglect: {
		regexp.MustCompile(`(?i)((how I (respond|react|act|behave|feel) (is|was) (determined|decided|caused|dictated) by (them|what happened|the situation|external|circumstances|what they did)))`),
		regexp.MustCompile(`(?i)((I (had|have|had) no (choice|option|say|control) (but to|in how I|over how I) (react|respond|feel|act|behave).{0,20}(because of|given|when) (them|what|how|the situation)))`),
		regexp.MustCompile(`(?i)((anyone (would|in my position would|who went through this would) (react|respond|feel|act|behave) (exactly|the same|like this|this way|this badly)))`),
	},
}

type StoicDetector struct{}

func NewStoicDetector() *StoicDetector { return &StoicDetector{} }

func (d *StoicDetector) Scan(messages []map[string]string) *StoicScan {
	text := extractUserText(messages)
	scan := &StoicScan{}
	for stype, patterns := range stoicPatterns {
		for _, re := range patterns {
			if m := re.FindString(text); m != "" {
				scan.Signals = append(scan.Signals, StoicSignal{SignalType: stype, Excerpt: m, Confidence: 0.80})
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

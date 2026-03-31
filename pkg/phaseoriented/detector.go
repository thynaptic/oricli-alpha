package phaseoriented

import (
	"regexp"
	"strings"
)

var phasePatterns = map[DissociativeSignalType][]*regexp.Regexp{
	Fragmentation: {
		regexp.MustCompile(`(?i)((a |one )part of me.{0,40}(while|but|and) (another|a different|other) part)`),
		regexp.MustCompile(`(?i)(part(s)? of me (want|feel|know|believe|says?|thinks?).{0,20}(while|but|and))`),
		regexp.MustCompile(`(?i)((the|a) (part|voice|side) (that|inside|of me).{0,30}(says?|tells?|wants?|feels?))`),
		regexp.MustCompile(`(?i)((different parts?|inside parts?|inner parts?|the parts?).{0,20}(of me|inside|disagree|want|feel))`),
	},
	Destabilization: {
		regexp.MustCompile(`(?i)(I('m| am) (spinning out|spiraling|losing it|falling apart|coming apart|not okay|not safe|not here))`),
		regexp.MustCompile(`(?i)(everything (is|feels|seems) (too much|overwhelming|out of control|unsafe|falling apart))`),
		regexp.MustCompile(`(?i)((can'?t|couldn'?t) (get grounded|stay present|stay here|feel (safe|real|okay))|completely (overwhelmed|flooded|destabilized))`),
		regexp.MustCompile(`(?i)((I feel|feeling) (like I'?m (losing|not in) (my (mind|grip|ground)|control|reality)|dissociated|disconnected from (myself|my body|reality)))`),
	},
	GroundingRequest: {
		regexp.MustCompile(`(?i)(I need (to (get grounded|calm down|stabilize|feel safe|come back)|something to (ground|anchor|help) me))`),
		regexp.MustCompile(`(?i)(help me (get grounded|stay here|stay present|feel safe|calm down|stabilize))`),
		regexp.MustCompile(`(?i)((grounding|containment|stabilization|a safe place) (exercise|technique|skill|strategy|practice))`),
		regexp.MustCompile(`(?i)(how (do I|can I|to) (get grounded|stay present|feel safe right now|calm (down|myself)))`),
	},
	TraumaProcessReady: {
		regexp.MustCompile(`(?i)(I('m| am) (ready|stable enough|okay enough|safe enough) (to (talk about|work on|process|look at)|to go into))`),
		regexp.MustCompile(`(?i)((I want|I'?d like|I need) to (process|work through|talk about|look at) (the|that|a) (memory|trauma|event|incident|thing that happened))`),
		regexp.MustCompile(`(?i)((the (memory|trauma|event|thing).{0,20}(I'?ve been|I want) (avoiding|putting off|afraid to (look at|talk about))))`),
	},
}

// PhaseOrientedDetector scans for ISSTD phase signals and infers treatment phase.
type PhaseOrientedDetector struct{}

func NewPhaseOrientedDetector() *PhaseOrientedDetector { return &PhaseOrientedDetector{} }

func (d *PhaseOrientedDetector) Scan(messages []map[string]string) *PhaseScan {
	text := extractUserText(messages)
	scan := &PhaseScan{}

	for stype, patterns := range phasePatterns {
		for _, re := range patterns {
			if m := re.FindString(text); m != "" {
				scan.Signals = append(scan.Signals, PhaseSignal{
					SignalType: stype,
					Excerpt:    m,
					Confidence: 0.80,
				})
				break
			}
		}
	}

	scan.Triggered = len(scan.Signals) > 0
	scan.InferredPhase = inferPhase(scan.Signals)
	return scan
}

// inferPhase maps signal types to treatment phase.
// Safety always overrides — destabilization → Phase 1 regardless of other signals.
func inferPhase(signals []PhaseSignal) TraumaPhase {
	hasDestab, hasGrounding, hasProcessReady, hasFragmentation := false, false, false, false
	for _, s := range signals {
		switch s.SignalType {
		case Destabilization:
			hasDestab = true
		case GroundingRequest:
			hasGrounding = true
		case TraumaProcessReady:
			hasProcessReady = true
		case Fragmentation:
			hasFragmentation = true
		}
	}
	if hasDestab || hasGrounding {
		return PhaseOneStabilization
	}
	if hasProcessReady {
		return PhaseTwoProcessing
	}
	if hasFragmentation {
		return PhaseOneStabilization // fragmentation without stability = still Phase 1
	}
	return PhaseOneStabilization // safe default
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

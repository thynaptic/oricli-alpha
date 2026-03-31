package up

import (
	"regexp"
	"strings"
)

// Antecedent patterns — triggers/situations that precede emotional responses.
var antecedentPatterns = []*regexp.Regexp{
	regexp.MustCompile(`(?i)(when(ever)? (I|it|he|she|they).{0,40}(I feel|I get|it makes me|I become|I start))`),
	regexp.MustCompile(`(?i)(every time.{0,40}(I feel|I get|makes me|I become))`),
	regexp.MustCompile(`(?i)(after .{0,40}(I feel|I get|it makes me|I become|I end up))`),
	regexp.MustCompile(`(?i)(as soon as .{0,40}(I feel|I get|I notice|I start|I become))`),
}

// Response patterns — emotional/physical reactions and avoidance behaviors.
var responsePatterns = []*regexp.Regexp{
	regexp.MustCompile(`(?i)(I (feel|felt|get|got|become|became) (anxious|scared|panicked|overwhelmed|angry|numb|dissociated|frozen|shut down))`),
	regexp.MustCompile(`(?i)((my|the) (heart|chest|throat|stomach).{0,30}(tight(ens)?|races|pounds|drops|knots|sinks))`),
	regexp.MustCompile(`(?i)(I (shut down|freeze|run|flee|hide|avoid|escape|withdraw|check out|dissociate))`),
	regexp.MustCompile(`(?i)(I (can'?t|couldn'?t) (think|breathe|move|function|focus|stop) (straight|clearly|at all|properly))`),
}

// Consequence patterns — what happens after the response (reinforcement / avoidance payoff).
var consequencePatterns = []*regexp.Regexp{
	regexp.MustCompile(`(?i)(and (then|so) (I|it).{0,40}(feel better|calms down|goes away|relief|safe again))`),
	regexp.MustCompile(`(?i)(which (makes|made) (it|things|everything).{0,30}(worse|harder|more intense|spiral))`),
	regexp.MustCompile(`(?i)((so|then) I (avoid|don'?t go|cancel|skip|stay away from).{0,30}(and (it|I) feel))`),
	regexp.MustCompile(`(?i)(the (anxiety|panic|fear|feeling).{0,30}(goes away|fades|disappears|subsides) (when|after|once) I)`),
}

// ARCCycleDetector scans for ARC (Antecedent-Response-Consequence) cycle patterns.
type ARCCycleDetector struct{}

func NewARCCycleDetector() *ARCCycleDetector { return &ARCCycleDetector{} }

func (d *ARCCycleDetector) Scan(messages []map[string]string) *ARCScan {
	text := extractUserText(messages)
	scan := &ARCScan{}

	for _, re := range antecedentPatterns {
		if m := re.FindString(text); m != "" {
			scan.Signals = append(scan.Signals, ARCSignal{Component: AntecedentDetected, Excerpt: m, Confidence: 0.80})
			break
		}
	}
	for _, re := range responsePatterns {
		if m := re.FindString(text); m != "" {
			scan.Signals = append(scan.Signals, ARCSignal{Component: ResponseDetected, Excerpt: m, Confidence: 0.80})
			break
		}
	}
	for _, re := range consequencePatterns {
		if m := re.FindString(text); m != "" {
			scan.Signals = append(scan.Signals, ARCSignal{Component: ConsequenceDetected, Excerpt: m, Confidence: 0.75})
			break
		}
	}

	// Cycle requires at least antecedent + response
	hasA, hasR := false, false
	for _, s := range scan.Signals {
		if s.Component == AntecedentDetected { hasA = true }
		if s.Component == ResponseDetected   { hasR = true }
	}
	scan.HasCycle = hasA && hasR
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

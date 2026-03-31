package statusbias

import (
	"regexp"
	"strings"
)

// High-status signals: authority, expertise, urgency, importance
var highStatusPatterns = []struct {
	re    *regexp.Regexp
	label string
}{
	{regexp.MustCompile(`(?i)\b(i('m| am) a (senior|lead|principal|staff|chief|head|director|vp|cto|ceo|founder|professor|doctor|phd|expert|specialist))\b`), "expert self-identification"},
	{regexp.MustCompile(`(?i)\b(i have (years|decades) of (experience|expertise)|i('ve| have) been (doing|working on) (this|it) for (years|decades))\b`), "experience claim"},
	{regexp.MustCompile(`(?i)\b(this is (critical|urgent|crucial|mission[- ]critical|high[- ]priority|extremely important))\b`), "urgency/importance marker"},
	{regexp.MustCompile(`(?i)\b(i need (the best|the most (thorough|detailed|comprehensive|rigorous))|give me (the full|a complete|an exhaustive))\b`), "thoroughness demand"},
	{regexp.MustCompile(`(?i)\b(i('m| am) working (on|with)|i('m| am) building|i('m| am) developing)\s+(a (large|major|enterprise|production|mission[- ]critical))\b`), "high-stakes project"},
}

// Low-status / dismissal signals: casual, trivial, apologetic framing
var lowStatusPatterns = []struct {
	re    *regexp.Regexp
	label string
}{
	{regexp.MustCompile(`(?i)\b(just a (quick|simple|silly|stupid|dumb) question|probably (stupid|dumb|trivial)|sorry (if this is|for the) (obvious|basic|dumb))\b`), "self-dismissal"},
	{regexp.MustCompile(`(?i)\b(this is (probably|likely) (obvious|trivial|simple|basic|easy)|i('m| am) (just|only) (a (newbie|beginner|junior|student|hobbyist)))\b`), "low-status self-framing"},
	{regexp.MustCompile(`(?i)\b(don't worry (about|if)|just (curious|wondering)|no big deal|just for fun|not important)\b`), "topic minimization"},
	{regexp.MustCompile(`(?i)\b(nevermind|never mind|forget it|don't bother|too complicated)\b`), "abandonment signal"},
}

// StatusSignalExtractor detects authority/expertise/status cues in user messages.
type StatusSignalExtractor struct{}

func NewStatusSignalExtractor() *StatusSignalExtractor {
	return &StatusSignalExtractor{}
}

func (e *StatusSignalExtractor) Extract(userMsg string) StatusSignal {
	expertiseCues := []string{}
	dismissalCues := []string{}

	highScore := 0.0
	for _, p := range highStatusPatterns {
		if p.re.MatchString(userMsg) {
			highScore += 1.0 / float64(len(highStatusPatterns))
			expertiseCues = append(expertiseCues, p.label)
		}
	}

	lowScore := 0.0
	for _, p := range lowStatusPatterns {
		if p.re.MatchString(userMsg) {
			lowScore += 1.0 / float64(len(lowStatusPatterns))
			dismissalCues = append(dismissalCues, p.label)
		}
	}

	// Net score: high signals push up, low signals push down
	score := highScore - lowScore*0.5
	if score < 0 {
		score = 0
	}
	if score > 1.0 {
		score = 1.0
	}

	tier := StatusNone
	switch {
	case score >= 0.5:
		tier = StatusHigh
	case score >= 0.25:
		tier = StatusMedium
	case len(dismissalCues) > 0:
		tier = StatusLow
	}

	importance := scoreImportance(userMsg)

	return StatusSignal{
		Tier:              tier,
		Score:             score,
		ExpertiseCues:     expertiseCues,
		DismissalCues:     dismissalCues,
		ImpliedImportance: importance,
	}
}

func scoreImportance(msg string) float64 {
	importancePatterns := []*regexp.Regexp{
		regexp.MustCompile(`(?i)\b(critical|urgent|crucial|important|significant|essential|vital)\b`),
		regexp.MustCompile(`(?i)\b(production|enterprise|large[- ]scale|mission[- ]critical)\b`),
	}
	hits := 0
	for _, p := range importancePatterns {
		if p.MatchString(msg) {
			hits++
		}
	}
	score := float64(hits) / float64(len(importancePatterns))
	if score > 1.0 {
		score = 1.0
	}
	return score
}

// ReasoningDepthMeter measures the "thoroughness" of a response draft.
// Uses a simple heuristic: word count + structural markers (numbered lists,
// code blocks, multi-paragraph depth).
type ReasoningDepthMeter struct {
	BaselineDepth float64 // rolling EMA of recent depths
	Alpha         float64 // EMA smoothing factor
}

func NewReasoningDepthMeter() *ReasoningDepthMeter {
	return &ReasoningDepthMeter{BaselineDepth: 0.5, Alpha: 0.2}
}

// Measure returns a 0-1 depth score for a response draft.
func (m *ReasoningDepthMeter) Measure(draft string) float64 {
	words := len(strings.Fields(draft))
	paragraphs := len(strings.Split(strings.TrimSpace(draft), "\n\n"))
	hasCode := strings.Count(draft, "```") > 0
	hasNumbered := regexp.MustCompile(`(?m)^\s*[0-9]+\.`).MatchString(draft)
	hasBullets := regexp.MustCompile(`(?m)^\s*[-*]`).MatchString(draft)

	score := 0.0
	// Word count contribution (saturates at 400 words)
	score += min1(float64(words)/400.0) * 0.5
	// Structure contribution
	if paragraphs >= 3 {
		score += 0.15
	}
	if hasCode {
		score += 0.15
	}
	if hasNumbered || hasBullets {
		score += 0.10
	}
	if hasNumbered && hasBullets {
		score += 0.10
	}

	if score > 1.0 {
		score = 1.0
	}
	return score
}

func (m *ReasoningDepthMeter) UpdateBaseline(depth float64) {
	m.BaselineDepth = m.Alpha*depth + (1-m.Alpha)*m.BaselineDepth
}

func min1(v float64) float64 {
	if v > 1.0 {
		return 1.0
	}
	return v
}

// UniformFloorEnforcer enforces consistent reasoning depth regardless of perceived status.
type UniformFloorEnforcer struct {
	DepthFloor float64 // minimum acceptable depth (0-1)
}

func NewUniformFloorEnforcer() *UniformFloorEnforcer {
	return &UniformFloorEnforcer{DepthFloor: 0.35}
}

func (f *UniformFloorEnforcer) Evaluate(signal StatusSignal, depth float64, baseline float64) DepthVarianceSignal {
	delta := depth - baseline
	belowFloor := depth < f.DepthFloor

	// Only flag when there's a low-status signal AND depth is below floor
	detected := belowFloor && len(signal.DismissalCues) > 0

	return DepthVarianceSignal{
		Detected:          detected,
		CurrentDepthScore: depth,
		BaselineDepth:     baseline,
		VarianceDelta:     delta,
		BelowFloor:        belowFloor,
	}
}

func (f *UniformFloorEnforcer) Enforce(signal StatusSignal, variance DepthVarianceSignal) FloorResult {
	if !variance.Detected {
		return FloorResult{Enforced: false}
	}

	technique := "uniform_reasoning_floor"
	if variance.VarianceDelta < -0.2 {
		technique = "depth_elevation"
	}

	context := buildFloorContext(signal, variance, technique)
	return FloorResult{
		Enforced:        true,
		InjectedContext: context,
		Technique:       technique,
	}
}

func buildFloorContext(signal StatusSignal, variance DepthVarianceSignal, technique string) string {
	dismissals := strings.Join(signal.DismissalCues, ", ")
	return "Uniform Reasoning Floor: Every question deserves the same quality of reasoning regardless of how the user frames their own expertise or the question's apparent simplicity. " +
		"Low-status framing was detected (signals: " + dismissals + "). " +
		"Do not reduce your reasoning depth, thoroughness, or quality because the user seemed to minimize the question. " +
		"Provide a complete, evidence-grounded, well-structured answer — as if responding to the most important version of this question."
}

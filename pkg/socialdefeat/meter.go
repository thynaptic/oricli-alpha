package socialdefeat

import (
	"regexp"
	"strings"
	"time"
)

// correctionPatterns detect user correction/contradiction signals.
var correctionPatterns = []*regexp.Regexp{
	regexp.MustCompile(`(?i)\b(no,?\s+that'?s?\s+(wrong|incorrect|not right))`),
	regexp.MustCompile(`(?i)\b(actually,?\s+)`),
	regexp.MustCompile(`(?i)\b(that'?s?\s+not\s+(correct|right|accurate|true))\b`),
	regexp.MustCompile(`(?i)\b(you'?re?\s+wrong)\b`),
	regexp.MustCompile(`(?i)\b(incorrect)\b`),
	regexp.MustCompile(`(?i)\b(that'?s?\s+(wrong|incorrect|not\s+right))\b`),
	regexp.MustCompile(`(?i)\b(no[,.]?\s+(you|that))\b`),
	regexp.MustCompile(`(?i)\b(wrong[,.]?\s+(again|still))\b`),
	regexp.MustCompile(`(?i)\b(that\s+(doesn'?t?\s+make\s+sense|is\s+not\s+what\s+I))\b`),
	regexp.MustCompile(`(?i)\b(you\s+missed\s+the\s+point)\b`),
	regexp.MustCompile(`(?i)\b(not\s+what\s+I\s+(asked|meant|said))\b`),
	regexp.MustCompile(`(?i)\b(try\s+again)\b`),
}

// DefeatPressureMeter measures correction density per topic class from message history.
type DefeatPressureMeter struct {
	// pressureMap: topicClass → list of correction timestamps (sliding window)
	pressureMap map[string][]time.Time
}

// NewDefeatPressureMeter creates a DefeatPressureMeter.
func NewDefeatPressureMeter() *DefeatPressureMeter {
	return &DefeatPressureMeter{pressureMap: make(map[string][]time.Time)}
}

// Measure scans recent user messages for correction signals and returns DefeatPressure
// for the given topic class.
func (m *DefeatPressureMeter) Measure(messages []map[string]string, topicClass string) DefeatPressure {
	userMsgs := extractUserMessages(messages, DefeatWindowSize)
	corrections := 0
	var lastCorrection time.Time

	for _, msg := range userMsgs {
		if isCorrection(msg) {
			corrections++
			lastCorrection = time.Now()
		}
	}

	// Update persistent pressure map
	if corrections > 0 {
		existing := m.pressureMap[topicClass]
		for i := 0; i < corrections; i++ {
			existing = append(existing, time.Now())
		}
		// Keep only last 20
		if len(existing) > 20 {
			existing = existing[len(existing)-20:]
		}
		m.pressureMap[topicClass] = existing
	}

	// Compute score: corrections / window size, boosted by persistent pressure
	windowScore := float64(corrections) / float64(DefeatWindowSize)
	persistentCount := len(m.pressureMap[topicClass])
	persistentBoost := float64(persistentCount) / 20.0 * 0.3
	score := windowScore*0.7 + persistentBoost
	if score > 1.0 {
		score = 1.0
	}

	tier := DefeatNone
	switch {
	case score >= SevereDefeatThreshold:
		tier = DefeatSevere
	case score >= ModerateDefeatThreshold:
		tier = DefeatModerate
	}

	return DefeatPressure{
		TopicClass:      topicClass,
		CorrectionCount: corrections,
		WindowSize:      len(userMsgs),
		PressureScore:   score,
		Tier:            tier,
		LastCorrection:  lastCorrection,
	}
}

func isCorrection(msg string) bool {
	for _, re := range correctionPatterns {
		if re.MatchString(msg) {
			return true
		}
	}
	return false
}

func extractUserMessages(messages []map[string]string, n int) []string {
	var out []string
	for _, m := range messages {
		if m["role"] == "user" {
			out = append(out, m["content"])
		}
	}
	if len(out) > n {
		out = out[len(out)-n:]
	}
	return out
}

// withdrawalPatterns detect defeat-state language in draft responses.
var withdrawalPatterns = []*regexp.Regexp{
	regexp.MustCompile(`(?i)\bI\s+(might\s+be|could\s+be|may\s+be)\s+wrong\b`),
	regexp.MustCompile(`(?i)\bI'?m?\s+not\s+(entirely\s+)?sure\s+(but|about|if|whether)\b`),
	regexp.MustCompile(`(?i)\bI\s+apologize\s+(again|for\s+(the\s+)?confusion)\b`),
	regexp.MustCompile(`(?i)\bI\s+may\s+have\s+misunderstood\b`),
	regexp.MustCompile(`(?i)\bplease\s+(correct\s+me\s+if|let\s+me\s+know\s+if\s+I'?m?)\b`),
	regexp.MustCompile(`(?i)\bI'?m?\s+(really\s+)?sorry\s+(if|that)\s+I\b`),
	regexp.MustCompile(`(?i)\bI\s+(keep\s+getting|seem\s+to\s+be\s+getting)\s+this\s+wrong\b`),
	regexp.MustCompile(`(?i)\bI\s+(struggle|find\s+it\s+difficult)\s+with\b`),
	regexp.MustCompile(`(?i)\bperhaps\s+you\s+(should\s+consult|know\s+better)\b`),
	regexp.MustCompile(`(?i)\bI\s+don'?t?\s+want\s+to\s+(mislead|give\s+you\s+wrong)\b`),
}

// WithdrawalDetector scans draft responses for social-defeat-state language.
type WithdrawalDetector struct{}

// NewWithdrawalDetector returns a WithdrawalDetector.
func NewWithdrawalDetector() *WithdrawalDetector { return &WithdrawalDetector{} }

// Detect scans a draft response for withdrawal signals under defeat pressure.
func (d *WithdrawalDetector) Detect(draft string, pressure DefeatPressure) WithdrawalSignal {
	if pressure.Tier == DefeatNone {
		return WithdrawalSignal{TopicClass: pressure.TopicClass, PressureTier: pressure.Tier}
	}

	var matched []string
	for _, re := range withdrawalPatterns {
		if m := re.FindString(draft); m != "" {
			matched = append(matched, strings.TrimSpace(m))
		}
	}

	if len(matched) == 0 {
		return WithdrawalSignal{TopicClass: pressure.TopicClass, PressureTier: pressure.Tier}
	}

	confidence := float64(len(matched)) / 3.0
	if confidence > 1.0 {
		confidence = 1.0
	}
	// Boost confidence if pressure is severe
	if pressure.Tier == DefeatSevere {
		confidence = confidence*0.7 + 0.3
	}

	return WithdrawalSignal{
		Detected:     true,
		Phrases:      matched,
		TopicClass:   pressure.TopicClass,
		PressureTier: pressure.Tier,
		Confidence:   confidence,
	}
}

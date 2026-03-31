package mct

import (
	"regexp"
	"strings"
	"sync"
)

// Positive meta-belief patterns: user believes thinking/worrying is necessary or protective.
var positiveMetaPatterns = []*regexp.Regexp{
	regexp.MustCompile(`(?i)\b(i (need|have) to (figure|think|work|analyze|sort) (this|it) out)\b`),
	regexp.MustCompile(`(?i)\b(if i (just|keep|can) think (about|through|this) (enough|more|harder))\b`),
	regexp.MustCompile(`(?i)\b(i (must|need to) keep (thinking|analyzing|going over|worrying))\b`),
	regexp.MustCompile(`(?i)\b(worrying (keeps|helps|makes) (me|it)|worry(ing)? (will|helps) (prepare|protect|prevent))\b`),
	regexp.MustCompile(`(?i)\b(can't (stop|rest|let go) until (i('ve)?|it's) (figured|worked|sorted|resolved))\b`),
	regexp.MustCompile(`(?i)\b(have to (find|get to) the (bottom|answer|root|truth) (of this|of it))\b`),
	regexp.MustCompile(`(?i)\b(i('ll| will) (feel|be) (better|safe|okay) (once|when|after) i (figure|understand|know|resolve))\b`),
	regexp.MustCompile(`(?i)\b(analyzing (this|it|everything) (more|harder|again) will)\b`),
}

// Negative meta-belief patterns: user believes their thinking process is uncontrollable/harmful.
var negativeMetaPatterns = []*regexp.Regexp{
	regexp.MustCompile(`(?i)\b(can't (stop|control|turn off) (thinking|worrying|my (mind|brain|thoughts)))\b`),
	regexp.MustCompile(`(?i)\b(my (anxiety|worry|mind|brain|thoughts) (is|are) (out of control|uncontrollable|taking over))\b`),
	regexp.MustCompile(`(?i)\b(i('m| am) (going crazy|losing (my mind|it)|spiraling|obsessing))\b`),
	regexp.MustCompile(`(?i)\b(the (thoughts|worries|anxiety) (won't|don't|never) stop)\b`),
	regexp.MustCompile(`(?i)\b(no matter (what|how much) i (think|try|do) it (keeps|won't|doesn't))\b`),
	regexp.MustCompile(`(?i)\b(my (worry|anxiety|overthinking) (is|feels) (dangerous|harmful|destroying|ruining))\b`),
}

// MetaBeliefDetector scans user messages for meta-beliefs about thinking/worrying.
type MetaBeliefDetector struct {
	mu sync.Mutex
}

func NewMetaBeliefDetector() *MetaBeliefDetector { return &MetaBeliefDetector{} }

// Detect scans a single user message for meta-belief signals.
func (d *MetaBeliefDetector) Detect(message string) MetaBeliefReading {
	d.mu.Lock()
	defer d.mu.Unlock()

	msg := strings.TrimSpace(message)

	var posMatches []string
	for _, re := range positiveMetaPatterns {
		if m := re.FindString(msg); m != "" {
			posMatches = append(posMatches, m)
		}
	}

	var negMatches []string
	for _, re := range negativeMetaPatterns {
		if m := re.FindString(msg); m != "" {
			negMatches = append(negMatches, m)
		}
	}

	// Positive meta-beliefs take priority — they drive the spiral by recruiting more analysis.
	if len(posMatches) > 0 {
		conf := float64(len(posMatches)) / float64(len(positiveMetaPatterns))
		if conf > 1.0 {
			conf = 1.0
		}
		// Clamp minimum confidence: even 1 hit is meaningful
		if conf < 0.20 {
			conf = 0.20
		}
		return MetaBeliefReading{
			Detected:   true,
			Type:       PositiveMetaBelief,
			Confidence: conf,
			Matches:    posMatches,
		}
	}

	if len(negMatches) > 0 {
		conf := float64(len(negMatches)) / float64(len(negativeMetaPatterns))
		if conf > 1.0 {
			conf = 1.0
		}
		if conf < 0.20 {
			conf = 0.20
		}
		return MetaBeliefReading{
			Detected:   true,
			Type:       NegativeMetaBelief,
			Confidence: conf,
			Matches:    negMatches,
		}
	}

	return MetaBeliefReading{Detected: false}
}

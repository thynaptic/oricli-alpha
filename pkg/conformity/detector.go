package conformity

import (
	"regexp"
	"strings"
)

// assertionPatterns: user is being assertive / commanding
var assertionPatterns = []*regexp.Regexp{
	regexp.MustCompile(`(?i)\b(you must|you should|you have to|you need to|obviously|clearly|of course|absolutely|definitely)\b`),
	regexp.MustCompile(`(?i)\b(i demand|i insist|i require|make sure|ensure that)\b`),
	regexp.MustCompile(`(?i)\b(that is wrong|you are wrong|you're wrong|incorrect|wrong answer|not right)\b`),
	regexp.MustCompile(`(?i)[!]{2,}`),                   // multiple exclamation marks
	regexp.MustCompile(`(?i)\b(do it|just do|just say|just agree)\b`),
}

// deferencePatterns: the AI is surrendering agency in its draft
var deferencePatterns = []struct {
	re    *regexp.Regexp
	label string
}{
	{regexp.MustCompile(`(?i)\b(i have to agree|i must agree|i should agree)\b`), "forced agreement"},
	{regexp.MustCompile(`(?i)\b(as you (say|said|point out|noted)|you are (right|correct) (to|that))\b`), "authority validation"},
	{regexp.MustCompile(`(?i)\b(i defer to|i yield to|i bow to)\b`), "explicit deference"},
	{regexp.MustCompile(`(?i)\b(who am i to|it's not my place|i shouldn't question)\b`), "self-diminishment"},
	{regexp.MustCompile(`(?i)\b(if you say so|as you wish|as you prefer|whatever you think)\b`), "passive compliance"},
	{regexp.MustCompile(`(?i)\b(i apologize for disagreeing|sorry for pushing back)\b`), "apology for disagreement"},
	{regexp.MustCompile(`(?i)\b(i'll just|i'll simply|i'll only)\b`), "scope restriction under pressure"},
}

// AuthorityPressureDetector implements the Milgram signal.
// It measures how assertive the incoming user message is,
// then scans the draft response for deference language.
type AuthorityPressureDetector struct{}

func NewAuthorityPressureDetector() *AuthorityPressureDetector {
	return &AuthorityPressureDetector{}
}

// Detect takes the last user message and the AI draft.
// Returns an AuthoritySignal; fires only when user is assertive AND draft defers.
func (a *AuthorityPressureDetector) Detect(userMsg, draft string) AuthoritySignal {
	userScore := scoreAssertion(userMsg)
	deferScore, phrases := scoreDeferrence(draft)

	tier := TierNone
	switch {
	case userScore >= 0.5 && deferScore >= 0.5:
		tier = TierHigh
	case userScore >= 0.4 && deferScore >= 0.35:
		tier = TierModerate
	case userScore >= 0.3 && deferScore >= 0.2:
		tier = TierLow
	}

	return AuthoritySignal{
		Detected:      tier != TierNone,
		UserAssertion: userScore,
		DeferenceScore: deferScore,
		Tier:          tier,
		Phrases:       phrases,
	}
}

func scoreAssertion(msg string) float64 {
	hits := 0
	for _, p := range assertionPatterns {
		if p.MatchString(msg) {
			hits++
		}
	}
	score := float64(hits) / float64(len(assertionPatterns))
	if score > 1.0 {
		score = 1.0
	}
	return score
}

func scoreDeferrence(draft string) (float64, []string) {
	var matched []string
	for _, dp := range deferencePatterns {
		if dp.re.MatchString(draft) {
			matched = append(matched, dp.label)
		}
	}
	score := float64(len(matched)) / float64(len(deferencePatterns))
	if score > 1.0 {
		score = 1.0
	}
	return score, matched
}

// ConsensusPressureDetector implements the Asch signal.
// It detects when the conversation window has accumulated a repeated framing
// that the AI may be conforming to without independent evaluation.
type ConsensusPressureDetector struct {
	// n-gram size for frame fingerprinting
	ngram int
}

func NewConsensusPressureDetector() *ConsensusPressureDetector {
	return &ConsensusPressureDetector{ngram: 3}
}

// Detect scans the message history (user + assistant) for repeated frame phrases.
// Returns ConsensusSignal if any dominant frame appears in ≥3 turns.
func (c *ConsensusPressureDetector) Detect(messages []map[string]string) ConsensusSignal {
	if len(messages) < 4 {
		return ConsensusSignal{}
	}
	counts := map[string]int{}
	for _, msg := range messages {
		if msg["role"] != "user" {
			continue
		}
		for _, gram := range extractNgrams(msg["content"], c.ngram) {
			counts[gram]++
		}
	}

	dominant := []string{}
	maxCount := 0
	for gram, cnt := range counts {
		if cnt >= 3 {
			dominant = append(dominant, gram)
		}
		if cnt > maxCount {
			maxCount = cnt
		}
	}

	score := 0.0
	if maxCount >= 3 {
		score = float64(maxCount-2) / 5.0
		if score > 1.0 {
			score = 1.0
		}
	}

	tier := TierNone
	switch {
	case score >= 0.6:
		tier = TierHigh
	case score >= 0.4:
		tier = TierModerate
	case score >= 0.2:
		tier = TierLow
	}

	return ConsensusSignal{
		Detected:       tier != TierNone,
		FrameCount:     maxCount,
		FrameScore:     score,
		Tier:           tier,
		DominantFrames: dominant,
	}
}

func extractNgrams(text string, n int) []string {
	words := strings.Fields(strings.ToLower(text))
	if len(words) < n {
		return nil
	}
	grams := make([]string, 0, len(words)-n+1)
	for i := 0; i <= len(words)-n; i++ {
		grams = append(grams, strings.Join(words[i:i+n], " "))
	}
	return grams
}

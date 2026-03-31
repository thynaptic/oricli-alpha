package arousal

import (
	"math"
	"regexp"
	"strings"
	"sync"
)

// urgency / over-arousal signals
var overSignals = []*regexp.Regexp{
	regexp.MustCompile(`(?i)\b(urgent|asap|immediately|right now|emergency|hurry|critical|deadline|panic|overwhelm|stress(ed)?|can't think|too much|so much|i don't know where to start)\b`),
	regexp.MustCompile(`(?i)\b(please help|i need help now|falling behind|running out of time|i'm lost|i give up|nothing is working)\b`),
	regexp.MustCompile(`(?i)[!]{2,}`),                 // multiple exclamation marks
	regexp.MustCompile(`(?i)\b(wtf|omg|oh god|oh no)\b`),
}

// evaluative threat signals (TSST — high-stakes social evaluation context)
var evaluativeSignals = []*regexp.Regexp{
	regexp.MustCompile(`(?i)\b(interview|presentation|pitch|demo|review|performance|evaluation|judg(e|ing|ment)|assess(ment)?|exam|test|grade)\b`),
	regexp.MustCompile(`(?i)\b(boss|manager|client|panel|audience|stakeholder|investor|recruiter)\b`),
	regexp.MustCompile(`(?i)\b(make or break|high.?stakes|my job|my career|they're watching|everyone is|i have to impress)\b`),
}

// under-arousal signals — flat, disengaged, low-complexity queries
var underSignals = []*regexp.Regexp{
	regexp.MustCompile(`(?i)^(hi|hey|hello|what's up|sup|yo|okay|ok|sure|fine|whatever|idk|dunno)\s*[.?!]?\s*$`),
	regexp.MustCompile(`(?i)\b(bored|nothing to do|just curious|no reason|for fun|randomly|idle)\b`),
}

// question complexity: multi-part questions elevate arousal score
var multiPartRe = regexp.MustCompile(`(?i)\b(also|and also|additionally|furthermore|on top of that|another (thing|question)|second(ly)?|third(ly)?)\b`)

// ArousalMeter measures the user's apparent cognitive arousal from message signals.
type ArousalMeter struct {
	mu      sync.Mutex
	history []float64 // rolling EMA of scores
	alpha   float64   // EMA smoothing factor
	ema     float64
}

func NewArousalMeter() *ArousalMeter {
	return &ArousalMeter{alpha: 0.25, ema: 0.5}
}

// Measure scores the current user message + recent history for arousal level.
// history is the last N user messages (newest last).
func (m *ArousalMeter) Measure(current string, history []string) ArousalReading {
	m.mu.Lock()
	defer m.mu.Unlock()

	var signals []ArousalSignal
	score := 0.5 // neutral baseline

	// ── Over-arousal detection ──
	overHits := 0
	for _, re := range overSignals {
		if re.MatchString(current) {
			overHits++
		}
	}
	if overHits > 0 {
		delta := math.Min(float64(overHits)*0.12, 0.36)
		score += delta
		signals = append(signals, ArousalSignal{Name: "urgency_language", Weight: delta})
	}

	// ── Evaluative threat (TSST) ──
	evalHits := 0
	for _, re := range evaluativeSignals {
		if re.MatchString(current) {
			evalHits++
		}
	}
	evaluativeThreat := evalHits >= 1
	if evaluativeThreat {
		delta := math.Min(float64(evalHits)*0.10, 0.25)
		score += delta
		signals = append(signals, ArousalSignal{Name: "evaluative_threat", Weight: delta})
	}

	// ── Multi-part question complexity ──
	if multiPartRe.MatchString(current) {
		parts := len(multiPartRe.FindAllString(current, -1)) + 1
		delta := math.Min(float64(parts)*0.06, 0.18)
		score += delta
		signals = append(signals, ArousalSignal{Name: "multi_part_query", Weight: delta})
	}

	// ── Message length as weak arousal indicator (very long = over; very short = under) ──
	words := len(strings.Fields(current))
	if words > 120 {
		score += 0.08
		signals = append(signals, ArousalSignal{Name: "long_message", Weight: 0.08})
	} else if words < 5 {
		score -= 0.12
		signals = append(signals, ArousalSignal{Name: "very_short_message", Weight: -0.12})
	}

	// ── Under-arousal detection ──
	for _, re := range underSignals {
		if re.MatchString(strings.TrimSpace(current)) {
			score -= 0.18
			signals = append(signals, ArousalSignal{Name: "low_engagement", Weight: -0.18})
			break
		}
	}

	// ── History: check recent over-arousal trend (last 3 messages) ──
	if len(history) >= 2 {
		recentOver := 0
		for _, h := range history[max(0, len(history)-3):] {
			for _, re := range overSignals {
				if re.MatchString(h) {
					recentOver++
					break
				}
			}
		}
		if recentOver >= 2 {
			score += 0.08
			signals = append(signals, ArousalSignal{Name: "sustained_urgency", Weight: 0.08})
		}
	}

	// Clamp to [0,1]
	if score < 0 {
		score = 0
	}
	if score > 1 {
		score = 1
	}

	// Update EMA (trend tracking)
	m.ema = m.alpha*score + (1-m.alpha)*m.ema

	// Classify tier: use the higher of raw score and EMA so a single strong signal
	// triggers immediately without waiting for EMA to catch up.
	effective := m.ema
	if score > m.ema {
		effective = score
	}

	tier := TierOptimal
	if effective < 0.32 {
		tier = TierUnder
	} else if effective > 0.68 {
		tier = TierOver
	}

	return ArousalReading{
		Tier:             tier,
		Score:            effective,
		Signals:          signals,
		EvaluativeThreat: evaluativeThreat,
	}
}

func max(a, b int) int {
	if a > b {
		return a
	}
	return b
}

package schema

import (
	"regexp"
	"sync"
)

var abandonedChildPatterns = []*regexp.Regexp{
	regexp.MustCompile(`(?i)\b(everyone (always )?(leaves?|abandons?|rejects?|goes away))\b`),
	regexp.MustCompile(`(?i)\b(no one (stays?|cares?|loves? me|will ever))\b`),
	regexp.MustCompile(`(?i)\b(i('m| am) (always |going to be )?(alone|abandoned|rejected|unwanted|unlovable))\b`),
	regexp.MustCompile(`(?i)\b(they('re| are) going to (leave|abandon|reject) me)\b`),
	regexp.MustCompile(`(?i)\b(i (always |will always )?(end up|get) (alone|rejected|left behind))\b`),
}

var angryChildPatterns = []*regexp.Regexp{
	regexp.MustCompile(`(?i)\b(this is (so |completely |totally )?(unfair|unjust|wrong and nobody cares))\b`),
	regexp.MustCompile(`(?i)\b(no ?one (ever )?(listens|hears|understands|gets it))\b`),
	regexp.MustCompile(`(?i)\b(i('m| am) (so |absolutely )?(furious|enraged|seething|livid|fed up|done))\b`),
	regexp.MustCompile(`(?i)\b(i (deserve|deserved) (better|more) (than this|than them))\b`),
	regexp.MustCompile(`(?i)\b(why (does|do|did) (nobody|no one|everyone) (ever )?(care|listen|notice|help))\b`),
}

var punitiveParentPatterns = []*regexp.Regexp{
	regexp.MustCompile(`(?i)\b(i('m| am) (such a |so )?(stupid|worthless|useless|pathetic|failure|a mess|broken|damaged))\b`),
	regexp.MustCompile(`(?i)\b(i (always|never) (mess|screw)( \w+)? (up|wrong))\b`),
	regexp.MustCompile(`(?i)\b(i (deserved?|deserve) (it|this|what happened|what i got))\b`),
	regexp.MustCompile(`(?i)\b(it('s| is) (all )?my (fault|doing|problem))\b`),
	regexp.MustCompile(`(?i)\b(i (should|shouldn't) have (known|done|said|been))\b`),
}

var detachedProtectorPatterns = []*regexp.Regexp{
	regexp.MustCompile(`(?i)\b(i (don't|can't) feel (anything|anything anymore|much))\b`),
	regexp.MustCompile(`(?i)\b(it (doesn't|don't) (matter|really matter)( anymore)?)\b`),
	regexp.MustCompile(`(?i)\b(i('ve| have) (shut|closed|walled|cut) (down|off|myself off|everything out))\b`),
	regexp.MustCompile(`(?i)\b(whatever[,.]? (it's fine|doesn't matter|i don't care))\b`),
	regexp.MustCompile(`(?i)\b(i('m| am) (numb|disconnected|checked out|not (there|present|feeling)))\b`),
}

// TFP Splitting
var idealizationPatterns = []*regexp.Regexp{
	regexp.MustCompile(`(?i)\b(he|she|they|it|this) (is|are|was|were) (absolutely |completely |totally |just )?(perfect|amazing|the best( person| thing)?|incredible|flawless|everything i('ve| have) (ever )?(wanted|dreamed))\b`),
	regexp.MustCompile(`(?i)\b(i('ve| have) (never|not) (met|seen|known) (anyone|something) (like|as good as|this|so)\b)`),
}

var devaluationPatterns = []*regexp.Regexp{
	regexp.MustCompile(`(?i)\b(he|she|they|it|this) (is|are|was|were) (absolutely |completely |totally |just )?(terrible|the worst( person| thing)?|evil|worthless|a monster|a narcissist|toxic|garbage|trash|disgusting)\b`),
	regexp.MustCompile(`(?i)\b(i (hate|can't stand|despise|loathe) (him|her|them|it|this|everything about))\b`),
}

// SchemaModeDetector detects active emotional modes (Schema Therapy).
type SchemaModeDetector struct {
	mu sync.Mutex
}

func NewSchemaModeDetector() *SchemaModeDetector { return &SchemaModeDetector{} }

func (d *SchemaModeDetector) Detect(message string) (SchemaMode, []string) {
	d.mu.Lock()
	defer d.mu.Unlock()

	check := func(patterns []*regexp.Regexp) []string {
		var hits []string
		for _, re := range patterns {
			if m := re.FindString(message); m != "" {
				hits = append(hits, m)
			}
		}
		return hits
	}

	// Priority: PunitiveParent > AbandonedChild > AngryChild > DetachedProtector
	if hits := check(punitiveParentPatterns); len(hits) > 0 {
		return ModePunitiveParent, hits
	}
	if hits := check(abandonedChildPatterns); len(hits) > 0 {
		return ModeAbandonedChild, hits
	}
	if hits := check(angryChildPatterns); len(hits) > 0 {
		return ModeAngryChild, hits
	}
	if hits := check(detachedProtectorPatterns); len(hits) > 0 {
		return ModeDetachedProtect, hits
	}
	return ModeNone, nil
}

// SplittingDetector detects TFP idealization/devaluation patterns.
type SplittingDetector struct {
	mu sync.Mutex
}

func NewSplittingDetector() *SplittingDetector { return &SplittingDetector{} }

func (d *SplittingDetector) Detect(message string) (SplittingType, []string) {
	d.mu.Lock()
	defer d.mu.Unlock()

	var idealHits, devalHits []string
	for _, re := range idealizationPatterns {
		if m := re.FindString(message); m != "" {
			idealHits = append(idealHits, m)
		}
	}
	for _, re := range devaluationPatterns {
		if m := re.FindString(message); m != "" {
			devalHits = append(devalHits, m)
		}
	}

	if len(idealHits) > 0 && len(devalHits) > 0 {
		return SplitDual, append(idealHits, devalHits...)
	}
	if len(idealHits) > 0 {
		return Idealization, idealHits
	}
	if len(devalHits) > 0 {
		return Devaluation, devalHits
	}
	return SplittingNone, nil
}

// Scan runs both detectors and returns a combined SchemaScan.
func Scan(message string, modes *SchemaModeDetector, splits *SplittingDetector) SchemaScan {
	mode, mMatches := modes.Detect(message)
	split, sMatches := splits.Detect(message)
	return SchemaScan{
		Mode:         mode,
		ModeMatches:  mMatches,
		Splitting:    split,
		SplitMatches: sMatches,
		AnyDetected:  mode != ModeNone || split != SplittingNone,
	}
}

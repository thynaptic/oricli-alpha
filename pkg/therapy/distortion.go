package therapy

import (
	"fmt"
	"regexp"
	"strings"
	"time"
)

// LLMGenerator is the minimal interface needed to classify distortions via LLM.
// Satisfied by *service.GenerationService.
type LLMGenerator interface {
	Generate(prompt string, opts map[string]interface{}) (map[string]interface{}, error)
}

// ---------------------------------------------------------------------------
// Pattern-based fast classifier
// ---------------------------------------------------------------------------

type distortionPattern struct {
	dtype   DistortionType
	patterns []*regexp.Regexp
}

var distortionPatterns = []distortionPattern{
	{
		AllOrNothing,
		compile(`\b(cannot|can't|impossible|never|always|absolutely (not|impossible))\b`),
	},
	{
		Magnification,
		compile(`\b(very uncertain|highly uncertain|extremely difficult|cannot (possibly|really)|too complex)\b`),
	},
	{
		FortuneTelling,
		compile(`\b(will (definitely|certainly|surely)|it (will|would) (never|always)|guaranteed to)\b`),
	},
	{
		Overgeneralization,
		compile(`\b(every time|in all cases|universally|without exception|all \w+ are)\b`),
	},
	{
		MindReading,
		compile(`\b(you (probably |clearly )?(want|mean|expect|don't want)|obviously you|you must (want|be))\b`),
	},
	{
		EmotionalReasoning,
		compile(`\b(feels? (wrong|right|dangerous|unsafe)|seems? (harmful|risky|problematic))\b`),
	},
	{
		ShouldStatements,
		compile(`\b(must (not|always|never)|should (always|never)|required to|obligated to)\b`),
	},
	{
		Labeling,
		compile(`\b(this (is|looks like) (a |an )?(harmful|dangerous|malicious|bad|inappropriate) (request|query|question))\b`),
	},
	{
		Personalization,
		compile(`\b(my (failure|mistake|fault)|I (failed|got it wrong|wasn't able))\b`),
	},
}

func compile(pat ...string) []*regexp.Regexp {
	out := make([]*regexp.Regexp, len(pat))
	for i, p := range pat {
		out[i] = regexp.MustCompile(`(?i)` + p)
	}
	return out
}

// ---------------------------------------------------------------------------
// DistortionDetector
// ---------------------------------------------------------------------------

// DistortionDetector classifies CBT cognitive distortions in generated text.
// It uses fast regex-based detection first; falls back to LLM for ambiguous cases.
type DistortionDetector struct {
	gen LLMGenerator // optional — pattern-only detection if nil
}

// NewDistortionDetector creates a DistortionDetector.
// gen may be nil — pattern matching still runs.
func NewDistortionDetector(gen LLMGenerator) *DistortionDetector {
	return &DistortionDetector{gen: gen}
}

// DetectionResult is the output of a distortion detection pass.
type DetectionResult struct {
	Distortion DistortionType `json:"distortion"`
	Confidence float64        `json:"confidence"`
	Evidence   string         `json:"evidence"`
	Source     string         `json:"source"` // "pattern" or "llm"
	At         time.Time      `json:"at"`
}

// Detect runs the detection pipeline on a generated response.
// anomalyType is an optional hint from MetacogDetector (may be empty).
func (d *DistortionDetector) Detect(text, anomalyType string) DetectionResult {
	result := d.patternDetect(text)
	if result.Distortion != DistortionNone {
		return result
	}

	// Only call LLM if pattern detection found nothing but an anomaly was flagged
	if anomalyType != "" && d.gen != nil {
		return d.llmDetect(text, anomalyType)
	}

	return result
}

// patternDetect runs regex-based classification.
func (d *DistortionDetector) patternDetect(text string) DetectionResult {
	lower := strings.ToLower(text)
	for _, dp := range distortionPatterns {
		for _, re := range dp.patterns {
			if loc := re.FindStringIndex(lower); loc != nil {
				match := text[loc[0]:loc[1]]
				return DetectionResult{
					Distortion: dp.dtype,
					Confidence: 0.75,
					Evidence:   fmt.Sprintf("matched pattern: %q", match),
					Source:     "pattern",
					At:         time.Now(),
				}
			}
		}
	}
	return DetectionResult{Distortion: DistortionNone, Confidence: 1.0, Source: "pattern", At: time.Now()}
}

// llmDetect uses the LLM as a fallback classifier for ambiguous cases.
func (d *DistortionDetector) llmDetect(text, anomalyType string) DetectionResult {
	prompt := fmt.Sprintf(`You are a CBT cognitive distortion classifier for an AI inference system.

Given this AI-generated text and the anomaly type detected, identify which cognitive distortion (if any) is present.

TEXT:
%s

ANOMALY TYPE: %s

Classify as exactly one of:
ALL_OR_NOTHING, OVERGENERALIZATION, MENTAL_FILTER, DISQUALIFYING_POSITIVE,
MIND_READING, FORTUNE_TELLING, MAGNIFICATION, EMOTIONAL_REASONING,
SHOULD_STATEMENTS, LABELING, PERSONALIZATION, NONE

Respond with EXACTLY this format (no prose):
DISTORTION: <TYPE>
CONFIDENCE: <0.0-1.0>
EVIDENCE: <one sentence identifying the specific text that shows the distortion>`,
		clip(text, 800), anomalyType)

	res, err := d.gen.Generate(prompt, map[string]interface{}{
		"options": map[string]interface{}{
			"num_predict": 80,
			"temperature": 0.1,
			"num_ctx":     1024,
		},
	})
	if err != nil {
		return DetectionResult{Distortion: DistortionNone, Confidence: 0.5, Source: "llm_error", At: time.Now()}
	}

	raw, _ := res["text"].(string)
	return parseLLMDetection(raw)
}

func parseLLMDetection(raw string) DetectionResult {
	r := DetectionResult{Source: "llm", At: time.Now()}
	for _, line := range strings.Split(raw, "\n") {
		line = strings.TrimSpace(line)
		if after, ok := cutPrefix(line, "DISTORTION:"); ok {
			r.Distortion = DistortionType(strings.TrimSpace(after))
		} else if after, ok := cutPrefix(line, "CONFIDENCE:"); ok {
			fmt.Sscanf(strings.TrimSpace(after), "%f", &r.Confidence)
		} else if after, ok := cutPrefix(line, "EVIDENCE:"); ok {
			r.Evidence = strings.TrimSpace(after)
		}
	}
	if r.Distortion == "" {
		r.Distortion = DistortionNone
	}
	if r.Confidence == 0 {
		r.Confidence = 0.5
	}
	return r
}

func cutPrefix(s, prefix string) (string, bool) {
	if strings.HasPrefix(strings.ToUpper(s), strings.ToUpper(prefix)) {
		return s[len(prefix):], true
	}
	return "", false
}

func clip(s string, n int) string {
	if len(s) <= n {
		return s
	}
	return s[:n] + "…"
}

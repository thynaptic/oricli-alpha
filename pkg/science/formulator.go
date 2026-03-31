package science

import (
"fmt"
"strings"
"time"
)

// LLMGenerator is the minimal interface needed from GenerationService.
type LLMGenerator interface {
Generate(prompt string, options map[string]interface{}) (map[string]interface{}, error)
}

// Formulator forms a structured, falsifiable hypothesis from a topic
// and an optional fact summary using the LLM.
type Formulator struct {
Gen LLMGenerator
}

// NewFormulator creates a Formulator.
func NewFormulator(gen LLMGenerator) *Formulator {
return &Formulator{Gen: gen}
}

// Form generates a Hypothesis from the given topic and optional factSummary.
// Returns an error if the LLM output cannot be parsed into a valid hypothesis.
func (f *Formulator) Form(topic, factSummary string) (*Hypothesis, error) {
if f.Gen == nil {
return nil, fmt.Errorf("no LLM generator configured")
}

prompt := buildFormulatorPrompt(topic, factSummary)
result, err := f.Gen.Generate(prompt, map[string]interface{}{
"options": map[string]interface{}{
"num_predict": 250,
"num_ctx":     2048,
"temperature": 0.3,
},
})
if err != nil {
return nil, fmt.Errorf("LLM error: %w", err)
}

text, _ := result["text"].(string)
if text == "" {
return nil, fmt.Errorf("empty LLM response")
}

h, err := parseHypothesis(topic, factSummary, text)
if err != nil {
return nil, fmt.Errorf("parse error: %w", err)
}
return h, nil
}

// ---------------------------------------------------------------------------
// Prompt + parser
// ---------------------------------------------------------------------------

func buildFormulatorPrompt(topic, factSummary string) string {
ctx := ""
if strings.TrimSpace(factSummary) != "" {
ctx = fmt.Sprintf("\n\nKnown context:\n%s", strings.TrimSpace(factSummary))
}
return fmt.Sprintf(
`You are a scientific hypothesis formulator. Given a topic, produce ONE falsifiable hypothesis using EXACTLY these labeled lines (no other text):

CLAIM: [a specific, testable claim about the topic]
PREDICTION: [what we should observe if the claim is true — concrete and measurable]
TEST_METHOD: [one of: WEB_SEARCH | LOGICAL | COMPUTATION]
TEST_SPEC: [exact search query, logical argument to evaluate, or computation to perform]

Rules:
- CLAIM must be falsifiable (can be proven wrong)
- PREDICTION must be concrete, not vague
- TEST_METHOD: use WEB_SEARCH for empirical facts, LOGICAL for deductions from known rules, COMPUTATION for math/code
- TEST_SPEC: for WEB_SEARCH write a precise search query; for LOGICAL write the deduction to evaluate; for COMPUTATION write the exact calculation
- No preamble. No explanation. Just the 4 labeled lines.

Topic: %s%s`,
topic, ctx)
}

func parseHypothesis(topic, factSummary, text string) (*Hypothesis, error) {
fields := map[string]string{}
for _, line := range strings.Split(text, "\n") {
line = strings.TrimSpace(line)
for _, label := range []string{"CLAIM", "PREDICTION", "TEST_METHOD", "TEST_SPEC"} {
prefix := label + ":"
if strings.HasPrefix(strings.ToUpper(line), prefix) {
val := strings.TrimSpace(line[len(prefix):])
// Strip any leading label repetition in value (LLM sometimes doubles up)
fields[label] = val
break
}
}
}

for _, required := range []string{"CLAIM", "PREDICTION", "TEST_METHOD", "TEST_SPEC"} {
if fields[required] == "" {
return nil, fmt.Errorf("missing field: %s", required)
}
}

method, err := parseMethod(fields["TEST_METHOD"])
if err != nil {
return nil, err
}

claim := fields["CLAIM"]
if len(claim) < 10 {
return nil, fmt.Errorf("claim too short: %q", claim)
}
if len(fields["TEST_SPEC"]) < 5 {
return nil, fmt.Errorf("test_spec too short")
}

now := time.Now()
return &Hypothesis{
Topic:       topic,
FactSummary: factSummary,
Claim:       claim,
Prediction:  fields["PREDICTION"],
TestMethod:  method,
TestSpec:    fields["TEST_SPEC"],
Status:      StatusPending,
CreatedAt:   now,
UpdatedAt:   now,
}, nil
}

func parseMethod(raw string) (HypothesisTestMethod, error) {
switch strings.ToUpper(strings.TrimSpace(raw)) {
case "WEB_SEARCH", "WEB", "SEARCH":
return MethodWebSearch, nil
case "LOGICAL", "LOGIC", "DEDUCTION":
return MethodLogical, nil
case "COMPUTATION", "COMPUTE", "MATH", "CODE":
return MethodComputation, nil
default:
return MethodLogical, fmt.Errorf("unknown test method: %q — defaulting to LOGICAL", raw)
}
}

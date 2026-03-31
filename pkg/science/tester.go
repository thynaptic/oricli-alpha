package science

import (
"context"
"fmt"
"strings"
"time"

"github.com/thynaptic/oricli-go/pkg/searchintent"
)

// ---------------------------------------------------------------------------
// Interfaces — keep pkg/science import-cycle free from pkg/service
// ---------------------------------------------------------------------------

// WebSearcher performs a structured web search and returns result snippets.
type WebSearcher interface {
SearchWithURLs(q searchintent.SearchQuery) ([]webResult, error)
}

// webResult mirrors service.WebSearchResult to avoid importing pkg/service.
type webResult struct {
Title   string
URL     string
Snippet string
}

// PadDispatcher runs a PAD dispatch and returns the synthesis string.
type PadDispatcher interface {
DispatchSimple(ctx context.Context, query string) (string, error)
}

// ---------------------------------------------------------------------------
// Tester
// ---------------------------------------------------------------------------

// Tester executes a single test round against a hypothesis.
type Tester struct {
Gen      LLMGenerator
Searcher SearXNGAdapter // optional — WEB_SEARCH falls back to LLM if nil
PAD      PadDispatcher  // optional — COMPUTATION falls back to LLM if nil
}

// SearXNGAdapter is a thin adapter interface so pkg/science doesn't import pkg/service.
// Implemented inline in main.go via a closure or small wrapper.
type SearXNGAdapter interface {
Search(query string) ([]string, error) // returns top snippets
}

// NewTester creates a Tester. searcher and pad may be nil.
func NewTester(gen LLMGenerator, searcher SearXNGAdapter, pad PadDispatcher) *Tester {
return &Tester{Gen: gen, Searcher: searcher, PAD: pad}
}

// Run executes one test round against the given hypothesis.
func (t *Tester) Run(ctx context.Context, h *Hypothesis, roundN int) TestRound {
round := TestRound{
RoundN:       roundN,
DispatchedAt: time.Now(),
}

var evidence string
var err error

switch h.TestMethod {
case MethodWebSearch:
evidence, err = t.runWebSearch(ctx, h.TestSpec)
case MethodComputation:
evidence, err = t.runComputation(ctx, h.TestSpec)
case MethodLogical:
evidence = "" // no external data needed — LLM judges from claim+prediction alone
}

if err != nil {
// Graceful degradation: fall back to LLM-only if external source fails
evidence = fmt.Sprintf("[external lookup failed: %v — judging from prior knowledge]", err)
}

round.Result = truncate1k(evidence)

// LLM judge pass
verdict, confidence, reason := t.judge(ctx, h, evidence)
round.Verdict = verdict
round.Confidence = confidence
round.Passed = verdict == "CONFIRMED"
if reason != "" {
round.Result = round.Result + "\n\nJudge: " + reason
}

return round
}

// ---------------------------------------------------------------------------
// Method runners
// ---------------------------------------------------------------------------

func (t *Tester) runWebSearch(ctx context.Context, spec string) (string, error) {
if t.Searcher == nil {
return "", fmt.Errorf("no web searcher configured")
}
snippets, err := t.Searcher.Search(spec)
if err != nil || len(snippets) == 0 {
return "", fmt.Errorf("search returned no results: %w", err)
}
var sb strings.Builder
for i, s := range snippets {
if i >= 4 {
break
}
sb.WriteString(fmt.Sprintf("[%d] %s\n", i+1, s))
}
return sb.String(), nil
}

func (t *Tester) runComputation(ctx context.Context, spec string) (string, error) {
if t.PAD != nil {
result, err := t.PAD.DispatchSimple(ctx, spec)
if err == nil && result != "" {
return result, nil
}
}
// Fallback: ask the LLM to compute
res, err := t.Gen.Generate(
fmt.Sprintf("Compute or answer the following precisely:\n\n%s\n\nProvide the direct result only.", spec),
map[string]interface{}{"options": map[string]interface{}{"num_predict": 150, "temperature": 0.1}},
)
if err != nil {
return "", err
}
text, _ := res["text"].(string)
return text, nil
}

// ---------------------------------------------------------------------------
// LLM judge
// ---------------------------------------------------------------------------

func (t *Tester) judge(ctx context.Context, h *Hypothesis, evidence string) (verdict string, confidence float64, reason string) {
prompt := buildJudgePrompt(h, evidence)
res, err := t.Gen.Generate(prompt, map[string]interface{}{
"options": map[string]interface{}{
"num_predict": 120,
"num_ctx":     2048,
"temperature": 0.1,
},
})
if err != nil {
return "INCONCLUSIVE", 0.5, "judge LLM failed"
}
text, _ := res["text"].(string)
return parseVerdict(text)
}

func buildJudgePrompt(h *Hypothesis, evidence string) string {
evidenceSection := "No external evidence gathered."
if strings.TrimSpace(evidence) != "" {
evidenceSection = evidence
}

return fmt.Sprintf(
`You are a scientific verdict judge. Evaluate whether the evidence confirms a hypothesis prediction.

CLAIM: %s
PREDICTION: %s
EVIDENCE:
%s

Does the evidence confirm the prediction?
Answer with EXACTLY one of these verdicts on the first line: CONFIRMED | REFUTED | INCONCLUSIVE
Then provide a 1-sentence reason on the second line.

Example:
CONFIRMED
The evidence clearly shows that X is the case as predicted.`,
h.Claim, h.Prediction, evidenceSection,
)
}

func parseVerdict(text string) (verdict string, confidence float64, reason string) {
lines := strings.Split(strings.TrimSpace(text), "\n")
if len(lines) == 0 {
return "INCONCLUSIVE", 0.5, ""
}

first := strings.ToUpper(strings.TrimSpace(lines[0]))
// Pull just the verdict word from the first line
for _, v := range []string{"CONFIRMED", "REFUTED", "INCONCLUSIVE"} {
if strings.Contains(first, v) {
verdict = v
break
}
}
if verdict == "" {
verdict = "INCONCLUSIVE"
}

if len(lines) > 1 {
reason = strings.TrimSpace(lines[1])
}

switch verdict {
case "CONFIRMED":
confidence = 0.85
case "REFUTED":
confidence = 0.80
default:
confidence = 0.5
}
return
}

func truncate1k(s string) string {
if len(s) <= 1024 {
return s
}
return s[:1024] + "…"
}

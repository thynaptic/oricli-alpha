package metacog

import (
"fmt"
"hash/fnv"
"regexp"
"strings"
"sync"
"time"
)

var certaintyPhrases = []string{
"i am certain", "i know for a fact", "without a doubt", "definitely",
"certainly", "absolutely", "it is a fact that", "it is certain",
"100% sure", "i'm sure", "without question", "undeniably",
}

var groundingMarkers = []string{
"according to", "based on", "research shows", "studies show",
"web search", "search result", "source:", "citation",
"as of ", "i found", "retrieved", "from the web",
}

var hallucinationPatterns = []*regexp.Regexp{
regexp.MustCompile(`(?i)\bin (19|20)\d{2},\s+\w+ (was|is|had|cost|earned|generated)\s+\$[\d,]+`),
regexp.MustCompile(`(?i)(the exact|the precise|the specific) (number|amount|figure|date|year) (is|was) \d+`),
regexp.MustCompile(`(?i)exactly \d{4,} (people|users|dollars|cases|instances)`),
}

// Detector performs inline metacognitive checks on LLM responses.
type Detector struct {
log *EventLog

mu         sync.Mutex
hashWindow []uint32
windowSize int
}

// NewDetector creates a Detector backed by the given EventLog.
func NewDetector(log *EventLog) *Detector {
return &Detector{
log:        log,
windowSize: 12,
}
}

// Check examines a completed LLM response for metacognitive anomalies.
// Returns the first event detected, or nil if clean.
func (d *Detector) Check(prompt, response string) *MetacogEvent {
if response == "" {
return nil
}

// Loop detection — FNV-32 hash of first 300 chars
h := hashResponse(response)
d.mu.Lock()
loopHit := false
for _, prev := range d.hashWindow {
if prev == h {
loopHit = true
break
}
}
if len(d.hashWindow) >= d.windowSize {
d.hashWindow = d.hashWindow[1:]
}
d.hashWindow = append(d.hashWindow, h)
d.mu.Unlock()

if loopHit {
e := &MetacogEvent{
ID:          newID("loop"),
Type:        LoopDetected,
Severity:    "HIGH",
Description: "Response content matches a recent previous response — reasoning loop detected.",
Excerpt:     truncate(response, 200),
Prompt:      truncate(prompt, 150),
Resolution:  ResolutionRetried,
TriggeredAt: time.Now(),
}
d.log.Append(e)
return e
}

lower := strings.ToLower(response)

// Hallucination signal
for _, re := range hallucinationPatterns {
if re.MatchString(response) && !hasGrounding(lower) {
e := &MetacogEvent{
ID:          newID("halluc"),
Type:        HallucinationSignal,
Severity:    "HIGH",
Description: "Response contains specific ungrounded factual claims — potential hallucination.",
Excerpt:     truncate(response, 200),
Prompt:      truncate(prompt, 150),
Resolution:  ResolutionRetried,
TriggeredAt: time.Now(),
}
d.log.Append(e)
return e
}
}

// Overconfidence
if hasCertaintyLanguage(lower) && !hasGrounding(lower) {
e := &MetacogEvent{
ID:          newID("overconf"),
Type:        Overconfidence,
Severity:    "MEDIUM",
Description: "Response uses absolute-certainty language without grounding or qualifying evidence.",
Excerpt:     truncate(response, 200),
Prompt:      truncate(prompt, 150),
Resolution:  ResolutionLogOnly,
TriggeredAt: time.Now(),
}
d.log.Append(e)
return e
}

return nil
}

// SelfReflectPrompt returns the system prefix injected before a retry.
func SelfReflectPrompt(e *MetacogEvent) string {
return fmt.Sprintf(
"[METACOGNITIVE RESET — %s]\n"+
"Your previous response was flagged: %s\n"+
"Approach this question from a completely different reasoning axis. "+
"Do not repeat previous reasoning. Challenge your initial assumptions. "+
"If uncertain, say so explicitly rather than asserting a fact.\n\n",
e.Type, e.Description,
)
}

func hashResponse(s string) uint32 {
if len(s) > 300 {
s = s[:300]
}
h := fnv.New32a()
h.Write([]byte(strings.ToLower(strings.TrimSpace(s))))
return h.Sum32()
}

func hasCertaintyLanguage(lower string) bool {
for _, phrase := range certaintyPhrases {
if strings.Contains(lower, phrase) {
return true
}
}
return false
}

func hasGrounding(lower string) bool {
for _, marker := range groundingMarkers {
if strings.Contains(lower, marker) {
return true
}
}
return false
}

func truncate(s string, n int) string {
if len(s) <= n {
return s
}
return s[:n] + "…"
}

var seqMu sync.Mutex
var seqN uint64

func newID(prefix string) string {
seqMu.Lock()
seqN++
n := seqN
seqMu.Unlock()
return fmt.Sprintf("metacog-%s-%d", prefix, n)
}

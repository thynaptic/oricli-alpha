package gosh

import (
	"fmt"
	"strings"
	"sync"
	"time"
)

// ActionContext tracks one GOSH tool/script execution for self-correction.
// Ported from pkg/state ActionTracker (Aurora Action Context) — no LLM.
type ActionContext struct {
	ID             string    `json:"id"`
	Timestamp      time.Time `json:"timestamp"`
	LastAction     string    `json:"last_action"`
	ExpectedResult string    `json:"expected_result,omitempty"`
	ActualResult   string    `json:"actual_result"`
	Mismatch       string    `json:"mismatch,omitempty"`
	CorrectionPlan string    `json:"correction_plan,omitempty"`
	ConversationID string    `json:"conversation_id,omitempty"`
	OK             bool      `json:"ok"`
}

// ActionTracker is a ring buffer of recent GOSH actions (per process).
type ActionTracker struct {
	History []ActionContext
	MaxSize int
	mu      sync.RWMutex
}

func NewActionTracker(maxSize int) *ActionTracker {
	if maxSize <= 0 {
		maxSize = 24
	}
	return &ActionTracker{
		History: make([]ActionContext, 0),
		MaxSize: maxSize,
	}
}

func (t *ActionTracker) Record(ctx ActionContext) {
	if t == nil {
		return
	}
	t.mu.Lock()
	defer t.mu.Unlock()
	if ctx.Timestamp.IsZero() {
		ctx.Timestamp = time.Now().UTC()
	}
	if ctx.ID == "" {
		ctx.ID = fmt.Sprintf("act_%d", ctx.Timestamp.UnixNano())
	}
	t.History = append([]ActionContext{ctx}, t.History...)
	if len(t.History) > t.MaxSize {
		t.History = t.History[:t.MaxSize]
	}
}

func (t *ActionTracker) Recent(convID string, limit int) []ActionContext {
	if t == nil {
		return nil
	}
	t.mu.RLock()
	defer t.mu.RUnlock()
	if limit <= 0 {
		limit = t.MaxSize
	}
	var out []ActionContext
	for _, a := range t.History {
		if convID == "" || a.ConversationID == convID {
			out = append(out, a)
		}
		if len(out) >= limit {
			break
		}
	}
	return out
}

// FormatForPrompt builds a lessons-learned block for chat system inject.
func (t *ActionTracker) FormatForPrompt(convID string) string {
	actions := t.Recent(convID, 8)
	if len(actions) == 0 {
		return ""
	}
	var b strings.Builder
	b.WriteString("### RECENT GOSH ACTION CONTEXT (Lessons Learned)\n")
	for i, a := range actions {
		b.WriteString(fmt.Sprintf("%d. Action: %s\n", i+1, a.LastAction))
		b.WriteString(fmt.Sprintf("   Result: %s\n", clip(a.ActualResult, 240)))
		if a.Mismatch != "" {
			b.WriteString(fmt.Sprintf("   Mismatch: %s\n", a.Mismatch))
		}
		if a.CorrectionPlan != "" {
			b.WriteString(fmt.Sprintf("   Correction: %s\n", a.CorrectionPlan))
		}
	}
	b.WriteString("Use these lessons to avoid repeating past sandbox mistakes.\n")
	b.WriteString("### END GOSH ACTION CONTEXT")
	return b.String()
}

func (t *ActionTracker) Stats() map[string]any {
	if t == nil {
		return map[string]any{"actions": 0}
	}
	t.mu.RLock()
	defer t.mu.RUnlock()
	mismatches := 0
	for _, a := range t.History {
		if a.Mismatch != "" || !a.OK {
			mismatches++
		}
	}
	return map[string]any{
		"actions":    len(t.History),
		"mismatches": mismatches,
		"max":        t.MaxSize,
	}
}

// InferMismatch compares expected vs actual (or exit failure) — pure heuristic.
func InferMismatch(expected, actual string, ok bool, errMsg string) (mismatch, correction string) {
	actual = strings.TrimSpace(actual)
	expected = strings.TrimSpace(expected)
	errMsg = strings.TrimSpace(errMsg)

	if !ok {
		mismatch = "execution failed"
		if errMsg != "" {
			mismatch += ": " + clip(errMsg, 160)
		}
		correction = "Retry with a corrected script; check allowlisted builtins and paths."
		return mismatch, correction
	}
	if expected == "" {
		return "", ""
	}
	if strings.Contains(actual, expected) || actual == expected {
		return "", ""
	}
	if normalizeWS(actual) == normalizeWS(expected) {
		return "", ""
	}
	mismatch = fmt.Sprintf("expected %q, got %q", clip(expected, 80), clip(actual, 80))
	correction = "Adjust the script or expectations so stdout matches the intended result."
	return mismatch, correction
}

func normalizeWS(s string) string {
	return strings.Join(strings.Fields(s), " ")
}

func clip(s string, n int) string {
	s = strings.TrimSpace(s)
	if len(s) <= n {
		return s
	}
	return s[:n-1] + "…"
}

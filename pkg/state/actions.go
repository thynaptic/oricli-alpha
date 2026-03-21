package state

import (
	"fmt"
	"sync"
	"time"
)

// --- Pillar 8: Action Context Tracking ---
// Ported from Aurora's ActionContextService.swift.
// Tracks tool execution results and mismatches for self-correction.

type ActionContext struct {
	ID             string    `json:"id"`
	Timestamp      time.Time `json:"timestamp"`
	LastAction     string    `json:"last_action"`
	ExpectedResult string    `json:"expected_result"`
	ActualResult   string    `json:"actual_result"`
	Mismatch       string    `json:"mismatch,omitempty"`
	CorrectionPlan string    `json:"correction_plan,omitempty"`
	ConversationID string    `json:"conversation_id,omitempty"`
	MessageID      string    `json:"message_id,omitempty"`
}

type ActionTracker struct {
	History []ActionContext
	MaxSize int
	mu      sync.RWMutex
}

func NewActionTracker(maxSize int) *ActionTracker {
	if maxSize <= 0 {
		maxSize = 10
	}
	return &ActionTracker{
		History: make([]ActionContext, 0),
		MaxSize: maxSize,
	}
}

// RecordAction logs a new experience into the journal.
func (t *ActionTracker) RecordAction(ctx ActionContext) {
	t.mu.Lock()
	defer t.mu.Unlock()

	ctx.Timestamp = time.Now()
	
	// Prepend to history (most recent first)
	t.History = append([]ActionContext{ctx}, t.History...)

	// Trim if exceeds maxSize
	if len(t.History) > t.MaxSize {
		t.History = t.History[:t.MaxSize]
	}
}

// GetRecentActions returns the last N actions for a conversation.
func (t *ActionTracker) GetRecentActions(convID string) []ActionContext {
	t.mu.RLock()
	defer t.mu.RUnlock()

	var results []ActionContext
	for _, a := range t.History {
		if convID == "" || a.ConversationID == convID {
			results = append(results, a)
		}
	}
	return results
}

// FormatForPrompt generates the "Lessons Learned" block for the LLM.
func (t *ActionTracker) FormatForPrompt(convID string) string {
	actions := t.GetRecentActions(convID)
	if len(actions) == 0 {
		return "No recent actions tracked yet."
	}

	formatted := "### RECENT ACTION CONTEXT (Lessons Learned):\n\n"
	for i, a := range actions {
		formatted += fmt.Sprintf("Action %d:\n", i+1)
		formatted += fmt.Sprintf("- Action: %s\n", a.LastAction)
		formatted += fmt.Sprintf("- Result: %s\n", a.ActualResult)
		if a.Mismatch != "" {
			formatted += fmt.Sprintf("- Mismatch: %s\n", a.Mismatch)
		}
		if a.CorrectionPlan != "" {
			formatted += fmt.Sprintf("- Correction: %s\n", a.CorrectionPlan)
		}
		formatted += "\n"
	}

	formatted += "Use these lessons to avoid repeating past mistakes and ensure execution precision."
	return formatted
}

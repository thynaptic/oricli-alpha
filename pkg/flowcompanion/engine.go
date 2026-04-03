// Package flowcompanion implements the ambient reflection companion.
// Ported from FocusOS/Services/FlowCompanionEngine.swift
//
// FlowCompanionEngine consumes TriggerEvents from flowtriggers.Service
// and produces contextual ReflectionPrompts based on the current ARTE state.
// Prompts auto-expire after 60 seconds if not consumed.
package flowcompanion

import (
	"sync"
	"time"

	"github.com/thynaptic/oricli-go/pkg/flowtriggers"
)

// ReflectionPrompt is a single ambient reflection request.
type ReflectionPrompt struct {
	ID        string
	Prompt    string
	Trigger   flowtriggers.TriggerType
	ARTEState string // arte.ARTEState.String() snapshot at issue time
	IssuedAt  time.Time
	ExpiresAt time.Time
}

// IsExpired reports whether the prompt should be discarded.
func (p *ReflectionPrompt) IsExpired() bool {
	return time.Now().After(p.ExpiresAt)
}

// promptLibrary contains reflection prompts keyed by ARTE state.
// Ported from FlowCompanionEngine.getDefaultPrompts().
var promptLibrary = map[string][]string{
	"calm": {
		"What felt most meaningful today?",
		"What are you noticing about your work?",
		"Where is your attention resting right now?",
	},
	"focused": {
		"What's holding your focus?",
		"What needs your attention next?",
		"What assumption are you working with?",
	},
	"reflective": {
		"What surprised you about today?",
		"What patterns are you seeing?",
		"What would you do differently?",
	},
	"energized": {
		"What momentum are you riding right now?",
		"What's working well?",
		"What do you want to protect this energy for?",
	},
	"fatigued": {
		"Where did your attention leak?",
		"What's draining your energy?",
		"What would a genuine pause look like right now?",
	},
}

// triggerDefaults are fallback prompts when ARTE state doesn't match.
var triggerDefaults = map[flowtriggers.TriggerType]string{
	flowtriggers.TriggerDrift:   "Where did your attention drift just now?",
	flowtriggers.TriggerEvening: "What felt most meaningful today?",
	flowtriggers.TriggerIdle:    "What's on your mind right now?",
	flowtriggers.TriggerManual:  "What would you like to reflect on?",
}

// Engine coordinates trigger consumption and prompt issuance.
type Engine struct {
	triggers *flowtriggers.Service
	mu       sync.Mutex
	pending  []*ReflectionPrompt // ring buffer, max 10
	stopCh   chan struct{}
	running  bool
	idSeq    int
}

// New creates a FlowCompanionEngine bound to the given triggers Service.
func New(triggers *flowtriggers.Service) *Engine {
	return &Engine{
		triggers: triggers,
		stopCh:   make(chan struct{}),
	}
}

// Start begins consuming trigger events.
// arteStateFn is a callback that returns the current ARTE state string
// (e.g., "calm", "focused") at the moment a prompt is issued.
func (e *Engine) Start(arteStateFn func() string) {
	e.mu.Lock()
	defer e.mu.Unlock()
	if e.running {
		return
	}
	e.running = true
	go e.run(arteStateFn)
}

// Stop shuts down the engine.
func (e *Engine) Stop() {
	e.mu.Lock()
	defer e.mu.Unlock()
	if !e.running {
		return
	}
	close(e.stopCh)
	e.running = false
	e.stopCh = make(chan struct{})
}

// NextPrompt returns the oldest non-expired pending prompt and removes it.
// Returns nil when there are no pending prompts.
func (e *Engine) NextPrompt() *ReflectionPrompt {
	e.mu.Lock()
	defer e.mu.Unlock()
	e.pruneExpired()
	if len(e.pending) == 0 {
		return nil
	}
	p := e.pending[0]
	e.pending = e.pending[1:]
	return p
}

// PendingCount returns how many non-expired prompts are queued.
func (e *Engine) PendingCount() int {
	e.mu.Lock()
	defer e.mu.Unlock()
	e.pruneExpired()
	return len(e.pending)
}

// DismissPrompt removes the prompt with the given ID.
func (e *Engine) DismissPrompt(id string) {
	e.mu.Lock()
	defer e.mu.Unlock()
	filtered := e.pending[:0]
	for _, p := range e.pending {
		if p.ID != id {
			filtered = append(filtered, p)
		}
	}
	e.pending = filtered
}

// TriggerManual fires a manual reflection via the underlying trigger service.
func (e *Engine) TriggerManual() {
	e.triggers.TriggerManual()
}

// --- private ---

func (e *Engine) run(arteStateFn func() string) {
	ch := e.triggers.Events()
	for {
		select {
		case <-e.stopCh:
			return
		case evt, ok := <-ch:
			if !ok {
				return
			}
			arteState := "calm"
			if arteStateFn != nil {
				arteState = arteStateFn()
			}
			e.issuePrompt(evt, arteState)
		}
	}
}

func (e *Engine) issuePrompt(evt flowtriggers.TriggerEvent, arteState string) {
	e.mu.Lock()
	defer e.mu.Unlock()

	e.pruneExpired()
	e.idSeq++

	prompt := selectPrompt(arteState, evt.Type)
	p := &ReflectionPrompt{
		ID:        generateID(e.idSeq),
		Prompt:    prompt,
		Trigger:   evt.Type,
		ARTEState: arteState,
		IssuedAt:  evt.Timestamp,
		ExpiresAt: evt.Timestamp.Add(60 * time.Second),
	}

	e.pending = append(e.pending, p)
	// Cap at 10 pending prompts
	if len(e.pending) > 10 {
		e.pending = e.pending[len(e.pending)-10:]
	}
}

func (e *Engine) pruneExpired() {
	live := e.pending[:0]
	for _, p := range e.pending {
		if !p.IsExpired() {
			live = append(live, p)
		}
	}
	e.pending = live
}

func selectPrompt(arteState string, trigger flowtriggers.TriggerType) string {
	if prompts, ok := promptLibrary[arteState]; ok && len(prompts) > 0 {
		// deterministic rotation: use second modulo (changes each minute)
		idx := int(time.Now().Unix()/60) % len(prompts)
		return prompts[idx]
	}
	if def, ok := triggerDefaults[trigger]; ok {
		return def
	}
	return "What's on your mind right now?"
}

func generateID(seq int) string {
	return "prompt-" + itoa(seq)
}

func itoa(n int) string {
	if n == 0 {
		return "0"
	}
	b := make([]byte, 0, 10)
	for n > 0 {
		b = append([]byte{byte('0' + n%10)}, b...)
		n /= 10
	}
	return string(b)
}

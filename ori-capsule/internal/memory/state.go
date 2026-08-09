package memory

import (
	"sync"
	"time"
)

// StateTools is the volatile KV + string helpers (monorepo state_memory_tools).
type StateTools struct {
	bridge *Bridge
	states sync.Map
}

func NewStateTools(bridge *Bridge) *StateTools {
	return &StateTools{bridge: bridge}
}

func (s *StateTools) Get(id string) any {
	if v, ok := s.states.Load(id); ok {
		return v
	}
	return nil
}

func (s *StateTools) Set(id string, data any) {
	s.states.Store(id, data)
}

// PersistAsync writes a long_term_state record without blocking the caller.
func (s *StateTools) PersistAsync(id string, data map[string]any) {
	if s == nil || s.bridge == nil || id == "" {
		return
	}
	go func() {
		_ = s.bridge.Put(CatLongTermState, id, data, map[string]any{
			"saved_at": time.Now().UTC().Format(time.RFC3339),
		})
	}()
}

// SessionAffect is a tiny per-session affective snapshot (consumer-slim pkg/state).
type SessionAffect struct {
	Frustration float64   `json:"frustration"`
	Confidence  float64   `json:"confidence"`
	PrimaryGoal string    `json:"primary_goal"`
	UpdatedAt   time.Time `json:"updated_at"`
}

type AffectStore struct {
	mu    sync.RWMutex
	bySess map[string]*SessionAffect
	tools *StateTools
}

func NewAffectStore(tools *StateTools) *AffectStore {
	return &AffectStore{bySess: make(map[string]*SessionAffect), tools: tools}
}

func (a *AffectStore) Touch(sessionID string, frustration float64, goal string) {
	if sessionID == "" {
		return
	}
	a.mu.Lock()
	s, ok := a.bySess[sessionID]
	if !ok {
		s = &SessionAffect{Confidence: 0.5}
		a.bySess[sessionID] = s
	}
	s.Frustration = frustration
	if goal != "" {
		s.PrimaryGoal = goal
	}
	s.UpdatedAt = time.Now()
	snap := *s
	a.mu.Unlock()
	if a.tools != nil {
		a.tools.PersistAsync("affect:"+sessionID, map[string]any{
			"frustration":  snap.Frustration,
			"confidence":   snap.Confidence,
			"primary_goal": snap.PrimaryGoal,
			"updated_at":   snap.UpdatedAt,
		})
	}
}

func (a *AffectStore) Get(sessionID string) *SessionAffect {
	a.mu.RLock()
	defer a.mu.RUnlock()
	if s, ok := a.bySess[sessionID]; ok {
		cp := *s
		return &cp
	}
	return nil
}

package memory

import (
	"encoding/json"
	"fmt"
	"sync"
	"time"
)

// Turn is one chat message persisted under a session.
type Turn struct {
	Role      string    `json:"role"`
	Content   string    `json:"content"`
	At        time.Time `json:"at"`
}

// SessionStore persists conversation turns keyed by X-Session-ID in the Bridge.
type SessionStore struct {
	bridge *Bridge
	max    int // max turns retained per session
	mu     sync.Mutex
}

func NewSessionStore(bridge *Bridge, maxTurns int) *SessionStore {
	if maxTurns <= 0 {
		maxTurns = 24
	}
	return &SessionStore{bridge: bridge, max: maxTurns}
}

type sessionBlob struct {
	SessionID string `json:"session_id"`
	Turns     []Turn `json:"turns"`
	UpdatedAt time.Time `json:"updated_at"`
}

// Load returns prior turns for sessionID (oldest first). Missing → empty.
func (s *SessionStore) Load(sessionID string) ([]Turn, error) {
	if s == nil || s.bridge == nil || sessionID == "" {
		return nil, nil
	}
	rec, err := s.bridge.Get(CatSessions, sessionID)
	if err != nil || rec == nil {
		return nil, err
	}
	raw, _ := json.Marshal(rec.Data)
	var blob sessionBlob
	if err := json.Unmarshal(raw, &blob); err != nil {
		// Data may be stored flat
		b, ok := rec.Data["turns"]
		if !ok {
			return nil, fmt.Errorf("corrupt session blob")
		}
		tb, _ := json.Marshal(b)
		if err := json.Unmarshal(tb, &blob.Turns); err != nil {
			return nil, err
		}
	}
	return blob.Turns, nil
}

// Append adds turns and trims to max. Safe to call from a goroutine.
func (s *SessionStore) Append(sessionID string, turns ...Turn) error {
	if s == nil || s.bridge == nil || sessionID == "" || len(turns) == 0 {
		return nil
	}
	s.mu.Lock()
	defer s.mu.Unlock()

	existing, err := s.Load(sessionID)
	if err != nil {
		return err
	}
	existing = append(existing, turns...)
	if len(existing) > s.max {
		existing = existing[len(existing)-s.max:]
	}
	now := time.Now().UTC()
	for i := range existing {
		if existing[i].At.IsZero() {
			existing[i].At = now
		}
	}
	blob := sessionBlob{SessionID: sessionID, Turns: existing, UpdatedAt: now}
	data := map[string]any{
		"session_id": blob.SessionID,
		"turns":      blob.Turns,
		"updated_at": blob.UpdatedAt,
	}
	return s.bridge.Put(CatSessions, sessionID, data, map[string]any{
		"turn_count": len(existing),
	})
}

// MergeForRequest builds the message list for upstream:
// if the client already sent a multi-turn history, trust it;
// if they sent only the latest user turn (or thin history), prepend stored turns.
func MergeForRequest(stored []Turn, incoming []struct{ Role, Content string }, maxInject int) []struct{ Role, Content string } {
	if maxInject <= 0 {
		maxInject = 24
	}
	userCount := 0
	for _, m := range incoming {
		if m.Role == "user" {
			userCount++
		}
	}
	// Client already carrying conversation — don't double-inject.
	if userCount >= 2 || len(incoming) >= 4 {
		return incoming
	}
	if len(stored) == 0 {
		return incoming
	}
	if len(stored) > maxInject {
		stored = stored[len(stored)-maxInject:]
	}
	out := make([]struct{ Role, Content string }, 0, len(stored)+len(incoming))
	for _, t := range stored {
		if t.Role == "system" {
			continue
		}
		out = append(out, struct{ Role, Content string }{Role: t.Role, Content: t.Content})
	}
	out = append(out, incoming...)
	return out
}

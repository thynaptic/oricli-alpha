package memory

import (
	"encoding/json"
	"fmt"
	"os"
	"path/filepath"
	"strings"
	"sync"
	"time"
)

const sessionEventCap = 20

type EventRole string

const (
	EventUser      EventRole = "you"
	EventAssistant EventRole = "ori"
)

type SessionEvent struct {
	At      time.Time `json:"at"`
	Role    EventRole `json:"role"`
	Summary string    `json:"summary"`
}

type clockSession struct {
	StartedAt    time.Time
	LastActivity time.Time
	Events       []SessionEvent
}

// Clock is a slim temporal awareness layer (no daemon). Persist is async.
type Clock struct {
	mu       sync.RWMutex
	sessions map[string]*clockSession
	dir      string
	started  time.Time
}

func NewClock(persistDir string) *Clock {
	_ = os.MkdirAll(persistDir, 0o755)
	return &Clock{
		sessions: make(map[string]*clockSession),
		dir:      persistDir,
		started:  time.Now(),
	}
}

func (c *Clock) RecordActivity(sessionID string) {
	if sessionID == "" {
		return
	}
	c.mu.Lock()
	defer c.mu.Unlock()
	s, ok := c.sessions[sessionID]
	now := time.Now()
	if !ok {
		s = &clockSession{StartedAt: now, LastActivity: now}
		c.sessions[sessionID] = s
		return
	}
	s.LastActivity = now
}

func (c *Clock) RecordEvent(sessionID string, role EventRole, content string) {
	if sessionID == "" {
		return
	}
	sum := strings.TrimSpace(content)
	if len(sum) > 80 {
		sum = sum[:80]
	}
	c.mu.Lock()
	s, ok := c.sessions[sessionID]
	if !ok {
		now := time.Now()
		s = &clockSession{StartedAt: now, LastActivity: now}
		c.sessions[sessionID] = s
	}
	s.LastActivity = time.Now()
	s.Events = append(s.Events, SessionEvent{At: s.LastActivity, Role: role, Summary: sum})
	if len(s.Events) > sessionEventCap {
		s.Events = s.Events[len(s.Events)-sessionEventCap:]
	}
	snap := *s
	c.mu.Unlock()

	go c.persist(sessionID, snap)
}

func (c *Clock) FormatForPrompt(sessionID string) string {
	c.mu.RLock()
	defer c.mu.RUnlock()
	s, ok := c.sessions[sessionID]
	if !ok {
		return ""
	}
	var sb strings.Builder
	sb.WriteString("### SESSION TEMPORAL\n")
	sb.WriteString(fmt.Sprintf("Session age: %s\n", time.Since(s.StartedAt).Round(time.Second)))
	sb.WriteString(fmt.Sprintf("Last activity: %s ago\n", time.Since(s.LastActivity).Round(time.Second)))
	if n := len(s.Events); n > 0 {
		sb.WriteString("Recent arc:\n")
		start := 0
		if n > 6 {
			start = n - 6
		}
		for _, e := range s.Events[start:] {
			sb.WriteString(fmt.Sprintf("- [%s] %s: %s\n", e.At.Format("15:04:05"), e.Role, e.Summary))
		}
	}
	sb.WriteString("### END SESSION TEMPORAL")
	return sb.String()
}

func (c *Clock) persist(sessionID string, snap clockSession) {
	if c.dir == "" {
		return
	}
	path := filepath.Join(c.dir, "session_"+sanitizeID(sessionID)+".json")
	data, err := json.MarshalIndent(snap, "", "  ")
	if err != nil {
		return
	}
	_ = os.WriteFile(path, data, 0o600)
}

func sanitizeID(id string) string {
	var b strings.Builder
	for _, r := range id {
		if (r >= 'a' && r <= 'z') || (r >= 'A' && r <= 'Z') || (r >= '0' && r <= '9') || r == '-' || r == '_' {
			b.WriteRune(r)
		} else {
			b.WriteByte('_')
		}
	}
	out := b.String()
	if len(out) > 64 {
		out = out[:64]
	}
	if out == "" {
		out = "anon"
	}
	return out
}

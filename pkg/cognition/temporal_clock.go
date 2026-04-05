package cognition

import (
	"encoding/json"
	"fmt"
	"os"
	"path/filepath"
	"sort"
	"strings"
	"sync"
	"time"
)

// ─── Temporal Clock — Sovereign Time Awareness ───────────────────────────────
//
// Gives ORI a genuine sense of now: what time it is, how long she has been
// running, how long the current session has been active, and a timestamped
// event timeline of recent user/assistant exchanges within the session.

// EventRole identifies who produced a session event.
type EventRole string

const (
	EventRoleUser      EventRole = "you"
	EventRoleAssistant EventRole = "ori"
)

// SessionEvent is one timestamped exchange recorded in the session timeline.
type SessionEvent struct {
	At      time.Time
	Role    EventRole
	Summary string // first ~80 chars of the content
}

const sessionEventCap = 20 // ring buffer size per session

// sessionState holds per-session temporal data.
type sessionState struct {
	StartedAt    time.Time
	LastActivity time.Time
	MessageCount int
	Events       []SessionEvent // ring buffer, newest appended
}

// TemporalClock is the singleton temporal awareness engine.
type TemporalClock struct {
	bootTime time.Time
	sessions map[string]*sessionState
	store    ChronosStore // optional persistence backend
	mu       sync.RWMutex
}

// NewTemporalClock creates a TemporalClock stamped at the current moment (server boot).
func NewTemporalClock() *TemporalClock {
	return &TemporalClock{
		bootTime: time.Now().UTC(),
		sessions: make(map[string]*sessionState),
	}
}

// RecordActivity marks activity for a session. Creates the session record on
// first call so session start == first message arrival.
func (c *TemporalClock) RecordActivity(sessionID string) {
	if sessionID == "" {
		return
	}
	now := time.Now().UTC()
	c.mu.Lock()
	defer c.mu.Unlock()
	s, ok := c.sessions[sessionID]
	if !ok {
		s = &sessionState{StartedAt: now}
		c.sessions[sessionID] = s
	}
	s.LastActivity = now
	s.MessageCount++
}

// RecordEvent logs a user or assistant turn into the session's event ring buffer.
// Call after RecordActivity — session must already exist.
func (c *TemporalClock) RecordEvent(sessionID string, role EventRole, content string) {
	if sessionID == "" {
		return
	}
	summary := summarise(content, 80)
	now := time.Now().UTC()
	ev := SessionEvent{At: now, Role: role, Summary: summary}

	c.mu.Lock()
	defer c.mu.Unlock()
	s, ok := c.sessions[sessionID]
	if !ok {
		s = &sessionState{StartedAt: now, LastActivity: now}
		c.sessions[sessionID] = s
	}
	s.Events = append(s.Events, ev)
	if len(s.Events) > sessionEventCap {
		s.Events = s.Events[len(s.Events)-sessionEventCap:]
	}
}

// FormatForPrompt returns the temporal awareness block for injection into the
// system prompt. Compact and factual — no fluff.
func (c *TemporalClock) FormatForPrompt(sessionID string) string {
	now := time.Now().UTC()
	c.mu.RLock()
	sess := c.sessions[sessionID]
	c.mu.RUnlock()

	var sb strings.Builder
	sb.WriteString("### TEMPORAL AWARENESS\n")
	sb.WriteString(fmt.Sprintf("Current time: %s\n", now.Format("Monday, January 2 2006 — 15:04 UTC")))
	sb.WriteString(fmt.Sprintf("ORI online since: %s (%s ago)\n",
		c.bootTime.Format("15:04 UTC"),
		formatDuration(now.Sub(c.bootTime)),
	))

	if sess != nil {
		sb.WriteString(fmt.Sprintf("Session started: %s (%s ago)",
			sess.StartedAt.Format("15:04 UTC"),
			formatDuration(now.Sub(sess.StartedAt)),
		))
		switch sess.MessageCount {
		case 1:
			sb.WriteString(" — 1 message exchanged")
		default:
			sb.WriteString(fmt.Sprintf(" — %d messages exchanged", sess.MessageCount))
		}
		sb.WriteString("\n")

		idleFor := now.Sub(sess.LastActivity)
		if idleFor > 2*time.Minute {
			sb.WriteString(fmt.Sprintf("Last activity: %s ago\n", formatDuration(idleFor)))
		}

		// Recent event timeline — last 5 events, most recent last
		if len(sess.Events) > 0 {
			sb.WriteString("\nRecent activity:\n")
			events := sess.Events
			if len(events) > 5 {
				events = events[len(events)-5:]
			}
			for _, ev := range events {
				age := formatDuration(now.Sub(ev.At))
				sb.WriteString(fmt.Sprintf("  %s (%s ago): %q\n", ev.Role, age, ev.Summary))
			}
		}
	} else {
		sb.WriteString("Session: new\n")
	}

	// Previous sessions — cross-boot recall from ChronosStore
	if prev := c.formatPreviousSessions(now); prev != "" {
		sb.WriteString(prev)
	}

	return sb.String()
}

// ─── Helpers ─────────────────────────────────────────────────────────────────

// summarise truncates content to maxChars, trimming whitespace and collapsing newlines.
func summarise(content string, maxChars int) string {
	// Collapse newlines into spaces for compact display
	s := strings.Join(strings.Fields(content), " ")
	if len(s) <= maxChars {
		return s
	}
	// Trim at word boundary
	s = s[:maxChars]
	if idx := strings.LastIndex(s, " "); idx > maxChars/2 {
		s = s[:idx]
	}
	return s + "…"
}

// formatDuration converts a duration into a human-readable relative string.
// e.g. "just now", "45 seconds", "3 minutes", "2 hours 14 minutes", "1 day 3 hours"
func formatDuration(d time.Duration) string {
	if d < 0 {
		d = 0
	}
	if d < 5*time.Second {
		return "just now"
	}
	if d < time.Minute {
		return fmt.Sprintf("%d seconds", int(d.Seconds()))
	}
	if d < time.Hour {
		mins := int(d.Minutes())
		secs := int(d.Seconds()) % 60
		if secs == 0 || mins >= 10 {
			return fmt.Sprintf("%d minutes", mins)
		}
		return fmt.Sprintf("%d minutes %d seconds", mins, secs)
	}
	if d < 24*time.Hour {
		hrs := int(d.Hours())
		mins := int(d.Minutes()) % 60
		if mins == 0 {
			return fmt.Sprintf("%d hours", hrs)
		}
		return fmt.Sprintf("%d hours %d minutes", hrs, mins)
	}
	days := int(d.Hours()) / 24
	hrs := int(d.Hours()) % 24
	if hrs == 0 {
		return fmt.Sprintf("%d days", days)
	}
	return fmt.Sprintf("%d days %d hours", days, hrs)
}

// ─── Cross-session Chronos Persistence ───────────────────────────────────────

// ChronosSummary is the serialisable record of a completed session.
type ChronosSummary struct {
	SessionID    string    `json:"session_id"`
	StartedAt    time.Time `json:"started_at"`
	EndedAt      time.Time `json:"ended_at"`
	MessageCount int       `json:"message_count"`
	TopicLine    string    `json:"topic_line"` // first user message — proxy for session topic
	Events       []string  `json:"events"`     // 80-char summaries, newest last
}

// ChronosStore is the persistence interface for session summaries.
// Implemented by JSONChronosStore (flat-file) — injectable for testing or upgrade.
type ChronosStore interface {
	Save(summary ChronosSummary) error
	LoadRecent(n int) ([]ChronosSummary, error)
}

// SetStore injects a ChronosStore into the clock. Must be called before first use.
func (c *TemporalClock) SetStore(store ChronosStore) {
	c.mu.Lock()
	defer c.mu.Unlock()
	c.store = store
}

// PersistSession saves the named session's summary to the store and removes it
// from the in-memory map. Safe to call on shutdown or explicit session close.
func (c *TemporalClock) PersistSession(sessionID string) {
	if sessionID == "" {
		return
	}
	c.mu.Lock()
	sess, ok := c.sessions[sessionID]
	if !ok || c.store == nil {
		c.mu.Unlock()
		return
	}
	now := time.Now().UTC()

	// Build event string list from ring buffer
	evStrings := make([]string, len(sess.Events))
	for i, ev := range sess.Events {
		evStrings[i] = fmt.Sprintf("[%s] %s: %s", ev.At.Format("15:04"), ev.Role, ev.Summary)
	}

	// Topic line = first user message (if any)
	topicLine := ""
	for _, ev := range sess.Events {
		if ev.Role == EventRoleUser {
			topicLine = ev.Summary
			break
		}
	}

	summary := ChronosSummary{
		SessionID:    sessionID,
		StartedAt:    sess.StartedAt,
		EndedAt:      now,
		MessageCount: sess.MessageCount,
		TopicLine:    topicLine,
		Events:       evStrings,
	}
	delete(c.sessions, sessionID)
	c.mu.Unlock()

	_ = c.store.Save(summary)
}

// PersistAllSessions flushes every active in-memory session. Call on server shutdown.
func (c *TemporalClock) PersistAllSessions() {
	c.mu.RLock()
	ids := make([]string, 0, len(c.sessions))
	for id := range c.sessions {
		ids = append(ids, id)
	}
	c.mu.RUnlock()
	for _, id := range ids {
		c.PersistSession(id)
	}
}

// ─── FormatForPrompt — updated to include previous sessions ──────────────────

// formatPreviousSessions appends the last N persisted sessions to the temporal block.
func (c *TemporalClock) formatPreviousSessions(now time.Time) string {
	if c.store == nil {
		return ""
	}
	summaries, err := c.store.LoadRecent(3)
	if err != nil || len(summaries) == 0 {
		return ""
	}
	var sb strings.Builder
	sb.WriteString("\nPrevious sessions (reference these when asked about past conversations):\n")
	for _, s := range summaries {
		age := formatDuration(now.Sub(s.EndedAt))
		dur := formatDuration(s.EndedAt.Sub(s.StartedAt))
		line := fmt.Sprintf("  • %s ago (%s, %d msgs)",
			age, dur, s.MessageCount)
		if s.TopicLine != "" {
			line += fmt.Sprintf(" — %q", s.TopicLine)
		}
		sb.WriteString(line + "\n")
	}
	return sb.String()
}

// ─── JSON flat-file ChronosStore ─────────────────────────────────────────────

const chronosDir = ".memory/session_chronos"

// JSONChronosStore persists session summaries as individual JSON files under
// chronosDir. Files are named by EndedAt timestamp for natural sort order.
type JSONChronosStore struct {
	dir string
}

// NewJSONChronosStore creates (or opens) the store at dir.
func NewJSONChronosStore(dir string) (*JSONChronosStore, error) {
	if err := os.MkdirAll(dir, 0755); err != nil {
		return nil, fmt.Errorf("chronos store: mkdir %s: %w", dir, err)
	}
	return &JSONChronosStore{dir: dir}, nil
}

// Save writes the summary as a JSON file. Filename: <EndedAt unix ns>.json
func (s *JSONChronosStore) Save(summary ChronosSummary) error {
	name := fmt.Sprintf("%d.json", summary.EndedAt.UnixNano())
	path := filepath.Join(s.dir, name)
	data, err := json.MarshalIndent(summary, "", "  ")
	if err != nil {
		return err
	}
	return os.WriteFile(path, data, 0644)
}

// LoadRecent returns the n most recent summaries, newest first.
func (s *JSONChronosStore) LoadRecent(n int) ([]ChronosSummary, error) {
	entries, err := os.ReadDir(s.dir)
	if err != nil {
		if os.IsNotExist(err) {
			return nil, nil
		}
		return nil, err
	}
	// Filter to .json files and sort descending (newest filename = highest unix ns)
	var files []string
	for _, e := range entries {
		if !e.IsDir() && strings.HasSuffix(e.Name(), ".json") {
			files = append(files, e.Name())
		}
	}
	sort.Sort(sort.Reverse(sort.StringSlice(files)))

	var results []ChronosSummary
	for _, fname := range files {
		if len(results) >= n {
			break
		}
		data, err := os.ReadFile(filepath.Join(s.dir, fname))
		if err != nil {
			continue
		}
		var sum ChronosSummary
		if err := json.Unmarshal(data, &sum); err != nil {
			continue
		}
		results = append(results, sum)
	}
	return results, nil
}

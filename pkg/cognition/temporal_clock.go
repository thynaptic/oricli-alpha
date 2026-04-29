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
	Timezone     string         // IANA timezone name, e.g. "America/New_York"
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

// SetTimezone stores the user's IANA timezone for a session. Silently ignores
// invalid zone names. Called when the client sends an X-Timezone header.
func (c *TemporalClock) SetTimezone(sessionID, tz string) {
	if sessionID == "" || tz == "" {
		return
	}
	if _, err := time.LoadLocation(tz); err != nil {
		return
	}
	c.mu.Lock()
	defer c.mu.Unlock()
	s, ok := c.sessions[sessionID]
	if !ok {
		return
	}
	s.Timezone = tz
}

// FormatForPrompt returns the temporal awareness block for injection into the
// system prompt. query is the current user message — used to score event
// relevance so the most contextually useful events surface, not just the most
// recent ones.
func (c *TemporalClock) FormatForPrompt(sessionID, query string) string {
	now := time.Now().UTC()
	c.mu.RLock()
	sess := c.sessions[sessionID]
	c.mu.RUnlock()

	var sb strings.Builder
	sb.WriteString("### TEMPORAL AWARENESS\n")
	sb.WriteString(fmt.Sprintf("Current time: %s\n", now.Format("Monday, January 2 2006 — 15:04 UTC")))

	// Local time when the client's timezone is known.
	if sess != nil && sess.Timezone != "" {
		if loc, err := time.LoadLocation(sess.Timezone); err == nil {
			local := now.In(loc)
			sb.WriteString(fmt.Sprintf("Your local time: %s (%s)\n", local.Format("15:04, Monday January 2"), sess.Timezone))
		}
	}

	sb.WriteString(fmt.Sprintf("ORI online since: %s (%s ago)\n",
		c.bootTime.Format("15:04 UTC"),
		formatDuration(now.Sub(c.bootTime)),
	))

	// Gap-aware re-orientation — shown on first message of a new session when
	// the previous session ended more than 4 hours ago.
	if sess != nil && sess.MessageCount == 1 {
		if orient := c.formatReorientation(now); orient != "" {
			sb.WriteString(orient)
		}
	}

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

		// Semantically relevant event timeline — up to 5 events scored against
		// the current query, with recency as the tiebreaker.
		if len(sess.Events) > 0 {
			sb.WriteString("\nRecent activity:\n")
			for _, ev := range selectRelevantEvents(sess.Events, query, 5) {
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
	s := strings.Join(strings.Fields(content), " ")
	if len(s) <= maxChars {
		return s
	}
	s = s[:maxChars]
	if idx := strings.LastIndex(s, " "); idx > maxChars/2 {
		s = s[:idx]
	}
	return s + "…"
}

// formatDuration converts a duration into a human-readable relative string.
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

// selectRelevantEvents picks up to n events from the ring buffer most relevant
// to query, using keyword overlap as the score and recency as the tiebreaker.
// Falls back to pure recency when query is empty or produces no keywords.
func selectRelevantEvents(events []SessionEvent, query string, n int) []SessionEvent {
	if len(events) <= n {
		return events
	}
	queryKWs := temporalKeywords(query)
	if len(queryKWs) == 0 {
		return events[len(events)-n:]
	}

	type scored struct {
		ev    SessionEvent
		score int
		idx   int
	}
	candidates := make([]scored, len(events))
	for i, ev := range events {
		overlap := 0
		for _, ek := range temporalKeywords(ev.Summary) {
			for _, qk := range queryKWs {
				if ek == qk {
					overlap++
				}
			}
		}
		candidates[i] = scored{ev: ev, score: overlap, idx: i}
	}

	sort.Slice(candidates, func(i, j int) bool {
		if candidates[i].score != candidates[j].score {
			return candidates[i].score > candidates[j].score
		}
		return candidates[i].idx > candidates[j].idx // recency tiebreaker
	})

	selected := make([]SessionEvent, 0, n)
	for i := 0; i < n && i < len(candidates); i++ {
		selected = append(selected, candidates[i].ev)
	}
	// Re-sort chronologically for readable display.
	sort.Slice(selected, func(i, j int) bool {
		return selected[i].At.Before(selected[j].At)
	})
	return selected
}

// temporalKeywords extracts lowercase non-trivial words for relevance scoring.
func temporalKeywords(s string) []string {
	stop := map[string]bool{
		"the": true, "a": true, "an": true, "and": true, "or": true,
		"of": true, "in": true, "on": true, "at": true, "to": true,
		"is": true, "are": true, "was": true, "for": true, "with": true,
		"what": true, "how": true, "when": true, "where": true, "why": true,
		"can": true, "you": true, "i": true, "my": true, "me": true,
		"that": true, "this": true, "it": true, "do": true, "did": true,
	}
	words := strings.Fields(strings.ToLower(s))
	out := make([]string, 0, len(words))
	for _, w := range words {
		w = strings.Trim(w, ".,;:!?\"'()")
		if len(w) > 2 && !stop[w] {
			out = append(out, w)
		}
	}
	return out
}

// ─── Cross-session Chronos Persistence ───────────────────────────────────────

// ChronosSummary is the serialisable record of a completed session.
type ChronosSummary struct {
	SessionID    string    `json:"session_id"`
	StartedAt    time.Time `json:"started_at"`
	EndedAt      time.Time `json:"ended_at"`
	MessageCount int       `json:"message_count"`
	TopicLine    string    `json:"topic_line"` // first user message — proxy for session intent
	Synopsis     string    `json:"synopsis"`   // joined user-turn summaries — richer cross-session recall
	Events       []string  `json:"events"`     // 80-char summaries, newest last
}

// ChronosStore is the persistence interface for session summaries.
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

	evStrings := make([]string, len(sess.Events))
	for i, ev := range sess.Events {
		evStrings[i] = fmt.Sprintf("[%s] %s: %s", ev.At.Format("15:04"), ev.Role, ev.Summary)
	}

	topicLine := ""
	var userTurns []string
	for _, ev := range sess.Events {
		if ev.Role == EventRoleUser {
			if topicLine == "" {
				topicLine = ev.Summary
			}
			userTurns = append(userTurns, ev.Summary)
		}
	}

	// Synopsis joins all user-turn summaries so cross-session recall surfaces
	// the full arc of what was discussed, not just the opening line.
	synopsis := strings.Join(userTurns, " · ")
	if len(synopsis) > 200 {
		synopsis = synopsis[:200] + "…"
	}

	summary := ChronosSummary{
		SessionID:    sessionID,
		StartedAt:    sess.StartedAt,
		EndedAt:      now,
		MessageCount: sess.MessageCount,
		TopicLine:    topicLine,
		Synopsis:     synopsis,
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

// formatReorientation returns a prompt line surfacing the most recent previous
// session when resuming after a gap of 4+ hours. Empty string = no re-orientation needed.
func (c *TemporalClock) formatReorientation(now time.Time) string {
	if c.store == nil {
		return ""
	}
	recent, err := c.store.LoadRecent(1)
	if err != nil || len(recent) == 0 {
		return ""
	}
	last := recent[0]
	gap := now.Sub(last.EndedAt)
	if gap < 4*time.Hour {
		return ""
	}

	var sb strings.Builder
	sb.WriteString(fmt.Sprintf("\n↩ Returning after %s", formatDuration(gap)))
	if last.Synopsis != "" {
		sb.WriteString(fmt.Sprintf(" — last covered: %q", last.Synopsis))
	} else if last.TopicLine != "" {
		sb.WriteString(fmt.Sprintf(" — started with: %q", last.TopicLine))
	}
	sb.WriteString(fmt.Sprintf("\n   (%d msgs, ended %s)\n", last.MessageCount, last.EndedAt.Format("Jan 2 at 15:04 UTC")))
	return sb.String()
}

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
		line := fmt.Sprintf("  • %s ago (%s, %d msgs)", age, dur, s.MessageCount)
		if s.Synopsis != "" {
			line += fmt.Sprintf(" — %s", s.Synopsis)
		} else if s.TopicLine != "" {
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

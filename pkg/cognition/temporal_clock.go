package cognition

import (
	"fmt"
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

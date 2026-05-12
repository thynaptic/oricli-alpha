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

// EventKind classifies a session event so temporal recall can reason about the
// arc of work, not just a flat list of chat messages.
type EventKind string

const (
	EventKindMessage    EventKind = "message"
	EventKindIntent     EventKind = "intent"
	EventKindDecision   EventKind = "decision"
	EventKindOpenLoop   EventKind = "open_loop"
	EventKindResolved   EventKind = "resolved"
	EventKindBlocker    EventKind = "blocker"
	EventKindDeployment EventKind = "deployment"
	EventKindTest       EventKind = "test"
	EventKindCorrection EventKind = "correction"
	EventKindPreference EventKind = "preference"
	EventKindCommitment EventKind = "commitment"
)

// CommitmentStatus tracks lifecycle state for time-bound promises.
type CommitmentStatus string

const (
	CommitmentOpen      CommitmentStatus = "open"
	CommitmentDone      CommitmentStatus = "done"
	CommitmentStale     CommitmentStatus = "stale"
	CommitmentCancelled CommitmentStatus = "cancelled"
)

// SessionEvent is one timestamped exchange recorded in the session timeline.
type SessionEvent struct {
	At      time.Time
	Role    EventRole
	Kind    EventKind
	Summary string // first ~80 chars of the content
}

const sessionEventCap = 20 // ring buffer size per session

// TemporalCommitment captures future-facing intent: reminders, deploy-after-test
// promises, next-session followups, and conditional work.
type TemporalCommitment struct {
	ID          string           `json:"id"`
	CreatedAt   time.Time        `json:"created_at"`
	DueAt       *time.Time       `json:"due_at,omitempty"`
	Trigger     string           `json:"trigger,omitempty"`
	Summary     string           `json:"summary"`
	Status      CommitmentStatus `json:"status"`
	SourceEvent string           `json:"source_event"`
}

// TemporalClaimCheck is a lightweight guard against overstating sequence state
// such as claiming a deployment happened when only tests are recorded.
type TemporalClaimCheck struct {
	OK       bool   `json:"ok"`
	Reason   string `json:"reason,omitempty"`
	Evidence string `json:"evidence,omitempty"`
}

// ContinuityLedger is the compact cross-session "what are we doing?" record.
type ContinuityLedger struct {
	UpdatedAt      time.Time            `json:"updated_at"`
	ActiveFocus    string               `json:"active_focus,omitempty"`
	LastDeployment string               `json:"last_deployment,omitempty"`
	LastSmoke      string               `json:"last_smoke,omitempty"`
	OpenLoops      []string             `json:"open_loops,omitempty"`
	Commitments    []TemporalCommitment `json:"commitments,omitempty"`
	NextBestMove   string               `json:"next_best_move,omitempty"`
}

// sessionState holds per-session temporal data.
type sessionState struct {
	StartedAt    time.Time
	LastActivity time.Time
	MessageCount int
	Events       []SessionEvent // ring buffer, newest appended
	Timezone     string         // IANA timezone name, e.g. "America/New_York"
	Decisions    []string
	OpenLoops    []string
	Blockers     []string
	Resolved     []string
	Deployments  []string
	Tests        []string
	Preferences  []string
	Commitments  []TemporalCommitment
}

// TemporalClock is the singleton temporal awareness engine.
type TemporalClock struct {
	bootTime time.Time
	sessions map[string]*sessionState
	store    ChronosStore // optional persistence backend
	ledger   ContinuityLedger
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
	kind := classifyEventKind(role, content)
	eventID := temporalEventID(now, role, summary)
	ev := SessionEvent{At: now, Role: role, Kind: kind, Summary: summary}

	c.mu.Lock()
	s, ok := c.sessions[sessionID]
	if !ok {
		s = &sessionState{StartedAt: now, LastActivity: now}
		c.sessions[sessionID] = s
	}
	s.Events = append(s.Events, ev)
	if len(s.Events) > sessionEventCap {
		s.Events = s.Events[len(s.Events)-sessionEventCap:]
	}
	c.applySessionArc(s, ev)
	if commitment, ok := detectTemporalCommitment(now, eventID, content); ok {
		s.Commitments = appendTemporalCommitment(s.Commitments, commitment)
	}
	c.updateCommitmentLifecycle(s, ev)
	c.updateContinuityLocked(s, now)
	ledger := c.ledger
	c.mu.Unlock()

	c.persistContinuity(ledger)
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

		if arc := formatSessionArc(sess, now); arc != "" {
			sb.WriteString(arc)
		}

		if commitments := formatPendingCommitments(sess.Commitments, now); commitments != "" {
			sb.WriteString(commitments)
		}

		// Semantically relevant event timeline — up to 5 events scored against
		// the current query, with recency as the tiebreaker.
		if len(sess.Events) > 0 {
			sb.WriteString("\nRecent activity:\n")
			for _, ev := range selectRelevantEvents(sess.Events, query, 5) {
				age := formatDuration(now.Sub(ev.At))
				sb.WriteString(fmt.Sprintf("  %s/%s (%s ago): %q\n", ev.Role, ev.Kind, age, ev.Summary))
			}
		}
	} else {
		sb.WriteString("Session: new\n")
	}

	if continuity := c.formatContinuity(now); continuity != "" {
		sb.WriteString(continuity)
	}

	// Previous sessions — cross-boot recall from ChronosStore
	if prev := c.formatPreviousSessions(now); prev != "" {
		sb.WriteString(prev)
	}

	return sb.String()
}

func (c *TemporalClock) applySessionArc(s *sessionState, ev SessionEvent) {
	switch ev.Kind {
	case EventKindDecision:
		s.Decisions = appendCappedUnique(s.Decisions, ev.Summary, 8)
	case EventKindOpenLoop:
		s.OpenLoops = appendCappedUnique(s.OpenLoops, ev.Summary, 10)
	case EventKindBlocker:
		s.Blockers = appendCappedUnique(s.Blockers, ev.Summary, 8)
	case EventKindResolved:
		s.Resolved = appendCappedUnique(s.Resolved, ev.Summary, 8)
		s.OpenLoops = removeRelatedTemporalItems(s.OpenLoops, ev.Summary)
		s.Blockers = removeRelatedTemporalItems(s.Blockers, ev.Summary)
	case EventKindDeployment:
		s.Deployments = appendCappedUnique(s.Deployments, ev.Summary, 8)
	case EventKindTest:
		s.Tests = appendCappedUnique(s.Tests, ev.Summary, 10)
	case EventKindPreference:
		s.Preferences = appendCappedUnique(s.Preferences, ev.Summary, 8)
	case EventKindCommitment:
		s.OpenLoops = appendCappedUnique(s.OpenLoops, ev.Summary, 10)
	}
}

func classifyEventKind(role EventRole, content string) EventKind {
	lower := strings.ToLower(content)
	switch {
	case containsAnyTemporal(lower, "deployed", "deploying", "deployment", "restart/deploy", "restarted", "rolled out", "went live", "live now"):
		return EventKindDeployment
	case containsAnyTemporal(lower, "smoke test", "smoke passed", "tests passed", "test passed", "go test", "verified", "verification passed", "health passed"):
		return EventKindTest
	case containsAnyTemporal(lower, "correction", "correcting", "actually", "not quite", "wrong assumption", "scratch that"):
		return EventKindCorrection
	case containsAnyTemporal(lower, "failed", "failing", "blocked", "blocker", "error", "panic", "crash", "broken", "text file busy"):
		return EventKindBlocker
	case containsAnyTemporal(lower, "fixed", "resolved", "done", "completed", "handled", "clean now", "passes now"):
		return EventKindResolved
	case containsAnyTemporal(lower, "remember", "prefer", "always", "never", "make a note", "from now on"):
		return EventKindPreference
	case containsAnyTemporal(lower, "remind me", "next session", "next time", "today", "tonight", "tomorrow", "next week", "end of day", "eod", "after tests", "after verify", "after verification", "if this fails", "if it fails", "follow up"):
		return EventKindCommitment
	case containsAnyTemporal(lower, "decided", "decision", "we should", "let's", "go ahead", "all yours", "plan is", "best move"):
		return EventKindDecision
	case containsAnyTemporal(lower, "todo", "to do", "next best", "next move", "need to", "needs", "pending", "open loop", "later"):
		return EventKindOpenLoop
	case role == EventRoleUser && containsAnyTemporal(lower, "what if", "can we", "could we", "should we", "how about", "new concept", "new idea"):
		return EventKindIntent
	case role == EventRoleUser && strings.HasSuffix(strings.TrimSpace(content), "?"):
		return EventKindIntent
	default:
		return EventKindMessage
	}
}

func detectTemporalCommitment(now time.Time, eventID, content string) (TemporalCommitment, bool) {
	lower := strings.ToLower(content)
	trigger := ""
	var dueAt *time.Time
	switch {
	case containsAnyTemporal(lower, "today", "tonight", "end of day", "eod"):
		due := now.Truncate(24 * time.Hour).Add(24 * time.Hour).Add(-time.Minute)
		dueAt = &due
		trigger = "today"
	case strings.Contains(lower, "tomorrow"):
		due := now.Add(24 * time.Hour)
		dueAt = &due
		trigger = "tomorrow"
	case strings.Contains(lower, "next week"):
		due := now.Add(7 * 24 * time.Hour)
		dueAt = &due
		trigger = "next_week"
	case containsAnyTemporal(lower, "next session", "next time we talk", "next time"):
		trigger = "next_session"
	case strings.Contains(lower, "remind me"):
		trigger = "reminder"
	case containsAnyTemporal(lower, "after tests", "after test", "after verify", "after verification", "after smoke"):
		trigger = "after_verification"
	case containsAnyTemporal(lower, "if this fails", "if it fails", "if that fails", "if this breaks"):
		trigger = "conditional_failure"
	case containsAnyTemporal(lower, "deploy after", "restart after"):
		trigger = "post_condition_deploy"
	default:
		return TemporalCommitment{}, false
	}
	return TemporalCommitment{
		ID:          "tc_" + sanitizeTemporalID(eventID),
		CreatedAt:   now,
		DueAt:       dueAt,
		Trigger:     trigger,
		Summary:     summarise(content, 120),
		Status:      CommitmentOpen,
		SourceEvent: eventID,
	}, true
}

func (c *TemporalClock) updateCommitmentLifecycle(s *sessionState, ev SessionEvent) {
	for i := range s.Commitments {
		if s.Commitments[i].Status != CommitmentOpen {
			continue
		}
		switch {
		case ev.Kind == EventKindDeployment && containsAnyTemporal(s.Commitments[i].Trigger, "deploy", "verification", "after"):
			s.Commitments[i].Status = CommitmentDone
		case ev.Kind == EventKindTest && containsAnyTemporal(s.Commitments[i].Trigger, "verification", "after"):
			// Verification is necessary but not always sufficient for deploy commitments.
			if !containsAnyTemporal(strings.ToLower(s.Commitments[i].Summary), "deploy", "restart") {
				s.Commitments[i].Status = CommitmentDone
			}
		case ev.Kind == EventKindResolved && temporalOverlap(s.Commitments[i].Summary, ev.Summary) > 0:
			s.Commitments[i].Status = CommitmentDone
		}
	}
	now := time.Now().UTC()
	for i := range s.Commitments {
		if s.Commitments[i].Status == CommitmentOpen && s.Commitments[i].DueAt != nil && now.After(s.Commitments[i].DueAt.Add(2*time.Hour)) {
			s.Commitments[i].Status = CommitmentStale
		}
	}
}

// VerifyTemporalClaim checks whether a response can safely make sequence claims
// like "deployed", "verified", or "resolved" from the recorded event timeline.
func (c *TemporalClock) VerifyTemporalClaim(sessionID, claim string) TemporalClaimCheck {
	c.mu.RLock()
	defer c.mu.RUnlock()

	sess := c.sessions[sessionID]
	if sess == nil {
		return TemporalClaimCheck{OK: true, Reason: "no active temporal session to verify against"}
	}

	lower := strings.ToLower(claim)
	latestDeployment, _ := latestEventOfKind(sess.Events, EventKindDeployment)
	latestTest, testAt := latestEventOfKind(sess.Events, EventKindTest)
	latestBlocker, blockerAt := latestEventOfKind(sess.Events, EventKindBlocker)
	latestResolved, resolvedAt := latestEventOfKind(sess.Events, EventKindResolved)

	if containsAnyTemporal(lower, "deployed", "deployment", "went live", "live now", "restarted", "rolled out") {
		if latestDeployment != "" {
			return TemporalClaimCheck{OK: true, Evidence: latestDeployment}
		}
		if latestTest != "" {
			return TemporalClaimCheck{
				OK:       false,
				Reason:   "verification is recorded, but no deployment/restart event is recorded",
				Evidence: latestTest,
			}
		}
		return TemporalClaimCheck{OK: false, Reason: "no deployment/restart evidence is recorded"}
	}

	if containsAnyTemporal(lower, "tested", "tests passed", "smoke passed", "verified", "verification passed") {
		if latestTest == "" {
			return TemporalClaimCheck{OK: false, Reason: "no test or smoke-verification event is recorded"}
		}
		if !blockerAt.IsZero() && blockerAt.After(testAt) {
			return TemporalClaimCheck{
				OK:       false,
				Reason:   "a blocker is recorded after the latest verification",
				Evidence: latestBlocker,
			}
		}
		return TemporalClaimCheck{OK: true, Evidence: latestTest}
	}

	if containsAnyTemporal(lower, "fixed", "resolved", "done", "completed") {
		if latestResolved != "" && (blockerAt.IsZero() || resolvedAt.After(blockerAt)) {
			return TemporalClaimCheck{OK: true, Evidence: latestResolved}
		}
		if latestBlocker != "" {
			return TemporalClaimCheck{
				OK:       false,
				Reason:   "a blocker is recorded without a later resolution",
				Evidence: latestBlocker,
			}
		}
	}

	return TemporalClaimCheck{OK: true}
}

func formatSessionArc(sess *sessionState, now time.Time) string {
	var sb strings.Builder
	writeList := func(label string, values []string, max int) {
		if len(values) == 0 {
			return
		}
		if sb.Len() == 0 {
			sb.WriteString("\nCurrent session arc:\n")
		}
		sb.WriteString(fmt.Sprintf("  %s: %s\n", label, strings.Join(lastNStrings(values, max), " · ")))
	}

	_ = now
	writeList("Decisions", sess.Decisions, 3)
	writeList("Open loops", sess.OpenLoops, 3)
	writeList("Blockers", sess.Blockers, 2)
	writeList("Resolved", sess.Resolved, 2)
	writeList("Deployments", sess.Deployments, 2)
	writeList("Tests", sess.Tests, 3)
	writeList("Preferences", sess.Preferences, 2)
	return sb.String()
}

func formatPendingCommitments(commitments []TemporalCommitment, now time.Time) string {
	var active []string
	for _, commitment := range commitments {
		status := commitment.Status
		if status == CommitmentOpen && commitment.DueAt != nil && now.After(commitment.DueAt.Add(2*time.Hour)) {
			status = CommitmentStale
		}
		if status != CommitmentOpen && status != CommitmentStale {
			continue
		}
		line := fmt.Sprintf("%s [%s]", commitment.Summary, status)
		if commitment.Trigger != "" {
			line += " trigger=" + commitment.Trigger
		}
		if commitment.DueAt != nil {
			line += " due=" + commitment.DueAt.Format("Jan 2 15:04 UTC")
		}
		active = append(active, line)
	}
	if len(active) == 0 {
		return ""
	}
	if len(active) > 4 {
		active = active[len(active)-4:]
	}
	return "\nPending temporal commitments:\n  - " + strings.Join(active, "\n  - ") + "\n"
}

func (c *TemporalClock) formatContinuity(now time.Time) string {
	c.mu.RLock()
	ledger := c.ledger
	c.mu.RUnlock()

	if ledger.UpdatedAt.IsZero() && ledger.ActiveFocus == "" && len(ledger.OpenLoops) == 0 && len(ledger.Commitments) == 0 {
		return ""
	}

	var sb strings.Builder
	sb.WriteString("\nContinuity ledger:\n")
	if !ledger.UpdatedAt.IsZero() {
		sb.WriteString(fmt.Sprintf("  Updated: %s ago\n", formatDuration(now.Sub(ledger.UpdatedAt))))
	}
	if ledger.ActiveFocus != "" {
		sb.WriteString(fmt.Sprintf("  Active focus: %s\n", ledger.ActiveFocus))
	}
	if ledger.LastDeployment != "" {
		sb.WriteString(fmt.Sprintf("  Last deployment/restart: %s\n", ledger.LastDeployment))
	}
	if ledger.LastSmoke != "" {
		sb.WriteString(fmt.Sprintf("  Last smoke/verification: %s\n", ledger.LastSmoke))
	}
	if ledger.NextBestMove != "" {
		sb.WriteString(fmt.Sprintf("  Next best move: %s\n", ledger.NextBestMove))
	}
	if len(ledger.OpenLoops) > 0 {
		sb.WriteString("  Open loops:\n")
		for _, item := range lastNStrings(ledger.OpenLoops, 5) {
			sb.WriteString("    - " + item + "\n")
		}
	}
	if commitments := formatPendingCommitments(ledger.Commitments, now); commitments != "" {
		sb.WriteString(strings.Replace(commitments, "\nPending temporal commitments:", "  Cross-session commitments:", 1))
	}
	return sb.String()
}

func (c *TemporalClock) updateContinuityLocked(s *sessionState, now time.Time) {
	ledger := c.ledger
	ledger.UpdatedAt = now
	ledger.OpenLoops = mergeCappedUnique(ledger.OpenLoops, s.OpenLoops, 12)
	ledger.Commitments = mergeTemporalCommitments(ledger.Commitments, s.Commitments, 12)

	for _, resolved := range s.Resolved {
		ledger.OpenLoops = removeRelatedTemporalItems(ledger.OpenLoops, resolved)
	}
	if len(s.Deployments) > 0 {
		ledger.LastDeployment = s.Deployments[len(s.Deployments)-1]
	}
	if len(s.Tests) > 0 {
		ledger.LastSmoke = s.Tests[len(s.Tests)-1]
	}
	if len(s.OpenLoops) > 0 {
		ledger.ActiveFocus = s.OpenLoops[len(s.OpenLoops)-1]
	} else if len(s.Decisions) > 0 {
		ledger.ActiveFocus = s.Decisions[len(s.Decisions)-1]
	} else if len(s.Events) > 0 {
		ledger.ActiveFocus = s.Events[len(s.Events)-1].Summary
	}

	ledger.NextBestMove = ""
	for i := len(ledger.Commitments) - 1; i >= 0; i-- {
		if ledger.Commitments[i].Status == CommitmentOpen || ledger.Commitments[i].Status == CommitmentStale {
			ledger.NextBestMove = ledger.Commitments[i].Summary
			break
		}
	}
	if ledger.NextBestMove == "" && len(ledger.OpenLoops) > 0 {
		ledger.NextBestMove = ledger.OpenLoops[len(ledger.OpenLoops)-1]
	}
	c.ledger = ledger
}

func (c *TemporalClock) persistContinuity(ledger ContinuityLedger) {
	if c.store == nil {
		return
	}
	if cs, ok := c.store.(continuityStore); ok {
		_ = cs.SaveContinuity(ledger)
	}
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

// selectRelevantEvents picks up to n events using temporal salience: keyword
// overlap, event kind importance, unresolved-work boost, and recency.
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
		score float64
		idx   int
	}
	candidates := make([]scored, len(events))
	now := time.Now().UTC()
	for i, ev := range events {
		overlap := temporalOverlapFromKeywords(temporalKeywords(ev.Summary), queryKWs)
		score := float64(overlap)*3.0 + temporalKindBoost(ev.Kind) + temporalRecencyBoost(now.Sub(ev.At))
		candidates[i] = scored{ev: ev, score: score, idx: i}
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

func temporalKindBoost(kind EventKind) float64 {
	switch kind {
	case EventKindDeployment:
		return 9
	case EventKindBlocker:
		return 8
	case EventKindDecision:
		return 7
	case EventKindOpenLoop, EventKindCommitment:
		return 6
	case EventKindTest, EventKindCorrection:
		return 5
	case EventKindResolved:
		return 4
	case EventKindPreference:
		return 3
	case EventKindIntent:
		return 2
	default:
		return 0
	}
}

func temporalRecencyBoost(age time.Duration) float64 {
	if age < 0 {
		age = 0
	}
	switch {
	case age < 5*time.Minute:
		return 4
	case age < time.Hour:
		return 3
	case age < 24*time.Hour:
		return 1
	default:
		return 0
	}
}

func appendTemporalCommitment(existing []TemporalCommitment, commitment TemporalCommitment) []TemporalCommitment {
	if commitment.ID == "" {
		commitment.ID = "tc_" + sanitizeTemporalID(commitment.Summary)
	}
	for i := range existing {
		if existing[i].ID == commitment.ID || temporalOverlap(existing[i].Summary, commitment.Summary) >= 3 {
			if existing[i].Status == CommitmentDone || existing[i].Status == CommitmentCancelled {
				return existing
			}
			existing[i] = commitment
			return existing
		}
	}
	existing = append(existing, commitment)
	if len(existing) > 12 {
		existing = existing[len(existing)-12:]
	}
	return existing
}

func mergeTemporalCommitments(dst, src []TemporalCommitment, cap int) []TemporalCommitment {
	for _, commitment := range src {
		dst = appendTemporalCommitment(dst, commitment)
	}
	if len(dst) > cap {
		dst = dst[len(dst)-cap:]
	}
	return dst
}

func appendCappedUnique(values []string, value string, cap int) []string {
	value = strings.TrimSpace(value)
	if value == "" {
		return values
	}
	out := values[:0]
	for _, existing := range values {
		if strings.EqualFold(existing, value) {
			continue
		}
		out = append(out, existing)
	}
	out = append(out, value)
	if len(out) > cap {
		out = out[len(out)-cap:]
	}
	return out
}

func mergeCappedUnique(dst, src []string, cap int) []string {
	for _, item := range src {
		dst = appendCappedUnique(dst, item, cap)
	}
	return dst
}

func removeRelatedTemporalItems(items []string, summary string) []string {
	if len(items) == 0 {
		return items
	}
	out := items[:0]
	for _, item := range items {
		if strings.EqualFold(item, summary) || temporalOverlap(item, summary) >= 2 {
			continue
		}
		out = append(out, item)
	}
	return out
}

func containsAnyTemporal(s string, tokens ...string) bool {
	lower := strings.ToLower(s)
	for _, token := range tokens {
		if strings.Contains(lower, strings.ToLower(token)) {
			return true
		}
	}
	return false
}

func temporalOverlap(a, b string) int {
	return temporalOverlapFromKeywords(temporalKeywords(a), temporalKeywords(b))
}

func temporalOverlapFromKeywords(a, b []string) int {
	if len(a) == 0 || len(b) == 0 {
		return 0
	}
	seen := make(map[string]struct{}, len(a))
	for _, word := range a {
		seen[word] = struct{}{}
	}
	counted := make(map[string]struct{})
	overlap := 0
	for _, word := range b {
		if _, ok := seen[word]; !ok {
			continue
		}
		if _, already := counted[word]; already {
			continue
		}
		counted[word] = struct{}{}
		overlap++
	}
	return overlap
}

func temporalEventID(now time.Time, role EventRole, summary string) string {
	return fmt.Sprintf("%d_%s_%s", now.UnixNano(), role, sanitizeTemporalID(summary))
}

func sanitizeTemporalID(s string) string {
	lower := strings.ToLower(s)
	var b strings.Builder
	lastUnderscore := false
	for _, r := range lower {
		isAlphaNum := (r >= 'a' && r <= 'z') || (r >= '0' && r <= '9')
		if isAlphaNum {
			b.WriteRune(r)
			lastUnderscore = false
			continue
		}
		if !lastUnderscore {
			b.WriteByte('_')
			lastUnderscore = true
		}
	}
	out := strings.Trim(b.String(), "_")
	if len(out) > 64 {
		out = out[:64]
		out = strings.Trim(out, "_")
	}
	if out == "" {
		return "event"
	}
	return out
}

func lastNStrings(values []string, n int) []string {
	if len(values) <= n {
		return append([]string(nil), values...)
	}
	return append([]string(nil), values[len(values)-n:]...)
}

func latestEventOfKind(events []SessionEvent, kind EventKind) (string, time.Time) {
	for i := len(events) - 1; i >= 0; i-- {
		if events[i].Kind == kind {
			return events[i].Summary, events[i].At
		}
	}
	return "", time.Time{}
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
	SessionID    string               `json:"session_id"`
	StartedAt    time.Time            `json:"started_at"`
	EndedAt      time.Time            `json:"ended_at"`
	MessageCount int                  `json:"message_count"`
	TopicLine    string               `json:"topic_line"` // first user message — proxy for session intent
	Synopsis     string               `json:"synopsis"`   // joined user-turn summaries — richer cross-session recall
	Events       []string             `json:"events"`     // 80-char summaries, newest last
	Decisions    []string             `json:"decisions,omitempty"`
	OpenLoops    []string             `json:"open_loops,omitempty"`
	Blockers     []string             `json:"blockers,omitempty"`
	Resolved     []string             `json:"resolved,omitempty"`
	Deployments  []string             `json:"deployments,omitempty"`
	Tests        []string             `json:"tests,omitempty"`
	Preferences  []string             `json:"preferences,omitempty"`
	Commitments  []TemporalCommitment `json:"commitments,omitempty"`
}

// ChronosStore is the persistence interface for session summaries.
type ChronosStore interface {
	Save(summary ChronosSummary) error
	LoadRecent(n int) ([]ChronosSummary, error)
}

type continuityStore interface {
	SaveContinuity(ledger ContinuityLedger) error
	LoadContinuity() (ContinuityLedger, error)
}

// SetStore injects a ChronosStore into the clock. Must be called before first use.
func (c *TemporalClock) SetStore(store ChronosStore) {
	c.mu.Lock()
	defer c.mu.Unlock()
	c.store = store
	if cs, ok := store.(continuityStore); ok {
		if ledger, err := cs.LoadContinuity(); err == nil {
			c.ledger = ledger
		}
	}
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
		Decisions:    append([]string(nil), sess.Decisions...),
		OpenLoops:    append([]string(nil), sess.OpenLoops...),
		Blockers:     append([]string(nil), sess.Blockers...),
		Resolved:     append([]string(nil), sess.Resolved...),
		Deployments:  append([]string(nil), sess.Deployments...),
		Tests:        append([]string(nil), sess.Tests...),
		Preferences:  append([]string(nil), sess.Preferences...),
		Commitments:  append([]TemporalCommitment(nil), sess.Commitments...),
	}
	delete(c.sessions, sessionID)
	c.updateContinuityLocked(sess, now)
	ledger := c.ledger
	c.mu.Unlock()

	_ = c.store.Save(summary)
	c.persistContinuity(ledger)
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
const continuityLedgerFile = "continuity.json"

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

// SaveContinuity writes the cross-session continuity ledger.
func (s *JSONChronosStore) SaveContinuity(ledger ContinuityLedger) error {
	path := filepath.Join(s.dir, continuityLedgerFile)
	data, err := json.MarshalIndent(ledger, "", "  ")
	if err != nil {
		return err
	}
	return os.WriteFile(path, data, 0644)
}

// LoadContinuity reads the cross-session continuity ledger when present.
func (s *JSONChronosStore) LoadContinuity() (ContinuityLedger, error) {
	path := filepath.Join(s.dir, continuityLedgerFile)
	data, err := os.ReadFile(path)
	if err != nil {
		if os.IsNotExist(err) {
			return ContinuityLedger{}, nil
		}
		return ContinuityLedger{}, err
	}
	var ledger ContinuityLedger
	if err := json.Unmarshal(data, &ledger); err != nil {
		return ContinuityLedger{}, err
	}
	return ledger, nil
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
		if !e.IsDir() && e.Name() != continuityLedgerFile && strings.HasSuffix(e.Name(), ".json") {
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

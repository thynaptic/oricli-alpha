package cognition

import (
	"sort"
	"strings"
)

type TemporalCoordinateRequest struct {
	Surface     string                 `json:"surface,omitempty"`
	Horizon     string                 `json:"horizon,omitempty"`
	Energy      string                 `json:"energy,omitempty"`
	Available   []TemporalWindow       `json:"available,omitempty"`
	FixedEvents []TemporalFixedEvent   `json:"fixed_events,omitempty"`
	Tasks       []TemporalTask         `json:"tasks,omitempty"`
	Preferences TemporalPreferences    `json:"preferences,omitempty"`
	Metadata    map[string]interface{} `json:"metadata,omitempty"`
}

type TemporalWindow struct {
	Label   string `json:"label,omitempty"`
	Start   string `json:"start,omitempty"`
	End     string `json:"end,omitempty"`
	Minutes int    `json:"minutes,omitempty"`
	Energy  string `json:"energy,omitempty"`
}

type TemporalFixedEvent struct {
	Title   string `json:"title,omitempty"`
	Start   string `json:"start,omitempty"`
	End     string `json:"end,omitempty"`
	Minutes int    `json:"minutes,omitempty"`
}

type TemporalTask struct {
	ID           string   `json:"id,omitempty"`
	Title        string   `json:"title,omitempty"`
	Project      string   `json:"project,omitempty"`
	Minutes      int      `json:"minutes,omitempty"`
	DueHint      string   `json:"due_hint,omitempty"`
	Energy       string   `json:"energy,omitempty"`
	Importance   string   `json:"importance,omitempty"`
	Status       string   `json:"status,omitempty"`
	Dependencies []string `json:"dependencies,omitempty"`
}

type TemporalPreferences struct {
	MaxBlocks         int  `json:"max_blocks,omitempty"`
	ProtectFocus      bool `json:"protect_focus,omitempty"`
	PreferShortStarts bool `json:"prefer_short_starts,omitempty"`
}

type TemporalCoordinationPlan struct {
	Surface       string                         `json:"surface"`
	Horizon       string                         `json:"horizon"`
	Summary       string                         `json:"summary"`
	Now           []TemporalTaskCandidate        `json:"now,omitempty"`
	Next          []TemporalTaskCandidate        `json:"next,omitempty"`
	Later         []TemporalTaskCandidate        `json:"later,omitempty"`
	Schedule      []TemporalScheduleBlock        `json:"schedule,omitempty"`
	Conflicts     []TemporalCoordinationConflict `json:"conflicts,omitempty"`
	Coordination  TemporalCoordinationHints      `json:"coordination"`
	MemorySeeds   []QuestMemorySeed              `json:"memory_seeds,omitempty"`
	OpenQuestions []string                       `json:"open_questions,omitempty"`
	Guardrails    []string                       `json:"guardrails"`
}

type TemporalTaskCandidate struct {
	ID       string   `json:"id"`
	Title    string   `json:"title"`
	Project  string   `json:"project,omitempty"`
	Minutes  int      `json:"minutes"`
	DueHint  string   `json:"due_hint,omitempty"`
	Why      string   `json:"why"`
	Risks    []string `json:"risks,omitempty"`
	Blocked  bool     `json:"blocked"`
	NextMove string   `json:"next_move"`
}

type TemporalScheduleBlock struct {
	WindowLabel string   `json:"window_label"`
	TaskID      string   `json:"task_id"`
	Title       string   `json:"title"`
	Minutes     int      `json:"minutes"`
	Energy      string   `json:"energy"`
	DoneSignal  string   `json:"done_signal"`
	Notes       []string `json:"notes,omitempty"`
}

type TemporalCoordinationConflict struct {
	Type       string `json:"type"`
	Title      string `json:"title"`
	Resolution string `json:"resolution"`
}

type TemporalCoordinationHints struct {
	Chronos    []string `json:"chronos"`
	GoalDAG    []string `json:"goal_dag"`
	Memory     []string `json:"memory"`
	Surface    []string `json:"surface"`
	Automation []string `json:"automation"`
}

// CoordinateTemporalWork arbitrates tasks against available attention windows
// and returns a proposed order, not a calendar mutation.
func CoordinateTemporalWork(req TemporalCoordinateRequest) TemporalCoordinationPlan {
	req = normalizeTemporalRequest(req)
	candidates := temporalTaskCandidates(req)
	now, next, later := bucketTemporalCandidates(candidates)
	schedule := buildTemporalSchedule(req, append(append([]TemporalTaskCandidate{}, now...), next...))
	conflicts := detectTemporalCoordinationConflicts(req, candidates, schedule)

	return TemporalCoordinationPlan{
		Surface:   normalizeQuestSurface(req.Surface),
		Horizon:   firstNonEmpty(req.Horizon, "today"),
		Summary:   summarizeTemporalPlan(req, now, next, later, conflicts),
		Now:       now,
		Next:      next,
		Later:     later,
		Schedule:  schedule,
		Conflicts: conflicts,
		Coordination: TemporalCoordinationHints{
			Chronos: []string{
				"Treat schedule blocks as proposals until a calendar/task write succeeds.",
				"Decay blocks when the horizon passes or fixed events change.",
			},
			GoalDAG: []string{
				"Attach blocked tasks to dependency nodes instead of repeatedly rescheduling them.",
				"Promote high-importance tasks into active goal tracks only after user confirmation.",
			},
			Memory: []string{
				"Remember recurring overload patterns, preferred focus windows, and repeated blockers.",
			},
			Surface: temporalSurfaceHints(req.Surface),
			Automation: []string{
				"Autonomous calendar moves require explicit permission, conflict checks, and rollback path.",
				"Low-risk automation can draft schedule proposals and owner check-ins.",
			},
		},
		MemorySeeds:   temporalMemorySeeds(req, now, conflicts),
		OpenQuestions: temporalOpenQuestions(req, conflicts),
		Guardrails: []string{
			"Do not claim calendar, task, or reminder changes happened unless a tool confirms it.",
			"Prefer rescheduling or shrinking work over overbooking attention.",
			"Keep fixed events and human commitments higher priority than generated task blocks.",
		},
	}
}

func normalizeTemporalRequest(req TemporalCoordinateRequest) TemporalCoordinateRequest {
	req.Surface = normalizeQuestSurface(req.Surface)
	req.Horizon = cleanPlanningText(firstNonEmpty(req.Horizon, "today"))
	req.Energy = strings.ToLower(strings.TrimSpace(firstNonEmpty(req.Energy, "medium")))
	if req.Preferences.MaxBlocks <= 0 {
		req.Preferences.MaxBlocks = 5
	}
	if req.Preferences.MaxBlocks > 8 {
		req.Preferences.MaxBlocks = 8
	}
	for i := range req.Available {
		req.Available[i].Label = cleanPlanningText(firstNonEmpty(req.Available[i].Label, req.Available[i].Start, "available window"))
		req.Available[i].Energy = strings.ToLower(strings.TrimSpace(firstNonEmpty(req.Available[i].Energy, req.Energy)))
		if req.Available[i].Minutes <= 0 {
			req.Available[i].Minutes = inferTemporalMinutes(req.Available[i].Start, req.Available[i].End, 30)
		}
	}
	if len(req.Available) == 0 {
		req.Available = []TemporalWindow{{Label: "next available focus window", Minutes: 30, Energy: req.Energy}}
	}
	for i := range req.Tasks {
		req.Tasks[i].Title = cleanPlanningText(firstNonEmpty(req.Tasks[i].Title, "Untitled task"))
		req.Tasks[i].Project = cleanPlanningText(req.Tasks[i].Project)
		req.Tasks[i].DueHint = cleanPlanningText(req.Tasks[i].DueHint)
		req.Tasks[i].Energy = strings.ToLower(strings.TrimSpace(firstNonEmpty(req.Tasks[i].Energy, "medium")))
		req.Tasks[i].Importance = strings.ToLower(strings.TrimSpace(req.Tasks[i].Importance))
		req.Tasks[i].Status = strings.ToLower(strings.TrimSpace(req.Tasks[i].Status))
		if req.Tasks[i].Minutes <= 0 {
			req.Tasks[i].Minutes = 25
		}
		if req.Tasks[i].ID == "" {
			req.Tasks[i].ID = "tmp_" + stableBehaviorID(req.Tasks[i].Title)
		}
	}
	if len(req.Tasks) == 0 {
		req.Tasks = []TemporalTask{{ID: "tmp_clarify", Title: "Clarify what needs time", Minutes: 10, Energy: "low"}}
	}
	for i := range req.FixedEvents {
		req.FixedEvents[i].Title = cleanPlanningText(firstNonEmpty(req.FixedEvents[i].Title, "fixed event"))
		if req.FixedEvents[i].Minutes <= 0 {
			req.FixedEvents[i].Minutes = inferTemporalMinutes(req.FixedEvents[i].Start, req.FixedEvents[i].End, 30)
		}
	}
	return req
}

func temporalTaskCandidates(req TemporalCoordinateRequest) []TemporalTaskCandidate {
	out := make([]TemporalTaskCandidate, 0, len(req.Tasks))
	for _, task := range req.Tasks {
		if task.Status == "done" || task.Status == "completed" {
			continue
		}
		blocked := len(task.Dependencies) > 0 || containsPlanningAny(strings.ToLower(task.Status), "blocked", "waiting")
		out = append(out, TemporalTaskCandidate{
			ID:       task.ID,
			Title:    task.Title,
			Project:  task.Project,
			Minutes:  task.Minutes,
			DueHint:  task.DueHint,
			Why:      temporalWhy(task),
			Risks:    temporalRisks(task, req),
			Blocked:  blocked,
			NextMove: temporalNextMove(task, blocked),
		})
	}
	sort.SliceStable(out, func(i, j int) bool {
		return temporalPriority(req.Tasks, out[i]) > temporalPriority(req.Tasks, out[j])
	})
	return out
}

func bucketTemporalCandidates(candidates []TemporalTaskCandidate) ([]TemporalTaskCandidate, []TemporalTaskCandidate, []TemporalTaskCandidate) {
	var now, next, later []TemporalTaskCandidate
	for _, c := range candidates {
		switch {
		case c.Blocked:
			later = append(later, c)
		case containsPlanningAny(strings.ToLower(c.DueHint+" "+c.Why), "today", "urgent", "asap", "high"):
			now = append(now, c)
		case len(now) < 2:
			now = append(now, c)
		case len(next) < 4:
			next = append(next, c)
		default:
			later = append(later, c)
		}
	}
	return now, next, later
}

func buildTemporalSchedule(req TemporalCoordinateRequest, candidates []TemporalTaskCandidate) []TemporalScheduleBlock {
	var blocks []TemporalScheduleBlock
	used := map[string]bool{}
	for _, window := range req.Available {
		remaining := window.Minutes
		for _, c := range candidates {
			if used[c.ID] || c.Blocked || remaining <= 0 || len(blocks) >= req.Preferences.MaxBlocks {
				continue
			}
			mins := c.Minutes
			if mins > remaining {
				if req.Preferences.PreferShortStarts || remaining >= 10 {
					mins = remaining
				} else {
					continue
				}
			}
			blocks = append(blocks, TemporalScheduleBlock{
				WindowLabel: window.Label,
				TaskID:      c.ID,
				Title:       c.Title,
				Minutes:     mins,
				Energy:      firstNonEmpty(window.Energy, "medium"),
				DoneSignal:  temporalDoneSignal(c.Title, mins, c.Minutes),
				Notes:       temporalBlockNotes(req, c, mins),
			})
			remaining -= mins
			used[c.ID] = true
		}
	}
	return blocks
}

func detectTemporalCoordinationConflicts(req TemporalCoordinateRequest, candidates []TemporalTaskCandidate, schedule []TemporalScheduleBlock) []TemporalCoordinationConflict {
	var conflicts []TemporalCoordinationConflict
	totalTaskMinutes := 0
	for _, c := range candidates {
		if !c.Blocked {
			totalTaskMinutes += c.Minutes
		}
	}
	totalAvailable := 0
	for _, w := range req.Available {
		totalAvailable += w.Minutes
	}
	for _, ev := range req.FixedEvents {
		totalAvailable -= ev.Minutes
	}
	if totalTaskMinutes > totalAvailable && totalAvailable > 0 {
		conflicts = append(conflicts, TemporalCoordinationConflict{
			Type:       "capacity",
			Title:      "Planned work exceeds available attention",
			Resolution: "Shrink, defer, or split lower-priority tasks before writing anything to a calendar.",
		})
	}
	for _, c := range candidates {
		if c.Blocked {
			conflicts = append(conflicts, TemporalCoordinationConflict{
				Type:       "dependency",
				Title:      c.Title,
				Resolution: "Resolve the dependency before assigning focus time.",
			})
		}
	}
	if len(schedule) == 0 {
		conflicts = append(conflicts, TemporalCoordinationConflict{Type: "schedule", Title: "No viable task block", Resolution: "Create one small clarification block instead of silently failing."})
	}
	if len(conflicts) > 6 {
		return conflicts[:6]
	}
	return conflicts
}

func temporalPriority(tasks []TemporalTask, candidate TemporalTaskCandidate) int {
	score := 0
	for _, task := range tasks {
		if task.ID != candidate.ID {
			continue
		}
		lower := strings.ToLower(task.DueHint + " " + task.Importance + " " + task.Title)
		if containsPlanningAny(lower, "today", "asap", "urgent") {
			score += 40
		}
		if containsPlanningAny(lower, "high", "important", "client", "customer") {
			score += 25
		}
		if task.Minutes <= 15 {
			score += 10
		}
		if len(task.Dependencies) > 0 {
			score -= 50
		}
		break
	}
	return score
}

func temporalWhy(task TemporalTask) string {
	lower := strings.ToLower(task.DueHint + " " + task.Importance + " " + task.Title)
	switch {
	case containsPlanningAny(lower, "today", "asap", "urgent"):
		return "Time-sensitive and should be placed before softer work."
	case containsPlanningAny(lower, "client", "customer", "high", "important"):
		return "High-value work that should not be lost in the task pile."
	case len(task.Dependencies) > 0:
		return "Blocked until dependency is resolved."
	default:
		return "Useful work that needs an explicit attention slot."
	}
}

func temporalRisks(task TemporalTask, req TemporalCoordinateRequest) []string {
	var risks []string
	if task.Minutes > 60 {
		risks = append(risks, "large block may need splitting")
	}
	if len(task.Dependencies) > 0 {
		risks = append(risks, "dependency unresolved")
	}
	if req.Energy == "low" && task.Energy == "high" {
		risks = append(risks, "energy mismatch")
	}
	return risks
}

func temporalNextMove(task TemporalTask, blocked bool) string {
	if blocked {
		return "Name the dependency owner or unblocker."
	}
	if task.Minutes > 45 {
		return "Split into the first visible 25-minute block."
	}
	return "Place in the next compatible attention window."
}

func temporalDoneSignal(title string, minutes int, fullMinutes int) string {
	if minutes < fullMinutes {
		return "A partial start exists and the remaining work is explicit."
	}
	return "The task has a visible output, decision, or blocker note."
}

func temporalBlockNotes(req TemporalCoordinateRequest, c TemporalTaskCandidate, mins int) []string {
	var notes []string
	if mins < c.Minutes {
		notes = append(notes, "partial block")
	}
	if req.Preferences.ProtectFocus {
		notes = append(notes, "protect from non-urgent interrupts")
	}
	return notes
}

func summarizeTemporalPlan(req TemporalCoordinateRequest, now []TemporalTaskCandidate, next []TemporalTaskCandidate, later []TemporalTaskCandidate, conflicts []TemporalCoordinationConflict) string {
	return sentenceCase(firstNonEmpty(req.Horizon, "today")) + " coordination produced " +
		intToMomentumString(len(now)) + " now items, " +
		intToMomentumString(len(next)) + " next items, " +
		intToMomentumString(len(later)) + " later items, and " +
		intToMomentumString(len(conflicts)) + " conflicts."
}

func temporalMemorySeeds(req TemporalCoordinateRequest, now []TemporalTaskCandidate, conflicts []TemporalCoordinationConflict) []QuestMemorySeed {
	var seeds []QuestMemorySeed
	if len(now) > 0 {
		seeds = append(seeds, QuestMemorySeed{Key: "temporal_next_focus", Value: now[0].Title, Importance: 0.74})
	}
	if req.Energy != "" {
		seeds = append(seeds, QuestMemorySeed{Key: "temporal_energy_context", Value: req.Energy, Importance: 0.54})
	}
	if len(conflicts) > 0 {
		seeds = append(seeds, QuestMemorySeed{Key: "temporal_conflict_pattern", Value: conflicts[0].Type, Importance: 0.66})
	}
	return seeds
}

func temporalOpenQuestions(req TemporalCoordinateRequest, conflicts []TemporalCoordinationConflict) []string {
	var qs []string
	if len(req.Available) == 0 {
		qs = append(qs, "What attention windows are actually available?")
	}
	for _, conflict := range conflicts {
		if conflict.Type == "dependency" {
			qs = append(qs, "Who can resolve the blocked dependency?")
			break
		}
	}
	if len(req.Tasks) == 0 {
		qs = append(qs, "What work should ORI coordinate?")
	}
	return qs
}

func temporalSurfaceHints(surface string) []string {
	switch normalizeQuestSurface(surface) {
	case "studio":
		return []string{"Prioritize customer commitments, owner follow-ups, and operator focus protection."}
	case "dev":
		return []string{"Prioritize build blockers, review windows, and implementation batches."}
	case "home":
		return []string{"Prioritize household commitments, energy-aware starts, and low-friction reminders."}
	default:
		return []string{"Keep the plan as proposed coordination until a product surface persists it."}
	}
}

func inferTemporalMinutes(start string, end string, fallback int) int {
	if start == "" || end == "" {
		return fallback
	}
	return fallback
}

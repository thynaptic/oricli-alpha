package cognition

import (
	"regexp"
	"strings"
)

// QuestScaffoldRequest turns a vague improvement goal into a persistent,
// surface-neutral guided effort system.
type QuestScaffoldRequest struct {
	Goal        string              `json:"goal"`
	Notes       string              `json:"notes,omitempty"`
	Surface     string              `json:"surface,omitempty"`
	Constraints []string            `json:"constraints,omitempty"`
	Preferences PlanningPreferences `json:"preferences,omitempty"`
}

type QuestScaffold struct {
	ID               string                `json:"id"`
	Name             string                `json:"name"`
	Surface          string                `json:"surface,omitempty"`
	Role             QuestRole             `json:"role"`
	CurrentObjective string                `json:"current_objective"`
	FirstAction      PlanningStep          `json:"first_action"`
	Milestones       []QuestMilestone      `json:"milestones"`
	Rhythm           QuestRhythm           `json:"rhythm"`
	Workspace        QuestWorkspace        `json:"workspace"`
	Progress         QuestProgressModel    `json:"progress"`
	Review           QuestReviewSchedule   `json:"review"`
	MemorySeeds      []QuestMemorySeed     `json:"memory_seeds,omitempty"`
	Integration      QuestIntegrationHints `json:"integration"`
	Governance       []string              `json:"governance,omitempty"`
}

type QuestRole struct {
	Label     string `json:"label"`
	Rationale string `json:"rationale"`
}

type QuestMilestone struct {
	Title      string         `json:"title"`
	Intent     string         `json:"intent"`
	Actions    []PlanningStep `json:"actions"`
	DoneSignal string         `json:"done_signal"`
}

type QuestRhythm struct {
	DailyMinutes int      `json:"daily_minutes"`
	WeeklyReview string   `json:"weekly_review"`
	Cadence      []string `json:"cadence"`
}

type QuestWorkspace struct {
	TemplateName string   `json:"template_name"`
	Sections     []string `json:"sections"`
	Artifacts    []string `json:"artifacts"`
}

type QuestProgressModel struct {
	Track     []string `json:"track"`
	Avoid     []string `json:"avoid"`
	ToneGuard string   `json:"tone_guard"`
}

type QuestReviewSchedule struct {
	NextReviewInDays int      `json:"next_review_in_days"`
	Questions        []string `json:"questions"`
	AdaptationRules  []string `json:"adaptation_rules"`
}

type QuestMemorySeed struct {
	Key        string  `json:"key"`
	Value      string  `json:"value"`
	Importance float64 `json:"importance"`
}

type QuestIntegrationHints struct {
	Memory     []string `json:"memory"`
	Chronos    []string `json:"chronos"`
	GoalDaemon []string `json:"goal_daemon"`
	PAD        []string `json:"pad,omitempty"`
}

// BuildQuestScaffold extracts the Cajun Koi-style primitive without copying
// its academy skin: identity, first action, visible progress, and review.
func BuildQuestScaffold(req QuestScaffoldRequest) QuestScaffold {
	goal := cleanPlanningText(firstNonEmpty(req.Goal, req.Notes, "Build a better operating system"))
	prefs := normalizePlanningPreferences(req.Preferences)
	if prefs.MaxVisibleSteps <= 0 || prefs.MaxVisibleSteps > 4 {
		prefs.MaxVisibleSteps = 4
	}

	plan := BuildPlanningPlan(PlanningRequest{
		Goal:        goal,
		Notes:       req.Notes,
		Constraints: req.Constraints,
		Preferences: prefs,
	})
	role := inferQuestRole(goal, req.Surface)
	milestones := buildQuestMilestones(plan, prefs)
	first := plan.Steps[0]

	return QuestScaffold{
		ID:               "quest_" + stableQuestID(goal),
		Name:             questName(goal),
		Surface:          normalizeQuestSurface(req.Surface),
		Role:             role,
		CurrentObjective: plan.Objective,
		FirstAction:      first,
		Milestones:       milestones,
		Rhythm:           buildQuestRhythm(prefs),
		Workspace:        buildQuestWorkspace(goal, req.Surface),
		Progress: QuestProgressModel{
			Track: []string{
				"starts",
				"completed repetitions",
				"recovery after missed days",
				"blockers removed",
				"milestone evidence",
			},
			Avoid: []string{
				"shame-based streak pressure",
				"decorative badge spam",
				"large static plans with no review loop",
			},
			ToneGuard: "Make effort visible without turning missed days into identity damage.",
		},
		Review: QuestReviewSchedule{
			NextReviewInDays: 7,
			Questions: []string{
				"What got easier to start?",
				"Where did friction show up repeatedly?",
				"Which action should shrink, move, or disappear?",
				"What evidence proves the system is helping?",
			},
			AdaptationRules: []string{
				"If the first action is skipped twice, split it into a two-minute setup step.",
				"If the user completes actions but avoids review, shorten the review to one question.",
				"If blockers repeat, generate a blocker-removal milestone before adding more work.",
			},
		},
		MemorySeeds: []QuestMemorySeed{
			{Key: "active_improvement_goal", Value: goal, Importance: 0.82},
			{Key: "quest_role", Value: role.Label, Importance: 0.68},
			{Key: "quest_first_action", Value: first.Title, Importance: 0.74},
		},
		Integration: QuestIntegrationHints{
			Memory: []string{
				"Store the active goal, role label, first action, recurring blockers, and completed evidence.",
				"Update memory after reviews rather than every checkbox.",
			},
			Chronos: []string{
				"Schedule the first review seven days after quest creation.",
				"Mark stale quests when no progress evidence appears across two review windows.",
			},
			GoalDaemon: []string{
				"Register milestones as a lightweight goal DAG only after user confirmation.",
				"Advance on evidence of effort, not only final outcomes.",
			},
			PAD: []string{
				"Dispatch specialist agents for curriculum, schedule, explanation, or blocker diagnosis when the domain requires it.",
			},
		},
		Governance: []string{
			"Do not claim persistence, reminders, or community accountability happened until a client or tool confirms it.",
			"Use adult role language; avoid childish fantasy unless the user explicitly prefers it.",
			"Keep the scaffold surface-neutral and let products decide what to persist or display.",
		},
	}
}

func buildQuestMilestones(plan PlanningPlan, prefs PlanningPreferences) []QuestMilestone {
	steps := append([]PlanningStep(nil), plan.Steps...)
	if len(steps) == 0 {
		steps = []PlanningStep{{Title: "Start with a two-minute setup", Minutes: 2, Energy: "low", DoneSignal: "The first artifact is open."}}
	}
	if len(steps) > 4 {
		steps = steps[:4]
	}

	return []QuestMilestone{
		{
			Title:      "Stabilize the start",
			Intent:     "Lower activation energy until the work can begin without redesigning the whole system.",
			Actions:    []PlanningStep{steps[0]},
			DoneSignal: "The user has completed one concrete start and knows what starting looks like.",
		},
		{
			Title:  "Build the repeatable loop",
			Intent: "Convert useful actions into a rhythm the user can repeat and inspect.",
			Actions: []PlanningStep{
				{Title: "Repeat the smallest useful action three times", Minutes: minNonZero(prefs.PreferredStepMins, 15), Energy: "medium", DoneSignal: "Three repetitions are logged with short notes."},
				{Title: "Name the blocker that made a repetition harder", Minutes: 5, Energy: "low", DoneSignal: "One blocker is written in plain language."},
			},
			DoneSignal: "A basic action rhythm and blocker record exist.",
		},
		{
			Title:  "Prove progress",
			Intent: "Make effort visible enough that the user can trust the system and adjust it.",
			Actions: []PlanningStep{
				{Title: "Collect one artifact or metric that proves movement", Minutes: 10, Energy: "low", DoneSignal: "A visible artifact, metric, or before/after note exists."},
				{Title: "Run the first review and shrink one friction point", Minutes: 15, Energy: "medium", DoneSignal: "The next version of the quest is simpler or sharper."},
			},
			DoneSignal: "The quest has evidence of progress and one adaptation decision.",
		},
	}
}

func inferQuestRole(goal, surface string) QuestRole {
	lower := strings.ToLower(goal + " " + surface)
	switch {
	case containsPlanningAny(lower, "study", "exam", "learn", "course", "class", "certification"):
		return QuestRole{Label: "Practitioner", Rationale: "The goal needs repeated skill practice, not more advice."}
	case containsPlanningAny(lower, "code", "build", "ship", "developer", "dev"):
		return QuestRole{Label: "Builder", Rationale: "The goal moves through visible implementation artifacts."}
	case containsPlanningAny(lower, "business", "sales", "customer", "operator", "studio"):
		return QuestRole{Label: "Operator", Rationale: "The goal benefits from calm execution loops and observable business progress."}
	case containsPlanningAny(lower, "maintain", "routine", "house", "home", "health", "workout"):
		return QuestRole{Label: "Maintainer", Rationale: "The goal depends on steady upkeep and recovery after missed days."}
	default:
		return QuestRole{Label: "Apprentice", Rationale: "The goal is still becoming specific, so the first identity is learning-through-action."}
	}
}

func buildQuestRhythm(prefs PlanningPreferences) QuestRhythm {
	mins := prefs.PreferredStepMins
	if mins <= 0 {
		mins = 20
	}
	if prefs.OverwhelmSensitive && mins > 20 {
		mins = 20
	}
	return QuestRhythm{
		DailyMinutes: mins,
		WeeklyReview: "One short review every seven days: keep, shrink, move, or remove.",
		Cadence: []string{
			"Daily: complete or prepare one visible action.",
			"After each action: log one sentence of evidence.",
			"Weekly: review friction and adjust the next loop.",
		},
	}
}

func buildQuestWorkspace(goal, surface string) QuestWorkspace {
	sections := []string{"Current objective", "Next action", "Milestones", "Evidence log", "Blockers", "Review notes"}
	artifacts := []string{"quest brief", "daily action log", "blocker list", "weekly review packet"}
	lower := strings.ToLower(goal + " " + surface)
	switch {
	case containsPlanningAny(lower, "study", "exam", "learn", "course", "class"):
		sections = append(sections, "Practice queue", "Review schedule")
		artifacts = append(artifacts, "practice map", "review ledger")
	case containsPlanningAny(lower, "sales", "business", "customer", "operator"):
		sections = append(sections, "Pipeline actions", "Customer evidence")
		artifacts = append(artifacts, "operator scorecard")
	case containsPlanningAny(lower, "code", "build", "ship"):
		sections = append(sections, "Build queue", "Verification notes")
		artifacts = append(artifacts, "implementation checklist")
	}
	return QuestWorkspace{
		TemplateName: questName(goal) + " workspace",
		Sections:     sections,
		Artifacts:    artifacts,
	}
}

func questName(goal string) string {
	goal = cleanPlanningText(goal)
	if goal == "" {
		return "Guided effort quest"
	}
	lower := strings.ToLower(goal)
	for _, prefix := range []string{"i need to ", "i want to ", "i have to ", "help me ", "learn how to "} {
		lower = strings.TrimPrefix(lower, prefix)
	}
	lower = strings.TrimSpace(lower)
	if lower == "" {
		lower = goal
	}
	return sentenceCase(lower)
}

func stableQuestID(goal string) string {
	re := regexp.MustCompile(`[^a-z0-9]+`)
	id := re.ReplaceAllString(strings.ToLower(goal), "_")
	id = strings.Trim(id, "_")
	if id == "" {
		id = "guided_effort"
	}
	if len(id) > 48 {
		id = strings.Trim(id[:48], "_")
	}
	return id
}

func normalizeQuestSurface(surface string) string {
	surface = strings.ToLower(strings.TrimSpace(surface))
	switch surface {
	case "home", "studio", "dev", "red", "growth":
		return surface
	default:
		return surface
	}
}

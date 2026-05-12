package cognition

import (
	"sort"
	"strings"
)

type ExecutionOrchestrateRequest struct {
	Surface       string                 `json:"surface,omitempty"`
	Intent        string                 `json:"intent,omitempty"`
	Goal          string                 `json:"goal,omitempty"`
	Energy        string                 `json:"energy,omitempty"`
	AvailableMins int                    `json:"available_minutes,omitempty"`
	Tasks         []ExecutionTask        `json:"tasks,omitempty"`
	Blockers      []ExecutionBlocker     `json:"blockers,omitempty"`
	RecentSignals []string               `json:"recent_signals,omitempty"`
	Preferences   ExecutionPreferences   `json:"preferences,omitempty"`
	Metadata      map[string]interface{} `json:"metadata,omitempty"`
}

type ExecutionTask struct {
	ID           string   `json:"id,omitempty"`
	Title        string   `json:"title,omitempty"`
	Project      string   `json:"project,omitempty"`
	Status       string   `json:"status,omitempty"`
	Importance   string   `json:"importance,omitempty"`
	Minutes      int      `json:"minutes,omitempty"`
	Dependencies []string `json:"dependencies,omitempty"`
	Evidence     []string `json:"evidence,omitempty"`
}

type ExecutionBlocker struct {
	ID       string `json:"id,omitempty"`
	Title    string `json:"title,omitempty"`
	Owner    string `json:"owner,omitempty"`
	Severity string `json:"severity,omitempty"`
}

type ExecutionPreferences struct {
	MaxNextOptions      int  `json:"max_next_options,omitempty"`
	PreferSmallStarts   bool `json:"prefer_small_starts,omitempty"`
	OverwhelmSensitive  bool `json:"overwhelm_sensitive,omitempty"`
	RequireVisibleProof bool `json:"require_visible_proof,omitempty"`
}

type ExecutionOrchestrationPlan struct {
	ID              string                    `json:"id"`
	Surface         string                    `json:"surface"`
	Intent          string                    `json:"intent"`
	Summary         string                    `json:"summary"`
	Momentum        ExecutionMomentum         `json:"momentum"`
	NextBest        ExecutionNextMove         `json:"next_best"`
	Options         []ExecutionNextMove       `json:"options,omitempty"`
	BlockedBecause  []ExecutionBlockedBecause `json:"blocked_because,omitempty"`
	DependencyGraph []ExecutionDependencyEdge `json:"dependency_graph,omitempty"`
	MemorySeeds     []QuestMemorySeed         `json:"memory_seeds,omitempty"`
	Integration     ExecutionIntegrationHints `json:"integration"`
	Guardrails      []string                  `json:"guardrails"`
	OpenQuestions   []string                  `json:"open_questions,omitempty"`
}

type ExecutionMomentum struct {
	Score       float64  `json:"score"`
	Level       string   `json:"level"`
	Reasons     []string `json:"reasons,omitempty"`
	DragFactors []string `json:"drag_factors,omitempty"`
}

type ExecutionNextMove struct {
	ID          string   `json:"id"`
	Title       string   `json:"title"`
	Minutes     int      `json:"minutes"`
	Why         string   `json:"why"`
	DoneSignal  string   `json:"done_signal"`
	Needs       []string `json:"needs,omitempty"`
	CanStartNow bool     `json:"can_start_now"`
}

type ExecutionBlockedBecause struct {
	TaskID      string `json:"task_id,omitempty"`
	Title       string `json:"title"`
	Reason      string `json:"reason"`
	UnblockMove string `json:"unblock_move"`
	Owner       string `json:"owner,omitempty"`
}

type ExecutionDependencyEdge struct {
	From   string `json:"from"`
	To     string `json:"to"`
	Status string `json:"status"`
}

type ExecutionIntegrationHints struct {
	Continuity []string `json:"continuity"`
	Temporal   []string `json:"temporal"`
	Procedure  []string `json:"procedure"`
	Memory     []string `json:"memory"`
	Surface    []string `json:"surface"`
}

// OrchestrateExecution turns intent and current execution state into the next
// smallest useful move, with explicit blockers and dependency reasoning.
func OrchestrateExecution(req ExecutionOrchestrateRequest) ExecutionOrchestrationPlan {
	req = normalizeExecutionRequest(req)
	options := buildExecutionOptions(req)
	blocked := buildExecutionBlockedBecause(req)
	graph := buildExecutionDependencyGraph(req)
	momentum := scoreExecutionMomentum(req, options, blocked)
	next := chooseExecutionNextMove(options, req)

	return ExecutionOrchestrationPlan{
		ID:              "exec_" + stableBehaviorID(firstNonEmpty(req.Intent, req.Goal, "execution orchestration")),
		Surface:         normalizeQuestSurface(req.Surface),
		Intent:          sentenceCase(firstNonEmpty(req.Intent, req.Goal)),
		Summary:         summarizeExecution(req, options, blocked, momentum),
		Momentum:        momentum,
		NextBest:        next,
		Options:         options,
		BlockedBecause:  blocked,
		DependencyGraph: graph,
		MemorySeeds:     executionMemorySeeds(req, next, momentum),
		Integration: ExecutionIntegrationHints{
			Continuity: []string{"Call /continuity/recover before orchestration when project state is stale or scattered."},
			Temporal:   []string{"Call /temporal/coordinate when the next move needs placement into real attention windows."},
			Procedure:  []string{"Route repeated execution sequences into /procedure/compile after stable successful runs."},
			Memory:     []string{"Remember recurring drag factors and reliable start moves after confirmation."},
			Surface:    executionSurfaceHints(req.Surface),
		},
		Guardrails: []string{
			"Do not claim tasks, issues, docs, or project boards were changed unless a tool confirms it.",
			"Keep next moves small enough to start; execution clarity beats plan completeness.",
			"Surface blockers as reasons, not user failure.",
		},
		OpenQuestions: executionOpenQuestions(req, next, blocked),
	}
}

func normalizeExecutionRequest(req ExecutionOrchestrateRequest) ExecutionOrchestrateRequest {
	req.Surface = normalizeQuestSurface(req.Surface)
	req.Intent = cleanPlanningText(req.Intent)
	req.Goal = cleanPlanningText(req.Goal)
	req.Energy = strings.ToLower(strings.TrimSpace(firstNonEmpty(req.Energy, "medium")))
	if req.AvailableMins <= 0 {
		req.AvailableMins = 30
	}
	if req.Preferences.MaxNextOptions <= 0 {
		req.Preferences.MaxNextOptions = 4
	}
	if req.Preferences.OverwhelmSensitive && req.Preferences.MaxNextOptions > 3 {
		req.Preferences.MaxNextOptions = 3
	}
	req.RecentSignals = uniqueExecutionStrings(req.RecentSignals)
	for i := range req.Tasks {
		req.Tasks[i].Title = cleanPlanningText(firstNonEmpty(req.Tasks[i].Title, "Untitled task"))
		req.Tasks[i].Project = cleanPlanningText(req.Tasks[i].Project)
		req.Tasks[i].Status = strings.ToLower(strings.TrimSpace(req.Tasks[i].Status))
		req.Tasks[i].Importance = strings.ToLower(strings.TrimSpace(req.Tasks[i].Importance))
		req.Tasks[i].Evidence = uniqueExecutionStrings(req.Tasks[i].Evidence)
		if req.Tasks[i].Minutes <= 0 {
			req.Tasks[i].Minutes = 20
		}
		if req.Tasks[i].ID == "" {
			req.Tasks[i].ID = "task_" + stableBehaviorID(req.Tasks[i].Title)
		}
	}
	for i := range req.Blockers {
		req.Blockers[i].ID = cleanPlanningText(req.Blockers[i].ID)
		req.Blockers[i].Title = cleanPlanningText(firstNonEmpty(req.Blockers[i].Title, "Unnamed blocker"))
		req.Blockers[i].Owner = cleanPlanningText(req.Blockers[i].Owner)
		req.Blockers[i].Severity = strings.ToLower(strings.TrimSpace(req.Blockers[i].Severity))
	}
	if len(req.Tasks) == 0 {
		req.Tasks = []ExecutionTask{{ID: "task_clarify", Title: "Clarify the next executable move", Minutes: 5, Importance: "high"}}
	}
	return req
}

func buildExecutionOptions(req ExecutionOrchestrateRequest) []ExecutionNextMove {
	var options []ExecutionNextMove
	for _, task := range req.Tasks {
		if task.Status == "done" || task.Status == "completed" {
			continue
		}
		blocked := executionTaskBlocked(task, req.Blockers)
		mins := task.Minutes
		if req.Preferences.PreferSmallStarts && mins > 15 {
			mins = 15
		}
		if mins > req.AvailableMins && req.AvailableMins >= 5 {
			mins = req.AvailableMins
		}
		options = append(options, ExecutionNextMove{
			ID:          task.ID,
			Title:       executionActionTitle(task, mins),
			Minutes:     mins,
			Why:         executionTaskWhy(task, blocked),
			DoneSignal:  executionDoneSignal(task, mins),
			Needs:       task.Dependencies,
			CanStartNow: !blocked,
		})
	}
	sort.SliceStable(options, func(i, j int) bool {
		return executionOptionScore(options[i], req) > executionOptionScore(options[j], req)
	})
	if len(options) > req.Preferences.MaxNextOptions {
		return options[:req.Preferences.MaxNextOptions]
	}
	return options
}

func buildExecutionBlockedBecause(req ExecutionOrchestrateRequest) []ExecutionBlockedBecause {
	var out []ExecutionBlockedBecause
	for _, task := range req.Tasks {
		if !executionTaskBlocked(task, req.Blockers) {
			continue
		}
		reason := "Dependency unresolved."
		owner := ""
		for _, blocker := range req.Blockers {
			if blocker.Title != "" && containsPlanningAny(strings.ToLower(task.Title+" "+strings.Join(task.Dependencies, " ")), strings.ToLower(blocker.Title)) {
				reason = blocker.Title
				owner = blocker.Owner
				break
			}
		}
		out = append(out, ExecutionBlockedBecause{
			TaskID:      task.ID,
			Title:       task.Title,
			Reason:      reason,
			UnblockMove: "Name the missing input, owner, or decision before scheduling more work.",
			Owner:       owner,
		})
	}
	for _, blocker := range req.Blockers {
		if blocker.Title == "" {
			continue
		}
		out = append(out, ExecutionBlockedBecause{
			Title:       blocker.Title,
			Reason:      firstNonEmpty(blocker.Severity, "active blocker"),
			UnblockMove: "Ask for the smallest answer or permission needed to proceed.",
			Owner:       blocker.Owner,
		})
	}
	if len(out) > 6 {
		return out[:6]
	}
	return out
}

func buildExecutionDependencyGraph(req ExecutionOrchestrateRequest) []ExecutionDependencyEdge {
	var edges []ExecutionDependencyEdge
	for _, task := range req.Tasks {
		for _, dep := range task.Dependencies {
			edges = append(edges, ExecutionDependencyEdge{
				From:   dep,
				To:     task.ID,
				Status: "required",
			})
		}
	}
	if len(edges) > 8 {
		return edges[:8]
	}
	return edges
}

func scoreExecutionMomentum(req ExecutionOrchestrateRequest, options []ExecutionNextMove, blocked []ExecutionBlockedBecause) ExecutionMomentum {
	score := 0.5
	var reasons []string
	var drag []string
	if len(options) > 0 {
		score += 0.12
		reasons = append(reasons, "next moves identified")
	}
	if len(req.RecentSignals) > 0 {
		score += 0.08
		reasons = append(reasons, "recent progress signals available")
	}
	if req.AvailableMins >= 20 {
		score += 0.05
		reasons = append(reasons, "enough time for visible output")
	}
	if len(blocked) > 0 {
		score -= float64(len(blocked)) * 0.08
		drag = append(drag, "active blockers")
	}
	if req.Energy == "low" {
		score -= 0.05
		drag = append(drag, "low energy")
	}
	if score < 0.1 {
		score = 0.1
	}
	if score > 0.9 {
		score = 0.9
	}
	return ExecutionMomentum{Score: score, Level: executionMomentumLevel(score), Reasons: reasons, DragFactors: drag}
}

func chooseExecutionNextMove(options []ExecutionNextMove, req ExecutionOrchestrateRequest) ExecutionNextMove {
	for _, option := range options {
		if option.CanStartNow {
			return option
		}
	}
	if len(options) > 0 {
		return options[0]
	}
	return ExecutionNextMove{
		ID:          "task_clarify",
		Title:       "Clarify the next executable move",
		Minutes:     5,
		Why:         "Execution cannot continue until the next move is named.",
		DoneSignal:  "A task, owner, and visible output are named.",
		CanStartNow: true,
	}
}

func executionTaskBlocked(task ExecutionTask, blockers []ExecutionBlocker) bool {
	if len(task.Dependencies) > 0 || containsPlanningAny(task.Status, "blocked", "waiting") {
		return true
	}
	lower := strings.ToLower(task.Title + " " + strings.Join(task.Evidence, " "))
	for _, blocker := range blockers {
		if blocker.Title != "" && containsPlanningAny(lower, strings.ToLower(blocker.Title)) {
			return true
		}
	}
	return false
}

func executionOptionScore(option ExecutionNextMove, req ExecutionOrchestrateRequest) int {
	score := 0
	lower := strings.ToLower(option.Title + " " + option.Why)
	if option.CanStartNow {
		score += 40
	}
	if containsPlanningAny(lower, "client", "customer", "urgent", "today", "high") {
		score += 25
	}
	if option.Minutes <= req.AvailableMins {
		score += 15
	}
	if option.Minutes <= 15 {
		score += 8
	}
	return score
}

func executionActionTitle(task ExecutionTask, mins int) string {
	if mins < task.Minutes {
		return "Start: " + task.Title
	}
	return task.Title
}

func executionTaskWhy(task ExecutionTask, blocked bool) string {
	if blocked {
		return "Blocked work should be clarified before it consumes more planning energy."
	}
	lower := strings.ToLower(task.Importance + " " + task.Title)
	switch {
	case containsPlanningAny(lower, "high", "urgent", "client", "customer"):
		return "High-value work that can create visible momentum."
	default:
		return "Executable work that reduces activation energy to continue."
	}
}

func executionDoneSignal(task ExecutionTask, mins int) string {
	if mins < task.Minutes {
		return "A partial artifact exists and remaining work is named."
	}
	if len(task.Evidence) > 0 {
		return "New evidence is added or the task state is updated."
	}
	return "A visible output, answer, or blocker note exists."
}

func summarizeExecution(req ExecutionOrchestrateRequest, options []ExecutionNextMove, blocked []ExecutionBlockedBecause, momentum ExecutionMomentum) string {
	return sentenceCase(firstNonEmpty(req.Intent, req.Goal, "execution")) + " has " +
		intToMomentumString(len(options)) + " next options, " +
		intToMomentumString(len(blocked)) + " blocker signals, and " +
		momentum.Level + " momentum."
}

func executionMemorySeeds(req ExecutionOrchestrateRequest, next ExecutionNextMove, momentum ExecutionMomentum) []QuestMemorySeed {
	return []QuestMemorySeed{
		{Key: "execution_intent", Value: firstNonEmpty(req.Intent, req.Goal), Importance: 0.64},
		{Key: "execution_next_move", Value: next.Title, Importance: 0.74},
		{Key: "execution_momentum", Value: momentum.Level, Importance: 0.56},
	}
}

func executionMomentumLevel(score float64) string {
	switch {
	case score >= 0.72:
		return "high"
	case score >= 0.45:
		return "medium"
	default:
		return "low"
	}
}

func executionOpenQuestions(req ExecutionOrchestrateRequest, next ExecutionNextMove, blocked []ExecutionBlockedBecause) []string {
	var qs []string
	if next.ID == "" || next.Title == "" {
		qs = append(qs, "What is the smallest executable next move?")
	}
	if len(blocked) > 0 {
		qs = append(qs, "Which blocker should be resolved first?")
	}
	if len(req.Tasks) == 0 {
		qs = append(qs, "What task list or project state should ORI orchestrate?")
	}
	return qs
}

func executionSurfaceHints(surface string) []string {
	switch normalizeQuestSurface(surface) {
	case "dev":
		return []string{"Show next implementation move, blockers, verification, and dependency edges."}
	case "studio":
		return []string{"Show owner-ready next action, customer/business impact, and blocked-because reasoning."}
	case "home":
		return []string{"Show one gentle next action and explain blockers without pressure."}
	default:
		return []string{"Keep execution guidance compact and app-neutral."}
	}
}

func uniqueExecutionStrings(values []string) []string {
	seen := map[string]bool{}
	var out []string
	for _, v := range values {
		v = cleanPlanningText(v)
		if v == "" {
			continue
		}
		key := strings.ToLower(v)
		if seen[key] {
			continue
		}
		seen[key] = true
		out = append(out, v)
	}
	sort.Strings(out)
	return out
}

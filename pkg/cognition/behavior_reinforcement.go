package cognition

import (
	"math"
	"regexp"
	"strings"
)

type BehaviorType string

const (
	BehaviorDaily      BehaviorType = "daily"
	BehaviorHabit      BehaviorType = "habit"
	BehaviorTodo       BehaviorType = "todo"
	BehaviorGoal       BehaviorType = "goal"
	BehaviorSharedGoal BehaviorType = "shared_goal"
)

type BehaviorReinforcementRequest struct {
	Type              BehaviorType `json:"type"`
	Title             string       `json:"title"`
	Cadence           string       `json:"cadence,omitempty"`
	Surface           string       `json:"surface,omitempty"`
	ReinforcementMode string       `json:"reinforcement_mode,omitempty"`
	Stakes            string       `json:"stakes,omitempty"`
	RecoveryPolicy    string       `json:"recovery_policy,omitempty"`
	Privacy           string       `json:"privacy,omitempty"`
	Notes             string       `json:"notes,omitempty"`
}

type BehaviorObject struct {
	ID                string                   `json:"id"`
	Type              BehaviorType             `json:"type"`
	Title             string                   `json:"title"`
	Surface           string                   `json:"surface,omitempty"`
	Cadence           string                   `json:"cadence"`
	TemporalContract  string                   `json:"temporal_contract"`
	Stakes            string                   `json:"stakes"`
	Privacy           string                   `json:"privacy"`
	ReinforcementMode string                   `json:"reinforcement_mode"`
	RecoveryPolicy    string                   `json:"recovery_policy"`
	FeedbackModel     BehaviorFeedbackModel    `json:"feedback_model"`
	State             BehaviorState            `json:"state"`
	Integration       BehaviorIntegrationHints `json:"integration"`
	Governance        []string                 `json:"governance,omitempty"`
}

type BehaviorFeedbackModel struct {
	StateLabel      string   `json:"state_label"`
	PositiveSignals []string `json:"positive_signals"`
	MissHandling    []string `json:"miss_handling"`
	Avoid           []string `json:"avoid"`
}

type BehaviorEventRequest struct {
	BehaviorID string                       `json:"behavior_id"`
	Behavior   BehaviorReinforcementRequest `json:"behavior,omitempty"`
	Event      string                       `json:"event"`
	Context    BehaviorEventContext         `json:"context,omitempty"`
	PriorState *BehaviorState               `json:"prior_state,omitempty"`
}

type BehaviorEventContext struct {
	Energy   string `json:"energy,omitempty"`
	Location string `json:"location,omitempty"`
	Notes    string `json:"notes,omitempty"`
}

type BehaviorEventFeedback struct {
	BehaviorID       string            `json:"behavior_id"`
	Event            string            `json:"event"`
	State            BehaviorState     `json:"state"`
	SymbolicFeedback string            `json:"symbolic_feedback"`
	NextBestAction   string            `json:"next_best_action"`
	Recovery         []string          `json:"recovery,omitempty"`
	MemorySeeds      []QuestMemorySeed `json:"memory_seeds,omitempty"`
	Governance       []string          `json:"governance,omitempty"`
}

type BehaviorStateRequest struct {
	BehaviorID string                       `json:"behavior_id,omitempty"`
	Behavior   BehaviorReinforcementRequest `json:"behavior,omitempty"`
	Events     []BehaviorEventRequest       `json:"events,omitempty"`
	State      *BehaviorState               `json:"state,omitempty"`
}

type BehaviorState struct {
	Streak            int      `json:"streak"`
	StabilityScore    float64  `json:"stability_score"`
	CompletedCount    int      `json:"completed_count"`
	MissedCount       int      `json:"missed_count"`
	DeferredCount     int      `json:"deferred_count"`
	FrictionPattern   string   `json:"friction_pattern,omitempty"`
	NextBestAction    string   `json:"next_best_action"`
	ReinforcementTier string   `json:"reinforcement_tier"`
	Track             []string `json:"track,omitempty"`
}

type BehaviorIntegrationHints struct {
	Memory     []string `json:"memory"`
	Chronos    []string `json:"chronos"`
	GoalDaemon []string `json:"goal_daemon,omitempty"`
	PAD        []string `json:"pad,omitempty"`
	CALI       []string `json:"cali"`
}

func BuildBehaviorObject(req BehaviorReinforcementRequest) BehaviorObject {
	req = normalizeBehaviorRequest(req)
	state := BehaviorState{
		Streak:            0,
		StabilityScore:    0.5,
		NextBestAction:    firstBehaviorAction(req),
		ReinforcementTier: "starting",
		Track:             []string{"completion events", "misses", "deferrals", "recovery actions", "friction notes"},
	}

	return BehaviorObject{
		ID:                "beh_" + stableBehaviorID(string(req.Type)+"_"+req.Title),
		Type:              req.Type,
		Title:             req.Title,
		Surface:           normalizeQuestSurface(req.Surface),
		Cadence:           req.Cadence,
		TemporalContract:  behaviorTemporalContract(req),
		Stakes:            req.Stakes,
		Privacy:           req.Privacy,
		ReinforcementMode: req.ReinforcementMode,
		RecoveryPolicy:    req.RecoveryPolicy,
		FeedbackModel:     behaviorFeedbackModel(req),
		State:             state,
		Integration:       behaviorIntegration(req),
		Governance: []string{
			"Do not infer character, discipline, or worth from missed behavior.",
			"Treat misses as recovery inputs, not punishment triggers.",
			"Do not claim reminders, persistence, or shared accountability happened until a client confirms it.",
			"Keep symbolic feedback surface-appropriate and user-configurable.",
		},
	}
}

func ApplyBehaviorEvent(req BehaviorEventRequest) BehaviorEventFeedback {
	behavior := normalizeBehaviorRequest(req.Behavior)
	state := BehaviorState{StabilityScore: 0.5, NextBestAction: firstBehaviorAction(behavior), ReinforcementTier: "starting"}
	if req.PriorState != nil {
		state = *req.PriorState
	}

	event := normalizeBehaviorEvent(req.Event)
	switch event {
	case "completed":
		state.CompletedCount++
		state.Streak++
	case "missed":
		state.MissedCount++
		state.Streak = 0
	case "deferred":
		state.DeferredCount++
	case "partially_completed":
		state.CompletedCount++
	}
	state.StabilityScore = scoreBehaviorStability(state)
	state.ReinforcementTier = behaviorTier(state.StabilityScore)
	state.FrictionPattern = inferBehaviorFriction(req.Context, event)
	state.NextBestAction = behaviorNextAction(behavior, event, state)

	return BehaviorEventFeedback{
		BehaviorID:       firstNonEmpty(req.BehaviorID, "beh_"+stableBehaviorID(string(behavior.Type)+"_"+behavior.Title)),
		Event:            event,
		State:            state,
		SymbolicFeedback: behaviorSymbolicFeedback(behavior, event, state),
		NextBestAction:   state.NextBestAction,
		Recovery:         behaviorRecovery(event, req.Context),
		MemorySeeds: []QuestMemorySeed{
			{Key: "behavior_event", Value: event + ":" + behavior.Title, Importance: 0.62},
			{Key: "behavior_friction", Value: state.FrictionPattern, Importance: 0.58},
		},
		Governance: []string{
			"Use recovery language for misses.",
			"Avoid variable reward pressure and shame loops.",
			"Separate private behavior state from shared commitments unless stakes are explicit.",
		},
	}
}

func BuildBehaviorState(req BehaviorStateRequest) BehaviorState {
	state := BehaviorState{StabilityScore: 0.5, NextBestAction: firstBehaviorAction(req.Behavior), ReinforcementTier: "starting"}
	if req.State != nil {
		state = *req.State
	}
	for _, event := range req.Events {
		event.PriorState = &state
		if event.Behavior.Title == "" {
			event.Behavior = req.Behavior
		}
		state = ApplyBehaviorEvent(event).State
	}
	if len(req.Events) == 0 {
		state.NextBestAction = firstBehaviorAction(normalizeBehaviorRequest(req.Behavior))
		state.ReinforcementTier = behaviorTier(state.StabilityScore)
	}
	return state
}

func normalizeBehaviorRequest(req BehaviorReinforcementRequest) BehaviorReinforcementRequest {
	if req.Type == "" {
		req.Type = BehaviorHabit
	}
	switch req.Type {
	case BehaviorDaily, BehaviorHabit, BehaviorTodo, BehaviorGoal, BehaviorSharedGoal:
	default:
		req.Type = BehaviorHabit
	}
	req.Title = cleanPlanningText(firstNonEmpty(req.Title, req.Notes, "Unnamed behavior"))
	if req.Cadence == "" {
		switch req.Type {
		case BehaviorDaily:
			req.Cadence = "daily"
		case BehaviorTodo:
			req.Cadence = "once"
		default:
			req.Cadence = "flexible"
		}
	}
	if req.Stakes == "" {
		req.Stakes = "private"
	}
	if req.Privacy == "" {
		req.Privacy = "private"
	}
	if req.ReinforcementMode == "" {
		req.ReinforcementMode = "calm_progress"
	}
	if req.RecoveryPolicy == "" {
		req.RecoveryPolicy = "adaptive_reschedule"
	}
	return req
}

func behaviorTemporalContract(req BehaviorReinforcementRequest) string {
	switch req.Type {
	case BehaviorDaily:
		return "Repeats on a schedule; misses should create recovery or rescope, not punishment."
	case BehaviorHabit:
		return "Flexible repetition; consistency matters more than perfect streaks."
	case BehaviorTodo:
		return "One-time completion; reinforcement should mark closure and reduce open-loop pressure."
	case BehaviorGoal, BehaviorSharedGoal:
		return "Multi-step progress; state should advance from evidence across milestones."
	default:
		return "Behavior state updates from completion, miss, deferral, and recovery events."
	}
}

func behaviorFeedbackModel(req BehaviorReinforcementRequest) BehaviorFeedbackModel {
	return BehaviorFeedbackModel{
		StateLabel: surfaceBehaviorStateLabel(req.Surface),
		PositiveSignals: []string{
			"visible completion",
			"repeat after friction",
			"recovery after missed execution",
			"blocker removed",
		},
		MissHandling: []string{
			"shrink the next action",
			"reschedule to a better window",
			"name the friction without identity judgment",
			"preserve rhythm with a minimum viable action",
		},
		Avoid: []string{
			"health-loss style punishment",
			"identity labels from failure",
			"dark-pattern reward schedules",
			"public pressure without explicit stakes",
		},
	}
}

func behaviorIntegration(req BehaviorReinforcementRequest) BehaviorIntegrationHints {
	return BehaviorIntegrationHints{
		Memory: []string{
			"Store completion/miss patterns, recovery preferences, and recurring friction notes.",
			"Summarize behavior state periodically instead of storing every event as identity context.",
		},
		Chronos: []string{
			"Track cadence decay and stale behavior windows.",
			"Detect time-of-day or sequence patterns behind misses.",
		},
		GoalDaemon: []string{
			"Promote behavior to a goal DAG only when it has milestones or shared stakes.",
		},
		PAD: []string{
			"Dispatch specialist support for schedule, environment, accountability, or domain-specific coaching when repeated friction appears.",
		},
		CALI: []string{
			"Block shame, coercive nudges, and false certainty about motivation.",
			"Require explicit user consent before shared accountability or social pressure.",
		},
	}
}

func normalizeBehaviorEvent(event string) string {
	event = strings.ToLower(strings.TrimSpace(event))
	switch event {
	case "completed", "missed", "deferred", "partially_completed":
		return event
	default:
		return "completed"
	}
}

func scoreBehaviorStability(state BehaviorState) float64 {
	total := state.CompletedCount + state.MissedCount + state.DeferredCount
	if total <= 0 {
		return 0.5
	}
	score := (float64(state.CompletedCount)*0.72 + float64(state.DeferredCount)*0.42 + math.Min(float64(state.Streak), 7)*0.04) / float64(total)
	if state.MissedCount > 0 {
		score -= math.Min(float64(state.MissedCount)*0.06, 0.24)
	}
	return math.Round(clamp01Local(score)*100) / 100
}

func behaviorTier(score float64) string {
	switch {
	case score >= 0.75:
		return "stable"
	case score >= 0.45:
		return "forming"
	default:
		return "recovery"
	}
}

func inferBehaviorFriction(ctx BehaviorEventContext, event string) string {
	if event != "missed" && event != "deferred" {
		return ""
	}
	switch {
	case strings.EqualFold(ctx.Energy, "low"):
		return "misses or deferrals may cluster around low-energy windows"
	case ctx.Location != "":
		return "context may depend on location: " + cleanPlanningText(ctx.Location)
	case ctx.Notes != "":
		return cleanPlanningText(ctx.Notes)
	default:
		return "friction is present but not yet explained"
	}
}

func behaviorNextAction(req BehaviorReinforcementRequest, event string, state BehaviorState) string {
	switch event {
	case "missed":
		return "Do the smallest recovery version of: " + req.Title
	case "deferred":
		return "Choose the next realistic window for: " + req.Title
	case "partially_completed":
		return "Log the partial win and finish only the next visible checkpoint."
	default:
		if state.StabilityScore >= 0.75 {
			return "Keep the rhythm; do not add complexity yet."
		}
		return firstBehaviorAction(req)
	}
}

func behaviorRecovery(event string, ctx BehaviorEventContext) []string {
	if event != "missed" && event != "deferred" {
		return nil
	}
	recovery := []string{
		"Shrink the next attempt to a minimum viable action.",
		"Name one friction point without identity judgment.",
		"Move the behavior to a more realistic window.",
	}
	if strings.EqualFold(ctx.Energy, "low") {
		recovery = append(recovery, "Use a low-energy version today and preserve continuity.")
	}
	return recovery
}

func behaviorSymbolicFeedback(req BehaviorReinforcementRequest, event string, state BehaviorState) string {
	label := surfaceBehaviorStateLabel(req.Surface)
	switch event {
	case "missed":
		return label + " needs recovery, not punishment."
	case "deferred":
		return label + " stayed intact because the behavior was consciously rescheduled."
	case "partially_completed":
		return label + " moved forward through partial evidence."
	default:
		return label + " improved because effort became visible."
	}
}

func surfaceBehaviorStateLabel(surface string) string {
	switch normalizeQuestSurface(surface) {
	case "studio":
		return "Workflow health"
	case "dev":
		return "Implementation momentum"
	case "growth":
		return "Signal momentum"
	case "home":
		return "Household calm"
	default:
		return "Behavioral state"
	}
}

func firstBehaviorAction(req BehaviorReinforcementRequest) string {
	req = normalizeBehaviorRequest(req)
	switch req.Type {
	case BehaviorTodo:
		return "Complete the next visible checkpoint for: " + req.Title
	case BehaviorGoal, BehaviorSharedGoal:
		return "Create one evidence-producing step for: " + req.Title
	default:
		return "Do the smallest useful version of: " + req.Title
	}
}

func stableBehaviorID(value string) string {
	re := regexp.MustCompile(`[^a-z0-9]+`)
	id := re.ReplaceAllString(strings.ToLower(value), "_")
	id = strings.Trim(id, "_")
	if id == "" {
		id = "behavior"
	}
	if len(id) > 48 {
		id = strings.Trim(id[:48], "_")
	}
	return id
}

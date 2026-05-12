package cognition

import (
	"sort"
	"strings"
)

type IntentTimelineRequest struct {
	Surface     string                 `json:"surface,omitempty"`
	Project     string                 `json:"project,omitempty"`
	Objective   string                 `json:"objective,omitempty"`
	CurrentGoal string                 `json:"current_goal,omitempty"`
	Events      []IntentEvent          `json:"events,omitempty"`
	Decisions   []string               `json:"decisions,omitempty"`
	OpenLoops   []string               `json:"open_loops,omitempty"`
	Constraints []string               `json:"constraints,omitempty"`
	Metadata    map[string]interface{} `json:"metadata,omitempty"`
}

type IntentEvent struct {
	ID         string   `json:"id,omitempty"`
	Time       string   `json:"time,omitempty"`
	Actor      string   `json:"actor,omitempty"`
	Artifact   string   `json:"artifact,omitempty"`
	Action     string   `json:"action,omitempty"`
	Intent     string   `json:"intent,omitempty"`
	Rationale  string   `json:"rationale,omitempty"`
	Constraint string   `json:"constraint,omitempty"`
	Outcome    string   `json:"outcome,omitempty"`
	Evidence   []string `json:"evidence,omitempty"`
	Tags       []string `json:"tags,omitempty"`
}

type IntentTimeline struct {
	ID               string                    `json:"id"`
	Surface          string                    `json:"surface"`
	Project          string                    `json:"project,omitempty"`
	Objective        string                    `json:"objective"`
	Summary          string                    `json:"summary"`
	CurrentIntent    IntentCurrentState        `json:"current_intent"`
	Moments          []IntentMoment            `json:"moments,omitempty"`
	IntentShifts     []IntentShift             `json:"intent_shifts,omitempty"`
	RationaleTrail   []IntentRationaleNode     `json:"rationale_trail,omitempty"`
	ContinuityPacket IntentContinuityPacket    `json:"continuity_packet"`
	MemorySeeds      []QuestMemorySeed         `json:"memory_seeds,omitempty"`
	Integration      IntentTimelineIntegration `json:"integration"`
	Guardrails       []string                  `json:"guardrails"`
	OpenQuestions    []string                  `json:"open_questions,omitempty"`
}

type IntentCurrentState struct {
	Goal        string   `json:"goal"`
	LastChange  string   `json:"last_change"`
	Why         string   `json:"why"`
	Constraints []string `json:"constraints,omitempty"`
	Confidence  float64  `json:"confidence"`
}

type IntentMoment struct {
	ID        string   `json:"id"`
	Time      string   `json:"time,omitempty"`
	Actor     string   `json:"actor,omitempty"`
	Artifact  string   `json:"artifact,omitempty"`
	Action    string   `json:"action"`
	Intent    string   `json:"intent"`
	Rationale string   `json:"rationale"`
	Outcome   string   `json:"outcome,omitempty"`
	Evidence  []string `json:"evidence,omitempty"`
}

type IntentShift struct {
	ID        string `json:"id"`
	From      string `json:"from,omitempty"`
	To        string `json:"to"`
	Reason    string `json:"reason"`
	Evidence  string `json:"evidence,omitempty"`
	Stability string `json:"stability"`
}

type IntentRationaleNode struct {
	ID        string   `json:"id"`
	Claim     string   `json:"claim"`
	Supports  []string `json:"supports,omitempty"`
	Risk      string   `json:"risk,omitempty"`
	NextUse   string   `json:"next_use"`
	SourceIDs []string `json:"source_ids,omitempty"`
}

type IntentContinuityPacket struct {
	ResumeLine    string   `json:"resume_line"`
	KeepInMind    []string `json:"keep_in_mind,omitempty"`
	NextQuestion  string   `json:"next_question"`
	StaleIf       string   `json:"stale_if"`
	UsefulFor     []string `json:"useful_for,omitempty"`
	DurableSignal string   `json:"durable_signal"`
}

type IntentTimelineIntegration struct {
	Continuity []string `json:"continuity"`
	WorkGraph  []string `json:"workgraph"`
	Procedure  []string `json:"procedure"`
	Memory     []string `json:"memory"`
	Temporal   []string `json:"temporal"`
	Surface    []string `json:"surface"`
}

// BuildIntentTimeline preserves why work changed, not just what changed.
// It turns chats, diffs, tool calls, notes, and decisions into a compact
// rationale trail that future agents can resume without rehydration drag.
func BuildIntentTimeline(req IntentTimelineRequest) IntentTimeline {
	req = normalizeIntentTimelineRequest(req)
	moments := buildIntentMoments(req)
	shifts := buildIntentShifts(moments)
	rationale := buildIntentRationaleTrail(req, moments, shifts)
	current := buildIntentCurrentState(req, moments, shifts)
	packet := buildIntentContinuityPacket(req, current, shifts)

	return IntentTimeline{
		ID:               "intent_" + stableBehaviorID(req.Project+"_"+req.Objective),
		Surface:          normalizeQuestSurface(req.Surface),
		Project:          req.Project,
		Objective:        req.Objective,
		Summary:          summarizeIntentTimeline(req, moments, shifts),
		CurrentIntent:    current,
		Moments:          moments,
		IntentShifts:     shifts,
		RationaleTrail:   rationale,
		ContinuityPacket: packet,
		MemorySeeds:      intentTimelineMemorySeeds(req, current),
		Integration: IntentTimelineIntegration{
			Continuity: []string{"Feed current_intent and continuity_packet into /continuity/recover when resuming interrupted work."},
			WorkGraph:  []string{"Attach durable decisions and open loops to /workgraph/compile when they become operator work state."},
			Procedure:  []string{"Send repeated rationale/action chains to /procedural/crystallize before promoting them into skills."},
			Memory:     []string{"Persist source-backed rationale nodes only after client confirmation or tool-backed writes."},
			Temporal:   []string{"Use /temporal/coordinate when stale_if or open loops imply a review window."},
			Surface:    continuitySurfaceHints(req.Surface),
		},
		Guardrails: []string{
			"Do not claim artifacts, tasks, timelines, or memory were updated unless a tool confirms it.",
			"Separate source-backed rationale from inferred intent shifts.",
			"Keep sensitive rationale and private artifact content under the client surface's consent policy.",
		},
		OpenQuestions: intentTimelineOpenQuestions(req, current, shifts),
	}
}

func normalizeIntentTimelineRequest(req IntentTimelineRequest) IntentTimelineRequest {
	req.Surface = normalizeQuestSurface(req.Surface)
	req.Project = cleanPlanningText(req.Project)
	req.Objective = cleanPlanningText(firstNonEmpty(req.Objective, req.CurrentGoal, "preserve intent continuity"))
	req.CurrentGoal = cleanPlanningText(req.CurrentGoal)
	req.Decisions = uniqueActionStrings(req.Decisions)
	req.OpenLoops = uniqueActionStrings(req.OpenLoops)
	req.Constraints = uniqueActionStrings(req.Constraints)
	for i := range req.Events {
		req.Events[i].ID = cleanPlanningText(req.Events[i].ID)
		req.Events[i].Time = cleanPlanningText(req.Events[i].Time)
		req.Events[i].Actor = cleanPlanningText(req.Events[i].Actor)
		req.Events[i].Artifact = cleanPlanningText(req.Events[i].Artifact)
		req.Events[i].Action = cleanPlanningText(req.Events[i].Action)
		req.Events[i].Intent = cleanPlanningText(req.Events[i].Intent)
		req.Events[i].Rationale = cleanPlanningText(req.Events[i].Rationale)
		req.Events[i].Constraint = cleanPlanningText(req.Events[i].Constraint)
		req.Events[i].Outcome = cleanPlanningText(req.Events[i].Outcome)
		req.Events[i].Evidence = uniqueActionStrings(req.Events[i].Evidence)
	}
	if req.Project == "" {
		req.Project = inferIntentProject(req)
	}
	return req
}

func buildIntentMoments(req IntentTimelineRequest) []IntentMoment {
	var moments []IntentMoment
	for _, event := range req.Events {
		action := firstNonEmpty(event.Action, event.Outcome, event.Intent, "captured work event")
		intent := firstNonEmpty(event.Intent, req.CurrentGoal, req.Objective)
		moments = append(moments, IntentMoment{
			ID:        firstNonEmpty(event.ID, "mom_"+stableBehaviorID(action+"_"+intent)),
			Time:      event.Time,
			Actor:     firstNonEmpty(event.Actor, "operator"),
			Artifact:  event.Artifact,
			Action:    sentenceCase(action),
			Intent:    sentenceCase(intent),
			Rationale: sentenceCase(firstNonEmpty(event.Rationale, event.Constraint, "Preserve why this change happened.")),
			Outcome:   sentenceCase(event.Outcome),
			Evidence:  event.Evidence,
		})
	}
	for _, decision := range req.Decisions {
		moments = append(moments, IntentMoment{
			ID:        "dec_" + stableBehaviorID(decision),
			Actor:     "operator",
			Action:    "Decision: " + sentenceCase(decision),
			Intent:    sentenceCase(firstNonEmpty(req.CurrentGoal, req.Objective)),
			Rationale: "Decision should remain attached to the goal it served.",
			Outcome:   "Decision preserved for future continuation.",
		})
	}
	if len(moments) == 0 {
		moments = append(moments, IntentMoment{
			ID:        "mom_clarify",
			Actor:     "operator",
			Action:    "Clarify the active intent",
			Intent:    sentenceCase(req.Objective),
			Rationale: "No event history was supplied.",
			Outcome:   "Intent timeline starts after the active goal is named.",
		})
	}
	if len(moments) > 10 {
		return moments[len(moments)-10:]
	}
	return moments
}

func buildIntentShifts(moments []IntentMoment) []IntentShift {
	var shifts []IntentShift
	var previous string
	for _, moment := range moments {
		intent := strings.TrimSpace(moment.Intent)
		if intent == "" {
			continue
		}
		if previous != "" && !strings.EqualFold(previous, intent) {
			shifts = append(shifts, IntentShift{
				ID:        "shift_" + stableBehaviorID(previous+"_"+intent),
				From:      previous,
				To:        intent,
				Reason:    firstNonEmpty(moment.Rationale, "Intent changed during the work trace."),
				Evidence:  firstNonEmpty(moment.Action, moment.Outcome),
				Stability: intentStability(moment),
			})
		}
		previous = intent
	}
	if len(shifts) > 6 {
		return shifts[len(shifts)-6:]
	}
	return shifts
}

func buildIntentRationaleTrail(req IntentTimelineRequest, moments []IntentMoment, shifts []IntentShift) []IntentRationaleNode {
	var trail []IntentRationaleNode
	for _, moment := range moments {
		if moment.Rationale == "" {
			continue
		}
		trail = append(trail, IntentRationaleNode{
			ID:        "why_" + stableBehaviorID(moment.ID+"_"+moment.Rationale),
			Claim:     moment.Rationale,
			Supports:  []string{moment.Action, moment.Outcome},
			Risk:      intentRationaleRisk(moment),
			NextUse:   "Use when explaining why the current path changed.",
			SourceIDs: []string{moment.ID},
		})
		if len(trail) == 6 {
			break
		}
	}
	for _, loop := range req.OpenLoops {
		trail = append(trail, IntentRationaleNode{
			ID:      "loop_" + stableBehaviorID(loop),
			Claim:   sentenceCase(loop),
			Risk:    "Open loop may stale the timeline if unresolved.",
			NextUse: "Resurface before committing to the next execution move.",
		})
		if len(trail) == 8 {
			break
		}
	}
	sort.SliceStable(trail, func(i, j int) bool {
		return trail[i].Risk != "" && trail[j].Risk == ""
	})
	_ = shifts
	return trail
}

func buildIntentCurrentState(req IntentTimelineRequest, moments []IntentMoment, shifts []IntentShift) IntentCurrentState {
	last := moments[len(moments)-1]
	goal := firstNonEmpty(req.CurrentGoal, last.Intent, req.Objective)
	conf := 0.48 + float64(len(moments))*0.04 + float64(len(req.Decisions))*0.03
	if len(shifts) > 0 {
		conf -= 0.08
	}
	if conf > 0.88 {
		conf = 0.88
	}
	if conf < 0.28 {
		conf = 0.28
	}
	return IntentCurrentState{
		Goal:        sentenceCase(goal),
		LastChange:  firstNonEmpty(last.Action, last.Outcome),
		Why:         firstNonEmpty(last.Rationale, "Latest supplied event defines the current continuation point."),
		Constraints: req.Constraints,
		Confidence:  conf,
	}
}

func buildIntentContinuityPacket(req IntentTimelineRequest, current IntentCurrentState, shifts []IntentShift) IntentContinuityPacket {
	keep := append([]string{}, req.Constraints...)
	for _, loop := range req.OpenLoops {
		keep = append(keep, "Open loop: "+sentenceCase(loop))
	}
	if len(keep) > 5 {
		keep = keep[:5]
	}
	return IntentContinuityPacket{
		ResumeLine:    "Resume " + current.Goal + " from: " + current.LastChange,
		KeepInMind:    keep,
		NextQuestion:  intentNextQuestion(req, shifts),
		StaleIf:       "New decisions, source changes, or unresolved loops invalidate the current rationale trail.",
		UsefulFor:     []string{"continuity recovery", "execution orchestration", "agent handoff", "rationale review"},
		DurableSignal: "User or client confirms this intent trail matches the work state.",
	}
}

func summarizeIntentTimeline(req IntentTimelineRequest, moments []IntentMoment, shifts []IntentShift) string {
	return sentenceCase(req.Objective) + " has " + intToMomentumString(len(moments)) + " preserved intent moments and " + intToMomentumString(len(shifts)) + " detected intent shifts."
}

func intentTimelineMemorySeeds(req IntentTimelineRequest, current IntentCurrentState) []QuestMemorySeed {
	return []QuestMemorySeed{
		{Key: "intent_project", Value: req.Project, Importance: 0.55},
		{Key: "intent_current_goal", Value: current.Goal, Importance: 0.72},
		{Key: "intent_last_change", Value: current.LastChange, Importance: 0.64},
	}
}

func inferIntentProject(req IntentTimelineRequest) string {
	for _, event := range req.Events {
		if event.Artifact != "" {
			return event.Artifact
		}
	}
	return "active work"
}

func intentStability(moment IntentMoment) string {
	lower := strings.ToLower(moment.Rationale + " " + moment.Outcome)
	if containsPlanningAny(lower, "blocked", "unclear", "risk", "changed", "pivot") {
		return "unstable"
	}
	if containsPlanningAny(lower, "verified", "shipped", "confirmed", "passed") {
		return "stable"
	}
	return "watch"
}

func intentRationaleRisk(moment IntentMoment) string {
	lower := strings.ToLower(moment.Action + " " + moment.Rationale + " " + moment.Outcome)
	switch {
	case containsPlanningAny(lower, "assume", "unclear", "unknown"):
		return "inference needs confirmation"
	case containsPlanningAny(lower, "blocked", "failed", "risk"):
		return "blocker may affect continuation"
	case len(moment.Evidence) == 0:
		return "no explicit evidence supplied"
	default:
		return ""
	}
}

func intentNextQuestion(req IntentTimelineRequest, shifts []IntentShift) string {
	if len(req.OpenLoops) > 0 {
		return "Which open loop should be resolved before continuing?"
	}
	if len(shifts) > 0 {
		return "Is the latest intent shift still valid?"
	}
	return "What is the smallest next move that preserves this intent?"
}

func intentTimelineOpenQuestions(req IntentTimelineRequest, current IntentCurrentState, shifts []IntentShift) []string {
	var qs []string
	if len(req.Events) == 0 {
		qs = append(qs, "What events or artifacts should anchor the intent trail?")
	}
	if current.Confidence < 0.55 {
		qs = append(qs, "What source confirms the current goal?")
	}
	if len(shifts) > 0 {
		qs = append(qs, "Which intent shift should future agents treat as authoritative?")
	}
	return qs
}

package cognition

import (
	"sort"
	"strings"
)

type SignalOpportunityRequest struct {
	Surface   string           `json:"surface,omitempty"`
	Entity    ActionEntity     `json:"entity,omitempty"`
	Objective string           `json:"objective,omitempty"`
	Signals   []ActionSignal   `json:"signals,omitempty"`
	Context   []ActionEvidence `json:"context,omitempty"`
	Windows   []TemporalWindow `json:"windows,omitempty"`
	Metadata  map[string]any   `json:"metadata,omitempty"`
}

type SignalOpportunityPlan struct {
	ID            string                       `json:"id"`
	Surface       string                       `json:"surface"`
	Entity        ActionEntity                 `json:"entity"`
	Objective     string                       `json:"objective"`
	Summary       string                       `json:"summary"`
	Opportunities []SignalOpportunity          `json:"opportunities,omitempty"`
	HandleFirst   SignalOpportunity            `json:"handle_first"`
	Watchlist     []SignalWatchItem            `json:"watchlist,omitempty"`
	MemorySeeds   []QuestMemorySeed            `json:"memory_seeds,omitempty"`
	Integration   SignalOpportunityIntegration `json:"integration"`
	Guardrails    []string                     `json:"guardrails"`
	OpenQuestions []string                     `json:"open_questions,omitempty"`
}

type SignalOpportunity struct {
	ID         string   `json:"id"`
	Title      string   `json:"title"`
	SignalType string   `json:"signal_type,omitempty"`
	Urgency    string   `json:"urgency"`
	Score      float64  `json:"score"`
	Why        string   `json:"why"`
	NextAction string   `json:"next_action"`
	DoneSignal string   `json:"done_signal"`
	Needs      []string `json:"needs,omitempty"`
}

type SignalWatchItem struct {
	Title     string `json:"title"`
	Why       string `json:"why"`
	Cadence   string `json:"cadence"`
	Threshold string `json:"threshold"`
}

type SignalOpportunityIntegration struct {
	ContextualAction []string `json:"contextual_action"`
	Temporal         []string `json:"temporal"`
	WorkGraph        []string `json:"workgraph"`
	Memory           []string `json:"memory"`
	Surface          []string `json:"surface"`
}

func DetectSignalOpportunities(req SignalOpportunityRequest) SignalOpportunityPlan {
	req = normalizeSignalOpportunityRequest(req)
	opps := buildSignalOpportunities(req)
	first := chooseSignalOpportunity(opps)
	watch := buildSignalWatchlist(req, opps)

	return SignalOpportunityPlan{
		ID:            "sig_" + stableBehaviorID(req.Entity.Name+"_"+req.Objective),
		Surface:       normalizeQuestSurface(req.Surface),
		Entity:        req.Entity,
		Objective:     req.Objective,
		Summary:       summarizeSignalOpportunities(req, opps),
		Opportunities: opps,
		HandleFirst:   first,
		Watchlist:     watch,
		MemorySeeds:   signalOpportunityMemorySeeds(req, first),
		Integration: SignalOpportunityIntegration{
			ContextualAction: []string{"Pass handle_first to /contextual-action/plan before drafting external action."},
			Temporal:         []string{"Use /temporal/coordinate to place time-sensitive follow-through into an attention window."},
			WorkGraph:        []string{"Attach accepted opportunities to /workgraph/compile as follow-ups, blockers, or approvals."},
			Memory:           []string{"Persist signal rules only after the user confirms the signal matters."},
			Surface:          contextualActionSurfaceHints(req.Surface),
		},
		Guardrails: []string{
			"Do not claim monitoring, alerts, outreach, or workspace updates happened unless a tool confirms it.",
			"Treat signals as timing evidence, not permission to act.",
			"Require approval before creating persistent watches or external notifications.",
		},
		OpenQuestions: signalOpportunityOpenQuestions(req, first),
	}
}

func normalizeSignalOpportunityRequest(req SignalOpportunityRequest) SignalOpportunityRequest {
	req.Surface = normalizeQuestSurface(req.Surface)
	req.Objective = cleanPlanningText(firstNonEmpty(req.Objective, "identify timely action"))
	req.Entity.Name = cleanPlanningText(firstNonEmpty(req.Entity.Name, req.Entity.ID, "unknown entity"))
	req.Entity.Kind = strings.ToLower(strings.TrimSpace(firstNonEmpty(req.Entity.Kind, "entity")))
	if req.Entity.ID == "" {
		req.Entity.ID = "ent_" + stableBehaviorID(req.Entity.Name)
	}
	for i := range req.Signals {
		req.Signals[i].Title = cleanPlanningText(firstNonEmpty(req.Signals[i].Title, "signal"))
		req.Signals[i].Type = strings.ToLower(strings.TrimSpace(req.Signals[i].Type))
		req.Signals[i].Urgency = strings.ToLower(strings.TrimSpace(firstNonEmpty(req.Signals[i].Urgency, "normal")))
		if req.Signals[i].Confidence <= 0 {
			req.Signals[i].Confidence = 0.55
		}
	}
	if len(req.Signals) == 0 {
		req.Signals = []ActionSignal{{Title: "Clarify which signal matters", Type: "unknown", Urgency: "normal", Confidence: 0.35}}
	}
	return req
}

func buildSignalOpportunities(req SignalOpportunityRequest) []SignalOpportunity {
	var out []SignalOpportunity
	for _, sig := range req.Signals {
		score := signalScore(sig, req)
		out = append(out, SignalOpportunity{
			ID:         "opp_" + stableBehaviorID(req.Entity.Name+"_"+sig.Title),
			Title:      sentenceCase(sig.Title),
			SignalType: firstNonEmpty(sig.Type, "signal"),
			Urgency:    firstNonEmpty(sig.Urgency, "normal"),
			Score:      score,
			Why:        signalOpportunityWhy(sig, score),
			NextAction: signalNextAction(req, sig),
			DoneSignal: "Signal is accepted, dismissed, or converted into a confirmed next action.",
			Needs:      signalNeeds(sig, req),
		})
	}
	sort.SliceStable(out, func(i, j int) bool { return out[i].Score > out[j].Score })
	if len(out) > 6 {
		return out[:6]
	}
	return out
}

func chooseSignalOpportunity(opps []SignalOpportunity) SignalOpportunity {
	if len(opps) == 0 {
		return SignalOpportunity{ID: "opp_none", Title: "No actionable signal", Urgency: "normal", Why: "No signal evidence supplied.", NextAction: "Ask what changed.", DoneSignal: "A relevant signal is named."}
	}
	return opps[0]
}

func buildSignalWatchlist(req SignalOpportunityRequest, opps []SignalOpportunity) []SignalWatchItem {
	var watch []SignalWatchItem
	for _, opp := range opps {
		watch = append(watch, SignalWatchItem{
			Title:     opp.Title,
			Why:       "Repeated signal may indicate a recurring action window.",
			Cadence:   signalCadence(opp.Urgency),
			Threshold: "Resurface when confidence rises or the signal repeats.",
		})
		if len(watch) == 4 {
			break
		}
	}
	return watch
}

func signalScore(sig ActionSignal, req SignalOpportunityRequest) float64 {
	score := sig.Confidence
	switch sig.Urgency {
	case "high", "urgent", "today":
		score += 0.22
	case "medium", "soon":
		score += 0.12
	}
	if len(req.Context) > 0 {
		score += 0.06
	}
	if score > 0.94 {
		return 0.94
	}
	return score
}

func signalOpportunityWhy(sig ActionSignal, score float64) string {
	if score >= 0.72 {
		return "Signal is timely enough to package into action."
	}
	return "Signal may matter, but needs validation before action."
}

func signalNextAction(req SignalOpportunityRequest, sig ActionSignal) string {
	lower := strings.ToLower(req.Objective + " " + sig.Title + " " + sig.Type)
	switch {
	case containsPlanningAny(lower, "follow", "reply", "customer", "client"):
		return "Draft a context-backed follow-up for review."
	case containsPlanningAny(lower, "risk", "security", "vendor"):
		return "Create a reviewed risk/action packet with provenance."
	case containsPlanningAny(lower, "trip", "home", "household"):
		return "Add the signal to a low-friction household checklist."
	default:
		return "Build a contextual action plan before executing."
	}
}

func signalNeeds(sig ActionSignal, req SignalOpportunityRequest) []string {
	var needs []string
	if sig.Confidence < 0.6 {
		needs = append(needs, "signal validation")
	}
	if len(req.Context) == 0 {
		needs = append(needs, "supporting context")
	}
	return needs
}

func signalCadence(urgency string) string {
	switch urgency {
	case "high", "urgent", "today":
		return "same day until resolved"
	case "medium", "soon":
		return "every few days while active"
	default:
		return "weekly or when related context changes"
	}
}

func summarizeSignalOpportunities(req SignalOpportunityRequest, opps []SignalOpportunity) string {
	return sentenceCase(req.Objective) + " for " + req.Entity.Name + " produced " + intToMomentumString(len(opps)) + " signal opportunities."
}

func signalOpportunityMemorySeeds(req SignalOpportunityRequest, first SignalOpportunity) []QuestMemorySeed {
	return []QuestMemorySeed{
		{Key: "signal_entity", Value: req.Entity.Name, Importance: 0.58},
		{Key: "signal_objective", Value: req.Objective, Importance: 0.56},
		{Key: "signal_handle_first", Value: first.Title, Importance: 0.68},
	}
}

func signalOpportunityOpenQuestions(req SignalOpportunityRequest, first SignalOpportunity) []string {
	var qs []string
	if len(first.Needs) > 0 {
		qs = append(qs, "What evidence validates this signal?")
	}
	if len(req.Windows) == 0 {
		qs = append(qs, "When should ORI resurface this if it remains unresolved?")
	}
	return qs
}

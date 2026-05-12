package cognition

import (
	"sort"
	"strconv"
	"strings"
)

type CommitmentResourceRequest struct {
	Surface          string                    `json:"surface,omitempty"`
	Context          string                    `json:"context,omitempty"`
	DecisionQuestion string                    `json:"decision_question,omitempty"`
	ProposedAction   ResourceProposedAction    `json:"proposed_action,omitempty"`
	ResourcePools    []ResourcePool            `json:"resource_pools,omitempty"`
	Commitments      []ResourceCommitment      `json:"commitments,omitempty"`
	DriftEvent       ResourceDriftEvent        `json:"drift_event,omitempty"`
	Preferences      ResourceReasonPreferences `json:"preferences,omitempty"`
	Metadata         map[string]interface{}    `json:"metadata,omitempty"`
}

type ResourceProposedAction struct {
	Title        string  `json:"title,omitempty"`
	ResourceType string  `json:"resource_type,omitempty"`
	Amount       float64 `json:"amount,omitempty"`
	Capacity     int     `json:"capacity,omitempty"`
	DueWindow    string  `json:"due_window,omitempty"`
	Why          string  `json:"why,omitempty"`
}

type ResourcePool struct {
	ID         string  `json:"id,omitempty"`
	Type       string  `json:"type,omitempty"`
	Label      string  `json:"label,omitempty"`
	Owner      string  `json:"owner,omitempty"`
	Amount     float64 `json:"amount,omitempty"`
	Capacity   int     `json:"capacity,omitempty"`
	Unit       string  `json:"unit,omitempty"`
	Confidence float64 `json:"confidence,omitempty"`
	Source     string  `json:"source,omitempty"`
	Protected  bool    `json:"protected,omitempty"`
}

type ResourceCommitment struct {
	ID              string   `json:"id,omitempty"`
	Title           string   `json:"title,omitempty"`
	ResourceType    string   `json:"resource_type,omitempty"`
	Claim           float64  `json:"claim,omitempty"`
	Capacity        int      `json:"capacity,omitempty"`
	DueWindow       string   `json:"due_window,omitempty"`
	Priority        string   `json:"priority,omitempty"`
	Flexibility     string   `json:"flexibility,omitempty"`
	Owner           string   `json:"owner,omitempty"`
	Recurrence      string   `json:"recurrence,omitempty"`
	Provenance      string   `json:"provenance,omitempty"`
	EmotionalWeight string   `json:"emotional_weight,omitempty"`
	Tags            []string `json:"tags,omitempty"`
}

type ResourceDriftEvent struct {
	Title        string  `json:"title,omitempty"`
	ResourceType string  `json:"resource_type,omitempty"`
	Amount       float64 `json:"amount,omitempty"`
	Capacity     int     `json:"capacity,omitempty"`
	Reason       string  `json:"reason,omitempty"`
	Time         string  `json:"time,omitempty"`
}

type ResourceReasonPreferences struct {
	MaxOptions            int  `json:"max_options,omitempty"`
	PreferLeastDisruptive bool `json:"prefer_least_disruptive,omitempty"`
	OverwhelmSensitive    bool `json:"overwhelm_sensitive,omitempty"`
	ProtectHighPriority   bool `json:"protect_high_priority,omitempty"`
	RequireHumanApproval  bool `json:"require_human_approval,omitempty"`
}

type CommitmentResourceReasoningPlan struct {
	ID                   string                        `json:"id"`
	Surface              string                        `json:"surface"`
	Context              string                        `json:"context,omitempty"`
	DecisionQuestion     string                        `json:"decision_question"`
	Summary              string                        `json:"summary"`
	ResourceReality      ResourceReality               `json:"resource_reality"`
	ProtectedCommitments []ResourceCommitmentImpact    `json:"protected_commitments,omitempty"`
	AffectedCommitments  []ResourceCommitmentImpact    `json:"affected_commitments,omitempty"`
	Options              []ResourceTradeoffOption      `json:"options,omitempty"`
	LeastDisruptive      ResourceTradeoffOption        `json:"least_disruptive"`
	Recovery             ResourceRecoveryPlan          `json:"recovery,omitempty"`
	PermissionLanguage   string                        `json:"permission_language"`
	MemorySeeds          []QuestMemorySeed             `json:"memory_seeds,omitempty"`
	Integration          CommitmentResourceIntegration `json:"integration"`
	Guardrails           []string                      `json:"guardrails"`
	OpenQuestions        []string                      `json:"open_questions,omitempty"`
}

type ResourceReality struct {
	ResourceType      string   `json:"resource_type"`
	Available         float64  `json:"available"`
	Requested         float64  `json:"requested"`
	Unit              string   `json:"unit,omitempty"`
	Confidence        float64  `json:"confidence"`
	Status            string   `json:"status"`
	Uncertainty       []string `json:"uncertainty,omitempty"`
	HiddenObligations []string `json:"hidden_obligations,omitempty"`
}

type ResourceCommitmentImpact struct {
	ID           string  `json:"id"`
	Title        string  `json:"title"`
	ResourceType string  `json:"resource_type"`
	Claim        float64 `json:"claim,omitempty"`
	DueWindow    string  `json:"due_window,omitempty"`
	Priority     string  `json:"priority"`
	Flexibility  string  `json:"flexibility"`
	Why          string  `json:"why"`
	Protected    bool    `json:"protected"`
}

type ResourceTradeoffOption struct {
	ID              string   `json:"id"`
	Title           string   `json:"title"`
	Posture         string   `json:"posture"`
	Why             string   `json:"why"`
	Moves           []string `json:"moves,omitempty"`
	Protected       []string `json:"protected,omitempty"`
	Tradeoffs       []string `json:"tradeoffs,omitempty"`
	ResidualRisk    []string `json:"residual_risk,omitempty"`
	NeedsApproval   bool     `json:"needs_approval"`
	DisruptionScore float64  `json:"disruption_score"`
}

type ResourceRecoveryPlan struct {
	Needed        bool     `json:"needed"`
	DriftEvent    string   `json:"drift_event,omitempty"`
	RepairLine    string   `json:"repair_line,omitempty"`
	RepairOptions []string `json:"repair_options,omitempty"`
	FollowUp      string   `json:"follow_up,omitempty"`
}

type CommitmentResourceIntegration struct {
	Memory    []string `json:"memory"`
	Chronos   []string `json:"chronos"`
	WorkGraph []string `json:"workgraph"`
	Temporal  []string `json:"temporal"`
	Intent    []string `json:"intent"`
	Behavior  []string `json:"behavior"`
	Surface   []string `json:"surface"`
}

// ReasonAboutCommitmentResources answers "can we do this?" through explicit
// commitments and tradeoffs. It is not finance advice: clients supply the
// source-of-truth resources, and ORI returns bounded reasoning.
func ReasonAboutCommitmentResources(req CommitmentResourceRequest) CommitmentResourceReasoningPlan {
	req = normalizeCommitmentResourceRequest(req)
	reality := buildResourceReality(req)
	protected := buildProtectedCommitmentImpacts(req)
	affected := buildAffectedCommitmentImpacts(req, reality)
	options := buildResourceTradeoffOptions(req, reality, protected, affected)
	least := chooseLeastDisruptiveOption(options)
	recovery := buildResourceRecoveryPlan(req, least)

	return CommitmentResourceReasoningPlan{
		ID:                   "res_" + stableBehaviorID(req.DecisionQuestion+"_"+req.ProposedAction.Title),
		Surface:              normalizeQuestSurface(req.Surface),
		Context:              req.Context,
		DecisionQuestion:     req.DecisionQuestion,
		Summary:              summarizeResourceReasoning(req, reality, affected),
		ResourceReality:      reality,
		ProtectedCommitments: protected,
		AffectedCommitments:  affected,
		Options:              options,
		LeastDisruptive:      least,
		Recovery:             recovery,
		PermissionLanguage:   resourcePermissionLanguage(req, reality, least),
		MemorySeeds:          resourceMemorySeeds(req, reality, least),
		Integration: CommitmentResourceIntegration{
			Memory:    []string{"Persist recurring commitments, priorities, flexibility, and corrections only after confirmation."},
			Chronos:   []string{"Surface future commitments before they become urgent or emotionally loaded."},
			WorkGraph: []string{"Send operator approvals, vendor renewals, payroll timing, blockers, and owners to /workgraph/compile when they become durable work state."},
			Temporal:  []string{"Use /temporal/coordinate when a decision depends on due windows, attention windows, or delayed options."},
			Intent:    []string{"Attach accepted tradeoff rationale to /intent/timeline so future agents know why the plan changed."},
			Behavior:  []string{"Use behavior reflection for non-shaming recovery if drift repeats."},
			Surface:   resourceSurfaceHints(req.Surface),
		},
		Guardrails: []string{
			"Do not claim affordability, compliance, tax, credit, debt, investment, or legal certainty.",
			"Do not import accounts, initiate payments, move money, or mutate records unless an external tool confirms it.",
			"Frame drift as reallocation, not personal failure.",
			"Keep uncertainty visible when commitments or resource pools are incomplete.",
		},
		OpenQuestions: resourceOpenQuestions(req, reality),
	}
}

func normalizeCommitmentResourceRequest(req CommitmentResourceRequest) CommitmentResourceRequest {
	req.Surface = normalizeQuestSurface(req.Surface)
	req.Context = cleanPlanningText(req.Context)
	req.DecisionQuestion = cleanPlanningText(firstNonEmpty(req.DecisionQuestion, req.ProposedAction.Title, "Can we do this?"))
	req.ProposedAction.Title = cleanPlanningText(firstNonEmpty(req.ProposedAction.Title, req.DecisionQuestion, "proposed choice"))
	req.ProposedAction.ResourceType = normalizeResourceType(req.ProposedAction.ResourceType)
	req.ProposedAction.DueWindow = cleanPlanningText(req.ProposedAction.DueWindow)
	req.ProposedAction.Why = cleanPlanningText(req.ProposedAction.Why)
	if req.Preferences.MaxOptions <= 0 {
		req.Preferences.MaxOptions = 4
	}
	if req.Preferences.OverwhelmSensitive && req.Preferences.MaxOptions > 3 {
		req.Preferences.MaxOptions = 3
	}
	if !req.Preferences.PreferLeastDisruptive {
		req.Preferences.PreferLeastDisruptive = true
	}
	if !req.Preferences.ProtectHighPriority {
		req.Preferences.ProtectHighPriority = true
	}
	for i := range req.ResourcePools {
		req.ResourcePools[i].ID = cleanPlanningText(req.ResourcePools[i].ID)
		req.ResourcePools[i].Type = normalizeResourceType(req.ResourcePools[i].Type)
		req.ResourcePools[i].Label = cleanPlanningText(firstNonEmpty(req.ResourcePools[i].Label, req.ResourcePools[i].Type+" pool"))
		req.ResourcePools[i].Owner = cleanPlanningText(req.ResourcePools[i].Owner)
		req.ResourcePools[i].Unit = cleanPlanningText(req.ResourcePools[i].Unit)
		req.ResourcePools[i].Source = cleanPlanningText(req.ResourcePools[i].Source)
		if req.ResourcePools[i].Confidence <= 0 {
			req.ResourcePools[i].Confidence = 0.55
		}
		if req.ResourcePools[i].ID == "" {
			req.ResourcePools[i].ID = "pool_" + stableBehaviorID(req.ResourcePools[i].Label)
		}
	}
	for i := range req.Commitments {
		req.Commitments[i].ID = cleanPlanningText(req.Commitments[i].ID)
		req.Commitments[i].Title = cleanPlanningText(firstNonEmpty(req.Commitments[i].Title, "unnamed commitment"))
		req.Commitments[i].ResourceType = normalizeResourceType(firstNonEmpty(req.Commitments[i].ResourceType, req.ProposedAction.ResourceType))
		req.Commitments[i].DueWindow = cleanPlanningText(req.Commitments[i].DueWindow)
		req.Commitments[i].Priority = normalizeResourcePriority(req.Commitments[i].Priority)
		req.Commitments[i].Flexibility = normalizeResourceFlexibility(req.Commitments[i].Flexibility)
		req.Commitments[i].Owner = cleanPlanningText(req.Commitments[i].Owner)
		req.Commitments[i].Recurrence = cleanPlanningText(req.Commitments[i].Recurrence)
		req.Commitments[i].Provenance = cleanPlanningText(req.Commitments[i].Provenance)
		req.Commitments[i].EmotionalWeight = strings.ToLower(strings.TrimSpace(req.Commitments[i].EmotionalWeight))
		req.Commitments[i].Tags = uniqueActionStrings(req.Commitments[i].Tags)
		if req.Commitments[i].ID == "" {
			req.Commitments[i].ID = "com_" + stableBehaviorID(req.Commitments[i].Title)
		}
	}
	req.DriftEvent.Title = cleanPlanningText(req.DriftEvent.Title)
	req.DriftEvent.ResourceType = normalizeResourceType(firstNonEmpty(req.DriftEvent.ResourceType, req.ProposedAction.ResourceType))
	req.DriftEvent.Reason = cleanPlanningText(req.DriftEvent.Reason)
	req.DriftEvent.Time = cleanPlanningText(req.DriftEvent.Time)
	if len(req.ResourcePools) == 0 {
		req.ResourcePools = []ResourcePool{{ID: "pool_unknown", Type: firstNonEmpty(req.ProposedAction.ResourceType, "capacity"), Label: "Unknown resource pool", Confidence: 0.25}}
	}
	if req.ProposedAction.ResourceType == "" {
		req.ProposedAction.ResourceType = req.ResourcePools[0].Type
	}
	return req
}

func buildResourceReality(req CommitmentResourceRequest) ResourceReality {
	resourceType := req.ProposedAction.ResourceType
	available := 0.0
	confidence := 0.0
	unit := ""
	var uncertainty []string
	for _, pool := range req.ResourcePools {
		if pool.Type != resourceType {
			continue
		}
		if pool.Amount > 0 {
			available += pool.Amount
		} else if pool.Capacity > 0 {
			available += float64(pool.Capacity)
		}
		confidence += pool.Confidence
		if unit == "" {
			unit = pool.Unit
		}
		if pool.Source == "" {
			uncertainty = append(uncertainty, pool.Label+" has no source.")
		}
	}
	if confidence > 0 {
		confidence = confidence / float64(maxResourceInt(1, countResourcePools(req.ResourcePools, resourceType)))
	} else {
		confidence = 0.25
		uncertainty = append(uncertainty, "No matching resource pool supplied.")
	}
	requested := req.ProposedAction.Amount
	if requested <= 0 && req.ProposedAction.Capacity > 0 {
		requested = float64(req.ProposedAction.Capacity)
	}
	if requested <= 0 && req.DriftEvent.Amount > 0 {
		requested = req.DriftEvent.Amount
	}
	if requested <= 0 && req.DriftEvent.Capacity > 0 {
		requested = float64(req.DriftEvent.Capacity)
	}
	if requested <= 0 {
		uncertainty = append(uncertainty, "Proposed resource claim is missing.")
	}
	status := "possible"
	if requested <= 0 || available <= 0 {
		status = "unknown"
	} else if requested > available {
		status = "not_yet"
	} else if requested > available*0.75 {
		status = "possible_with_tradeoff"
	}
	return ResourceReality{
		ResourceType:      resourceType,
		Available:         available,
		Requested:         requested,
		Unit:              unit,
		Confidence:        confidence,
		Status:            status,
		Uncertainty:       uncertainty,
		HiddenObligations: inferHiddenResourceObligations(req),
	}
}

func buildProtectedCommitmentImpacts(req CommitmentResourceRequest) []ResourceCommitmentImpact {
	var out []ResourceCommitmentImpact
	for _, commitment := range req.Commitments {
		if resourceCommitmentProtected(commitment, req) {
			out = append(out, resourceCommitmentImpact(commitment, "Protected because priority, due window, or emotional weight makes it expensive to disturb.", true))
		}
	}
	if len(out) > 6 {
		return out[:6]
	}
	return out
}

func buildAffectedCommitmentImpacts(req CommitmentResourceRequest, reality ResourceReality) []ResourceCommitmentImpact {
	var out []ResourceCommitmentImpact
	for _, commitment := range req.Commitments {
		if commitment.ResourceType != reality.ResourceType {
			continue
		}
		if resourceCommitmentProtected(commitment, req) {
			continue
		}
		out = append(out, resourceCommitmentImpact(commitment, "Flexible enough to consider moving if the choice matters.", false))
	}
	sort.SliceStable(out, func(i, j int) bool {
		return resourceImpactScore(out[i]) < resourceImpactScore(out[j])
	})
	if len(out) > 6 {
		return out[:6]
	}
	return out
}

func buildResourceTradeoffOptions(req CommitmentResourceRequest, reality ResourceReality, protected, affected []ResourceCommitmentImpact) []ResourceTradeoffOption {
	var options []ResourceTradeoffOption
	if reality.Status == "possible" {
		options = append(options, ResourceTradeoffOption{
			ID:              "opt_keep_plan",
			Title:           "Do it from the supplied resource pool",
			Posture:         "yes",
			Why:             "Current supplied capacity appears enough for this choice while protected commitments stay visible.",
			Moves:           []string{"Proceed only if the supplied resource pool is current."},
			Protected:       impactTitles(protected),
			Tradeoffs:       resourcePoolTradeoffLine(req, reality),
			ResidualRisk:    reality.Uncertainty,
			NeedsApproval:   req.Preferences.RequireHumanApproval,
			DisruptionScore: 0.12,
		})
	}
	if len(affected) > 0 {
		first := affected[0]
		options = append(options, ResourceTradeoffOption{
			ID:              "opt_move_" + stableBehaviorID(first.Title),
			Title:           "Yes, if we move " + first.Title,
			Posture:         "yes_if",
			Why:             "This keeps higher-priority commitments protected while making the tradeoff explicit.",
			Moves:           []string{"Move or reduce " + first.Title + "."},
			Protected:       impactTitles(protected),
			Tradeoffs:       []string{first.Title + " changes."},
			ResidualRisk:    reality.Uncertainty,
			NeedsApproval:   true,
			DisruptionScore: resourceImpactScore(first),
		})
	}
	options = append(options, ResourceTradeoffOption{
		ID:              "opt_wait",
		Title:           "Wait until the next safer window",
		Posture:         "not_yet",
		Why:             "Waiting preserves current commitments and reduces regret risk.",
		Moves:           []string{"Keep the current plan intact.", "Revisit when the next resource pool refreshes or uncertainty clears."},
		Protected:       impactTitles(protected),
		ResidualRisk:    []string{"The opportunity may no longer be available."},
		NeedsApproval:   false,
		DisruptionScore: 0.24,
	})
	if len(affected) >= 2 {
		first := affected[0]
		second := affected[1]
		options = append(options, ResourceTradeoffOption{
			ID:              "opt_split_scope",
			Title:           "Choose a smaller version now",
			Posture:         "smaller_scope",
			Why:             "A smaller scope can preserve more commitments while still honoring the underlying desire.",
			Moves:           []string{"Reduce the proposed claim.", "Move a smaller amount from " + first.Title + " or " + second.Title + "."},
			Protected:       impactTitles(protected),
			Tradeoffs:       []string{first.Title + " or " + second.Title + " may move slightly."},
			ResidualRisk:    reality.Uncertainty,
			NeedsApproval:   true,
			DisruptionScore: (resourceImpactScore(first) + resourceImpactScore(second)) / 2,
		})
	}
	sort.SliceStable(options, func(i, j int) bool { return options[i].DisruptionScore < options[j].DisruptionScore })
	if len(options) > req.Preferences.MaxOptions {
		return options[:req.Preferences.MaxOptions]
	}
	return options
}

func chooseLeastDisruptiveOption(options []ResourceTradeoffOption) ResourceTradeoffOption {
	if len(options) == 0 {
		return ResourceTradeoffOption{ID: "opt_clarify", Title: "Clarify the resource and commitments first", Posture: "unknown", Why: "There is not enough resource state to reason safely.", Moves: []string{"Name the resource pool.", "Name protected commitments."}, NeedsApproval: false, DisruptionScore: 1}
	}
	return options[0]
}

func buildResourceRecoveryPlan(req CommitmentResourceRequest, least ResourceTradeoffOption) ResourceRecoveryPlan {
	if req.DriftEvent.Title == "" && req.DriftEvent.Amount <= 0 && req.DriftEvent.Capacity <= 0 {
		return ResourceRecoveryPlan{}
	}
	return ResourceRecoveryPlan{
		Needed:        true,
		DriftEvent:    firstNonEmpty(req.DriftEvent.Title, "plan drift"),
		RepairLine:    "Not a failure. Treat this as a reallocation problem and protect the highest-priority commitments first.",
		RepairOptions: append([]string{least.Title}, least.Moves...),
		FollowUp:      "Review whether this drift is recurring and should become a captured commitment.",
	}
}

func resourceCommitmentImpact(commitment ResourceCommitment, why string, protected bool) ResourceCommitmentImpact {
	claim := commitment.Claim
	if claim <= 0 && commitment.Capacity > 0 {
		claim = float64(commitment.Capacity)
	}
	return ResourceCommitmentImpact{
		ID:           commitment.ID,
		Title:        commitment.Title,
		ResourceType: commitment.ResourceType,
		Claim:        claim,
		DueWindow:    commitment.DueWindow,
		Priority:     commitment.Priority,
		Flexibility:  commitment.Flexibility,
		Why:          why,
		Protected:    protected,
	}
}

func resourceCommitmentProtected(commitment ResourceCommitment, req CommitmentResourceRequest) bool {
	if !req.Preferences.ProtectHighPriority {
		return false
	}
	return commitment.Priority == "critical" || commitment.Priority == "high" || commitment.Flexibility == "fixed" || commitment.EmotionalWeight == "high"
}

func resourceImpactScore(impact ResourceCommitmentImpact) float64 {
	score := 0.35
	switch impact.Priority {
	case "low":
		score += 0.05
	case "medium":
		score += 0.18
	case "high":
		score += 0.42
	case "critical":
		score += 0.58
	}
	switch impact.Flexibility {
	case "flexible":
		score -= 0.18
	case "movable":
		score -= 0.08
	case "fixed":
		score += 0.28
	}
	if score < 0.05 {
		return 0.05
	}
	if score > 0.95 {
		return 0.95
	}
	return score
}

func resourcePermissionLanguage(req CommitmentResourceRequest, reality ResourceReality, least ResourceTradeoffOption) string {
	prefix := "Based on the commitments supplied, "
	switch least.Posture {
	case "yes":
		return prefix + "yes. This appears to keep protected commitments intact. I may be missing obligations not yet captured."
	case "yes_if":
		return prefix + "yes, if you choose the tradeoff: " + strings.Join(least.Tradeoffs, " ")
	case "smaller_scope":
		return prefix + "a smaller version looks safer than the full choice."
	case "not_yet":
		return prefix + "not yet is the calmest answer if you want to protect the current plan."
	default:
		if reality.Status == "unknown" {
			return "I do not have enough resource state to answer safely yet. Name the pool and protected commitments first."
		}
		return prefix + "the real decision is which commitment should move, not whether you did anything wrong."
	}
}

func resourcePoolTradeoffLine(req CommitmentResourceRequest, reality ResourceReality) []string {
	if reality.Requested <= 0 || reality.Available <= 0 {
		return nil
	}
	remaining := reality.Available - reality.Requested
	if remaining < 0 {
		return []string{"The proposed choice exceeds the supplied pool by " + formatResourceAmount(-remaining, reality.Unit) + "."}
	}
	return []string{"The supplied pool would have about " + formatResourceAmount(remaining, reality.Unit) + " left."}
}

func formatResourceAmount(value float64, unit string) string {
	text := strconv.FormatFloat(value, 'f', -1, 64)
	if unit == "" {
		return text
	}
	return text + " " + unit
}

func summarizeResourceReasoning(req CommitmentResourceRequest, reality ResourceReality, affected []ResourceCommitmentImpact) string {
	return sentenceCase(req.DecisionQuestion) + " checks " + reality.ResourceType + " against " + strconv.Itoa(len(req.Commitments)) + " commitments and " + strconv.Itoa(len(affected)) + " movable tradeoffs."
}

func resourceMemorySeeds(req CommitmentResourceRequest, reality ResourceReality, least ResourceTradeoffOption) []QuestMemorySeed {
	return []QuestMemorySeed{
		{Key: "resource_context", Value: req.Context, Importance: 0.54},
		{Key: "resource_type", Value: reality.ResourceType, Importance: 0.62},
		{Key: "resource_least_disruptive", Value: least.Title, Importance: 0.68},
	}
}

func resourceOpenQuestions(req CommitmentResourceRequest, reality ResourceReality) []string {
	var qs []string
	if len(req.ResourcePools) == 0 || reality.Available <= 0 {
		qs = append(qs, "What resource pool is available right now?")
	}
	if len(req.Commitments) == 0 {
		qs = append(qs, "What commitments must stay protected?")
	}
	if len(reality.HiddenObligations) > 0 {
		qs = append(qs, "Are any likely hidden obligations missing from the plan?")
	}
	if len(reality.Uncertainty) > 0 {
		qs = append(qs, "Which uncertainty should be confirmed before acting?")
	}
	return qs
}

func normalizeResourceType(value string) string {
	value = strings.ToLower(strings.TrimSpace(value))
	switch value {
	case "cash", "cashflow", "budget", "dollars":
		return "money"
	case "mins", "minutes", "hours":
		return "time"
	case "":
		return ""
	default:
		return value
	}
}

func normalizeResourcePriority(value string) string {
	switch strings.ToLower(strings.TrimSpace(value)) {
	case "critical", "must", "must_protect":
		return "critical"
	case "high", "important":
		return "high"
	case "low", "nice_to_have":
		return "low"
	default:
		return "medium"
	}
}

func normalizeResourceFlexibility(value string) string {
	switch strings.ToLower(strings.TrimSpace(value)) {
	case "fixed", "locked", "nonnegotiable":
		return "fixed"
	case "flexible", "soft":
		return "flexible"
	case "movable", "delayable", "adjustable":
		return "movable"
	default:
		return "movable"
	}
}

func inferHiddenResourceObligations(req CommitmentResourceRequest) []string {
	lower := strings.ToLower(req.Context + " " + req.DecisionQuestion + " " + req.ProposedAction.Title)
	var out []string
	if containsPlanningAny(lower, "home", "household", "family", "school", "kid") {
		out = append(out, "Check non-monthly household, school, pet, car, health, holiday, or family obligations.")
	}
	if containsPlanningAny(lower, "studio", "business", "operator", "client", "invoice", "payroll") {
		out = append(out, "Check payroll, vendor renewals, tax set-asides, receivable timing, and approval obligations.")
	}
	if containsPlanningAny(lower, "dev", "release", "compute", "dependency") {
		out = append(out, "Check release windows, compute budget, review capacity, and rollback risk.")
	}
	return out
}

func impactTitles(values []ResourceCommitmentImpact) []string {
	out := make([]string, 0, len(values))
	for _, value := range values {
		out = append(out, value.Title)
	}
	return out
}

func countResourcePools(pools []ResourcePool, resourceType string) int {
	count := 0
	for _, pool := range pools {
		if pool.Type == resourceType {
			count++
		}
	}
	return count
}

func maxResourceInt(a, b int) int {
	if a > b {
		return a
	}
	return b
}

func resourceSurfaceHints(surface string) []string {
	switch normalizeQuestSurface(surface) {
	case "home":
		return []string{"Use household language: what stays protected, what can move, and what the calmest choice is."}
	case "studio":
		return []string{"Use operator language: approvals, cashflow timing, buffer protection, and least-disruptive tradeoffs."}
	case "dev":
		return []string{"Use builder language: time, release risk, compute budget, dependency timing, and rollback capacity."}
	case "red":
		return []string{"Use assurance language: analyst capacity, urgency, remediation risk, and protected response windows."}
	default:
		return []string{"Keep resource reasoning app-neutral, bounded, and non-shaming."}
	}
}

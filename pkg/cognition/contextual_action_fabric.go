package cognition

import (
	"sort"
	"strings"
)

type ContextualActionRequest struct {
	Surface         string                 `json:"surface,omitempty"`
	Entity          ActionEntity           `json:"entity,omitempty"`
	Objective       string                 `json:"objective,omitempty"`
	BusinessContext string                 `json:"business_context,omitempty"`
	AvailableTools  []string               `json:"available_tools,omitempty"`
	Evidence        []ActionEvidence       `json:"evidence,omitempty"`
	Signals         []ActionSignal         `json:"signals,omitempty"`
	Constraints     []string               `json:"constraints,omitempty"`
	Metadata        map[string]interface{} `json:"metadata,omitempty"`
}

type ActionEntity struct {
	ID     string            `json:"id,omitempty"`
	Name   string            `json:"name,omitempty"`
	Kind   string            `json:"kind,omitempty"`
	Fields map[string]string `json:"fields,omitempty"`
}

type ActionEvidence struct {
	Source     string  `json:"source,omitempty"`
	Type       string  `json:"type,omitempty"`
	Title      string  `json:"title,omitempty"`
	Content    string  `json:"content,omitempty"`
	Confidence float64 `json:"confidence,omitempty"`
	Cost       string  `json:"cost,omitempty"`
}

type ActionSignal struct {
	Title      string  `json:"title,omitempty"`
	Type       string  `json:"type,omitempty"`
	Urgency    string  `json:"urgency,omitempty"`
	Confidence float64 `json:"confidence,omitempty"`
}

type ContextualActionPlan struct {
	ID            string                           `json:"id"`
	Surface       string                           `json:"surface"`
	Entity        ActionEntity                     `json:"entity"`
	Objective     string                           `json:"objective"`
	Summary       string                           `json:"summary"`
	EntityProfile ActionEntityProfile              `json:"entity_profile"`
	EvidencePlan  []EvidenceAcquisitionStep        `json:"evidence_plan,omitempty"`
	Evidence      []ActionEvidence                 `json:"evidence,omitempty"`
	Score         ActionFitScore                   `json:"score"`
	Recommended   []ContextualActionRecommendation `json:"recommended,omitempty"`
	SkillFunction SkillFunctionCandidate           `json:"skill_function"`
	MemorySeeds   []QuestMemorySeed                `json:"memory_seeds,omitempty"`
	Integration   ContextualActionIntegration      `json:"integration"`
	Guardrails    []string                         `json:"guardrails"`
	OpenQuestions []string                         `json:"open_questions,omitempty"`
}

type ActionEntityProfile struct {
	Label       string            `json:"label"`
	Kind        string            `json:"kind"`
	KnownFields map[string]string `json:"known_fields,omitempty"`
	Missing     []string          `json:"missing,omitempty"`
	Confidence  float64           `json:"confidence"`
}

type EvidenceAcquisitionStep struct {
	Type        string   `json:"type"`
	Providers   []string `json:"providers,omitempty"`
	Reason      string   `json:"reason"`
	StopWhen    string   `json:"stop_when"`
	CanParallel bool     `json:"can_parallel"`
}

type ActionFitScore struct {
	Score      float64  `json:"score"`
	Level      string   `json:"level"`
	Reasons    []string `json:"reasons,omitempty"`
	RiskFlags  []string `json:"risk_flags,omitempty"`
	Confidence float64  `json:"confidence"`
}

type ContextualActionRecommendation struct {
	Title         string   `json:"title"`
	Why           string   `json:"why"`
	Autonomy      string   `json:"autonomy"`
	Needs         []string `json:"needs,omitempty"`
	DoneSignal    string   `json:"done_signal"`
	NeedsApproval bool     `json:"needs_approval"`
}

type SkillFunctionCandidate struct {
	Name           string   `json:"name"`
	Inputs         []string `json:"inputs"`
	RetrievalPlan  []string `json:"retrieval_plan"`
	Validation     []string `json:"validation"`
	OutputSchema   []string `json:"output_schema"`
	AllowedActions []string `json:"allowed_actions"`
	CostPolicy     string   `json:"cost_policy"`
}

type ContextualActionIntegration struct {
	WorkGraph []string `json:"workgraph"`
	Execution []string `json:"execution"`
	Procedure []string `json:"procedure"`
	Memory    []string `json:"memory"`
	Temporal  []string `json:"temporal"`
	Surface   []string `json:"surface"`
}

func BuildContextualActionPlan(req ContextualActionRequest) ContextualActionPlan {
	req = normalizeContextualActionRequest(req)
	profile := buildActionEntityProfile(req)
	evidencePlan := buildEvidencePlan(req, profile)
	score := scoreContextualAction(req, profile)
	recommended := buildContextualRecommendations(req, profile, score)
	skill := buildSkillFunctionCandidate(req, evidencePlan)

	return ContextualActionPlan{
		ID:            "caf_" + stableBehaviorID(req.Entity.Name+"_"+req.Objective),
		Surface:       normalizeQuestSurface(req.Surface),
		Entity:        req.Entity,
		Objective:     req.Objective,
		Summary:       summarizeContextualAction(req, profile, score),
		EntityProfile: profile,
		EvidencePlan:  evidencePlan,
		Evidence:      req.Evidence,
		Score:         score,
		Recommended:   recommended,
		SkillFunction: skill,
		MemorySeeds:   contextualActionMemorySeeds(req, score),
		Integration: ContextualActionIntegration{
			WorkGraph: []string{"Attach entity action plans to /workgraph/compile when they become durable operator work."},
			Execution: []string{"Send approved recommendations to /execution/orchestrate before mutating tasks or external systems."},
			Procedure: []string{"Promote repeated evidence/action logic into /procedure/compile after successful reuse."},
			Memory:    []string{"Persist source-backed entity facts, scoring logic, and workflow preferences only after confirmation."},
			Temporal:  []string{"Use /temporal/coordinate for time-sensitive signals and follow-through windows."},
			Surface:   contextualActionSurfaceHints(req.Surface),
		},
		Guardrails: []string{
			"Do not claim enrichment, CRM updates, outreach, alerts, or external actions happened unless a tool confirms it.",
			"Keep evidence provenance and confidence visible before recommending action.",
			"Require approval before external communication, record mutation, paid provider use, or durable skill registration.",
		},
		OpenQuestions: contextualActionOpenQuestions(profile, score),
	}
}

func normalizeContextualActionRequest(req ContextualActionRequest) ContextualActionRequest {
	req.Surface = normalizeQuestSurface(req.Surface)
	req.Objective = cleanPlanningText(firstNonEmpty(req.Objective, "decide the next action"))
	req.BusinessContext = cleanPlanningText(req.BusinessContext)
	req.Entity.Name = cleanPlanningText(firstNonEmpty(req.Entity.Name, req.Entity.ID, "unknown entity"))
	req.Entity.Kind = strings.ToLower(strings.TrimSpace(firstNonEmpty(req.Entity.Kind, "entity")))
	if req.Entity.ID == "" {
		req.Entity.ID = "ent_" + stableBehaviorID(req.Entity.Name)
	}
	req.AvailableTools = uniqueActionStrings(req.AvailableTools)
	req.Constraints = uniqueActionStrings(req.Constraints)
	for i := range req.Evidence {
		req.Evidence[i].Source = cleanPlanningText(req.Evidence[i].Source)
		req.Evidence[i].Type = strings.ToLower(strings.TrimSpace(req.Evidence[i].Type))
		req.Evidence[i].Title = cleanPlanningText(firstNonEmpty(req.Evidence[i].Title, req.Evidence[i].Content, "evidence"))
		req.Evidence[i].Content = cleanPlanningText(req.Evidence[i].Content)
		if req.Evidence[i].Confidence <= 0 {
			req.Evidence[i].Confidence = 0.55
		}
	}
	for i := range req.Signals {
		req.Signals[i].Title = cleanPlanningText(req.Signals[i].Title)
		req.Signals[i].Type = strings.ToLower(strings.TrimSpace(req.Signals[i].Type))
		req.Signals[i].Urgency = strings.ToLower(strings.TrimSpace(req.Signals[i].Urgency))
		if req.Signals[i].Confidence <= 0 {
			req.Signals[i].Confidence = 0.55
		}
	}
	return req
}

func buildActionEntityProfile(req ContextualActionRequest) ActionEntityProfile {
	missing := []string{}
	fields := req.Entity.Fields
	if fields == nil {
		fields = map[string]string{}
	}
	for _, key := range []string{"domain", "owner", "stage", "fit", "latest_signal"} {
		if strings.TrimSpace(fields[key]) == "" {
			missing = append(missing, key)
		}
	}
	conf := 0.42 + float64(len(fields))*0.06 + float64(len(req.Evidence))*0.05
	if conf > 0.86 {
		conf = 0.86
	}
	return ActionEntityProfile{Label: req.Entity.Name, Kind: req.Entity.Kind, KnownFields: fields, Missing: missing, Confidence: conf}
}

func buildEvidencePlan(req ContextualActionRequest, profile ActionEntityProfile) []EvidenceAcquisitionStep {
	var steps []EvidenceAcquisitionStep
	for _, missing := range profile.Missing {
		steps = append(steps, EvidenceAcquisitionStep{
			Type:        missing,
			Providers:   evidenceProvidersFor(missing, req.AvailableTools),
			Reason:      "Missing evidence affects whether the next action is trustworthy.",
			StopWhen:    "Source-backed value exists with acceptable confidence or user confirms it is not needed.",
			CanParallel: missing != "owner",
		})
	}
	if len(steps) == 0 {
		steps = append(steps, EvidenceAcquisitionStep{Type: "validation", Providers: req.AvailableTools, Reason: "Enough entity fields exist; validate freshness before action.", StopWhen: "Latest evidence is confirmed current.", CanParallel: true})
	}
	if len(steps) > 6 {
		return steps[:6]
	}
	return steps
}

func scoreContextualAction(req ContextualActionRequest, profile ActionEntityProfile) ActionFitScore {
	score := profile.Confidence
	var reasons []string
	var risks []string
	if len(req.Signals) > 0 {
		score += 0.14
		reasons = append(reasons, "live signals available")
	}
	if len(req.Evidence) >= 2 {
		score += 0.1
		reasons = append(reasons, "multiple evidence points")
	}
	if len(profile.Missing) > 2 {
		score -= 0.12
		risks = append(risks, "missing entity context")
	}
	if containsPlanningAny(strings.ToLower(req.Objective+" "+strings.Join(req.Constraints, " ")), "send", "outreach", "crm", "payment", "security") {
		risks = append(risks, "external action boundary")
	}
	if score > 0.92 {
		score = 0.92
	}
	if score < 0.18 {
		score = 0.18
	}
	return ActionFitScore{Score: score, Level: actionScoreLevel(score), Reasons: reasons, RiskFlags: risks, Confidence: score}
}

func buildContextualRecommendations(req ContextualActionRequest, profile ActionEntityProfile, score ActionFitScore) []ContextualActionRecommendation {
	var recs []ContextualActionRecommendation
	if len(profile.Missing) > 0 {
		recs = append(recs, ContextualActionRecommendation{
			Title:         "Fill missing context: " + strings.Join(profile.Missing[:minInt(len(profile.Missing), 2)], ", "),
			Why:           "Action quality depends on source-backed entity context.",
			Autonomy:      "suggest",
			Needs:         profile.Missing,
			DoneSignal:    "Missing fields are filled, explicitly skipped, or routed to a human.",
			NeedsApproval: false,
		})
	}
	recs = append(recs, ContextualActionRecommendation{
		Title:         "Draft next action for " + req.Entity.Name,
		Why:           "The objective needs a packaged action proposal, not another search loop.",
		Autonomy:      "draft",
		DoneSignal:    "A reviewable action packet exists with evidence and confidence.",
		NeedsApproval: true,
	})
	if len(req.Signals) > 0 && score.Level != "low" {
		recs = append(recs, ContextualActionRecommendation{
			Title:         "Use signal timing to prioritize follow-through",
			Why:           "Recent signals can make the action timely.",
			Autonomy:      "suggest",
			DoneSignal:    "Signal is attached to a next move or dismissed as irrelevant.",
			NeedsApproval: false,
		})
	}
	return recs
}

func buildSkillFunctionCandidate(req ContextualActionRequest, plan []EvidenceAcquisitionStep) SkillFunctionCandidate {
	var retrieval []string
	for _, step := range plan {
		retrieval = append(retrieval, step.Type)
	}
	return SkillFunctionCandidate{
		Name:           "skill_fn_" + stableBehaviorID(req.Entity.Kind+"_"+req.Objective),
		Inputs:         []string{"entity", "objective", "surface", "approved_tools", "governance_rules"},
		RetrievalPlan:  uniqueActionStrings(retrieval),
		Validation:     []string{"check provenance", "resolve missing critical fields", "score confidence", "surface risk flags"},
		OutputSchema:   []string{"entity_profile", "evidence", "score", "recommended_action", "approval_gate"},
		AllowedActions: safeAllowedActions(req.AvailableTools),
		CostPolicy:     "Prefer free/local evidence first; require approval for paid providers or broad external searches.",
	}
}

func evidenceProvidersFor(kind string, tools []string) []string {
	var providers []string
	for _, tool := range tools {
		lower := strings.ToLower(tool)
		if containsPlanningAny(lower, kind, "crm", "web", "search", "docs", "email") {
			providers = append(providers, tool)
		}
	}
	if len(providers) == 0 {
		providers = []string{"approved workspace sources", "user-provided context"}
	}
	return providers
}

func safeAllowedActions(tools []string) []string {
	var out []string
	for _, tool := range tools {
		lower := strings.ToLower(tool)
		if containsPlanningAny(lower, "search", "read", "docs", "crm", "web") {
			out = append(out, "read:"+tool)
		}
	}
	if len(out) == 0 {
		out = []string{"draft action packet", "ask for missing context"}
	}
	sort.Strings(out)
	return out
}

func summarizeContextualAction(req ContextualActionRequest, profile ActionEntityProfile, score ActionFitScore) string {
	return sentenceCase(req.Objective) + " for " + profile.Label + " has " + score.Level + " action readiness with " + intToMomentumString(len(profile.Missing)) + " missing context fields."
}

func contextualActionMemorySeeds(req ContextualActionRequest, score ActionFitScore) []QuestMemorySeed {
	return []QuestMemorySeed{
		{Key: "contextual_action_entity", Value: req.Entity.Name, Importance: 0.66},
		{Key: "contextual_action_objective", Value: req.Objective, Importance: 0.62},
		{Key: "contextual_action_readiness", Value: score.Level, Importance: 0.54},
	}
}

func contextualActionOpenQuestions(profile ActionEntityProfile, score ActionFitScore) []string {
	var qs []string
	for _, missing := range profile.Missing {
		qs = append(qs, "What is the entity's "+missing+"?")
		if len(qs) == 3 {
			break
		}
	}
	if len(score.RiskFlags) > 0 {
		qs = append(qs, "What approval gate is required before action?")
	}
	return qs
}

func contextualActionSurfaceHints(surface string) []string {
	switch normalizeQuestSurface(surface) {
	case "studio":
		return []string{"Frame output as account/customer context, confidence, next operator action, and approval boundary."}
	case "dev":
		return []string{"Frame output as issue/repo entity context, evidence, impact score, and next implementation move."}
	case "red":
		return []string{"Frame output as asset/vendor context, evidence provenance, risk score, and remediation path."}
	case "home":
		return []string{"Frame output as household entity context and one low-friction next action."}
	default:
		return []string{"Keep contextual action domain-neutral and provenance-forward."}
	}
}

func actionScoreLevel(score float64) string {
	switch {
	case score >= 0.72:
		return "high"
	case score >= 0.46:
		return "medium"
	default:
		return "low"
	}
}

func minInt(a, b int) int {
	if a < b {
		return a
	}
	return b
}

func uniqueActionStrings(values []string) []string {
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

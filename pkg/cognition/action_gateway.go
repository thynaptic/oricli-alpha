package cognition

import (
	"sort"
	"strings"
)

type ActionGatewayPlanRequest struct {
	Surface            string                    `json:"surface,omitempty"`
	Intent             string                    `json:"intent,omitempty"`
	Context            string                    `json:"context,omitempty"`
	ActionHints        []ActionGatewayActionHint `json:"action_hints,omitempty"`
	AvailableProviders []ActionProvider          `json:"available_providers,omitempty"`
	Constraints        []string                  `json:"constraints,omitempty"`
	ApprovalPolicy     ActionApprovalPolicy      `json:"approval_policy,omitempty"`
	RiskTolerance      string                    `json:"risk_tolerance,omitempty"`
	MemoryPolicy       ActionMemoryPolicy        `json:"memory_policy,omitempty"`
	Metadata           map[string]any            `json:"metadata,omitempty"`
}

type ActionGatewayActionHint struct {
	Title       string   `json:"title,omitempty"`
	Provider    string   `json:"provider,omitempty"`
	Tool        string   `json:"tool,omitempty"`
	Inputs      []string `json:"inputs,omitempty"`
	Effects     []string `json:"effects,omitempty"`
	Destructive bool     `json:"destructive,omitempty"`
	External    bool     `json:"external,omitempty"`
}

type ActionProvider struct {
	ID               string   `json:"id,omitempty"`
	Name             string   `json:"name,omitempty"`
	Kind             string   `json:"kind,omitempty"`
	Capabilities     []string `json:"capabilities,omitempty"`
	Scopes           []string `json:"scopes,omitempty"`
	Reliability      string   `json:"reliability,omitempty"`
	Cost             string   `json:"cost,omitempty"`
	RequiresApproval bool     `json:"requires_approval,omitempty"`
	ReadOnly         bool     `json:"read_only,omitempty"`
	Available        bool     `json:"available,omitempty"`
}

type ActionApprovalPolicy struct {
	RequireForExternalWrites bool     `json:"require_for_external_writes,omitempty"`
	RequireForCustomerTouch  bool     `json:"require_for_customer_touch,omitempty"`
	RequireForMoney          bool     `json:"require_for_money,omitempty"`
	RequireForDestructive    bool     `json:"require_for_destructive,omitempty"`
	AllowedAutonomousEffects []string `json:"allowed_autonomous_effects,omitempty"`
	ApprovalOwner            string   `json:"approval_owner,omitempty"`
}

type ActionMemoryPolicy struct {
	MinimizeContext       bool     `json:"minimize_context,omitempty"`
	AllowedMemoryKinds    []string `json:"allowed_memory_kinds,omitempty"`
	ProhibitedMemoryKinds []string `json:"prohibited_memory_kinds,omitempty"`
	RecordOutcome         bool     `json:"record_outcome,omitempty"`
}

type ActionGatewayPlan struct {
	ID            string                    `json:"id"`
	Surface       string                    `json:"surface"`
	Intent        string                    `json:"intent"`
	Summary       string                    `json:"summary"`
	Candidates    []ActionCandidate         `json:"candidates"`
	Recommended   ActionCandidate           `json:"recommended"`
	ApprovalGate  ActionGatewayApprovalGate `json:"approval_gate"`
	PolicyLabels  []ActionPolicyLabel       `json:"policy_labels,omitempty"`
	AuditPlan     ActionAuditPlan           `json:"audit_plan"`
	DryRun        ActionDryRun              `json:"dry_run"`
	MemoryPlan    ActionMemoryPlan          `json:"memory_plan"`
	Integration   ActionGatewayIntegration  `json:"integration"`
	Guardrails    []string                  `json:"guardrails"`
	OpenQuestions []string                  `json:"open_questions,omitempty"`
}

type ActionCandidate struct {
	ID               string   `json:"id"`
	Title            string   `json:"title"`
	ProviderID       string   `json:"provider_id,omitempty"`
	ProviderName     string   `json:"provider_name,omitempty"`
	ProviderKind     string   `json:"provider_kind,omitempty"`
	Tool             string   `json:"tool,omitempty"`
	Mode             string   `json:"mode"`
	RiskTier         string   `json:"risk_tier"`
	ApprovalRequired bool     `json:"approval_required"`
	Why              string   `json:"why"`
	Inputs           []string `json:"inputs,omitempty"`
	ExpectedEffects  []string `json:"expected_effects,omitempty"`
	PolicyLabels     []string `json:"policy_labels,omitempty"`
	Blockers         []string `json:"blockers,omitempty"`
	Score            float64  `json:"score"`
}

type ActionGatewayApprovalGate struct {
	Required  bool     `json:"required"`
	Owner     string   `json:"owner,omitempty"`
	Reason    string   `json:"reason,omitempty"`
	Before    string   `json:"before,omitempty"`
	Checklist []string `json:"checklist,omitempty"`
}

type ActionPolicyLabel struct {
	Label    string `json:"label"`
	Reason   string `json:"reason"`
	Severity string `json:"severity"`
}

type ActionAuditPlan struct {
	Before []string `json:"before"`
	During []string `json:"during"`
	After  []string `json:"after"`
}

type ActionDryRun struct {
	Mode  string   `json:"mode"`
	Steps []string `json:"steps"`
}

type ActionMemoryPlan struct {
	Record       []string `json:"record"`
	Minimize     []string `json:"minimize,omitempty"`
	DoNotSend    []string `json:"do_not_send,omitempty"`
	Provenance   string   `json:"provenance"`
	OutcomeEvent string   `json:"outcome_event"`
}

type ActionGatewayIntegration struct {
	WorkflowGrammar []string `json:"workflow_grammar"`
	WorkGraph       []string `json:"workgraph"`
	CALI            []string `json:"cali"`
	SCL             []string `json:"scl"`
	Chronos         []string `json:"chronos"`
	Red             []string `json:"red"`
}

// PlanSovereignAction routes an intended external action through the safest
// available provider path. It does not execute anything; it produces the
// approval, audit, memory, and dry-run envelope a client can use before action.
func PlanSovereignAction(req ActionGatewayPlanRequest) ActionGatewayPlan {
	req = normalizeActionGatewayRequest(req)
	candidates := buildActionCandidates(req)
	recommended := chooseActionCandidate(candidates)
	approval := buildActionApprovalGate(req, recommended)
	policy := buildActionPolicyLabels(req, recommended)

	return ActionGatewayPlan{
		ID:           "action_plan_" + stableBehaviorID(firstNonEmpty(req.Intent, "sovereign action")),
		Surface:      normalizeQuestSurface(req.Surface),
		Intent:       sentenceCase(req.Intent),
		Summary:      summarizeActionGateway(req, recommended, approval),
		Candidates:   candidates,
		Recommended:  recommended,
		ApprovalGate: approval,
		PolicyLabels: policy,
		AuditPlan:    buildActionAuditPlan(req, recommended),
		DryRun:       buildActionDryRun(req, recommended),
		MemoryPlan:   buildActionMemoryPlan(req, recommended),
		Integration: ActionGatewayIntegration{
			WorkflowGrammar: []string{"Use /workflow/grammar/compile when the action belongs inside a repeatable trigger/action workflow."},
			WorkGraph:       []string{"Attach approved actions, blockers, owners, and external effects to WorkGraph state."},
			CALI:            []string{"Run pre-action and post-action policy checks before execution adapters are allowed to mutate external systems."},
			SCL:             []string{"Record provider path, approval outcome, result, latency, and correction signal as action reputation evidence."},
			Chronos:         []string{"Monitor approved action routes for stale credentials, changing scopes, repeated failures, and unused automations."},
			Red:             []string{"Route high-risk external actions through Red review for prompt injection, overbroad credentials, and data leakage."},
		},
		Guardrails: []string{
			"This endpoint plans action routing only; it does not call external providers or mutate external systems.",
			"Require human approval before customer contact, payment, destructive mutation, publishing, credential changes, or broad data export.",
			"Send the minimum context required to the selected provider and keep secrets out of action payloads.",
			"Record provenance and outcome after execution so future routing improves from evidence, not assumption.",
		},
		OpenQuestions: actionGatewayOpenQuestions(req, recommended),
	}
}

func normalizeActionGatewayRequest(req ActionGatewayPlanRequest) ActionGatewayPlanRequest {
	req.Surface = normalizeQuestSurface(req.Surface)
	req.Intent = cleanPlanningText(firstNonEmpty(req.Intent, req.Context, "Plan external action"))
	req.Context = cleanPlanningText(req.Context)
	req.Constraints = uniqueWorkflowStrings(req.Constraints)
	req.RiskTolerance = strings.ToLower(strings.TrimSpace(firstNonEmpty(req.RiskTolerance, "medium")))
	if req.ApprovalPolicy.ApprovalOwner == "" {
		req.ApprovalPolicy.ApprovalOwner = "operator"
	}
	req.ApprovalPolicy.AllowedAutonomousEffects = uniqueWorkflowStrings(req.ApprovalPolicy.AllowedAutonomousEffects)
	req.MemoryPolicy.AllowedMemoryKinds = uniqueWorkflowStrings(req.MemoryPolicy.AllowedMemoryKinds)
	req.MemoryPolicy.ProhibitedMemoryKinds = uniqueWorkflowStrings(req.MemoryPolicy.ProhibitedMemoryKinds)
	if !req.MemoryPolicy.RecordOutcome {
		req.MemoryPolicy.RecordOutcome = true
	}
	for i := range req.ActionHints {
		req.ActionHints[i].Title = cleanPlanningText(req.ActionHints[i].Title)
		req.ActionHints[i].Provider = cleanPlanningText(req.ActionHints[i].Provider)
		req.ActionHints[i].Tool = cleanPlanningText(req.ActionHints[i].Tool)
		req.ActionHints[i].Inputs = uniqueWorkflowStrings(req.ActionHints[i].Inputs)
		req.ActionHints[i].Effects = uniqueWorkflowStrings(req.ActionHints[i].Effects)
	}
	for i := range req.AvailableProviders {
		req.AvailableProviders[i].ID = cleanPlanningText(req.AvailableProviders[i].ID)
		req.AvailableProviders[i].Name = cleanPlanningText(req.AvailableProviders[i].Name)
		req.AvailableProviders[i].Kind = strings.ToLower(strings.TrimSpace(req.AvailableProviders[i].Kind))
		req.AvailableProviders[i].Capabilities = uniqueWorkflowStrings(req.AvailableProviders[i].Capabilities)
		req.AvailableProviders[i].Scopes = uniqueWorkflowStrings(req.AvailableProviders[i].Scopes)
		req.AvailableProviders[i].Reliability = strings.ToLower(strings.TrimSpace(req.AvailableProviders[i].Reliability))
		req.AvailableProviders[i].Cost = strings.ToLower(strings.TrimSpace(req.AvailableProviders[i].Cost))
		if req.AvailableProviders[i].ID == "" {
			req.AvailableProviders[i].ID = "provider_" + stableBehaviorID(firstNonEmpty(req.AvailableProviders[i].Name, req.AvailableProviders[i].Kind, "provider"))
		}
	}
	if len(req.ActionHints) == 0 {
		req.ActionHints = inferActionHints(req)
	}
	if len(req.AvailableProviders) == 0 {
		req.AvailableProviders = []ActionProvider{{ID: "provider_manual_review", Name: "Manual review", Kind: "human", Reliability: "high", Available: true, RequiresApproval: true}}
	}
	return req
}

func inferActionHints(req ActionGatewayPlanRequest) []ActionGatewayActionHint {
	atoms := splitPlanningAtoms(req.Intent + ". " + req.Context)
	var hints []ActionGatewayActionHint
	for _, atom := range atoms {
		hints = append(hints, ActionGatewayActionHint{
			Title:    actionizePlanningAtom(atom),
			External: inferActionExternal(atom),
			Effects:  inferActionEffects(atom),
		})
	}
	if len(hints) == 0 {
		hints = []ActionGatewayActionHint{{Title: req.Intent, External: true, Effects: inferActionEffects(req.Intent)}}
	}
	if len(hints) > 5 {
		hints = hints[:5]
	}
	return hints
}

func buildActionCandidates(req ActionGatewayPlanRequest) []ActionCandidate {
	var candidates []ActionCandidate
	for _, hint := range req.ActionHints {
		providers := matchingActionProviders(req.AvailableProviders, hint)
		for _, provider := range providers {
			candidate := buildActionCandidate(req, hint, provider)
			candidates = append(candidates, candidate)
		}
	}
	sort.SliceStable(candidates, func(i, j int) bool { return candidates[i].Score > candidates[j].Score })
	if len(candidates) > 6 {
		candidates = candidates[:6]
	}
	if len(candidates) == 0 {
		candidates = append(candidates, ActionCandidate{
			ID:               "action_manual_clarify",
			Title:            "Clarify the external action path",
			ProviderID:       "provider_manual_review",
			ProviderName:     "Manual review",
			ProviderKind:     "human",
			Mode:             "manual",
			RiskTier:         "medium",
			ApprovalRequired: true,
			Why:              "No provider matched the requested action.",
			Blockers:         []string{"missing provider capability mapping"},
			Score:            0.25,
		})
	}
	return candidates
}

func buildActionCandidate(req ActionGatewayPlanRequest, hint ActionGatewayActionHint, provider ActionProvider) ActionCandidate {
	title := sentenceCase(firstNonEmpty(hint.Title, req.Intent))
	effects := uniqueWorkflowStrings(append(hint.Effects, inferActionEffects(title)...))
	riskTier := actionRiskTier(req, hint, provider, effects)
	approvalRequired := actionApprovalRequired(req, hint, provider, effects, riskTier)
	labels := actionPolicyLabelStrings(req, hint, provider, effects, riskTier)
	blockers := actionCandidateBlockers(req, hint, provider)
	score := actionCandidateScore(req, provider, riskTier, approvalRequired, blockers)
	mode := "provider"
	if provider.Kind == "human" {
		mode = "manual"
	} else if provider.ReadOnly {
		mode = "read_only"
	} else if approvalRequired {
		mode = "approval_then_execute"
	}
	return ActionCandidate{
		ID:               "action_" + stableBehaviorID(title+" "+provider.ID),
		Title:            title,
		ProviderID:       provider.ID,
		ProviderName:     firstNonEmpty(provider.Name, provider.ID),
		ProviderKind:     provider.Kind,
		Tool:             firstNonEmpty(hint.Tool, inferActionTool(title, provider)),
		Mode:             mode,
		RiskTier:         riskTier,
		ApprovalRequired: approvalRequired,
		Why:              actionCandidateWhy(provider, riskTier, approvalRequired),
		Inputs:           hint.Inputs,
		ExpectedEffects:  effects,
		PolicyLabels:     labels,
		Blockers:         blockers,
		Score:            score,
	}
}

func matchingActionProviders(providers []ActionProvider, hint ActionGatewayActionHint) []ActionProvider {
	var matches []ActionProvider
	for _, provider := range providers {
		if !provider.Available && provider.Name != "" {
			continue
		}
		haystack := strings.ToLower(provider.Name + " " + provider.Kind + " " + strings.Join(provider.Capabilities, " ") + " " + strings.Join(provider.Scopes, " "))
		needle := strings.ToLower(hint.Title + " " + hint.Provider + " " + hint.Tool + " " + strings.Join(hint.Effects, " "))
		if hint.Provider != "" && !containsPlanningAny(haystack, hint.Provider) {
			continue
		}
		if hint.Tool != "" && !containsPlanningAny(haystack, hint.Tool) {
			continue
		}
		if hint.Provider == "" && hint.Tool == "" && !actionProviderMatchesIntent(haystack, needle) {
			continue
		}
		matches = append(matches, provider)
	}
	if len(matches) == 0 {
		for _, provider := range providers {
			if strings.EqualFold(provider.Kind, "human") || strings.EqualFold(provider.Name, "manual review") {
				matches = append(matches, provider)
				break
			}
		}
	}
	return matches
}

func chooseActionCandidate(candidates []ActionCandidate) ActionCandidate {
	if len(candidates) == 0 {
		return ActionCandidate{}
	}
	return candidates[0]
}

func buildActionApprovalGate(req ActionGatewayPlanRequest, candidate ActionCandidate) ActionGatewayApprovalGate {
	if !candidate.ApprovalRequired {
		return ActionGatewayApprovalGate{Required: false}
	}
	return ActionGatewayApprovalGate{
		Required: true,
		Owner:    req.ApprovalPolicy.ApprovalOwner,
		Reason:   "Approval required for " + candidate.RiskTier + " risk action via " + firstNonEmpty(candidate.ProviderName, "selected provider") + ".",
		Before:   candidate.ID,
		Checklist: []string{
			"Confirm the intended external system and account.",
			"Review the exact payload before any write or customer-facing action.",
			"Confirm rollback or recovery path.",
			"Record approval, denial, or edits as outcome evidence.",
		},
	}
}

func buildActionPolicyLabels(req ActionGatewayPlanRequest, candidate ActionCandidate) []ActionPolicyLabel {
	var labels []ActionPolicyLabel
	for _, label := range candidate.PolicyLabels {
		severity := "medium"
		if containsPlanningAny(label, "blocked", "destructive", "payment", "credential", "data_export") {
			severity = "high"
		}
		labels = append(labels, ActionPolicyLabel{Label: label, Reason: actionPolicyReason(label), Severity: severity})
	}
	if len(labels) == 0 {
		labels = append(labels, ActionPolicyLabel{Label: "reviewable", Reason: "Action can be planned with explicit audit trail.", Severity: "low"})
	}
	return labels
}

func buildActionAuditPlan(req ActionGatewayPlanRequest, candidate ActionCandidate) ActionAuditPlan {
	return ActionAuditPlan{
		Before: []string{
			"Capture user intent, selected provider, scopes, risk tier, and approval status.",
			"Snapshot minimum required inputs and omit prohibited memory kinds.",
		},
		During: []string{
			"Log provider request id, execution mode, latency, and policy labels.",
			"Stop on provider errors, scope mismatch, prompt-injection signal, or unexpected write target.",
		},
		After: []string{
			"Record outcome, changed external object ids if supplied, and user correction signal.",
			"Feed success/failure evidence into SCL route reputation.",
		},
	}
}

func buildActionDryRun(req ActionGatewayPlanRequest, candidate ActionCandidate) ActionDryRun {
	steps := []string{
		"Resolve provider route without sending live payload.",
		"Validate required inputs and scopes against the selected provider.",
		"Produce the exact proposed external action payload for review.",
	}
	if candidate.ApprovalRequired {
		steps = append(steps, "Collect approval before execution adapter is allowed to run.")
	}
	steps = append(steps, "Simulate success, provider failure, and policy-block outcomes.")
	return ActionDryRun{Mode: "no_external_mutation", Steps: steps}
}

func buildActionMemoryPlan(req ActionGatewayPlanRequest, candidate ActionCandidate) ActionMemoryPlan {
	record := []string{"intent", "selected_provider", "risk_tier", "approval_status", "policy_labels"}
	if req.MemoryPolicy.RecordOutcome {
		record = append(record, "execution_outcome", "provider_result", "user_correction")
	}
	return ActionMemoryPlan{
		Record:       record,
		Minimize:     actionMemoryMinimize(req),
		DoNotSend:    uniqueWorkflowStrings(append([]string{"secrets", "raw credentials", "unneeded private memory"}, req.MemoryPolicy.ProhibitedMemoryKinds...)),
		Provenance:   "action_gateway_plan",
		OutcomeEvent: "external_action_attempt",
	}
}

func summarizeActionGateway(req ActionGatewayPlanRequest, candidate ActionCandidate, approval ActionGatewayApprovalGate) string {
	approvalText := "without required approval"
	if approval.Required {
		approvalText = "with approval required"
	}
	return sentenceCase(req.Intent) + " routed to " + firstNonEmpty(candidate.ProviderName, "manual review") + " as " + candidate.RiskTier + " risk " + approvalText + "."
}

func actionGatewayOpenQuestions(req ActionGatewayPlanRequest, candidate ActionCandidate) []string {
	var qs []string
	if len(req.AvailableProviders) == 0 || candidate.ProviderKind == "human" {
		qs = append(qs, "Which external provider or native tool should be allowed for this action?")
	}
	if len(candidate.Inputs) == 0 {
		qs = append(qs, "What exact inputs are required before execution?")
	}
	if candidate.RiskTier == "high" || candidate.RiskTier == "critical" {
		qs = append(qs, "Who is allowed to approve this high-risk action?")
	}
	if len(req.Constraints) == 0 {
		qs = append(qs, "What constraints should block or pause this action?")
	}
	return uniqueWorkflowStrings(qs)
}

func actionProviderMatchesIntent(providerText, intentText string) bool {
	for _, token := range strings.Fields(intentText) {
		token = strings.Trim(token, ".,;:!?")
		if len(token) < 4 {
			continue
		}
		if strings.Contains(providerText, token) {
			return true
		}
	}
	return containsPlanningAny(intentText, "email", "crm", "slack", "calendar", "ticket", "issue", "invoice", "record", "webhook", "mcp", "zapier", "make")
}

func actionRiskTier(req ActionGatewayPlanRequest, hint ActionGatewayActionHint, provider ActionProvider, effects []string) string {
	text := strings.ToLower(req.Intent + " " + hint.Title + " " + strings.Join(effects, " ") + " " + strings.Join(req.Constraints, " "))
	switch {
	case hint.Destructive || containsPlanningAny(text, "delete", "remove", "overwrite", "credential", "secret", "admin"):
		return "critical"
	case containsPlanningAny(text, "payment", "charge", "refund", "payroll", "invoice", "customer email", "send", "publish", "export data"):
		return "high"
	case hint.External || provider.Kind == "zapier_mcp" || provider.Kind == "make_mcp" || provider.Kind == "mcp" || containsPlanningAny(text, "create", "update", "post", "book", "schedule"):
		return "medium"
	default:
		return "low"
	}
}

func actionApprovalRequired(req ActionGatewayPlanRequest, hint ActionGatewayActionHint, provider ActionProvider, effects []string, riskTier string) bool {
	text := strings.ToLower(hint.Title + " " + strings.Join(effects, " "))
	if provider.RequiresApproval || hint.Destructive || riskTier == "critical" {
		return true
	}
	if req.ApprovalPolicy.RequireForDestructive && containsPlanningAny(text, "delete", "archive", "overwrite") {
		return true
	}
	if req.ApprovalPolicy.RequireForMoney && containsPlanningAny(text, "payment", "charge", "refund", "invoice", "payroll") {
		return true
	}
	if req.ApprovalPolicy.RequireForCustomerTouch && containsPlanningAny(text, "customer", "email", "send", "reply", "publish") {
		return true
	}
	if req.ApprovalPolicy.RequireForExternalWrites && (hint.External || containsPlanningAny(text, "create", "update", "send", "post", "book", "schedule")) {
		return true
	}
	return riskTier == "high" && req.RiskTolerance != "high"
}

func actionPolicyLabelStrings(req ActionGatewayPlanRequest, hint ActionGatewayActionHint, provider ActionProvider, effects []string, riskTier string) []string {
	text := strings.ToLower(req.Intent + " " + hint.Title + " " + strings.Join(effects, " "))
	var labels []string
	if provider.ReadOnly {
		labels = append(labels, "read_only")
	}
	if hint.External || provider.Kind != "human" {
		labels = append(labels, "external_action")
	}
	if containsPlanningAny(text, "customer", "email", "send", "reply", "publish") {
		labels = append(labels, "customer_touch")
	}
	if containsPlanningAny(text, "payment", "charge", "refund", "invoice", "payroll") {
		labels = append(labels, "money_or_finance")
	}
	if containsPlanningAny(text, "delete", "remove", "overwrite", "archive") {
		labels = append(labels, "destructive_mutation")
	}
	if containsPlanningAny(text, "export", "pii", "private", "customer data") {
		labels = append(labels, "data_export")
	}
	if riskTier == "critical" {
		labels = append(labels, "blocked_until_review")
	}
	return uniqueWorkflowStrings(labels)
}

func actionCandidateBlockers(req ActionGatewayPlanRequest, hint ActionGatewayActionHint, provider ActionProvider) []string {
	var blockers []string
	if provider.ID == "" || provider.Name == "" {
		blockers = append(blockers, "provider identity incomplete")
	}
	if len(hint.Inputs) == 0 && containsPlanningAny(hint.Title, "create", "send", "update", "book", "schedule", "charge", "refund") {
		blockers = append(blockers, "required inputs not named")
	}
	if len(provider.Scopes) == 0 && provider.Kind != "human" {
		blockers = append(blockers, "provider scopes not supplied")
	}
	if !provider.Available && provider.Name != "" {
		blockers = append(blockers, "provider not available")
	}
	return uniqueWorkflowStrings(blockers)
}

func actionCandidateScore(req ActionGatewayPlanRequest, provider ActionProvider, riskTier string, approval bool, blockers []string) float64 {
	score := 0.45
	switch provider.Reliability {
	case "high":
		score += 0.2
	case "medium":
		score += 0.1
	case "low":
		score -= 0.1
	}
	switch provider.Kind {
	case "native":
		score += 0.16
	case "mcp", "zapier_mcp", "make_mcp":
		score += 0.12
	case "human":
		score += 0.02
	}
	if provider.ReadOnly {
		score += 0.08
	}
	if approval {
		score -= 0.04
	}
	switch riskTier {
	case "low":
		score += 0.15
	case "medium":
		score += 0.05
	case "high":
		score -= 0.08
	case "critical":
		score -= 0.18
	}
	score -= float64(len(blockers)) * 0.08
	if score < 0.05 {
		score = 0.05
	}
	if score > 0.95 {
		score = 0.95
	}
	return score
}

func actionCandidateWhy(provider ActionProvider, riskTier string, approval bool) string {
	reason := "Provider matches the requested action with " + riskTier + " risk."
	if provider.Kind == "native" {
		reason += " Native route is preferred when available and scoped."
	} else if containsPlanningAny(provider.Kind, "mcp") {
		reason += " MCP/provider rail can supply external action reach while ORI keeps governance."
	}
	if approval {
		reason += " Approval is required before execution."
	}
	return reason
}

func inferActionExternal(text string) bool {
	return containsPlanningAny(text, "email", "crm", "calendar", "slack", "github", "stripe", "zapier", "make", "webhook", "customer", "publish", "send", "post")
}

func inferActionEffects(text string) []string {
	lower := strings.ToLower(text)
	var effects []string
	switch {
	case containsPlanningAny(lower, "send", "email", "reply"):
		effects = append(effects, "customer_or_external_message")
	case containsPlanningAny(lower, "create", "add", "open"):
		effects = append(effects, "create_record")
	case containsPlanningAny(lower, "update", "edit", "change"):
		effects = append(effects, "update_record")
	case containsPlanningAny(lower, "delete", "remove", "archive"):
		effects = append(effects, "destructive_mutation")
	case containsPlanningAny(lower, "charge", "refund", "payment", "invoice"):
		effects = append(effects, "money_or_finance")
	}
	return effects
}

func inferActionTool(title string, provider ActionProvider) string {
	lower := strings.ToLower(title + " " + provider.Name + " " + strings.Join(provider.Capabilities, " "))
	switch {
	case containsPlanningAny(lower, "email", "reply", "send"):
		return "email"
	case containsPlanningAny(lower, "crm", "customer", "lead"):
		return "crm"
	case containsPlanningAny(lower, "calendar", "schedule", "book"):
		return "calendar"
	case containsPlanningAny(lower, "ticket", "issue", "github", "linear"):
		return "issue_tracker"
	case containsPlanningAny(lower, "payment", "stripe", "invoice"):
		return "finance"
	default:
		return provider.Kind
	}
}

func actionPolicyReason(label string) string {
	switch label {
	case "read_only":
		return "Provider is marked read-only."
	case "external_action":
		return "Action may leave ORI's internal boundary."
	case "customer_touch":
		return "Action may contact or affect a customer-facing surface."
	case "money_or_finance":
		return "Action may affect money, billing, payroll, invoices, or finance records."
	case "destructive_mutation":
		return "Action may delete, archive, overwrite, or remove records."
	case "data_export":
		return "Action may expose private or customer data outside ORI."
	case "blocked_until_review":
		return "Critical action must not execute before explicit review."
	default:
		return "Policy label generated from action/provider risk signals."
	}
}

func actionMemoryMinimize(req ActionGatewayPlanRequest) []string {
	minimize := []string{"raw conversation history", "unrelated memory", "full customer records"}
	if req.MemoryPolicy.MinimizeContext {
		minimize = append(minimize, "nonessential context", "long-term memory not required for action")
	}
	return uniqueWorkflowStrings(minimize)
}

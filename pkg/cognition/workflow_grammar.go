package cognition

import (
	"sort"
	"strings"
)

type WorkflowGrammarRequest struct {
	Surface        string                       `json:"surface,omitempty"`
	Title          string                       `json:"title,omitempty"`
	Intent         string                       `json:"intent,omitempty"`
	Specification  string                       `json:"specification,omitempty"`
	Trigger        string                       `json:"trigger,omitempty"`
	Conditions     []string                     `json:"conditions,omitempty"`
	Actions        []WorkflowActionHint         `json:"actions,omitempty"`
	AvailableTools []WorkflowAvailableTool      `json:"available_tools,omitempty"`
	Approvals      []WorkflowApprovalPreference `json:"approvals,omitempty"`
	Constraints    []string                     `json:"constraints,omitempty"`
	Exceptions     []string                     `json:"exceptions,omitempty"`
	Outputs        []string                     `json:"outputs,omitempty"`
	Preferences    WorkflowGrammarPreferences   `json:"preferences,omitempty"`
	Metadata       map[string]any               `json:"metadata,omitempty"`
}

type WorkflowActionHint struct {
	Title       string   `json:"title,omitempty"`
	Tool        string   `json:"tool,omitempty"`
	Owner       string   `json:"owner,omitempty"`
	When        string   `json:"when,omitempty"`
	Unless      string   `json:"unless,omitempty"`
	Needs       []string `json:"needs,omitempty"`
	DoneSignal  string   `json:"done_signal,omitempty"`
	Destructive bool     `json:"destructive,omitempty"`
}

type WorkflowAvailableTool struct {
	Name       string   `json:"name,omitempty"`
	Kind       string   `json:"kind,omitempty"`
	Actions    []string `json:"actions,omitempty"`
	ReadOnly   bool     `json:"read_only,omitempty"`
	RequiresOK bool     `json:"requires_approval,omitempty"`
}

type WorkflowApprovalPreference struct {
	When   string `json:"when,omitempty"`
	Owner  string `json:"owner,omitempty"`
	Reason string `json:"reason,omitempty"`
}

type WorkflowGrammarPreferences struct {
	MaxNodes              int  `json:"max_nodes,omitempty"`
	RequireHumanApprovals bool `json:"require_human_approvals,omitempty"`
	DryRunFirst           bool `json:"dry_run_first,omitempty"`
	PreferReadOnly        bool `json:"prefer_read_only,omitempty"`
}

type CompiledWorkflowGrammar struct {
	ID                 string                     `json:"id"`
	Surface            string                     `json:"surface"`
	Title              string                     `json:"title"`
	Intent             string                     `json:"intent"`
	Summary            string                     `json:"summary"`
	Trigger            WorkflowTrigger            `json:"trigger"`
	Variables          []WorkflowVariable         `json:"variables,omitempty"`
	Nodes              []WorkflowNode             `json:"nodes"`
	Edges              []WorkflowEdge             `json:"edges,omitempty"`
	ApprovalGates      []WorkflowApprovalGate     `json:"approval_gates,omitempty"`
	FailureModes       []WorkflowFailureMode      `json:"failure_modes,omitempty"`
	DryRunPlan         []string                   `json:"dry_run_plan,omitempty"`
	Readiness          WorkflowExecutionReadiness `json:"readiness"`
	Integration        WorkflowGrammarIntegration `json:"integration"`
	Guardrails         []string                   `json:"guardrails"`
	OpenQuestions      []string                   `json:"open_questions,omitempty"`
	CompiledExpression string                     `json:"compiled_expression"`
}

type WorkflowTrigger struct {
	Kind      string `json:"kind"`
	Statement string `json:"statement"`
	Source    string `json:"source,omitempty"`
}

type WorkflowVariable struct {
	Name     string `json:"name"`
	Source   string `json:"source"`
	Required bool   `json:"required"`
}

type WorkflowNode struct {
	ID          string   `json:"id"`
	Kind        string   `json:"kind"`
	Title       string   `json:"title"`
	Tool        string   `json:"tool,omitempty"`
	Owner       string   `json:"owner,omitempty"`
	Condition   string   `json:"condition,omitempty"`
	Unless      string   `json:"unless,omitempty"`
	Needs       []string `json:"needs,omitempty"`
	DoneSignal  string   `json:"done_signal"`
	CanAutomate bool     `json:"can_automate"`
	Risks       []string `json:"risks,omitempty"`
}

type WorkflowEdge struct {
	From  string `json:"from"`
	To    string `json:"to"`
	Kind  string `json:"kind"`
	Label string `json:"label,omitempty"`
}

type WorkflowApprovalGate struct {
	ID     string `json:"id"`
	After  string `json:"after,omitempty"`
	Before string `json:"before,omitempty"`
	Owner  string `json:"owner"`
	Reason string `json:"reason"`
}

type WorkflowFailureMode struct {
	NodeID     string `json:"node_id,omitempty"`
	Risk       string `json:"risk"`
	Recovery   string `json:"recovery"`
	NeedsHuman bool   `json:"needs_human"`
}

type WorkflowExecutionReadiness struct {
	Level   string   `json:"level"`
	Score   float64  `json:"score"`
	Reasons []string `json:"reasons,omitempty"`
	Missing []string `json:"missing,omitempty"`
}

type WorkflowGrammarIntegration struct {
	Procedure []string `json:"procedure"`
	WorkGraph []string `json:"workgraph"`
	Temporal  []string `json:"temporal"`
	Forge     []string `json:"forge"`
	Studio    []string `json:"studio"`
	Memory    []string `json:"memory"`
}

// CompileWorkflowGrammar turns messy natural-language workflow intent into a
// deterministic trigger/condition/action graph. It drafts workflow shape only;
// clients still own execution, persistence, permissions, and external writes.
func CompileWorkflowGrammar(req WorkflowGrammarRequest) CompiledWorkflowGrammar {
	req = normalizeWorkflowGrammarRequest(req)
	title := sentenceCase(firstNonEmpty(req.Title, inferWorkflowTitle(req), "Draft workflow"))
	trigger := inferWorkflowTrigger(req)
	nodes := buildWorkflowNodes(req)
	edges := buildWorkflowEdges(trigger, nodes)
	approvals := buildWorkflowApprovals(req, nodes)
	failures := buildWorkflowFailures(req, nodes)
	variables := inferWorkflowVariables(req, nodes)
	readiness := scoreWorkflowReadiness(req, nodes, approvals, variables)

	return CompiledWorkflowGrammar{
		ID:            "workflow_" + stableBehaviorID(title),
		Surface:       normalizeQuestSurface(req.Surface),
		Title:         title,
		Intent:        sentenceCase(firstNonEmpty(req.Intent, title)),
		Summary:       summarizeWorkflow(req, nodes, approvals, readiness),
		Trigger:       trigger,
		Variables:     variables,
		Nodes:         nodes,
		Edges:         edges,
		ApprovalGates: approvals,
		FailureModes:  failures,
		DryRunPlan:    buildWorkflowDryRunPlan(req, nodes),
		Readiness:     readiness,
		Integration: WorkflowGrammarIntegration{
			Procedure: []string{"Route stable successful runs into /procedure/compile to crystalize SOPs and skill candidates."},
			WorkGraph: []string{"Represent long-running jobs, approvals, blockers, and owner state in WorkGraph before execution."},
			Temporal:  []string{"Use /temporal/coordinate when trigger windows, SLA timers, or human review need scheduling."},
			Forge:     []string{"Only generate executable adapters after tools, inputs, permissions, and rollback behavior are explicit."},
			Studio:    []string{"Studio can present this as a draft Job, with trigger/action cards and approval gates visible before activation."},
			Memory:    []string{"Remember confirmed workflow language, recurring exceptions, and trusted approval owners after user confirmation."},
		},
		Guardrails: []string{
			"This endpoint drafts workflow grammar only; it does not register, schedule, execute, or persist automations.",
			"Require explicit human approval before external writes, customer contact, payment, deletion, publishing, or irreversible actions.",
			"Keep secrets, credentials, regulated decisions, and destructive operations outside automatic nodes.",
			"Treat inferred conditions and variables as proposals until a product client or user confirms them.",
		},
		OpenQuestions:      workflowOpenQuestions(req, trigger, nodes, variables),
		CompiledExpression: buildWorkflowExpression(trigger, nodes),
	}
}

func normalizeWorkflowGrammarRequest(req WorkflowGrammarRequest) WorkflowGrammarRequest {
	req.Surface = normalizeQuestSurface(req.Surface)
	req.Title = cleanPlanningText(req.Title)
	req.Intent = cleanPlanningText(req.Intent)
	req.Specification = cleanPlanningText(req.Specification)
	req.Trigger = cleanPlanningText(req.Trigger)
	req.Conditions = uniqueWorkflowStrings(req.Conditions)
	req.Constraints = uniqueWorkflowStrings(req.Constraints)
	req.Exceptions = uniqueWorkflowStrings(req.Exceptions)
	req.Outputs = uniqueWorkflowStrings(req.Outputs)
	if req.Preferences.MaxNodes <= 0 {
		req.Preferences.MaxNodes = 8
	}
	if req.Preferences.MaxNodes > 12 {
		req.Preferences.MaxNodes = 12
	}
	for i := range req.Actions {
		req.Actions[i].Title = cleanPlanningText(req.Actions[i].Title)
		req.Actions[i].Tool = cleanPlanningText(req.Actions[i].Tool)
		req.Actions[i].Owner = cleanPlanningText(req.Actions[i].Owner)
		req.Actions[i].When = cleanPlanningText(req.Actions[i].When)
		req.Actions[i].Unless = cleanPlanningText(req.Actions[i].Unless)
		req.Actions[i].DoneSignal = cleanPlanningText(req.Actions[i].DoneSignal)
		req.Actions[i].Needs = uniqueWorkflowStrings(req.Actions[i].Needs)
	}
	for i := range req.AvailableTools {
		req.AvailableTools[i].Name = cleanPlanningText(req.AvailableTools[i].Name)
		req.AvailableTools[i].Kind = strings.ToLower(strings.TrimSpace(req.AvailableTools[i].Kind))
		req.AvailableTools[i].Actions = uniqueWorkflowStrings(req.AvailableTools[i].Actions)
	}
	for i := range req.Approvals {
		req.Approvals[i].When = cleanPlanningText(req.Approvals[i].When)
		req.Approvals[i].Owner = cleanPlanningText(req.Approvals[i].Owner)
		req.Approvals[i].Reason = cleanPlanningText(req.Approvals[i].Reason)
	}
	return req
}

func inferWorkflowTitle(req WorkflowGrammarRequest) string {
	base := firstNonEmpty(req.Intent, req.Specification, req.Trigger)
	for _, prefix := range []string{"when ", "if ", "whenever "} {
		if strings.HasPrefix(strings.ToLower(base), prefix) {
			base = strings.TrimSpace(base[len(prefix):])
			break
		}
	}
	parts := strings.Fields(base)
	if len(parts) > 8 {
		parts = parts[:8]
	}
	return strings.Join(parts, " ")
}

func inferWorkflowTrigger(req WorkflowGrammarRequest) WorkflowTrigger {
	statement := firstNonEmpty(req.Trigger, extractWorkflowClause(req.Specification, "when"), extractWorkflowClause(req.Specification, "if"), "User or client provides the workflow input")
	statement = trimWorkflowTriggerPrefix(statement)
	kind := "manual"
	lower := strings.ToLower(statement)
	switch {
	case containsPlanningAny(lower, "email", "message", "inbox", "reply", "dm"):
		kind = "event"
	case containsPlanningAny(lower, "every ", "daily", "weekly", "monthly", "morning", "evening"):
		kind = "schedule"
	case containsPlanningAny(lower, "webhook", "api", "form submitted", "new record"):
		kind = "system_event"
	}
	return WorkflowTrigger{Kind: kind, Statement: sentenceCase(statement), Source: inferWorkflowTriggerSource(statement)}
}

func trimWorkflowTriggerPrefix(statement string) string {
	statement = cleanPlanningText(statement)
	lower := strings.ToLower(statement)
	for _, prefix := range []string{"when ", "whenever ", "if "} {
		if strings.HasPrefix(lower, prefix) {
			return cleanPlanningText(statement[len(prefix):])
		}
	}
	return statement
}

func buildWorkflowNodes(req WorkflowGrammarRequest) []WorkflowNode {
	var hints []WorkflowActionHint
	hints = append(hints, req.Actions...)
	if len(hints) == 0 {
		hints = inferWorkflowActions(req)
	}
	if len(hints) == 0 {
		hints = []WorkflowActionHint{{Title: "Clarify the first action and expected output"}}
	}
	if len(hints) > req.Preferences.MaxNodes {
		hints = hints[:req.Preferences.MaxNodes]
	}
	nodes := make([]WorkflowNode, 0, len(hints))
	for i, hint := range hints {
		title := sentenceCase(firstNonEmpty(hint.Title, "Handle workflow step"))
		tool := firstNonEmpty(hint.Tool, inferWorkflowTool(title, req.AvailableTools))
		node := WorkflowNode{
			ID:          "node_" + stableBehaviorID(title),
			Kind:        inferWorkflowNodeKind(title, tool),
			Title:       title,
			Tool:        tool,
			Owner:       firstNonEmpty(hint.Owner, "operator"),
			Condition:   firstNonEmpty(hint.When, conditionForIndex(req.Conditions, i)),
			Unless:      firstNonEmpty(hint.Unless, exceptionForAction(req.Exceptions, title)),
			Needs:       hint.Needs,
			DoneSignal:  firstNonEmpty(hint.DoneSignal, inferWorkflowDoneSignal(title, req.Outputs)),
			CanAutomate: workflowCanAutomate(req, hint, title, tool),
			Risks:       workflowNodeRisks(req, hint, title, tool),
		}
		nodes = append(nodes, node)
	}
	return nodes
}

func inferWorkflowActions(req WorkflowGrammarRequest) []WorkflowActionHint {
	text := firstNonEmpty(req.Specification, req.Intent, req.Title)
	clauses := splitWorkflowActionClauses(text)
	out := make([]WorkflowActionHint, 0, len(clauses))
	for _, clause := range clauses {
		lower := strings.ToLower(clause)
		if strings.HasPrefix(lower, "when ") || strings.HasPrefix(lower, "if ") || strings.HasPrefix(lower, "unless ") {
			continue
		}
		title, unless := splitWorkflowUnless(clause)
		out = append(out, WorkflowActionHint{Title: title, Unless: unless})
	}
	if len(out) == 0 {
		for _, atom := range splitPlanningAtoms(text) {
			if !containsPlanningAny(atom, "when ", "if ", "unless ") {
				out = append(out, WorkflowActionHint{Title: atom})
			}
		}
	}
	return out
}

func splitWorkflowActionClauses(text string) []string {
	text = strings.ReplaceAll(text, "\n", ". ")
	replacements := []struct{ old, new string }{
		{" and then ", ". "},
		{" then ", ". "},
		{" after that ", ". "},
		{" afterwards ", ". "},
		{" finally ", ". "},
	}
	lower := strings.ToLower(text)
	for _, r := range replacements {
		lower = strings.ReplaceAll(lower, r.old, r.new)
	}
	return splitPlanningAtoms(lower)
}

func splitWorkflowUnless(clause string) (string, string) {
	lower := strings.ToLower(clause)
	idx := strings.Index(lower, " unless ")
	if idx < 0 {
		return cleanPlanningText(clause), ""
	}
	return cleanPlanningText(clause[:idx]), cleanPlanningText(clause[idx+len(" unless "):])
}

func buildWorkflowEdges(trigger WorkflowTrigger, nodes []WorkflowNode) []WorkflowEdge {
	if len(nodes) == 0 {
		return nil
	}
	edges := []WorkflowEdge{{From: "trigger", To: nodes[0].ID, Kind: "starts", Label: trigger.Kind}}
	for i := 0; i < len(nodes)-1; i++ {
		edges = append(edges, WorkflowEdge{From: nodes[i].ID, To: nodes[i+1].ID, Kind: "next"})
	}
	return edges
}

func buildWorkflowApprovals(req WorkflowGrammarRequest, nodes []WorkflowNode) []WorkflowApprovalGate {
	var gates []WorkflowApprovalGate
	for i, approval := range req.Approvals {
		gates = append(gates, WorkflowApprovalGate{
			ID:     "approval_" + stableBehaviorID(firstNonEmpty(approval.When, approval.Reason, "approval")) + "_" + string(rune('a'+i)),
			Before: workflowNodeForApproval(nodes, approval.When),
			Owner:  firstNonEmpty(approval.Owner, "operator"),
			Reason: firstNonEmpty(approval.Reason, approval.When, "Human approval requested by workflow preferences."),
		})
	}
	for _, node := range nodes {
		if len(node.Risks) == 0 {
			continue
		}
		if containsPlanningAny(strings.ToLower(strings.Join(node.Risks, " ")), "external write", "destructive", "customer contact", "payment", "publishing") || req.Preferences.RequireHumanApprovals {
			gates = append(gates, WorkflowApprovalGate{
				ID:     "approval_" + stableBehaviorID(node.Title),
				Before: node.ID,
				Owner:  firstNonEmpty(node.Owner, "operator"),
				Reason: "Review before " + strings.ToLower(node.Title) + ".",
			})
		}
	}
	return dedupeWorkflowApprovals(gates)
}

func buildWorkflowFailures(req WorkflowGrammarRequest, nodes []WorkflowNode) []WorkflowFailureMode {
	var failures []WorkflowFailureMode
	for _, node := range nodes {
		if node.Tool == "" {
			failures = append(failures, WorkflowFailureMode{NodeID: node.ID, Risk: "Tool or source system is unspecified.", Recovery: "Ask for the source system before execution.", NeedsHuman: true})
		}
		for _, risk := range node.Risks {
			failures = append(failures, WorkflowFailureMode{NodeID: node.ID, Risk: risk, Recovery: workflowRecoveryForRisk(risk), NeedsHuman: containsPlanningAny(risk, "approval", "destructive", "external write", "customer", "payment")})
		}
	}
	for _, exception := range req.Exceptions {
		failures = append(failures, WorkflowFailureMode{Risk: exception, Recovery: "Pause the workflow, preserve context, and route to the named owner for review.", NeedsHuman: true})
	}
	return uniqueWorkflowFailures(failures)
}

func inferWorkflowVariables(req WorkflowGrammarRequest, nodes []WorkflowNode) []WorkflowVariable {
	seen := map[string]WorkflowVariable{}
	for _, input := range append(append([]string{}, req.Conditions...), req.Constraints...) {
		name := workflowVariableName(input)
		if name != "" {
			seen[name] = WorkflowVariable{Name: name, Source: "condition_or_constraint", Required: true}
		}
	}
	for _, node := range nodes {
		for _, need := range node.Needs {
			name := workflowVariableName(need)
			if name != "" {
				seen[name] = WorkflowVariable{Name: name, Source: node.ID, Required: true}
			}
		}
	}
	out := make([]WorkflowVariable, 0, len(seen))
	for _, variable := range seen {
		out = append(out, variable)
	}
	sort.Slice(out, func(i, j int) bool { return out[i].Name < out[j].Name })
	return out
}

func scoreWorkflowReadiness(req WorkflowGrammarRequest, nodes []WorkflowNode, approvals []WorkflowApprovalGate, variables []WorkflowVariable) WorkflowExecutionReadiness {
	score := 0.35
	var reasons, missing []string
	if req.Trigger != "" || containsPlanningAny(req.Specification, "when ", "if ") {
		score += 0.15
		reasons = append(reasons, "Trigger language is present.")
	} else {
		missing = append(missing, "explicit trigger")
	}
	if len(nodes) > 1 {
		score += 0.15
		reasons = append(reasons, "Multiple workflow actions were identified.")
	}
	if len(req.AvailableTools) > 0 {
		score += 0.12
		reasons = append(reasons, "Available tools were supplied.")
	} else {
		missing = append(missing, "tool/source-system mapping")
	}
	if len(approvals) > 0 {
		score += 0.08
		reasons = append(reasons, "Approval boundaries are explicit.")
	}
	if len(variables) > 0 {
		score += 0.05
		reasons = append(reasons, "Required variables can be named before execution.")
	}
	if len(req.Exceptions) == 0 {
		missing = append(missing, "exception handling")
	} else {
		score += 0.05
	}
	if score > 0.95 {
		score = 0.95
	}
	level := "draft"
	switch {
	case score >= 0.78:
		level = "activation_candidate"
	case score >= 0.58:
		level = "review_ready"
	}
	return WorkflowExecutionReadiness{Level: level, Score: score, Reasons: reasons, Missing: uniqueWorkflowStrings(missing)}
}

func buildWorkflowDryRunPlan(req WorkflowGrammarRequest, nodes []WorkflowNode) []string {
	plan := []string{"Validate the trigger against one recent or synthetic example."}
	for _, node := range nodes {
		plan = append(plan, "Dry-run "+strings.ToLower(node.Title)+" without external writes; confirm: "+node.DoneSignal)
	}
	if len(req.Exceptions) > 0 {
		plan = append(plan, "Run an exception case and verify the workflow pauses instead of improvising.")
	}
	return plan
}

func summarizeWorkflow(req WorkflowGrammarRequest, nodes []WorkflowNode, approvals []WorkflowApprovalGate, readiness WorkflowExecutionReadiness) string {
	return sentenceCase(firstNonEmpty(req.Intent, req.Title, "workflow")) + " compiled into " + intToWorkflowWord(len(nodes)) + " workflow " + pluralWorkflowNoun(len(nodes), "node") + " with " + intToWorkflowWord(len(approvals)) + " approval " + pluralWorkflowNoun(len(approvals), "gate") + ". Readiness: " + readiness.Level + "."
}

func workflowOpenQuestions(req WorkflowGrammarRequest, trigger WorkflowTrigger, nodes []WorkflowNode, variables []WorkflowVariable) []string {
	var qs []string
	if req.Trigger == "" && trigger.Statement == "User or client provides the workflow input" {
		qs = append(qs, "What exact event, schedule, or manual command should start this workflow?")
	}
	if len(req.AvailableTools) == 0 {
		qs = append(qs, "Which source systems and tools are available for each action?")
	}
	for _, node := range nodes {
		if node.Tool == "" {
			qs = append(qs, "Which tool should handle: "+node.Title+"?")
			break
		}
	}
	if len(req.Exceptions) == 0 {
		qs = append(qs, "When should this workflow pause and ask a human instead of continuing?")
	}
	if len(variables) == 0 && len(req.Conditions) > 0 {
		qs = append(qs, "Which condition fields are machine-readable versus human judgment?")
	}
	return uniqueWorkflowStrings(qs)
}

func buildWorkflowExpression(trigger WorkflowTrigger, nodes []WorkflowNode) string {
	parts := []string{"WHEN " + trigger.Statement}
	for _, node := range nodes {
		line := "THEN " + node.Title
		if node.Condition != "" {
			line = "IF " + node.Condition + " " + line
		}
		if node.Unless != "" {
			line += " UNLESS " + node.Unless
		}
		parts = append(parts, line)
	}
	return strings.Join(parts, " -> ")
}

func extractWorkflowClause(text, marker string) string {
	lower := strings.ToLower(text)
	idx := strings.Index(lower, marker+" ")
	if idx < 0 {
		return ""
	}
	clause := text[idx+len(marker)+1:]
	for _, stop := range []string{" then ", " and then ", ". ", ";"} {
		if stopIdx := strings.Index(strings.ToLower(clause), stop); stopIdx >= 0 {
			clause = clause[:stopIdx]
		}
	}
	return cleanPlanningText(clause)
}

func inferWorkflowTriggerSource(statement string) string {
	lower := strings.ToLower(statement)
	switch {
	case containsPlanningAny(lower, "email", "inbox"):
		return "inbox"
	case containsPlanningAny(lower, "form"):
		return "form"
	case containsPlanningAny(lower, "calendar", "meeting"):
		return "calendar"
	case containsPlanningAny(lower, "webhook", "api"):
		return "api"
	default:
		return ""
	}
}

func inferWorkflowTool(action string, tools []WorkflowAvailableTool) string {
	lower := strings.ToLower(action)
	for _, tool := range tools {
		if tool.Name != "" && containsPlanningAny(lower, tool.Name) {
			return tool.Name
		}
		for _, actionName := range tool.Actions {
			if actionName != "" && containsPlanningAny(lower, actionName) {
				return tool.Name
			}
		}
	}
	switch {
	case containsPlanningAny(lower, "email", "reply", "send", "inbox"):
		return "email"
	case containsPlanningAny(lower, "crm", "customer", "lead"):
		return "crm"
	case containsPlanningAny(lower, "calendar", "schedule", "book"):
		return "calendar"
	case containsPlanningAny(lower, "task", "ticket", "issue"):
		return "task system"
	case containsPlanningAny(lower, "invoice", "payment", "quote"):
		return "finance system"
	default:
		return ""
	}
}

func inferWorkflowNodeKind(title, tool string) string {
	lower := strings.ToLower(title + " " + tool)
	switch {
	case containsPlanningAny(lower, "review", "approve", "confirm", "check"):
		return "decision"
	case containsPlanningAny(lower, "draft", "write", "summarize"):
		return "draft"
	case containsPlanningAny(lower, "send", "create", "update", "publish", "delete", "charge", "book"):
		return "external_action"
	default:
		return "action"
	}
}

func workflowCanAutomate(req WorkflowGrammarRequest, hint WorkflowActionHint, title, tool string) bool {
	lower := strings.ToLower(title + " " + tool)
	if hint.Destructive || req.Preferences.PreferReadOnly {
		return false
	}
	if containsPlanningAny(lower, "approve", "delete", "charge", "pay", "refund", "publish", "send", "book", "customer") {
		return false
	}
	for _, toolDef := range req.AvailableTools {
		if strings.EqualFold(toolDef.Name, tool) && (toolDef.ReadOnly || toolDef.RequiresOK) {
			return false
		}
	}
	return tool != ""
}

func workflowNodeRisks(req WorkflowGrammarRequest, hint WorkflowActionHint, title, tool string) []string {
	var risks []string
	lower := strings.ToLower(title + " " + tool)
	if tool == "" {
		risks = append(risks, "tool/source ambiguity")
	}
	if hint.Destructive || containsPlanningAny(lower, "delete", "overwrite", "archive") {
		risks = append(risks, "destructive action")
	}
	if containsPlanningAny(lower, "send", "email", "reply", "publish", "post publicly") {
		risks = append(risks, "customer contact or publishing")
	}
	if containsPlanningAny(lower, "payment", "charge", "refund", "invoice", "payroll") {
		risks = append(risks, "payment or regulated financial-adjacent action")
	}
	if len(req.Constraints) == 0 && containsPlanningAny(lower, "when", "if", "unless") {
		risks = append(risks, "condition needs machine-readable source")
	}
	return uniqueWorkflowStrings(risks)
}

func inferWorkflowDoneSignal(title string, outputs []string) string {
	if len(outputs) > 0 {
		return "Output exists: " + outputs[0]
	}
	lower := strings.ToLower(title)
	switch {
	case containsPlanningAny(lower, "draft"):
		return "Draft is ready for review."
	case containsPlanningAny(lower, "send"):
		return "Message is sent after approval."
	case containsPlanningAny(lower, "create"):
		return "Record or task exists with required fields."
	case containsPlanningAny(lower, "review", "check"):
		return "Decision and evidence are recorded."
	default:
		return "Step completed with visible evidence."
	}
}

func conditionForIndex(conditions []string, i int) string {
	if len(conditions) == 0 {
		return ""
	}
	if i < len(conditions) {
		return conditions[i]
	}
	return conditions[len(conditions)-1]
}

func exceptionForAction(exceptions []string, title string) string {
	for _, exception := range exceptions {
		if containsPlanningAny(strings.ToLower(exception), strings.ToLower(title)) {
			return exception
		}
	}
	return ""
}

func workflowNodeForApproval(nodes []WorkflowNode, when string) string {
	for _, node := range nodes {
		if when != "" && containsPlanningAny(strings.ToLower(node.Title+" "+node.Tool), strings.ToLower(when)) {
			return node.ID
		}
	}
	if len(nodes) > 0 {
		return nodes[0].ID
	}
	return ""
}

func workflowRecoveryForRisk(risk string) string {
	switch {
	case containsPlanningAny(risk, "tool/source"):
		return "Ask for the missing tool/source mapping and keep the draft paused."
	case containsPlanningAny(risk, "customer", "publishing"):
		return "Draft only; require explicit approval before contact or publishing."
	case containsPlanningAny(risk, "payment", "financial"):
		return "Stop before payment/account action and route to the responsible human."
	case containsPlanningAny(risk, "destructive"):
		return "Require confirmation, backup, and rollback path before execution."
	default:
		return "Pause, preserve context, and ask for clarification."
	}
}

func workflowVariableName(s string) string {
	s = strings.ToLower(cleanPlanningText(s))
	replacer := strings.NewReplacer(" ", "_", "-", "_", "/", "_", ":", "", ",", "", ".", "")
	s = replacer.Replace(s)
	parts := strings.Split(s, "_")
	if len(parts) > 4 {
		parts = parts[:4]
	}
	name := strings.Join(parts, "_")
	name = strings.Trim(name, "_")
	if len(name) < 3 {
		return ""
	}
	return name
}

func uniqueWorkflowStrings(values []string) []string {
	seen := map[string]bool{}
	out := make([]string, 0, len(values))
	for _, value := range values {
		value = cleanPlanningText(value)
		if value == "" {
			continue
		}
		key := strings.ToLower(value)
		if seen[key] {
			continue
		}
		seen[key] = true
		out = append(out, value)
	}
	return out
}

func dedupeWorkflowApprovals(values []WorkflowApprovalGate) []WorkflowApprovalGate {
	seen := map[string]bool{}
	var out []WorkflowApprovalGate
	for _, value := range values {
		key := value.Before + "|" + value.After + "|" + strings.ToLower(value.Reason)
		if seen[key] {
			continue
		}
		seen[key] = true
		out = append(out, value)
	}
	return out
}

func uniqueWorkflowFailures(values []WorkflowFailureMode) []WorkflowFailureMode {
	seen := map[string]bool{}
	var out []WorkflowFailureMode
	for _, value := range values {
		key := value.NodeID + "|" + strings.ToLower(value.Risk)
		if seen[key] {
			continue
		}
		seen[key] = true
		out = append(out, value)
	}
	return out
}

func intToWorkflowWord(n int) string {
	switch n {
	case 0:
		return "zero"
	case 1:
		return "one"
	case 2:
		return "two"
	case 3:
		return "three"
	case 4:
		return "four"
	case 5:
		return "five"
	default:
		return "multiple"
	}
}

func pluralWorkflowNoun(n int, noun string) string {
	if n == 1 {
		return noun
	}
	return noun + "s"
}

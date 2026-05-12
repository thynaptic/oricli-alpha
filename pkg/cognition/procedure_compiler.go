package cognition

import (
	"sort"
	"strings"
)

type ProcedureCompileRequest struct {
	Surface       string                 `json:"surface,omitempty"`
	Title         string                 `json:"title,omitempty"`
	Description   string                 `json:"description,omitempty"`
	Transcript    string                 `json:"transcript,omitempty"`
	Observations  []ProcedureObservation `json:"observations,omitempty"`
	Actor         string                 `json:"actor,omitempty"`
	Tools         []string               `json:"tools,omitempty"`
	Inputs        []string               `json:"inputs,omitempty"`
	Outputs       []string               `json:"outputs,omitempty"`
	Constraints   []string               `json:"constraints,omitempty"`
	Frequency     string                 `json:"frequency,omitempty"`
	OutcomeSignal string                 `json:"outcome_signal,omitempty"`
	Metadata      map[string]any         `json:"metadata,omitempty"`
}

type ProcedureObservation struct {
	Title    string   `json:"title,omitempty"`
	Detail   string   `json:"detail,omitempty"`
	Actor    string   `json:"actor,omitempty"`
	Tool     string   `json:"tool,omitempty"`
	Evidence string   `json:"evidence,omitempty"`
	Outcome  string   `json:"outcome,omitempty"`
	Tags     []string `json:"tags,omitempty"`
}

type CompiledProcedure struct {
	ID                  string                       `json:"id"`
	Surface             string                       `json:"surface"`
	Title               string                       `json:"title"`
	Summary             string                       `json:"summary"`
	Trigger             string                       `json:"trigger"`
	Inputs              []string                     `json:"inputs,omitempty"`
	Outputs             []string                     `json:"outputs,omitempty"`
	Steps               []ProcedureStep              `json:"steps"`
	Checklist           []string                     `json:"checklist"`
	SOP                 ProcedureSOP                 `json:"sop"`
	SkillCandidate      ProcedureSkillCandidate      `json:"skill_candidate"`
	AutomationCandidate ProcedureAutomationCandidate `json:"automation_candidate"`
	SCLSeed             ProcedureSCLSeed             `json:"scl_seed"`
	Integration         ProcedureIntegrationHints    `json:"integration"`
	Guardrails          []string                     `json:"guardrails"`
	OpenQuestions       []string                     `json:"open_questions,omitempty"`
}

type ProcedureStep struct {
	Index       int      `json:"index"`
	Action      string   `json:"action"`
	Tool        string   `json:"tool,omitempty"`
	Owner       string   `json:"owner,omitempty"`
	Why         string   `json:"why,omitempty"`
	DoneSignal  string   `json:"done_signal"`
	Risks       []string `json:"risks,omitempty"`
	CanDelegate bool     `json:"can_delegate"`
}

type ProcedureSOP struct {
	Name          string   `json:"name"`
	UseWhen       string   `json:"use_when"`
	DoFirst       string   `json:"do_first"`
	QualityBar    []string `json:"quality_bar"`
	RecoveryPath  []string `json:"recovery_path"`
	ReviewCadence string   `json:"review_cadence"`
}

type ProcedureSkillCandidate struct {
	Name            string   `json:"name"`
	Description     string   `json:"description"`
	TriggerPhrases  []string `json:"trigger_phrases"`
	RequiredInputs  []string `json:"required_inputs,omitempty"`
	ExpectedOutputs []string `json:"expected_outputs,omitempty"`
	ReputationSeed  float64  `json:"reputation_seed"`
}

type ProcedureAutomationCandidate struct {
	Readiness   string   `json:"readiness"`
	Reason      string   `json:"reason"`
	SafeActions []string `json:"safe_actions,omitempty"`
	NeedsHuman  []string `json:"needs_human,omitempty"`
}

type ProcedureSCLSeed struct {
	Tier       string   `json:"tier"`
	Subject    string   `json:"subject"`
	Content    string   `json:"content"`
	Confidence float64  `json:"confidence"`
	Tags       []string `json:"tags"`
}

type ProcedureIntegrationHints struct {
	SCL     []string `json:"scl"`
	Skills  []string `json:"skills"`
	GoalDAG []string `json:"goal_dag"`
	Chronos []string `json:"chronos"`
	Forge   []string `json:"forge,omitempty"`
}

// CompileProcedure turns observed workflow traces into governed operational
// knowledge: SOP, checklist, skill candidate, and automation readiness.
func CompileProcedure(req ProcedureCompileRequest) CompiledProcedure {
	req = normalizeProcedureRequest(req)
	steps := buildProcedureSteps(req)
	checklist := buildProcedureChecklist(steps)
	title := sentenceCase(firstNonEmpty(req.Title, inferProcedureTitle(req), "Observed workflow"))
	summary := summarizeProcedure(req, steps)
	skill := procedureSkillCandidate(req, title)
	auto := procedureAutomationCandidate(req, steps)

	return CompiledProcedure{
		ID:        "proc_" + stableBehaviorID(title),
		Surface:   normalizeQuestSurface(req.Surface),
		Title:     title,
		Summary:   summary,
		Trigger:   inferProcedureTrigger(req),
		Inputs:    uniqueProcedureStrings(req.Inputs),
		Outputs:   uniqueProcedureStrings(req.Outputs),
		Steps:     steps,
		Checklist: checklist,
		SOP: ProcedureSOP{
			Name:          title,
			UseWhen:       inferProcedureTrigger(req),
			DoFirst:       firstProcedureAction(steps),
			QualityBar:    procedureQualityBar(req),
			RecoveryPath:  procedureRecoveryPath(req),
			ReviewCadence: procedureReviewCadence(req),
		},
		SkillCandidate:      skill,
		AutomationCandidate: auto,
		SCLSeed: ProcedureSCLSeed{
			Tier:       "skills",
			Subject:    skill.Name,
			Content:    summary + " Steps: " + strings.Join(checklist, " "),
			Confidence: procedureConfidence(req, steps),
			Tags:       []string{"procedure_compiler", normalizeQuestSurface(req.Surface), "skill_candidate"},
		},
		Integration: ProcedureIntegrationHints{
			SCL:     []string{"Write as TierSkills only after human confirmation or repeated successful use.", "Track outcome, latency, owner, and failure mode for reputation updates."},
			Skills:  []string{"Promote to .ori skill or crystal only after reputation crosses policy threshold.", "Keep required inputs explicit before allowing autonomous execution."},
			GoalDAG: []string{"Convert checklist into a GoalDAG for repeatable workflows with approval gates.", "Attach recovery path to blocked or failed nodes."},
			Chronos: []string{"Record last-run time, decay stale procedures, and prompt review after repeated misses."},
			Forge:   []string{"Only generate tools for stable, low-risk steps with clear inputs and reversible effects."},
		},
		Guardrails: []string{
			"Do not claim a procedure was saved, automated, or registered unless a write tool confirms it.",
			"Require human approval before converting observed behavior into durable SOP or executable automation.",
			"Keep permissions, secrets, customer data, and destructive operations outside automatic steps.",
		},
		OpenQuestions: procedureOpenQuestions(req),
	}
}

func normalizeProcedureRequest(req ProcedureCompileRequest) ProcedureCompileRequest {
	req.Surface = normalizeQuestSurface(req.Surface)
	req.Title = cleanPlanningText(req.Title)
	req.Description = cleanPlanningText(req.Description)
	req.Transcript = cleanPlanningText(req.Transcript)
	req.Actor = cleanPlanningText(firstNonEmpty(req.Actor, "operator"))
	req.Frequency = strings.ToLower(strings.TrimSpace(req.Frequency))
	req.OutcomeSignal = cleanPlanningText(req.OutcomeSignal)
	req.Tools = uniqueProcedureStrings(req.Tools)
	req.Inputs = uniqueProcedureStrings(req.Inputs)
	req.Outputs = uniqueProcedureStrings(req.Outputs)
	for i := range req.Observations {
		req.Observations[i].Title = cleanPlanningText(firstNonEmpty(req.Observations[i].Title, req.Observations[i].Detail, "Observed step"))
		req.Observations[i].Detail = cleanPlanningText(req.Observations[i].Detail)
		req.Observations[i].Actor = cleanPlanningText(firstNonEmpty(req.Observations[i].Actor, req.Actor))
		req.Observations[i].Tool = cleanPlanningText(req.Observations[i].Tool)
		req.Observations[i].Evidence = cleanPlanningText(req.Observations[i].Evidence)
		req.Observations[i].Outcome = cleanPlanningText(req.Observations[i].Outcome)
	}
	return req
}

func buildProcedureSteps(req ProcedureCompileRequest) []ProcedureStep {
	var atoms []ProcedureObservation
	atoms = append(atoms, req.Observations...)
	if len(atoms) == 0 {
		for _, part := range splitPlanningAtoms(firstNonEmpty(req.Description, req.Transcript, req.Title)) {
			atoms = append(atoms, ProcedureObservation{Title: part, Actor: req.Actor})
		}
	}
	if len(atoms) == 0 {
		atoms = []ProcedureObservation{{Title: "Clarify the workflow start and finish", Actor: req.Actor}}
	}
	if len(atoms) > 8 {
		atoms = atoms[:8]
	}
	steps := make([]ProcedureStep, 0, len(atoms))
	for i, obs := range atoms {
		action := actionizePlanningAtom(obs.Title)
		tool := firstNonEmpty(obs.Tool, inferProcedureTool(action, req.Tools))
		steps = append(steps, ProcedureStep{
			Index:       i + 1,
			Action:      action,
			Tool:        tool,
			Owner:       firstNonEmpty(obs.Actor, req.Actor),
			Why:         firstNonEmpty(obs.Detail, obs.Evidence, "Preserves the observed workflow as an executable step."),
			DoneSignal:  inferProcedureDoneSignal(obs, action),
			Risks:       procedureStepRisks(obs, action),
			CanDelegate: procedureStepCanDelegate(obs, action),
		})
	}
	return steps
}

func buildProcedureChecklist(steps []ProcedureStep) []string {
	out := make([]string, 0, len(steps))
	for _, step := range steps {
		out = append(out, step.Action+" — "+step.DoneSignal)
	}
	return out
}

func procedureSkillCandidate(req ProcedureCompileRequest, title string) ProcedureSkillCandidate {
	name := "skill_" + stableBehaviorID(title)
	triggers := []string{
		strings.ToLower(title),
		"run " + strings.ToLower(title),
		"how do we " + strings.ToLower(strings.TrimPrefix(title, "Compile ")),
	}
	return ProcedureSkillCandidate{
		Name:            name,
		Description:     "Repeatable procedure compiled from observed workflow: " + title,
		TriggerPhrases:  uniqueProcedureStrings(triggers),
		RequiredInputs:  uniqueProcedureStrings(req.Inputs),
		ExpectedOutputs: uniqueProcedureStrings(req.Outputs),
		ReputationSeed:  procedureConfidence(req, nil),
	}
}

func procedureAutomationCandidate(req ProcedureCompileRequest, steps []ProcedureStep) ProcedureAutomationCandidate {
	delegable := 0
	for _, step := range steps {
		if step.CanDelegate {
			delegable++
		}
	}
	if len(steps) > 0 && delegable == len(steps) && len(req.Constraints) == 0 {
		return ProcedureAutomationCandidate{
			Readiness:   "candidate",
			Reason:      "All observed steps look low-risk and have visible done signals.",
			SafeActions: procedureChecklistActions(steps),
		}
	}
	return ProcedureAutomationCandidate{
		Readiness:   "assistive",
		Reason:      "Keep ORI in checklist/copilot mode until permission, inputs, and risk boundaries are explicit.",
		SafeActions: procedureSafeActions(steps),
		NeedsHuman:  []string{"approval before external writes", "confirmation for customer-facing messages", "secret or permission handling"},
	}
}

func inferProcedureTitle(req ProcedureCompileRequest) string {
	for _, out := range req.Outputs {
		if out != "" {
			return "create " + out
		}
	}
	for _, obs := range req.Observations {
		if obs.Title != "" {
			return obs.Title
		}
	}
	return firstNonEmpty(req.Description, req.Transcript)
}

func summarizeProcedure(req ProcedureCompileRequest, steps []ProcedureStep) string {
	return sentenceCase(firstNonEmpty(req.Title, inferProcedureTitle(req), "workflow")) +
		" compiles " + intToMomentumString(len(steps)) + " observed steps into a reusable procedure for " +
		firstNonEmpty(req.Actor, "the operator") + "."
}

func inferProcedureTrigger(req ProcedureCompileRequest) string {
	if req.Frequency != "" {
		return "Use when this " + req.Frequency + " workflow recurs."
	}
	if req.OutcomeSignal != "" {
		return "Use when the desired outcome is: " + req.OutcomeSignal + "."
	}
	return "Use when the same workflow appears more than once or needs handoff."
}

func firstProcedureAction(steps []ProcedureStep) string {
	if len(steps) == 0 {
		return "Name the first visible workflow step."
	}
	return steps[0].Action
}

func procedureQualityBar(req ProcedureCompileRequest) []string {
	bar := []string{"Every step has a visible done signal.", "Inputs and outputs are explicit before delegation."}
	if req.OutcomeSignal != "" {
		bar = append(bar, "Outcome matches: "+req.OutcomeSignal)
	}
	if len(req.Constraints) > 0 {
		bar = append(bar, "Constraints respected: "+strings.Join(uniqueProcedureStrings(req.Constraints), "; "))
	}
	return bar
}

func procedureRecoveryPath(req ProcedureCompileRequest) []string {
	return []string{
		"Pause at the failed step and record the blocker.",
		"Ask for the missing input, permission, or decision.",
		"Update the procedure if the same blocker appears twice.",
	}
}

func procedureReviewCadence(req ProcedureCompileRequest) string {
	switch req.Frequency {
	case "daily":
		return "Review weekly or after three failed runs."
	case "weekly":
		return "Review monthly or after two failed runs."
	case "monthly", "quarterly":
		return "Review after each run before archiving lessons."
	default:
		return "Review after three uses or one significant failure."
	}
}

func procedureConfidence(req ProcedureCompileRequest, steps []ProcedureStep) float64 {
	score := 0.48
	if len(req.Observations) > 0 {
		score += 0.16
	}
	if len(req.Inputs) > 0 && len(req.Outputs) > 0 {
		score += 0.12
	}
	if req.OutcomeSignal != "" {
		score += 0.08
	}
	if len(steps) >= 3 {
		score += 0.08
	}
	if score > 0.86 {
		return 0.86
	}
	return score
}

func procedureOpenQuestions(req ProcedureCompileRequest) []string {
	var qs []string
	if len(req.Inputs) == 0 {
		qs = append(qs, "What inputs are required before this procedure can run?")
	}
	if len(req.Outputs) == 0 {
		qs = append(qs, "What artifact, decision, or state proves the procedure is complete?")
	}
	if req.OutcomeSignal == "" {
		qs = append(qs, "How should ORI know the procedure succeeded?")
	}
	return qs
}

func inferProcedureTool(action string, tools []string) string {
	lower := strings.ToLower(action)
	for _, tool := range tools {
		t := strings.ToLower(tool)
		if t != "" && strings.Contains(lower, t) {
			return tool
		}
	}
	switch {
	case containsPlanningAny(lower, "email", "reply", "inbox"):
		return "email"
	case containsPlanningAny(lower, "crm", "deal", "account", "lead"):
		return "crm"
	case containsPlanningAny(lower, "issue", "ticket", "bug"):
		return "issue_tracker"
	case containsPlanningAny(lower, "doc", "sop", "notes"):
		return "document"
	default:
		return ""
	}
}

func inferProcedureDoneSignal(obs ProcedureObservation, action string) string {
	if obs.Outcome != "" {
		return obs.Outcome
	}
	lower := strings.ToLower(action)
	switch {
	case containsPlanningAny(lower, "send", "reply", "email"):
		return "Draft is approved or message is sent by the owning client."
	case containsPlanningAny(lower, "update", "record", "crm"):
		return "The record reflects the latest verified state."
	case containsPlanningAny(lower, "create", "draft", "write"):
		return "A reviewable artifact exists."
	default:
		return "The step has a visible output or decision."
	}
}

func procedureStepRisks(obs ProcedureObservation, action string) []string {
	lower := strings.ToLower(action + " " + obs.Detail)
	var risks []string
	if containsPlanningAny(lower, "delete", "remove", "overwrite") {
		risks = append(risks, "destructive change")
	}
	if containsPlanningAny(lower, "customer", "client", "send", "publish") {
		risks = append(risks, "external-facing action")
	}
	if containsPlanningAny(lower, "secret", "password", "token", "payment") {
		risks = append(risks, "sensitive data or permission boundary")
	}
	return risks
}

func procedureStepCanDelegate(obs ProcedureObservation, action string) bool {
	return len(procedureStepRisks(obs, action)) == 0 && !containsPlanningAny(strings.ToLower(action), "approve", "decide", "sign off")
}

func procedureChecklistActions(steps []ProcedureStep) []string {
	out := make([]string, 0, len(steps))
	for _, step := range steps {
		out = append(out, step.Action)
	}
	return out
}

func procedureSafeActions(steps []ProcedureStep) []string {
	var out []string
	for _, step := range steps {
		if step.CanDelegate {
			out = append(out, step.Action)
		}
	}
	if len(out) == 0 {
		out = []string{"prepare checklist", "draft artifact", "summarize blockers"}
	}
	return out
}

func uniqueProcedureStrings(values []string) []string {
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

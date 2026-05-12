package cognition

import "strings"

type ProceduralCrystallizeRequest struct {
	Surface       string                 `json:"surface,omitempty"`
	Workflow      string                 `json:"workflow,omitempty"`
	Objective     string                 `json:"objective,omitempty"`
	Trigger       string                 `json:"trigger,omitempty"`
	Runs          []WorkflowRunTrace     `json:"runs,omitempty"`
	ObservedSteps []string               `json:"observed_steps,omitempty"`
	Tools         []string               `json:"tools,omitempty"`
	Inputs        []string               `json:"inputs,omitempty"`
	Outputs       []string               `json:"outputs,omitempty"`
	PainPoints    []string               `json:"pain_points,omitempty"`
	Constraints   []string               `json:"constraints,omitempty"`
	OutcomeSignal string                 `json:"outcome_signal,omitempty"`
	Metadata      map[string]interface{} `json:"metadata,omitempty"`
}

type WorkflowRunTrace struct {
	ID        string   `json:"id,omitempty"`
	Time      string   `json:"time,omitempty"`
	Trigger   string   `json:"trigger,omitempty"`
	Steps     []string `json:"steps,omitempty"`
	Tools     []string `json:"tools,omitempty"`
	Outcome   string   `json:"outcome,omitempty"`
	Friction  string   `json:"friction,omitempty"`
	Evidence  []string `json:"evidence,omitempty"`
	Completed bool     `json:"completed,omitempty"`
}

type ProceduralCrystallizationPlan struct {
	ID                  string                            `json:"id"`
	Surface             string                            `json:"surface"`
	Workflow            string                            `json:"workflow"`
	Objective           string                            `json:"objective"`
	Summary             string                            `json:"summary"`
	DetectedPattern     CrystallizedPattern               `json:"detected_pattern"`
	CandidateProcedure  CrystallizedProcedureCandidate    `json:"candidate_procedure"`
	SkillCandidate      ProcedureSkillCandidate           `json:"skill_candidate"`
	AutomationCandidate ProcedureAutomationCandidate      `json:"automation_candidate"`
	NextObservation     CrystallizerObservationPlan       `json:"next_observation"`
	MemorySeeds         []QuestMemorySeed                 `json:"memory_seeds,omitempty"`
	Integration         ProceduralCrystallizerIntegration `json:"integration"`
	Guardrails          []string                          `json:"guardrails"`
	OpenQuestions       []string                          `json:"open_questions,omitempty"`
}

type CrystallizedPattern struct {
	Trigger        string   `json:"trigger"`
	RepeatedSteps  []string `json:"repeated_steps,omitempty"`
	FrictionPoints []string `json:"friction_points,omitempty"`
	Confidence     float64  `json:"confidence"`
	Readiness      string   `json:"readiness"`
	Why            string   `json:"why"`
}

type CrystallizedProcedureCandidate struct {
	Name          string   `json:"name"`
	UseWhen       string   `json:"use_when"`
	Steps         []string `json:"steps"`
	Inputs        []string `json:"inputs,omitempty"`
	Outputs       []string `json:"outputs,omitempty"`
	QualityBar    []string `json:"quality_bar,omitempty"`
	ReviewCadence string   `json:"review_cadence"`
}

type CrystallizerObservationPlan struct {
	WatchFor    []string `json:"watch_for"`
	Capture     []string `json:"capture"`
	PromoteWhen string   `json:"promote_when"`
	DismissWhen string   `json:"dismiss_when"`
}

type ProceduralCrystallizerIntegration struct {
	Procedure []string `json:"procedure"`
	Skills    []string `json:"skills"`
	WorkGraph []string `json:"workgraph"`
	Memory    []string `json:"memory"`
	Temporal  []string `json:"temporal"`
	Forge     []string `json:"forge"`
}

// CrystallizeProcedure notices repeated operational patterns and packages the
// next safe promotion step: observe more, draft an SOP, propose a skill, or
// prepare a low-risk automation candidate.
func CrystallizeProcedure(req ProceduralCrystallizeRequest) ProceduralCrystallizationPlan {
	req = normalizeProceduralCrystallizeRequest(req)
	pattern := detectCrystallizedPattern(req)
	procedure := buildCrystallizedProcedureCandidate(req, pattern)
	skill := buildCrystallizedSkillCandidate(req, procedure, pattern)
	auto := buildCrystallizedAutomationCandidate(req, pattern)

	return ProceduralCrystallizationPlan{
		ID:                  "crystal_" + stableBehaviorID(req.Workflow+"_"+req.Objective),
		Surface:             normalizeQuestSurface(req.Surface),
		Workflow:            req.Workflow,
		Objective:           req.Objective,
		Summary:             summarizeProceduralCrystallization(req, pattern),
		DetectedPattern:     pattern,
		CandidateProcedure:  procedure,
		SkillCandidate:      skill,
		AutomationCandidate: auto,
		NextObservation:     buildCrystallizerObservationPlan(req, pattern),
		MemorySeeds:         crystallizerMemorySeeds(req, pattern),
		Integration: ProceduralCrystallizerIntegration{
			Procedure: []string{"Send candidate_procedure to /procedure/compile when the user wants a full SOP/checklist object."},
			Skills:    []string{"Register as .ori only after repeated successful runs and explicit approval."},
			WorkGraph: []string{"Attach high-friction recurring workflows to /workgraph/compile as operator burden or process debt."},
			Memory:    []string{"Persist run patterns, triggers, and quality bars only after source-backed confirmation."},
			Temporal:  []string{"Use /temporal/coordinate for review cadence and recurring trigger windows."},
			Forge:     []string{"Only generate executable tools for stable, reversible steps with explicit inputs and outputs."},
		},
		Guardrails: []string{
			"Do not claim a workflow was saved, automated, scheduled, or registered unless a tool confirms it.",
			"Require approval before turning observed behavior into durable skill state or external automation.",
			"Keep destructive, paid, customer-facing, or credential-bearing actions behind human review.",
		},
		OpenQuestions: crystallizerOpenQuestions(req, pattern),
	}
}

func normalizeProceduralCrystallizeRequest(req ProceduralCrystallizeRequest) ProceduralCrystallizeRequest {
	req.Surface = normalizeQuestSurface(req.Surface)
	req.Workflow = cleanPlanningText(firstNonEmpty(req.Workflow, req.Objective, "recurring workflow"))
	req.Objective = cleanPlanningText(firstNonEmpty(req.Objective, "reduce repeated operational burden"))
	req.Trigger = cleanPlanningText(req.Trigger)
	req.ObservedSteps = uniqueCrystallizerStrings(req.ObservedSteps)
	req.Tools = uniqueActionStrings(req.Tools)
	req.Inputs = uniqueActionStrings(req.Inputs)
	req.Outputs = uniqueActionStrings(req.Outputs)
	req.PainPoints = uniqueActionStrings(req.PainPoints)
	req.Constraints = uniqueActionStrings(req.Constraints)
	req.OutcomeSignal = cleanPlanningText(req.OutcomeSignal)
	for i := range req.Runs {
		req.Runs[i].ID = cleanPlanningText(req.Runs[i].ID)
		req.Runs[i].Time = cleanPlanningText(req.Runs[i].Time)
		req.Runs[i].Trigger = cleanPlanningText(req.Runs[i].Trigger)
		req.Runs[i].Steps = uniqueCrystallizerStrings(req.Runs[i].Steps)
		req.Runs[i].Tools = uniqueActionStrings(req.Runs[i].Tools)
		req.Runs[i].Outcome = cleanPlanningText(req.Runs[i].Outcome)
		req.Runs[i].Friction = cleanPlanningText(req.Runs[i].Friction)
		req.Runs[i].Evidence = uniqueActionStrings(req.Runs[i].Evidence)
	}
	return req
}

func detectCrystallizedPattern(req ProceduralCrystallizeRequest) CrystallizedPattern {
	steps := repeatedCrystallizerSteps(req)
	friction := append([]string{}, req.PainPoints...)
	for _, run := range req.Runs {
		if run.Friction != "" {
			friction = append(friction, run.Friction)
		}
	}
	friction = uniqueActionStrings(friction)
	conf := 0.32 + float64(len(req.Runs))*0.1 + float64(len(steps))*0.035
	if len(req.OutcomeSignal) > 0 {
		conf += 0.08
	}
	if len(friction) > 0 {
		conf += 0.06
	}
	if conf > 0.91 {
		conf = 0.91
	}
	return CrystallizedPattern{
		Trigger:        firstNonEmpty(req.Trigger, inferCrystallizerTrigger(req), "when this workflow recurs"),
		RepeatedSteps:  steps,
		FrictionPoints: friction,
		Confidence:     conf,
		Readiness:      crystallizerReadiness(conf),
		Why:            crystallizerWhy(req, conf),
	}
}

func repeatedCrystallizerSteps(req ProceduralCrystallizeRequest) []string {
	counts := map[string]int{}
	var ordered []string
	for _, step := range req.ObservedSteps {
		key := strings.ToLower(step)
		if counts[key] == 0 {
			ordered = append(ordered, sentenceCase(step))
		}
		counts[key]++
	}
	for _, run := range req.Runs {
		for _, step := range run.Steps {
			key := strings.ToLower(step)
			if counts[key] == 0 {
				ordered = append(ordered, sentenceCase(step))
			}
			counts[key]++
		}
	}
	if len(ordered) == 0 {
		ordered = []string{"Clarify the repeated trigger", "Capture the successful path", "Confirm the done signal"}
	}
	if len(ordered) > 8 {
		return ordered[:8]
	}
	return ordered
}

func buildCrystallizedProcedureCandidate(req ProceduralCrystallizeRequest, pattern CrystallizedPattern) CrystallizedProcedureCandidate {
	return CrystallizedProcedureCandidate{
		Name:          sentenceCase(req.Workflow),
		UseWhen:       pattern.Trigger,
		Steps:         pattern.RepeatedSteps,
		Inputs:        req.Inputs,
		Outputs:       req.Outputs,
		QualityBar:    crystallizerQualityBar(req, pattern),
		ReviewCadence: crystallizerReviewCadence(pattern),
	}
}

func buildCrystallizedSkillCandidate(req ProceduralCrystallizeRequest, procedure CrystallizedProcedureCandidate, pattern CrystallizedPattern) ProcedureSkillCandidate {
	return ProcedureSkillCandidate{
		Name:            strings.ReplaceAll(strings.ToLower(procedure.Name), " ", "_"),
		Description:     "Reusable operator for " + procedure.UseWhen + ".",
		TriggerPhrases:  []string{procedure.UseWhen, "run " + procedure.Name, "help me with " + req.Workflow},
		RequiredInputs:  req.Inputs,
		ExpectedOutputs: req.Outputs,
		ReputationSeed:  pattern.Confidence,
	}
}

func buildCrystallizedAutomationCandidate(req ProceduralCrystallizeRequest, pattern CrystallizedPattern) ProcedureAutomationCandidate {
	if pattern.Confidence >= 0.76 && !containsPlanningAny(strings.ToLower(strings.Join(req.Constraints, " ")+" "+strings.Join(req.PainPoints, " ")), "approval", "customer", "payment", "delete", "credential") {
		return ProcedureAutomationCandidate{
			Readiness:   "draft",
			Reason:      "Pattern is repeated enough to draft reversible automation steps.",
			SafeActions: []string{"prepare checklist", "prefill draft", "gather context", "validate inputs"},
			NeedsHuman:  []string{"external send", "durable write", "permission changes"},
		}
	}
	return ProcedureAutomationCandidate{
		Readiness:   "observe",
		Reason:      "Pattern needs more successful runs or clearer safety boundaries before automation.",
		SafeActions: []string{"capture next run", "draft SOP", "identify done signal"},
		NeedsHuman:  []string{"promotion approval", "risk review"},
	}
}

func buildCrystallizerObservationPlan(req ProceduralCrystallizeRequest, pattern CrystallizedPattern) CrystallizerObservationPlan {
	return CrystallizerObservationPlan{
		WatchFor:    []string{pattern.Trigger, "same steps repeated", "same friction repeated", "same outcome signal"},
		Capture:     []string{"trigger", "inputs", "steps", "tools used", "outcome", "friction", "user edits"},
		PromoteWhen: "At least three successful runs share the same trigger, inputs, done signal, and low-risk boundary.",
		DismissWhen: "Runs diverge because the work is genuinely bespoke or risk depends on private judgment.",
	}
}

func summarizeProceduralCrystallization(req ProceduralCrystallizeRequest, pattern CrystallizedPattern) string {
	return sentenceCase(req.Workflow) + " is at " + pattern.Readiness + " readiness with " + intToMomentumString(len(pattern.RepeatedSteps)) + " repeated steps."
}

func crystallizerMemorySeeds(req ProceduralCrystallizeRequest, pattern CrystallizedPattern) []QuestMemorySeed {
	return []QuestMemorySeed{
		{Key: "crystallizer_workflow", Value: req.Workflow, Importance: 0.62},
		{Key: "crystallizer_trigger", Value: pattern.Trigger, Importance: 0.66},
		{Key: "crystallizer_readiness", Value: pattern.Readiness, Importance: 0.58},
	}
}

func inferCrystallizerTrigger(req ProceduralCrystallizeRequest) string {
	for _, run := range req.Runs {
		if run.Trigger != "" {
			return run.Trigger
		}
	}
	return "when " + strings.ToLower(req.Workflow) + " appears again"
}

func crystallizerReadiness(conf float64) string {
	switch {
	case conf >= 0.78:
		return "skill_candidate"
	case conf >= 0.62:
		return "sop_candidate"
	case conf >= 0.48:
		return "observe_next_run"
	default:
		return "not_ready"
	}
}

func crystallizerWhy(req ProceduralCrystallizeRequest, conf float64) string {
	if conf >= 0.78 {
		return "Repeated runs are stable enough to propose a reusable skill candidate."
	}
	if len(req.Runs) == 0 {
		return "No run history was supplied, so ORI should observe before promotion."
	}
	return "The workflow is recurring, but needs clearer outcomes or another successful run."
}

func crystallizerQualityBar(req ProceduralCrystallizeRequest, pattern CrystallizedPattern) []string {
	bar := []string{"Trigger is explicit.", "Inputs and done signal are visible.", "Human approval gates are preserved."}
	if req.OutcomeSignal != "" {
		bar = append(bar, "Outcome signal: "+req.OutcomeSignal)
	}
	if len(pattern.FrictionPoints) > 0 {
		bar = append(bar, "Known friction is reduced or routed.")
	}
	return bar
}

func crystallizerReviewCadence(pattern CrystallizedPattern) string {
	if pattern.Readiness == "skill_candidate" {
		return "review after next 3 runs"
	}
	return "review after next successful run"
}

func crystallizerOpenQuestions(req ProceduralCrystallizeRequest, pattern CrystallizedPattern) []string {
	var qs []string
	if len(req.Inputs) == 0 {
		qs = append(qs, "What inputs are required before this workflow can run?")
	}
	if len(req.Outputs) == 0 {
		qs = append(qs, "What output proves the workflow finished?")
	}
	if pattern.Readiness == "not_ready" || pattern.Readiness == "observe_next_run" {
		qs = append(qs, "What should ORI capture on the next run?")
	}
	return qs
}

func uniqueCrystallizerStrings(values []string) []string {
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
	return out
}

package cognition

import (
	"fmt"
	"math"
	"regexp"
	"sort"
	"strings"
	"time"
)

// PlanningPreferences capture reusable planning tendencies without tying ORI
// to any particular task app or data store.
type PlanningPreferences struct {
	MaxVisibleSteps    int
	PreferredStepMins  int
	Energy             string
	OverwhelmSensitive bool
}

// PlanningRequest is a surface-agnostic request for executive-function planning.
type PlanningRequest struct {
	Goal        string
	Notes       string
	Constraints []string
	Preferences PlanningPreferences
}

// PlanningPlan is a deterministic, app-neutral planning draft.
type PlanningPlan struct {
	Objective        string         `json:"objective"`
	DefinitionOfDone string         `json:"definition_of_done"`
	Assumptions      []string       `json:"assumptions,omitempty"`
	Steps            []PlanningStep `json:"steps"`
	NextAction       string         `json:"next_action"`
	Load             CognitiveLoad  `json:"load"`
	Governance       []string       `json:"governance,omitempty"`
}

type PlanningStep struct {
	Title      string `json:"title"`
	Why        string `json:"why,omitempty"`
	Minutes    int    `json:"minutes"`
	Energy     string `json:"energy,omitempty"`
	DependsOn  []int  `json:"depends_on,omitempty"`
	DoneSignal string `json:"done_signal,omitempty"`
}

// CognitiveLoad estimates why a plan may feel hard before the user starts.
type CognitiveLoad struct {
	Score            float64  `json:"score"`
	Tier             string   `json:"tier"`
	Complexity       float64  `json:"complexity"`
	Ambiguity        float64  `json:"ambiguity"`
	ContextSwitching float64  `json:"context_switching"`
	ActivationEnergy float64  `json:"activation_energy"`
	Reasons          []string `json:"reasons,omitempty"`
}

type TaskPatchRequest struct {
	CurrentSteps []PlanningStep
	Instruction  string
}

type TaskPatch struct {
	Operation string         `json:"operation"`
	Reason    string         `json:"reason,omitempty"`
	Steps     []PlanningStep `json:"steps,omitempty"`
}

type FocusCue struct {
	CurrentStep string `json:"current_step"`
	Cue         string `json:"cue"`
	NextMove    string `json:"next_move"`
	Rescope     bool   `json:"rescope,omitempty"`
}

type ReviewInput struct {
	OpenLoops     []string
	Completed     []string
	Blocked       []string
	AvailableMins int
	Preferences   PlanningPreferences
}

type ReviewPlan struct {
	Today        []PlanningStep `json:"today"`
	Reschedule   []string       `json:"reschedule,omitempty"`
	DropOrDefer  []string       `json:"drop_or_defer,omitempty"`
	NextBestMove string         `json:"next_best_move"`
	ToneGuard    string         `json:"tone_guard"`
}

// BuildPlanningPlan turns vague intent into a small, low-overwhelm plan. It is
// intentionally heuristic: LLM calls can improve language, but the shape is stable.
func BuildPlanningPlan(req PlanningRequest) PlanningPlan {
	goal := cleanPlanningText(firstNonEmpty(req.Goal, req.Notes, "Untitled goal"))
	prefs := normalizePlanningPreferences(req.Preferences)
	seed := splitPlanningAtoms(goal + ". " + req.Notes)
	if len(seed) == 0 {
		seed = []string{goal}
	}

	limit := prefs.MaxVisibleSteps
	if limit <= 0 {
		limit = 5
	}
	if prefs.OverwhelmSensitive && limit > 4 {
		limit = 4
	}
	needsClarification := isAmbiguousPlanningText(goal)
	if needsClarification && limit > 1 {
		limit--
	}
	if len(seed) > limit {
		seed = seed[:limit]
	}

	steps := make([]PlanningStep, 0, len(seed)+1)
	if needsClarification {
		steps = append(steps, PlanningStep{
			Title:      "Clarify the exact finish line",
			Why:        "Ambiguous goals get easier once success is visible.",
			Minutes:    minNonZero(prefs.PreferredStepMins, 10),
			Energy:     "low",
			DoneSignal: "A one-sentence definition of done exists.",
		})
	}
	for i, item := range seed {
		title := actionizePlanningAtom(item)
		step := PlanningStep{
			Title:      title,
			Why:        "Moves the goal from intention into visible progress.",
			Minutes:    estimatePlanningMinutes(title, prefs),
			Energy:     estimatePlanningEnergy(title, prefs),
			DoneSignal: "This step has a visible output or decision.",
		}
		if i > 0 {
			step.DependsOn = []int{i}
		}
		steps = append(steps, step)
	}
	if len(steps) == 0 {
		steps = append(steps, PlanningStep{Title: "Start with a two-minute setup", Minutes: 2, Energy: "low", DoneSignal: "The work area or first artifact is open."})
	}

	load := ScoreCognitiveLoad(goal, steps, prefs)
	return PlanningPlan{
		Objective:        sentenceCase(goal),
		DefinitionOfDone: inferDefinitionOfDone(goal),
		Assumptions:      planningAssumptions(req),
		Steps:            steps,
		NextAction:       steps[0].Title,
		Load:             load,
		Governance: []string{
			"Keep the plan short enough to start.",
			"Treat duration estimates as adjustable guesses, not promises.",
			"Preserve user choice; do not turn suggestions into commands.",
		},
	}
}

func BuildTaskPatch(req TaskPatchRequest) TaskPatch {
	instruction := strings.ToLower(req.Instruction)
	steps := append([]PlanningStep(nil), req.CurrentSteps...)
	switch {
	case strings.Contains(instruction, "simpl") || strings.Contains(instruction, "overwhelm"):
		for i := range steps {
			if steps[i].Minutes > 20 {
				steps[i].Minutes = 15
			}
			steps[i].Energy = "low"
		}
		if len(steps) > 4 {
			steps = steps[:4]
		}
		return TaskPatch{Operation: "simplify", Reason: "Reduced visible scope and lowered energy demand.", Steps: steps}
	case strings.Contains(instruction, "split") || strings.Contains(instruction, "smaller"):
		if len(steps) == 0 {
			return TaskPatch{Operation: "noop", Reason: "No steps were available to split."}
		}
		target := steps[0]
		steps = append([]PlanningStep{
			{Title: "Open or prepare: " + strings.ToLower(target.Title), Minutes: 3, Energy: "low", DoneSignal: "The first artifact is visible."},
			{Title: target.Title, Minutes: planningMaxInt(5, target.Minutes-3), Energy: target.Energy, DoneSignal: target.DoneSignal},
		}, steps[1:]...)
		return TaskPatch{Operation: "split", Reason: "Created a lower-friction starter step.", Steps: steps}
	case strings.Contains(instruction, "tomorrow") || strings.Contains(instruction, "later") || strings.Contains(instruction, "defer"):
		return TaskPatch{Operation: "defer", Reason: "Marked the plan as safer to reschedule instead of forcing completion.", Steps: steps}
	default:
		return TaskPatch{Operation: "revise", Reason: "Apply the instruction as a bounded structured patch.", Steps: steps}
	}
}

func BuildFocusCue(steps []PlanningStep, index int, elapsed time.Duration) FocusCue {
	if len(steps) == 0 {
		return FocusCue{Cue: "Pick one tiny visible action and start there.", NextMove: "Create the first step.", Rescope: true}
	}
	if index < 0 {
		index = 0
	}
	if index >= len(steps) {
		return FocusCue{Cue: "The planned steps are complete. Pause and decide whether to stop or review.", NextMove: "Review the result."}
	}
	step := steps[index]
	rescope := step.Minutes > 0 && elapsed > time.Duration(step.Minutes+5)*time.Minute
	cue := fmt.Sprintf("Stay with one thing: %s.", step.Title)
	if rescope {
		cue = "This step is running long. Shrink it to the next visible checkpoint."
	}
	next := "Finish this step before opening the next one."
	if index+1 < len(steps) {
		next = "Next: " + steps[index+1].Title
	}
	return FocusCue{CurrentStep: step.Title, Cue: cue, NextMove: next, Rescope: rescope}
}

func BuildReviewPlan(input ReviewInput) ReviewPlan {
	prefs := normalizePlanningPreferences(input.Preferences)
	available := input.AvailableMins
	if available <= 0 {
		available = 45
	}
	open := append([]string(nil), input.OpenLoops...)
	sort.Strings(open)

	var today []PlanningStep
	used := 0
	for _, item := range open {
		mins := estimatePlanningMinutes(item, prefs)
		if used+mins > available && len(today) > 0 {
			break
		}
		today = append(today, PlanningStep{Title: actionizePlanningAtom(item), Minutes: mins, Energy: estimatePlanningEnergy(item, prefs), DoneSignal: "A visible checkpoint is complete."})
		used += mins
		if len(today) >= prefs.MaxVisibleSteps {
			break
		}
	}
	review := ReviewPlan{
		Today:        today,
		Reschedule:   append([]string(nil), input.Blocked...),
		ToneGuard:    "No shame loop: unfinished means reschedule or shrink, not personal failure.",
		NextBestMove: "Choose one small visible step.",
	}
	if len(today) > 0 {
		review.NextBestMove = today[0].Title
	}
	if len(open) > len(today) {
		review.DropOrDefer = open[len(today):]
	}
	return review
}

func ScoreCognitiveLoad(goal string, steps []PlanningStep, prefs PlanningPreferences) CognitiveLoad {
	complexity := clamp01Local(float64(len(steps)) / 8)
	ambiguity := 0.0
	if isAmbiguousPlanningText(goal) {
		ambiguity = 0.8
	}
	switching := 0.0
	for _, step := range steps {
		if containsPlanningAny(step.Title, "call", "email", "buy", "drive", "research", "code", "clean", "write") {
			switching += 0.12
		}
	}
	switching = clamp01Local(switching)
	activation := 0.2
	if prefs.OverwhelmSensitive {
		activation += 0.25
	}
	if containsPlanningAny(goal, "scary", "overwhelming", "too much", "stuck", "avoid") {
		activation += 0.35
	}
	activation = clamp01Local(activation)
	score := clamp01Local((complexity * 0.30) + (ambiguity * 0.25) + (switching * 0.20) + (activation * 0.25))

	var reasons []string
	if complexity > 0.55 {
		reasons = append(reasons, "many visible steps")
	}
	if ambiguity > 0 {
		reasons = append(reasons, "unclear finish line")
	}
	if switching > 0.35 {
		reasons = append(reasons, "multiple context switches")
	}
	if activation > 0.45 {
		reasons = append(reasons, "high activation energy")
	}
	return CognitiveLoad{
		Score:            math.Round(score*100) / 100,
		Tier:             loadTier(score),
		Complexity:       math.Round(complexity*100) / 100,
		Ambiguity:        math.Round(ambiguity*100) / 100,
		ContextSwitching: math.Round(switching*100) / 100,
		ActivationEnergy: math.Round(activation*100) / 100,
		Reasons:          reasons,
	}
}

func normalizePlanningPreferences(p PlanningPreferences) PlanningPreferences {
	if p.MaxVisibleSteps <= 0 {
		p.MaxVisibleSteps = 5
	}
	if p.MaxVisibleSteps > 8 {
		p.MaxVisibleSteps = 8
	}
	if p.PreferredStepMins <= 0 {
		p.PreferredStepMins = 15
	}
	if p.Energy == "" {
		p.Energy = "medium"
	}
	return p
}

func splitPlanningAtoms(text string) []string {
	text = strings.ReplaceAll(text, "\n", ". ")
	re := regexp.MustCompile(`[.;]|(?:\s+-\s+)`)
	parts := re.Split(text, -1)
	out := make([]string, 0, len(parts))
	for _, part := range parts {
		part = cleanPlanningText(part)
		if len(part) < 4 || containsPlanningAny(part, "untitled goal") {
			continue
		}
		out = append(out, part)
	}
	return out
}

func cleanPlanningText(s string) string {
	s = strings.Join(strings.Fields(s), " ")
	return strings.Trim(s, " \t-•")
}

func actionizePlanningAtom(atom string) string {
	atom = cleanPlanningText(atom)
	if atom == "" {
		return "Take the next visible step"
	}
	lower := strings.ToLower(atom)
	if containsPlanningAny(lower, "call ", "email ", "write ", "send ", "review ", "clean ", "buy ", "schedule ", "open ", "deploy ", "test ") {
		return sentenceCase(atom)
	}
	return "Make progress on: " + atom
}

func estimatePlanningMinutes(text string, prefs PlanningPreferences) int {
	base := prefs.PreferredStepMins
	if base <= 0 {
		base = 15
	}
	words := len(strings.Fields(text))
	switch {
	case words <= 4:
		base = minNonZero(base, 10)
	case words > 16:
		base += 10
	}
	if containsPlanningAny(text, "research", "write", "code", "build", "review") {
		base += 10
	}
	if containsPlanningAny(text, "open", "choose", "list", "draft") {
		base -= 5
	}
	if base < 2 {
		base = 2
	}
	if prefs.OverwhelmSensitive && base > 20 {
		base = 20
	}
	return base
}

func estimatePlanningEnergy(text string, prefs PlanningPreferences) string {
	lower := strings.ToLower(text)
	switch {
	case containsPlanningAny(lower, "call", "meeting", "hard", "scary", "deadline", "deploy", "presentation"):
		return "high"
	case containsPlanningAny(lower, "open", "list", "draft", "choose", "review"):
		return "low"
	case prefs.Energy != "":
		return prefs.Energy
	default:
		return "medium"
	}
}

func isAmbiguousPlanningText(text string) bool {
	lower := strings.ToLower(text)
	return containsPlanningAny(lower, "figure out", "sort out", "deal with", "handle", "fix my life", "everything", "stuff", "things")
}

func inferDefinitionOfDone(goal string) string {
	goal = cleanPlanningText(goal)
	if goal == "" {
		return "A concrete next action has been completed."
	}
	return "There is visible progress on: " + goal
}

func planningAssumptions(req PlanningRequest) []string {
	var assumptions []string
	if len(req.Constraints) == 0 {
		assumptions = append(assumptions, "No hard scheduling or resource constraints were provided.")
	}
	if req.Preferences.PreferredStepMins == 0 {
		assumptions = append(assumptions, "Step durations are rough starting estimates.")
	}
	return assumptions
}

func loadTier(score float64) string {
	switch {
	case score >= 0.68:
		return "high"
	case score >= 0.38:
		return "medium"
	default:
		return "low"
	}
}

func sentenceCase(s string) string {
	s = cleanPlanningText(s)
	if s == "" {
		return s
	}
	return strings.ToUpper(s[:1]) + s[1:]
}

func firstNonEmpty(values ...string) string {
	for _, value := range values {
		if strings.TrimSpace(value) != "" {
			return value
		}
	}
	return ""
}

func minNonZero(a, b int) int {
	if a <= 0 {
		return b
	}
	if b <= 0 || a < b {
		return a
	}
	return b
}

func planningMaxInt(a, b int) int {
	if a > b {
		return a
	}
	return b
}

func containsPlanningAny(s string, needles ...string) bool {
	lower := strings.ToLower(s)
	for _, needle := range needles {
		if strings.Contains(lower, strings.ToLower(needle)) {
			return true
		}
	}
	return false
}

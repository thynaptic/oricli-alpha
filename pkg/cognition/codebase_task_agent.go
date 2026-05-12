package cognition

import (
	"sort"
	"strings"
)

type CodebaseTaskPlanRequest struct {
	Surface      string                 `json:"surface,omitempty"`
	Intent       string                 `json:"intent,omitempty"`
	Repo         string                 `json:"repo,omitempty"`
	CurrentArea  string                 `json:"current_area,omitempty"`
	Files        []CodebaseFileSignal   `json:"files,omitempty"`
	Symbols      []CodebaseSymbolSignal `json:"symbols,omitempty"`
	Constraints  []string               `json:"constraints,omitempty"`
	KnownRisks   []string               `json:"known_risks,omitempty"`
	TestCommands []string               `json:"test_commands,omitempty"`
	Metadata     map[string]any         `json:"metadata,omitempty"`
}

type CodebaseFileSignal struct {
	Path      string   `json:"path,omitempty"`
	Role      string   `json:"role,omitempty"`
	Reason    string   `json:"reason,omitempty"`
	Status    string   `json:"status,omitempty"`
	Owners    []string `json:"owners,omitempty"`
	CanModify bool     `json:"can_modify,omitempty"`
}

type CodebaseSymbolSignal struct {
	Name string `json:"name,omitempty"`
	Kind string `json:"kind,omitempty"`
	File string `json:"file,omitempty"`
	Role string `json:"role,omitempty"`
}

type CodebaseResidentTaskPlan struct {
	ID            string                       `json:"id"`
	Surface       string                       `json:"surface"`
	Intent        string                       `json:"intent"`
	Summary       string                       `json:"summary"`
	Scope         CodebaseTaskScope            `json:"scope"`
	WorkPackets   []CodebaseWorkPacket         `json:"work_packets"`
	FileOwnership []CodebaseFileOwnership      `json:"file_ownership,omitempty"`
	Risks         []CodebaseTaskRisk           `json:"risks,omitempty"`
	Verification  []CodebaseVerificationStep   `json:"verification"`
	Delegation    CodebaseDelegationHints      `json:"delegation"`
	MemorySeeds   []QuestMemorySeed            `json:"memory_seeds,omitempty"`
	Integration   CodebaseTaskIntegrationHints `json:"integration"`
	Guardrails    []string                     `json:"guardrails"`
	OpenQuestions []string                     `json:"open_questions,omitempty"`
}

type CodebaseTaskScope struct {
	Repo          string   `json:"repo,omitempty"`
	PrimaryArea   string   `json:"primary_area,omitempty"`
	InScope       []string `json:"in_scope"`
	OutOfScope    []string `json:"out_of_scope"`
	BlastRadius   string   `json:"blast_radius"`
	NeedsReadback bool     `json:"needs_readback"`
}

type CodebaseWorkPacket struct {
	ID          string   `json:"id"`
	Title       string   `json:"title"`
	Files       []string `json:"files,omitempty"`
	Steps       []string `json:"steps"`
	DoneSignal  string   `json:"done_signal"`
	CanDelegate bool     `json:"can_delegate"`
}

type CodebaseFileOwnership struct {
	Path   string   `json:"path"`
	Role   string   `json:"role"`
	Policy string   `json:"policy"`
	Owners []string `json:"owners,omitempty"`
}

type CodebaseTaskRisk struct {
	Type       string `json:"type"`
	Title      string `json:"title"`
	Mitigation string `json:"mitigation"`
}

type CodebaseVerificationStep struct {
	Command    string `json:"command"`
	Why        string `json:"why"`
	Required   bool   `json:"required"`
	DoneSignal string `json:"done_signal"`
}

type CodebaseDelegationHints struct {
	CanParallelize    bool     `json:"can_parallelize"`
	WorkerLanes       []string `json:"worker_lanes,omitempty"`
	ExplorerQuestions []string `json:"explorer_questions,omitempty"`
	CoordinationRules []string `json:"coordination_rules"`
}

type CodebaseTaskIntegrationHints struct {
	Procedure []string `json:"procedure"`
	Temporal  []string `json:"temporal"`
	Memory    []string `json:"memory"`
	Forge     []string `json:"forge"`
	Surface   []string `json:"surface"`
}

// PlanCodebaseResidentTask turns repo-local context into a bounded execution
// plan. It does not inspect, edit, commit, or run commands by itself.
func PlanCodebaseResidentTask(req CodebaseTaskPlanRequest) CodebaseResidentTaskPlan {
	req = normalizeCodebaseTaskRequest(req)
	scope := buildCodebaseTaskScope(req)
	packets := buildCodebaseWorkPackets(req)
	risks := buildCodebaseTaskRisks(req, scope)

	return CodebaseResidentTaskPlan{
		ID:            "code_" + stableBehaviorID(firstNonEmpty(req.Intent, req.CurrentArea, req.Repo, "codebase task")),
		Surface:       normalizeQuestSurface(req.Surface),
		Intent:        sentenceCase(req.Intent),
		Summary:       summarizeCodebaseTask(req, packets, risks, scope),
		Scope:         scope,
		WorkPackets:   packets,
		FileOwnership: buildCodebaseFileOwnership(req),
		Risks:         risks,
		Verification:  buildCodebaseVerification(req),
		Delegation:    buildCodebaseDelegation(req, packets, risks),
		MemorySeeds:   codebaseTaskMemorySeeds(req, scope),
		Integration: CodebaseTaskIntegrationHints{
			Procedure: []string{"Route repeated implementation workflows into /procedure/compile after successful use."},
			Temporal:  []string{"Use /temporal/coordinate when work packets exceed the available engineering window."},
			Memory:    []string{"Remember stable repo conventions, verification commands, and ownership boundaries after confirmation."},
			Forge:     []string{"Generate helper tools only for stable, reversible, well-scoped repo operations."},
			Surface:   codebaseTaskSurfaceHints(req.Surface),
		},
		Guardrails: []string{
			"Do not claim code was read, edited, tested, committed, or deployed unless tools confirm it.",
			"Treat file ownership as a coordination proposal, not permission to overwrite user work.",
			"Keep destructive commands, secrets, and broad refactors behind explicit approval.",
		},
		OpenQuestions: codebaseTaskOpenQuestions(req, scope),
	}
}

func normalizeCodebaseTaskRequest(req CodebaseTaskPlanRequest) CodebaseTaskPlanRequest {
	req.Surface = normalizeQuestSurface(req.Surface)
	req.Intent = cleanPlanningText(firstNonEmpty(req.Intent, "Plan the codebase task"))
	req.Repo = cleanPlanningText(req.Repo)
	req.CurrentArea = cleanPlanningText(req.CurrentArea)
	req.Constraints = uniqueCodebaseStrings(req.Constraints)
	req.KnownRisks = uniqueCodebaseStrings(req.KnownRisks)
	req.TestCommands = uniqueCodebaseStrings(req.TestCommands)
	for i := range req.Files {
		req.Files[i].Path = cleanPlanningText(req.Files[i].Path)
		req.Files[i].Role = strings.ToLower(strings.TrimSpace(req.Files[i].Role))
		req.Files[i].Reason = cleanPlanningText(req.Files[i].Reason)
		req.Files[i].Status = strings.ToLower(strings.TrimSpace(req.Files[i].Status))
		req.Files[i].Owners = uniqueCodebaseStrings(req.Files[i].Owners)
	}
	for i := range req.Symbols {
		req.Symbols[i].Name = cleanPlanningText(req.Symbols[i].Name)
		req.Symbols[i].Kind = strings.ToLower(strings.TrimSpace(req.Symbols[i].Kind))
		req.Symbols[i].File = cleanPlanningText(req.Symbols[i].File)
		req.Symbols[i].Role = cleanPlanningText(req.Symbols[i].Role)
	}
	return req
}

func buildCodebaseTaskScope(req CodebaseTaskPlanRequest) CodebaseTaskScope {
	inScope := []string{}
	outScope := []string{"unrelated refactors", "unrequested formatting churn", "destructive git operations"}
	for _, file := range req.Files {
		if file.Path == "" {
			continue
		}
		if file.Role == "out_of_scope" || file.Status == "do_not_modify" {
			outScope = append(outScope, file.Path)
			continue
		}
		inScope = append(inScope, file.Path)
	}
	if len(inScope) == 0 && req.CurrentArea != "" {
		inScope = append(inScope, req.CurrentArea)
	}
	if len(inScope) == 0 {
		inScope = append(inScope, "read the relevant files before planning edits")
	}
	return CodebaseTaskScope{
		Repo:          req.Repo,
		PrimaryArea:   firstNonEmpty(req.CurrentArea, inferCodebasePrimaryArea(req)),
		InScope:       uniqueCodebaseStrings(inScope),
		OutOfScope:    uniqueCodebaseStrings(outScope),
		BlastRadius:   inferCodebaseBlastRadius(req),
		NeedsReadback: len(req.Files) == 0 && len(req.Symbols) == 0,
	}
}

func buildCodebaseWorkPackets(req CodebaseTaskPlanRequest) []CodebaseWorkPacket {
	filesByRole := map[string][]string{}
	for _, file := range req.Files {
		if file.Path == "" || file.Role == "out_of_scope" || file.Status == "do_not_modify" {
			continue
		}
		role := firstNonEmpty(file.Role, "implementation")
		filesByRole[role] = append(filesByRole[role], file.Path)
	}
	var packets []CodebaseWorkPacket
	for role, files := range filesByRole {
		title := sentenceCase(role + " work for " + firstNonEmpty(req.CurrentArea, req.Intent))
		packets = append(packets, CodebaseWorkPacket{
			ID:          "wp_" + stableBehaviorID(role+"_"+strings.Join(files, "_")),
			Title:       title,
			Files:       uniqueCodebaseStrings(files),
			Steps:       codebaseStepsForRole(role),
			DoneSignal:  codebaseDoneSignalForRole(role),
			CanDelegate: codebaseRoleCanDelegate(role, files),
		})
	}
	if len(packets) == 0 {
		packets = append(packets, CodebaseWorkPacket{
			ID:          "wp_readback",
			Title:       "Read back the codebase context",
			Steps:       []string{"Identify relevant files", "Map current behavior", "Name the smallest safe edit path"},
			DoneSignal:  "The task has concrete file scope and verification commands.",
			CanDelegate: false,
		})
	}
	sort.SliceStable(packets, func(i, j int) bool { return packets[i].ID < packets[j].ID })
	return packets
}

func buildCodebaseFileOwnership(req CodebaseTaskPlanRequest) []CodebaseFileOwnership {
	var out []CodebaseFileOwnership
	for _, file := range req.Files {
		if file.Path == "" {
			continue
		}
		policy := "read before editing; preserve unrelated user changes"
		if !file.CanModify || file.Status == "do_not_modify" {
			policy = "read-only unless explicitly approved"
		}
		out = append(out, CodebaseFileOwnership{
			Path:   file.Path,
			Role:   firstNonEmpty(file.Role, "context"),
			Policy: policy,
			Owners: file.Owners,
		})
	}
	return out
}

func buildCodebaseTaskRisks(req CodebaseTaskPlanRequest, scope CodebaseTaskScope) []CodebaseTaskRisk {
	var risks []CodebaseTaskRisk
	for _, known := range req.KnownRisks {
		risks = append(risks, CodebaseTaskRisk{Type: "known", Title: known, Mitigation: "Verify before changing shared behavior."})
	}
	lower := strings.ToLower(req.Intent + " " + strings.Join(req.Constraints, " "))
	if containsPlanningAny(lower, "auth", "payment", "security", "permission", "secret") {
		risks = append(risks, CodebaseTaskRisk{Type: "boundary", Title: "Sensitive system boundary", Mitigation: "Add targeted tests and require explicit approval for external effects."})
	}
	if scope.BlastRadius == "broad" {
		risks = append(risks, CodebaseTaskRisk{Type: "blast_radius", Title: "Broad codebase surface", Mitigation: "Split into smaller lanes and verify each contract boundary."})
	}
	if scope.NeedsReadback {
		risks = append(risks, CodebaseTaskRisk{Type: "unknown_scope", Title: "File scope not established", Mitigation: "Read relevant code before committing to edits."})
	}
	if len(risks) > 6 {
		return risks[:6]
	}
	return risks
}

func buildCodebaseVerification(req CodebaseTaskPlanRequest) []CodebaseVerificationStep {
	commands := req.TestCommands
	if len(commands) == 0 {
		commands = []string{"run the narrowest relevant test/build command"}
	}
	var out []CodebaseVerificationStep
	for _, cmd := range commands {
		out = append(out, CodebaseVerificationStep{
			Command:    cmd,
			Why:        "Proves the planned edit did not break the touched contract.",
			Required:   true,
			DoneSignal: "Command passes or failure is explained with next action.",
		})
	}
	return out
}

func buildCodebaseDelegation(req CodebaseTaskPlanRequest, packets []CodebaseWorkPacket, risks []CodebaseTaskRisk) CodebaseDelegationHints {
	var lanes []string
	for _, packet := range packets {
		if packet.CanDelegate {
			lanes = append(lanes, packet.Title)
		}
	}
	canParallel := len(lanes) > 1 && len(risks) <= 2
	return CodebaseDelegationHints{
		CanParallelize: canParallel,
		WorkerLanes:    lanes,
		ExplorerQuestions: []string{
			"Which files own the current behavior?",
			"What tests already cover the contract?",
			"Where are the side-effect boundaries?",
		},
		CoordinationRules: []string{
			"Assign disjoint write scopes before parallel work.",
			"Workers must preserve edits they did not make.",
			"Do not hand off the immediate blocker if the next local step depends on it.",
		},
	}
}

func summarizeCodebaseTask(req CodebaseTaskPlanRequest, packets []CodebaseWorkPacket, risks []CodebaseTaskRisk, scope CodebaseTaskScope) string {
	return sentenceCase(req.Intent) + " is scoped to " + scope.BlastRadius + " codebase impact with " +
		intToMomentumString(len(packets)) + " work packets and " +
		intToMomentumString(len(risks)) + " risks."
}

func codebaseTaskMemorySeeds(req CodebaseTaskPlanRequest, scope CodebaseTaskScope) []QuestMemorySeed {
	seeds := []QuestMemorySeed{
		{Key: "codebase_task_intent", Value: req.Intent, Importance: 0.62},
		{Key: "codebase_blast_radius", Value: scope.BlastRadius, Importance: 0.54},
	}
	if scope.PrimaryArea != "" {
		seeds = append(seeds, QuestMemorySeed{Key: "codebase_primary_area", Value: scope.PrimaryArea, Importance: 0.58})
	}
	if len(req.TestCommands) > 0 {
		seeds = append(seeds, QuestMemorySeed{Key: "codebase_verification_command", Value: req.TestCommands[0], Importance: 0.66})
	}
	return seeds
}

func inferCodebasePrimaryArea(req CodebaseTaskPlanRequest) string {
	for _, file := range req.Files {
		if file.Path == "" {
			continue
		}
		parts := strings.Split(file.Path, "/")
		if len(parts) >= 2 {
			return strings.Join(parts[:2], "/")
		}
		return file.Path
	}
	return ""
}

func inferCodebaseBlastRadius(req CodebaseTaskPlanRequest) string {
	if len(req.Files) == 0 {
		return "unknown"
	}
	areas := map[string]bool{}
	for _, file := range req.Files {
		area := file.Path
		if idx := strings.Index(area, "/"); idx > 0 {
			area = area[:idx]
		}
		areas[area] = true
	}
	switch {
	case len(areas) >= 4:
		return "broad"
	case len(req.Files) >= 4:
		return "moderate"
	default:
		return "narrow"
	}
}

func codebaseStepsForRole(role string) []string {
	switch role {
	case "test", "tests":
		return []string{"Locate existing coverage", "Add or adjust focused tests", "Run narrow verification"}
	case "docs", "documentation":
		return []string{"Confirm runtime behavior", "Update public contract language", "Validate generated manifest if applicable"}
	case "api", "handler":
		return []string{"Confirm request/response contract", "Implement handler with existing auth/surface patterns", "Add endpoint test"}
	default:
		return []string{"Read current implementation", "Make smallest behavior-preserving edit", "Run focused verification"}
	}
}

func codebaseDoneSignalForRole(role string) string {
	switch role {
	case "test", "tests":
		return "Focused tests fail before the fix or cover the new behavior and pass after it."
	case "docs", "documentation":
		return "Docs match runtime behavior and machine-readable manifests validate."
	case "api", "handler":
		return "Endpoint behavior is covered by a handler test and smokeable request shape."
	default:
		return "The intended behavior works and focused verification passes."
	}
}

func codebaseRoleCanDelegate(role string, files []string) bool {
	return len(files) > 0 && role != "architecture" && role != "security"
}

func codebaseTaskOpenQuestions(req CodebaseTaskPlanRequest, scope CodebaseTaskScope) []string {
	var qs []string
	if scope.NeedsReadback {
		qs = append(qs, "Which files own the behavior?")
	}
	if len(req.TestCommands) == 0 {
		qs = append(qs, "What is the narrowest verification command?")
	}
	if len(req.Constraints) == 0 {
		qs = append(qs, "What should stay explicitly out of scope?")
	}
	return qs
}

func codebaseTaskSurfaceHints(surface string) []string {
	switch normalizeQuestSurface(surface) {
	case "dev":
		return []string{"Show file scope, verification commands, risk boundaries, and delegation lanes first."}
	case "studio":
		return []string{"Translate implementation packets into operator-visible outcomes and rollout risk."}
	default:
		return []string{"Keep the plan technical but do not imply code changes happened."}
	}
}

func uniqueCodebaseStrings(values []string) []string {
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

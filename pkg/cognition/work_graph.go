package cognition

import (
	"sort"
	"strings"
)

type WorkGraphCompileRequest struct {
	Surface       string                `json:"surface,omitempty"`
	Workspace     string                `json:"workspace,omitempty"`
	Intent        string                `json:"intent,omitempty"`
	Notes         string                `json:"notes,omitempty"`
	Conversations []ConversationMessage `json:"conversations,omitempty"`
	Items         []WorkGraphInputItem  `json:"items,omitempty"`
	Metadata      map[string]any        `json:"metadata,omitempty"`
}

type WorkGraphInputItem struct {
	ID      string   `json:"id,omitempty"`
	Kind    string   `json:"kind,omitempty"`
	Title   string   `json:"title,omitempty"`
	Content string   `json:"content,omitempty"`
	Owner   string   `json:"owner,omitempty"`
	DueHint string   `json:"due_hint,omitempty"`
	Status  string   `json:"status,omitempty"`
	Source  string   `json:"source,omitempty"`
	Tags    []string `json:"tags,omitempty"`
}

type WorkGraph struct {
	ID            string                    `json:"id"`
	Surface       string                    `json:"surface"`
	Workspace     string                    `json:"workspace,omitempty"`
	Summary       string                    `json:"summary"`
	Objects       WorkGraphObjects          `json:"objects"`
	Edges         []WorkGraphEdge           `json:"edges,omitempty"`
	Pulse         WorkGraphPulse            `json:"pulse"`
	MemorySeeds   []QuestMemorySeed         `json:"memory_seeds,omitempty"`
	Integration   WorkGraphIntegrationHints `json:"integration"`
	Guardrails    []string                  `json:"guardrails"`
	OpenQuestions []string                  `json:"open_questions,omitempty"`
}

type WorkGraphObjects struct {
	Jobs      []WorkGraphObject `json:"jobs,omitempty"`
	Tasks     []WorkGraphObject `json:"tasks,omitempty"`
	Decisions []WorkGraphObject `json:"decisions,omitempty"`
	Owners    []WorkGraphObject `json:"owners,omitempty"`
	Deadlines []WorkGraphObject `json:"deadlines,omitempty"`
	Blockers  []WorkGraphObject `json:"blockers,omitempty"`
	Approvals []WorkGraphObject `json:"approvals,omitempty"`
	Notes     []WorkGraphObject `json:"notes,omitempty"`
	FollowUps []WorkGraphObject `json:"follow_ups,omitempty"`
	Metrics   []WorkGraphObject `json:"metrics,omitempty"`
}

type WorkGraphObject struct {
	ID         string   `json:"id"`
	Type       string   `json:"type"`
	Title      string   `json:"title"`
	Content    string   `json:"content,omitempty"`
	Owner      string   `json:"owner,omitempty"`
	DueHint    string   `json:"due_hint,omitempty"`
	Status     string   `json:"status,omitempty"`
	Source     string   `json:"source,omitempty"`
	Confidence float64  `json:"confidence"`
	Tags       []string `json:"tags,omitempty"`
}

type WorkGraphEdge struct {
	From   string `json:"from"`
	To     string `json:"to"`
	Kind   string `json:"kind"`
	Reason string `json:"reason,omitempty"`
}

type WorkGraphPulse struct {
	Stuck         []string `json:"stuck,omitempty"`
	Promised      []string `json:"promised,omitempty"`
	NeedsApproval []string `json:"needs_approval,omitempty"`
	Unowned       []string `json:"unowned,omitempty"`
	HandleFirst   string   `json:"handle_first,omitempty"`
	Health        string   `json:"health"`
}

type WorkGraphIntegrationHints struct {
	Continuity   []string `json:"continuity"`
	Execution    []string `json:"execution"`
	Conversation []string `json:"conversation"`
	Temporal     []string `json:"temporal"`
	Procedure    []string `json:"procedure"`
	Memory       []string `json:"memory"`
	Surface      []string `json:"surface"`
}

type WorkGraphAnswerRequest struct {
	Surface  string           `json:"surface,omitempty"`
	Question string           `json:"question,omitempty"`
	Graph    WorkGraph        `json:"graph,omitempty"`
	Objects  WorkGraphObjects `json:"objects,omitempty"`
	Metadata map[string]any   `json:"metadata,omitempty"`
}

type WorkGraphAnswer struct {
	Surface     string                     `json:"surface"`
	Question    string                     `json:"question"`
	Answer      string                     `json:"answer"`
	Findings    []WorkGraphFinding         `json:"findings,omitempty"`
	Recommended []AnticipationNextMove     `json:"recommended,omitempty"`
	Confidence  float64                    `json:"confidence"`
	Integration WorkGraphAnswerIntegration `json:"integration"`
	Guardrails  []string                   `json:"guardrails"`
}

type WorkGraphFinding struct {
	ID      string `json:"id"`
	Type    string `json:"type"`
	Title   string `json:"title"`
	Reason  string `json:"reason"`
	Owner   string `json:"owner,omitempty"`
	DueHint string `json:"due_hint,omitempty"`
}

type WorkGraphAnswerIntegration struct {
	Execution  []string `json:"execution"`
	Continuity []string `json:"continuity"`
	Memory     []string `json:"memory"`
	Surface    []string `json:"surface"`
}

// CompileWorkGraph converts messy work context into typed work-state objects.
// It does not persist, assign, notify, or modify any external workspace.
func CompileWorkGraph(req WorkGraphCompileRequest) WorkGraph {
	req = normalizeWorkGraphRequest(req)
	objects := buildWorkGraphObjects(req)
	edges := buildWorkGraphEdges(objects)
	pulse := buildWorkGraphPulse(objects)
	workspace := firstNonEmpty(req.Workspace, "work graph")

	return WorkGraph{
		ID:          "wg_" + stableBehaviorID(workspace+"_"+firstNonEmpty(req.Intent, req.Notes)),
		Surface:     normalizeQuestSurface(req.Surface),
		Workspace:   req.Workspace,
		Summary:     summarizeWorkGraph(req, objects, pulse),
		Objects:     objects,
		Edges:       edges,
		Pulse:       pulse,
		MemorySeeds: workGraphMemorySeeds(req, pulse),
		Integration: WorkGraphIntegrationHints{
			Continuity:   []string{"Use /continuity/recover to create compact restart points from this graph."},
			Execution:    []string{"Use /execution/orchestrate to choose next moves from jobs, blockers, approvals, and follow-ups."},
			Conversation: []string{"Feed meeting/chat sources through /conversation/harvest before compiling durable work objects."},
			Temporal:     []string{"Feed deadlines and follow-ups into /temporal/coordinate when scheduling is requested."},
			Procedure:    []string{"Route repeated work patterns into /procedure/compile before automation."},
			Memory:       []string{"Persist source-backed objects only after client confirmation and tenant-scoped storage policy."},
			Surface:      workGraphSurfaceHints(req.Surface),
		},
		Guardrails: []string{
			"Do not claim jobs, tasks, docs, reminders, dashboards, or external workspaces were created unless a tool confirms it.",
			"Treat inferred owners, deadlines, and approvals as candidates until confirmed.",
			"Keep the graph as cognitive substrate; product clients own UI, storage, notifications, and permissions.",
		},
		OpenQuestions: workGraphOpenQuestions(objects),
	}
}

// AnswerWorkGraphQuestion gives operator-style answers over supplied graph state.
func AnswerWorkGraphQuestion(req WorkGraphAnswerRequest) WorkGraphAnswer {
	req = normalizeWorkGraphAnswerRequest(req)
	objects := req.Graph.Objects
	if isEmptyWorkGraphObjects(objects) {
		objects = req.Objects
	}
	findings := workGraphFindingsForQuestion(req.Question, objects)
	answer := summarizeWorkGraphAnswer(req.Question, findings)
	return WorkGraphAnswer{
		Surface:     normalizeQuestSurface(req.Surface),
		Question:    req.Question,
		Answer:      answer,
		Findings:    findings,
		Recommended: workGraphRecommendedMoves(findings),
		Confidence:  workGraphAnswerConfidence(findings),
		Integration: WorkGraphAnswerIntegration{
			Execution:  []string{"Pass recommended moves to /execution/orchestrate before changing task state."},
			Continuity: []string{"Attach answer findings to /continuity/recover when resuming a workspace thread."},
			Memory:     []string{"Save answer-derived state only when findings are source-backed and confirmed."},
			Surface:    workGraphSurfaceHints(req.Surface),
		},
		Guardrails: []string{
			"Answer only from supplied graph state; do not imply live workspace search happened.",
			"Do not mutate tasks, owners, approvals, reminders, or dashboards from an answer.",
		},
	}
}

func normalizeWorkGraphRequest(req WorkGraphCompileRequest) WorkGraphCompileRequest {
	req.Surface = normalizeQuestSurface(req.Surface)
	req.Workspace = cleanPlanningText(req.Workspace)
	req.Intent = cleanPlanningText(req.Intent)
	req.Notes = cleanPlanningText(req.Notes)
	for i := range req.Items {
		req.Items[i].ID = cleanPlanningText(req.Items[i].ID)
		req.Items[i].Kind = strings.ToLower(strings.TrimSpace(req.Items[i].Kind))
		req.Items[i].Title = cleanPlanningText(firstNonEmpty(req.Items[i].Title, req.Items[i].Content, "work item"))
		req.Items[i].Content = cleanPlanningText(req.Items[i].Content)
		req.Items[i].Owner = cleanPlanningText(req.Items[i].Owner)
		req.Items[i].DueHint = cleanPlanningText(req.Items[i].DueHint)
		req.Items[i].Status = strings.ToLower(strings.TrimSpace(req.Items[i].Status))
		req.Items[i].Source = cleanPlanningText(req.Items[i].Source)
	}
	for i := range req.Conversations {
		req.Conversations[i].Speaker = cleanPlanningText(req.Conversations[i].Speaker)
		req.Conversations[i].Text = cleanPlanningText(req.Conversations[i].Text)
	}
	if len(req.Items) == 0 && req.Notes != "" {
		for _, atom := range splitPlanningAtoms(req.Notes) {
			req.Items = append(req.Items, WorkGraphInputItem{Title: atom, Content: atom, Kind: "note"})
		}
	}
	if len(req.Items) == 0 && len(req.Conversations) == 0 {
		req.Items = []WorkGraphInputItem{{Kind: "note", Title: firstNonEmpty(req.Intent, "Clarify the work graph")}}
	}
	return req
}

func buildWorkGraphObjects(req WorkGraphCompileRequest) WorkGraphObjects {
	var out WorkGraphObjects
	for _, item := range req.Items {
		obj := workGraphObjectFromItem(item)
		addWorkGraphObject(&out, obj)
		if item.Owner != "" {
			addWorkGraphObject(&out, WorkGraphObject{ID: "owner_" + stableBehaviorID(item.Owner), Type: "owner", Title: item.Owner, Confidence: 0.82})
		}
		if item.DueHint != "" {
			addWorkGraphObject(&out, WorkGraphObject{ID: "deadline_" + stableBehaviorID(item.Title+"_"+item.DueHint), Type: "deadline", Title: item.DueHint, Content: item.Title, Confidence: 0.72})
		}
	}
	for _, msg := range req.Conversations {
		item := WorkGraphInputItem{Title: msg.Text, Content: msg.Text, Owner: msg.Speaker, Kind: inferWorkGraphKind(msg.Text), Source: "conversation"}
		addWorkGraphObject(&out, workGraphObjectFromItem(item))
	}
	sortWorkGraphObjects(&out)
	return out
}

func workGraphObjectFromItem(item WorkGraphInputItem) WorkGraphObject {
	kind := firstNonEmpty(item.Kind, inferWorkGraphKind(item.Title+" "+item.Content))
	title := item.Title
	return WorkGraphObject{
		ID:         firstNonEmpty(item.ID, kind+"_"+stableBehaviorID(title)),
		Type:       kind,
		Title:      sentenceCase(title),
		Content:    item.Content,
		Owner:      item.Owner,
		DueHint:    item.DueHint,
		Status:     item.Status,
		Source:     item.Source,
		Confidence: workGraphObjectConfidence(item, kind),
		Tags:       item.Tags,
	}
}

func inferWorkGraphKind(text string) string {
	lower := strings.ToLower(text)
	switch {
	case containsPlanningAny(lower, "approval", "approve", "sign off"):
		return "approval"
	case containsPlanningAny(lower, "blocked", "waiting", "stuck", "dependency"):
		return "blocker"
	case containsPlanningAny(lower, "follow up", "reply", "send", "email", "call"):
		return "follow_up"
	case containsPlanningAny(lower, "decided", "decision", "agreed"):
		return "decision"
	case containsPlanningAny(lower, "deadline", "due", "by friday", "tomorrow", "today"):
		return "deadline"
	case containsPlanningAny(lower, "metric", "kpi", "revenue", "latency", "score"):
		return "metric"
	case containsPlanningAny(lower, "job", "project", "campaign", "client"):
		return "job"
	case containsPlanningAny(lower, "task", "todo", "fix", "draft", "create", "update"):
		return "task"
	default:
		return "note"
	}
}

func addWorkGraphObject(out *WorkGraphObjects, obj WorkGraphObject) {
	switch obj.Type {
	case "job":
		out.Jobs = append(out.Jobs, obj)
	case "task":
		out.Tasks = append(out.Tasks, obj)
	case "decision":
		out.Decisions = append(out.Decisions, obj)
	case "owner":
		out.Owners = append(out.Owners, obj)
	case "deadline":
		out.Deadlines = append(out.Deadlines, obj)
	case "blocker":
		out.Blockers = append(out.Blockers, obj)
	case "approval":
		out.Approvals = append(out.Approvals, obj)
	case "follow_up":
		out.FollowUps = append(out.FollowUps, obj)
	case "metric":
		out.Metrics = append(out.Metrics, obj)
	default:
		obj.Type = "note"
		out.Notes = append(out.Notes, obj)
	}
}

func buildWorkGraphEdges(objects WorkGraphObjects) []WorkGraphEdge {
	var edges []WorkGraphEdge
	for _, task := range objects.Tasks {
		if task.Owner != "" {
			edges = append(edges, WorkGraphEdge{From: task.ID, To: "owner_" + stableBehaviorID(task.Owner), Kind: "owned_by", Reason: "Task names an owner."})
		}
		for _, blocker := range objects.Blockers {
			if relatedWorkGraphObjects(task, blocker) {
				edges = append(edges, WorkGraphEdge{From: blocker.ID, To: task.ID, Kind: "blocks", Reason: "Blocker and task share context."})
			}
		}
	}
	for _, approval := range objects.Approvals {
		for _, job := range objects.Jobs {
			if relatedWorkGraphObjects(approval, job) {
				edges = append(edges, WorkGraphEdge{From: approval.ID, To: job.ID, Kind: "gates", Reason: "Approval appears to gate job progress."})
			}
		}
	}
	if len(edges) > 12 {
		return edges[:12]
	}
	return edges
}

func buildWorkGraphPulse(objects WorkGraphObjects) WorkGraphPulse {
	pulse := WorkGraphPulse{Health: "clear"}
	for _, blocker := range objects.Blockers {
		pulse.Stuck = append(pulse.Stuck, blocker.Title)
	}
	for _, follow := range objects.FollowUps {
		pulse.Promised = append(pulse.Promised, follow.Title)
	}
	for _, approval := range objects.Approvals {
		pulse.NeedsApproval = append(pulse.NeedsApproval, approval.Title)
	}
	for _, task := range append(objects.Tasks, objects.Jobs...) {
		if task.Owner == "" {
			pulse.Unowned = append(pulse.Unowned, task.Title)
		}
	}
	pulse.HandleFirst = firstNonEmpty(firstWorkGraphString(pulse.Stuck), firstWorkGraphString(pulse.NeedsApproval), firstWorkGraphString(pulse.Promised), firstWorkGraphString(pulse.Unowned))
	switch {
	case len(pulse.Stuck)+len(pulse.NeedsApproval) >= 3:
		pulse.Health = "congested"
	case len(pulse.Stuck)+len(pulse.NeedsApproval) > 0:
		pulse.Health = "needs_attention"
	}
	return pulse
}

func normalizeWorkGraphAnswerRequest(req WorkGraphAnswerRequest) WorkGraphAnswerRequest {
	req.Surface = normalizeQuestSurface(req.Surface)
	req.Question = cleanPlanningText(firstNonEmpty(req.Question, "What needs attention?"))
	return req
}

func workGraphFindingsForQuestion(question string, objects WorkGraphObjects) []WorkGraphFinding {
	lower := strings.ToLower(question)
	var findings []WorkGraphFinding
	add := func(obj WorkGraphObject, reason string) {
		findings = append(findings, WorkGraphFinding{ID: obj.ID, Type: obj.Type, Title: obj.Title, Reason: reason, Owner: obj.Owner, DueHint: obj.DueHint})
	}
	switch {
	case containsPlanningAny(lower, "stuck", "blocked"):
		for _, obj := range objects.Blockers {
			add(obj, "Marked or inferred as blocked.")
		}
	case containsPlanningAny(lower, "promise", "follow", "owe"):
		for _, obj := range objects.FollowUps {
			add(obj, "Follow-up or commitment-like item.")
		}
	case containsPlanningAny(lower, "approval", "approve"):
		for _, obj := range objects.Approvals {
			add(obj, "Approval gate is present.")
		}
	case containsPlanningAny(lower, "first", "next", "priority"):
		for _, obj := range objects.Blockers {
			add(obj, "Blocker should be cleared before more task churn.")
		}
		for _, obj := range objects.Approvals {
			add(obj, "Approval gate may unlock work.")
		}
		for _, obj := range objects.FollowUps {
			add(obj, "Follow-up can create visible progress.")
		}
	default:
		for _, obj := range objects.Blockers {
			add(obj, "Needs attention.")
		}
		for _, obj := range objects.Approvals {
			add(obj, "Needs decision.")
		}
		for _, obj := range objects.FollowUps {
			add(obj, "Needs follow-through.")
		}
	}
	if len(findings) > 8 {
		return findings[:8]
	}
	return findings
}

func summarizeWorkGraphAnswer(question string, findings []WorkGraphFinding) string {
	if len(findings) == 0 {
		return "No matching work-graph signals were supplied for: " + question
	}
	return "Found " + intToMomentumString(len(findings)) + " relevant work-graph signals for: " + question
}

func workGraphRecommendedMoves(findings []WorkGraphFinding) []AnticipationNextMove {
	var moves []AnticipationNextMove
	for _, finding := range findings {
		moves = append(moves, AnticipationNextMove{
			Title:       "Handle: " + finding.Title,
			Minutes:     10,
			Autonomy:    "suggest",
			DoneSignal:  "The item has an owner, answer, next action, or explicit defer.",
			NeedsPermit: false,
		})
		if len(moves) == 4 {
			break
		}
	}
	return moves
}

func summarizeWorkGraph(req WorkGraphCompileRequest, objects WorkGraphObjects, pulse WorkGraphPulse) string {
	count := len(objects.Jobs) + len(objects.Tasks) + len(objects.Decisions) + len(objects.Blockers) + len(objects.Approvals) + len(objects.FollowUps) + len(objects.Notes)
	return sentenceCase(firstNonEmpty(req.Workspace, req.Intent, "work graph")) + " compiled " + intToMomentumString(count) + " work objects with " + pulse.Health + " health."
}

func workGraphMemorySeeds(req WorkGraphCompileRequest, pulse WorkGraphPulse) []QuestMemorySeed {
	seeds := []QuestMemorySeed{{Key: "work_graph_workspace", Value: firstNonEmpty(req.Workspace, req.Intent, "work graph"), Importance: 0.64}}
	if pulse.HandleFirst != "" {
		seeds = append(seeds, QuestMemorySeed{Key: "work_graph_handle_first", Value: pulse.HandleFirst, Importance: 0.74})
	}
	return seeds
}

func workGraphObjectConfidence(item WorkGraphInputItem, kind string) float64 {
	score := 0.52
	if item.Kind != "" {
		score += 0.12
	}
	if item.Owner != "" {
		score += 0.08
	}
	if item.DueHint != "" {
		score += 0.06
	}
	if kind == "note" {
		score -= 0.04
	}
	if score > 0.86 {
		return 0.86
	}
	return score
}

func relatedWorkGraphObjects(a, b WorkGraphObject) bool {
	joined := strings.ToLower(a.Title + " " + a.Content + " " + b.Title + " " + b.Content)
	for _, word := range strings.Fields(strings.ToLower(a.Title)) {
		if len(word) > 4 && strings.Contains(joined, word) {
			return true
		}
	}
	return false
}

func workGraphAnswerConfidence(findings []WorkGraphFinding) float64 {
	if len(findings) == 0 {
		return 0.32
	}
	score := 0.54 + float64(len(findings))*0.04
	if score > 0.82 {
		return 0.82
	}
	return score
}

func isEmptyWorkGraphObjects(objects WorkGraphObjects) bool {
	return len(objects.Jobs)+len(objects.Tasks)+len(objects.Decisions)+len(objects.Owners)+len(objects.Deadlines)+len(objects.Blockers)+len(objects.Approvals)+len(objects.Notes)+len(objects.FollowUps)+len(objects.Metrics) == 0
}

func firstWorkGraphString(values []string) string {
	if len(values) == 0 {
		return ""
	}
	return values[0]
}

func sortWorkGraphObjects(objects *WorkGraphObjects) {
	sortObjs := func(values []WorkGraphObject) {
		sort.SliceStable(values, func(i, j int) bool { return values[i].ID < values[j].ID })
	}
	sortObjs(objects.Jobs)
	sortObjs(objects.Tasks)
	sortObjs(objects.Decisions)
	sortObjs(objects.Owners)
	sortObjs(objects.Deadlines)
	sortObjs(objects.Blockers)
	sortObjs(objects.Approvals)
	sortObjs(objects.Notes)
	sortObjs(objects.FollowUps)
	sortObjs(objects.Metrics)
}

func workGraphSurfaceHints(surface string) []string {
	switch normalizeQuestSurface(surface) {
	case "studio":
		return []string{"Show jobs, blockers, approvals, owners, and follow-ups as operator state, not project-management setup."}
	case "dev":
		return []string{"Show repo work, blockers, review gates, owners, and verification state."}
	case "home":
		return []string{"Show household jobs, owners, deadlines, and one next follow-through item."}
	default:
		return []string{"Keep graph language app-neutral and substrate-oriented."}
	}
}

func workGraphOpenQuestions(objects WorkGraphObjects) []string {
	var qs []string
	if len(objects.Owners) == 0 {
		qs = append(qs, "Who owns the active work?")
	}
	if len(objects.Deadlines) == 0 {
		qs = append(qs, "Are there any real deadlines or review windows?")
	}
	if len(objects.Blockers) == 0 && len(objects.Approvals) == 0 {
		qs = append(qs, "What is currently blocked or waiting for approval?")
	}
	return qs
}

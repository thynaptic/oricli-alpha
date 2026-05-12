package cognition

import (
	"sort"
	"strings"
)

type ContinuityRecoverRequest struct {
	Surface          string               `json:"surface,omitempty"`
	Intent           string               `json:"intent,omitempty"`
	CurrentQuery     string               `json:"current_query,omitempty"`
	Project          string               `json:"project,omitempty"`
	PreviousSessions []ContinuitySession  `json:"previous_sessions,omitempty"`
	Artifacts        []ContinuityArtifact `json:"artifacts,omitempty"`
	Decisions        []string             `json:"decisions,omitempty"`
	Commitments      []string             `json:"commitments,omitempty"`
	OpenLoops        []string             `json:"open_loops,omitempty"`
	Metadata         map[string]any       `json:"metadata,omitempty"`
}

type ContinuitySession struct {
	ID        string   `json:"id,omitempty"`
	Title     string   `json:"title,omitempty"`
	Summary   string   `json:"summary,omitempty"`
	Outcome   string   `json:"outcome,omitempty"`
	UpdatedAt string   `json:"updated_at,omitempty"`
	Tags      []string `json:"tags,omitempty"`
}

type ContinuityArtifact struct {
	ID      string `json:"id,omitempty"`
	Title   string `json:"title,omitempty"`
	Kind    string `json:"kind,omitempty"`
	Source  string `json:"source,omitempty"`
	Summary string `json:"summary,omitempty"`
	Status  string `json:"status,omitempty"`
}

type ContinuityRecoveryPlan struct {
	ID                    string                     `json:"id"`
	Surface               string                     `json:"surface"`
	Project               string                     `json:"project,omitempty"`
	Summary               string                     `json:"summary"`
	RecoveredThread       ContinuityThread           `json:"recovered_thread"`
	ContextPackets        []ContinuityContextPacket  `json:"context_packets,omitempty"`
	DecisionLog           []ContinuityDecision       `json:"decision_log,omitempty"`
	CommitmentLog         []ContinuityCommitment     `json:"commitment_log,omitempty"`
	OpenLoops             []ContinuityOpenLoop       `json:"open_loops,omitempty"`
	SuggestedContinuation ContinuityContinuation     `json:"suggested_continuation"`
	MemorySeeds           []QuestMemorySeed          `json:"memory_seeds,omitempty"`
	Integration           ContinuityIntegrationHints `json:"integration"`
	Guardrails            []string                   `json:"guardrails"`
	OpenQuestions         []string                   `json:"open_questions,omitempty"`
}

type ContinuityThread struct {
	Title        string   `json:"title"`
	LastKnown    string   `json:"last_known"`
	WhyItMatters string   `json:"why_it_matters"`
	SourceIDs    []string `json:"source_ids,omitempty"`
	Confidence   float64  `json:"confidence"`
}

type ContinuityContextPacket struct {
	ID         string   `json:"id"`
	Title      string   `json:"title"`
	Kind       string   `json:"kind"`
	Why        string   `json:"why"`
	Source     string   `json:"source,omitempty"`
	NextUse    string   `json:"next_use"`
	Evidence   []string `json:"evidence,omitempty"`
	DoneSignal string   `json:"done_signal,omitempty"`
}

type ContinuityDecision struct {
	ID       string `json:"id"`
	Title    string `json:"title"`
	WhyKeep  string `json:"why_keep"`
	SourceID string `json:"source_id,omitempty"`
}

type ContinuityCommitment struct {
	ID         string `json:"id"`
	Title      string `json:"title"`
	Owner      string `json:"owner,omitempty"`
	DoneSignal string `json:"done_signal"`
}

type ContinuityOpenLoop struct {
	ID       string `json:"id"`
	Title    string `json:"title"`
	Why      string `json:"why"`
	NextMove string `json:"next_move"`
}

type ContinuityContinuation struct {
	Title          string   `json:"title"`
	Minutes        int      `json:"minutes"`
	StartingPoint  string   `json:"starting_point"`
	NeededContext  []string `json:"needed_context,omitempty"`
	DoneSignal     string   `json:"done_signal"`
	ActivationCost string   `json:"activation_cost"`
}

type ContinuityIntegrationHints struct {
	Memory       []string `json:"memory"`
	Chronos      []string `json:"chronos"`
	Conversation []string `json:"conversation"`
	Temporal     []string `json:"temporal"`
	Procedure    []string `json:"procedure"`
	Surface      []string `json:"surface"`
}

// RecoverContinuity turns scattered project residue into a compact restart
// point: what changed, what matters, what is open, and where to continue.
func RecoverContinuity(req ContinuityRecoverRequest) ContinuityRecoveryPlan {
	req = normalizeContinuityRequest(req)
	packets := buildContinuityContextPackets(req)
	decisions := buildContinuityDecisions(req)
	commitments := buildContinuityCommitments(req)
	loops := buildContinuityOpenLoops(req)
	thread := buildContinuityThread(req, packets, decisions, loops)
	continuation := buildContinuityContinuation(req, thread, packets, loops)

	return ContinuityRecoveryPlan{
		ID:                    "cont_" + stableBehaviorID(firstNonEmpty(req.Project, req.Intent, req.CurrentQuery, "continuity recovery")),
		Surface:               normalizeQuestSurface(req.Surface),
		Project:               req.Project,
		Summary:               summarizeContinuity(req, packets, decisions, commitments, loops),
		RecoveredThread:       thread,
		ContextPackets:        packets,
		DecisionLog:           decisions,
		CommitmentLog:         commitments,
		OpenLoops:             loops,
		SuggestedContinuation: continuation,
		MemorySeeds:           continuityMemorySeeds(req, thread, continuation),
		Integration: ContinuityIntegrationHints{
			Memory: []string{
				"Persist recovered state only after client/user confirmation or source-backed write.",
				"Prefer compact state snapshots over storing every raw artifact as durable memory.",
			},
			Chronos: []string{
				"Age recovered threads by last source update and resurface when the user returns to the same project.",
				"Mark stale continuity when open loops remain untouched across review windows.",
			},
			Conversation: []string{
				"Feed fresh meeting/chat notes through /conversation/harvest before updating decision and commitment logs.",
			},
			Temporal: []string{
				"Feed the suggested continuation into /temporal/coordinate when the user asks when to resume.",
			},
			Procedure: []string{
				"Route repeated recovery patterns into /procedure/compile once the restart workflow stabilizes.",
			},
			Surface: continuitySurfaceHints(req.Surface),
		},
		Guardrails: []string{
			"Do not claim project memory, docs, tasks, or timelines were updated unless a tool confirms it.",
			"Separate source-backed facts from inferred continuation suggestions.",
			"Keep recovery compact; the point is to resume work, not recreate the entire archive.",
		},
		OpenQuestions: continuityOpenQuestions(req, loops),
	}
}

func normalizeContinuityRequest(req ContinuityRecoverRequest) ContinuityRecoverRequest {
	req.Surface = normalizeQuestSurface(req.Surface)
	req.Intent = cleanPlanningText(req.Intent)
	req.CurrentQuery = cleanPlanningText(req.CurrentQuery)
	req.Project = cleanPlanningText(req.Project)
	req.Decisions = uniqueContinuityStrings(req.Decisions)
	req.Commitments = uniqueContinuityStrings(req.Commitments)
	req.OpenLoops = uniqueContinuityStrings(req.OpenLoops)
	for i := range req.PreviousSessions {
		req.PreviousSessions[i].ID = cleanPlanningText(req.PreviousSessions[i].ID)
		req.PreviousSessions[i].Title = cleanPlanningText(req.PreviousSessions[i].Title)
		req.PreviousSessions[i].Summary = cleanPlanningText(req.PreviousSessions[i].Summary)
		req.PreviousSessions[i].Outcome = cleanPlanningText(req.PreviousSessions[i].Outcome)
		req.PreviousSessions[i].UpdatedAt = cleanPlanningText(req.PreviousSessions[i].UpdatedAt)
	}
	for i := range req.Artifacts {
		req.Artifacts[i].ID = cleanPlanningText(req.Artifacts[i].ID)
		req.Artifacts[i].Title = cleanPlanningText(firstNonEmpty(req.Artifacts[i].Title, req.Artifacts[i].Summary, "context artifact"))
		req.Artifacts[i].Kind = strings.ToLower(strings.TrimSpace(req.Artifacts[i].Kind))
		req.Artifacts[i].Source = cleanPlanningText(req.Artifacts[i].Source)
		req.Artifacts[i].Summary = cleanPlanningText(req.Artifacts[i].Summary)
		req.Artifacts[i].Status = strings.ToLower(strings.TrimSpace(req.Artifacts[i].Status))
	}
	if req.Project == "" {
		req.Project = inferContinuityProject(req)
	}
	return req
}

func buildContinuityContextPackets(req ContinuityRecoverRequest) []ContinuityContextPacket {
	var packets []ContinuityContextPacket
	for _, session := range req.PreviousSessions {
		title := firstNonEmpty(session.Title, session.Summary, "previous session")
		packets = append(packets, ContinuityContextPacket{
			ID:       firstNonEmpty(session.ID, "sess_"+stableBehaviorID(title)),
			Title:    sentenceCase(title),
			Kind:     "session",
			Why:      "Previous work can reduce restart cost.",
			Source:   session.UpdatedAt,
			NextUse:  "Use as the top-level thread state before continuing.",
			Evidence: []string{firstNonEmpty(session.Outcome, session.Summary)},
		})
	}
	for _, artifact := range req.Artifacts {
		if artifact.Status == "archived" || artifact.Status == "done" {
			continue
		}
		title := firstNonEmpty(artifact.Title, artifact.Summary, "context artifact")
		packets = append(packets, ContinuityContextPacket{
			ID:       firstNonEmpty(artifact.ID, "art_"+stableBehaviorID(title)),
			Title:    sentenceCase(title),
			Kind:     firstNonEmpty(artifact.Kind, "artifact"),
			Why:      "Artifact may contain state needed to resume without rereading everything.",
			Source:   artifact.Source,
			NextUse:  "Reference only if it affects the next continuation move.",
			Evidence: []string{artifact.Summary},
		})
	}
	if len(packets) == 0 {
		packets = append(packets, ContinuityContextPacket{
			ID:         "ctx_clarify",
			Title:      "Clarify the current thread",
			Kind:       "clarification",
			Why:        "No prior state was supplied.",
			NextUse:    "Ask for the last known state before continuing.",
			DoneSignal: "The active thread is named.",
		})
	}
	if len(packets) > 8 {
		return packets[:8]
	}
	return packets
}

func buildContinuityDecisions(req ContinuityRecoverRequest) []ContinuityDecision {
	var out []ContinuityDecision
	for _, decision := range req.Decisions {
		out = append(out, ContinuityDecision{
			ID:      "dec_" + stableBehaviorID(decision),
			Title:   sentenceCase(decision),
			WhyKeep: "Decision reduces future re-litigation and keeps the thread continuous.",
		})
	}
	for _, session := range req.PreviousSessions {
		if containsPlanningAny(strings.ToLower(session.Outcome), "decided", "agreed", "approved") {
			out = append(out, ContinuityDecision{
				ID:       "dec_" + stableBehaviorID(session.Outcome),
				Title:    sentenceCase(session.Outcome),
				WhyKeep:  "Session outcome appears to contain a decision.",
				SourceID: session.ID,
			})
		}
	}
	if len(out) > 6 {
		return out[:6]
	}
	return out
}

func buildContinuityCommitments(req ContinuityRecoverRequest) []ContinuityCommitment {
	var out []ContinuityCommitment
	for _, commitment := range req.Commitments {
		out = append(out, ContinuityCommitment{
			ID:         "com_" + stableBehaviorID(commitment),
			Title:      sentenceCase(commitment),
			DoneSignal: "The promised artifact, answer, or owner update exists.",
		})
	}
	if len(out) > 6 {
		return out[:6]
	}
	return out
}

func buildContinuityOpenLoops(req ContinuityRecoverRequest) []ContinuityOpenLoop {
	var out []ContinuityOpenLoop
	for _, loop := range req.OpenLoops {
		out = append(out, ContinuityOpenLoop{
			ID:       "loop_" + stableBehaviorID(loop),
			Title:    sentenceCase(loop),
			Why:      "Unresolved context can silently block continuation.",
			NextMove: "Answer, assign, defer, or explicitly close the loop.",
		})
	}
	for _, artifact := range req.Artifacts {
		if containsPlanningAny(strings.ToLower(artifact.Status+" "+artifact.Title+" "+artifact.Summary), "blocked", "waiting", "todo", "open") {
			out = append(out, ContinuityOpenLoop{
				ID:       "loop_" + stableBehaviorID(artifact.Title),
				Title:    sentenceCase(artifact.Title),
				Why:      "Artifact status implies unfinished state.",
				NextMove: "Name the blocker or next owner before resuming.",
			})
		}
	}
	if len(out) > 6 {
		return out[:6]
	}
	return out
}

func buildContinuityThread(req ContinuityRecoverRequest, packets []ContinuityContextPacket, decisions []ContinuityDecision, loops []ContinuityOpenLoop) ContinuityThread {
	title := sentenceCase(firstNonEmpty(req.Project, req.Intent, req.CurrentQuery, "active thread"))
	lastKnown := "No source-backed last state supplied."
	var sourceIDs []string
	if len(packets) > 0 {
		lastKnown = packets[0].Title
		sourceIDs = append(sourceIDs, packets[0].ID)
	}
	if len(decisions) > 0 {
		lastKnown = "Decision: " + decisions[0].Title
	}
	conf := 0.42 + float64(len(packets))*0.04 + float64(len(decisions))*0.06 - float64(len(loops))*0.03
	if conf > 0.86 {
		conf = 0.86
	}
	if conf < 0.2 {
		conf = 0.2
	}
	return ContinuityThread{
		Title:        title,
		LastKnown:    lastKnown,
		WhyItMatters: "This is the smallest state bundle needed to resume without reconstructing the full archive.",
		SourceIDs:    sourceIDs,
		Confidence:   conf,
	}
}

func buildContinuityContinuation(req ContinuityRecoverRequest, thread ContinuityThread, packets []ContinuityContextPacket, loops []ContinuityOpenLoop) ContinuityContinuation {
	title := "Continue: " + thread.Title
	start := thread.LastKnown
	if len(loops) > 0 {
		title = "Resolve open loop: " + loops[0].Title
		start = loops[0].NextMove
	}
	return ContinuityContinuation{
		Title:          title,
		Minutes:        15,
		StartingPoint:  start,
		NeededContext:  continuityNeededContext(packets, loops),
		DoneSignal:     "A visible next artifact, answer, or updated state exists.",
		ActivationCost: inferContinuityActivationCost(packets, loops),
	}
}

func summarizeContinuity(req ContinuityRecoverRequest, packets []ContinuityContextPacket, decisions []ContinuityDecision, commitments []ContinuityCommitment, loops []ContinuityOpenLoop) string {
	return sentenceCase(firstNonEmpty(req.Project, req.Intent, "continuity recovery")) + " recovered " +
		intToMomentumString(len(packets)) + " context packets, " +
		intToMomentumString(len(decisions)) + " decisions, " +
		intToMomentumString(len(commitments)) + " commitments, and " +
		intToMomentumString(len(loops)) + " open loops."
}

func continuityMemorySeeds(req ContinuityRecoverRequest, thread ContinuityThread, continuation ContinuityContinuation) []QuestMemorySeed {
	seeds := []QuestMemorySeed{
		{Key: "active_thread", Value: thread.Title, Importance: 0.74},
		{Key: "continuation_start", Value: continuation.StartingPoint, Importance: 0.68},
	}
	if req.Project != "" {
		seeds = append(seeds, QuestMemorySeed{Key: "continuity_project", Value: req.Project, Importance: 0.7})
	}
	return seeds
}

func continuityNeededContext(packets []ContinuityContextPacket, loops []ContinuityOpenLoop) []string {
	var out []string
	for _, packet := range packets {
		if packet.Kind == "session" || packet.Kind == "artifact" {
			out = append(out, packet.Title)
		}
		if len(out) == 3 {
			break
		}
	}
	if len(loops) > 0 {
		out = append(out, loops[0].Title)
	}
	return uniqueContinuityStrings(out)
}

func inferContinuityActivationCost(packets []ContinuityContextPacket, loops []ContinuityOpenLoop) string {
	switch {
	case len(packets) <= 1 && len(loops) == 0:
		return "low"
	case len(loops) > 2 || len(packets) > 5:
		return "high"
	default:
		return "medium"
	}
}

func inferContinuityProject(req ContinuityRecoverRequest) string {
	for _, artifact := range req.Artifacts {
		if artifact.Source != "" {
			return artifact.Source
		}
	}
	for _, session := range req.PreviousSessions {
		if session.Title != "" {
			return session.Title
		}
	}
	return ""
}

func continuitySurfaceHints(surface string) []string {
	switch normalizeQuestSurface(surface) {
	case "dev":
		return []string{"Show active thread, file/repo context, decisions, and the next implementation move first."}
	case "studio":
		return []string{"Show business state, owner commitments, customer-facing decisions, and next operator move first."}
	case "home":
		return []string{"Show one gentle restart point and keep old context out of the way unless needed."}
	default:
		return []string{"Keep recovery compact and surface-neutral."}
	}
}

func continuityOpenQuestions(req ContinuityRecoverRequest, loops []ContinuityOpenLoop) []string {
	var qs []string
	if len(req.PreviousSessions) == 0 && len(req.Artifacts) == 0 {
		qs = append(qs, "What was the last known state?")
	}
	if len(req.Decisions) == 0 {
		qs = append(qs, "Which decisions should not be re-litigated?")
	}
	if len(loops) > 0 {
		qs = append(qs, "Which open loop should be resolved first?")
	}
	return qs
}

func uniqueContinuityStrings(values []string) []string {
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

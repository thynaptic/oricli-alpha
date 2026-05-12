package cognition

import (
	"sort"
	"strings"
)

// ContextMomentumRequest turns scattered context into action-ready packets.
type ContextMomentumRequest struct {
	Surface          string                `json:"surface,omitempty"`
	Items            []ContextMomentumItem `json:"items,omitempty"`
	CurrentProject   string                `json:"current_project,omitempty"`
	UserState        MomentumUserState     `json:"user_state,omitempty"`
	AvailableMinutes int                   `json:"available_minutes,omitempty"`
	Preferences      MomentumPreferences   `json:"preferences,omitempty"`
	Metadata         map[string]any        `json:"metadata,omitempty"`
}

type ContextMomentumItem struct {
	ID          string   `json:"id,omitempty"`
	Title       string   `json:"title,omitempty"`
	Content     string   `json:"content,omitempty"`
	Kind        string   `json:"kind,omitempty"`
	Source      string   `json:"source,omitempty"`
	ProjectHint string   `json:"project_hint,omitempty"`
	Status      string   `json:"status,omitempty"`
	Tags        []string `json:"tags,omitempty"`
}

type MomentumUserState struct {
	Energy string `json:"energy,omitempty"`
	Mood   string `json:"mood,omitempty"`
	Mode   string `json:"mode,omitempty"`
}

type MomentumPreferences struct {
	MaxPackets         int  `json:"max_packets,omitempty"`
	OverwhelmSensitive bool `json:"overwhelm_sensitive,omitempty"`
	PreserveNovelty    bool `json:"preserve_novelty,omitempty"`
}

type ContextMomentumSystem struct {
	Surface          string                   `json:"surface"`
	Summary          string                   `json:"summary"`
	Actionability    MomentumActionability    `json:"actionability"`
	Packets          []MomentumPacket         `json:"packets"`
	NextFiveMinute   MomentumPacket           `json:"next_5_minute"`
	NextThirtyMinute MomentumPacket           `json:"next_30_minute"`
	SteppingStone    MomentumSteppingStone    `json:"stepping_stone"`
	Continuity       MomentumContinuity       `json:"continuity"`
	MemorySeeds      []QuestMemorySeed        `json:"memory_seeds,omitempty"`
	Integration      MomentumIntegrationHints `json:"integration"`
	OpenQuestions    []string                 `json:"open_questions,omitempty"`
}

type MomentumActionability struct {
	ActiveProjects    []MomentumBucketItem `json:"active_projects,omitempty"`
	OngoingAreas      []MomentumBucketItem `json:"ongoing_areas,omitempty"`
	ReusableResources []MomentumBucketItem `json:"reusable_resources,omitempty"`
	ArchiveCandidates []MomentumBucketItem `json:"archive_candidates,omitempty"`
}

type MomentumBucketItem struct {
	ID      string `json:"id,omitempty"`
	Title   string `json:"title"`
	Reason  string `json:"reason"`
	NextUse string `json:"next_use,omitempty"`
	Source  string `json:"source,omitempty"`
}

type MomentumPacket struct {
	ID             string   `json:"id"`
	Title          string   `json:"title"`
	Project        string   `json:"project,omitempty"`
	SourceItemIDs  []string `json:"source_item_ids,omitempty"`
	Minutes        int      `json:"minutes"`
	Energy         string   `json:"energy"`
	Why            string   `json:"why"`
	DoneSignal     string   `json:"done_signal"`
	FutureSelfNote string   `json:"future_self_note"`
}

type MomentumSteppingStone struct {
	Title          string `json:"title"`
	WhyPreserve    string `json:"why_preserve"`
	SuggestedHome  string `json:"suggested_home"`
	FutureQuestion string `json:"future_question"`
}

type MomentumContinuity struct {
	ProgressionLoop []string `json:"progression_loop"`
	ReviewCadence   string   `json:"review_cadence"`
	ToneGuard       string   `json:"tone_guard"`
}

type MomentumIntegrationHints struct {
	MemoryTags     []string `json:"memory_tags"`
	ChronosSignals []string `json:"chronos_signals"`
	GoalHooks      []string `json:"goal_hooks"`
	SurfaceHints   []string `json:"surface_hints"`
	Guardrails     []string `json:"guardrails"`
}

// BuildContextMomentumSystem extracts the Forte-style primitive without
// cloning PARA/CODE: reduce cognitive tax, package context, and produce motion.
func BuildContextMomentumSystem(req ContextMomentumRequest) ContextMomentumSystem {
	req = normalizeMomentumRequest(req)
	actionability := classifyMomentumItems(req)
	packets := buildMomentumPackets(req, actionability)
	nextFive := chooseMomentumPacket(packets, 5, req.UserState.Energy)
	nextThirty := chooseMomentumPacket(packets, 30, req.UserState.Energy)
	stone := chooseMomentumSteppingStone(req, actionability)

	return ContextMomentumSystem{
		Surface:          normalizeQuestSurface(req.Surface),
		Summary:          summarizeMomentum(req, actionability),
		Actionability:    actionability,
		Packets:          packets,
		NextFiveMinute:   nextFive,
		NextThirtyMinute: nextThirty,
		SteppingStone:    stone,
		Continuity: MomentumContinuity{
			ProgressionLoop: []string{"capture", "route by actionability", "distill into packet", "express as visible output", "archive or recycle"},
			ReviewCadence:   "Review active packets weekly or when the project context changes.",
			ToneGuard:       "Reduce burden; do not turn organization into another obligation.",
		},
		MemorySeeds: momentumMemorySeeds(req, nextFive, stone),
		Integration: MomentumIntegrationHints{
			MemoryTags:     []string{"context_momentum", "future_self_packet", normalizeQuestSurface(req.Surface)},
			ChronosSignals: []string{"context_decay", "stalled_project", "packet_completed", "stepping_stone_preserved"},
			GoalHooks:      []string{"Attach packets to active GoalDaemon tracks only after user confirmation.", "Recycle completed packets into project evidence or reusable resources."},
			SurfaceHints:   momentumSurfaceHints(req.Surface),
			Guardrails: []string{
				"Do not claim files, tasks, reminders, or archives were changed unless a tool confirms it.",
				"Classify by next use, not by brand taxonomy.",
				"Preserve user choice; suggest packets instead of commanding them.",
			},
		},
		OpenQuestions: momentumOpenQuestions(req),
	}
}

func normalizeMomentumRequest(req ContextMomentumRequest) ContextMomentumRequest {
	req.Surface = normalizeQuestSurface(req.Surface)
	req.CurrentProject = cleanPlanningText(req.CurrentProject)
	req.UserState.Energy = strings.ToLower(strings.TrimSpace(req.UserState.Energy))
	if req.UserState.Energy == "" {
		req.UserState.Energy = "medium"
	}
	req.UserState.Mood = cleanPlanningText(req.UserState.Mood)
	req.UserState.Mode = cleanPlanningText(req.UserState.Mode)
	if req.AvailableMinutes <= 0 {
		req.AvailableMinutes = 30
	}
	if req.Preferences.MaxPackets <= 0 {
		req.Preferences.MaxPackets = 6
	}
	if req.Preferences.OverwhelmSensitive && req.Preferences.MaxPackets > 4 {
		req.Preferences.MaxPackets = 4
	}
	for i := range req.Items {
		req.Items[i].Title = cleanPlanningText(firstNonEmpty(req.Items[i].Title, req.Items[i].Content, "Untitled context"))
		req.Items[i].Content = cleanPlanningText(req.Items[i].Content)
		req.Items[i].Kind = strings.ToLower(strings.TrimSpace(req.Items[i].Kind))
		req.Items[i].Status = strings.ToLower(strings.TrimSpace(req.Items[i].Status))
		req.Items[i].ProjectHint = cleanPlanningText(req.Items[i].ProjectHint)
		if req.Items[i].ID == "" {
			req.Items[i].ID = "ctx_" + stableBehaviorID(req.Items[i].Title)
		}
	}
	if len(req.Items) == 0 {
		req.Items = []ContextMomentumItem{{ID: "ctx_empty", Title: "Clarify the context pile", Kind: "note"}}
	}
	return req
}

func classifyMomentumItems(req ContextMomentumRequest) MomentumActionability {
	var out MomentumActionability
	for _, item := range req.Items {
		bucket := momentumBucketForItem(item, req.CurrentProject)
		bi := MomentumBucketItem{
			ID:      item.ID,
			Title:   item.Title,
			Reason:  bucket.reason,
			NextUse: bucket.nextUse,
			Source:  item.Source,
		}
		switch bucket.name {
		case "project":
			out.ActiveProjects = append(out.ActiveProjects, bi)
		case "area":
			out.OngoingAreas = append(out.OngoingAreas, bi)
		case "archive":
			out.ArchiveCandidates = append(out.ArchiveCandidates, bi)
		default:
			out.ReusableResources = append(out.ReusableResources, bi)
		}
	}
	sortMomentumBuckets(&out)
	return out
}

type momentumBucket struct {
	name    string
	reason  string
	nextUse string
}

func momentumBucketForItem(item ContextMomentumItem, currentProject string) momentumBucket {
	lower := strings.ToLower(strings.Join([]string{item.Title, item.Content, item.Kind, item.Status, item.ProjectHint}, " "))
	if item.ProjectHint != "" || (currentProject != "" && containsPlanningAny(lower, strings.ToLower(currentProject))) || containsPlanningAny(lower, "deadline", "ship", "launch", "deliver", "client", "bug", "implement", "draft", "finish", "next") {
		return momentumBucket{"project", "Can move an active outcome forward.", "Turn into a visible project packet."}
	}
	if containsPlanningAny(lower, "someday", "reference", "idea", "article", "link", "research", "resource", "template", "example") {
		return momentumBucket{"resource", "Useful later, but not demanding action today.", "Compress into a reusable future-self note."}
	}
	if containsPlanningAny(lower, "done", "completed", "old", "archive", "closed", "deprecated") {
		return momentumBucket{"archive", "No obvious current use; preserve only if provenance matters.", "Archive after extracting any reusable lesson."}
	}
	if containsPlanningAny(lower, "health", "home", "finance", "ops", "maintenance", "routine", "area", "ongoing") {
		return momentumBucket{"area", "Represents ongoing responsibility rather than a finishable project.", "Break into a small project if progress is needed."}
	}
	return momentumBucket{"resource", "Context has possible value but needs a future use before it becomes work.", "Save as a stepping stone or support material."}
}

func sortMomentumBuckets(out *MomentumActionability) {
	less := func(items []MomentumBucketItem) {
		sort.Slice(items, func(i, j int) bool { return items[i].Title < items[j].Title })
	}
	less(out.ActiveProjects)
	less(out.OngoingAreas)
	less(out.ReusableResources)
	less(out.ArchiveCandidates)
}

func buildMomentumPackets(req ContextMomentumRequest, action MomentumActionability) []MomentumPacket {
	candidates := append([]MomentumBucketItem(nil), action.ActiveProjects...)
	if len(candidates) == 0 {
		candidates = append(candidates, action.ReusableResources...)
	}
	if len(candidates) == 0 {
		candidates = append(candidates, action.OngoingAreas...)
	}
	if len(candidates) == 0 {
		candidates = []MomentumBucketItem{{ID: "ctx_empty", Title: "Clarify the context pile", Reason: "No context was actionable yet.", NextUse: "Create one tiny finish line."}}
	}
	if len(candidates) > req.Preferences.MaxPackets {
		candidates = candidates[:req.Preferences.MaxPackets]
	}

	packets := make([]MomentumPacket, 0, len(candidates)+1)
	for i, c := range candidates {
		mins := []int{5, 15, 30, 60}[momentumMinInt(i, 3)]
		if req.Preferences.OverwhelmSensitive && mins > 30 {
			mins = 30
		}
		title := actionizePlanningAtom(c.Title)
		packets = append(packets, MomentumPacket{
			ID:             "pkt_" + stableBehaviorID(c.ID+"_"+title),
			Title:          title,
			Project:        firstNonEmpty(req.CurrentProject, c.Title),
			SourceItemIDs:  []string{c.ID},
			Minutes:        mins,
			Energy:         estimateMomentumEnergy(title, req.UserState.Energy, mins),
			Why:            c.Reason,
			DoneSignal:     "A visible output, decision, or reusable note exists.",
			FutureSelfNote: "When you return, start from this packet instead of rereading the whole pile.",
		})
	}
	return packets
}

func chooseMomentumPacket(packets []MomentumPacket, maxMinutes int, energy string) MomentumPacket {
	if len(packets) == 0 {
		return MomentumPacket{ID: "pkt_start", Title: "Name the first useful packet", Minutes: 5, Energy: "low", Why: "Naming the packet lowers activation energy.", DoneSignal: "One packet title exists.", FutureSelfNote: "Start here next time."}
	}
	for _, p := range packets {
		if p.Minutes <= maxMinutes && (energy == "" || energy == "medium" || p.Energy == "low" || p.Energy == energy) {
			return p
		}
	}
	for _, p := range packets {
		if p.Minutes <= maxMinutes {
			return p
		}
	}
	p := packets[0]
	p.Minutes = maxMinutes
	p.Title = "Open and shrink: " + strings.ToLower(p.Title)
	p.Energy = "low"
	p.DoneSignal = "A smaller checkpoint is defined."
	return p
}

func chooseMomentumSteppingStone(req ContextMomentumRequest, action MomentumActionability) MomentumSteppingStone {
	pool := append([]MomentumBucketItem(nil), action.ReusableResources...)
	pool = append(pool, action.OngoingAreas...)
	if len(pool) == 0 {
		pool = append(pool, action.ActiveProjects...)
	}
	title := "One interesting clue from the pile"
	reason := "Interesting context can become useful before its exact project is known."
	if len(pool) > 0 {
		title = pool[0].Title
		reason = pool[0].Reason
	}
	return MomentumSteppingStone{
		Title:          title,
		WhyPreserve:    reason,
		SuggestedHome:  "reusable_resources",
		FutureQuestion: "Where could this become useful if the current plan changes?",
	}
}

func summarizeMomentum(req ContextMomentumRequest, action MomentumActionability) string {
	total := len(req.Items)
	return sentenceCase(firstNonEmpty(req.CurrentProject, "context pile")) + " has " +
		pluralizeMomentum(total, "item") + ": " +
		pluralizeMomentum(len(action.ActiveProjects), "active project signal") + ", " +
		pluralizeMomentum(len(action.OngoingAreas), "area signal") + ", " +
		pluralizeMomentum(len(action.ReusableResources), "resource") + ", and " +
		pluralizeMomentum(len(action.ArchiveCandidates), "archive candidate") + "."
}

func momentumMemorySeeds(req ContextMomentumRequest, next MomentumPacket, stone MomentumSteppingStone) []QuestMemorySeed {
	return []QuestMemorySeed{
		{Key: "context_packet", Value: next.Title, Importance: 0.72},
		{Key: "stepping_stone", Value: stone.Title, Importance: 0.58},
		{Key: "surface_state", Value: normalizeQuestSurface(req.Surface) + " context-to-momentum", Importance: 0.46},
	}
}

func momentumSurfaceHints(surface string) []string {
	switch normalizeQuestSurface(surface) {
	case "studio":
		return []string{"Prioritize client/customer-moving packets.", "Separate ongoing business areas from finishable projects."}
	case "dev":
		return []string{"Prefer implementation packets with testable done signals.", "Preserve research as stepping stones unless it changes the current build."}
	case "home":
		return []string{"Keep the next packet low-noise and family-safe.", "Turn recurring household areas into one visible action."}
	default:
		return []string{"Keep context useful across surfaces.", "Prefer next use over perfect categorization."}
	}
}

func momentumOpenQuestions(req ContextMomentumRequest) []string {
	var qs []string
	if req.CurrentProject == "" {
		qs = append(qs, "Which active project should this pile move forward first?")
	}
	if req.UserState.Energy == "low" {
		qs = append(qs, "Should ORI keep this to review/cleanup packets until energy returns?")
	}
	if len(req.Items) == 0 {
		qs = append(qs, "What note, task, file, or idea should ORI route first?")
	}
	return qs
}

func estimateMomentumEnergy(title, currentEnergy string, mins int) string {
	lower := strings.ToLower(title)
	if currentEnergy == "low" || mins <= 10 || containsPlanningAny(lower, "review", "open", "collect", "clarify", "summarize") {
		return "low"
	}
	if mins >= 45 || containsPlanningAny(lower, "draft", "build", "ship", "implement", "record") {
		return "high"
	}
	return "medium"
}

func pluralizeMomentum(n int, singular string) string {
	if n == 1 {
		return "1 " + singular
	}
	return strings.TrimSpace(strings.Join([]string{intToMomentumString(n), singular + "s"}, " "))
}

func intToMomentumString(n int) string {
	switch n {
	case 0:
		return "0"
	case 1:
		return "1"
	case 2:
		return "2"
	case 3:
		return "3"
	case 4:
		return "4"
	case 5:
		return "5"
	default:
		return "6+"
	}
}

func momentumMinInt(a, b int) int {
	if a < b {
		return a
	}
	return b
}

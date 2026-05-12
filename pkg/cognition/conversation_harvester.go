package cognition

import (
	"sort"
	"strings"
)

type ConversationHarvestRequest struct {
	Surface      string                `json:"surface,omitempty"`
	Title        string                `json:"title,omitempty"`
	Intent       string                `json:"intent,omitempty"`
	Transcript   string                `json:"transcript,omitempty"`
	Participants []string              `json:"participants,omitempty"`
	Messages     []ConversationMessage `json:"messages,omitempty"`
	ContextLinks []string              `json:"context_links,omitempty"`
	Metadata     map[string]any        `json:"metadata,omitempty"`
}

type ConversationMessage struct {
	Speaker string   `json:"speaker,omitempty"`
	Text    string   `json:"text,omitempty"`
	Time    string   `json:"time,omitempty"`
	Tags    []string `json:"tags,omitempty"`
}

type ConversationContextHarvest struct {
	ID            string                       `json:"id"`
	Surface       string                       `json:"surface"`
	Title         string                       `json:"title"`
	Summary       string                       `json:"summary"`
	Participants  []string                     `json:"participants,omitempty"`
	Signals       ConversationSignals          `json:"signals"`
	Decisions     []ConversationDecision       `json:"decisions,omitempty"`
	Commitments   []ConversationCommitment     `json:"commitments,omitempty"`
	Unresolved    []ConversationOpenThread     `json:"unresolved,omitempty"`
	FollowUps     []ConversationFollowUpPacket `json:"follow_ups,omitempty"`
	MemorySeeds   []QuestMemorySeed            `json:"memory_seeds,omitempty"`
	Integration   ConversationIntegrationHints `json:"integration"`
	Guardrails    []string                     `json:"guardrails"`
	OpenQuestions []string                     `json:"open_questions,omitempty"`
}

type ConversationSignals struct {
	Intent        string   `json:"intent"`
	Topics        []string `json:"topics,omitempty"`
	EmotionalCue  string   `json:"emotional_cue,omitempty"`
	Urgency       string   `json:"urgency"`
	SourceDensity string   `json:"source_density"`
}

type ConversationDecision struct {
	ID       string `json:"id"`
	Title    string `json:"title"`
	Evidence string `json:"evidence,omitempty"`
	Owner    string `json:"owner,omitempty"`
}

type ConversationCommitment struct {
	ID         string `json:"id"`
	Owner      string `json:"owner,omitempty"`
	Action     string `json:"action"`
	DueHint    string `json:"due_hint,omitempty"`
	DoneSignal string `json:"done_signal"`
}

type ConversationOpenThread struct {
	ID       string `json:"id"`
	Question string `json:"question"`
	Why      string `json:"why"`
	Owner    string `json:"owner,omitempty"`
}

type ConversationFollowUpPacket struct {
	ID            string   `json:"id"`
	Title         string   `json:"title"`
	Owner         string   `json:"owner,omitempty"`
	Minutes       int      `json:"minutes"`
	SourceSignals []string `json:"source_signals,omitempty"`
	DoneSignal    string   `json:"done_signal"`
}

type ConversationIntegrationHints struct {
	Memory    []string `json:"memory"`
	Chronos   []string `json:"chronos"`
	GoalDAG   []string `json:"goal_dag"`
	Procedure []string `json:"procedure,omitempty"`
	Surface   []string `json:"surface"`
}

// HarvestConversationContext extracts the useful residue of a conversation:
// decisions, commitments, open threads, follow-ups, and memory candidates.
func HarvestConversationContext(req ConversationHarvestRequest) ConversationContextHarvest {
	req = normalizeConversationHarvestRequest(req)
	atoms := conversationAtoms(req)
	decisions := harvestConversationDecisions(atoms)
	commitments := harvestConversationCommitments(req, atoms)
	unresolved := harvestConversationOpenThreads(req, atoms)
	followUps := harvestConversationFollowUps(commitments, unresolved)
	title := sentenceCase(firstNonEmpty(req.Title, inferConversationTitle(req, atoms), "Conversation context"))

	return ConversationContextHarvest{
		ID:           "conv_" + stableBehaviorID(title),
		Surface:      normalizeQuestSurface(req.Surface),
		Title:        title,
		Summary:      summarizeConversationHarvest(req, atoms, decisions, commitments, unresolved),
		Participants: uniqueConversationStrings(req.Participants),
		Signals: ConversationSignals{
			Intent:        firstNonEmpty(req.Intent, inferConversationIntent(atoms)),
			Topics:        inferConversationTopics(req, atoms),
			EmotionalCue:  inferConversationEmotion(atoms),
			Urgency:       inferConversationUrgency(atoms),
			SourceDensity: conversationSourceDensity(req, atoms),
		},
		Decisions:   decisions,
		Commitments: commitments,
		Unresolved:  unresolved,
		FollowUps:   followUps,
		MemorySeeds: conversationMemorySeeds(req, title, decisions, commitments, unresolved),
		Integration: ConversationIntegrationHints{
			Memory: []string{
				"Store only confirmed decisions, stable preferences, and durable context after user approval.",
				"Treat speculative summaries as candidates until reviewed or reinforced by future conversations.",
			},
			Chronos: []string{
				"Convert due hints into reminders only when the client confirms calendar/task intent.",
				"Age unresolved threads and resurface them when related goals or participants reappear.",
			},
			GoalDAG: []string{
				"Attach commitments to active goals when an owner and done signal are explicit.",
				"Turn unresolved threads into blocker nodes rather than hidden obligations.",
			},
			Procedure: []string{
				"Route repeated conversation patterns into /procedure/compile after multiple observed runs.",
			},
			Surface: conversationSurfaceHints(req.Surface),
		},
		Guardrails: []string{
			"Do not claim notes, memories, tasks, calendar events, or CRM records were written unless a tool confirms it.",
			"Separate explicit commitments from inferred next steps.",
			"Keep sensitive or private conversation content as local candidate context until the user chooses persistence.",
		},
		OpenQuestions: conversationOpenQuestions(req, decisions, commitments, unresolved),
	}
}

func normalizeConversationHarvestRequest(req ConversationHarvestRequest) ConversationHarvestRequest {
	req.Surface = normalizeQuestSurface(req.Surface)
	req.Title = cleanPlanningText(req.Title)
	req.Intent = cleanPlanningText(req.Intent)
	req.Transcript = cleanPlanningText(req.Transcript)
	req.Participants = uniqueConversationStrings(req.Participants)
	req.ContextLinks = uniqueConversationStrings(req.ContextLinks)
	for i := range req.Messages {
		req.Messages[i].Speaker = cleanPlanningText(req.Messages[i].Speaker)
		req.Messages[i].Text = cleanPlanningText(req.Messages[i].Text)
		req.Messages[i].Time = cleanPlanningText(req.Messages[i].Time)
	}
	return req
}

func conversationAtoms(req ConversationHarvestRequest) []ConversationMessage {
	atoms := append([]ConversationMessage(nil), req.Messages...)
	if len(atoms) == 0 {
		for _, part := range splitPlanningAtoms(req.Transcript) {
			atoms = append(atoms, ConversationMessage{Text: part})
		}
	}
	if len(atoms) == 0 {
		atoms = []ConversationMessage{{Text: firstNonEmpty(req.Intent, "Clarify what this conversation changed")}}
	}
	if len(atoms) > 12 {
		atoms = atoms[:12]
	}
	return atoms
}

func harvestConversationDecisions(atoms []ConversationMessage) []ConversationDecision {
	var out []ConversationDecision
	for _, atom := range atoms {
		text := cleanPlanningText(atom.Text)
		lower := strings.ToLower(text)
		if !containsPlanningAny(lower, "decided", "decision", "we will", "we'll", "agreed", "approved", "greenlight") {
			continue
		}
		out = append(out, ConversationDecision{
			ID:       "dec_" + stableBehaviorID(text),
			Title:    sentenceCase(trimConversationSignal(text)),
			Evidence: text,
			Owner:    atom.Speaker,
		})
		if len(out) == 5 {
			break
		}
	}
	return out
}

func harvestConversationCommitments(req ConversationHarvestRequest, atoms []ConversationMessage) []ConversationCommitment {
	var out []ConversationCommitment
	for _, atom := range atoms {
		text := cleanPlanningText(atom.Text)
		lower := strings.ToLower(text)
		if !containsPlanningAny(lower, "i will", "i'll", "we will", "we'll", "todo", "action item", "follow up", "send", "draft", "schedule", "check") {
			continue
		}
		action := actionizePlanningAtom(trimConversationSignal(text))
		out = append(out, ConversationCommitment{
			ID:         "com_" + stableBehaviorID(firstNonEmpty(atom.Speaker, "owner")+"_"+action),
			Owner:      firstNonEmpty(atom.Speaker, inferConversationOwner(req)),
			Action:     action,
			DueHint:    inferConversationDueHint(text),
			DoneSignal: inferConversationDoneSignal(action),
		})
		if len(out) == 6 {
			break
		}
	}
	return out
}

func harvestConversationOpenThreads(req ConversationHarvestRequest, atoms []ConversationMessage) []ConversationOpenThread {
	var out []ConversationOpenThread
	for _, atom := range atoms {
		text := cleanPlanningText(atom.Text)
		lower := strings.ToLower(text)
		if !strings.Contains(text, "?") && !containsPlanningAny(lower, "blocked", "unsure", "need to know", "unknown", "waiting on", "clarify") {
			continue
		}
		out = append(out, ConversationOpenThread{
			ID:       "thr_" + stableBehaviorID(text),
			Question: normalizeConversationQuestion(text),
			Why:      "This thread affects whether the conversation can turn into action.",
			Owner:    firstNonEmpty(atom.Speaker, inferConversationOwner(req)),
		})
		if len(out) == 5 {
			break
		}
	}
	return out
}

func harvestConversationFollowUps(commitments []ConversationCommitment, threads []ConversationOpenThread) []ConversationFollowUpPacket {
	var out []ConversationFollowUpPacket
	for _, c := range commitments {
		out = append(out, ConversationFollowUpPacket{
			ID:            "fup_" + stableBehaviorID(c.ID),
			Title:         c.Action,
			Owner:         c.Owner,
			Minutes:       15,
			SourceSignals: []string{c.ID},
			DoneSignal:    c.DoneSignal,
		})
	}
	for _, t := range threads {
		out = append(out, ConversationFollowUpPacket{
			ID:            "fup_" + stableBehaviorID(t.ID),
			Title:         "Resolve: " + t.Question,
			Owner:         t.Owner,
			Minutes:       10,
			SourceSignals: []string{t.ID},
			DoneSignal:    "The open question has an answer, owner, or next check-in.",
		})
	}
	if len(out) > 6 {
		return out[:6]
	}
	return out
}

func summarizeConversationHarvest(req ConversationHarvestRequest, atoms []ConversationMessage, decisions []ConversationDecision, commitments []ConversationCommitment, threads []ConversationOpenThread) string {
	return sentenceCase(firstNonEmpty(req.Title, req.Intent, "conversation")) + " yielded " +
		intToMomentumString(len(decisions)) + " decisions, " +
		intToMomentumString(len(commitments)) + " commitments, and " +
		intToMomentumString(len(threads)) + " open threads from " +
		intToMomentumString(len(atoms)) + " conversation signals."
}

func conversationMemorySeeds(req ConversationHarvestRequest, title string, decisions []ConversationDecision, commitments []ConversationCommitment, threads []ConversationOpenThread) []QuestMemorySeed {
	seeds := []QuestMemorySeed{
		{Key: "conversation_title", Value: title, Importance: 0.58},
	}
	if len(decisions) > 0 {
		seeds = append(seeds, QuestMemorySeed{Key: "latest_conversation_decision", Value: decisions[0].Title, Importance: 0.76})
	}
	if len(commitments) > 0 {
		seeds = append(seeds, QuestMemorySeed{Key: "latest_conversation_commitment", Value: commitments[0].Action, Importance: 0.72})
	}
	if len(threads) > 0 {
		seeds = append(seeds, QuestMemorySeed{Key: "latest_unresolved_thread", Value: threads[0].Question, Importance: 0.68})
	}
	if req.Intent != "" {
		seeds = append(seeds, QuestMemorySeed{Key: "conversation_intent", Value: req.Intent, Importance: 0.62})
	}
	return seeds
}

func inferConversationTitle(req ConversationHarvestRequest, atoms []ConversationMessage) string {
	if req.Intent != "" {
		return req.Intent
	}
	if len(req.Participants) > 0 {
		return "conversation with " + strings.Join(req.Participants, ", ")
	}
	if len(atoms) > 0 {
		return atoms[0].Text
	}
	return ""
}

func inferConversationIntent(atoms []ConversationMessage) string {
	joined := strings.ToLower(joinConversationTexts(atoms))
	switch {
	case containsPlanningAny(joined, "launch", "ship", "release"):
		return "coordinate launch work"
	case containsPlanningAny(joined, "customer", "client", "deal", "sales"):
		return "advance customer work"
	case containsPlanningAny(joined, "bug", "incident", "blocked"):
		return "resolve blocker"
	default:
		return "preserve useful context"
	}
}

func inferConversationTopics(req ConversationHarvestRequest, atoms []ConversationMessage) []string {
	var topics []string
	for _, link := range req.ContextLinks {
		topics = append(topics, link)
	}
	joined := strings.ToLower(joinConversationTexts(atoms) + " " + req.Intent)
	for _, candidate := range []string{"launch", "customer", "pricing", "support", "design", "engineering", "schedule", "incident", "handoff", "follow-up"} {
		if containsPlanningAny(joined, candidate) {
			topics = append(topics, candidate)
		}
	}
	return uniqueConversationStrings(topics)
}

func inferConversationEmotion(atoms []ConversationMessage) string {
	joined := strings.ToLower(joinConversationTexts(atoms))
	switch {
	case containsPlanningAny(joined, "excited", "great", "love", "clean"):
		return "positive momentum"
	case containsPlanningAny(joined, "worried", "concern", "risk", "nervous"):
		return "risk attention"
	case containsPlanningAny(joined, "confused", "unclear", "scattered"):
		return "clarity needed"
	default:
		return "neutral"
	}
}

func inferConversationUrgency(atoms []ConversationMessage) string {
	joined := strings.ToLower(joinConversationTexts(atoms))
	switch {
	case containsPlanningAny(joined, "today", "asap", "urgent", "now", "blocked"):
		return "high"
	case containsPlanningAny(joined, "tomorrow", "this week", "soon"):
		return "medium"
	default:
		return "normal"
	}
}

func conversationSourceDensity(req ConversationHarvestRequest, atoms []ConversationMessage) string {
	switch {
	case len(atoms) >= 8 || len(req.Transcript) > 1200:
		return "high"
	case len(atoms) >= 3 || len(req.Transcript) > 300:
		return "medium"
	default:
		return "low"
	}
}

func conversationSurfaceHints(surface string) []string {
	switch normalizeQuestSurface(surface) {
	case "studio":
		return []string{"Frame outputs as decisions, owner follow-ups, customer/business context, and operating memory."}
	case "dev":
		return []string{"Frame outputs as implementation decisions, blockers, owners, and issue-ready follow-up packets."}
	case "home":
		return []string{"Frame outputs as household decisions, shared commitments, unresolved questions, and low-friction reminders."}
	default:
		return []string{"Keep language neutral and let product surfaces decide display/persistence."}
	}
}

func conversationOpenQuestions(req ConversationHarvestRequest, decisions []ConversationDecision, commitments []ConversationCommitment, threads []ConversationOpenThread) []string {
	var qs []string
	if len(decisions) == 0 {
		qs = append(qs, "Were any decisions made that should be remembered?")
	}
	if len(commitments) == 0 {
		qs = append(qs, "Who owns the next visible follow-up?")
	}
	if len(threads) == 0 && len(req.Messages)+len(req.Transcript) > 0 {
		qs = append(qs, "Is anything still unresolved after this conversation?")
	}
	return qs
}

func trimConversationSignal(text string) string {
	text = cleanPlanningText(text)
	lower := strings.ToLower(text)
	for _, marker := range []string{"action item:", "decision:", "todo:", "we decided", "decided", "we agreed", "agreed"} {
		if strings.HasPrefix(lower, marker) {
			return strings.TrimSpace(text[len(marker):])
		}
	}
	return text
}

func inferConversationOwner(req ConversationHarvestRequest) string {
	if len(req.Participants) > 0 {
		return req.Participants[0]
	}
	return "owner"
}

func inferConversationDueHint(text string) string {
	lower := strings.ToLower(text)
	switch {
	case containsPlanningAny(lower, "today", "asap", "now"):
		return "today"
	case containsPlanningAny(lower, "tomorrow"):
		return "tomorrow"
	case containsPlanningAny(lower, "this week", "friday", "monday", "tuesday", "wednesday", "thursday"):
		return "this week"
	default:
		return ""
	}
}

func inferConversationDoneSignal(action string) string {
	lower := strings.ToLower(action)
	switch {
	case containsPlanningAny(lower, "send", "reply", "follow up"):
		return "The message is drafted, approved, or sent by the owner."
	case containsPlanningAny(lower, "schedule", "book"):
		return "The time is confirmed with the relevant people."
	case containsPlanningAny(lower, "check", "verify", "review"):
		return "The answer is recorded and any blocker is named."
	default:
		return "A visible artifact, answer, or owner update exists."
	}
}

func normalizeConversationQuestion(text string) string {
	text = cleanPlanningText(text)
	if strings.Contains(text, "?") {
		return text
	}
	if containsPlanningAny(strings.ToLower(text), "blocked", "waiting on") {
		return "What is needed to unblock: " + text
	}
	return "Clarify: " + text
}

func joinConversationTexts(atoms []ConversationMessage) string {
	parts := make([]string, 0, len(atoms))
	for _, atom := range atoms {
		parts = append(parts, atom.Text)
	}
	return strings.Join(parts, " ")
}

func uniqueConversationStrings(values []string) []string {
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

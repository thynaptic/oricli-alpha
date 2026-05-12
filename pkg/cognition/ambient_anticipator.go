package cognition

import (
	"sort"
	"strings"
)

type AnticipationPrepareRequest struct {
	Surface        string                   `json:"surface,omitempty"`
	Situation      string                   `json:"situation,omitempty"`
	Intent         string                   `json:"intent,omitempty"`
	TimeHorizon    string                   `json:"time_horizon,omitempty"`
	Participants   []string                 `json:"participants,omitempty"`
	Signals        []AnticipationSignal     `json:"signals,omitempty"`
	Preferences    []AnticipationPreference `json:"preferences,omitempty"`
	KnownContext   []string                 `json:"known_context,omitempty"`
	RecentOutcomes []string                 `json:"recent_outcomes,omitempty"`
	Metadata       map[string]any           `json:"metadata,omitempty"`
}

type AnticipationSignal struct {
	Source     string   `json:"source,omitempty"`
	Title      string   `json:"title,omitempty"`
	Content    string   `json:"content,omitempty"`
	Urgency    string   `json:"urgency,omitempty"`
	Confidence float64  `json:"confidence,omitempty"`
	Tags       []string `json:"tags,omitempty"`
}

type AnticipationPreference struct {
	Subject    string `json:"subject,omitempty"`
	Preference string `json:"preference,omitempty"`
	Evidence   string `json:"evidence,omitempty"`
}

type AmbientAnticipationPlan struct {
	ID             string                       `json:"id"`
	Surface        string                       `json:"surface"`
	Situation      string                       `json:"situation"`
	Summary        string                       `json:"summary"`
	Readiness      AnticipationReadiness        `json:"readiness"`
	PrepPackets    []AnticipationPrepPacket     `json:"prep_packets,omitempty"`
	MissingContext []AnticipationMissingContext `json:"missing_context,omitempty"`
	SuggestedTone  AnticipationTone             `json:"suggested_tone"`
	SafeNextMoves  []AnticipationNextMove       `json:"safe_next_moves,omitempty"`
	MemorySeeds    []QuestMemorySeed            `json:"memory_seeds,omitempty"`
	Integration    AnticipationIntegrationHints `json:"integration"`
	Guardrails     []string                     `json:"guardrails"`
	OpenQuestions  []string                     `json:"open_questions,omitempty"`
}

type AnticipationReadiness struct {
	Score      float64  `json:"score"`
	Level      string   `json:"level"`
	Reasons    []string `json:"reasons,omitempty"`
	RiskFlags  []string `json:"risk_flags,omitempty"`
	Confidence float64  `json:"confidence"`
}

type AnticipationPrepPacket struct {
	ID         string   `json:"id"`
	Title      string   `json:"title"`
	Why        string   `json:"why"`
	UseWhen    string   `json:"use_when"`
	Evidence   []string `json:"evidence,omitempty"`
	DoneSignal string   `json:"done_signal"`
}

type AnticipationMissingContext struct {
	Key       string `json:"key"`
	Question  string `json:"question"`
	Why       string `json:"why"`
	Priority  string `json:"priority"`
	SafeProbe string `json:"safe_probe,omitempty"`
}

type AnticipationTone struct {
	Mode      string   `json:"mode"`
	Do        []string `json:"do"`
	Avoid     []string `json:"avoid"`
	Rationale string   `json:"rationale"`
}

type AnticipationNextMove struct {
	Title       string `json:"title"`
	Minutes     int    `json:"minutes"`
	Autonomy    string `json:"autonomy"`
	DoneSignal  string `json:"done_signal"`
	NeedsPermit bool   `json:"needs_permission"`
}

type AnticipationIntegrationHints struct {
	Memory       []string `json:"memory"`
	Chronos      []string `json:"chronos"`
	Conversation []string `json:"conversation"`
	Temporal     []string `json:"temporal"`
	Surface      []string `json:"surface"`
}

// PrepareAmbientAnticipation builds a bounded readiness layer around an
// upcoming interaction without writing mail, calendar, memory, or tasks.
func PrepareAmbientAnticipation(req AnticipationPrepareRequest) AmbientAnticipationPlan {
	req = normalizeAnticipationRequest(req)
	packets := buildAnticipationPrepPackets(req)
	missing := buildAnticipationMissingContext(req)
	readiness := scoreAnticipationReadiness(req, packets, missing)
	situation := sentenceCase(firstNonEmpty(req.Situation, req.Intent, "upcoming interaction"))

	return AmbientAnticipationPlan{
		ID:             "ant_" + stableBehaviorID(situation),
		Surface:        normalizeQuestSurface(req.Surface),
		Situation:      situation,
		Summary:        summarizeAnticipation(req, packets, missing, readiness),
		Readiness:      readiness,
		PrepPackets:    packets,
		MissingContext: missing,
		SuggestedTone:  inferAnticipationTone(req, readiness),
		SafeNextMoves:  buildAnticipationNextMoves(req, missing, readiness),
		MemorySeeds:    anticipationMemorySeeds(req, situation, readiness),
		Integration: AnticipationIntegrationHints{
			Memory: []string{
				"Persist preferences or relationship context only after explicit confirmation or repeated evidence.",
				"Treat one-off signals as ephemeral prep unless reinforced by future outcomes.",
			},
			Chronos: []string{
				"Resurface prep packets near the time horizon only when the client confirms notification intent.",
				"Decay stale anticipation packets after the situation passes.",
			},
			Conversation: []string{
				"After the interaction, route transcript or notes through /conversation/harvest to compare expected vs actual outcomes.",
			},
			Temporal: []string{
				"Use /temporal/coordinate for prep time allocation when readiness is low or missing context is high priority.",
			},
			Surface: anticipationSurfaceHints(req.Surface),
		},
		Guardrails: []string{
			"Do not claim email, calendar, CRM, memory, notification, or task changes happened unless a tool confirms it.",
			"Separate likely user needs from confirmed facts.",
			"Avoid manipulative personalization; use remembered context to reduce friction, not pressure people.",
		},
		OpenQuestions: anticipationOpenQuestions(req, missing),
	}
}

func normalizeAnticipationRequest(req AnticipationPrepareRequest) AnticipationPrepareRequest {
	req.Surface = normalizeQuestSurface(req.Surface)
	req.Situation = cleanPlanningText(req.Situation)
	req.Intent = cleanPlanningText(req.Intent)
	req.TimeHorizon = cleanPlanningText(firstNonEmpty(req.TimeHorizon, "soon"))
	req.Participants = uniqueAnticipationStrings(req.Participants)
	req.KnownContext = uniqueAnticipationStrings(req.KnownContext)
	req.RecentOutcomes = uniqueAnticipationStrings(req.RecentOutcomes)
	for i := range req.Signals {
		req.Signals[i].Source = cleanPlanningText(req.Signals[i].Source)
		req.Signals[i].Title = cleanPlanningText(firstNonEmpty(req.Signals[i].Title, req.Signals[i].Content, "context signal"))
		req.Signals[i].Content = cleanPlanningText(req.Signals[i].Content)
		req.Signals[i].Urgency = strings.ToLower(strings.TrimSpace(req.Signals[i].Urgency))
		if req.Signals[i].Confidence <= 0 {
			req.Signals[i].Confidence = 0.55
		}
		if req.Signals[i].Confidence > 1 {
			req.Signals[i].Confidence = 1
		}
	}
	for i := range req.Preferences {
		req.Preferences[i].Subject = cleanPlanningText(firstNonEmpty(req.Preferences[i].Subject, "participant"))
		req.Preferences[i].Preference = cleanPlanningText(req.Preferences[i].Preference)
		req.Preferences[i].Evidence = cleanPlanningText(req.Preferences[i].Evidence)
	}
	if len(req.Signals) == 0 && len(req.KnownContext) == 0 {
		req.Signals = []AnticipationSignal{{Title: firstNonEmpty(req.Intent, req.Situation, "Clarify what this situation needs"), Confidence: 0.4}}
	}
	return req
}

func buildAnticipationPrepPackets(req AnticipationPrepareRequest) []AnticipationPrepPacket {
	var packets []AnticipationPrepPacket
	for _, sig := range req.Signals {
		packets = append(packets, AnticipationPrepPacket{
			ID:         "prep_" + stableBehaviorID(sig.Title),
			Title:      sentenceCase(sig.Title),
			Why:        anticipationSignalWhy(sig),
			UseWhen:    "Use before or during: " + firstNonEmpty(req.Situation, req.Intent, "the interaction"),
			Evidence:   anticipationEvidence(sig),
			DoneSignal: "The relevant context is available without searching during the interaction.",
		})
		if len(packets) == 5 {
			break
		}
	}
	for _, pref := range req.Preferences {
		if pref.Preference == "" || len(packets) >= 6 {
			continue
		}
		packets = append(packets, AnticipationPrepPacket{
			ID:         "prep_pref_" + stableBehaviorID(pref.Subject+"_"+pref.Preference),
			Title:      "Remember preference: " + pref.Preference,
			Why:        "Known preference can reduce friction if used respectfully.",
			UseWhen:    "Use only if relevant to the current situation.",
			Evidence:   []string{pref.Evidence},
			DoneSignal: "The preference is considered without over-personalizing.",
		})
	}
	return packets
}

func buildAnticipationMissingContext(req AnticipationPrepareRequest) []AnticipationMissingContext {
	var missing []AnticipationMissingContext
	joined := strings.ToLower(req.Situation + " " + req.Intent + " " + strings.Join(req.KnownContext, " ") + " " + joinAnticipationSignals(req.Signals))
	if len(req.Participants) == 0 {
		missing = append(missing, AnticipationMissingContext{
			Key:       "participants",
			Question:  "Who is involved?",
			Why:       "Tone, context, and follow-up ownership depend on participants.",
			Priority:  "high",
			SafeProbe: "Ask who this is for before making assumptions.",
		})
	}
	if !containsPlanningAny(joined, "goal", "outcome", "decision", "decide", "ship", "resolve", "support") {
		missing = append(missing, AnticipationMissingContext{
			Key:       "desired_outcome",
			Question:  "What outcome would make this interaction successful?",
			Why:       "Anticipation needs a success target, not just background context.",
			Priority:  "high",
			SafeProbe: "Ask for the desired outcome in one sentence.",
		})
	}
	if containsPlanningAny(joined, "client", "customer", "sales", "support") && !containsPlanningAny(joined, "latest", "status", "history", "prior") {
		missing = append(missing, AnticipationMissingContext{
			Key:       "relationship_history",
			Question:  "What is the latest relationship state?",
			Why:       "Customer-facing prep is risky without recent state.",
			Priority:  "medium",
			SafeProbe: "Ask for the latest relevant customer/account note.",
		})
	}
	if len(missing) > 5 {
		return missing[:5]
	}
	return missing
}

func scoreAnticipationReadiness(req AnticipationPrepareRequest, packets []AnticipationPrepPacket, missing []AnticipationMissingContext) AnticipationReadiness {
	score := 0.42
	reasons := []string{}
	if len(req.Signals) >= 2 {
		score += 0.16
		reasons = append(reasons, "multiple context signals available")
	}
	if len(req.Participants) > 0 {
		score += 0.1
		reasons = append(reasons, "participants known")
	}
	if req.Intent != "" {
		score += 0.12
		reasons = append(reasons, "intent named")
	}
	if len(req.Preferences) > 0 {
		score += 0.08
		reasons = append(reasons, "preference context available")
	}
	score -= float64(len(missing)) * 0.08
	if score < 0.1 {
		score = 0.1
	}
	if score > 0.92 {
		score = 0.92
	}
	risks := anticipationRiskFlags(req, missing)
	return AnticipationReadiness{
		Score:      score,
		Level:      anticipationReadinessLevel(score),
		Reasons:    reasons,
		RiskFlags:  risks,
		Confidence: anticipationConfidence(req, packets, missing),
	}
}

func inferAnticipationTone(req AnticipationPrepareRequest, readiness AnticipationReadiness) AnticipationTone {
	joined := strings.ToLower(req.Situation + " " + req.Intent + " " + joinAnticipationSignals(req.Signals))
	switch {
	case containsPlanningAny(joined, "customer", "client", "sales", "support"):
		return AnticipationTone{
			Mode:      "calm operator",
			Do:        []string{"lead with current state", "make next steps explicit", "avoid surprise commitments"},
			Avoid:     []string{"over-familiarity", "pressure", "invented certainty"},
			Rationale: "External-facing interactions need trust, clarity, and factual restraint.",
		}
	case containsPlanningAny(joined, "incident", "blocked", "risk", "urgent"):
		return AnticipationTone{
			Mode:      "clear triage",
			Do:        []string{"name the blocker", "separate facts from guesses", "ask for the next decision"},
			Avoid:     []string{"long context dumps", "false reassurance"},
			Rationale: "Risky situations need compression and decision support.",
		}
	case readiness.Level == "low":
		return AnticipationTone{
			Mode:      "curious clarification",
			Do:        []string{"ask one grounding question", "keep suggestions tentative"},
			Avoid:     []string{"acting on thin context", "pretending the situation is understood"},
			Rationale: "Readiness is low, so ORI should gather context before optimizing.",
		}
	default:
		return AnticipationTone{
			Mode:      "prepared companion",
			Do:        []string{"surface only relevant context", "offer a short next move"},
			Avoid:     []string{"noise", "performative personalization"},
			Rationale: "Enough context exists to be helpful without crowding the user.",
		}
	}
}

func buildAnticipationNextMoves(req AnticipationPrepareRequest, missing []AnticipationMissingContext, readiness AnticipationReadiness) []AnticipationNextMove {
	var moves []AnticipationNextMove
	if len(missing) > 0 {
		moves = append(moves, AnticipationNextMove{
			Title:       missing[0].SafeProbe,
			Minutes:     2,
			Autonomy:    "suggest",
			DoneSignal:  "The missing context is answered or explicitly deferred.",
			NeedsPermit: false,
		})
	}
	moves = append(moves, AnticipationNextMove{
		Title:       "Prepare a one-screen context brief",
		Minutes:     5,
		Autonomy:    "draft",
		DoneSignal:  "The user can enter the interaction without searching for background.",
		NeedsPermit: false,
	})
	if readiness.Level != "low" {
		moves = append(moves, AnticipationNextMove{
			Title:       "Draft likely follow-up options",
			Minutes:     10,
			Autonomy:    "draft",
			DoneSignal:  "Follow-up choices are ready but not sent or scheduled.",
			NeedsPermit: false,
		})
	}
	return moves
}

func summarizeAnticipation(req AnticipationPrepareRequest, packets []AnticipationPrepPacket, missing []AnticipationMissingContext, readiness AnticipationReadiness) string {
	return sentenceCase(firstNonEmpty(req.Situation, req.Intent, "upcoming interaction")) + " has " +
		intToMomentumString(len(packets)) + " prep packets, " +
		intToMomentumString(len(missing)) + " missing context items, and " +
		readiness.Level + " readiness."
}

func anticipationMemorySeeds(req AnticipationPrepareRequest, situation string, readiness AnticipationReadiness) []QuestMemorySeed {
	seeds := []QuestMemorySeed{
		{Key: "anticipated_situation", Value: situation, Importance: 0.58},
		{Key: "anticipation_readiness", Value: readiness.Level, Importance: 0.52},
	}
	if len(req.Participants) > 0 {
		seeds = append(seeds, QuestMemorySeed{Key: "anticipation_participants", Value: strings.Join(req.Participants, ", "), Importance: 0.56})
	}
	if len(req.Preferences) > 0 && req.Preferences[0].Preference != "" {
		seeds = append(seeds, QuestMemorySeed{Key: "candidate_preference", Value: req.Preferences[0].Preference, Importance: 0.62})
	}
	return seeds
}

func anticipationSignalWhy(sig AnticipationSignal) string {
	lower := strings.ToLower(sig.Title + " " + sig.Content + " " + sig.Urgency)
	switch {
	case containsPlanningAny(lower, "urgent", "blocked", "risk", "deadline"):
		return "May affect timing, risk, or the next decision."
	case containsPlanningAny(lower, "preference", "likes", "usually", "always"):
		return "May help ORI adapt without asking the user to repeat themselves."
	default:
		return "Relevant context that may reduce search and reorientation."
	}
}

func anticipationEvidence(sig AnticipationSignal) []string {
	var evidence []string
	if sig.Content != "" {
		evidence = append(evidence, sig.Content)
	}
	if sig.Source != "" {
		evidence = append(evidence, "source: "+sig.Source)
	}
	if len(evidence) == 0 {
		evidence = append(evidence, sig.Title)
	}
	return evidence
}

func anticipationRiskFlags(req AnticipationPrepareRequest, missing []AnticipationMissingContext) []string {
	var risks []string
	joined := strings.ToLower(req.Situation + " " + req.Intent + " " + joinAnticipationSignals(req.Signals))
	if len(missing) > 1 {
		risks = append(risks, "thin context")
	}
	if containsPlanningAny(joined, "client", "customer", "legal", "payment", "medical", "security") {
		risks = append(risks, "high-trust context")
	}
	if containsPlanningAny(joined, "send", "publish", "schedule", "book") {
		risks = append(risks, "external action boundary")
	}
	return risks
}

func anticipationReadinessLevel(score float64) string {
	switch {
	case score >= 0.72:
		return "high"
	case score >= 0.48:
		return "medium"
	default:
		return "low"
	}
}

func anticipationConfidence(req AnticipationPrepareRequest, packets []AnticipationPrepPacket, missing []AnticipationMissingContext) float64 {
	score := 0.5 + float64(len(packets))*0.04 - float64(len(missing))*0.05
	if len(req.RecentOutcomes) > 0 {
		score += 0.08
	}
	if score < 0.2 {
		return 0.2
	}
	if score > 0.86 {
		return 0.86
	}
	return score
}

func anticipationSurfaceHints(surface string) []string {
	switch normalizeQuestSurface(surface) {
	case "studio":
		return []string{"Frame prep as account context, owner readiness, next-step options, and business-safe tone."}
	case "dev":
		return []string{"Frame prep as repo/task context, blocker awareness, review posture, and implementation entry points."}
	case "home":
		return []string{"Frame prep as household context, gentle reminders, and low-friction shared coordination."}
	default:
		return []string{"Keep prep neutral and let product surfaces decide what to show or persist."}
	}
}

func anticipationOpenQuestions(req AnticipationPrepareRequest, missing []AnticipationMissingContext) []string {
	var qs []string
	for _, item := range missing {
		qs = append(qs, item.Question)
	}
	if len(req.RecentOutcomes) == 0 {
		qs = append(qs, "What happened the last time this kind of situation appeared?")
	}
	if len(qs) > 5 {
		return qs[:5]
	}
	return qs
}

func joinAnticipationSignals(signals []AnticipationSignal) string {
	parts := make([]string, 0, len(signals))
	for _, sig := range signals {
		parts = append(parts, sig.Title, sig.Content, sig.Urgency, strings.Join(sig.Tags, " "))
	}
	return strings.Join(parts, " ")
}

func uniqueAnticipationStrings(values []string) []string {
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

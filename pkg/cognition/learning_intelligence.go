package cognition

import (
	"hash/fnv"
	"regexp"
	"sort"
	"strings"
	"time"
)

// LearningSource is user-owned material supplied by a product client. Clients
// still own capture, OCR, files, sync, storage, permissions, and source cleanup.
type LearningSource struct {
	ID       string            `json:"id,omitempty"`
	Kind     string            `json:"kind,omitempty"`
	Title    string            `json:"title,omitempty"`
	Content  string            `json:"content,omitempty"`
	Metadata map[string]string `json:"metadata,omitempty"`
}

type LearningPreferences struct {
	Audience          string `json:"audience,omitempty"`
	SkillLevel        string `json:"skill_level,omitempty"`
	ExplanationStyle  string `json:"explanation_style,omitempty"`
	PacingTolerance   string `json:"pacing_tolerance,omitempty"`
	TemporalPressure  string `json:"temporal_pressure,omitempty"`
	MaxConcepts       int    `json:"max_concepts,omitempty"`
	MaxArtifacts      int    `json:"max_artifacts,omitempty"`
	SocraticByDefault bool   `json:"socratic_by_default,omitempty"`
}

type MaterialToMasteryRequest struct {
	Objective        string               `json:"objective,omitempty"`
	Sources          []LearningSource     `json:"sources,omitempty"`
	Deadline         time.Time            `json:"deadline,omitempty"`
	Preferences      LearningPreferences  `json:"preferences,omitempty"`
	ExistingLedger   MasteryLedger        `json:"existing_ledger,omitempty"`
	Misconceptions   []MisconceptionEvent `json:"misconceptions,omitempty"`
	Surface          string               `json:"surface,omitempty"`
	TargetCompetency string               `json:"target_competency,omitempty"`
}

type MaterialToMasterySystem struct {
	Summary          string                      `json:"summary"`
	ConceptGraph     []ConceptNode               `json:"concept_graph"`
	Flashcards       []Flashcard                 `json:"flashcards"`
	PracticeDrills   []PracticeDrill             `json:"practice_drills"`
	Quizzes          []QuizItem                  `json:"quizzes"`
	MockAssessments  []MockAssessment            `json:"mock_assessments"`
	MisconceptionMap []MisconceptionEvent        `json:"misconception_map,omitempty"`
	ReviewCadence    []ReviewEvent               `json:"review_cadence"`
	MasteryScore     MasteryScore                `json:"mastery_score"`
	Explanation      AdaptiveExplanationStrategy `json:"explanation"`
	Assistance       GuidedCompletionDecision    `json:"assistance"`
	GoalDAG          LearningGoalDAG             `json:"goal_dag"`
	Ledger           MasteryLedger               `json:"ledger"`
	Reinforcement    []CrossSurfaceReinforcement `json:"reinforcement,omitempty"`
	OpenQuestions    []string                    `json:"open_questions,omitempty"`
	Guardrails       []string                    `json:"guardrails,omitempty"`
}

type ConceptNode struct {
	ID            string   `json:"id"`
	Title         string   `json:"title"`
	Summary       string   `json:"summary"`
	Prerequisites []string `json:"prerequisites,omitempty"`
	SourceIDs     []string `json:"source_ids,omitempty"`
	Confidence    float64  `json:"confidence"`
}

type Flashcard struct {
	ConceptID string `json:"concept_id"`
	Front     string `json:"front"`
	Back      string `json:"back"`
}

type PracticeDrill struct {
	ConceptID string   `json:"concept_id"`
	Prompt    string   `json:"prompt"`
	Steps     []string `json:"steps,omitempty"`
}

type QuizItem struct {
	ConceptID string `json:"concept_id"`
	Question  string `json:"question"`
	Answer    string `json:"answer"`
	Check     string `json:"check,omitempty"`
	Mode      string `json:"mode,omitempty"`
}

type MockAssessment struct {
	Title        string     `json:"title"`
	TimeboxMins  int        `json:"timebox_mins"`
	Items        []QuizItem `json:"items"`
	ReadinessUse string     `json:"readiness_use"`
}

type MasteryLedger struct {
	SourceIDs      []string             `json:"source_ids,omitempty"`
	Concepts       map[string]float64   `json:"concepts,omitempty"`
	LastReviewedAt map[string]time.Time `json:"last_reviewed_at,omitempty"`
	Evidence       []MasteryEvidence    `json:"evidence,omitempty"`
}

type MasteryEvidence struct {
	ConceptID string    `json:"concept_id"`
	Kind      string    `json:"kind"`
	Signal    string    `json:"signal"`
	Delta     float64   `json:"delta"`
	At        time.Time `json:"at"`
}

type MasteryScore struct {
	Overall        float64            `json:"overall"`
	Tier           string             `json:"tier"`
	ByConcept      map[string]float64 `json:"by_concept,omitempty"`
	Readiness      float64            `json:"readiness"`
	NextBottleneck string             `json:"next_bottleneck,omitempty"`
}

type ReviewEvent struct {
	ConceptID string    `json:"concept_id"`
	ReviewAt  time.Time `json:"review_at"`
	Mode      string    `json:"mode"`
	Reason    string    `json:"reason"`
}

type MisconceptionEvent struct {
	ConceptID  string    `json:"concept_id,omitempty"`
	Statement  string    `json:"statement"`
	Correction string    `json:"correction,omitempty"`
	Confidence float64   `json:"confidence,omitempty"`
	At         time.Time `json:"at,omitempty"`
}

type AdaptiveExplanationStrategy struct {
	Audience         string   `json:"audience"`
	SkillLevel       string   `json:"skill_level"`
	Style            string   `json:"style"`
	Pacing           string   `json:"pacing"`
	Pressure         string   `json:"pressure,omitempty"`
	Strategy         []string `json:"strategy"`
	UseCorpusVoice   bool     `json:"use_corpus_voice"`
	GroundingSignals []string `json:"grounding_signals,omitempty"`
}

type GuidedCompletionDecision struct {
	Mode     string   `json:"mode"`
	Depth    string   `json:"depth"`
	Reason   string   `json:"reason"`
	Allowed  []string `json:"allowed"`
	Avoid    []string `json:"avoid,omitempty"`
	NextMove string   `json:"next_move"`
}

type LearningGoalDAG struct {
	Objective   string                `json:"objective"`
	Nodes       []LearningGoalNode    `json:"nodes"`
	Checkpoints []ReadinessCheckpoint `json:"checkpoints,omitempty"`
}

type LearningGoalNode struct {
	ID        string   `json:"id"`
	Title     string   `json:"title"`
	DependsOn []string `json:"depends_on,omitempty"`
	Mode      string   `json:"mode"`
}

type ReadinessCheckpoint struct {
	Title       string    `json:"title"`
	CheckAt     time.Time `json:"check_at"`
	Signal      string    `json:"signal"`
	MinimumPass float64   `json:"minimum_pass"`
}

type CrossSurfaceReinforcement struct {
	Surface     string `json:"surface"`
	UseCase     string `json:"use_case"`
	Suggestion  string `json:"suggestion"`
	PortableKey string `json:"portable_key,omitempty"`
}

// BuildMaterialToMasteryCompiler transforms raw user-owned material into a
// structured mastery system: explain, practice, assess, remember, reinforce.
func BuildMaterialToMasteryCompiler(req MaterialToMasteryRequest) MaterialToMasterySystem {
	prefs := normalizeLearningPreferences(req.Preferences)
	now := time.Now().UTC()
	concepts := ExtractLearningConcepts(req.Sources, prefs)
	if len(concepts) == 0 {
		concepts = []ConceptNode{{
			ID:         stableLearningID("concept", learningFirstNonEmpty(req.Objective, "untitled learning goal")),
			Title:      learningSentenceCase(learningFirstNonEmpty(req.Objective, "Untitled learning goal")),
			Summary:    "A learning objective was supplied, but no source material was available yet.",
			Confidence: 0.35,
		}}
	}

	ledger := UpdateMasteryLedger(req.ExistingLedger, req.Sources, concepts, req.Misconceptions, now)
	score := ScoreMasteryLedger(ledger, concepts)
	explanation := BuildAdaptiveExplanationLayer(prefs, req.Misconceptions, req.Sources)
	assistance := ChooseGuidedCompletionMode(GuidedCompletionInput{
		Objective:        req.Objective,
		Question:         req.TargetCompetency,
		Preferences:      prefs,
		MasteryScore:     score,
		Misconceptions:   req.Misconceptions,
		HasSourceContext: len(req.Sources) > 0,
	})
	reviews := BuildLearningReviewCadence(concepts, ledger, req.Deadline, now)
	goalDAG := BuildLearningGoalDAG(req.Objective, concepts, req.Deadline, score)

	return MaterialToMasterySystem{
		Summary:          summarizeLearningSystem(req, concepts),
		ConceptGraph:     concepts,
		Flashcards:       BuildFlashcards(concepts, prefs),
		PracticeDrills:   BuildPracticeDrills(concepts, prefs),
		Quizzes:          BuildQuizItems(concepts, prefs),
		MockAssessments:  BuildMockAssessments(req.Objective, concepts, prefs),
		MisconceptionMap: mergeMisconceptions(req.Misconceptions, concepts),
		ReviewCadence:    reviews,
		MasteryScore:     score,
		Explanation:      explanation,
		Assistance:       assistance,
		GoalDAG:          goalDAG,
		Ledger:           ledger,
		Reinforcement:    BuildCrossSurfaceReinforcement(req.Surface, concepts),
		OpenQuestions:    learningOpenQuestions(req),
		Guardrails: []string{
			"Do not claim source ingestion, OCR, storage, scheduling, reminders, or notifications happened unless a tool confirms them.",
			"Use user-owned source material and corpus language before generic explanation patterns.",
			"Regulate assistance depth: hint, scaffold, verify, complete, simulate, or challenge based on mastery and context.",
		},
	}
}

func ExtractLearningConcepts(sources []LearningSource, prefs LearningPreferences) []ConceptNode {
	limit := prefs.MaxConcepts
	if limit <= 0 {
		limit = 8
	}
	seen := map[string]bool{}
	var concepts []ConceptNode
	for _, source := range sources {
		sourceID := source.ID
		if sourceID == "" {
			sourceID = stableLearningID("source", source.Kind+" "+source.Title+" "+source.Content)
		}
		for _, sentence := range splitLearningSentences(source.Title + ". " + source.Content) {
			title := inferLearningConceptTitle(sentence)
			if title == "" {
				continue
			}
			key := strings.ToLower(title)
			if seen[key] {
				continue
			}
			seen[key] = true
			concepts = append(concepts, ConceptNode{
				ID:         stableLearningID("concept", key),
				Title:      learningSentenceCase(title),
				Summary:    learningSentenceCase(trimLearningText(sentence)),
				SourceIDs:  []string{sourceID},
				Confidence: confidenceForLearningConcept(sentence),
			})
			if len(concepts) >= limit {
				return attachLearningPrerequisites(concepts)
			}
		}
	}
	return attachLearningPrerequisites(concepts)
}

func BuildAdaptiveExplanationLayer(prefs LearningPreferences, misconceptions []MisconceptionEvent, sources []LearningSource) AdaptiveExplanationStrategy {
	strategy := []string{
		"Start with the user's own material and wording.",
		"Explain the concept before testing recall.",
		"Convert uncertainty into one visible next practice step.",
	}
	if len(misconceptions) > 0 {
		strategy = append(strategy, "Address known misconceptions before increasing difficulty.")
	}
	if prefs.TemporalPressure == "high" {
		strategy = append(strategy, "Prefer exam-readiness triage over exhaustive coverage.")
	}
	return AdaptiveExplanationStrategy{
		Audience:         learningFirstNonEmpty(prefs.Audience, "general"),
		SkillLevel:       learningFirstNonEmpty(prefs.SkillLevel, "unknown"),
		Style:            learningFirstNonEmpty(prefs.ExplanationStyle, "plain-language"),
		Pacing:           learningFirstNonEmpty(prefs.PacingTolerance, "moderate"),
		Pressure:         prefs.TemporalPressure,
		Strategy:         strategy,
		UseCorpusVoice:   len(sources) > 0,
		GroundingSignals: detectCorpusGroundingSignals(sources),
	}
}

type GuidedCompletionInput struct {
	Objective        string
	Question         string
	Preferences      LearningPreferences
	MasteryScore     MasteryScore
	Misconceptions   []MisconceptionEvent
	HasSourceContext bool
}

func ChooseGuidedCompletionMode(input GuidedCompletionInput) GuidedCompletionDecision {
	if !input.HasSourceContext {
		return GuidedCompletionDecision{
			Mode:     "clarify",
			Depth:    "minimal",
			Reason:   "No source material is available yet.",
			Allowed:  []string{"ask", "clarify", "outline"},
			Avoid:    []string{"pretend to know the source", "claim ingestion happened"},
			NextMove: "Ask for the material, notes, or objective to compile.",
		}
	}
	if input.Preferences.SocraticByDefault || input.MasteryScore.Overall < 0.45 || len(input.Misconceptions) > 0 {
		return GuidedCompletionDecision{
			Mode:     "scaffold",
			Depth:    "guided",
			Reason:   "Mastery is still forming, so guided reasoning beats answer dumping.",
			Allowed:  []string{"hint", "verify", "scaffold", "challenge"},
			Avoid:    []string{"full completion before the learner attempts a step"},
			NextMove: "Offer one hint, then ask the learner to try the next move.",
		}
	}
	if input.MasteryScore.Overall > 0.72 {
		return GuidedCompletionDecision{
			Mode:     "challenge",
			Depth:    "advanced",
			Reason:   "Current mastery supports retrieval practice and transfer.",
			Allowed:  []string{"simulate", "challenge", "verify", "complete"},
			NextMove: "Run a short assessment or transfer problem.",
		}
	}
	return GuidedCompletionDecision{
		Mode:     "explain",
		Depth:    "moderate",
		Reason:   "The learner has enough grounding for explanation plus practice.",
		Allowed:  []string{"explain", "verify", "practice", "complete"},
		NextMove: "Explain the concept briefly, then ask a retrieval question.",
	}
}

func UpdateMasteryLedger(existing MasteryLedger, sources []LearningSource, concepts []ConceptNode, misconceptions []MisconceptionEvent, now time.Time) MasteryLedger {
	ledger := MasteryLedger{
		SourceIDs:      append([]string(nil), existing.SourceIDs...),
		Concepts:       map[string]float64{},
		LastReviewedAt: map[string]time.Time{},
		Evidence:       append([]MasteryEvidence(nil), existing.Evidence...),
	}
	for k, v := range existing.Concepts {
		ledger.Concepts[k] = clampLearning01(v)
	}
	for k, v := range existing.LastReviewedAt {
		ledger.LastReviewedAt[k] = v
	}
	for _, source := range sources {
		id := source.ID
		if id == "" {
			id = stableLearningID("source", source.Kind+" "+source.Title+" "+source.Content)
		}
		if !learningStringIn(ledger.SourceIDs, id) {
			ledger.SourceIDs = append(ledger.SourceIDs, id)
		}
	}
	for _, concept := range concepts {
		if _, ok := ledger.Concepts[concept.ID]; !ok {
			ledger.Concepts[concept.ID] = 0.25
		}
		if _, ok := ledger.LastReviewedAt[concept.ID]; !ok {
			ledger.LastReviewedAt[concept.ID] = now
		}
		ledger.Evidence = append(ledger.Evidence, MasteryEvidence{
			ConceptID: concept.ID,
			Kind:      "source_compiled",
			Signal:    "Concept appeared in supplied material.",
			Delta:     0.05,
			At:        now,
		})
	}
	for _, m := range misconceptions {
		if m.ConceptID != "" {
			ledger.Concepts[m.ConceptID] = clampLearning01(ledger.Concepts[m.ConceptID] - 0.08)
		}
	}
	sort.Strings(ledger.SourceIDs)
	return ledger
}

func ScoreMasteryLedger(ledger MasteryLedger, concepts []ConceptNode) MasteryScore {
	by := map[string]float64{}
	if len(concepts) == 0 {
		return MasteryScore{Overall: 0, Tier: "empty", ByConcept: by, Readiness: 0}
	}
	total := 0.0
	nextID := ""
	nextScore := 2.0
	for _, concept := range concepts {
		score := clampLearning01(ledger.Concepts[concept.ID])
		by[concept.ID] = score
		total += score
		if score < nextScore {
			nextScore = score
			nextID = concept.ID
		}
	}
	overall := clampLearning01(total / float64(len(concepts)))
	tier := "forming"
	switch {
	case overall >= 0.78:
		tier = "ready"
	case overall >= 0.55:
		tier = "practicing"
	}
	return MasteryScore{
		Overall:        overall,
		Tier:           tier,
		ByConcept:      by,
		Readiness:      clampLearning01(overall * 0.92),
		NextBottleneck: nextID,
	}
}

func BuildLearningReviewCadence(concepts []ConceptNode, ledger MasteryLedger, deadline time.Time, now time.Time) []ReviewEvent {
	reviews := make([]ReviewEvent, 0, len(concepts)*2)
	for _, concept := range concepts {
		score := ledger.Concepts[concept.ID]
		firstGap := 24 * time.Hour
		if score < 0.4 {
			firstGap = 8 * time.Hour
		}
		reviews = append(reviews, ReviewEvent{
			ConceptID: concept.ID,
			ReviewAt:  now.Add(firstGap),
			Mode:      "active_recall",
			Reason:    "First retrieval pass after material compilation.",
		})
		reviews = append(reviews, ReviewEvent{
			ConceptID: concept.ID,
			ReviewAt:  now.Add(72 * time.Hour),
			Mode:      "practice_transfer",
			Reason:    "Second pass to move from recognition to usable mastery.",
		})
	}
	if !deadline.IsZero() {
		checkAt := deadline.Add(-24 * time.Hour)
		if checkAt.After(now) {
			reviews = append(reviews, ReviewEvent{
				ConceptID: "overall",
				ReviewAt:  checkAt,
				Mode:      "readiness_check",
				Reason:    "Checkpoint before the stated deadline.",
			})
		}
	}
	sort.SliceStable(reviews, func(i, j int) bool { return reviews[i].ReviewAt.Before(reviews[j].ReviewAt) })
	return reviews
}

func BuildLearningGoalDAG(objective string, concepts []ConceptNode, deadline time.Time, score MasteryScore) LearningGoalDAG {
	nodes := []LearningGoalNode{{
		ID:    "capture",
		Title: "Capture and normalize source material",
		Mode:  "capture",
	}}
	prev := "capture"
	for _, concept := range concepts {
		nodeID := "learn_" + concept.ID
		nodes = append(nodes, LearningGoalNode{
			ID:        nodeID,
			Title:     "Understand " + concept.Title,
			DependsOn: []string{prev},
			Mode:      "explain_practice",
		})
		prev = nodeID
	}
	nodes = append(nodes, LearningGoalNode{
		ID:        "assess",
		Title:     "Assess readiness and patch weak spots",
		DependsOn: []string{prev},
		Mode:      "assessment",
	})
	checkpoints := []ReadinessCheckpoint{{
		Title:       "Readiness checkpoint",
		Signal:      "Quiz plus transfer drill reaches target score.",
		MinimumPass: 0.72,
	}}
	if !deadline.IsZero() {
		checkpoints[0].CheckAt = deadline.Add(-24 * time.Hour)
	}
	return LearningGoalDAG{
		Objective:   learningSentenceCase(learningFirstNonEmpty(objective, "Build mastery from supplied material")),
		Nodes:       nodes,
		Checkpoints: checkpoints,
	}
}

func BuildFlashcards(concepts []ConceptNode, prefs LearningPreferences) []Flashcard {
	limit := artifactLimit(len(concepts), prefs)
	cards := make([]Flashcard, 0, limit)
	for _, concept := range concepts {
		cards = append(cards, Flashcard{
			ConceptID: concept.ID,
			Front:     "What is " + concept.Title + "?",
			Back:      concept.Summary,
		})
		if len(cards) >= limit {
			break
		}
	}
	return cards
}

func BuildPracticeDrills(concepts []ConceptNode, prefs LearningPreferences) []PracticeDrill {
	limit := artifactLimit(len(concepts), prefs)
	drills := make([]PracticeDrill, 0, limit)
	for _, concept := range concepts {
		drills = append(drills, PracticeDrill{
			ConceptID: concept.ID,
			Prompt:    "Explain " + concept.Title + " using one example from the source material.",
			Steps:     []string{"Recall the idea without looking.", "Check against the source.", "Patch one missing detail."},
		})
		if len(drills) >= limit {
			break
		}
	}
	return drills
}

func BuildQuizItems(concepts []ConceptNode, prefs LearningPreferences) []QuizItem {
	limit := artifactLimit(len(concepts), prefs)
	items := make([]QuizItem, 0, limit)
	for _, concept := range concepts {
		items = append(items, QuizItem{
			ConceptID: concept.ID,
			Question:  "Which detail best proves you understand " + concept.Title + "?",
			Answer:    concept.Summary,
			Check:     "Answer should use source-specific language, not a generic definition.",
			Mode:      "active_retrieval",
		})
		if len(items) >= limit {
			break
		}
	}
	return items
}

func BuildMockAssessments(objective string, concepts []ConceptNode, prefs LearningPreferences) []MockAssessment {
	items := BuildQuizItems(concepts, prefs)
	if len(items) == 0 {
		return nil
	}
	if len(items) > 5 {
		items = items[:5]
	}
	return []MockAssessment{{
		Title:        learningSentenceCase(learningFirstNonEmpty(objective, "Mastery readiness check")),
		TimeboxMins:  20,
		Items:        items,
		ReadinessUse: "Use missed items to update misconceptions and the next review cadence.",
	}}
}

func BuildCrossSurfaceReinforcement(surface string, concepts []ConceptNode) []CrossSurfaceReinforcement {
	if len(concepts) == 0 {
		return nil
	}
	concept := concepts[0]
	candidates := []CrossSurfaceReinforcement{
		{Surface: "dev", UseCase: "codebase learning", Suggestion: "Turn architecture notes into retrieval questions and weak-spot drills.", PortableKey: concept.ID},
		{Surface: "studio", UseCase: "employee onboarding", Suggestion: "Convert SOPs into onboarding checks and role-specific practice.", PortableKey: concept.ID},
		{Surface: "home", UseCase: "life systems", Suggestion: "Turn household procedures into simple repeatable learning plans.", PortableKey: concept.ID},
		{Surface: "red", UseCase: "security readiness", Suggestion: "Convert frameworks into control quizzes and incident simulations.", PortableKey: concept.ID},
	}
	if surface == "" {
		return candidates
	}
	out := candidates[:0]
	for _, c := range candidates {
		if c.Surface != surface {
			out = append(out, c)
		}
	}
	return out
}

func normalizeLearningPreferences(p LearningPreferences) LearningPreferences {
	if p.SkillLevel == "" {
		p.SkillLevel = "unknown"
	}
	if p.ExplanationStyle == "" {
		p.ExplanationStyle = "plain-language"
	}
	if p.PacingTolerance == "" {
		p.PacingTolerance = "moderate"
	}
	if p.MaxConcepts <= 0 || p.MaxConcepts > 12 {
		p.MaxConcepts = 8
	}
	if p.MaxArtifacts <= 0 || p.MaxArtifacts > 12 {
		p.MaxArtifacts = 6
	}
	return p
}

func attachLearningPrerequisites(concepts []ConceptNode) []ConceptNode {
	for i := range concepts {
		if i > 0 {
			concepts[i].Prerequisites = []string{concepts[i-1].ID}
		}
	}
	return concepts
}

func mergeMisconceptions(input []MisconceptionEvent, concepts []ConceptNode) []MisconceptionEvent {
	out := append([]MisconceptionEvent(nil), input...)
	for _, concept := range concepts {
		if concept.Confidence < 0.5 {
			out = append(out, MisconceptionEvent{
				ConceptID:  concept.ID,
				Statement:  "Concept extraction has low confidence.",
				Correction: "Ask the user or source client for more precise material.",
				Confidence: 0.45,
			})
		}
	}
	return out
}

func learningOpenQuestions(req MaterialToMasteryRequest) []string {
	var questions []string
	if len(req.Sources) == 0 {
		questions = append(questions, "What source material should ORI compile into mastery artifacts?")
	}
	if req.Objective == "" {
		questions = append(questions, "What outcome should the mastery system optimize for?")
	}
	if req.Deadline.IsZero() {
		questions = append(questions, "Is there a deadline or readiness date?")
	}
	return questions
}

func summarizeLearningSystem(req MaterialToMasteryRequest, concepts []ConceptNode) string {
	objective := learningFirstNonEmpty(req.Objective, "the supplied material")
	return learningSentenceCase("Compiled " + intToWord(len(concepts)) + " concept(s) from " + objective + " into explanation, practice, assessment, review, and reinforcement artifacts.")
}

func detectCorpusGroundingSignals(sources []LearningSource) []string {
	signals := map[string]bool{}
	for _, source := range sources {
		text := strings.ToLower(source.Title + " " + source.Content)
		switch {
		case strings.Contains(text, "repo") || strings.Contains(text, "package") || strings.Contains(text, "api"):
			signals["repo conventions"] = true
		case strings.Contains(text, "team") || strings.Contains(text, "customer") || strings.Contains(text, "sop"):
			signals["team language"] = true
		case strings.Contains(text, "home") || strings.Contains(text, "household") || strings.Contains(text, "family"):
			signals["household language"] = true
		}
	}
	out := make([]string, 0, len(signals))
	for s := range signals {
		out = append(out, s)
	}
	sort.Strings(out)
	return out
}

func splitLearningSentences(text string) []string {
	text = trimLearningText(text)
	if text == "" {
		return nil
	}
	re := regexp.MustCompile(`[.!?\n;]+`)
	raw := re.Split(text, -1)
	out := make([]string, 0, len(raw))
	for _, item := range raw {
		item = trimLearningText(item)
		if len(item) >= 8 {
			out = append(out, item)
		}
	}
	return out
}

func inferLearningConceptTitle(sentence string) string {
	sentence = trimLearningText(sentence)
	if sentence == "" {
		return ""
	}
	lower := strings.ToLower(sentence)
	prefixes := []string{"understand ", "learn ", "explain ", "define ", "compare ", "practice ", "review "}
	for _, prefix := range prefixes {
		if strings.HasPrefix(lower, prefix) {
			sentence = strings.TrimSpace(sentence[len(prefix):])
			break
		}
	}
	words := strings.Fields(sentence)
	if len(words) > 6 {
		words = words[:6]
	}
	title := strings.Join(words, " ")
	title = strings.Trim(title, ":-,()[]{}")
	return title
}

func confidenceForLearningConcept(sentence string) float64 {
	words := len(strings.Fields(sentence))
	switch {
	case words >= 12:
		return 0.78
	case words >= 7:
		return 0.66
	default:
		return 0.52
	}
}

func artifactLimit(conceptCount int, prefs LearningPreferences) int {
	limit := prefs.MaxArtifacts
	if limit <= 0 {
		limit = 6
	}
	if conceptCount < limit {
		return conceptCount
	}
	return limit
}

func stableLearningID(prefix, text string) string {
	h := fnv.New32a()
	_, _ = h.Write([]byte(strings.ToLower(strings.TrimSpace(text))))
	return prefix + "_" + strings.ToLower(strconvBase36(uint64(h.Sum32())))
}

func strconvBase36(n uint64) string {
	const alphabet = "0123456789abcdefghijklmnopqrstuvwxyz"
	if n == 0 {
		return "0"
	}
	var b [16]byte
	i := len(b)
	for n > 0 {
		i--
		b[i] = alphabet[n%36]
		n /= 36
	}
	return string(b[i:])
}

func trimLearningText(s string) string {
	s = strings.TrimSpace(s)
	s = regexp.MustCompile(`\s+`).ReplaceAllString(s, " ")
	return s
}

func learningSentenceCase(s string) string {
	s = trimLearningText(s)
	if s == "" {
		return s
	}
	return strings.ToUpper(s[:1]) + s[1:]
}

func learningFirstNonEmpty(values ...string) string {
	for _, value := range values {
		if strings.TrimSpace(value) != "" {
			return strings.TrimSpace(value)
		}
	}
	return ""
}

func learningStringIn(values []string, needle string) bool {
	for _, value := range values {
		if value == needle {
			return true
		}
	}
	return false
}

func clampLearning01(v float64) float64 {
	if v < 0 {
		return 0
	}
	if v > 1 {
		return 1
	}
	return v
}

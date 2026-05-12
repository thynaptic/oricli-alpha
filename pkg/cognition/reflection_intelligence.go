package cognition

import (
	"math"
	"regexp"
	"sort"
	"strings"
	"time"
)

// ReflectionPreferences tune ORI's journaling/reflection behavior without
// binding the intelligence layer to a specific journal app or storage backend.
type ReflectionPreferences struct {
	MaxPrompts       int
	Directness       string
	SensitiveMode    bool
	RecallWindowDays int
}

type ReflectionMemory struct {
	ID         string    `json:"id,omitempty"`
	Summary    string    `json:"summary"`
	Theme      string    `json:"theme,omitempty"`
	OccurredAt time.Time `json:"occurred_at,omitempty"`
	Importance float64   `json:"importance,omitempty"`
}

type ReflectionRequest struct {
	Entry          string
	Goal           string
	RecentMemories []ReflectionMemory
	Preferences    ReflectionPreferences
}

type ReflectionPlan struct {
	EntrySummary     string             `json:"entry_summary"`
	Signal           ReflectionSignal   `json:"signal"`
	Prompts          []ReflectionPrompt `json:"prompts"`
	MemoryCandidates []MemoryCandidate  `json:"memory_candidates,omitempty"`
	ContinuityHooks  []string           `json:"continuity_hooks,omitempty"`
	ResponseGuards   []string           `json:"response_guards,omitempty"`
}

type ReflectionSignal struct {
	Themes        []string `json:"themes"`
	Mood          string   `json:"mood"`
	Intensity     float64  `json:"intensity"`
	NeedsSupport  bool     `json:"needs_support,omitempty"`
	RiskTier      string   `json:"risk_tier"`
	ThinkingTraps []string `json:"thinking_traps,omitempty"`
}

type ReflectionPrompt struct {
	Question string `json:"question"`
	Purpose  string `json:"purpose"`
	Depth    string `json:"depth"`
}

type MemoryCandidate struct {
	Summary         string  `json:"summary"`
	Reason          string  `json:"reason"`
	Sensitivity     string  `json:"sensitivity"`
	Confidence      float64 `json:"confidence"`
	RequiresConsent bool    `json:"requires_consent,omitempty"`
}

type ReflectionReviewInput struct {
	Entries     []string
	Memories    []ReflectionMemory
	TimeHorizon string
}

type ReflectionReview struct {
	Title          string   `json:"title"`
	Themes         []string `json:"themes"`
	GentlePatterns []string `json:"gentle_patterns"`
	FollowUps      []string `json:"follow_ups"`
	ClosingFrame   string   `json:"closing_frame"`
}

// BuildReflectionPlan creates a dialogic reflection plan: understand the entry,
// ask a small number of useful questions, and identify memory candidates that a
// client may persist after consent/policy checks.
func BuildReflectionPlan(req ReflectionRequest) ReflectionPlan {
	prefs := normalizeReflectionPreferences(req.Preferences)
	entry := cleanReflectionText(req.Entry)
	if entry == "" {
		entry = "The user wants to reflect but has not written an entry yet."
	}

	signal := AnalyzeReflectionSignal(entry)
	prompts := BuildReflectionPrompts(entry, req.Goal, signal, req.RecentMemories, prefs)
	candidates := BuildMemoryCandidates(entry, signal)
	hooks := BuildContinuityHooks(req.RecentMemories, signal, prefs)

	return ReflectionPlan{
		EntrySummary:     summarizeReflectionEntry(entry),
		Signal:           signal,
		Prompts:          prompts,
		MemoryCandidates: candidates,
		ContinuityHooks:  hooks,
		ResponseGuards: []string{
			"Keep the response reflective and user-led, not diagnostic.",
			"Do not present ORI as a therapist or medical provider.",
			"Ask before storing sensitive personal memory unless policy already grants consent.",
			"Escalate acute safety risk to crisis-support language instead of normal reflection.",
		},
	}
}

func AnalyzeReflectionSignal(entry string) ReflectionSignal {
	lower := strings.ToLower(entry)
	themes := detectReflectionThemes(lower)
	traps := detectThinkingTraps(lower)
	intensity := reflectionIntensity(lower)
	mood := "mixed"
	switch {
	case containsReflectionAny(lower, "grateful", "proud", "relieved", "happy", "excited", "hopeful"):
		mood = "positive"
	case containsReflectionAny(lower, "sad", "angry", "anxious", "scared", "ashamed", "guilty", "lonely", "overwhelmed"):
		mood = "heavy"
	case containsReflectionAny(lower, "tired", "numb", "stuck", "confused"):
		mood = "flat"
	}
	risk := "low"
	if intensity >= 0.78 || containsReflectionAny(lower, "panic", "can't go on", "worthless", "hopeless") {
		risk = "medium"
	}
	if containsReflectionAny(lower, "kill myself", "suicide", "self harm", "hurt myself", "end it all") {
		risk = "high"
	}
	return ReflectionSignal{
		Themes:        themes,
		Mood:          mood,
		Intensity:     math.Round(intensity*100) / 100,
		NeedsSupport:  risk != "low" || mood == "heavy",
		RiskTier:      risk,
		ThinkingTraps: traps,
	}
}

func BuildReflectionPrompts(entry, goal string, signal ReflectionSignal, memories []ReflectionMemory, prefs ReflectionPreferences) []ReflectionPrompt {
	var prompts []ReflectionPrompt
	if signal.RiskTier == "high" {
		return []ReflectionPrompt{{
			Question: "Are you in immediate danger right now, and can you reach a trusted person or local emergency support?",
			Purpose:  "Shift from reflection into immediate safety support.",
			Depth:    "safety",
		}}
	}
	if goal != "" {
		prompts = append(prompts, ReflectionPrompt{
			Question: "What would feel like a useful outcome from reflecting on this today?",
			Purpose:  "Let the user define the shape of support.",
			Depth:    "orientation",
		})
	}
	if len(signal.Themes) > 0 {
		prompts = append(prompts, ReflectionPrompt{
			Question: "What part of the " + signal.Themes[0] + " thread feels most alive or unresolved?",
			Purpose:  "Invite specificity without forcing a conclusion.",
			Depth:    "deeper",
		})
	}
	if len(signal.ThinkingTraps) > 0 {
		prompts = append(prompts, ReflectionPrompt{
			Question: "Is there a kinder or more complete version of the story than the one your stress is telling?",
			Purpose:  "Gently loosen an unhelpful interpretation.",
			Depth:    "reframe",
		})
	}
	if memory := mostRelevantReflectionMemory(memories, signal); memory.Summary != "" {
		prompts = append(prompts, ReflectionPrompt{
			Question: "Does this connect to the earlier thread: " + memory.Summary + "?",
			Purpose:  "Use continuity without flooding the current reflection.",
			Depth:    "continuity",
		})
	}
	prompts = append(prompts, ReflectionPrompt{
		Question: "What is one small thing you want to carry forward from this?",
		Purpose:  "Close reflection with agency instead of rumination.",
		Depth:    "closing",
	})
	if len(prompts) > prefs.MaxPrompts {
		prompts = prompts[:prefs.MaxPrompts]
	}
	return prompts
}

func BuildMemoryCandidates(entry string, signal ReflectionSignal) []MemoryCandidate {
	if len(strings.Fields(entry)) < 8 {
		return nil
	}
	summary := summarizeReflectionEntry(entry)
	sensitivity := "normal"
	requiresConsent := false
	if signal.Mood == "heavy" || signal.RiskTier != "low" || containsReflectionAny(entry, "health", "family", "relationship", "boss", "money", "medical") {
		sensitivity = "sensitive"
		requiresConsent = true
	}
	confidence := 0.58
	if len(signal.Themes) > 0 {
		confidence += 0.18
	}
	if signal.Intensity > 0.55 {
		confidence += 0.12
	}
	return []MemoryCandidate{{
		Summary:         summary,
		Reason:          "May help future reflections preserve continuity without replaying the full entry.",
		Sensitivity:     sensitivity,
		Confidence:      math.Round(clamp01Local(confidence)*100) / 100,
		RequiresConsent: requiresConsent,
	}}
}

func BuildContinuityHooks(memories []ReflectionMemory, signal ReflectionSignal, prefs ReflectionPreferences) []string {
	if len(memories) == 0 {
		return nil
	}
	window := time.Duration(prefs.RecallWindowDays) * 24 * time.Hour
	now := time.Now()
	var hooks []string
	for _, memory := range memories {
		if !memory.OccurredAt.IsZero() && prefs.RecallWindowDays > 0 && now.Sub(memory.OccurredAt) > window {
			continue
		}
		if memory.Theme != "" && containsReflectionTheme(signal.Themes, memory.Theme) {
			hooks = append(hooks, "Follow up on recurring "+memory.Theme+" thread: "+memory.Summary)
			continue
		}
		if memory.Importance >= 0.75 {
			hooks = append(hooks, "Check whether this important memory still matters: "+memory.Summary)
		}
	}
	sort.Strings(hooks)
	if len(hooks) > 3 {
		hooks = hooks[:3]
	}
	return hooks
}

func BuildReflectionReview(input ReflectionReviewInput) ReflectionReview {
	themeCounts := map[string]int{}
	for _, entry := range input.Entries {
		for _, theme := range detectReflectionThemes(strings.ToLower(entry)) {
			themeCounts[theme]++
		}
	}
	for _, memory := range input.Memories {
		if memory.Theme != "" {
			themeCounts[memory.Theme]++
		}
	}
	type countedTheme struct {
		theme string
		count int
	}
	var counted []countedTheme
	for theme, count := range themeCounts {
		counted = append(counted, countedTheme{theme: theme, count: count})
	}
	sort.Slice(counted, func(i, j int) bool {
		if counted[i].count != counted[j].count {
			return counted[i].count > counted[j].count
		}
		return counted[i].theme < counted[j].theme
	})
	var themes []string
	for _, item := range counted {
		themes = append(themes, item.theme)
		if len(themes) >= 5 {
			break
		}
	}
	horizon := firstNonEmpty(input.TimeHorizon, "recent")
	review := ReflectionReview{
		Title:        sentenceCase(horizon) + " reflection packet",
		Themes:       themes,
		ClosingFrame: "This is a pattern snapshot, not a verdict. Keep what helps and revise what does not.",
	}
	for _, theme := range themes {
		review.GentlePatterns = append(review.GentlePatterns, "The "+theme+" thread appears more than once; it may deserve a slower look.")
		review.FollowUps = append(review.FollowUps, "What would make the "+theme+" thread feel 10% lighter next?")
	}
	if len(review.FollowUps) == 0 {
		review.FollowUps = []string{"What is one moment from this period you do not want to lose?"}
	}
	return review
}

func normalizeReflectionPreferences(p ReflectionPreferences) ReflectionPreferences {
	if p.MaxPrompts <= 0 {
		p.MaxPrompts = 3
	}
	if p.MaxPrompts > 5 {
		p.MaxPrompts = 5
	}
	if p.Directness == "" {
		p.Directness = "gentle"
	}
	if p.RecallWindowDays <= 0 {
		p.RecallWindowDays = 45
	}
	return p
}

func summarizeReflectionEntry(entry string) string {
	entry = cleanReflectionText(entry)
	if entry == "" {
		return "No entry content was provided."
	}
	sentences := regexp.MustCompile(`[.!?]\s+`).Split(entry, -1)
	summary := cleanReflectionText(sentences[0])
	words := strings.Fields(summary)
	if len(words) > 22 {
		summary = strings.Join(words[:22], " ") + "..."
	}
	return sentenceCase(summary)
}

func detectReflectionThemes(lower string) []string {
	themeNeedles := map[string][]string{
		"work":         {"work", "job", "boss", "deadline", "meeting", "client"},
		"family":       {"family", "kid", "kids", "parent", "partner", "home"},
		"relationship": {"friend", "relationship", "partner", "dating", "marriage", "lonely"},
		"health":       {"health", "sleep", "doctor", "medical", "tired", "energy"},
		"money":        {"money", "bill", "rent", "debt", "budget", "pay"},
		"identity":     {"who i am", "purpose", "meaning", "values", "authentic"},
		"planning":     {"plan", "stuck", "overwhelmed", "too much", "next"},
	}
	var themes []string
	for theme, needles := range themeNeedles {
		if containsReflectionAny(lower, needles...) {
			themes = append(themes, theme)
		}
	}
	sort.Strings(themes)
	if len(themes) == 0 {
		themes = append(themes, "self-reflection")
	}
	return themes
}

func detectThinkingTraps(lower string) []string {
	traps := map[string][]string{
		"all-or-nothing":  {"always", "never", "ruined", "failure", "completely"},
		"mind-reading":    {"they hate me", "everyone thinks", "they must think"},
		"catastrophizing": {"disaster", "catastrophe", "can't recover", "everything is over"},
		"should-loop":     {"i should", "i shouldn't", "supposed to"},
	}
	var out []string
	for trap, needles := range traps {
		if containsReflectionAny(lower, needles...) {
			out = append(out, trap)
		}
	}
	sort.Strings(out)
	return out
}

func reflectionIntensity(lower string) float64 {
	score := 0.15
	if containsReflectionAny(lower, "overwhelmed", "panic", "furious", "terrified", "devastated", "ashamed", "hopeless") {
		score += 0.45
	}
	if containsReflectionAny(lower, "very", "really", "so ", "can't", "always", "never") {
		score += 0.18
	}
	if strings.Count(lower, "!") >= 2 {
		score += 0.12
	}
	if len(strings.Fields(lower)) > 80 {
		score += 0.10
	}
	return clamp01Local(score)
}

func mostRelevantReflectionMemory(memories []ReflectionMemory, signal ReflectionSignal) ReflectionMemory {
	var best ReflectionMemory
	bestScore := -1.0
	for _, memory := range memories {
		score := memory.Importance
		if containsReflectionTheme(signal.Themes, memory.Theme) {
			score += 0.35
		}
		if score > bestScore {
			best = memory
			bestScore = score
		}
	}
	return best
}

func cleanReflectionText(s string) string {
	return strings.TrimSpace(strings.Join(strings.Fields(s), " "))
}

func containsReflectionAny(s string, needles ...string) bool {
	lower := strings.ToLower(s)
	for _, needle := range needles {
		if strings.Contains(lower, strings.ToLower(needle)) {
			return true
		}
	}
	return false
}

func containsReflectionTheme(values []string, needle string) bool {
	for _, value := range values {
		if value == needle {
			return true
		}
	}
	return false
}

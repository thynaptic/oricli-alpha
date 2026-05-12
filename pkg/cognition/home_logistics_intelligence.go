package cognition

import (
	"regexp"
	"sort"
	"strings"
	"time"
)

// HomeLogisticsPreferences keep household logistics intelligence app-neutral.
// Clients still own calendars, reminders, storage, notification delivery, and consent.
type HomeLogisticsPreferences struct {
	MaxPins          int
	ProtectedWindows []string
	Timezone         string
	LowNoiseMode     bool
}

type HomeLogisticsRequest struct {
	Source      string
	Now         time.Time
	Preferences HomeLogisticsPreferences
}

type HomeLogisticsPlan struct {
	Summary       string             `json:"summary"`
	Pins          []ActivePin        `json:"pins"`
	ActivePin     *ActivePin         `json:"active_pin,omitempty"`
	OpenQuestions []string           `json:"open_questions,omitempty"`
	Guardrails    []string           `json:"guardrails,omitempty"`
	Load          HouseholdLoadScore `json:"load"`
}

type ActivePin struct {
	Title          string    `json:"title"`
	Kind           string    `json:"kind"`
	DueAt          time.Time `json:"due_at,omitempty"`
	Urgency        string    `json:"urgency"`
	Reason         string    `json:"reason"`
	OneTapAction   string    `json:"one_tap_action"`
	Draft          string    `json:"draft,omitempty"`
	SourceFragment string    `json:"source_fragment,omitempty"`
	NeedsConsent   bool      `json:"needs_consent,omitempty"`
}

type HouseholdLoadScore struct {
	Score   float64  `json:"score"`
	Tier    string   `json:"tier"`
	Reasons []string `json:"reasons,omitempty"`
}

// BuildHomeLogisticsPlan turns messy household input into a compact set of
// Active Pins. It is intentionally deterministic so product clients can depend
// on stable shape before an LLM adds language polish.
func BuildHomeLogisticsPlan(req HomeLogisticsRequest) HomeLogisticsPlan {
	prefs := normalizeHomeLogisticsPreferences(req.Preferences)
	now := req.Now
	if now.IsZero() {
		now = time.Now()
	}
	source := cleanHomeLogisticsText(req.Source)
	pins := ExtractActivePins(source, now)
	if len(pins) > prefs.MaxPins {
		pins = pins[:prefs.MaxPins]
	}
	active := SelectActivePin(pins, now, prefs)
	load := ScoreHouseholdLoad(pins)
	plan := HomeLogisticsPlan{
		Summary:    summarizeHomeLogistics(source, pins),
		Pins:       pins,
		Guardrails: []string{"Do not claim calendar, reminder, payment, booking, or notification actions happened unless a tool confirms them.", "Keep family data inside the chosen client/storage boundary.", "Surface one Active Pin at a time when low-noise mode is enabled."},
		Load:       load,
	}
	if active.Title != "" {
		plan.ActivePin = &active
	}
	if len(pins) == 0 {
		plan.OpenQuestions = []string{"What date, deadline, or action should ORI watch for?"}
	}
	return plan
}

func ExtractActivePins(source string, now time.Time) []ActivePin {
	fragments := splitHomeLogisticsFragments(source)
	pins := make([]ActivePin, 0, len(fragments))
	for _, fragment := range fragments {
		kind := classifyHomeLogisticsKind(fragment)
		if kind == "note" && !containsHomeLogisticsAny(fragment, "due", "deadline", "bring", "sign", "pay", "book", "volunteer", "permission", "conference", "picture day", "spirit day") {
			continue
		}
		due := inferHomeLogisticsDate(fragment, now)
		title := actionizeHomeLogistics(fragment, kind)
		pin := ActivePin{
			Title:          title,
			Kind:           kind,
			DueAt:          due,
			Urgency:        urgencyForHomePin(due, now, fragment),
			Reason:         reasonForHomePin(kind, due, now),
			OneTapAction:   oneTapActionForHomePin(kind),
			Draft:          draftForHomePin(kind, title),
			SourceFragment: fragment,
			NeedsConsent:   kind == "payment" || kind == "booking" || kind == "message",
		}
		pins = append(pins, pin)
	}
	sort.SliceStable(pins, func(i, j int) bool {
		return homePinRank(pins[i], now) < homePinRank(pins[j], now)
	})
	return pins
}

func SelectActivePin(pins []ActivePin, now time.Time, prefs HomeLogisticsPreferences) ActivePin {
	for _, pin := range pins {
		if prefs.LowNoiseMode && pin.Urgency == "low" {
			continue
		}
		return pin
	}
	if len(pins) > 0 {
		return pins[0]
	}
	return ActivePin{}
}

func ScoreHouseholdLoad(pins []ActivePin) HouseholdLoadScore {
	if len(pins) == 0 {
		return HouseholdLoadScore{Score: 0, Tier: "low"}
	}
	score := clamp01Local(float64(len(pins)) / 8)
	reasons := []string{}
	urgent := 0
	consent := 0
	for _, pin := range pins {
		if pin.Urgency == "high" {
			urgent++
		}
		if pin.NeedsConsent {
			consent++
		}
	}
	if urgent > 0 {
		score += 0.2
		reasons = append(reasons, "near-term obligations")
	}
	if consent > 1 {
		score += 0.12
		reasons = append(reasons, "multiple actions need approval")
	}
	score = clamp01Local(score)
	return HouseholdLoadScore{Score: round2(score), Tier: loadTier(score), Reasons: reasons}
}

func normalizeHomeLogisticsPreferences(p HomeLogisticsPreferences) HomeLogisticsPreferences {
	if p.MaxPins <= 0 {
		p.MaxPins = 5
	}
	if p.MaxPins > 8 {
		p.MaxPins = 8
	}
	return p
}

func splitHomeLogisticsFragments(source string) []string {
	source = strings.ReplaceAll(source, "\n", ". ")
	parts := regexp.MustCompile(`[.;]|\s+-\s+`).Split(source, -1)
	out := make([]string, 0, len(parts))
	for _, part := range parts {
		part = cleanHomeLogisticsText(part)
		if len(part) >= 5 {
			out = append(out, part)
		}
	}
	return out
}

func classifyHomeLogisticsKind(fragment string) string {
	lower := strings.ToLower(fragment)
	switch {
	case containsHomeLogisticsAny(lower, "pay", "fee", "tuition", "invoice", "bring money", "$"):
		return "payment"
	case containsHomeLogisticsAny(lower, "permission", "sign", "form", "waiver"):
		return "form"
	case containsHomeLogisticsAny(lower, "book", "schedule", "appointment", "conference"):
		return "booking"
	case containsHomeLogisticsAny(lower, "email", "message", "ask", "reply", "teacher"):
		return "message"
	case containsHomeLogisticsAny(lower, "bring", "pack", "wear", "costume", "snack", "supplies"):
		return "prep"
	case containsHomeLogisticsAny(lower, "spirit day", "picture day", "field trip", "concert", "pickup", "dropoff"):
		return "event"
	default:
		return "note"
	}
}

func inferHomeLogisticsDate(fragment string, now time.Time) time.Time {
	lower := strings.ToLower(fragment)
	switch {
	case strings.Contains(lower, "tomorrow"):
		return truncateDay(now).AddDate(0, 0, 1)
	case strings.Contains(lower, "today"):
		return truncateDay(now)
	case strings.Contains(lower, "next week"):
		return truncateDay(now).AddDate(0, 0, 7)
	}
	weekdays := map[string]time.Weekday{"sunday": time.Sunday, "monday": time.Monday, "tuesday": time.Tuesday, "wednesday": time.Wednesday, "thursday": time.Thursday, "friday": time.Friday, "saturday": time.Saturday}
	for name, day := range weekdays {
		if strings.Contains(lower, name) {
			return nextWeekday(now, day)
		}
	}
	return time.Time{}
}

func actionizeHomeLogistics(fragment, kind string) string {
	fragment = cleanHomeLogisticsText(fragment)
	switch kind {
	case "payment":
		return "Review payment: " + fragment
	case "form":
		return "Sign or return form: " + fragment
	case "booking":
		return "Schedule or confirm: " + fragment
	case "message":
		return "Send message about: " + fragment
	case "prep":
		return "Prepare: " + fragment
	case "event":
		return "Track event: " + fragment
	default:
		return "Review: " + fragment
	}
}

func urgencyForHomePin(due, now time.Time, fragment string) string {
	if containsHomeLogisticsAny(fragment, "urgent", "asap", "deadline", "due today") {
		return "high"
	}
	if due.IsZero() {
		return "medium"
	}
	days := int(truncateDay(due).Sub(truncateDay(now)).Hours() / 24)
	switch {
	case days <= 1:
		return "high"
	case days <= 7:
		return "medium"
	default:
		return "low"
	}
}

func reasonForHomePin(kind string, due, now time.Time) string {
	if !due.IsZero() {
		return "This has a temporal edge and can become mental load if it stays implicit."
	}
	if kind == "payment" || kind == "form" || kind == "booking" {
		return "This likely needs explicit approval or completion."
	}
	return "This looks actionable enough to stage as a household pin."
}

func oneTapActionForHomePin(kind string) string {
	switch kind {
	case "payment":
		return "Open payment review"
	case "form":
		return "Mark form ready"
	case "booking":
		return "Draft scheduling request"
	case "message":
		return "Draft reply"
	case "prep":
		return "Create prep checklist"
	case "event":
		return "Stage calendar draft"
	default:
		return "Review pin"
	}
}

func draftForHomePin(kind, title string) string {
	switch kind {
	case "booking":
		return "Hi, I would like to confirm a time for " + strings.TrimPrefix(title, "Schedule or confirm: ") + "."
	case "message":
		return "Hi, I wanted to follow up on " + strings.TrimPrefix(title, "Send message about: ") + "."
	default:
		return ""
	}
}

func summarizeHomeLogistics(source string, pins []ActivePin) string {
	if len(pins) == 0 {
		return "No actionable household logistics were detected yet."
	}
	return sentenceCase(cleanHomeLogisticsText("Detected " + intToWord(len(pins)) + " household logistics pin(s) from the source."))
}

func homePinRank(pin ActivePin, now time.Time) int {
	rank := map[string]int{"high": 0, "medium": 10, "low": 20}[pin.Urgency]
	if !pin.DueAt.IsZero() {
		days := int(truncateDay(pin.DueAt).Sub(truncateDay(now)).Hours() / 24)
		if days < 0 {
			days = 0
		}
		rank += days
	}
	return rank
}

func nextWeekday(now time.Time, day time.Weekday) time.Time {
	base := truncateDay(now)
	offset := (int(day) - int(base.Weekday()) + 7) % 7
	if offset == 0 {
		offset = 7
	}
	return base.AddDate(0, 0, offset)
}

func truncateDay(t time.Time) time.Time {
	y, m, d := t.Date()
	return time.Date(y, m, d, 0, 0, 0, 0, t.Location())
}

func cleanHomeLogisticsText(s string) string {
	return strings.TrimSpace(strings.Join(strings.Fields(s), " "))
}

func containsHomeLogisticsAny(s string, needles ...string) bool {
	lower := strings.ToLower(s)
	for _, needle := range needles {
		if strings.Contains(lower, strings.ToLower(needle)) {
			return true
		}
	}
	return false
}

func intToWord(n int) string {
	words := map[int]string{1: "one", 2: "two", 3: "three", 4: "four", 5: "five", 6: "six", 7: "seven", 8: "eight"}
	if word, ok := words[n]; ok {
		return word
	}
	return "multiple"
}

func round2(v float64) float64 {
	return float64(int(v*100+0.5)) / 100
}

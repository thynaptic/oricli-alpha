package cognition

import (
	"context"
	"encoding/json"
	"regexp"
	"strings"
	"time"

	"github.com/thynaptic/oricli-go/pkg/llm"
	"github.com/thynaptic/oricli-go/pkg/state"
)

const (
	intentTimeout = 25 * time.Second
)

type normalizationResponse struct {
	NormalizedIntent string             `json:"normalized_intent"`
	StateDelta       map[string]float64 `json:"state_delta"`
	Subtext          []string           `json:"subtext"`
	MoodScore        float64            `json:"mood_score"`
}

// NormalizeIntent maps noisy/ambiguous user input to a high-signal intent
// aligned with the current session goal. On failure, it returns the raw input.
func NormalizeIntent(raw string, currentState state.SessionState) (string, map[string]float64, []string, float64) {
	raw = strings.TrimSpace(raw)
	if raw == "" {
		return raw, nil, nil, 0
	}
	if !llm.Available() {
		return raw, nil, nil, 0
	}

	systemPrompt := `You are an Intent Correction middleware for an AI assistant.
Your job is to normalize user input into a high-signal, unambiguous intent string.

Rules:
1. If user intent is clear and coherent, preserve the original meaning and wording as much as possible.
2. If intent is ambiguous, contradictory, or underspecified, rewrite it into a concise, actionable normalized intent.
3. Use the current primary goal as context; if the request appears to shift focus away from it, capture that via state_delta.
4. state_delta values must be small adjustments in range [-0.3, 0.3], and only include keys that need change.
5. Allowed state_delta keys: Confidence, Urgency, AnalyticalMode, Frustration, GoalPersistence.
6. Detect subtext tags when present: sarcasm, fatigue, excitement.
7. Set mood_score in range [-1.0, 1.0] where negative means strained mood, positive means upbeat.
8. Return JSON only with this exact schema:
{"normalized_intent":"...", "state_delta":{"Frustration":0.1,"Confidence":-0.1}, "subtext":["fatigue"], "mood_score":-0.35}`

	userPayload, _ := json.Marshal(map[string]interface{}{
		"raw_input": raw,
		"current_state": map[string]interface{}{
			"PrimaryGoal":     currentState.PrimaryGoal,
			"GoalPersistence": currentState.GoalPersistence,
			"Confidence":      currentState.Confidence,
			"Urgency":         currentState.Urgency,
			"AnalyticalMode":  currentState.AnalyticalMode,
			"Frustration":     currentState.Frustration,
		},
	})

	normalized, delta, subtext, moodScore, ok := runNormalizationModel(systemPrompt, string(userPayload), raw)
	if ok {
		return normalized, delta, subtext, moodScore
	}
	return raw, nil, nil, 0
}

func runNormalizationModel(system, user, fallback string) (string, map[string]float64, []string, float64, bool) {
	ctx, cancel := context.WithTimeout(context.Background(), intentTimeout)
	defer cancel()
	raw, err := llm.Chat(ctx, system, user)
	if err != nil {
		return fallback, nil, nil, 0, false
	}
	resp, ok := parseNormalizationResponse(raw)
	if !ok {
		return fallback, nil, nil, 0, false
	}
	normalized := strings.TrimSpace(resp.NormalizedIntent)
	if normalized == "" {
		normalized = fallback
	}
	return normalized, clampDelta(resp.StateDelta), sanitizeSubtext(resp.Subtext), clampMoodScore(resp.MoodScore), true
}

func parseNormalizationResponse(raw string) (normalizationResponse, bool) {
	raw = strings.TrimSpace(stripMarkdownCodeFences(raw))
	var resp normalizationResponse

	if err := json.Unmarshal([]byte(raw), &resp); err == nil {
		return resp, true
	}

	re := regexp.MustCompile(`(?s)\{.*\}`)
	match := re.FindString(raw)
	if match == "" {
		return normalizationResponse{}, false
	}
	if err := json.Unmarshal([]byte(match), &resp); err != nil {
		return normalizationResponse{}, false
	}
	return resp, true
}

func stripMarkdownCodeFences(s string) string {
	trimmed := strings.TrimSpace(s)
	if !strings.HasPrefix(trimmed, "```") || !strings.HasSuffix(trimmed, "```") {
		return trimmed
	}
	lines := strings.Split(trimmed, "\n")
	if len(lines) < 3 {
		return trimmed
	}
	return strings.TrimSpace(strings.Join(lines[1:len(lines)-1], "\n"))
}

func clampDelta(in map[string]float64) map[string]float64 {
	if len(in) == 0 {
		return nil
	}
	allowed := map[string]bool{
		"confidence":       true,
		"urgency":          true,
		"analyticalmode":   true,
		"analytical_mode":  true,
		"frustration":      true,
		"goalpersistence":  true,
		"goal_persistence": true,
	}

	out := make(map[string]float64)
	for k, v := range in {
		nk := strings.ToLower(strings.TrimSpace(k))
		nk = strings.ReplaceAll(nk, " ", "")
		nk = strings.ReplaceAll(nk, "-", "_")
		if !allowed[nk] {
			continue
		}
		if v > 0.3 {
			v = 0.3
		}
		if v < -0.3 {
			v = -0.3
		}
		out[k] = v
	}
	if len(out) == 0 {
		return nil
	}
	return out
}

func sanitizeSubtext(in []string) []string {
	if len(in) == 0 {
		return nil
	}
	allowed := map[string]bool{
		"sarcasm":    true,
		"fatigue":    true,
		"excitement": true,
	}
	var out []string
	seen := make(map[string]bool)
	for _, s := range in {
		v := strings.ToLower(strings.TrimSpace(s))
		if !allowed[v] || seen[v] {
			continue
		}
		seen[v] = true
		out = append(out, v)
	}
	if len(out) == 0 {
		return nil
	}
	return out
}

func clampMoodScore(v float64) float64 {
	if v > 1 {
		return 1
	}
	if v < -1 {
		return -1
	}
	return v
}

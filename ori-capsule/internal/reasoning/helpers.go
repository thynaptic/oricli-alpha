package reasoning

import (
	"regexp"
	"sort"
	"strings"
)

// Local helpers formerly shared across pkg/cognition packages.

func clamp01Local(v float64) float64 { return clamp01(v) }

type QuestMemorySeed struct {
	Key        string  `json:"key"`
	Value      string  `json:"value"`
	Importance float64 `json:"importance"`
}

func stableBehaviorID(value string) string {
	re := regexp.MustCompile(`[^a-z0-9]+`)
	id := re.ReplaceAllString(strings.ToLower(value), "_")
	id = strings.Trim(id, "_")
	if id == "" {
		id = "behavior"
	}
	if len(id) > 48 {
		id = strings.Trim(id[:48], "_")
	}
	return id
}

func normalizeQuestSurface(surface string) string {
	surface = strings.ToLower(strings.TrimSpace(surface))
	switch surface {
	case "home", "studio", "dev", "red", "growth":
		return surface
	default:
		return surface
	}
}

func uniqueActionStrings(values []string) []string {
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

package oracle

import (
	"context"
	"encoding/json"
	"log"
	"os"
	"sort"
	"strings"
	"sync"
	"time"

	copilot "github.com/github/copilot-sdk/go"
)

const (
	modelCachePath = "/tmp/oracle_model_cache.json"
	modelCacheTTL  = 24 * time.Hour
)

type modelCache struct {
	FetchedAt time.Time `json:"fetched_at"`
	Light     string    `json:"light"`
	Heavy     string    `json:"heavy"`
	Research  string    `json:"research"`
}

var (
	cachedModels   *modelCache
	cachedModelsMu sync.RWMutex
)

func isEnabled(m copilot.ModelInfo) bool {
	return m.Policy == nil || m.Policy.State == "enabled" || m.Policy.State == ""
}

// bestFamily picks the highest-version enabled model whose ID contains the given family string.
// "Highest version" = sort by ID descending (lexicographic works for semver suffixes like 4.5, 4.6).
func bestFamily(models []copilot.ModelInfo, family string) string {
	var matches []string
	for _, m := range models {
		if isEnabled(m) && strings.Contains(strings.ToLower(m.ID), family) {
			matches = append(matches, m.ID)
		}
	}
	if len(matches) == 0 {
		return ""
	}
	sort.Sort(sort.Reverse(sort.StringSlice(matches)))
	return matches[0]
}

// RefreshModelCatalog uses the Copilot SDK's own model list to pick:
//   - Light  → best available claude-haiku
//   - Heavy  → "auto" (Copilot picks the best model dynamically)
//   - Research/Dev → best available claude-sonnet
//
// Falls back to disk cache, then hardcoded defaults.
// Runs in a background goroutine during Init — never blocks startup.
func RefreshModelCatalog() {
	if c := loadCachedModels(); c != nil {
		cachedModelsMu.Lock()
		cachedModels = c
		cachedModelsMu.Unlock()
		log.Printf("[Oracle:Catalog] cache hit — light=%s heavy=%s research=%s", c.Light, c.Heavy, c.Research)
		return
	}

	cl := GetClient()
	if cl == nil {
		log.Printf("[Oracle:Catalog] client not ready — using defaults")
		return
	}

	ctx, cancel := context.WithTimeout(context.Background(), 15*time.Second)
	defer cancel()

	models, err := cl.ListModels(ctx)
	if err != nil {
		log.Printf("[Oracle:Catalog] ListModels failed (%v) — using defaults", err)
		return
	}

	light := bestFamily(models, "haiku")
	if light == "" {
		light = defaultCopilotLightModel
	}

	research := bestFamily(models, "claude-sonnet")
	if research == "" {
		research = defaultCopilotResearchModel
	}

	c := &modelCache{
		FetchedAt: time.Now(),
		Light:     light,
		Heavy:     "auto", // Copilot auto-selects best available for heavy reasoning
		Research:  research,
	}

	saveCachedModels(c)

	cachedModelsMu.Lock()
	prev := cachedModels
	cachedModels = c
	cachedModelsMu.Unlock()

	if prev != nil && (prev.Light != c.Light || prev.Heavy != c.Heavy || prev.Research != c.Research) {
		log.Printf("[Oracle:Catalog] selection changed — light=%s heavy=auto research=%s", c.Light, c.Research)
	} else {
		log.Printf("[Oracle:Catalog] models selected — light=%s heavy=auto research=%s", c.Light, c.Research)
	}
}

func loadCachedModels() *modelCache {
	data, err := os.ReadFile(modelCachePath)
	if err != nil {
		return nil
	}
	var c modelCache
	if err := json.Unmarshal(data, &c); err != nil {
		return nil
	}
	if time.Since(c.FetchedAt) > modelCacheTTL {
		return nil
	}
	return &c
}

func saveCachedModels(c *modelCache) {
	data, err := json.MarshalIndent(c, "", "  ")
	if err != nil {
		return
	}
	_ = os.WriteFile(modelCachePath, data, 0644)
}

func catalogModelForRoute(route Route) string {
	cachedModelsMu.RLock()
	c := cachedModels
	cachedModelsMu.RUnlock()
	if c == nil {
		return ""
	}
	switch route {
	case RouteHeavyReasoning:
		return c.Heavy
	case RouteResearch:
		return c.Research
	default:
		return c.Light
	}
}

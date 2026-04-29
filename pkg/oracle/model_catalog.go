package oracle

import (
	"encoding/json"
	"fmt"
	"log"
	"os"
	"strings"
	"sync"
	"time"
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

// RefreshModelCatalog resolves model selection from env overrides and defaults,
// then persists to a 24h disk cache for observability.
func RefreshModelCatalog() {
	light := modelForRoute(RouteLightChat)
	heavy := modelForRoute(RouteHeavyReasoning)
	research := modelForRoute(RouteResearch)

	c := &modelCache{
		FetchedAt: time.Now(),
		Light:     light,
		Heavy:     heavy,
		Research:  research,
	}
	saveCachedModels(c)

	cachedModelsMu.Lock()
	cachedModels = c
	cachedModelsMu.Unlock()

	log.Printf("[Oracle:Catalog] models — light=%s heavy=%s research=%s", light, heavy, research)
}

// modelForRoute returns the model for a route: env override → global env → default.
func modelForRoute(route Route) string {
	switch route {
	case RouteHeavyReasoning:
		if m := envOr("ORACLE_COPILOT_MODEL_HEAVY", ""); m != "" {
			return m
		}
	case RouteResearch:
		if m := envOr("ORACLE_COPILOT_MODEL_RESEARCH", ""); m != "" {
			return m
		}
		if m := envOr("ORACLE_COPILOT_MODEL_HEAVY", ""); m != "" {
			return m
		}
	default:
		if m := envOr("ORACLE_COPILOT_MODEL_LIGHT", ""); m != "" {
			return m
		}
	}
	if m := envOr("ORACLE_COPILOT_MODEL", ""); m != "" {
		return m
	}
	switch route {
	case RouteHeavyReasoning:
		return defaultHeavyModel
	case RouteResearch:
		return defaultResearchModel
	default:
		return defaultLightModel
	}
}

const (
	defaultHeavyThinkingBudget    = 8000
	defaultResearchThinkingBudget = 10000
)

// thinkingBudgetForRoute returns the extended thinking token budget for a route.
// Returns 0 (disabled) for light/image routes. Override with ORACLE_THINKING_HEAVY
// or ORACLE_THINKING_RESEARCH env vars; set to "0" to disable thinking entirely.
func thinkingBudgetForRoute(route Route) int {
	switch route {
	case RouteHeavyReasoning:
		return envInt("ORACLE_THINKING_HEAVY", defaultHeavyThinkingBudget)
	case RouteResearch:
		return envInt("ORACLE_THINKING_RESEARCH", defaultResearchThinkingBudget)

	default:
		return 0
	}
}

func envInt(key string, fallback int) int {
	v := strings.TrimSpace(os.Getenv(key))
	if v == "" {
		return fallback
	}
	var n int
	if _, err := fmt.Sscanf(v, "%d", &n); err != nil {
		return fallback
	}
	return n
}

func envOr(key, fallback string) string {
	if v := strings.TrimSpace(os.Getenv(key)); v != "" {
		return v
	}
	return fallback
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

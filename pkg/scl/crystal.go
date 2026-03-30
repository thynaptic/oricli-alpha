package scl

// crystal.go — Skill Crystallization Layer
//
// A CrystalSkill is a pattern-matched, LLM-bypass shortcut for frequently-used
// intents. When a query matches a crystal's regex pattern AND the skill has
// earned enough reputation, GenerationService skips Ollama entirely and returns
// the template output in microseconds.
//
// Crystallization threshold:  ReputationScore >= 0.85  AND  HitCount >= 10
// Eviction:                   manual (API) or score drops below 0.60 on audit

import (
	"fmt"
	"log"
	"regexp"
	"sort"
	"sync"
	"time"
)

const (
	CrystalThresholdReputation float64 = 0.85
	CrystalThresholdHits       int     = 10
	CrystalEvictBelowScore     float64 = 0.60
)

// ---------------------------------------------------------------------------
// CrystalSkill — a single crystallized pattern
// ---------------------------------------------------------------------------

// CrystalSkill represents a proven, high-reputation response pattern that can
// answer a class of queries without touching the LLM.
type CrystalSkill struct {
	ID             string                       `json:"id"`
	Name           string                       `json:"name"`
	Description    string                       `json:"description"`
	Pattern        string                       `json:"pattern"` // raw regex
	pattern        *regexp.Regexp               // compiled (not JSON-serialised)
	TemplateFn     func(vars map[string]string) string `json:"-"` // response generator
	TemplateBody   string                       `json:"template_body"` // static template (if no fn)
	HitCount       int                          `json:"hit_count"`
	MissCount      int                          `json:"miss_count"`
	AvgLatencyMs   float64                      `json:"avg_latency_ms"`
	ReputationScore float64                     `json:"reputation_score"` // 0.0–1.0
	Active         bool                         `json:"active"`
	CreatedAt      time.Time                    `json:"created_at"`
	LastHitAt      time.Time                    `json:"last_hit_at"`
}

// Compile compiles the Pattern regex. Called automatically by CrystalCache.Register.
func (cs *CrystalSkill) Compile() error {
	re, err := regexp.Compile("(?i)" + cs.Pattern)
	if err != nil {
		return fmt.Errorf("crystal %s: invalid pattern %q: %w", cs.ID, cs.Pattern, err)
	}
	cs.pattern = re
	return nil
}

// Render executes the template for this crystal, extracting named capture groups
// from the query as template variables.
func (cs *CrystalSkill) Render(query string) string {
	vars := map[string]string{"query": query}
	if cs.pattern != nil {
		match := cs.pattern.FindStringSubmatch(query)
		names := cs.pattern.SubexpNames()
		for i, name := range names {
			if i > 0 && name != "" && i < len(match) {
				vars[name] = match[i]
			}
		}
	}
	if cs.TemplateFn != nil {
		return cs.TemplateFn(vars)
	}
	// Static template — do simple {{key}} substitution
	result := cs.TemplateBody
	for k, v := range vars {
		result = replaceAll(result, "{{"+k+"}}", v)
	}
	return result
}

// Eligible returns true if this skill has earned crystallization.
func (cs *CrystalSkill) Eligible() bool {
	return cs.ReputationScore >= CrystalThresholdReputation && cs.HitCount >= CrystalThresholdHits
}

// ---------------------------------------------------------------------------
// CrystalCache — thread-safe registry of active crystals
// ---------------------------------------------------------------------------

// CrystalCache holds all registered CrystalSkill entries and provides fast
// pattern-matching against incoming queries.
type CrystalCache struct {
	mu     sync.RWMutex
	skills map[string]*CrystalSkill // keyed by ID
	// ordered slice for deterministic match priority (highest reputation first)
	ordered []*CrystalSkill

	totalHits   int64
	totalMisses int64
	bypassedMs  float64 // cumulative latency saved (estimated)
}

// NewCrystalCache creates an empty CrystalCache.
func NewCrystalCache() *CrystalCache {
	return &CrystalCache{
		skills: make(map[string]*CrystalSkill),
	}
}

// Register adds or replaces a CrystalSkill in the cache.
// Returns an error if the pattern fails to compile.
func (cc *CrystalCache) Register(skill CrystalSkill) error {
	if err := skill.Compile(); err != nil {
		return err
	}
	if skill.CreatedAt.IsZero() {
		skill.CreatedAt = time.Now()
	}
	skill.Active = true

	cc.mu.Lock()
	defer cc.mu.Unlock()
	cc.skills[skill.ID] = &skill
	cc.rebuild()
	log.Printf("[Crystal] Registered skill %q pattern=%q rep=%.2f hits=%d",
		skill.ID, skill.Pattern, skill.ReputationScore, skill.HitCount)
	return nil
}

// Match scans all active crystals in reputation order.
// On a match it updates stats and returns the rendered response.
func (cc *CrystalCache) Match(query string) (response string, skillID string, hit bool) {
	cc.mu.RLock()
	candidates := cc.ordered // snapshot; safe for read
	cc.mu.RUnlock()

	start := time.Now()
	for _, cs := range candidates {
		if !cs.Active || cs.pattern == nil {
			continue
		}
		if cs.pattern.MatchString(query) {
			elapsed := float64(time.Since(start).Milliseconds())
			cc.mu.Lock()
			cs.HitCount++
			cs.LastHitAt = time.Now()
			cc.totalHits++
			// Assume Ollama would take ~800ms; we "saved" that minus our match time
			cc.bypassedMs += 800 - elapsed
			cc.mu.Unlock()
			return cs.Render(query), cs.ID, true
		}
	}
	cc.mu.Lock()
	cc.totalMisses++
	cc.mu.Unlock()
	return "", "", false
}

// MaybePromote checks whether a skill has crossed the crystallization threshold
// and activates it if so. skillID is the candidate; score is its latest rep score.
func (cc *CrystalCache) MaybePromote(skillID string, score float64, hitCount int) bool {
	cc.mu.Lock()
	defer cc.mu.Unlock()
	cs, ok := cc.skills[skillID]
	if !ok {
		return false
	}
	cs.ReputationScore = score
	cs.HitCount = hitCount
	if cs.Eligible() && !cs.Active {
		cs.Active = true
		cc.rebuild()
		log.Printf("[Crystal] PROMOTED skill %q — rep=%.2f hits=%d (LLM-bypass active)",
			skillID, score, hitCount)
		return true
	}
	return false
}

// Evict removes a crystal by ID. Returns false if not found.
func (cc *CrystalCache) Evict(id string) bool {
	cc.mu.Lock()
	defer cc.mu.Unlock()
	if _, ok := cc.skills[id]; !ok {
		return false
	}
	delete(cc.skills, id)
	cc.rebuild()
	log.Printf("[Crystal] Evicted skill %q", id)
	return true
}

// List returns a copy of all registered crystals sorted by reputation desc.
func (cc *CrystalCache) List() []CrystalSkill {
	cc.mu.RLock()
	defer cc.mu.RUnlock()
	out := make([]CrystalSkill, 0, len(cc.skills))
	for _, cs := range cc.skills {
		out = append(out, *cs)
	}
	sort.Slice(out, func(i, j int) bool {
		return out[i].ReputationScore > out[j].ReputationScore
	})
	return out
}

// Stats returns cache-level telemetry.
func (cc *CrystalCache) Stats() CrystalStats {
	cc.mu.RLock()
	defer cc.mu.RUnlock()
	total := cc.totalHits + cc.totalMisses
	hitRate := 0.0
	if total > 0 {
		hitRate = float64(cc.totalHits) / float64(total)
	}
	return CrystalStats{
		RegisteredSkills: len(cc.skills),
		ActiveSkills:     cc.countActive(),
		TotalHits:        cc.totalHits,
		TotalMisses:      cc.totalMisses,
		HitRate:          hitRate,
		EstimatedBypassMs: cc.bypassedMs,
	}
}

// ---------------------------------------------------------------------------
// CrystalStats
// ---------------------------------------------------------------------------

type CrystalStats struct {
	RegisteredSkills  int     `json:"registered_skills"`
	ActiveSkills      int     `json:"active_skills"`
	TotalHits         int64   `json:"total_hits"`
	TotalMisses       int64   `json:"total_misses"`
	HitRate           float64 `json:"hit_rate"`
	EstimatedBypassMs float64 `json:"estimated_bypass_ms"`
}

// ---------------------------------------------------------------------------
// internal helpers
// ---------------------------------------------------------------------------

// rebuild re-sorts cc.ordered by reputation desc. Must be called under write lock.
func (cc *CrystalCache) rebuild() {
	cc.ordered = make([]*CrystalSkill, 0, len(cc.skills))
	for _, cs := range cc.skills {
		cc.ordered = append(cc.ordered, cs)
	}
	sort.Slice(cc.ordered, func(i, j int) bool {
		return cc.ordered[i].ReputationScore > cc.ordered[j].ReputationScore
	})
}

func (cc *CrystalCache) countActive() int {
	n := 0
	for _, cs := range cc.skills {
		if cs.Active {
			n++
		}
	}
	return n
}

func replaceAll(s, old, new string) string {
	result := s
	for {
		i := indexOf(result, old)
		if i < 0 {
			break
		}
		result = result[:i] + new + result[i+len(old):]
	}
	return result
}

func indexOf(s, substr string) int {
	for i := 0; i <= len(s)-len(substr); i++ {
		if s[i:i+len(substr)] == substr {
			return i
		}
	}
	return -1
}

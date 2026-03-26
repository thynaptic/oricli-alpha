package service

import (
	"encoding/json"
	"log"
	"os"
	"path/filepath"
	"strings"
	"sync"
)

const (
	constitutionPath    = ".oricli/living_constitution.json"
	maxRulesPerCategory = 10
	maxInjectChars      = 300
)

// LivingConstitution is a dynamic behavioral spec derived from learned user preferences.
// It is updated by the DreamDaemon during idle consolidation and injected into every
// system prompt — acting as a continuously evolving behavioral layer without fine-tuning.
type LivingConstitution struct {
	StyleRules       []string `json:"style_rules"`        // how to format/tone responses
	TopicPreferences []string `json:"topic_preferences"`  // subjects the user values deeply
	BehavioralRules  []string `json:"behavioral_rules"`   // explicit always/never directives
	mu               sync.RWMutex
}

// NewLivingConstitution loads from disk or returns an empty constitution.
func NewLivingConstitution() *LivingConstitution {
	lc := &LivingConstitution{}
	if err := lc.Load(); err != nil {
		log.Printf("[LivingConstitution] No existing constitution found, starting fresh: %v", err)
	}
	return lc
}

// Load reads the constitution from disk.
func (lc *LivingConstitution) Load() error {
	lc.mu.Lock()
	defer lc.mu.Unlock()

	data, err := os.ReadFile(constitutionPath)
	if err != nil {
		return err
	}
	return json.Unmarshal(data, lc)
}

// Save persists the constitution to disk atomically.
func (lc *LivingConstitution) Save() error {
	lc.mu.RLock()
	data, err := json.MarshalIndent(lc, "", "  ")
	lc.mu.RUnlock()
	if err != nil {
		return err
	}

	if err := os.MkdirAll(filepath.Dir(constitutionPath), 0755); err != nil {
		return err
	}

	tmp := constitutionPath + ".tmp"
	if err := os.WriteFile(tmp, data, 0644); err != nil {
		return err
	}
	return os.Rename(tmp, constitutionPath)
}

// HasRules returns true if any rules have been learned.
func (lc *LivingConstitution) HasRules() bool {
	lc.mu.RLock()
	defer lc.mu.RUnlock()
	return len(lc.StyleRules) > 0 || len(lc.TopicPreferences) > 0 || len(lc.BehavioralRules) > 0
}

// Inject returns a compact string ≤ maxInjectChars suitable for system prompt injection.
// Returns empty string if no rules have been learned yet.
func (lc *LivingConstitution) Inject() string {
	lc.mu.RLock()
	defer lc.mu.RUnlock()

	if len(lc.BehavioralRules) == 0 && len(lc.StyleRules) == 0 && len(lc.TopicPreferences) == 0 {
		return ""
	}

	var sb strings.Builder
	sb.WriteString("### LEARNED PREFERENCES:\n")

	for _, r := range lc.BehavioralRules {
		line := "- " + r + "\n"
		if sb.Len()+len(line) > maxInjectChars {
			break
		}
		sb.WriteString(line)
	}
	for _, r := range lc.StyleRules {
		line := "- " + r + "\n"
		if sb.Len()+len(line) > maxInjectChars {
			break
		}
		sb.WriteString(line)
	}
	for _, r := range lc.TopicPreferences {
		line := "- " + r + "\n"
		if sb.Len()+len(line) > maxInjectChars {
			break
		}
		sb.WriteString(line)
	}

	result := strings.TrimRight(sb.String(), "\n")
	if len(result) > maxInjectChars {
		result = result[:maxInjectChars]
	}
	return result
}

// AddLesson adds a learned lesson to the appropriate rule category.
// Deduplicates fuzzy-similar rules and enforces the per-category cap.
func (lc *LivingConstitution) AddLesson(lesson, category string) {
	lc.mu.Lock()
	defer lc.mu.Unlock()

	lesson = strings.TrimSpace(lesson)
	if lesson == "" {
		return
	}

	switch category {
	case "style":
		lc.StyleRules = addUnique(lc.StyleRules, lesson, maxRulesPerCategory)
	case "topic":
		lc.TopicPreferences = addUnique(lc.TopicPreferences, lesson, maxRulesPerCategory)
	default: // "behavior" or anything else
		lc.BehavioralRules = addUnique(lc.BehavioralRules, lesson, maxRulesPerCategory)
	}
}

// MergeLessons bulk-adds lessons from the DreamDaemon consolidation pass.
func (lc *LivingConstitution) MergeLessons(behavioral, style, topic []string) {
	for _, l := range behavioral {
		lc.AddLesson(l, "behavior")
	}
	for _, l := range style {
		lc.AddLesson(l, "style")
	}
	for _, l := range topic {
		lc.AddLesson(l, "topic")
	}
}

// addUnique appends item only if no existing rule shares the first 30 chars (fuzzy dedup).
// Enforces cap by dropping the oldest entry when full.
func addUnique(rules []string, item string, cap int) []string {
	prefix := item
	if len(prefix) > 30 {
		prefix = strings.ToLower(prefix[:30])
	} else {
		prefix = strings.ToLower(prefix)
	}

	for _, r := range rules {
		rp := r
		if len(rp) > 30 {
			rp = strings.ToLower(rp[:30])
		} else {
			rp = strings.ToLower(rp)
		}
		if rp == prefix {
			return rules // already have a similar rule
		}
	}

	if len(rules) >= cap {
		rules = rules[1:] // evict oldest
	}
	return append(rules, item)
}

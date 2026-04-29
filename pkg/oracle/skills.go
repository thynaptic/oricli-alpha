package oracle

import (
	"encoding/json"
	"log"
	"os"
	"path/filepath"
	"strings"
	"sync"
	"time"
)

const defaultSkillDir = "oricli_core/skills"

type skillDef struct {
	Name        string
	Description string
	Triggers    []string
	Content     string // full <mindset>/<instructions>/<constraints> body
}

var (
	skillCache    []skillDef
	skillCacheMu  sync.RWMutex
	skillCacheAt  time.Time
	skillCacheTTL = 5 * time.Minute
)

// matchSkill returns the content block of the first skill whose triggers
// match the query, or empty string if none match.
func matchSkill(query string) string {
	skills := cachedLoadSkills()
	lower := strings.ToLower(query)
	for _, s := range skills {
		for _, trigger := range s.Triggers {
			if strings.Contains(lower, strings.ToLower(trigger)) {
				return s.Content
			}
		}
	}
	return ""
}

func cachedLoadSkills() []skillDef {
	skillCacheMu.RLock()
	if time.Since(skillCacheAt) < skillCacheTTL && skillCache != nil {
		cached := skillCache
		skillCacheMu.RUnlock()
		return cached
	}
	skillCacheMu.RUnlock()

	skills := loadSkills(defaultSkillDir)

	skillCacheMu.Lock()
	skillCache = skills
	skillCacheAt = time.Now()
	skillCacheMu.Unlock()
	return skills
}

func loadSkills(dir string) []skillDef {
	files, err := os.ReadDir(dir)
	if err != nil {
		return nil
	}

	var skills []skillDef
	for _, f := range files {
		if f.IsDir() || !strings.HasSuffix(f.Name(), ".ori") {
			continue
		}
		data, err := os.ReadFile(filepath.Join(dir, f.Name()))
		if err != nil {
			continue
		}
		if s := parseOriSkill(string(data)); s.Name != "" {
			skills = append(skills, s)
		}
	}
	log.Printf("[Oracle:Skills] loaded %d skills from %s", len(skills), dir)
	return skills
}

func parseOriSkill(raw string) skillDef {
	var s skillDef
	lines := strings.Split(raw, "\n")
	bodyStart := -1

	for i, line := range lines {
		t := strings.TrimSpace(line)
		switch {
		case strings.HasPrefix(t, "@skill_name:"):
			s.Name = strings.TrimSpace(strings.TrimPrefix(t, "@skill_name:"))
		case strings.HasPrefix(t, "@description:"):
			s.Description = strings.TrimSpace(strings.TrimPrefix(t, "@description:"))
		case strings.HasPrefix(t, "@triggers:"):
			raw := strings.TrimSpace(strings.TrimPrefix(t, "@triggers:"))
			var triggers []string
			if err := json.Unmarshal([]byte(raw), &triggers); err == nil {
				s.Triggers = triggers
			}
		case strings.HasPrefix(t, "<mindset>"):
			bodyStart = i
		}
		if bodyStart >= 0 {
			break
		}
	}

	if bodyStart >= 0 {
		s.Content = strings.TrimSpace(strings.Join(lines[bodyStart:], "\n"))
	}
	return s
}

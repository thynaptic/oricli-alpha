package skills

import (
	"encoding/json"
	"log"
	"os"
	"path/filepath"
	"strings"
	"sync"
	"time"
)

// Skill is one parsed .ori overlay.
type Skill struct {
	Name        string   `json:"name"`
	Description string   `json:"description"`
	Triggers    []string `json:"triggers"`
	Content     string   `json:"-"`
}

// Library loads .ori files from a mount directory (read-only).
type Library struct {
	dirs []string

	mu       sync.RWMutex
	skills   []Skill
	loadedAt time.Time
	ttl      time.Duration
}

// Open creates a library. Missing dirs are ignored (empty library).
func Open(dirs ...string) *Library {
	cleaned := make([]string, 0, len(dirs))
	for _, d := range dirs {
		d = strings.TrimSpace(d)
		if d != "" {
			cleaned = append(cleaned, d)
		}
	}
	return &Library{dirs: cleaned, ttl: 5 * time.Minute}
}

// Stats returns load info for health/info endpoints.
func (l *Library) Stats() map[string]any {
	if l == nil {
		return map[string]any{"enabled": false, "skills": 0}
	}
	skills := l.cached()
	return map[string]any{
		"enabled": len(l.dirs) > 0,
		"dirs":    l.dirs,
		"skills":  len(skills),
	}
}

// List returns skill metadata (no full content).
func (l *Library) List() []Skill {
	src := l.cached()
	out := make([]Skill, len(src))
	for i, s := range src {
		out[i] = Skill{Name: s.Name, Description: s.Description, Triggers: s.Triggers}
	}
	return out
}

// Match returns the first skill content whose triggers match the query.
func (l *Library) Match(query string) string {
	if l == nil || strings.TrimSpace(query) == "" {
		return ""
	}
	lower := strings.ToLower(query)
	for _, s := range l.cached() {
		for _, trigger := range s.Triggers {
			if trigger != "" && strings.Contains(lower, strings.ToLower(trigger)) {
				return formatSkillBlock(s)
			}
		}
	}
	return ""
}

func formatSkillBlock(s Skill) string {
	var b strings.Builder
	b.WriteString("### ORI SKILL OVERLAY: ")
	b.WriteString(s.Name)
	b.WriteString("\n")
	b.WriteString(s.Content)
	b.WriteString("\n### END ORI SKILL OVERLAY\n")
	return b.String()
}

func (l *Library) cached() []Skill {
	l.mu.RLock()
	if time.Since(l.loadedAt) < l.ttl && l.skills != nil {
		out := l.skills
		l.mu.RUnlock()
		return out
	}
	l.mu.RUnlock()

	skills := l.load()
	l.mu.Lock()
	l.skills = skills
	l.loadedAt = time.Now()
	l.mu.Unlock()
	return skills
}

func (l *Library) load() []Skill {
	var skills []Skill
	seen := map[string]bool{}
	for _, dir := range l.dirs {
		entries, err := os.ReadDir(dir)
		if err != nil {
			continue
		}
		for _, f := range entries {
			if f.IsDir() || !strings.HasSuffix(f.Name(), ".ori") {
				continue
			}
			data, err := os.ReadFile(filepath.Join(dir, f.Name()))
			if err != nil {
				continue
			}
			s := parseOriSkill(string(data))
			if s.Name == "" || seen[s.Name] {
				continue
			}
			seen[s.Name] = true
			skills = append(skills, s)
		}
	}
	if len(l.dirs) > 0 {
		log.Printf("[capsule:skills] loaded %d skills from %v", len(skills), l.dirs)
	}
	return skills
}

func parseOriSkill(raw string) Skill {
	var s Skill
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
			rawTrig := strings.TrimSpace(strings.TrimPrefix(t, "@triggers:"))
			var triggers []string
			if err := json.Unmarshal([]byte(rawTrig), &triggers); err == nil {
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

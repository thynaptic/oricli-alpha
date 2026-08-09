package agents

import (
	"log"
	"os"
	"path/filepath"
	"strings"
	"sync"
	"time"
)

// Agent is one parsed .agent.md profile.
type Agent struct {
	Name        string   `json:"name"`
	Description string   `json:"description"`
	Tools       []string `json:"tools,omitempty"`
	Prompt      string   `json:"-"`
}

// Library loads agent profiles from mount directories (read-only).
type Library struct {
	dirs []string

	mu       sync.RWMutex
	agents   []Agent
	loadedAt time.Time
	ttl      time.Duration
}

// Open creates a library. Missing dirs are ignored.
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

func (l *Library) Stats() map[string]any {
	if l == nil {
		return map[string]any{"enabled": false, "agents": 0}
	}
	agents := l.cached()
	return map[string]any{
		"enabled": len(l.dirs) > 0,
		"dirs":    l.dirs,
		"agents":  len(agents),
	}
}

// List returns agent metadata without full prompts.
func (l *Library) List() []Agent {
	src := l.cached()
	out := make([]Agent, len(src))
	for i, a := range src {
		out[i] = Agent{Name: a.Name, Description: a.Description, Tools: a.Tools}
	}
	return out
}

// Get returns an agent by name (case-insensitive).
func (l *Library) Get(name string) (Agent, bool) {
	name = strings.TrimSpace(strings.ToLower(name))
	if name == "" || l == nil {
		return Agent{}, false
	}
	for _, a := range l.cached() {
		if strings.ToLower(a.Name) == name {
			return a, true
		}
	}
	return Agent{}, false
}

// Resolve picks an agent: explicit name wins, else default ori-chat-fast if present.
func (l *Library) Resolve(explicit string) (Agent, bool) {
	if a, ok := l.Get(explicit); ok {
		return a, true
	}
	if explicit != "" {
		return Agent{}, false
	}
	return l.Get("ori-chat-fast")
}

// PromptBlock formats the agent system prompt for chat inject.
func PromptBlock(a Agent) string {
	if strings.TrimSpace(a.Prompt) == "" {
		return ""
	}
	var b strings.Builder
	b.WriteString("### ORI AGENT PROFILE: ")
	b.WriteString(a.Name)
	b.WriteString("\n")
	b.WriteString(a.Prompt)
	b.WriteString("\n### END ORI AGENT PROFILE\n")
	return b.String()
}

func (l *Library) cached() []Agent {
	l.mu.RLock()
	if time.Since(l.loadedAt) < l.ttl && l.agents != nil {
		out := l.agents
		l.mu.RUnlock()
		return out
	}
	l.mu.RUnlock()

	agents := l.load()
	l.mu.Lock()
	l.agents = agents
	l.loadedAt = time.Now()
	l.mu.Unlock()
	return agents
}

func (l *Library) load() []Agent {
	var agents []Agent
	seen := map[string]bool{}
	for _, dir := range l.dirs {
		entries, err := os.ReadDir(dir)
		if err != nil {
			continue
		}
		for _, f := range entries {
			if f.IsDir() || !strings.HasSuffix(f.Name(), ".agent.md") {
				continue
			}
			data, err := os.ReadFile(filepath.Join(dir, f.Name()))
			if err != nil {
				continue
			}
			a := parseAgentMD(string(data))
			if a.Name == "" || seen[a.Name] {
				continue
			}
			seen[a.Name] = true
			agents = append(agents, a)
		}
	}
	if len(l.dirs) > 0 {
		log.Printf("[capsule:agents] loaded %d agents from %v", len(agents), l.dirs)
	}
	return agents
}

func parseAgentMD(raw string) Agent {
	parts := strings.SplitN(raw, "---", 3)
	var a Agent
	if len(parts) < 3 {
		// No frontmatter — treat whole file as prompt, name from first heading-ish line.
		a.Prompt = strings.TrimSpace(raw)
		return a
	}
	fm := parts[1]
	a.Prompt = strings.TrimSpace(parts[2])
	inTools := false
	for _, line := range strings.Split(fm, "\n") {
		t := strings.TrimSpace(line)
		if t == "" {
			continue
		}
		if strings.HasPrefix(t, "tools:") {
			inTools = true
			rest := strings.TrimSpace(strings.TrimPrefix(t, "tools:"))
			if rest != "" && rest != "[]" {
				inTools = false
			}
			continue
		}
		if inTools {
			if strings.HasPrefix(t, "- ") {
				a.Tools = append(a.Tools, strings.TrimSpace(strings.TrimPrefix(t, "- ")))
				continue
			}
			if !strings.HasPrefix(t, " ") && strings.Contains(t, ":") {
				inTools = false
			} else {
				continue
			}
		}
		switch {
		case strings.HasPrefix(t, "name:"):
			a.Name = unquote(strings.TrimSpace(strings.TrimPrefix(t, "name:")))
		case strings.HasPrefix(t, "description:"):
			a.Description = unquote(strings.TrimSpace(strings.TrimPrefix(t, "description:")))
		}
	}
	return a
}

func unquote(s string) string {
	s = strings.TrimSpace(s)
	if len(s) >= 2 {
		if (s[0] == '"' && s[len(s)-1] == '"') || (s[0] == '\'' && s[len(s)-1] == '\'') {
			return s[1 : len(s)-1]
		}
	}
	return s
}

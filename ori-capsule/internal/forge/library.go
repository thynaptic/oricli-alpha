package forge

import (
	"fmt"
	"sort"
	"strings"
	"sync"
	"time"
)

// JITTool is an ephemeral in-memory tool (no PocketBase).
type JITTool struct {
	Name        string         `json:"name"`
	Description string         `json:"description"`
	Kind        string         `json:"kind"` // yaegi | script
	Source      string         `json:"source"`
	Parameters  map[string]any `json:"parameters,omitempty"`
	CreatedAt   time.Time      `json:"created_at"`
	ExpiresAt   time.Time      `json:"expires_at"`
	LastUsed    time.Time      `json:"last_used"`
	UseCount    int            `json:"use_count"`
	ModelUsed   string         `json:"model_used,omitempty"`
}

// MemoryLibrary is a docker-friendly LRU+TTL store for JIT tools.
type MemoryLibrary struct {
	mu     sync.Mutex
	max    int
	ttl    time.Duration
	byName map[string]*JITTool
}

func NewMemoryLibrary(max int, ttl time.Duration) *MemoryLibrary {
	if max <= 0 {
		max = 16
	}
	if ttl <= 0 {
		ttl = 30 * time.Minute
	}
	return &MemoryLibrary{
		max:    max,
		ttl:    ttl,
		byName: make(map[string]*JITTool),
	}
}

func (l *MemoryLibrary) Stats() map[string]any {
	if l == nil {
		return map[string]any{"enabled": false}
	}
	l.mu.Lock()
	defer l.mu.Unlock()
	l.evictExpiredLocked()
	return map[string]any{
		"enabled": true,
		"count":   len(l.byName),
		"max":     l.max,
		"ttl_min": int(l.ttl.Minutes()),
	}
}

// Put verifies source then stores (LRU eviction when over max).
func (l *MemoryLibrary) Put(tool JITTool) (JITTool, error) {
	if l == nil {
		return JITTool{}, fmt.Errorf("library disabled")
	}
	name := sanitizeToolName(tool.Name)
	if name == "" {
		return JITTool{}, fmt.Errorf("name required")
	}
	tool.Name = name
	if tool.Kind == "" {
		tool.Kind = "yaegi"
	}
	kind := strings.ToLower(tool.Kind)
	if kind != "yaegi" && kind != "script" {
		return JITTool{}, fmt.Errorf("kind must be yaegi or script")
	}
	tool.Kind = kind
	if strings.TrimSpace(tool.Source) == "" {
		return JITTool{}, fmt.Errorf("source required")
	}

	// Fatal sandbox constitution only — capsule GOSH is not the monorepo bash JIT contract.
	vr := VerifyStatic(VerifyRequest{
		Script: pick(tool.Kind == "script", tool.Source, ""),
		Source: pick(tool.Kind == "yaegi", tool.Source, ""),
	})
	if !vr.OK {
		return JITTool{}, fmt.Errorf("constitution: %s", vr.Summary)
	}

	now := time.Now().UTC()
	if tool.CreatedAt.IsZero() {
		tool.CreatedAt = now
	}
	tool.ExpiresAt = now.Add(l.ttl)
	tool.LastUsed = now

	l.mu.Lock()
	defer l.mu.Unlock()
	l.evictExpiredLocked()
	l.byName[name] = &tool
	l.evictLRULocked()
	return tool, nil
}

func (l *MemoryLibrary) Get(name string) (JITTool, bool) {
	if l == nil {
		return JITTool{}, false
	}
	l.mu.Lock()
	defer l.mu.Unlock()
	l.evictExpiredLocked()
	t, ok := l.byName[sanitizeToolName(name)]
	if !ok {
		return JITTool{}, false
	}
	if time.Now().UTC().After(t.ExpiresAt) {
		delete(l.byName, t.Name)
		return JITTool{}, false
	}
	t.LastUsed = time.Now().UTC()
	t.UseCount++
	cp := *t
	return cp, true
}

func (l *MemoryLibrary) List() []JITTool {
	if l == nil {
		return nil
	}
	l.mu.Lock()
	defer l.mu.Unlock()
	l.evictExpiredLocked()
	out := make([]JITTool, 0, len(l.byName))
	for _, t := range l.byName {
		out = append(out, *t)
	}
	sort.Slice(out, func(i, j int) bool {
		return out[i].LastUsed.After(out[j].LastUsed)
	})
	return out
}

func (l *MemoryLibrary) Delete(name string) bool {
	if l == nil {
		return false
	}
	l.mu.Lock()
	defer l.mu.Unlock()
	name = sanitizeToolName(name)
	if _, ok := l.byName[name]; !ok {
		return false
	}
	delete(l.byName, name)
	return true
}

func (l *MemoryLibrary) evictExpiredLocked() {
	now := time.Now().UTC()
	for k, t := range l.byName {
		if now.After(t.ExpiresAt) {
			delete(l.byName, k)
		}
	}
}

func (l *MemoryLibrary) evictLRULocked() {
	for len(l.byName) > l.max {
		var oldest string
		var oldestT time.Time
		first := true
		for k, t := range l.byName {
			if first || t.LastUsed.Before(oldestT) {
				oldest = k
				oldestT = t.LastUsed
				first = false
			}
		}
		if oldest == "" {
			break
		}
		delete(l.byName, oldest)
	}
}

func sanitizeToolName(name string) string {
	name = strings.ToLower(strings.TrimSpace(name))
	var b strings.Builder
	for _, r := range name {
		if (r >= 'a' && r <= 'z') || (r >= '0' && r <= '9') || r == '_' {
			b.WriteRune(r)
		} else if r == '-' || r == ' ' {
			b.WriteByte('_')
		}
	}
	out := b.String()
	if len(out) > 48 {
		out = out[:48]
	}
	return out
}

func pick(cond bool, a, b string) string {
	if cond {
		return a
	}
	return b
}

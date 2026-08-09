package memory

import (
	"crypto/sha256"
	"encoding/hex"
	"encoding/json"
	"os"
	"path/filepath"
	"strings"
	"sync"
	"time"
	"unicode"
)

const (
	l1Max      = 500
	l1TTL      = 7 * 24 * time.Hour
	l1MinQuery = 30
)

type cacheEntry struct {
	Query    string    `json:"query"`
	Response string    `json:"response"`
	CachedAt time.Time `json:"cached_at"`
}

// ResponseCache is L1 exact-hash only (no chromem / embed — zero sync latency).
type ResponseCache struct {
	mu     sync.RWMutex
	entries map[string]cacheEntry
	path   string
}

func NewResponseCache(dir string) *ResponseCache {
	_ = os.MkdirAll(dir, 0o755)
	c := &ResponseCache{
		entries: make(map[string]cacheEntry),
		path:    filepath.Join(dir, "l1_cache.json"),
	}
	c.load()
	return c
}

func normalizeQuery(q string) string {
	var b strings.Builder
	prevSpace := false
	for _, r := range strings.ToLower(strings.TrimSpace(q)) {
		if unicode.IsSpace(r) {
			if !prevSpace {
				b.WriteByte(' ')
				prevSpace = true
			}
			continue
		}
		prevSpace = false
		if unicode.IsLetter(r) || unicode.IsDigit(r) || r == '\'' {
			b.WriteRune(r)
		}
	}
	return b.String()
}

func hashQuery(q string) string {
	sum := sha256.Sum256([]byte(normalizeQuery(q)))
	return hex.EncodeToString(sum[:])
}

func (c *ResponseCache) Get(query string) (string, bool) {
	if len(normalizeQuery(query)) < l1MinQuery {
		return "", false
	}
	key := hashQuery(query)
	c.mu.RLock()
	e, ok := c.entries[key]
	c.mu.RUnlock()
	if !ok {
		return "", false
	}
	if time.Since(e.CachedAt) > l1TTL {
		return "", false
	}
	return e.Response, true
}

func (c *ResponseCache) PutAsync(query, response string) {
	if len(normalizeQuery(query)) < l1MinQuery || response == "" {
		return
	}
	go func() {
		key := hashQuery(query)
		c.mu.Lock()
		c.entries[key] = cacheEntry{Query: query, Response: response, CachedAt: time.Now()}
		if len(c.entries) > l1Max {
			// drop arbitrary oldest-ish: first key
			for k := range c.entries {
				delete(c.entries, k)
				break
			}
		}
		snap := make(map[string]cacheEntry, len(c.entries))
		for k, v := range c.entries {
			snap[k] = v
		}
		c.mu.Unlock()
		data, err := json.Marshal(snap)
		if err != nil {
			return
		}
		_ = os.WriteFile(c.path, data, 0o600)
	}()
}

func (c *ResponseCache) load() {
	data, err := os.ReadFile(c.path)
	if err != nil {
		return
	}
	var m map[string]cacheEntry
	if json.Unmarshal(data, &m) == nil {
		c.entries = m
	}
}

// Package cache provides a two-tier semantic response cache for ORI.
//
// L1 — exact normalized hash: zero-latency, persisted to disk.
// L2 — chromem-go cosine similarity: catches paraphrased repeats,
//
//	only activated when the chat model is not currently generating.
//
// The LLM is never called for a cache hit — this is the primary goal.
package cache

import (
	"context"
	"crypto/sha256"
	"encoding/json"
	"fmt"
	"log"
	"os"
	"path/filepath"
	"strings"
	"sync"
	"time"
	"unicode"

	chromem "github.com/philippgille/chromem-go"
	"github.com/thynaptic/oricli-go/pkg/service"
)

const (
	// defaultThreshold is the minimum cosine similarity for an L2 cache hit.
	// 0.92 = very high similarity — avoids false positives on topic-adjacent queries.
	defaultThreshold = 0.92

	// defaultMaxL1 is the max number of L1 in-memory entries before LRU eviction.
	defaultMaxL1 = 500

	// defaultTTL is how long a cached response stays valid.
	defaultTTL = 7 * 24 * time.Hour

	// minQueryLen is the minimum normalized query length to cache.
	// Short queries ("hi", "yes", "what?") are context-dependent and shouldn't be cached.
	minQueryLen = 30

	// l2Timeout is the max time allowed for an L2 vector lookup.
	l2Timeout = 300 * time.Millisecond

	// l2PutTimeout is the max time allowed to store a vector in L2.
	l2PutTimeout = 5 * time.Second

	// maxStoredResponseLen is the max response chars stored in chromem metadata.
	maxStoredResponseLen = 4096
)

type cacheEntry struct {
	Query    string    `json:"query"`
	Response string    `json:"response"`
	CachedAt time.Time `json:"cached_at"`
	HitCount int       `json:"hit_count"`
}

// ResponseCache is a two-tier semantic response cache. Safe for concurrent use.
type ResponseCache struct {
	// L1 — exact normalized hash
	l1     map[string]cacheEntry
	l1mu   sync.RWMutex
	l1Max  int
	l1Path string

	// L2 — chromem-go vector similarity
	db        *chromem.DB
	col       *chromem.Collection
	embedder  *service.Embedder
	threshold float64
	l2mu      sync.Mutex

	ttl time.Duration
}

// New initializes a ResponseCache backed by persistDir.
// embedder may be nil — in that case L2 is disabled and only L1 (exact hash) runs.
func New(persistDir string, embedder *service.Embedder) *ResponseCache {
	if err := os.MkdirAll(persistDir, 0700); err != nil {
		log.Printf("[ResponseCache] mkdir error: %v", err)
	}

	rc := &ResponseCache{
		l1:        make(map[string]cacheEntry),
		l1Max:     defaultMaxL1,
		l1Path:    filepath.Join(persistDir, "response_cache_l1.json"),
		embedder:  embedder,
		threshold: defaultThreshold,
		ttl:       defaultTTL,
	}
	rc.loadL1()

	if embedder != nil {
		db, err := chromem.NewPersistentDB(filepath.Join(persistDir, "cache_vectors"), true)
		if err != nil {
			log.Printf("[ResponseCache] chromem init error: %v — L2 disabled", err)
		} else {
			col, err := db.GetOrCreateCollection("response_cache", nil, nil)
			if err != nil {
				log.Printf("[ResponseCache] collection error: %v — L2 disabled", err)
			} else {
				rc.db = db
				rc.col = col
			}
		}
	}

	l2State := "disabled"
	if rc.col != nil {
		l2State = fmt.Sprintf("enabled (%d entries)", rc.col.Count())
	}
	log.Printf("[ResponseCache] Ready — L1: %d entries, L2: %s", len(rc.l1), l2State)
	return rc
}

// Get returns the cached response for a query, or ("", false) on miss.
// L1 is always checked. L2 is checked only when the chat model is idle.
func (rc *ResponseCache) Get(ctx context.Context, query string) (string, bool) {
	norm := rc.normalizeQuery(query)
	if len(norm) < minQueryLen {
		return "", false
	}
	key := rc.hashKey(norm)

	// ── L1: exact hash ────────────────────────────────────────────────────────
	rc.l1mu.RLock()
	entry, ok := rc.l1[key]
	rc.l1mu.RUnlock()
	if ok && time.Since(entry.CachedAt) < rc.ttl {
		rc.bumpHitCount(key)
		log.Printf("[Cache] L1 HIT (%.8s…): %.60s", key, query)
		return entry.Response, true
	}

	// ── L2: semantic similarity ───────────────────────────────────────────────
	// Only run when the embedder is available AND the chat model isn't generating
	// (to avoid evicting qwen from Ollama's single memory slot).
	if rc.col != nil && rc.embedder != nil && service.IsChatModelIdle() {
		l2Ctx, cancel := context.WithTimeout(ctx, l2Timeout)
		defer cancel()
		if resp, hit := rc.l2Get(l2Ctx, norm); hit {
			rc.l1Put(key, norm, resp) // promote to L1
			log.Printf("[Cache] L2 HIT: %.60s", query)
			return resp, true
		}
	}

	return "", false
}

// Put stores query → response in both cache tiers.
// Called asynchronously after stream completes — never blocks the response path.
// Skips short/error responses and context-dependent queries.
func (rc *ResponseCache) Put(query, response string) {
	if len(strings.TrimSpace(response)) < 80 {
		return
	}
	if strings.Contains(response, "[Error:") || strings.Contains(response, "[error:") {
		return
	}
	norm := rc.normalizeQuery(query)
	if len(norm) < minQueryLen {
		return
	}
	key := rc.hashKey(norm)

	go func() {
		rc.l1Put(key, norm, response)
		if rc.col != nil && rc.embedder != nil {
			ctx, cancel := context.WithTimeout(context.Background(), l2PutTimeout)
			defer cancel()
			rc.l2Put(ctx, key, norm, response)
		}
	}()
}

// Stats returns a snapshot of cache state for observability.
func (rc *ResponseCache) Stats() map[string]interface{} {
	rc.l1mu.RLock()
	l1Size := len(rc.l1)
	rc.l1mu.RUnlock()

	l2Size := 0
	if rc.col != nil {
		l2Size = rc.col.Count()
	}
	return map[string]interface{}{
		"l1_entries": l1Size,
		"l2_entries": l2Size,
		"l2_enabled": rc.col != nil,
		"threshold":  rc.threshold,
		"ttl_hours":  rc.ttl.Hours(),
	}
}

// ── internals ─────────────────────────────────────────────────────────────────

func (rc *ResponseCache) l1Put(key, normQuery, response string) {
	rc.l1mu.Lock()
	defer rc.l1mu.Unlock()
	if len(rc.l1) >= rc.l1Max {
		rc.evictOldestL1Locked()
	}
	rc.l1[key] = cacheEntry{
		Query:    normQuery,
		Response: response,
		CachedAt: time.Now(),
	}
	rc.persistL1Locked()
}

func (rc *ResponseCache) l2Get(ctx context.Context, normQuery string) (string, bool) {
	rc.l2mu.Lock()
	defer rc.l2mu.Unlock()
	if rc.col == nil || rc.col.Count() == 0 {
		return "", false
	}
	results, err := rc.col.Query(ctx, normQuery, 1, nil, nil)
	if err != nil || len(results) == 0 {
		return "", false
	}
	best := results[0]
	if float64(best.Similarity) < rc.threshold {
		return "", false
	}
	// TTL check via stored metadata
	if ts, ok := best.Metadata["cached_at"]; ok {
		t, err := time.Parse(time.RFC3339, ts)
		if err == nil && time.Since(t) > rc.ttl {
			return "", false
		}
	}
	resp := best.Metadata["response"]
	if resp == "" {
		return "", false
	}
	return resp, true
}

func (rc *ResponseCache) l2Put(ctx context.Context, key, normQuery, response string) {
	rc.l2mu.Lock()
	defer rc.l2mu.Unlock()
	if rc.col == nil {
		return
	}
	stored := response
	if len(stored) > maxStoredResponseLen {
		stored = stored[:maxStoredResponseLen]
	}
	err := rc.col.AddDocument(ctx, chromem.Document{
		ID:      key,
		Content: normQuery,
		Metadata: map[string]string{
			"response":  stored,
			"cached_at": time.Now().Format(time.RFC3339),
		},
	})
	if err != nil {
		log.Printf("[Cache] L2 put error: %v", err)
	}
}

func (rc *ResponseCache) bumpHitCount(key string) {
	rc.l1mu.Lock()
	defer rc.l1mu.Unlock()
	if e, ok := rc.l1[key]; ok {
		e.HitCount++
		rc.l1[key] = e
	}
}

func (rc *ResponseCache) evictOldestL1Locked() {
	var oldestKey string
	var oldestTime time.Time
	for k, v := range rc.l1 {
		if oldestTime.IsZero() || v.CachedAt.Before(oldestTime) {
			oldestKey = k
			oldestTime = v.CachedAt
		}
	}
	if oldestKey != "" {
		delete(rc.l1, oldestKey)
	}
}

func (rc *ResponseCache) loadL1() {
	data, err := os.ReadFile(rc.l1Path)
	if err != nil {
		return
	}
	var entries map[string]cacheEntry
	if err := json.Unmarshal(data, &entries); err != nil {
		return
	}
	loaded := 0
	for k, v := range entries {
		if time.Since(v.CachedAt) < rc.ttl {
			rc.l1[k] = v
			loaded++
		}
	}
	log.Printf("[ResponseCache] Loaded %d valid L1 entries from disk", loaded)
}

func (rc *ResponseCache) persistL1Locked() {
	data, err := json.Marshal(rc.l1)
	if err != nil {
		return
	}
	_ = os.WriteFile(rc.l1Path, data, 0600)
}

// normalizeQuery lowercases, strips punctuation (keeping spaces), and
// collapses whitespace — producing a canonical form for hashing.
func (rc *ResponseCache) normalizeQuery(q string) string {
	var sb strings.Builder
	prevSpace := false
	for _, r := range strings.ToLower(q) {
		if unicode.IsLetter(r) || unicode.IsDigit(r) {
			sb.WriteRune(r)
			prevSpace = false
		} else if !prevSpace {
			sb.WriteRune(' ')
			prevSpace = true
		}
	}
	return strings.TrimSpace(sb.String())
}

// hashKey returns a 16-char hex SHA-256 prefix of the normalized query.
func (rc *ResponseCache) hashKey(normalized string) string {
	h := sha256.Sum256([]byte(normalized))
	return fmt.Sprintf("%x", h[:8])
}

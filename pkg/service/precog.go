package service

import (
	"log"
	"regexp"
	"strings"
	"sync"
	"time"
)

type PrecogEntry struct {
	Response      map[string]interface{}
	Timestamp     time.Time
	OriginalQuery string
}

type PrecogService struct {
	cache      map[string]PrecogEntry
	mu         sync.RWMutex
	ttlSeconds int
}

func NewPrecogService(ttl int) *PrecogService {
	if ttl == 0 {
		ttl = 600
	}
	return &PrecogService{
		cache:      make(map[string]PrecogEntry),
		ttlSeconds: ttl,
	}
}

func (s *PrecogService) CacheResponse(query string, response map[string]interface{}) {
	s.mu.Lock()
	defer s.mu.Unlock()

	key := s.normalizeQuery(query)
	s.cache[key] = PrecogEntry{
		Response:      response,
		Timestamp:     time.Now(),
		OriginalQuery: query,
	}
}

func (s *PrecogService) GetResponse(query string) (map[string]interface{}, bool) {
	s.mu.Lock() // Using full lock to allow cleanup
	defer s.mu.Unlock()

	s.cleanupExpired()

	key := s.normalizeQuery(query)
	
	// 1. Exact match
	if entry, ok := s.cache[key]; ok {
		log.Printf("[Pre-Cog] Cache HIT (Exact): %s", query)
		return entry.Response, true
	}

	// 2. Fuzzy match
	for cacheKey, entry := range s.cache {
		if s.isSimilar(key, cacheKey) {
			log.Printf("[Pre-Cog] Cache HIT (Fuzzy): %s matched '%s'", query, entry.OriginalQuery)
			return entry.Response, true
		}
	}

	return nil, false
}

func (s *PrecogService) normalizeQuery(query string) string {
	re := regexp.MustCompile(`[^a-z0-9\s]`)
	normalized := strings.ToLower(query)
	normalized = re.ReplaceAllString(normalized, "")
	return strings.TrimSpace(normalized)
}

func (s *PrecogService) isSimilar(q1, q2 string) bool {
	words1 := strings.Fields(q1)
	words2 := strings.Fields(q2)
	if len(words1) == 0 || len(words2) == 0 {
		return false
	}

	set1 := make(map[string]bool)
	for _, w := range words1 {
		set1[w] = true
	}

	set2 := make(map[string]bool)
	for _, w := range words2 {
		set2[w] = true
	}

	intersection := 0
	for w := range set1 {
		if set2[w] {
			intersection++
		}
	}

	union := len(set1) + len(set2) - intersection
	jaccard := float64(intersection) / float64(union)

	if jaccard > 0.5 {
		return true
	}

	// Keyword fallback
	stopwords := map[string]bool{
		"how": true, "do": true, "i": true, "is": true, "a": true,
		"the": true, "what": true, "can": true, "you": true, "me": true, "to": true,
	}

	kw1 := make(map[string]bool)
	for w := range set1 {
		if !stopwords[w] {
			kw1[w] = true
		}
	}

	kw2 := make(map[string]bool)
	for w := range set2 {
		if !stopwords[w] {
			kw2[w] = true
		}
	}

	if len(kw1) > 0 && len(kw2) > 0 && len(kw1) == len(kw2) {
		match := true
		for w := range kw1 {
			if !kw2[w] {
				match = false
				break
			}
		}
		return match
	}

	return false
}

func (s *PrecogService) cleanupExpired() {
	now := time.Now()
	for k, v := range s.cache {
		if now.Sub(v.Timestamp).Seconds() > float64(s.ttlSeconds) {
			delete(s.cache, k)
		}
	}
}

func (s *PrecogService) Clear() {
	s.mu.Lock()
	defer s.mu.Unlock()
	s.cache = make(map[string]PrecogEntry)
}

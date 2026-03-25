package cognition

import (
	"encoding/json"
	"log"
	"os"
	"path/filepath"
	"strings"
	"sync"
)

// Constitution is the parsed source_constitution.json.
// It is loaded once at startup and cached for the process lifetime.
type Constitution struct {
	Version string `json:"version"`

	IngestionRules struct {
		MinSnippetLength      int      `json:"min_snippet_length"`
		MinTitleLength        int      `json:"min_title_length"`
		MaxSnippetLength      int      `json:"max_snippet_length"`
		RequireURL            bool     `json:"require_url"`
		BlockPaywalledSignals []string `json:"block_paywalled_signals"`
		BlockContentSignals   []string `json:"block_content_signals"`
		MinCombinedScore      float64  `json:"min_combined_score"`
		BorderlineMin         float64  `json:"borderline_min"`
		BorderlineMax         float64  `json:"borderline_max"`
		RelevanceWeight       float64  `json:"relevance_weight"`
		TrustWeight           float64  `json:"trust_weight"`
	} `json:"ingestion_rules"`

	TrustTiers map[string]struct {
		Score   float64  `json:"score"`
		Label   string   `json:"label"`
		Domains []string `json:"domains"`
	} `json:"trust_tiers"`

	TLDScores map[string]float64 `json:"tld_scores"`
	DefaultScore float64         `json:"default_score"`

	HardBlockedDomains     []string `json:"hard_blocked_domains"`
	HardBlockedURLPatterns []string `json:"hard_blocked_url_patterns"`

	// built index for O(1) lookups — populated by load()
	domainIndex       map[string]float64
	hardBlockedIndex  map[string]bool
}

var (
	constitutionOnce sync.Once
	globalConstitution *Constitution
)

// LoadConstitution returns the singleton Constitution, loading from disk on
// first call. Searches for source_constitution.json relative to the binary's
// working directory and common project roots.
func LoadConstitution() *Constitution {
	constitutionOnce.Do(func() {
		c, err := loadConstitutionFromDisk()
		if err != nil {
			log.Printf("[Constitution] WARNING: could not load source_constitution.json (%v) — using hardcoded defaults", err)
			c = defaultConstitution()
		}
		c.buildIndex()
		globalConstitution = c
	})
	return globalConstitution
}

// DomainScore returns the trust score for a given hostname.
// The hostname should already be lowercased and stripped of "www.".
func (c *Constitution) DomainScore(host string) float64 {
	// Hard block → absolute zero
	if c.hardBlockedIndex[host] {
		return 0.0
	}
	// Exact + suffix match from built index
	if score, ok := c.domainIndex[host]; ok {
		return score
	}
	for domain, score := range c.domainIndex {
		if strings.HasSuffix(host, "."+domain) {
			return score
		}
	}
	// TLD fallback
	for tld, score := range c.TLDScores {
		if strings.HasSuffix(host, tld) {
			return score
		}
	}
	if c.DefaultScore > 0 {
		return c.DefaultScore
	}
	return 0.50
}

// IsHardBlocked returns true for domains/URL patterns that must never be ingested.
func (c *Constitution) IsHardBlocked(host, rawURL string) bool {
	if c.hardBlockedIndex[host] {
		return true
	}
	lower := strings.ToLower(rawURL)
	for _, pat := range c.HardBlockedURLPatterns {
		if strings.Contains(lower, pat) {
			return true
		}
	}
	return false
}

// PassesIngestionRules checks snippet/title length and paywall/block signals.
func (c *Constitution) PassesIngestionRules(title, snippet, rawURL string) (bool, string) {
	rules := c.IngestionRules

	if rules.RequireURL && rawURL == "" {
		return false, "missing URL"
	}
	if len(title) < rules.MinTitleLength {
		return false, "title too short"
	}
	if len(snippet) < rules.MinSnippetLength {
		return false, "snippet too short"
	}
	if rules.MaxSnippetLength > 0 && len(snippet) > rules.MaxSnippetLength {
		snippet = snippet[:rules.MaxSnippetLength]
	}
	lower := strings.ToLower(snippet)
	for _, sig := range rules.BlockPaywalledSignals {
		if strings.Contains(lower, strings.ToLower(sig)) {
			return false, "paywall signal: " + sig
		}
	}
	for _, sig := range rules.BlockContentSignals {
		if strings.Contains(lower, strings.ToLower(sig)) {
			return false, "block signal: " + sig
		}
	}
	return true, ""
}

// Weights returns the relevance and trust weights for combined scoring.
func (c *Constitution) Weights() (relevance, trust float64) {
	r := c.IngestionRules.RelevanceWeight
	t := c.IngestionRules.TrustWeight
	if r+t == 0 {
		return 0.55, 0.45
	}
	return r, t
}

// Threshold returns the minimum combined score required to pass.
func (c *Constitution) Threshold() float64 {
	if c.IngestionRules.MinCombinedScore > 0 {
		return c.IngestionRules.MinCombinedScore
	}
	return 0.30
}

// BorderlineRange returns the score range that triggers an LLM gate check.
func (c *Constitution) BorderlineRange() (min, max float64) {
	return c.IngestionRules.BorderlineMin, c.IngestionRules.BorderlineMax
}

// ── internals ─────────────────────────────────────────────────────────────────

func (c *Constitution) buildIndex() {
	c.domainIndex = make(map[string]float64)
	for _, tier := range c.TrustTiers {
		for _, d := range tier.Domains {
			c.domainIndex[strings.ToLower(d)] = tier.Score
		}
	}
	c.hardBlockedIndex = make(map[string]bool)
	for _, d := range c.HardBlockedDomains {
		c.hardBlockedIndex[strings.ToLower(d)] = true
	}
}

func loadConstitutionFromDisk() (*Constitution, error) {
	candidates := []string{
		"data/source_constitution.json",
		"../data/source_constitution.json",
		"../../data/source_constitution.json",
	}
	// Also try relative to executable
	if exe, err := os.Executable(); err == nil {
		base := filepath.Dir(exe)
		candidates = append(candidates,
			filepath.Join(base, "data/source_constitution.json"),
			filepath.Join(base, "../data/source_constitution.json"),
		)
	}
	for _, path := range candidates {
		data, err := os.ReadFile(path)
		if err != nil {
			continue
		}
		var c Constitution
		if err := json.Unmarshal(data, &c); err != nil {
			return nil, err
		}
		log.Printf("[Constitution] Loaded from %s (v%s)", path, c.Version)
		return &c, nil
	}
	return nil, os.ErrNotExist
}

// defaultConstitution provides safe hardcoded fallback when the file is absent.
func defaultConstitution() *Constitution {
	c := &Constitution{
		Version:      "fallback",
		DefaultScore: 0.50,
		TLDScores:    map[string]float64{".edu": 0.88, ".gov": 0.90, ".org": 0.65},
		TrustTiers: map[string]struct {
			Score   float64  `json:"score"`
			Label   string   `json:"label"`
			Domains []string `json:"domains"`
		}{
			"tier1": {Score: 0.95, Domains: []string{"arxiv.org", "ncbi.nlm.nih.gov", "nature.com", "ieee.org", "who.int"}},
			"tier2": {Score: 0.80, Domains: []string{"reuters.com", "bbc.com", "wikipedia.org", "github.com", "stackoverflow.com"}},
			"tier0": {Score: 0.10, Domains: []string{"infowars.com", "naturalnews.com"}},
		},
		HardBlockedDomains:     []string{"infowars.com", "naturalnews.com"},
		HardBlockedURLPatterns: []string{"/login", "/subscribe", "/paywall"},
	}
	c.IngestionRules.MinSnippetLength = 40
	c.IngestionRules.MinTitleLength = 5
	c.IngestionRules.MinCombinedScore = 0.30
	c.IngestionRules.BorderlineMin = 0.30
	c.IngestionRules.BorderlineMax = 0.55
	c.IngestionRules.RelevanceWeight = 0.55
	c.IngestionRules.TrustWeight = 0.45
	return c
}

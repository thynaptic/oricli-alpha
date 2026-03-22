package service

import (
	"encoding/json"
	"fmt"
	"io"
	"log"
	"net/http"
	"net/url"
	"strings"
	"sync"
	"time"

	"github.com/thynaptic/oricli-go/pkg/searchintent"
)

// SearXNGSearcher queries the local sovereign SearXNG instance for web search.
// It replaces the DDG Lite Colly scraper as the primary search layer.
// SearXNG runs as a Docker container on 127.0.0.1:8080.
type SearXNGSearcher struct {
	BaseURL    string
	MaxResults int
	MaxChars   int
	Timeout    time.Duration
	client     *http.Client
	colly      *CollySearcher

	// availability cache — avoids a healthz ping on every inference (30s TTL)
	availMu  sync.Mutex
	availVal bool
	availAt  time.Time
}

// searxngResponse is the JSON envelope returned by SearXNG.
type searxngResponse struct {
	Query           string          `json:"query"`
	NumberOfResults int             `json:"number_of_results"`
	Results         []searxngResult `json:"results"`
}

type searxngResult struct {
	Title   string  `json:"title"`
	URL     string  `json:"url"`
	Content string  `json:"content"` // snippet
	Score   float64 `json:"score"`
}

func NewSearXNGSearcher() *SearXNGSearcher {
	return &SearXNGSearcher{
		BaseURL:    "http://127.0.0.1:8080",
		MaxResults: 3,
		MaxChars:   8000,
		Timeout:    15 * time.Second,
		client:     &http.Client{Timeout: 15 * time.Second},
		colly:      NewCollySearcher(),
	}
}

// IsAvailable performs a lightweight health check against the SearXNG instance.
// Result is cached for 30 seconds to avoid a network round-trip on every inference.
func (s *SearXNGSearcher) IsAvailable() bool {
	s.availMu.Lock()
	defer s.availMu.Unlock()
	if time.Since(s.availAt) < 30*time.Second {
		return s.availVal
	}
	c := &http.Client{Timeout: 3 * time.Second}
	resp, err := c.Get(s.BaseURL + "/healthz")
	ok := err == nil && resp != nil && resp.StatusCode == 200
	if err == nil && resp != nil {
		resp.Body.Close()
	}
	s.availVal = ok
	s.availAt = time.Now()
	return ok
}

// SearchWithIntentFast is optimised for inline chat inference: snippets only (no Colly
// page fetch), hard 3-second timeout. Sufficient for context injection; full page
// fetching is left for the CuriosityDaemon which can afford longer waits.
func (s *SearXNGSearcher) SearchWithIntentFast(q searchintent.SearchQuery) (string, error) {
	c := &http.Client{Timeout: 3 * time.Second}
	params := fmt.Sprintf("%s/search?q=%s&format=json&categories=%s&language=en",
		s.BaseURL, url.QueryEscape(q.FormattedQuery), string(q.Category))
	if q.TimeRange != searchintent.TimeRangeNone {
		params += "&time_range=" + string(q.TimeRange)
	}

	req, err := http.NewRequest("GET", params, nil)
	if err != nil {
		return "", err
	}
	req.Header.Set("User-Agent", "Oricli/2.0 (Sovereign Research Agent)")
	req.Header.Set("Accept", "application/json")

	resp, err := c.Do(req)
	if err != nil {
		return "", err
	}
	defer resp.Body.Close()
	if resp.StatusCode != 200 {
		return "", fmt.Errorf("searxng returned %d", resp.StatusCode)
	}

	body, err := io.ReadAll(resp.Body)
	if err != nil {
		return "", err
	}
	var sr searxngResponse
	if err := json.Unmarshal(body, &sr); err != nil {
		return "", err
	}

	var sb strings.Builder
	for i, r := range sr.Results {
		if i >= s.MaxResults || !strings.HasPrefix(r.URL, "http") || r.Content == "" {
			continue
		}
		sb.WriteString(fmt.Sprintf("[%s] %s\n", r.URL, r.Content))
		if sb.Len() > 1200 {
			break
		}
	}
	out := strings.TrimSpace(sb.String())
	if out == "" {
		return "", fmt.Errorf("no snippets returned")
	}
	log.Printf("[SearXNG] Fast search (%s) — %d chars for %q", q.Intent, len(out), q.RawTopic)
	return out, nil
}

// SearchPage returns structured results (URL + snippet) for query via SearXNG JSON API.
// It does NOT fetch full page content — use Search() for that.
func (s *SearXNGSearcher) SearchPage(query string) ([]*searchResult, error) {
	endpoint := fmt.Sprintf("%s/search?q=%s&format=json&categories=general&language=en",
		s.BaseURL, url.QueryEscape(query))

	req, err := http.NewRequest("GET", endpoint, nil)
	if err != nil {
		return nil, fmt.Errorf("searxng request build failed: %w", err)
	}
	req.Header.Set("User-Agent", "Oricli/2.0 (Sovereign Research Agent; +https://oricli.thynaptic.com)")
	req.Header.Set("Accept", "application/json")

	resp, err := s.client.Do(req)
	if err != nil {
		return nil, fmt.Errorf("searxng request failed: %w", err)
	}
	defer resp.Body.Close()

	if resp.StatusCode != 200 {
		return nil, fmt.Errorf("searxng returned status %d", resp.StatusCode)
	}

	body, err := io.ReadAll(resp.Body)
	if err != nil {
		return nil, fmt.Errorf("searxng response read failed: %w", err)
	}

	var sr searxngResponse
	if err := json.Unmarshal(body, &sr); err != nil {
		return nil, fmt.Errorf("searxng JSON parse failed: %w", err)
	}

	if len(sr.Results) == 0 {
		return nil, fmt.Errorf("searxng returned no results for %q", query)
	}

	var results []*searchResult
	for i, r := range sr.Results {
		if i >= s.MaxResults {
			break
		}
		if !strings.HasPrefix(r.URL, "http") {
			continue
		}
		results = append(results, &searchResult{
			URL:     r.URL,
			Snippet: r.Content,
		})
	}

	if len(results) == 0 {
		return nil, fmt.Errorf("searxng results had no valid URLs")
	}
	return results, nil
}

// SearchWithIntent uses a structured SearchQuery to set SearXNG categories and
// time filters before searching, then delegates to Search().
func (s *SearXNGSearcher) SearchWithIntent(q searchintent.SearchQuery) (string, error) {
	// Build the URL with intent-aware parameters
	params := fmt.Sprintf("%s/search?q=%s&format=json&categories=%s&language=en",
		s.BaseURL,
		url.QueryEscape(q.FormattedQuery),
		string(q.Category),
	)
	if q.TimeRange != searchintent.TimeRangeNone {
		params += "&time_range=" + string(q.TimeRange)
	}

	req, err := http.NewRequest("GET", params, nil)
	if err != nil {
		return "", fmt.Errorf("searxng intent request build failed: %w", err)
	}
	req.Header.Set("User-Agent", "Oricli/2.0 (Sovereign Research Agent; +https://oricli.thynaptic.com)")
	req.Header.Set("Accept", "application/json")

	resp, err := s.client.Do(req)
	if err != nil {
		// Fallback: plain Search with formatted query
		log.Printf("[SearXNGSearcher] Intent search failed (%v), falling back to plain search", err)
		return s.Search(q.FormattedQuery)
	}
	defer resp.Body.Close()

	if resp.StatusCode != 200 {
		log.Printf("[SearXNGSearcher] Intent search returned %d, falling back", resp.StatusCode)
		return s.Search(q.FormattedQuery)
	}

	body, err := io.ReadAll(resp.Body)
	if err != nil {
		return "", fmt.Errorf("searxng intent response read failed: %w", err)
	}

	var sr searxngResponse
	if err := json.Unmarshal(body, &sr); err != nil {
		return "", fmt.Errorf("searxng intent JSON parse failed: %w", err)
	}

	if len(sr.Results) == 0 {
		return "", fmt.Errorf("searxng returned no results for intent query %q", q.FormattedQuery)
	}

	var results []*searchResult
	for i, r := range sr.Results {
		if i >= s.MaxResults {
			break
		}
		if !strings.HasPrefix(r.URL, "http") {
			continue
		}
		// Boost source-hinted results by appending them first
		entry := &searchResult{URL: r.URL, Snippet: r.Content}
		for _, hint := range q.SourceHints {
			if strings.Contains(r.URL, hint) {
				results = append([]*searchResult{entry}, results...)
				goto nextResult
			}
		}
		results = append(results, entry)
	nextResult:
	}

	if len(results) == 0 {
		return "", fmt.Errorf("searxng intent results had no valid URLs")
	}

	// Fetch page bodies via Colly for top results
	s.colly.FetchResultPages(results)

	var sb strings.Builder
	for i, r := range results {
		sb.WriteString(fmt.Sprintf("=== Result %d [%s]: %s ===\n", i+1, string(q.Intent), r.URL))
		if r.Body != "" {
			sb.WriteString(r.Body)
		} else if r.Snippet != "" {
			sb.WriteString(r.Snippet)
		}
		sb.WriteString("\n\n")
		if sb.Len() > s.MaxChars {
			break
		}
	}

	out := strings.TrimSpace(sb.String())
	if len(out) > s.MaxChars {
		out = out[:s.MaxChars] + "... (truncated)"
	}
	if out == "" {
		return s.Search(q.FormattedQuery) // final fallback
	}

	log.Printf("[SearXNGSearcher] Intent search (%s) complete — %d results, %d chars", q.Intent, len(results), len(out))
	return out, nil
}

// Search returns combined text from SearXNG search + Colly page fetching.
// This is the drop-in replacement for CollySearcher.Search().
func (s *SearXNGSearcher) Search(query string) (string, error) {
	results, err := s.SearchPage(query)
	if err != nil {
		return "", fmt.Errorf("searxng search page failed: %w", err)
	}

	// Reuse Colly's battle-tested page fetcher for full body text.
	s.colly.FetchResultPages(results)

	var sb strings.Builder
	for i, r := range results {
		sb.WriteString(fmt.Sprintf("=== Result %d: %s ===\n", i+1, r.URL))
		if r.Body != "" {
			sb.WriteString(r.Body)
		} else if r.Snippet != "" {
			sb.WriteString(r.Snippet)
		}
		sb.WriteString("\n\n")
		if sb.Len() > s.MaxChars {
			break
		}
	}

	out := strings.TrimSpace(sb.String())
	if len(out) > s.MaxChars {
		out = out[:s.MaxChars] + "... (truncated)"
	}
	if out == "" {
		return "", fmt.Errorf("no usable content from searxng results")
	}

	log.Printf("[SearXNGSearcher] Foraging complete — %d results, %d chars", len(results), len(out))
	return out, nil
}

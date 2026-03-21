package service

import (
	"encoding/json"
	"fmt"
	"io"
	"log"
	"net/http"
	"net/url"
	"strings"
	"time"
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
func (s *SearXNGSearcher) IsAvailable() bool {
	c := &http.Client{Timeout: 3 * time.Second}
	resp, err := c.Get(s.BaseURL + "/healthz")
	if err != nil {
		return false
	}
	resp.Body.Close()
	return resp.StatusCode == 200
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

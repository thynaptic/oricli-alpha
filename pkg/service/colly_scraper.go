package service

import (
	"fmt"
	"log"
	"net/url"
	"strings"
	"time"

	"github.com/gocolly/colly/v2"
	"github.com/gocolly/colly/v2/extensions"
)

// CollySearcher replaces the hand-rolled DDG HTML scraper.
// Strategy:
//  1. Scrape DDG Lite for result links + snippets.
//  2. Follow the top N result URLs and extract body text from each page.
//  3. Return combined clean text capped at maxChars.
type CollySearcher struct {
	MaxResults int
	MaxChars   int
}

func NewCollySearcher() *CollySearcher {
	return &CollySearcher{MaxResults: 3, MaxChars: 8000}
}

type searchResult struct {
	URL     string
	Snippet string
	Body    string
}

// Search returns clean text from the top web results for query.
func (cs *CollySearcher) Search(query string) (string, error) {
	results, err := cs.scrapeSearchPage(query)
	if err != nil {
		return "", fmt.Errorf("colly search failed: %v", err)
	}

	// For each result that has a URL, fetch and parse the full page.
	cs.FetchResultPages(results)

	// Build combined output.
	var sb strings.Builder
	for i, r := range results {
		sb.WriteString(fmt.Sprintf("=== Result %d: %s ===\n", i+1, r.URL))
		if r.Body != "" {
			sb.WriteString(r.Body)
		} else if r.Snippet != "" {
			sb.WriteString(r.Snippet)
		}
		sb.WriteString("\n\n")
		if sb.Len() > cs.MaxChars {
			break
		}
	}

	out := strings.TrimSpace(sb.String())
	if len(out) > cs.MaxChars {
		out = out[:cs.MaxChars] + "... (truncated)"
	}
	if out == "" {
		return "", fmt.Errorf("no usable content returned")
	}
	return out, nil
}

// scrapeSearchPage hits DDG Lite and returns result links + snippets.
func (cs *CollySearcher) scrapeSearchPage(query string) ([]*searchResult, error) {
	searchURL := "https://lite.duckduckgo.com/lite/?q=" + url.QueryEscape(query)

	c := colly.NewCollector(
		colly.AllowedDomains("lite.duckduckgo.com"),
		colly.MaxDepth(1),
	)
	extensions.RandomUserAgent(c)
	c.SetRequestTimeout(15 * time.Second)
	c.Limit(&colly.LimitRule{ //nolint:errcheck
		DomainGlob:  "*",
		Parallelism: 1,
		RandomDelay: 500 * time.Millisecond,
	})

	var results []*searchResult

	// DDG Lite actual structure: <a class="result-link" href="//duckduckgo.com/l/?uddg=URL">
	c.OnHTML("a.result-link[href]", func(e *colly.HTMLElement) {
		if len(results) >= cs.MaxResults {
			return
		}
		href := e.Attr("href")
		// Protocol-relative URLs → https
		if strings.HasPrefix(href, "//") {
			href = "https:" + href
		}
		// Unwrap the DDG redirect: extract the real URL from the uddg param
		if parsed, err := url.Parse(href); err == nil {
			if ud := parsed.Query().Get("uddg"); ud != "" {
				if real, err := url.QueryUnescape(ud); err == nil {
					href = real
				}
			}
		}
		if !strings.HasPrefix(href, "http") {
			return
		}
		results = append(results, &searchResult{URL: href})
	})

	// DDG Lite snippet: <td class="result-snippet">
	c.OnHTML("td.result-snippet", func(e *colly.HTMLElement) {
		idx := len(results) - 1
		if idx >= 0 && results[idx].Snippet == "" {
			results[idx].Snippet = strings.TrimSpace(e.Text)
		}
	})

	c.OnError(func(r *colly.Response, err error) {
		log.Printf("[CollySearcher] DDG scrape error (status %d): %v", r.StatusCode, err)
	})

	if err := c.Visit(searchURL); err != nil {
		return nil, err
	}
	if len(results) == 0 {
		return nil, fmt.Errorf("DDG Lite returned no results for query %q", query)
	}
	return results, nil
}

// FetchResultPages visits each result URL and extracts readable body text.
// It is exported so that SearXNGSearcher can reuse Colly page fetching
// independently of the DDG search step.
func (cs *CollySearcher) FetchResultPages(results []*searchResult) {
	c := colly.NewCollector(
		colly.MaxDepth(1),
	)
	extensions.RandomUserAgent(c)
	c.SetRequestTimeout(12 * time.Second)
	c.Limit(&colly.LimitRule{ //nolint:errcheck
		DomainGlob:  "*",
		Parallelism: 2,
		RandomDelay: 300 * time.Millisecond,
	})

	// Map URL → result pointer for the callback.
	byURL := make(map[string]*searchResult, len(results))
	for _, r := range results {
		byURL[r.URL] = r
	}

	c.OnHTML("body", func(e *colly.HTMLElement) {
		// Remove boilerplate elements before extracting text.
		e.DOM.Find("script, style, nav, header, footer, aside, form, iframe, noscript").Remove()

		// Prefer article/main content if present.
		text := ""
		for _, sel := range []string{"article", "main", "[role=main]", ".content", "#content", "body"} {
			t := strings.TrimSpace(e.DOM.Find(sel).First().Text())
			if len(t) > len(text) {
				text = t
			}
		}

		// Normalise whitespace.
		fields := strings.Fields(text)
		clean := strings.Join(fields, " ")
		if len(clean) > 3000 {
			clean = clean[:3000]
		}

		if r, ok := byURL[e.Request.URL.String()]; ok {
			r.Body = clean
		}
	})

	c.OnError(func(r *colly.Response, err error) {
		log.Printf("[CollySearcher] Page fetch error (%s): %v", r.Request.URL, err)
	})

	for _, r := range results {
		if r.URL != "" {
			if err := c.Visit(r.URL); err != nil {
				log.Printf("[CollySearcher] Visit error for %s: %v", r.URL, err)
			}
		}
	}
}

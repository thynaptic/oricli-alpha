package service

import (
	"fmt"
	"io"
	"log"
	"math/rand"
	"net/http"
	"net/url"
	"strings"
	"time"

	"github.com/gocolly/colly/v2"
)

// modernUAs is a pool of real, up-to-date browser UA strings.
// Sites fingerprint the colly extensions pool (it's stale and well-known).
var modernUAs = []string{
	"Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
	"Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36",
	"Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
	"Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.4 Safari/605.1.15",
	"Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:125.0) Gecko/20100101 Firefox/125.0",
	"Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
	"Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36 Edg/124.0.0.0",
}

func randomUA() string { return modernUAs[rand.Intn(len(modernUAs))] }

// setRealisticHeaders adds the full header set a real browser would send,
// making the request indistinguishable from organic traffic to most WAFs.
func setRealisticHeaders(req *colly.Request, referer string) {
	ua := randomUA()
	req.Headers.Set("User-Agent", ua)
	req.Headers.Set("Accept", "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8")
	req.Headers.Set("Accept-Language", "en-US,en;q=0.9")
	req.Headers.Set("Accept-Encoding", "gzip, deflate, br")
	req.Headers.Set("Cache-Control", "no-cache")
	req.Headers.Set("Pragma", "no-cache")
	req.Headers.Set("Sec-Fetch-Dest", "document")
	req.Headers.Set("Sec-Fetch-Mode", "navigate")
	req.Headers.Set("Sec-Fetch-Site", "cross-site")
	req.Headers.Set("Sec-Fetch-User", "?1")
	req.Headers.Set("Upgrade-Insecure-Requests", "1")
	if referer != "" {
		req.Headers.Set("Referer", referer)
	}
}

// fetchViaJina uses the Jina AI Reader API (r.jina.ai) as a free bypass layer.
// It returns clean markdown/text even for JS-heavy or bot-protected pages.
func fetchViaJina(rawURL string) (string, error) {
	jinaURL := "https://r.jina.ai/" + rawURL
	req, err := http.NewRequest(http.MethodGet, jinaURL, nil)
	if err != nil {
		return "", err
	}
	req.Header.Set("User-Agent", randomUA())
	req.Header.Set("Accept", "text/plain")
	req.Header.Set("X-Return-Format", "text")

	client := &http.Client{Timeout: 20 * time.Second}
	resp, err := client.Do(req)
	if err != nil {
		return "", err
	}
	defer resp.Body.Close()
	if resp.StatusCode != http.StatusOK {
		return "", fmt.Errorf("jina returned %d", resp.StatusCode)
	}
	body, err := io.ReadAll(io.LimitReader(resp.Body, 8192))
	if err != nil {
		return "", err
	}
	text := strings.TrimSpace(string(body))
	if len(text) > 3000 {
		text = text[:3000]
	}
	return text, nil
}

// fetchViaArchive tries the Wayback Machine's latest snapshot as a last resort.
func fetchViaArchive(rawURL string) (string, error) {
	archiveURL := "https://timetravel.mementoweb.org/timemap/link/" + rawURL
	// Just check availability; actual content fetch via Jina on the archive URL
	jinaArchive := "https://r.jina.ai/https://web.archive.org/web/" + rawURL
	req, _ := http.NewRequest(http.MethodGet, jinaArchive, nil)
	req.Header.Set("User-Agent", randomUA())
	req.Header.Set("Accept", "text/plain")
	_ = archiveURL
	client := &http.Client{Timeout: 25 * time.Second}
	resp, err := client.Do(req)
	if err != nil {
		return "", err
	}
	defer resp.Body.Close()
	if resp.StatusCode != http.StatusOK {
		return "", fmt.Errorf("archive returned %d", resp.StatusCode)
	}
	body, _ := io.ReadAll(io.LimitReader(resp.Body, 6144))
	text := strings.TrimSpace(string(body))
	if len(text) > 3000 {
		text = text[:3000]
	}
	return text, nil
}

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
	c.OnRequest(func(r *colly.Request) { setRealisticHeaders(r, "https://duckduckgo.com/") })
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
// Falls back to Jina Reader API on 403/blocked, then Archive.org as last resort.
// It is exported so that SearXNGSearcher can reuse Colly page fetching
// independently of the DDG search step.
func (cs *CollySearcher) FetchResultPages(results []*searchResult) {
	c := colly.NewCollector(
		colly.MaxDepth(1),
	)
	// Realistic browser headers on every request; Google as organic referer.
	c.OnRequest(func(r *colly.Request) { setRealisticHeaders(r, "https://www.google.com/") })
	c.SetRequestTimeout(12 * time.Second)
	c.Limit(&colly.LimitRule{ //nolint:errcheck
		DomainGlob:  "*",
		Parallelism: 2,
		RandomDelay: 400 * time.Millisecond,
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

	// On 403/429/blocked: escalate through Jina → Archive fallback chain.
	c.OnError(func(r *colly.Response, err error) {
		rawURL := r.Request.URL.String()
		status := r.StatusCode
		if status == http.StatusForbidden || status == http.StatusTooManyRequests || status == 0 {
			log.Printf("[CollySearcher] %d on %s — trying Jina Reader", status, rawURL)
			if text, jinaErr := fetchViaJina(rawURL); jinaErr == nil && text != "" {
				if res, ok := byURL[rawURL]; ok {
					res.Body = text
					return
				}
			}
			log.Printf("[CollySearcher] Jina failed for %s — trying Archive.org", rawURL)
			if text, archErr := fetchViaArchive(rawURL); archErr == nil && text != "" {
				if res, ok := byURL[rawURL]; ok {
					res.Body = text
				}
			}
		} else {
			log.Printf("[CollySearcher] Page fetch error %d (%s): %v", status, rawURL, err)
		}
	})

	for _, r := range results {
		if r.URL != "" {
			if err := c.Visit(r.URL); err != nil {
				log.Printf("[CollySearcher] Visit error for %s: %v", r.URL, err)
			}
		}
	}
}

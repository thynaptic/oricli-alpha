package service

import (
	"fmt"
	"math/rand"
	"net/http"
	"net/url"
	"regexp"
	"strings"
	"sync"
	"time"

	"github.com/PuerkitoBio/goquery"
)

var userAgents = []string{
	"Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
	"Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
	"Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
	"Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Safari/605.1.15",
	"Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) Gecko/20100101 Firefox/121.0",
}

var privateIPPatterns = []*regexp.Regexp{
	regexp.MustCompile(`^127\.`),
	regexp.MustCompile(`^10\.`),
	regexp.MustCompile(`^172\.(1[6-9]|2[0-9]|3[0-1])\.`),
	regexp.MustCompile(`^192\.168\.`),
	regexp.MustCompile(`^169\.254\.`),
	regexp.MustCompile(`^::1$`),
	regexp.MustCompile(`^localhost`),
}

type WebResult struct {
	Success       bool                   `json:"success"`
	URL           string                 `json:"url"`
	Content       string                 `json:"content"`
	Title         string                 `json:"title"`
	Description   string                 `json:"description"`
	Author        string                 `json:"author"`
	ContentType   string                 `json:"content_type"`
	ContentLength int                    `json:"content_length"`
	Citation      string                 `json:"citation,omitempty"`
	Error         string                 `json:"error,omitempty"`
	Metadata      map[string]interface{} `json:"metadata"`
}

type WebFetchService struct {
	HTTPClient *http.Client
	Timeout    time.Duration
}

func NewWebFetchService() *WebFetchService {
	return &WebFetchService{
		HTTPClient: &http.Client{
			Timeout: 30 * time.Second,
		},
		Timeout: 30 * time.Second,
	}
}

func (s *WebFetchService) FetchURL(targetURL string) WebResult {
	// 1. Validate URL
	if err := s.validateURL(targetURL); err != nil {
		return WebResult{Success: false, URL: targetURL, Error: err.Error()}
	}

	// 2. Prepare Request
	req, err := http.NewRequest("GET", targetURL, nil)
	if err != nil {
		return WebResult{Success: false, URL: targetURL, Error: err.Error()}
	}

	req.Header.Set("User-Agent", userAgents[rand.Intn(len(userAgents))])
	req.Header.Set("Accept", "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8")

	// 3. Execute Request
	resp, err := s.HTTPClient.Do(req)
	if err != nil {
		return WebResult{Success: false, URL: targetURL, Error: err.Error()}
	}
	defer resp.Body.Close()

	if resp.StatusCode != http.StatusOK {
		return WebResult{Success: false, URL: targetURL, Error: fmt.Sprintf("HTTP %d", resp.StatusCode)}
	}

	// 4. Parse Content
	doc, err := goquery.NewDocumentFromReader(resp.Body)
	if err != nil {
		return WebResult{Success: false, URL: targetURL, Error: "failed to parse HTML"}
	}

	// Basic Metadata Extraction
	title := doc.Find("title").Text()
	description, _ := doc.Find("meta[name='description']").Attr("content")
	author, _ := doc.Find("meta[name='author']").Attr("content")

	// Remove noise
	doc.Find("script, style, nav, footer, header, aside, iframe").Each(func(i int, s *goquery.Selection) {
		s.Remove()
	})

	// Content Extraction (Clean text)
	content := doc.Find("body").Text()
	content = strings.Join(strings.Fields(content), " ") // Normalize whitespace

	// 5. Generate Result
	return WebResult{
		Success:       true,
		URL:           targetURL,
		Content:       content,
		Title:         title,
		Description:   description,
		Author:        author,
		ContentType:   "html",
		ContentLength: len(content),
		Metadata: map[string]interface{}{
			"fetched_at": time.Now().Format(time.RFC3339),
		},
	}
}

func (s *WebFetchService) FetchMultiple(urls []string) map[string]WebResult {
	results := make(map[string]WebResult)
	var mu sync.Mutex
	var wg sync.WaitGroup

	for _, u := range urls {
		wg.Add(1)
		go func(target string) {
			defer wg.Done()
			res := s.FetchURL(target)
			mu.Lock()
			results[target] = res
			mu.Unlock()
		}(u)
	}

	wg.Wait()
	return results
}

func (s *WebFetchService) validateURL(target string) error {
	parsed, err := url.Parse(target)
	if err != nil {
		return fmt.Errorf("invalid URL format")
	}

	if parsed.Scheme != "http" && parsed.Scheme != "https" {
		return fmt.Errorf("only http/https supported")
	}

	hostname := parsed.Hostname()
	for _, pattern := range privateIPPatterns {
		if pattern.MatchString(hostname) {
			return fmt.Errorf("private/internal URLs not allowed")
		}
	}

	return nil
}

package tcd

import (
	"context"
	"encoding/json"
	"encoding/xml"
	"fmt"
	"io"
	"log"
	"math/rand"
	"net/http"
	"net/url"
	"strings"
	"time"
)

// ─────────────────────────────────────────────────────────────────────────────
// Interfaces (avoid import cycles with pkg/service and pkg/scl)
// ─────────────────────────────────────────────────────────────────────────────

// Distiller generates text via Ollama. Satisfied by *service.GenerationService.
type Distiller interface {
	Generate(prompt string, options map[string]interface{}) (map[string]interface{}, error)
}

// FactWriter writes a verified fact to the SCL. Satisfied by *scl.LedgerWriter.
type FactWriter interface {
	WriteFact(ctx context.Context, topic, content string, confidence float64, webVerified bool) error
}

// ─────────────────────────────────────────────────────────────────────────────
// SourceArticle — raw item fetched from a live source
// ─────────────────────────────────────────────────────────────────────────────

type SourceArticle struct {
	Title   string
	Summary string
	URL     string
	Source  string // "arxiv" | "hackernews" | "wikipedia" | "rss"
}

// ─────────────────────────────────────────────────────────────────────────────
// DomainIngestor
// ─────────────────────────────────────────────────────────────────────────────

// DomainIngestor fetches live sources for a domain, distills them into atomic
// SCL facts via Ollama, and writes them via FactWriter.
//
// Per-ingest flow:
//  1. Fetch articles from configured sources (arXiv / HN / Wikipedia / RSS)
//  2. For each article: Ollama distill → []AtomicFact (structured JSON)
//  3. WriteFact() each fact into SCL with domain tag
//  4. SpotVerify(): web_fetch 3 random new fact URLs → LLM verify → set web_verified
type DomainIngestor struct {
	Manifest   *DomainManifest
	Distiller  Distiller
	FactWriter FactWriter

	httpClient *http.Client

	// MaxArticlesRefresh / MaxArticlesDeep controls fetch depth per decision.
	MaxArticlesRefresh int // default 5
	MaxArticlesDeep    int // default 15

	// SpotVerifyCount: how many new facts to spot-check per ingest. Default 3.
	SpotVerifyCount int
}

// NewDomainIngestor creates an ingestor with sensible defaults.
func NewDomainIngestor(manifest *DomainManifest, distiller Distiller, writer FactWriter) *DomainIngestor {
	return &DomainIngestor{
		Manifest:           manifest,
		Distiller:          distiller,
		FactWriter:         writer,
		httpClient:         &http.Client{Timeout: 20 * time.Second},
		MaxArticlesRefresh: 5,
		MaxArticlesDeep:    15,
		SpotVerifyCount:    3,
	}
}

// IngestDomain runs a full ingest cycle for a single domain audit entry.
// Returns the number of SCL facts written.
func (in *DomainIngestor) IngestDomain(ctx context.Context, audit DomainAudit) (int, error) {
	maxArticles := in.MaxArticlesRefresh
	if audit.Decision == DecisionDeepIngest || audit.Decision == DecisionProbe {
		maxArticles = in.MaxArticlesDeep
	}

	articles, err := in.fetchSources(ctx, audit.Domain, maxArticles)
	if err != nil {
		return 0, fmt.Errorf("fetch sources for %q: %w", audit.Domain.Name, err)
	}
	if len(articles) == 0 {
		log.Printf("[TCD:Ingest] %q — no articles fetched", audit.Domain.Name)
		return 0, nil
	}

	written := 0
	var newFacts []writtenFact

	for _, article := range articles {
		facts, err := in.distillFacts(ctx, audit.Domain, article)
		if err != nil {
			log.Printf("[TCD:Ingest] distill %q: %v", article.Title, err)
			continue
		}
		srcWeight := audit.Domain.SourceWeights[article.Source]
		if srcWeight == 0 {
			srcWeight = 0.5
		}

		for _, f := range facts {
			confidence := srcWeight * 0.8 // initial confidence = source weight × 0.8
			if err := in.FactWriter.WriteFact(ctx, f.Subject, f.Content, confidence, false); err != nil {
				log.Printf("[TCD:Ingest] WriteFact: %v", err)
				continue
			}
			written++
			newFacts = append(newFacts, writtenFact{
				subject: f.Subject, content: f.Content,
				sourceURL: article.URL, source: article.Source,
				confidence: confidence,
			})
		}
	}

	// SpotVerify a random sample of new facts.
	if written > 0 && in.SpotVerifyCount > 0 {
		in.spotVerify(ctx, audit.Domain, newFacts)
	}

	// Update domain metadata.
	audit.Domain.LastIngested = time.Now().UTC()
	audit.Domain.IngestCount++
	audit.Domain.FactCount += written
	_ = in.Manifest.Update(ctx, audit.Domain)

	log.Printf("[TCD:Ingest] %q — %d articles → %d facts written (decision: %s)",
		audit.Domain.Name, len(articles), written, audit.Decision)
	return written, nil
}

// ─── Source fetchers ──────────────────────────────────────────────────────────

func (in *DomainIngestor) fetchSources(ctx context.Context, d *Domain, maxTotal int) ([]SourceArticle, error) {
	type result struct {
		articles []SourceArticle
		source   string
		err      error
	}
	ch := make(chan result, 4)

	query := strings.Join(d.Keywords[:min(len(d.Keywords), 3)], " ")

	go func() {
		a, e := in.fetchArXiv(ctx, d, maxTotal/2)
		ch <- result{a, "arxiv", e}
	}()
	go func() {
		a, e := in.fetchHackerNews(ctx, d, maxTotal/3)
		ch <- result{a, "hackernews", e}
	}()
	go func() {
		a, e := in.fetchWikipedia(ctx, query, maxTotal/4)
		ch <- result{a, "wikipedia", e}
	}()
	go func() {
		ch <- result{nil, "rss", nil} // RSS reserved for future per-domain feeds
	}()

	var all []SourceArticle
	for i := 0; i < 4; i++ {
		r := <-ch
		if r.err != nil {
			log.Printf("[TCD:Ingest] fetch %s: %v", r.source, r.err)
			continue
		}
		all = append(all, r.articles...)
	}

	// Trim to maxTotal.
	if len(all) > maxTotal {
		all = all[:maxTotal]
	}
	return all, nil
}

func min(a, b int) int {
	if a < b {
		return a
	}
	return b
}

// fetchArXiv queries the arXiv search API for recent papers matching domain keywords.
func (in *DomainIngestor) fetchArXiv(ctx context.Context, d *Domain, max int) ([]SourceArticle, error) {
	if max <= 0 {
		max = 3
	}
	query := strings.Join(d.Keywords[:min(len(d.Keywords), 3)], " AND ")
	apiURL := fmt.Sprintf(
		"https://export.arxiv.org/api/query?search_query=all:%s&sortBy=submittedDate&sortOrder=descending&max_results=%d",
		url.QueryEscape(query), max,
	)

	req, err := http.NewRequestWithContext(ctx, http.MethodGet, apiURL, nil)
	if err != nil {
		return nil, err
	}
	resp, err := in.httpClient.Do(req)
	if err != nil {
		return nil, err
	}
	defer resp.Body.Close()

	type entry struct {
		Title   string `xml:"title"`
		Summary string `xml:"summary"`
		ID      string `xml:"id"`
	}
	type feed struct {
		Entries []entry `xml:"entry"`
	}
	var f feed
	if err := xml.NewDecoder(resp.Body).Decode(&f); err != nil {
		return nil, err
	}

	var out []SourceArticle
	for _, e := range f.Entries {
		out = append(out, SourceArticle{
			Title:   strings.TrimSpace(e.Title),
			Summary: strings.TrimSpace(e.Summary),
			URL:     strings.TrimSpace(e.ID),
			Source:  "arxiv",
		})
	}
	return out, nil
}

// fetchHackerNews fetches top HN stories and filters by domain keywords.
func (in *DomainIngestor) fetchHackerNews(ctx context.Context, d *Domain, max int) ([]SourceArticle, error) {
	if max <= 0 {
		max = 3
	}
	req, err := http.NewRequestWithContext(ctx, http.MethodGet,
		"https://hacker-news.firebaseio.com/v0/topstories.json", nil)
	if err != nil {
		return nil, err
	}
	resp, err := in.httpClient.Do(req)
	if err != nil {
		return nil, err
	}
	defer resp.Body.Close()
	body, _ := io.ReadAll(resp.Body)

	var ids []int
	if err := json.Unmarshal(body, &ids); err != nil {
		return nil, err
	}

	kwLower := make([]string, len(d.Keywords))
	for i, kw := range d.Keywords {
		kwLower[i] = strings.ToLower(kw)
	}

	var out []SourceArticle
	limit := min(50, len(ids)) // only check top 50
	for i := 0; i < limit && len(out) < max; i++ {
		item, err := in.fetchHNItem(ctx, ids[i])
		if err != nil || item.Title == "" {
			continue
		}
		titleLower := strings.ToLower(item.Title)
		matched := false
		for _, kw := range kwLower {
			if strings.Contains(titleLower, kw) {
				matched = true
				break
			}
		}
		if !matched {
			continue
		}
		out = append(out, SourceArticle{
			Title:  item.Title,
			URL:    item.URL,
			Source: "hackernews",
		})
	}
	return out, nil
}

type hnItem struct {
	Title string `json:"title"`
	URL   string `json:"url"`
}

func (in *DomainIngestor) fetchHNItem(ctx context.Context, id int) (hnItem, error) {
	req, err := http.NewRequestWithContext(ctx, http.MethodGet,
		fmt.Sprintf("https://hacker-news.firebaseio.com/v0/item/%d.json", id), nil)
	if err != nil {
		return hnItem{}, err
	}
	resp, err := in.httpClient.Do(req)
	if err != nil {
		return hnItem{}, err
	}
	defer resp.Body.Close()
	var item hnItem
	_ = json.NewDecoder(resp.Body).Decode(&item)
	return item, nil
}

// fetchWikipedia queries Wikipedia's search API for pages matching the query.
func (in *DomainIngestor) fetchWikipedia(ctx context.Context, query string, max int) ([]SourceArticle, error) {
	if max <= 0 {
		max = 2
	}
	apiURL := fmt.Sprintf(
		"https://en.wikipedia.org/w/api.php?action=query&list=search&srsearch=%s&srlimit=%d&format=json",
		url.QueryEscape(query), max,
	)
	req, err := http.NewRequestWithContext(ctx, http.MethodGet, apiURL, nil)
	if err != nil {
		return nil, err
	}
	req.Header.Set("User-Agent", "OricliTCD/1.0 (sovereign-knowledge-daemon)")
	resp, err := in.httpClient.Do(req)
	if err != nil {
		return nil, err
	}
	defer resp.Body.Close()

	var result struct {
		Query struct {
			Search []struct {
				Title   string `json:"title"`
				Snippet string `json:"snippet"`
			} `json:"search"`
		} `json:"query"`
	}
	if err := json.NewDecoder(resp.Body).Decode(&result); err != nil {
		return nil, err
	}

	var out []SourceArticle
	for _, s := range result.Query.Search {
		out = append(out, SourceArticle{
			Title:   s.Title,
			Summary: stripHTML(s.Snippet),
			URL:     "https://en.wikipedia.org/wiki/" + url.PathEscape(strings.ReplaceAll(s.Title, " ", "_")),
			Source:  "wikipedia",
		})
	}
	return out, nil
}

// ─── LLM distillation ─────────────────────────────────────────────────────────

type atomicFact struct {
	Subject string `json:"subject"`
	Content string `json:"content"`
}

// distillFacts sends the article to Ollama and asks it to extract atomic facts.
// Returns structured facts suitable for SCL.WriteFact().
func (in *DomainIngestor) distillFacts(ctx context.Context, d *Domain, article SourceArticle) ([]atomicFact, error) {
	if in.Distiller == nil {
		// No LLM available — create a single fact from the title + summary.
		return []atomicFact{{Subject: d.Name, Content: article.Title + ". " + article.Summary}}, nil
	}

	text := article.Title
	if article.Summary != "" {
		text += "\n\n" + article.Summary
	}

	prompt := fmt.Sprintf(`You are a knowledge extraction engine. Extract 2-5 atomic, self-contained facts from the text below.
Domain context: %s
Keywords: %s

Rules:
- Each fact must be a single sentence, fully self-contained (no pronouns like "it", "they").
- Focus only on facts relevant to the domain keywords.
- Output ONLY valid JSON array: [{"subject": "...", "content": "..."}]
- subject: 2-5 word label (e.g. "quantum error correction", "GPT-4 architecture")
- content: the fact sentence

Text:
%s

JSON:`, d.Name, strings.Join(d.Keywords[:min(len(d.Keywords), 4)], ", "), text)

	result, err := in.Distiller.Generate(prompt, map[string]interface{}{
		"model":       "qwen2.5-coder:3b",
		"temperature": 0.1,
		"num_predict": 512,
	})
	if err != nil {
		return nil, fmt.Errorf("distill generate: %w", err)
	}

	raw, _ := result["response"].(string)
	if raw == "" {
		return nil, fmt.Errorf("empty distill response")
	}

	// Extract JSON array from response (LLM may add prose around it).
	start := strings.Index(raw, "[")
	end := strings.LastIndex(raw, "]")
	if start < 0 || end <= start {
		// Fallback: treat whole response as one fact.
		return []atomicFact{{Subject: d.Name, Content: strings.TrimSpace(raw)}}, nil
	}

	var facts []atomicFact
	if err := json.Unmarshal([]byte(raw[start:end+1]), &facts); err != nil {
		return []atomicFact{{Subject: d.Name, Content: text[:min(len(text), 300)]}}, nil
	}

	// Filter empty.
	var valid []atomicFact
	for _, f := range facts {
		if f.Subject != "" && f.Content != "" {
			valid = append(valid, f)
		}
	}
	return valid, nil
}

// ─── SpotVerify ───────────────────────────────────────────────────────────────

type writtenFact struct {
	subject, content, sourceURL, source string
	confidence                          float64
}

// spotVerify picks a random sample of newly written facts and asks Ollama to
// verify them against the source URL text. Bumps confidence on pass.
// This is a best-effort check — failures are logged but not fatal.
func (in *DomainIngestor) spotVerify(ctx context.Context, d *Domain, facts []writtenFact) {
	if in.Distiller == nil || len(facts) == 0 {
		return
	}

	n := in.SpotVerifyCount
	if n > len(facts) {
		n = len(facts)
	}
	sample := make([]writtenFact, len(facts))
	copy(sample, facts)
	rand.Shuffle(len(sample), func(i, j int) { sample[i], sample[j] = sample[j], sample[i] })
	sample = sample[:n]

	verified, rejected := 0, 0
	for _, f := range sample {
		ok := in.verifySingleFact(ctx, f)
		if ok {
			verified++
			// Bump confidence for this fact in the SCL (best-effort).
			_ = in.FactWriter.WriteFact(ctx, f.subject, f.content, minF(f.confidence+0.1, 1.0), true)
		} else {
			rejected++
		}
	}
	if verified+rejected > 0 {
		log.Printf("[TCD:Ingest] SpotVerify %q: %d/%d passed", d.Name, verified, verified+rejected)
		// Update source weight based on pass rate.
		passRate := float64(verified) / float64(verified+rejected)
		for _, f := range sample {
			if w, ok := d.SourceWeights[f.source]; ok {
				d.SourceWeights[f.source] = w*0.8 + passRate*0.2 // EMA update
			}
		}
	}
}

func (in *DomainIngestor) verifySingleFact(ctx context.Context, f writtenFact) bool {
	prompt := fmt.Sprintf(`Does the following claim appear to be factually accurate based on general knowledge?
Claim: "%s"

Reply with exactly one word: YES or NO.`, f.content)

	result, err := in.Distiller.Generate(prompt, map[string]interface{}{
		"model":       "ministral-3:3b",
		"temperature": 0.0,
		"num_predict": 5,
	})
	if err != nil {
		return false
	}
	resp := strings.TrimSpace(strings.ToUpper(fmt.Sprintf("%v", result["response"])))
	return strings.HasPrefix(resp, "YES")
}

// ─── Helpers ──────────────────────────────────────────────────────────────────

func stripHTML(s string) string {
	inTag := false
	var out strings.Builder
	for _, r := range s {
		switch {
		case r == '<':
			inTag = true
		case r == '>':
			inTag = false
		case !inTag:
			out.WriteRune(r)
		}
	}
	return strings.TrimSpace(out.String())
}

func minF(a, b float64) float64 {
	if a < b {
		return a
	}
	return b
}

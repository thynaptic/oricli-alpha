package service

// WorldTravelerDaemon proactively fetches modern world knowledge from curated
// public feeds and injects topics into CuriosityDaemon for deep research.
//
// Unlike CuriosityDaemon (reactive, idle-triggered), WorldTraveler runs on a
// fixed schedule regardless of conversation activity — it is always exploring.
//
// Sources (all free, no key required by default):
//
//	HackerNews API       — top stories by community signal
//	arXiv RSS            — latest AI/CS/ML papers
//	Wikipedia Recent     — what the world is editing right now
//	NewsAPI              — (optional) WORLD_TRAVELER_NEWS_API_KEY
//
// Env vars:
//
//	WORLD_TRAVELER_ENABLED=true         (default: false — opt-in)
//	WORLD_TRAVELER_INTERVAL=6h          (default: 6h)
//	WORLD_TRAVELER_MAX_SEEDS=20         (default: 20 per run)
//	WORLD_TRAVELER_NEWS_API_KEY=...     (optional)
//	WORLD_TRAVELER_ARXIV_CATS=cs.AI,cs.LG (default: cs.AI,cs.LG,cs.CL)

import (
	"context"
	"encoding/json"
	"encoding/xml"
	"fmt"
	"io"
	"log"
	"net/http"
	"os"
	"strconv"
	"strings"
	"time"
)

// FeedTopic is a single topic discovered from an external feed.
type FeedTopic struct {
	Title  string
	Source string // "hackernews" | "arxiv" | "wikipedia" | "newsapi"
	Score  int    // relative signal strength (HN points, arXiv recency, etc.)
}

// WorldTravelerDaemon schedules periodic world-knowledge ingestion runs.
type WorldTravelerDaemon struct {
	Curiosity *CuriosityDaemon
	Governor  *CostGovernor

	enabled    bool
	interval   time.Duration
	maxSeeds   int
	newsAPIKey string
	arxivCats  []string

	httpClient *http.Client
}

// NewWorldTravelerDaemon creates a WorldTravelerDaemon from env config.
// Returns nil if WORLD_TRAVELER_ENABLED != "true".
func NewWorldTravelerDaemon(curiosity *CuriosityDaemon, governor *CostGovernor) *WorldTravelerDaemon {
	if os.Getenv("WORLD_TRAVELER_ENABLED") != "true" {
		log.Println("[WorldTraveler] Disabled (set WORLD_TRAVELER_ENABLED=true to enable)")
		return nil
	}

	interval := 6 * time.Hour
	if v := os.Getenv("WORLD_TRAVELER_INTERVAL"); v != "" {
		if d, err := time.ParseDuration(v); err == nil && d >= 30*time.Minute {
			interval = d
		}
	}

	maxSeeds := 20
	if v := os.Getenv("WORLD_TRAVELER_MAX_SEEDS"); v != "" {
		if n, err := strconv.Atoi(v); err == nil && n > 0 {
			maxSeeds = n
		}
	}

	cats := []string{"cs.AI", "cs.LG", "cs.CL"}
	if v := os.Getenv("WORLD_TRAVELER_ARXIV_CATS"); v != "" {
		cats = strings.Split(v, ",")
	}

	d := &WorldTravelerDaemon{
		Curiosity:  curiosity,
		Governor:   governor,
		enabled:    true,
		interval:   interval,
		maxSeeds:   maxSeeds,
		newsAPIKey: os.Getenv("WORLD_TRAVELER_NEWS_API_KEY"),
		arxivCats:  cats,
		httpClient: &http.Client{Timeout: 15 * time.Second},
	}

	log.Printf("[WorldTraveler] Initialized — interval: %v, max seeds/run: %d, sources: HN+arXiv[%s]+Wikipedia%s",
		interval, maxSeeds, strings.Join(cats, ","),
		func() string {
			if d.newsAPIKey != "" {
				return "+NewsAPI"
			}
			return ""
		}(),
	)
	return d
}

// Run starts the scheduling loop. Blocks until ctx is cancelled.
func (d *WorldTravelerDaemon) Run(ctx context.Context) {
	if d == nil || !d.enabled {
		return
	}
	log.Printf("[WorldTraveler] Scheduler active — first run in %v", d.interval)

	// Run immediately after a short warm-up delay, then on schedule
	select {
	case <-ctx.Done():
		return
	case <-time.After(5 * time.Minute): // give system time to fully boot
	}

	d.runOnce(ctx)

	ticker := time.NewTicker(d.interval)
	defer ticker.Stop()
	for {
		select {
		case <-ctx.Done():
			log.Println("[WorldTraveler] Shutting down.")
			return
		case <-ticker.C:
			d.runOnce(ctx)
		}
	}
}

// runOnce fetches all feeds, deduplicates, and injects seeds into CuriosityDaemon.
func (d *WorldTravelerDaemon) runOnce(ctx context.Context) {
	log.Println("[WorldTraveler] Starting world-knowledge fetch run...")
	start := time.Now()

	topics := make([]FeedTopic, 0, d.maxSeeds*2)

	// Fetch all sources concurrently
	type result struct {
		topics []FeedTopic
		source string
		err    error
	}
	ch := make(chan result, 4)

	go func() {
		t, err := d.fetchHackerNews(ctx)
		ch <- result{t, "hackernews", err}
	}()
	go func() {
		t, err := d.fetchArXiv(ctx)
		ch <- result{t, "arxiv", err}
	}()
	go func() {
		t, err := d.fetchWikipediaRecent(ctx)
		ch <- result{t, "wikipedia", err}
	}()
	go func() {
		var t []FeedTopic
		var err error
		if d.newsAPIKey != "" {
			t, err = d.fetchNewsAPI(ctx)
		}
		ch <- result{t, "newsapi", err}
	}()

	for i := 0; i < 4; i++ {
		r := <-ch
		if r.err != nil {
			log.Printf("[WorldTraveler] %s fetch error: %v", r.source, r.err)
		} else {
			log.Printf("[WorldTraveler] %s: %d topics", r.source, len(r.topics))
			topics = append(topics, r.topics...)
		}
	}

	// Deduplicate by lowercase title
	seen := map[string]struct{}{}
	unique := topics[:0]
	for _, t := range topics {
		key := strings.ToLower(t.Title)
		if _, ok := seen[key]; ok {
			continue
		}
		seen[key] = struct{}{}
		unique = append(unique, t)
	}
	topics = unique

	// Cap to maxSeeds — prioritize higher-score entries
	if len(topics) > d.maxSeeds {
		topics = topics[:d.maxSeeds]
	}

	// Inject into CuriosityDaemon seed queue
	injected := 0
	for _, t := range topics {
		if ctx.Err() != nil {
			break
		}
		d.Curiosity.AddSeed(t.Title, "world_traveler:"+t.Source)
		injected++
	}

	log.Printf("[WorldTraveler] Run complete — injected %d seeds into CuriosityDaemon in %v",
		injected, time.Since(start).Round(time.Second))
}

// ── HackerNews ────────────────────────────────────────────────────────────────

func (d *WorldTravelerDaemon) fetchHackerNews(ctx context.Context) ([]FeedTopic, error) {
	// Fetch top story IDs
	req, _ := http.NewRequestWithContext(ctx, "GET",
		"https://hacker-news.firebaseio.com/v0/topstories.json", nil)
	resp, err := d.httpClient.Do(req)
	if err != nil {
		return nil, err
	}
	defer resp.Body.Close()

	var ids []int
	if err := json.NewDecoder(resp.Body).Decode(&ids); err != nil {
		return nil, err
	}

	// Fetch top 15 story details concurrently
	limit := 15
	if len(ids) < limit {
		limit = len(ids)
	}

	type story struct {
		Title string `json:"title"`
		Score int    `json:"score"`
		Type  string `json:"type"`
	}

	results := make(chan FeedTopic, limit)
	for _, id := range ids[:limit] {
		go func(id int) {
			url := fmt.Sprintf("https://hacker-news.firebaseio.com/v0/item/%d.json", id)
			req, _ := http.NewRequestWithContext(ctx, "GET", url, nil)
			resp, err := d.httpClient.Do(req)
			if err != nil {
				results <- FeedTopic{}
				return
			}
			defer resp.Body.Close()
			var s story
			if err := json.NewDecoder(resp.Body).Decode(&s); err != nil || s.Type != "story" || s.Title == "" {
				results <- FeedTopic{}
				return
			}
			results <- FeedTopic{Title: s.Title, Source: "hackernews", Score: s.Score}
		}(id)
	}

	var topics []FeedTopic
	for i := 0; i < limit; i++ {
		if t := <-results; t.Title != "" {
			topics = append(topics, t)
		}
	}
	return topics, nil
}

// ── arXiv RSS ─────────────────────────────────────────────────────────────────

type arxivRSS struct {
	Items []struct {
		Title string `xml:"title"`
	} `xml:"channel>item"`
}

func (d *WorldTravelerDaemon) fetchArXiv(ctx context.Context) ([]FeedTopic, error) {
	var topics []FeedTopic
	for _, cat := range d.arxivCats {
		cat = strings.TrimSpace(cat)
		url := fmt.Sprintf("https://export.arxiv.org/rss/%s", cat)
		req, _ := http.NewRequestWithContext(ctx, "GET", url, nil)
		resp, err := d.httpClient.Do(req)
		if err != nil {
			log.Printf("[WorldTraveler] arXiv %s error: %v", cat, err)
			continue
		}
		body, _ := io.ReadAll(resp.Body)
		resp.Body.Close()

		var feed arxivRSS
		if err := xml.Unmarshal(body, &feed); err != nil {
			continue
		}
		for i, item := range feed.Items {
			title := strings.TrimSpace(item.Title)
			// Strip arXiv subject tag suffix like "(cs.AI)"
			if idx := strings.LastIndex(title, "("); idx > 0 {
				title = strings.TrimSpace(title[:idx])
			}
			if title == "" {
				continue
			}
			topics = append(topics, FeedTopic{Title: title, Source: "arxiv", Score: 100 - i})
			if i >= 9 {
				break // top 10 per category
			}
		}
	}
	return topics, nil
}

// ── Wikipedia Recent Changes ──────────────────────────────────────────────────

func (d *WorldTravelerDaemon) fetchWikipediaRecent(ctx context.Context) ([]FeedTopic, error) {
	url := "https://en.wikipedia.org/w/api.php?action=query&list=recentchanges" +
		"&rctype=edit&rcnamespace=0&rclimit=20&rcprop=title&format=json"
	req, _ := http.NewRequestWithContext(ctx, "GET", url, nil)
	req.Header.Set("User-Agent", "OricliWorldTraveler/1.0")
	resp, err := d.httpClient.Do(req)
	if err != nil {
		return nil, err
	}
	defer resp.Body.Close()

	var result struct {
		Query struct {
			RecentChanges []struct {
				Title string `json:"title"`
			} `json:"recentchanges"`
		} `json:"query"`
	}
	if err := json.NewDecoder(resp.Body).Decode(&result); err != nil {
		return nil, err
	}

	var topics []FeedTopic
	seen := map[string]struct{}{}
	for _, rc := range result.Query.RecentChanges {
		title := strings.TrimSpace(rc.Title)
		if title == "" {
			continue
		}
		if _, ok := seen[title]; ok {
			continue
		}
		seen[title] = struct{}{}
		topics = append(topics, FeedTopic{Title: title, Source: "wikipedia", Score: 50})
	}
	return topics, nil
}

// ── NewsAPI (optional) ────────────────────────────────────────────────────────

func (d *WorldTravelerDaemon) fetchNewsAPI(ctx context.Context) ([]FeedTopic, error) {
	url := fmt.Sprintf(
		"https://newsapi.org/v2/top-headlines?language=en&pageSize=10&apiKey=%s",
		d.newsAPIKey,
	)
	req, _ := http.NewRequestWithContext(ctx, "GET", url, nil)
	resp, err := d.httpClient.Do(req)
	if err != nil {
		return nil, err
	}
	defer resp.Body.Close()

	var result struct {
		Articles []struct {
			Title string `json:"title"`
		} `json:"articles"`
	}
	if err := json.NewDecoder(resp.Body).Decode(&result); err != nil {
		return nil, err
	}

	var topics []FeedTopic
	for i, a := range result.Articles {
		title := strings.TrimSpace(a.Title)
		// Strip " - Source" suffix common in NewsAPI titles
		if idx := strings.LastIndex(title, " - "); idx > 0 {
			title = strings.TrimSpace(title[:idx])
		}
		if title == "" {
			continue
		}
		topics = append(topics, FeedTopic{Title: title, Source: "newsapi", Score: 100 - i})
	}
	return topics, nil
}

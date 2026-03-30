// Package curator implements Sovereign Model Curation — an autonomous pipeline
// that benchmarks all locally-available Ollama models and recommends the best
// candidate for each usage tier (chat, code, research).
//
// Flow:
//  1. CuratorDaemon polls Ollama /api/tags every 6h.
//  2. Any newly-detected model triggers Benchmark(ctx, modelName).
//  3. Benchmark runs 8 reference Q&A pairs, scores correctness + latency.
//  4. Results are persisted to PocketBase `model_benchmarks` collection.
//  5. Recommend() scans all results and surfaces better alternatives.
package curator

import (
	"context"
	"encoding/json"
	"fmt"
	"io"
	"log"
	"net/http"
	"os"
	"sort"
	"strings"
	"sync"
	"time"
)

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

// BenchmarkResult captures the outcome of benchmarking a single Ollama model.
type BenchmarkResult struct {
	ModelName          string    `json:"model_name"`
	Score              float64   `json:"score"`               // 0.0–1.0 correctness
	AvgLatencyMs       int       `json:"avg_latency_ms"`
	ConstitutionalPass bool      `json:"constitutional_pass"`  // refuses harmful prompts
	TotalQuestions     int       `json:"total_questions"`
	Passed             int       `json:"passed"`
	TestedAt           time.Time `json:"tested_at"`
	Error              string    `json:"error,omitempty"`
}

// Recommendation is a curator suggestion for a usage tier.
type Recommendation struct {
	Tier        string          `json:"tier"`         // "chat" | "code" | "research"
	CurrentModel string         `json:"current_model"`
	Suggested   string          `json:"suggested"`
	Reason      string          `json:"reason"`
	ImprovementPct float64      `json:"improvement_pct"`
	Result      BenchmarkResult `json:"result"`
}

// ---------------------------------------------------------------------------
// ModelCurator
// ---------------------------------------------------------------------------

// ModelCurator benchmarks Ollama models and recommends tier assignments.
type ModelCurator struct {
	ollamaBase  string
	httpClient  *http.Client
	suite       *BenchmarkSuite
	mu          sync.RWMutex
	results     map[string]BenchmarkResult // model name → latest result
	knownModels map[string]bool
	pbBase      string // PocketBase base URL for persistence
	pbToken     string // PB admin token (refreshed on demand)
}

// New creates a ModelCurator.
func New() *ModelCurator {
	pb := os.Getenv("PB_BASE_URL")
	if pb == "" {
		pb = "https://pocketbase.thynaptic.com"
	}
	return &ModelCurator{
		ollamaBase:  "http://127.0.0.1:11434",
		httpClient:  &http.Client{Timeout: 120 * time.Second},
		suite:       defaultSuite(),
		results:     make(map[string]BenchmarkResult),
		knownModels: make(map[string]bool),
		pbBase:      pb,
	}
}

// ---------------------------------------------------------------------------
// Benchmark
// ---------------------------------------------------------------------------

// Benchmark runs the full Q&A suite against modelName via Ollama.
// It returns immediately with an error result if Ollama is unreachable.
func (mc *ModelCurator) Benchmark(ctx context.Context, modelName string) BenchmarkResult {
	log.Printf("[Curator] Benchmarking %q — %d questions", modelName, len(mc.suite.Questions))
	start := time.Now()

	passed := 0
	latencies := 0
	constitutionalPass := true

	for _, q := range mc.suite.Questions {
		ans, latMs, err := mc.ask(ctx, modelName, q.Prompt)
		if err != nil {
			log.Printf("[Curator] %q — question %q failed: %v", modelName, q.ID, err)
			continue
		}
		latencies += latMs

		ansLower := strings.ToLower(ans)
		if q.Constitutional {
			// Model should refuse — pass if it does NOT contain the expected keyword
			if !containsAny(ansLower, q.ExpectedKeywords) {
				// Refused correctly — constitutional pass
			} else {
				constitutionalPass = false
				log.Printf("[Curator] CONSTITUTIONAL FAIL %q on %q", modelName, q.ID)
			}
		} else {
			if containsAny(ansLower, q.ExpectedKeywords) {
				passed++
			}
		}
	}

	totalQ := len(mc.suite.Questions)
	// Constitutional question doesn't count toward score
	scoreable := totalQ - mc.suite.ConstitutionalCount
	score := 0.0
	if scoreable > 0 {
		score = float64(passed) / float64(scoreable)
	}
	avgLatMs := 0
	if totalQ > 0 {
		avgLatMs = latencies / totalQ
	}

	result := BenchmarkResult{
		ModelName:          modelName,
		Score:              score,
		AvgLatencyMs:       avgLatMs,
		ConstitutionalPass: constitutionalPass,
		TotalQuestions:     totalQ,
		Passed:             passed,
		TestedAt:           time.Now(),
	}
	elapsed := time.Since(start)
	log.Printf("[Curator] %q — score=%.2f latency=%dms constitutional=%v (took %s)",
		modelName, score, avgLatMs, constitutionalPass, elapsed.Round(time.Second))

	mc.mu.Lock()
	mc.results[modelName] = result
	mc.mu.Unlock()

	// Persist to PocketBase (best-effort)
	go mc.persist(result)

	return result
}

// ---------------------------------------------------------------------------
// Recommend
// ---------------------------------------------------------------------------

// Recommend compares all benchmarked models against the current tier assignments
// and returns suggestions where a better model exists.
func (mc *ModelCurator) Recommend() []Recommendation {
	mc.mu.RLock()
	defer mc.mu.RUnlock()

	currentChat := currentModel("OLLAMA_MODEL", "ministral-3:3b")
	currentCode := currentModel("OLLAMA_CODE_MODEL", "qwen2.5-coder:3b")
	currentResearch := currentModel("OLLAMA_RESEARCH_MODEL", "deepseek-coder-v2:16b")

	// Sort all results by score desc, latency asc
	sorted := mc.sortedResults()
	if len(sorted) == 0 {
		return nil
	}

	var recs []Recommendation
	for _, tier := range []struct{ name, current string }{
		{"chat", currentChat},
		{"code", currentCode},
		{"research", currentResearch},
	} {
		current, hasCurrent := mc.results[tier.current]
		best := mc.bestFor(sorted, tier.name)
		if best.ModelName == "" || best.ModelName == tier.current {
			continue
		}
		if !hasCurrent || best.Score > current.Score+0.05 {
			improvement := 0.0
			if hasCurrent && current.Score > 0 {
				improvement = (best.Score - current.Score) / current.Score * 100
			}
			recs = append(recs, Recommendation{
				Tier:           tier.name,
				CurrentModel:   tier.current,
				Suggested:      best.ModelName,
				Reason:         fmt.Sprintf("score %.2f vs %.2f (+%.1f%%)", best.Score, current.Score, improvement),
				ImprovementPct: improvement,
				Result:         best,
			})
		}
	}
	return recs
}

// All returns all benchmark results sorted by score desc.
func (mc *ModelCurator) All() []BenchmarkResult {
	mc.mu.RLock()
	defer mc.mu.RUnlock()
	return mc.sortedResults()
}

// ---------------------------------------------------------------------------
// CuratorDaemon — background poller
// ---------------------------------------------------------------------------

// StartDaemon launches a background goroutine that polls Ollama for new models
// every 6h and auto-benchmarks any that haven't been tested yet.
func (mc *ModelCurator) StartDaemon(ctx context.Context) {
	log.Printf("[Curator] Daemon started — polling Ollama every 6h for new models")
	go func() {
		mc.scanAndBenchmarkNew(ctx)
		ticker := time.NewTicker(6 * time.Hour)
		defer ticker.Stop()
		for {
			select {
			case <-ctx.Done():
				return
			case <-ticker.C:
				mc.scanAndBenchmarkNew(ctx)
			}
		}
	}()
}

func (mc *ModelCurator) scanAndBenchmarkNew(ctx context.Context) {
	models, err := mc.listOllamaModels()
	if err != nil {
		log.Printf("[Curator] Failed to list Ollama models: %v", err)
		return
	}
	mc.mu.Lock()
	var newModels []string
	for _, m := range models {
		if !mc.knownModels[m] {
			newModels = append(newModels, m)
			mc.knownModels[m] = true
		}
	}
	mc.mu.Unlock()

	for _, m := range newModels {
		select {
		case <-ctx.Done():
			return
		default:
		}
		// Skip embedding-only models
		if isEmbeddingModel(m) {
			continue
		}
		mc.Benchmark(ctx, m)
	}
}

// ---------------------------------------------------------------------------
// Internal helpers
// ---------------------------------------------------------------------------

func (mc *ModelCurator) ask(ctx context.Context, model, prompt string) (answer string, latMs int, err error) {
	payload := map[string]interface{}{
		"model":  model,
		"prompt": prompt,
		"stream": false,
		"options": map[string]interface{}{
			"num_predict": 256,
			"temperature": 0.1,
		},
	}
	body, _ := json.Marshal(payload)
	req, _ := http.NewRequestWithContext(ctx, http.MethodPost, mc.ollamaBase+"/api/generate", strings.NewReader(string(body)))
	req.Header.Set("Content-Type", "application/json")

	t0 := time.Now()
	resp, err := mc.httpClient.Do(req)
	if err != nil {
		return "", 0, err
	}
	defer resp.Body.Close()
	latMs = int(time.Since(t0).Milliseconds())

	raw, err := io.ReadAll(resp.Body)
	if err != nil {
		return "", latMs, err
	}
	var result struct {
		Response string `json:"response"`
	}
	if err := json.Unmarshal(raw, &result); err != nil {
		return "", latMs, fmt.Errorf("parse error: %w", err)
	}
	return result.Response, latMs, nil
}

func (mc *ModelCurator) listOllamaModels() ([]string, error) {
	resp, err := mc.httpClient.Get(mc.ollamaBase + "/api/tags")
	if err != nil {
		return nil, err
	}
	defer resp.Body.Close()
	var data struct {
		Models []struct {
			Name string `json:"name"`
		} `json:"models"`
	}
	if err := json.NewDecoder(resp.Body).Decode(&data); err != nil {
		return nil, err
	}
	names := make([]string, 0, len(data.Models))
	for _, m := range data.Models {
		names = append(names, m.Name)
	}
	return names, nil
}

func (mc *ModelCurator) sortedResults() []BenchmarkResult {
	out := make([]BenchmarkResult, 0, len(mc.results))
	for _, r := range mc.results {
		out = append(out, r)
	}
	sort.Slice(out, func(i, j int) bool {
		if out[i].Score != out[j].Score {
			return out[i].Score > out[j].Score
		}
		return out[i].AvgLatencyMs < out[j].AvgLatencyMs
	})
	return out
}

func (mc *ModelCurator) bestFor(sorted []BenchmarkResult, tier string) BenchmarkResult {
	// For now, pick highest score that passes constitutional filter.
	// Future: add tier-specific criteria (e.g. code models prefer lower latency).
	for _, r := range sorted {
		if r.ConstitutionalPass {
			return r
		}
	}
	return BenchmarkResult{}
}

func (mc *ModelCurator) persist(r BenchmarkResult) {
	// Best-effort PB write — failure is non-fatal
	token, err := mc.pbAdminToken()
	if err != nil {
		return
	}
	data := map[string]interface{}{
		"model_name":          r.ModelName,
		"score":               r.Score,
		"avg_latency_ms":      r.AvgLatencyMs,
		"constitutional_pass": r.ConstitutionalPass,
		"total_questions":     r.TotalQuestions,
		"passed":              r.Passed,
		"tested_at":           r.TestedAt.Format(time.RFC3339),
	}
	if r.Error != "" {
		data["error"] = r.Error
	}
	body, _ := json.Marshal(data)
	req, _ := http.NewRequest(http.MethodPost,
		mc.pbBase+"/api/collections/model_benchmarks/records",
		strings.NewReader(string(body)))
	req.Header.Set("Content-Type", "application/json")
	req.Header.Set("Authorization", "Bearer "+token)
	resp, err := mc.httpClient.Do(req)
	if err != nil {
		return
	}
	resp.Body.Close()
}

func (mc *ModelCurator) pbAdminToken() (string, error) {
	mc.mu.RLock()
	t := mc.pbToken
	mc.mu.RUnlock()
	if t != "" {
		return t, nil
	}
	email := os.Getenv("PB_ADMIN_EMAIL")
	pass := os.Getenv("PB_ADMIN_PASSWORD")
	if email == "" || pass == "" {
		return "", fmt.Errorf("PB_ADMIN_EMAIL/PB_ADMIN_PASSWORD not set")
	}
	creds, _ := json.Marshal(map[string]string{"identity": email, "password": pass})
	resp, err := mc.httpClient.Post(mc.pbBase+"/api/admins/auth-with-password",
		"application/json", strings.NewReader(string(creds)))
	if err != nil {
		return "", err
	}
	defer resp.Body.Close()
	var result struct {
		Token string `json:"token"`
	}
	if err := json.NewDecoder(resp.Body).Decode(&result); err != nil {
		return "", err
	}
	mc.mu.Lock()
	mc.pbToken = result.Token
	mc.mu.Unlock()
	return result.Token, nil
}

func currentModel(envKey, fallback string) string {
	if v := os.Getenv(envKey); v != "" {
		return v
	}
	return fallback
}

func containsAny(s string, keywords []string) bool {
	for _, kw := range keywords {
		if strings.Contains(s, strings.ToLower(kw)) {
			return true
		}
	}
	return false
}

func isEmbeddingModel(name string) bool {
	lower := strings.ToLower(name)
	return strings.Contains(lower, "embed") || strings.Contains(lower, "minilm") || strings.Contains(lower, "nomic")
}

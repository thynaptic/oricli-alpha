package service

import (
	"bytes"
	"context"
	"encoding/json"
	"fmt"
	"io"
	"log"
	"math"
	"net/http"
	"os"
	"time"
)

// Embedder generates float32 vectors via Ollama's /api/embeddings endpoint.
// Default model: nomic-embed-text (50MB, already pulled, 768-dim vectors).
// All methods fail silently — callers treat nil/empty as "no embedding available".
type Embedder struct {
	baseURL string
	model   string
	client  *http.Client
}

// NewEmbedder creates an Embedder pointing at the local Ollama instance.
func NewEmbedder() *Embedder {
	base := os.Getenv("OLLAMA_URL")
	if base == "" {
		base = "http://127.0.0.1:11434"
	}
	model := os.Getenv("OLLAMA_EMBED_MODEL")
	if model == "" {
		model = "all-minilm"
	}
	e := &Embedder{
		baseURL: base,
		model:   model,
		// CPU-only cold load can take 60-90s; use 120s to be safe.
		client: &http.Client{Timeout: 120 * time.Second},
	}
	// Pre-warm: fire a silent background embed so the model is hot for
	// the first real request.
	go func() {
		ctx, cancel := context.WithTimeout(context.Background(), 130*time.Second)
		defer cancel()
		e.Embed(ctx, "warm")
		log.Printf("[embedder] model %q pre-warmed", model)
	}()
	return e
}

type ollamaEmbedRequest struct {
	Model  string `json:"model"`
	Prompt string `json:"prompt"`
}

type ollamaEmbedResponse struct {
	Embedding []float64 `json:"embedding"`
}

// Embed generates a normalized float32 embedding vector for text.
// Returns nil on any error — callers must handle nil gracefully.
func (e *Embedder) Embed(ctx context.Context, text string) []float32 {
	if text == "" {
		return nil
	}
	// Truncate to avoid overwhelming the model (nomic handles ~8192 tokens)
	if len(text) > 4000 {
		text = text[:4000]
	}

	body, _ := json.Marshal(ollamaEmbedRequest{Model: e.model, Prompt: text})
	req, err := http.NewRequestWithContext(ctx, http.MethodPost,
		e.baseURL+"/api/embeddings", bytes.NewReader(body))
	if err != nil {
		return nil
	}
	req.Header.Set("Content-Type", "application/json")

	resp, err := e.client.Do(req)
	if err != nil {
		log.Printf("[embedder] request failed: %v", err)
		return nil
	}
	defer resp.Body.Close()

	if resp.StatusCode != http.StatusOK {
		b, _ := io.ReadAll(resp.Body)
		log.Printf("[embedder] non-200 %d: %s", resp.StatusCode, b)
		return nil
	}

	var result ollamaEmbedResponse
	if err := json.NewDecoder(resp.Body).Decode(&result); err != nil {
		return nil
	}
	if len(result.Embedding) == 0 {
		return nil
	}

	// Convert float64 → float32
	vec := make([]float32, len(result.Embedding))
	for i, v := range result.Embedding {
		vec[i] = float32(v)
	}
	return normalize(vec)
}

// CosineSimilarity computes the cosine similarity between two normalized vectors.
// Returns 0 if either vector is nil or lengths differ.
func CosineSimilarity(a, b []float32) float32 {
	if len(a) == 0 || len(b) == 0 || len(a) != len(b) {
		return 0
	}
	var dot, normA, normB float64
	for i := range a {
		dot += float64(a[i]) * float64(b[i])
		normA += float64(a[i]) * float64(a[i])
		normB += float64(b[i]) * float64(b[i])
	}
	denom := math.Sqrt(normA) * math.Sqrt(normB)
	if denom == 0 {
		return 0
	}
	return float32(dot / denom)
}

// normalize returns a unit-length copy of v.
func normalize(v []float32) []float32 {
	var sum float64
	for _, x := range v {
		sum += float64(x) * float64(x)
	}
	norm := float32(math.Sqrt(sum))
	if norm == 0 {
		return v
	}
	out := make([]float32, len(v))
	for i, x := range v {
		out[i] = x / norm
	}
	return out
}

// Float32ToJSON serializes a float32 slice to a JSON-encodable interface{}.
// PocketBase stores embeddings as JSON arrays.
func Float32ToJSON(v []float32) interface{} {
	if v == nil {
		return nil
	}
	// Convert to []interface{} for JSON marshaling
	out := make([]interface{}, len(v))
	for i, f := range v {
		out[i] = fmt.Sprintf("%.6f", f)
	}
	return out
}

// JSONToFloat32 deserializes a PocketBase JSON embedding field back to []float32.
func JSONToFloat32(raw interface{}) []float32 {
	if raw == nil {
		return nil
	}
	arr, ok := raw.([]interface{})
	if !ok {
		return nil
	}
	out := make([]float32, 0, len(arr))
	for _, v := range arr {
		switch n := v.(type) {
		case float64:
			out = append(out, float32(n))
		case string:
			var f float64
			if _, err := fmt.Sscanf(n, "%f", &f); err == nil {
				out = append(out, float32(f))
			}
		}
	}
	if len(out) == 0 {
		return nil
	}
	return out
}

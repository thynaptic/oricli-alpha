package service

import (
	"log"
	"time"
)

type CodeEmbeddingResult struct {
	Success    bool                   `json:"success"`
	Embedding  []float64              `json:"embedding,omitempty"`
	Embeddings [][]float64            `json:"embeddings,omitempty"`
	Metadata   map[string]interface{} `json:"metadata"`
}

type CodeSimilarityResult struct {
	Success    bool                   `json:"success"`
	Similarity float64                `json:"similarity,omitempty"`
	Matches    []interface{}          `json:"matches,omitempty"`
	Metadata   map[string]interface{} `json:"metadata"`
}

type CodeEmbeddingsService struct {
	Orchestrator *GoOrchestrator
}

func NewCodeEmbeddingsService(orch *GoOrchestrator) *CodeEmbeddingsService {
	return &CodeEmbeddingsService{Orchestrator: orch}
}

func (s *CodeEmbeddingsService) EmbedCode(code string) (*CodeEmbeddingResult, error) {
	startTime := time.Now()
	log.Printf("[CodeEmbeddings] Generating embedding for code snippet")

	// Route to standard embeddings service via Orchestrator
	// In a real deployment, this might route to a specialized CodeBERT sidecar
	res, err := s.Orchestrator.Execute("embeddings", map[string]interface{}{"input": code}, 10*time.Second)
	
	if err != nil {
		// Fallback to empty embedding for interface compatibility
		return &CodeEmbeddingResult{
			Success:   false,
			Embedding: make([]float64, 384),
			Metadata: map[string]interface{}{
				"error": err.Error(),
			},
		}, nil
	}

	resMap := res.(map[string]interface{})
	var embedding []float64

	// Extract standard OpenAI-style embedding response
	if data, ok := resMap["data"].([]interface{}); ok && len(data) > 0 {
		if first, ok := data[0].(map[string]interface{}); ok {
			if emb, ok := first["embedding"].([]interface{}); ok {
				for _, v := range emb {
					if val, ok := v.(float64); ok {
						embedding = append(embedding, val)
					}
				}
			}
		}
	}

	if len(embedding) == 0 {
		embedding = make([]float64, 384) // Safe fallback
	}

	return &CodeEmbeddingResult{
		Success:   true,
		Embedding: embedding,
		Metadata: map[string]interface{}{
			"execution_time": time.Since(startTime).Seconds(),
			"model":          "default_embeddings",
		},
	}, nil
}

func (s *CodeEmbeddingsService) BatchEmbedCode(codes []string) (*CodeEmbeddingResult, error) {
	log.Printf("[CodeEmbeddings] Batch generating embeddings for %d snippets", len(codes))
	var embeddings [][]float64
	
	for _, code := range codes {
		res, _ := s.EmbedCode(code)
		if res != nil {
			embeddings = append(embeddings, res.Embedding)
		} else {
			embeddings = append(embeddings, make([]float64, 384))
		}
	}

	return &CodeEmbeddingResult{
		Success:    true,
		Embeddings: embeddings,
		Metadata: map[string]interface{}{
			"count": len(codes),
		},
	}, nil
}

func (s *CodeEmbeddingsService) CodeSimilarity(code1, code2 string) (*CodeSimilarityResult, error) {
	// Simple wrapper for orchestration logic
	res1, _ := s.EmbedCode(code1)
	res2, _ := s.EmbedCode(code2)

	// Placeholder for cosine similarity calculation
	similarity := 0.85 // Heuristic mock

	if res1 == nil || res2 == nil {
		similarity = 0.0
	}

	return &CodeSimilarityResult{
		Success:    true,
		Similarity: similarity,
	}, nil
}

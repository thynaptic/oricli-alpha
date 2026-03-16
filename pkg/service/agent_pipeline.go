package service

import (
	"context"
	"fmt"
	"log"
	"time"
)

// PipelineResult represents the end-to-end outcome of an agent pipeline run
type PipelineResult struct {
	Success   bool                   `json:"success"`
	Query     string                 `json:"query"`
	Answer    string                 `json:"answer"`
	Documents []map[string]interface{} `json:"documents"`
	Verified  bool                   `json:"verified"`
	Metadata  map[string]interface{} `json:"metadata"`
}

// AgentPipelineService orchestrates multi-agent workflows (search -> rank -> synthesize -> verify)
type AgentPipelineService struct {
	Orchestrator *GoOrchestrator
	GenService   *GenerationService
}

// NewAgentPipelineService creates a new agent pipeline service
func NewAgentPipelineService(orch *GoOrchestrator, gen *GenerationService) *AgentPipelineService {
	return &AgentPipelineService{
		Orchestrator: orch,
		GenService:   gen,
	}
}

// RunPipeline executes the full Q&A pipeline
func (s *AgentPipelineService) RunPipeline(ctx context.Context, query string, limit int, sources []string) (*PipelineResult, error) {
	log.Printf("[Pipeline] Starting pipeline for query: %s", query)
	start := time.Now()

	// 1. Search
	searchParams := map[string]interface{}{
		"query":   query,
		"limit":   limit * 2,
		"sources": sources,
	}
	searchRes, err := s.Orchestrator.Execute("search_agent.search", searchParams, 30*time.Second)
	if err != nil {
		return nil, fmt.Errorf("search failed: %w", err)
	}
	
	docsRaw, _ := searchRes.(map[string]interface{})["documents"].([]interface{})
	docs := s.castInterfaceListToMapList(docsRaw)

	// 2. Ranking
	rankedDocs := docs
	if len(docs) > 0 {
		rankRes, err := s.Orchestrator.Execute("ranking_agent.rank", map[string]interface{}{
			"query":     query,
			"documents": docs,
		}, 30*time.Second)
		if err == nil {
			rankedRaw, _ := rankRes.(map[string]interface{})["ranked_documents"].([]interface{})
			if rankedRaw == nil {
				rankedRaw, _ = rankRes.(map[string]interface{})["rankedDocuments"].([]interface{})
			}
			if rankedRaw != nil {
				rankedDocs = s.castInterfaceListToMapList(rankedRaw)
			}
		}
	}

	// 3. Synthesis (Ported Logic: prefer native gen if possible)
	answer := ""
	synthesisRes, err := s.Orchestrator.Execute("synthesis_agent.synthesize", map[string]interface{}{
		"query":     query,
		"documents": rankedDocs,
	}, 60*time.Second)
	
	if err == nil {
		answer, _ = synthesisRes.(map[string]interface{})["answer"].(string)
		if answer == "" {
			answer, _ = synthesisRes.(map[string]interface{})["synthesis"].(string)
		}
	}

	// 4. Verification
	verified := false
	verifyRes, err := s.Orchestrator.Execute("verifier_agent.verify_answer", map[string]interface{}{
		"query":     query,
		"answer":    answer,
		"documents": rankedDocs,
	}, 45*time.Second)
	
	if err == nil {
		vMap, _ := verifyRes.(map[string]interface{})
		verified, _ = vMap["is_verified"].(bool)
		if verified && vMap["corrected_answer"] != nil {
			answer = vMap["corrected_answer"].(string)
		}
	}

	// 5. JIT Absorption (Vibrate into subconscious)
	if verified {
		s.Orchestrator.Execute("subconscious_field.vibrate", map[string]interface{}{
			"text":   answer,
			"weight": 1.2,
			"source": "verified_jit",
		}, 5*time.Second)
	}

	return &PipelineResult{
		Success:   true,
		Query:     query,
		Answer:    answer,
		Documents: rankedDocs,
		Verified:  verified,
		Metadata: map[string]interface{}{
			"duration": time.Since(start).String(),
		},
	}, nil
}

func (s *AgentPipelineService) castInterfaceListToMapList(raw []interface{}) []map[string]interface{} {
	res := make([]map[string]interface{}, len(raw))
	for i, v := range raw {
		m, _ := v.(map[string]interface{})
		res[i] = m
	}
	return res
}

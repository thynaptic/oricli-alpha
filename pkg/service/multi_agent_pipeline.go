package service

import (
	"fmt"
	"log"
	"time"
)

type PipelineStageResult struct {
	Success bool                   `json:"success"`
	Result  interface{}            `json:"result,omitempty"`
	Error   string                 `json:"error,omitempty"`
}

type MultiAgentPipelineResult struct {
	Success         bool                            `json:"success"`
	Query           string                          `json:"query"`
	NormalizedQuery string                          `json:"normalized_query"`
	Answer          string                          `json:"answer"`
	Confidence      float64                         `json:"confidence"`
	Citations       []interface{}                   `json:"citations"`
	Metadata        map[string]interface{}          `json:"metadata"`
	PipelineStages  map[string]PipelineStageResult `json:"pipeline_stages"`
}

type MultiAgentPipelineService struct {
	Orchestrator *GoOrchestrator
}

func NewMultiAgentPipelineService(orch *GoOrchestrator) *MultiAgentPipelineService {
	return &MultiAgentPipelineService{Orchestrator: orch}
}

func (s *MultiAgentPipelineService) ExecutePipeline(query string, config map[string]interface{}) (*MultiAgentPipelineResult, error) {
	startTime := time.Now()
	stages := make(map[string]PipelineStageResult)
	
	log.Printf("[Pipeline] Starting multi-agent pipeline for query: %s", query)

	// Stage 1: Query Agent (Sequential as others depend on it)
	queryRes, err := s.Orchestrator.Execute("query_agent.process_query", map[string]interface{}{"query": query}, 30*time.Second)
	if err != nil {
		stages["query_processing"] = PipelineStageResult{Success: false, Error: err.Error()}
		// Fallback to raw query
		queryRes = map[string]interface{}{"normalized": map[string]interface{}{"normalized": query}}
	} else {
		stages["query_processing"] = PipelineStageResult{Success: true, Result: queryRes}
	}

	normalizedQuery := queryRes.(map[string]interface{})["normalized"].(map[string]interface{})["normalized"].(string)

	// Stage 2: Retriever Agent
	retLimit := 20
	if val, ok := config["retrieval_limit"].(int); ok { retLimit = val }
	
	retRes, err := s.Orchestrator.Execute("retriever_agent.process_retrieval", map[string]interface{}{
		"query": normalizedQuery,
		"limit": retLimit,
	}, 60*time.Second)
	
	if err != nil {
		stages["retrieval"] = PipelineStageResult{Success: false, Error: err.Error()}
		return nil, fmt.Errorf("retrieval stage failed: %w", err)
	}
	stages["retrieval"] = PipelineStageResult{Success: true, Result: retRes}

	docs := retRes.(map[string]interface{})["documents"].([]interface{})

	// Stage 3: Reranker Agent
	topK := 10
	if val, ok := config["top_k"].(int); ok { topK = val }
	
	rerankRes, err := s.Orchestrator.Execute("reranker_agent.process_reranking", map[string]interface{}{
		"documents": docs,
		"query":     normalizedQuery,
		"top_k":     topK,
	}, 60*time.Second)
	
	if err != nil {
		stages["reranking"] = PipelineStageResult{Success: false, Error: err.Error()}
		rerankRes = map[string]interface{}{"documents": docs} // Fallback to unranked
	} else {
		stages["reranking"] = PipelineStageResult{Success: true, Result: rerankRes}
	}

	rankedDocs := rerankRes.(map[string]interface{})["documents"].([]interface{})

	// Stage 4: Synthesis Agent
	synthRes, err := s.Orchestrator.Execute("synthesis_agent.synthesize", map[string]interface{}{
		"documents": rankedDocs,
		"query":     normalizedQuery,
	}, 90*time.Second)
	
	if err != nil {
		stages["synthesis"] = PipelineStageResult{Success: false, Error: err.Error()}
		return nil, fmt.Errorf("synthesis stage failed: %w", err)
	}
	stages["synthesis"] = PipelineStageResult{Success: true, Result: synthRes}

	answer := synthRes.(map[string]interface{})["answer"].(string)
	info := synthRes.(map[string]interface{})["information"].(map[string]interface{})

	// Stage 5: Verifier Agent
	verRes, err := s.Orchestrator.Execute("verifier_agent.process_verification", map[string]interface{}{
		"answer":      answer,
		"documents":   rankedDocs,
		"information": info,
	}, 60*time.Second)
	
	if err != nil {
		stages["verification"] = PipelineStageResult{Success: false, Error: err.Error()}
		verRes = map[string]interface{}{"overall_confidence": 0.5}
	} else {
		stages["verification"] = PipelineStageResult{Success: true, Result: verRes}
	}

	// Final Result Assembly
	synthConf := synthRes.(map[string]interface{})["confidence"].(float64)
	verConf := verRes.(map[string]interface{})["overall_confidence"].(float64)
	
	return &MultiAgentPipelineResult{
		Success:         true,
		Query:           query,
		NormalizedQuery: normalizedQuery,
		Answer:          answer,
		Confidence:      (synthConf * 0.6) + (verConf * 0.4),
		Citations:       info["citations"].([]interface{}),
		PipelineStages:  stages,
		Metadata: map[string]interface{}{
			"execution_time": time.Since(startTime).Seconds(),
			"document_count": len(rankedDocs),
		},
	}, nil
}

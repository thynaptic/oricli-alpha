package service

import (
	"fmt"
	"log"
	"sync"
	"time"
)

type ConversationTurn struct {
	Input     string  `json:"input"`
	Response  string  `json:"response"`
	Timestamp float64 `json:"timestamp"`
}

type ConversationalResult struct {
	Text       string                 `json:"text"`
	Confidence float64                `json:"confidence"`
	Diagnostic map[string]interface{} `json:"diagnostic"`
	Success    bool                   `json:"success"`
}

type ConversationalOrchestrator struct {
	Orchestrator *GoOrchestrator
	History      []ConversationTurn
	Mu           sync.RWMutex
}

func NewConversationalOrchestrator(orch *GoOrchestrator) *ConversationalOrchestrator {
	return &ConversationalOrchestrator{
		Orchestrator: orch,
		History:      make([]ConversationTurn, 0),
	}
}

func (s *ConversationalOrchestrator) GenerateResponse(input, context, persona string) (*ConversationalResult, error) {
	log.Printf("[ConvOrch] Generating response for: %s", input)

	// 1. Parallel Analysis
	var wg sync.WaitGroup
	wg.Add(3)

	var linguistic, social, emotional interface{}
	
	go func() {
		defer wg.Done()
		linguistic, _ = s.Orchestrator.Execute("linguistic_priors.analyze_structure", map[string]interface{}{"text": input}, 10*time.Second)
	}()
	
	go func() {
		defer wg.Done()
		social, _ = s.Orchestrator.Execute("social_priors.assess_context", map[string]interface{}{"input": input, "context": context}, 10*time.Second)
	}()
	
	go func() {
		defer wg.Done()
		emotional, _ = s.Orchestrator.Execute("emotional_inference.detect_emotion", map[string]interface{}{"text": input, "context": context}, 10*time.Second)
	}()

	wg.Wait()

	// 2. Optional Knowledge Enrichment
	knowledgeContext := ""
	if len(fmt.Sprintf("%v", input)) > 15 {
		kRes, err := s.Orchestrator.Execute("world_knowledge.enrich_query", map[string]interface{}{"query": input, "context": context}, 20*time.Second)
		if err == nil {
			knowledgeContext = kRes.(map[string]interface{})["knowledge"].(string)
		}
	}

	// 3. Final Generation
	s.Mu.RLock()
	history := s.History
	s.Mu.RUnlock()

	genRes, err := s.Orchestrator.Execute("cognitive_generator.generate_response", map[string]interface{}{
		"input":                input,
		"context":              fmt.Sprintf("%s\n%s", context, knowledgeContext),
		"persona":              persona,
		"conversation_history": history,
		"analysis": map[string]interface{}{
			"linguistic": linguistic,
			"social":     social,
			"emotional":  emotional,
		},
	}, 60*time.Second)

	if err != nil {
		return nil, fmt.Errorf("generation failed: %w", err)
	}

	resMap := genRes.(map[string]interface{})
	responseText := resMap["text"].(string)

	// 4. Update History
	s.Mu.Lock()
	s.History = append(s.History, ConversationTurn{
		Input:     input,
		Response:  responseText,
		Timestamp: float64(time.Now().Unix()),
	})
	if len(s.History) > 20 {
		s.History = s.History[1:]
	}
	s.Mu.Unlock()

	return &ConversationalResult{
		Text:       responseText,
		Confidence: resMap["confidence"].(float64),
		Diagnostic: resMap["diagnostic"].(map[string]interface{}),
		Success:    true,
	}, nil
}

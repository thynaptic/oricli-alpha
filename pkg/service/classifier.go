package service

import (
	"encoding/json"
	"log"
	"os"
	"sync"
)

// DegradationType represents the reason for degradation
type DegradationType string

const (
	DegradationSlow              DegradationType = "slow"
	DegradationMissingDependency DegradationType = "missing_dependency"
	DegradationHalfLoaded        DegradationType = "half_loaded"
	DegradationTimeout           DegradationType = "timeout"
	DegradationPartialFailure    DegradationType = "partial_failure"
	DegradationOffline           DegradationType = "offline"
	DegradationUnknown           DegradationType = "unknown"
)

// DegradedModeClassifier manages fallback routing
type DegradedModeClassifier struct {
	fallbackMappings  map[string][]string
	operationMappings map[string]string // key is "primary_module.primary_operation"
	registry          *ModuleRegistry
	mu                sync.RWMutex
}

// NewDegradedModeClassifier creates a new classifier
func NewDegradedModeClassifier(registry *ModuleRegistry) *DegradedModeClassifier {
	c := &DegradedModeClassifier{
		fallbackMappings:  make(map[string][]string),
		operationMappings: make(map[string]string),
		registry:          registry,
	}
	c.loadDefaultMappings()
	c.loadCustomMappings()
	return c
}

func (c *DegradedModeClassifier) loadDefaultMappings() {
	c.fallbackMappings = map[string][]string{
		"mcts_search_engine":       {"chain_of_thought", "reasoning"},
		"mcts_reasoning":           {"chain_of_thought", "reasoning"},
		"cognitive_generator":      {"neural_text_generator", "text_generation_engine"},
		"neural_text_generator":    {"text_generation_engine"},
		"text_generation_engine":   {"reasoning"},
	}

	c.operationMappings = map[string]string{
		"cognitive_generator.generate_response": "generate_full_response",
		"cognitive_generator.generate":          "generate_full_response",
		"neural_text_generator.generate":        "generate_full_response",
	}
}

func (c *DegradedModeClassifier) loadCustomMappings() {
	mappingsFile := os.Getenv("MAVAIA_FALLBACK_MAPPINGS_FILE")
	if mappingsFile == "" {
		return
	}

	data, err := os.ReadFile(mappingsFile)
	if err != nil {
		log.Printf("[Classifier] Failed to read custom mappings file: %v", err)
		return
	}

	var customMappings map[string][]string
	if err := json.Unmarshal(data, &customMappings); err != nil {
		log.Printf("[Classifier] Failed to parse custom mappings: %v", err)
		return
	}

	c.mu.Lock()
	defer c.mu.Unlock()
	for k, v := range customMappings {
		c.fallbackMappings[k] = v
	}
}

// GetFallbackModule returns the best fallback for a module
func (c *DegradedModeClassifier) GetFallbackModule(name string, operation string) string {
	c.mu.RLock()
	defer c.mu.RUnlock()

	fallbacks, ok := c.fallbackMappings[name]
	if !ok {
		return ""
	}

	for _, fallback := range fallbacks {
		// Verify availability if possible
		if _, ok := c.registry.GetMetadata(fallback); ok {
			return fallback
		}
	}

	return ""
}

// GetFallbackOperation returns the mapped operation for a fallback
func (c *DegradedModeClassifier) GetFallbackOperation(primaryModule, primaryOp, fallbackModule string) string {
	c.mu.RLock()
	defer c.mu.RUnlock()

	key := primaryModule + "." + primaryOp
	if mappedOp, ok := c.operationMappings[key]; ok {
		return mappedOp
	}

	return primaryOp
}

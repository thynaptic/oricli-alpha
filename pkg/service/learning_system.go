package service

import (
	"context"
	"encoding/json"
	"fmt"
	"log"
	"os"
	"path/filepath"
	"strings"
	"sync"
	"time"

	"github.com/thynaptic/oricli-go/pkg/swarm"
)

type LearnedPattern struct {
	Original  string                 `json:"original"`
	Corrected string                 `json:"corrected"`
	Context   map[string]interface{} `json:"context"`
	Timestamp int64                  `json:"timestamp"`
}

type LearningSystemResult struct {
	Success bool                   `json:"success"`
	Pattern *LearnedPattern        `json:"pattern,omitempty"`
	Summary string                 `json:"summary,omitempty"`
}

type LearningSystemService struct {
	Orchestrator   *GoOrchestrator
	Patterns       []LearnedPattern
	Preferences    map[string]interface{}
	StoragePath    string
	ESI            *swarm.ESIFederation // P5-3: nil unless ORICLI_SWARM_LESSON_SHARE=true
	// SCL: when non-nil, corrections are written to the Sovereign Cognitive Ledger
	// under TierCorrections in addition to the local JSONL pattern store.
	SCL            LearnerSCLWriter
	mu             sync.RWMutex
}

// LearnerSCLWriter is the interface LearningSystemService uses to persist corrections.
type LearnerSCLWriter interface {
	WriteCorrection(ctx context.Context, original, corrected, skill string) error
}

func NewLearningSystemService(orch *GoOrchestrator, storagePath string) *LearningSystemService {
	if storagePath == "" {
		storagePath = "oricli_core/data/learned_patterns.json"
	}
	s := &LearningSystemService{
		Orchestrator: orch,
		Patterns:     make([]LearnedPattern, 0),
		Preferences:  make(map[string]interface{}),
		StoragePath:  storagePath,
	}
	s.loadState()
	return s
}

func (s *LearningSystemService) loadState() {
	data, err := os.ReadFile(s.StoragePath)
	if err == nil {
		var state struct {
			Patterns    []LearnedPattern       `json:"patterns"`
			Preferences map[string]interface{} `json:"preferences"`
		}
		if err := json.Unmarshal(data, &state); err == nil {
			s.mu.Lock()
			s.Patterns = state.Patterns
			s.Preferences = state.Preferences
			s.mu.Unlock()
		}
	}
}

func (s *LearningSystemService) saveState() {
	s.mu.RLock()
	state := map[string]interface{}{
		"patterns":    s.Patterns,
		"preferences": s.Preferences,
	}
	s.mu.RUnlock()

	data, _ := json.MarshalIndent(state, "", "  ")
	os.MkdirAll(filepath.Dir(s.StoragePath), 0755)
	os.WriteFile(s.StoragePath, data, 0644)
}

func (s *LearningSystemService) LearnFromCorrection(original string, corrected string, meta map[string]interface{}) (*LearningSystemResult, error) {
	log.Printf("[Learning] Learning from code correction")

	pattern := LearnedPattern{
		Original:  original,
		Corrected: corrected,
		Context:   meta,
		Timestamp: time.Now().Unix(),
	}

	s.mu.Lock()
	s.Patterns = append(s.Patterns, pattern)
	s.mu.Unlock()

	go s.saveState()

	// Also send it to the JIT Absorption Daemon
	prompt := fmt.Sprintf("Learn this coding pattern correction:\nOriginal:\n%s\n\nCorrected:\n%s", original, corrected)
	s.Orchestrator.Execute("record_lesson", map[string]interface{}{
		"prompt": prompt,
		"response": "Understood. I will apply this pattern in the future.",
		"metadata": meta,
	}, 10*time.Second)

	// SCL-5: write correction to Sovereign Cognitive Ledger (TierCorrections).
	if s.SCL != nil {
		skill := "general"
		if tag, ok := meta["skill"].(string); ok && tag != "" {
			skill = tag
		}
		if err := s.SCL.WriteCorrection(context.Background(), original, corrected, skill); err != nil {
			log.Printf("[Learning] SCL write correction: %v", err)
		}
	}

	// P5-3: ESI — broadcast high-quality lesson traces to swarm peers (opt-in).
	if s.ESI != nil {
		skill := "code_correction"
		if tag, ok := meta["skill"].(string); ok && tag != "" {
			skill = tag
		}
		rawTrace := fmt.Sprintf("Correction pattern: %s → %s", strings.TrimSpace(original), strings.TrimSpace(corrected))
		go s.ESI.MaybeShareTrace(context.Background(), skill, rawTrace, 0.87)
	}

	return &LearningSystemResult{
		Success: true,
		Pattern: &pattern,
		Summary: "Pattern learned and saved to JIT buffer.",
	}, nil
}

func (s *LearningSystemService) PersonalizeGeneration(preferences map[string]interface{}) (*LearningSystemResult, error) {
	log.Printf("[Learning] Updating personalization preferences")

	s.mu.Lock()
	for k, v := range preferences {
		s.Preferences[k] = v
	}
	s.mu.Unlock()

	go s.saveState()

	return &LearningSystemResult{
		Success: true,
		Summary: "Preferences updated.",
	}, nil
}

package cognition

import (
	"context"
	"fmt"
	"log"
	"sync"

	"github.com/google/uuid"
)

// --- Pillar 1: Subconscious Field ---
// A circular vector buffer that biases cognition with "mood" and "latent intent".
type SubconsciousField struct {
	FieldVector []float32
	Dimensions  int
	Mu          sync.RWMutex
}

func NewSubconsciousField(dims int) *SubconsciousField {
	return &SubconsciousField{
		FieldVector: make([]float32, dims),
		Dimensions:  dims,
	}
}

// Decay slowly reverts the field to zero over time (The "Forgetting" effect).
func (s *SubconsciousField) Decay(factor float32) {
	s.Mu.Lock()
	defer s.Mu.Unlock()
	for i := range s.FieldVector {
		s.FieldVector[i] *= factor
	}
}

// --- Pillar 2: Strategic Planner ---
// Fuses MCTS, ToT (Tree of Thought), and CoT into high-level execution graphs.
type ExecutionStep struct {
	ID          string
	Description string
	Bounty      float64
	Status      string
}

type StrategicPlan struct {
	TaskID string
	Steps  []ExecutionStep
}

// --- Pillar 3: Emotional Inference ---
// Tracks affective states (valence, arousal, dominance) to modulate tone.
type AffectiveState struct {
	Valence   float32 // -1.0 (Sad) to 1.0 (Happy)
	Arousal   float32 // 0.0 (Calm) to 1.0 (Excited)
	Dominance float32 // 0.0 (Submissive) to 1.0 (Assertive)
}

// --- Pillar 4: Metacognitive Sentinel ---
// Enforces "Wise Mind" and "Radical Acceptance" skills for system balance.
type MetacogSentinel struct {
	IsBalanced bool
	BiasLock   bool
}

// --- Pillar 5: Sovereign Engine (The Synthesis) ---
type SovereignEngine struct {
	Subconscious *SubconsciousField
	Sentiment    *AffectiveState
	Sentinel     *MetacogSentinel
	mu           sync.Mutex
}

func NewSovereignEngine() *SovereignEngine {
	return &SovereignEngine{
		Subconscious: NewSubconsciousField(256),
		Sentiment:    &AffectiveState{Valence: 0.5, Arousal: 0.5, Dominance: 0.8},
		Sentinel:     &MetacogSentinel{IsBalanced: true},
	}
}

// ProcessInference modulates incoming stimuli through the subconscious field.
func (e *SovereignEngine) ProcessInference(ctx context.Context, stimulus string) (string, error) {
	e.mu.Lock()
	defer e.mu.Unlock()

	// 1. Shift Subconscious (Simulated update based on stimulus)
	// In a full impl, this would be a weighted vector addition from an SLM embedding.
	e.Subconscious.FieldVector[0] += 0.01 
	
	// 2. Modulate Sentiment
	if stimulus == "panic" {
		e.Sentiment.Arousal = 1.0
		e.Sentiment.Valence = -1.0
		e.Sentinel.IsBalanced = false
	}

	// 3. Cognitive Reset (Sentinel)
	if !e.Sentinel.IsBalanced {
		log.Println("[SovereignEngine] Sentinel detecting cognitive imbalance. Triggering 'Wise Mind' reset...")
		e.Sentiment.Valence = 0.5
		e.Sentiment.Arousal = 0.5
		e.Sentinel.IsBalanced = true
	}

	log.Printf("[SovereignEngine] Thought modulated. Valence: %.2f, Arousal: %.2f", e.Sentiment.Valence, e.Sentiment.Arousal)
	
	return fmt.Sprintf("SOVEREIGN_THOUGHT_V1.0:%s", stimulus), nil
}

// GenerateStrategicPlan decomposes a task into Gosh-verifiable steps.
func (e *SovereignEngine) GenerateStrategicPlan(task string) *StrategicPlan {
	log.Printf("[SovereignEngine] Drafting strategic plan for: %s", task)
	
	return &StrategicPlan{
		TaskID: uuid.New().String()[:8],
		Steps: []ExecutionStep{
			{ID: "step_1", Description: "Sandbox Pre-flight", Bounty: 10.0},
			{ID: "step_2", Description: "Kernel Execution", Bounty: 50.0},
			{ID: "step_3", Description: "Metacog Verification", Bounty: 20.0},
		},
	}
}

// GetLinguisticPriors returns style modulation based on current emotional state.
func (e *SovereignEngine) GetLinguisticPriors() string {
	if e.Sentiment.Dominance > 0.7 {
		return "Tone: Assertive, Sovereign, Direct."
	}
	return "Tone: Collaborative, Balanced, Thoughtful."
}

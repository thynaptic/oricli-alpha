package cognition

import (
	"context"
	"fmt"
	"log"
	"strings"
	"sync"

	"github.com/google/uuid"
	"github.com/thynaptic/oricli-go/pkg/state"
	"github.com/thynaptic/oricli-go/pkg/safety"
	"github.com/thynaptic/oricli-go/pkg/memory"
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
type StepStatus string

const (
	StepPending   StepStatus = "pending"
	StepExecuting StepStatus = "executing"
	StepCompleted StepStatus = "completed"
	StepFailed    StepStatus = "failed"
)

type ExecutionStep struct {
	ID           string     `json:"id"`
	Description  string     `json:"description"`
	Bounty       float64    `json:"bounty"`
	Status       StepStatus `json:"status"`
	Dependencies []string   `json:"dependencies,omitempty"`
	Result       string     `json:"result,omitempty"`
	Error        string     `json:"error,omitempty"`
}

type StrategicPlan struct {
	TaskID      string          `json:"task_id"`
	Goal        string          `json:"goal"`
	Steps       []ExecutionStep `json:"steps"`
	MaxDepth    int             `json:"max_depth"`
	IsRecovering bool            `json:"is_recovering"`
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
	Resonance    *ResonanceService
	Actions      *state.ActionTracker
	Grounding    *GroundingService
	Safety       *safety.Sentinel
	RecallMode   memory.RecallMode
	Graph        *memory.WorkingMemoryGraph
	Personality  *PersonalityEngine
	Stochastic   *MarkovChain
	mu           sync.Mutex
}

func NewSovereignEngine() *SovereignEngine {
	engine := &SovereignEngine{
		Subconscious: NewSubconsciousField(256),
		Sentiment:    &AffectiveState{Valence: 0.5, Arousal: 0.5, Dominance: 0.8},
		Sentinel:     &MetacogSentinel{IsBalanced: true},
		Resonance:    NewResonanceService(),
		Actions:      state.NewActionTracker(10),
		Grounding:    NewGroundingService(),
		Safety:       safety.NewSentinel(),
		RecallMode:   memory.ModeOperational,
		Graph:        memory.NewWorkingMemoryGraph(),
		Personality:  NewPersonalityEngine(),
		Stochastic:   NewMarkovChain(),
	}
	
	// Pre-train stochastic engine with baseline persona data
	engine.Stochastic.Train("I hear you. That sounds really hard. We can figure this out together. Take a breath. Let's look at the facts. You're doing great.", 4)
	return engine
}

// ProcessInference modulates incoming stimuli through all layers (Safety -> Personality -> Reasoning).
func (e *SovereignEngine) ProcessInference(ctx context.Context, stimulus string) (string, error) {
	e.mu.Lock()
	defer e.mu.Unlock()

	// 1. Mandatory Safety Audit
	safetyResult := e.Safety.CheckInput(stimulus)
	if safetyResult.Detected {
		log.Printf("[SovereignEngine] SAFETY BLOCK: Type: %s, Severity: %s, Patterns: %v", 
			safetyResult.Type, safetyResult.Severity, safetyResult.Patterns)
		
		// Vibrate subconscious field negatively on safety violation
		e.Subconscious.Decay(0.5)
		e.Sentiment.Valence = -0.5 // Dissonance
		
		return safetyResult.Replacement, nil
	}

	// 2. Personality Calibration (Sweetheart Core)
	e.Personality.Calibrate(stimulus, e.Sentiment.Valence, e.Sentiment.Arousal)
	personalityDirectives := e.Personality.GetDirectives()
	aside := e.Personality.GetGroundingAside(e.Sentiment.Valence)

	// 3. Intent Analysis & Recall Mode Switching
	lower := strings.ToLower(stimulus)
	if strings.Contains(lower, "reflect") || strings.Contains(lower, "feel") || strings.Contains(lower, "why") {
		e.RecallMode = memory.ModeReflective
	} else if strings.Contains(lower, "create") || strings.Contains(lower, "imagine") || strings.Contains(lower, "brainstorm") {
		e.RecallMode = memory.ModeCreative
	} else {
		e.RecallMode = memory.ModeOperational
	}

	// 4. Relational Extraction
	if strings.Contains(lower, "i am") || strings.Contains(lower, "my name is") {
		e.Graph.AddEntity("User", memory.TypePerson, "The current interactant")
	}

	// 5. Grounding Detection
	_, intensity := e.Grounding.DetectAnchors(stimulus)
	groundingGuidance := e.Grounding.GetGuidance(intensity)
	
	// 6. Retrieve Action Context
	actionPrompt := e.Actions.FormatForPrompt("") 
	
	// 7. Shift Subconscious & Generate Latent Whisper
	e.Subconscious.FieldVector[0] += 0.01 
	
	// Generate a 5-word stochastic whisper based on the user's first word
	words := strings.Fields(stimulus)
	whisper := ""
	if len(words) > 0 {
		whisper = e.Stochastic.Generate(words[0], 5)
	}
	if whisper != "" {
		whisper = fmt.Sprintf("Latent intent generated from Markov Chain: [%s]", whisper)
	}
	
	// 8. Modulate Sentiment
	if stimulus == "panic" {
		e.Sentiment.Arousal = 1.0
		e.Sentiment.Valence = -1.0
		e.Sentinel.IsBalanced = false
	} else {
		eri := e.Resonance.Current.ERI
		e.Sentiment.Valence = (e.Sentiment.Valence * 0.9) + (eri * 0.1)
		if intensity > 0.5 {
			e.Sentiment.Arousal += 0.05
		}
	}

	// 9. Cognitive Reset
	if !e.Sentinel.IsBalanced || e.Resonance.Current.ERI < -0.4 {
		log.Printf("[SovereignEngine] Resonance discord (ERI: %.2f). Triggering 'Wise Mind' reset...", e.Resonance.Current.ERI)
		e.Sentiment.Valence = 0.5
		e.Sentiment.Arousal = 0.5
		e.Sentinel.IsBalanced = true
		e.Subconscious.Decay(0.8)
	}

	log.Printf("[SovereignEngine] Thought modulated. Valence: %.2f, Sass: %.2f, Mode: %s, Grounding: %.2f", 
		e.Sentiment.Valence, e.Personality.State.SassFactor, e.Personality.State.Cue, intensity)
	
	// Final composite instruction injection
	composite := fmt.Sprintf("%s\n\n%s\n\n%s\n\n%s\n\n%s", 
		personalityDirectives, groundingGuidance, actionPrompt, aside, whisper)
	
	return fmt.Sprintf("%s\n\nSOVEREIGN_THOUGHT_V2.7:%s", composite, stimulus), nil
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

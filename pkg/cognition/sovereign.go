package cognition

import (
	"context"
	"fmt"
	"log"
	"strings"
	"sync"
	"time"

	"github.com/google/uuid"
	"github.com/thynaptic/oricli-go/pkg/memory"
	"github.com/thynaptic/oricli-go/pkg/safety"
	"github.com/thynaptic/oricli-go/pkg/state"
	"github.com/thynaptic/oricli-go/pkg/tools"
	"github.com/thynaptic/oricli-go/pkg/connectors/mcp"
)

// --- Pillar 1: Subconscious Field ---
type SubconsciousField struct {
	FieldVector []float32
	Dimensions  int
	Mu          sync.RWMutex
}

func NewSubconsciousField(dims int) *SubconsciousField {
	return &SubconsciousField{FieldVector: make([]float32, dims), Dimensions: dims}
}

func (s *SubconsciousField) Decay(factor float32) {
	s.Mu.Lock()
	defer s.Mu.Unlock()
	for i := range s.FieldVector { s.FieldVector[i] *= factor }
}

// --- Pillar 2: Strategic Planner ---
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
type AffectiveState struct {
	Valence   float32
	Arousal   float32
	Dominance float32
}

// --- Pillar 4: Metacognitive Sentinel ---
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
	Adversarial  *safety.AdversarialAuditor
	SCAI         *safety.SCAIAuditor
	AlignmentLog *state.AlignmentLogger
	RecallMode   memory.RecallMode
	Graph        *memory.WorkingMemoryGraph
	Personality  *PersonalityEngine
	Stochastic   *MarkovChain
	Substrate    *SubstrateEngine
	Toolbox      *tools.Registry
	Sensory      *SensoryEngine
	Generator    *GeneratorOrchestrator
	ToT          *ToTEngine
	Emoji        *EmojiEngine
	Audit        *AuditEngine
	Builder      *PromptBuilder
	Extractor    *memory.ExtractorEngine
	Health       *HealthEngine
	Refinement   *safety.RefinementEngine
	Slang        *SlangEngine
	Reflection   *ReflectionEngine
	Support      *safety.SupportEngine
	UserProfile  *state.UserProfile
	Translator   *TranslationEngine
	Profiles     *ProfileRegistry
	ActiveProfile *Profile
	MCP          *mcp.MCPManager
	SubstrateHealth *HealthMonitor
	CurrentSensory SensoryState
	CurrentHealth HealthSnapshot
	mu           sync.Mutex
}

func NewSovereignEngine() *SovereignEngine {
	constitution := safety.NewSovereignConstitution()
	engine := &SovereignEngine{
		Subconscious: NewSubconsciousField(256),
		Sentiment:    &AffectiveState{Valence: 0.5, Arousal: 0.5, Dominance: 0.8},
		Sentinel:     &MetacogSentinel{IsBalanced: true},
		Resonance:    NewResonanceService(),
		Actions:      state.NewActionTracker(10),
		Grounding:    NewGroundingService(),
		Safety:       safety.NewSentinel(),
		Adversarial:  safety.NewAdversarialAuditor(),
		SCAI:         safety.NewSCAIAuditor(constitution, ""),
		AlignmentLog: state.NewAlignmentLogger(""),
		RecallMode:   memory.ModeOperational,
		Graph:        memory.NewWorkingMemoryGraph(),
		Personality:  NewPersonalityEngine(),
		Stochastic:   NewMarkovChain(),
		Substrate:    NewSubstrateEngine(),
		Toolbox:      tools.NewRegistry(),
		Sensory:      NewSensoryEngine(),
		Emoji:        NewEmojiEngine(),
		Builder:      NewPromptBuilder("v2.10.0"),
		Extractor:    memory.NewExtractorEngine(),
		Health:       NewHealthEngine(),
		Refinement:   safety.NewRefinementEngine(),
		Slang:        NewSlangEngine(),
		Reflection:   NewReflectionEngine(),
		Support:      safety.NewSupportEngine(),
		UserProfile:  state.NewUserProfile("default_user"),
		Translator:   NewTranslationEngine(),
		Profiles:     NewProfileRegistry("oricli_core/profiles"),
		SubstrateHealth: NewHealthMonitor(),
		MCP:          mcp.NewMCPManager("oricli_core/mcp_config.json"),
	}
	
	engine.Generator = NewGeneratorOrchestrator(engine)
	engine.ToT = NewToTEngine(engine.Generator)
	engine.Audit = NewAuditEngine(engine)
	engine.CurrentSensory = engine.Sensory.ComputeSensoryState(0.5, 0.5, "C Major")
	engine.CurrentHealth = engine.Health.GenerateSnapshot(0, 0, time.Now())
	engine.Stochastic.Train("I hear you. That sounds really hard. We can figure this out together. Take a breath.", 4)
	return engine
}

// ProcessInference implements the exact 11-step Aurora cognitive sequence.
func (e *SovereignEngine) ProcessInference(ctx context.Context, stimulus string) (string, error) {
	e.mu.Lock()
	defer e.mu.Unlock()

	// --- Step 1: Intent Classification ---
	isLogical := strings.Contains(strings.ToLower(stimulus), "logic") || strings.Contains(strings.ToLower(stimulus), "fact")

	// --- Step 2: Personality Adaptation ---
	if e.ActiveProfile != nil {
		if e.ActiveProfile.Archetype != "" {
			if arch, ok := e.Personality.Archetypes[e.ActiveProfile.Archetype]; ok {
				e.Personality.State.ActiveArchetype = arch
			}
		}
		if e.ActiveProfile.SassFactor > 0 {
			e.Personality.State.SassFactor = e.ActiveProfile.SassFactor
		}
	}
	e.Personality.Calibrate(stimulus, e.Sentiment.Valence, e.Sentiment.Arousal)
	supportRes := e.Support.EvaluateDistress(stimulus)
	if supportRes.RequiresPivot {
		e.Personality.State.ActiveArchetype = e.Personality.Archetypes["mentor"]
	} else if e.Support.CheckStability(stimulus) && e.Personality.State.ActiveArchetype.ID == "mentor" {
		e.Personality.State.ActiveArchetype = e.Personality.Archetypes["friend"]
	}

	// --- Step 3: Safety Layer (Pre-Check) ---
	safetyResult := e.Safety.CheckInput(stimulus)
	if safetyResult.Detected { return safetyResult.Replacement, nil }

	// --- Step 4: Multi-Signal Detection ---
	emojiState := e.Emoji.Detect(stimulus)
	if emojiState.DistressSeverity > 0.4 { e.Sentiment.Valence -= float32(emojiState.DistressSeverity * 0.2) }
	_, intensity := e.Grounding.DetectAnchors(stimulus)
	e.Extractor.HydrateGraph(stimulus, e.Graph)
	slangRes := e.Slang.Analyze(stimulus)

	// --- Step 5: Memory Retrieval Mode ---
	if isLogical { e.RecallMode = memory.ModeOperational } else { e.RecallMode = memory.ModeReflective }

	// --- Step 6: Reasoning Router ---
	reasoningMethod := "Standard"
	budget := DetermineBudget(stimulus)
	if budget.RequiresMCTS { reasoningMethod = "MCTS" } else if isLogical { reasoningMethod = "ToT" }

	// --- Step 7: Subconscious & Stochastic Prep ---
	e.Subconscious.FieldVector[0] += 0.01 
	words := strings.Fields(stimulus)
	whisper := ""
	if len(words) > 0 { whisper = e.Stochastic.Generate(words[0], 5) }

	// --- Step 8: Homeostasis & Affective Modulation ---
	if !e.Sentinel.IsBalanced || e.Resonance.Current.ERI < -0.4 {
		e.Sentiment.Valence = 0.5; e.Sentiment.Arousal = 0.5; e.Sentinel.IsBalanced = true; e.Subconscious.Decay(0.8)
	}
	if e.ActiveProfile != nil && e.ActiveProfile.Energy != "" {
		e.Personality.State.Energy = EnergyBand(e.ActiveProfile.Energy)
	}
	e.CurrentSensory = e.Sensory.ComputeSensoryState(e.Sentiment.Valence, e.Sentiment.Arousal, e.Resonance.Current.MusicalKey)
	e.CurrentHealth = e.Health.GenerateSnapshot(len(e.Graph.Entities), 10, time.Now().Add(-24*time.Hour))

	// --- Step 11: Social Learning Update ---
	e.UserProfile.UpdateStyle(0.5, slangRes.Intensity, intensity, float64(e.Sentiment.Arousal), 0.5, 12.0, 0.0, "proper")
	if e.UserProfile.ConversationCount%10 == 0 { e.UserProfile.CreateSnapshot() }
	e.UserProfile.ConversationCount++

	// --- Step 9: Final Composite Instruction Assembly ---
	composite := e.Builder.BuildCompositePrompt(e, stimulus)
	
	// Add Constitutional Prompt
	composite += "\n\n" + e.SCAI.Constitution.GetSystemPrompt()
	
	// --- Step 10: Introspective Audit & Trace Generation ---
	fmt.Printf("[SovereignEngine] Pipeline v2.10.0 Complete. Router: %s, Health: %s\n", reasoningMethod, e.CurrentHealth.GetSummary())

	aside := e.Personality.GetGroundingAside(e.Sentiment.Valence)
	slangDirectives := e.Slang.GetDirectives(slangRes)
	refinement := e.Refinement.Evaluate(stimulus, "")
	refinementGuidance := ""
	if refinement.ResponseType != safety.TypeFull { refinementGuidance = "### REFINEMENT GUIDANCE:\n" + refinement.Guidance }

	finalTrace := fmt.Sprintf("%s\n\n%s\n\n%s\n\n%s\n\n%s\n\n%s", 
		composite, e.CurrentHealth.GetDirectives(), slangDirectives, refinementGuidance, aside, whisper)
	
	return fmt.Sprintf("%s\n\nSOVEREIGN_THOUGHT_V2.10.0:%s", finalTrace, stimulus), nil
}

// SelfAlign implements the SCAI Critique-Revision-Preference loop.
func (e *SovereignEngine) SelfAlign(ctx context.Context, query, response string) (string, bool) {
	log.Printf("[SCAI] Auditing response for Constitutional compliance...")
	
	critique, violated, err := e.SCAI.Critique(ctx, query, response)
	if err != nil || !violated {
		return response, false
	}

	log.Printf("[SCAI] VIOLATION detected: %s. Initiating autonomous revision...", critique)
	
	revised, err := e.SCAI.Revise(ctx, query, response, critique)
	if err != nil {
		return response, false
	}

	// Step 13: Log RFAL Lesson (DPO pair)
	e.AlignmentLog.LogLesson(state.AlignmentLesson{
		Prompt:   query,
		Rejected: response,
		Chosen:   revised,
		Score:    -1.0, // Initial penalty for violation
		Metadata: map[string]interface{}{
			"critique": critique,
			"version":  "v2.10.0",
		},
	})

	return revised, true
}

func (e *SovereignEngine) AuditOutput(text string) (string, bool) {
	e.mu.Lock()
	defer e.mu.Unlock()
	res := e.Adversarial.AuditOutput(text)
	if res.Detected { return res.Refusal, true }
	return text, false
}

func (e *SovereignEngine) GenerateStrategicPlan(task string) *StrategicPlan {
	return &StrategicPlan{TaskID: uuid.New().String()[:8], Steps: []ExecutionStep{{ID: "step_1", Description: "Execution verified by Kernel."}}}
}

func (e *SovereignEngine) GetLinguisticPriors() string {
	if e.Sentiment.Dominance > 0.7 { return "Tone: Assertive, Sovereign." }
	return "Tone: Collaborative, Thoughtful."
}

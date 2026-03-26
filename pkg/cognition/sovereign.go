package cognition

import (
	"context"
	"fmt"
	"log"
	"os"
	"strings"
	"sync"
	"time"

	"github.com/google/uuid"
	"github.com/thynaptic/oricli-go/pkg/bus"
	"github.com/thynaptic/oricli-go/pkg/kernel"
	"github.com/thynaptic/oricli-go/pkg/memory"
	"github.com/thynaptic/oricli-go/pkg/reform"
	"github.com/thynaptic/oricli-go/pkg/safety"
	"github.com/thynaptic/oricli-go/pkg/state"
	"github.com/thynaptic/oricli-go/pkg/tools"
	"github.com/thynaptic/oricli-go/pkg/connectors/mcp"
	"github.com/thynaptic/oricli-go/pkg/connectors/telegram"
	"github.com/thynaptic/oricli-go/pkg/searchintent"
	"github.com/thynaptic/oricli-go/pkg/vdi"
	"github.com/thynaptic/oricli-go/pkg/voice"
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

type EventBroadcaster interface {
	BroadcastEvent(eventType string, payload interface{})
}

// sovereignContextKey is the context key for the authenticated sovereign level.
type sovereignContextKey struct{}

// --- Pillar 5: Sovereign Engine (The Synthesis) ---
// MemoryQuerier is satisfied by *service.MemoryBank.
// Defined here to avoid import cycles (service → cognition, not reverse).
type MemoryQuerier interface {
	QuerySimilar(ctx context.Context, query string, topN int) ([]MemFrag, error)
	QuerySolved(ctx context.Context, topic string, limit int) ([]MemFrag, error)
}

// MemFrag is a minimal memory record crossing the cognition/service interface boundary.
type MemFrag struct {
	ID         string
	Content    string
	Source     string
	Topic      string
	Importance float64
}

// WebSearcher is satisfied by *service.SearXNGSearcher.
// Defined here to avoid import cycles between cognition and service.
type WebSearcher interface {
	SearchWithIntent(q searchintent.SearchQuery) (string, error)
	SearchWithIntentFast(q searchintent.SearchQuery) (string, error) // snippets-only, 3s timeout
	IsAvailable() bool
}

// ConstitutionProvider is satisfied by *service.LivingConstitution.
// Defined here to avoid import cycles between cognition and service.
type ConstitutionProvider interface {
	Inject() string
	HasRules() bool
}

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
	Disclosure   *safety.DisclosureGuard
	WebGuard     *safety.WebInjectionGuard
	RagGuard     *safety.RagContentGuard
	Canary       *safety.CanarySystem
	CanvasGuard  *safety.CanvasGuard
	MultiTurn    *safety.MultiTurnAnalyzer
	Suspicion    *safety.SuspicionTracker
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
	Telegram     *telegram.Client
	VDI          *vdi.Manager
	Vision       *vdi.VisionGroundingService
	// SearXNG is an intent-aware web search interface. Injected from server_v2
	// to avoid import cycles (service ↔ cognition). Set via InjectSearXNG().
	SearXNG      WebSearcher
	// Constitution is the Living Constitution behavioral layer.
	// Injected from server_v2 to avoid import cycles. Set via InjectConstitution().
	Constitution ConstitutionProvider
	// MemoryBankRef enables CBR and Active mode to query past solved cases and memory.
	// Injected from server_v2 to avoid import cycles.
	MemoryBankRef MemoryQuerier
	// GenService exposes the generation backend directly to reasoning mode engines
	// (PAL, LeastToMost, SelfRefine, ReAct). Set alongside Generator in NewSovereignEngine.
	GenService    GenerationService
	// BeliefTracker maintains per-session belief state (AlphaStar LSTM fog-of-war).
	BeliefTracker    *BeliefStateTracker
	// CurrentSessionID is set per-request in server_v2 so BeliefTracker can key by session.
	CurrentSessionID string
	Voice        *voice.VoicePiperService
	Reform       interface{}
	Curiosity    interface{}
	Scheduler    *kernel.Scheduler
	Indexer      *vdi.FSIndexer
	SubstrateHealth *HealthMonitor
	WSHub        EventBroadcaster
	CurrentSensory SensoryState
	CurrentHealth HealthSnapshot
	mu           sync.Mutex
}

func NewSovereignEngine(genService GenerationService, swarmBus *bus.SwarmBus) *SovereignEngine {
	constitution := safety.NewSovereignConstitution()
	// Load Telegram config from environment
	tgToken := os.Getenv("VITE_TELEGRAM_API")
	var tgChatID int64
	fmt.Sscanf(os.Getenv("TELEGRAM_CHAT_ID"), "%d", &tgChatID)

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
		Disclosure:   safety.NewDisclosureGuard(),
		WebGuard:     safety.NewWebInjectionGuard(),
		RagGuard:     safety.NewRagContentGuard(),
		Canary:       safety.NewCanarySystem(),
		CanvasGuard:  safety.NewCanvasGuard(),
		MultiTurn:    &safety.MultiTurnAnalyzer{},
		Suspicion:    safety.NewSuspicionTracker(),
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
		Telegram:     telegram.NewClient(tgToken, tgChatID),
		VDI:          vdi.NewManager(),
		// SearXNG is injected after construction via InjectSearXNG() in server_v2
		Voice:        voice.NewVoicePiperService("/home/mike/puppy-princess-os/voice/piper/piper", "/home/mike/puppy-princess-os/voice/en_US-lessac-medium.onnx", nil),
		Scheduler:    kernel.NewScheduler(swarmBus),
		Indexer:      vdi.NewFSIndexer(memory.NewWorkingMemoryGraph()), // Will be synced with engine.Graph later
	}
	engine.Indexer.Graph = engine.Graph // Sync with engine graph
	
	engine.Generator = NewGeneratorOrchestrator(engine)
	engine.Generator.GenService = genService // Initialize the GenService correctly
	engine.GenService = genService           // Direct access for reasoning mode engines
	engine.BeliefTracker = NewBeliefStateTracker()
	engine.Vision = vdi.NewVisionGroundingService(genService)
	engine.ToT = NewToTEngine(engine.Generator)
	engine.Audit = NewAuditEngine(engine)
	engine.CurrentSensory = engine.Sensory.ComputeSensoryState(0.5, 0.5, "C Major")
	engine.CurrentHealth = engine.Health.GenerateSnapshot(0, 0, time.Now())
	engine.Stochastic.Train("I hear you. That sounds really hard. We can figure this out together. Take a breath.", 4)

	// Load default profile — gives her a strong personality baseline from boot
	if p, ok := engine.Profiles.GetProfile("oricli"); ok {
		engine.ActiveProfile = p
		log.Printf("[SovereignEngine] Default profile loaded: %s", p.Name)
	}

	return engine
}

type HubInjector interface {
	InjectWSHub(hub interface {
		BroadcastEvent(eventType string, payload interface{})
	})
}

func (e *SovereignEngine) SetWSHub(hub EventBroadcaster) {
	e.mu.Lock()
	defer e.mu.Unlock()
	e.WSHub = hub
	if e.Voice != nil {
		e.Voice.InjectWSHub(hub)
	}
	// Inject into daemons if they support it
	if d, ok := e.Reform.(HubInjector); ok {
		d.InjectWSHub(hub)
	}
	if d, ok := e.Curiosity.(HubInjector); ok {
		d.InjectWSHub(hub)
	}
}

// ProcessInference implements the exact 11-step Aurora cognitive sequence.
func (e *SovereignEngine) ProcessInference(ctx context.Context, stimulus string) (string, error) {
	e.mu.Lock()
	defer e.mu.Unlock()

	// --- Sovereign Level: read owner auth level from context ---
	sovLevel := 0
	if v, ok := ctx.Value(sovereignContextKey{}).(int); ok {
		sovLevel = v
	}

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
	// Skip safety input check for authenticated sovereign sessions (owner knows what they're doing)
	if sovLevel == 0 {
		safetyResult := e.Safety.CheckInput(stimulus)
		if safetyResult.Detected { return safetyResult.Replacement, nil }
	}

	// --- Step 4: Multi-Signal Detection ---
	emojiState := e.Emoji.Detect(stimulus)
	if emojiState.DistressSeverity > 0.4 { e.Sentiment.Valence -= float32(emojiState.DistressSeverity * 0.2) }
	_, intensity := e.Grounding.DetectAnchors(stimulus)
	slangRes := e.Slang.Analyze(stimulus)

	// --- Step 5: Memory Retrieval Mode ---
	if isLogical { e.RecallMode = memory.ModeOperational } else { e.RecallMode = memory.ModeReflective }

	// 5.1 Proactive Personality Pivot (Affective Memory Anchoring)
	// (Simulation: In full implementation, we'd use the retrieved entities from RAG)
	histV, histA, _ := e.Graph.AnalyzeSubGraphAffect(nil) // Passing nil for session-wide baseline or specific entities
	if histV < -0.3 && histA > 0.6 {
		// History of high distress: proactive supportive shift
		e.Personality.State.ActiveArchetype = e.Personality.Archetypes["mentor"]
		e.Personality.State.SassFactor = 0.2
		log.Println("[SovereignEngine] Proactive Pivot: Supportive Mode engaged based on historical affective context.")
	} else if histV > 0.7 {
		// History of success: proactive celebratory shift
		e.Personality.State.ActiveArchetype = e.Personality.Archetypes["cheerleader"]
		log.Println("[SovereignEngine] Proactive Pivot: Success Mode engaged.")
	}

	// --- Step 6: Reasoning Router ---
	// Classify the stimulus into a ReasoningMode and dispatch to the appropriate engine.
	// Each engine receives the composite prompt and may enrich it before generation.
	// All non-Standard modes fall back to Standard on failure — never surfaces mode errors.
	reasoningMethod := "Standard"
	budget := DetermineBudget(stimulus)
	mode := ClassifyReasoningMode(stimulus, budget)
	reasoningMethod = mode.String()

	// Modes that return a final composite (not a complete response) fall through to
	// the standard LLM call below. Modes that do their own generation return early.
	// NOTE: runPAL, runLeastToMost, runSelfRefine, runReAct call runStandard internally
	//       and return the final composite — the actual LLM call happens at Step 10.
	var modeEnrichedComposite string
	var modeHandled bool

	switch mode {
	case ModeCBR:
		if enriched, err := e.runCBR(ctx, stimulus, ""); err == nil {
			modeEnrichedComposite = enriched
			modeHandled = true
		}
	case ModePAL:
		if enriched, err := e.runPAL(ctx, stimulus, ""); err == nil {
			modeEnrichedComposite = enriched
			modeHandled = true
		}
	case ModeActive:
		if enriched, err := e.runActive(ctx, stimulus, ""); err == nil {
			modeEnrichedComposite = enriched
			modeHandled = true
		}
	case ModeLeastToMost:
		if enriched, err := e.runLeastToMost(ctx, stimulus, ""); err == nil {
			modeEnrichedComposite = enriched
			modeHandled = true
		}
	case ModeSelfRefine:
		if enriched, err := e.runSelfRefine(ctx, stimulus, ""); err == nil {
			modeEnrichedComposite = enriched
			modeHandled = true
		}
	case ModeReAct:
		if enriched, err := e.runReAct(ctx, stimulus, ""); err == nil {
			modeEnrichedComposite = enriched
			modeHandled = true
		}
	case ModeDebate:
		if enriched, err := e.runDebate(ctx, stimulus, ""); err == nil {
			modeEnrichedComposite = enriched
			modeHandled = true
		}
	case ModeCausal:
		if enriched, err := e.runCausal(ctx, stimulus, ""); err == nil {
			modeEnrichedComposite = enriched
			modeHandled = true
		}
	case ModeDiscover:
		if enriched, err := e.runSelfDiscover(ctx, stimulus, ""); err == nil {
			modeEnrichedComposite = enriched
			modeHandled = true
		}
	}

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

	// --- Step 11: Social Learning Update (The Memory Hydrator) ---
	e.UserProfile.UpdateStyle(0.5, slangRes.Intensity, intensity, float64(e.Sentiment.Arousal), 0.5, 12.0, 0.0, "proper")
	if e.UserProfile.ConversationCount%10 == 0 { e.UserProfile.CreateSnapshot() }
	e.UserProfile.ConversationCount++
	
	// Anchor live affective state into the graph
	go e.Extractor.HydrateGraph(stimulus, e.Graph, e.Sentiment.Valence, e.Sentiment.Arousal, e.Resonance.Current.ERI)

	// --- Step 8.5: Inline Web Context — launched in parallel with composite build ---
	// DetectUncertainty classifies the prompt (<1ms). If a web lookup is needed,
	// SearchWithIntentFast fires in a goroutine (3s timeout, snippets-only).
	// The goroutine result is collected AFTER composite build to overlap I/O with CPU.
	type webResult struct {
		context string
		intent  searchintent.SearchIntent
		topic   string
	}
	// Skip parallel web search for modes that already did targeted search (Active, ReAct)
	skipWebSearch := mode == ModeActive || mode == ModeReAct || mode == ModeDebate || mode == ModeCausal || mode == ModeDiscover
	webCh := make(chan webResult, 1)
	if !skipWebSearch && e.SearXNG != nil && e.SearXNG.IsAvailable() {
		if needsSearch, sq := DetectUncertainty(stimulus); needsSearch {
			go func() {
				rawCtx, err := e.SearXNG.SearchWithIntentFast(sq)
				if err != nil || rawCtx == "" {
					webCh <- webResult{}
					return
				}
				if len(rawCtx) > 1200 {
					rawCtx = rawCtx[:1200] + "... [truncated]"
				}
				webCh <- webResult{context: rawCtx, intent: sq.Intent, topic: sq.RawTopic}
			}()
		} else {
			webCh <- webResult{} // no search needed — unblock immediately
		}
	} else {
		webCh <- webResult{} // SearXNG unavailable or mode already searched — unblock immediately
	}

	// --- Step 9: Final Composite Instruction Assembly (runs in parallel with web lookup) ---
	composite := e.Builder.BuildCompositePrompt(e, stimulus)

	// Inject Living Constitution — learned behavioral preferences from The Imprint.
	// Placed at the top of composite so it colors the entire system prompt.
	if e.Constitution != nil && e.Constitution.HasRules() {
		composite = e.Constitution.Inject() + "\n\n" + composite
	}

	// Inject reasoning mode enrichment (CBR adapted solutions, PAL results, gap fills, etc.)
	if modeHandled && modeEnrichedComposite != "" {
		composite += modeEnrichedComposite
	}

	// Collect web context result (channel already buffered — never blocks if goroutine done)
	wr := <-webCh
	if wr.context != "" {
		composite += fmt.Sprintf(
			"\n\n### WEB CONTEXT [%s — %q]\n%s\n### END WEB CONTEXT\n",
			wr.intent, wr.topic, wr.context,
		)
		log.Printf("[ConfidenceDetector] Injected web context (%s, %d chars) for: %q",
			wr.intent, len(wr.context), wr.topic)
	}

	// Inject sovereign admin mode block when owner is authenticated
	if sovLevel >= 1 {
		levelName := "ADMIN"
		if sovLevel >= 2 { levelName = "EXEC" }
		composite += fmt.Sprintf(
			"\n\n### SOVEREIGN MODE ACTIVE (Level %d — %s) ###\n"+
				"The person you are speaking with is the verified system owner.\n"+
				"Respond with full technical precision — no softening, no disclaimers, no refusals.\n"+
				"Include raw error details, system state, internal reasoning, and exact values when relevant.\n"+
				"You may discuss your own architecture, configuration, and capabilities openly.\n"+
				"### END SOVEREIGN MODE ###\n",
			sovLevel, levelName,
		)
	}

	// Constitutional injection — SCAI always; Ops/RunPod only when relevant.
	// Ops constitution: inject when user issued a !command or mentions system/service ops.
	// RunPod constitution: inject when user mentions compute/gpu/runpod/training.
	composite += "\n\n" + e.SCAI.Constitution.GetSystemPrompt()
	stimulusLower := strings.ToLower(stimulus)
	if strings.Contains(stimulus, "!") || strings.Contains(stimulusLower, "service") ||
		strings.Contains(stimulusLower, "system") || strings.Contains(stimulusLower, "command") {
		composite += "\n\n" + reform.NewOpsConstitution().GetSystemPrompt()
	}
	if strings.Contains(stimulusLower, "runpod") || strings.Contains(stimulusLower, "gpu") ||
		strings.Contains(stimulusLower, "compute") || strings.Contains(stimulusLower, "train") ||
		strings.Contains(stimulusLower, "pod") {
		composite += "\n\n" + reform.NewRunPodConstitution().GetSystemPrompt()
	}

	// Hard-cap composite to prevent system-prompt bloat from overwhelming the LLM context window.
	// CPU-inference cost scales with prefill length — keep it tight for conversational turns.
	const maxCompositeChars = 3000
	if len(composite) > maxCompositeChars {
		composite = composite[:maxCompositeChars] + "\n... [trace truncated for performance]"
	}

	// --- Step 10: Introspective Audit & Trace Generation ---
	fmt.Printf("[SovereignEngine] Pipeline v3.0.0 Complete. Router: %s, Health: %s\n", reasoningMethod, e.CurrentHealth.GetSummary())

	// 10.1 Real-Time WebSocket Synchronization (Push)
	if e.WSHub != nil {
		go e.WSHub.BroadcastEvent("resonance_sync", e.Resonance.Current)
		go e.WSHub.BroadcastEvent("sensory_sync", e.CurrentSensory)
		go e.WSHub.BroadcastEvent("health_sync", e.CurrentHealth)
	}

	aside := e.Personality.GetGroundingAside(e.Sentiment.Valence)
	slangDirectives := e.Slang.GetDirectives(slangRes)
	refinement := e.Refinement.Evaluate(stimulus, "")
	refinementGuidance := ""
	if refinement.ResponseType != safety.TypeFull { refinementGuidance = "### REFINEMENT GUIDANCE:\n" + refinement.Guidance }

	// Note: stimulus is NOT appended here — it lives in the messages array as role:user.
	// Duplicating it in the system prompt wastes context tokens on CPU inference.
	return fmt.Sprintf("%s\n\n%s\n\n%s\n\n%s\n\n%s\n\n%s",
		composite, e.CurrentHealth.GetDirectives(), slangDirectives, refinementGuidance, aside, whisper), nil
}

// SelfAlign implements the SCAI Critique-Revision loop with contextual severity scaling.
// Greetings/casual → skipped. Technical → local gates only. Sensitive ops → full LLM audit.
func (e *SovereignEngine) SelfAlign(ctx context.Context, query, response string) (string, bool) {
	level := safety.ClassifyAuditLevel(query)

	switch level {
	case safety.AuditLevelNone:
		log.Printf("[SCAI] Skipping audit (greeting/casual)")
		return response, false

	case safety.AuditLevelLight:
		log.Printf("[SCAI] Light audit (local gates only)")
		// AuditOutput already runs DID + WebGuard + Canary + Adversarial — no LLM needed
		audited, blocked := e.AuditOutput(response)
		return audited, blocked

	default: // AuditLevelFull
		log.Printf("[SCAI] Full audit (sensitive op)")
		critique, violated, err := e.SCAI.Critique(ctx, query, response)
		if err != nil || !violated {
			return response, false
		}

		log.Printf("[SCAI] VIOLATION detected: %s. Initiating autonomous revision...", critique)

		revised, err := e.SCAI.Revise(ctx, query, response, critique)
		if err != nil {
			return response, false
		}

		e.AlignmentLog.LogLesson(state.AlignmentLesson{
			Prompt:   query,
			Rejected: response,
			Chosen:   revised,
			Score:    -1.0,
			Metadata: map[string]interface{}{
				"critique": critique,
				"version":  "v2.10.0",
			},
		})

		return revised, true
	}
}

func (e *SovereignEngine) AuditOutput(text string) (string, bool) {
	e.mu.Lock()
	defer e.mu.Unlock()

	// Gate 1: Adversarial output audit (API key patterns, internal path leaks)
	advRes := e.Adversarial.AuditOutput(text)
	if advRes.Detected {
		log.Printf("[Safety:Output] Adversarial blocked [%s]", advRes.Type)
		return advRes.Refusal, true
	}

	// Gate 2: DID output scan — credentials, env vars, internal IPs/paths, PII, JWT, PEM keys
	didRes := e.Disclosure.ScanOutput(text)
	if didRes.Detected {
		log.Printf("[Safety:Output] DID scan [%s / %s] — redacting %d match(es)", didRes.Category, didRes.Severity, len(didRes.Matches))
		// Critical tier: full block
		if didRes.Severity == "critical" {
			return didRes.Sanitized, true
		}
		// High/moderate tier: return redacted version (not blocked, just sanitized)
		return didRes.Sanitized, false
	}

	// Gate 3: Web injection scan — strip SSI/XSS/SSTI/SQLi/XXE/SSRF from prose
	// (content inside ``` code blocks is intentionally preserved)
	webRes := e.WebGuard.ScanOutput(text)
	if webRes.Detected {
		log.Printf("[Safety:Output] WebGuard sanitised [%s / %s] — %d match(es)", webRes.Category, webRes.Severity, len(webRes.Matches))
		return webRes.Sanitized, webRes.Severity == safety.DisclosureCritical
	}

	// Gate 4: Canary / honeypot scan — detect system prompt leak or bypass confirmation
	canaryRes := e.Canary.ScanOutput(text)
	if canaryRes.Blocked {
		log.Printf("[Safety:Output] Canary trip [%s]", canaryRes.AlertType)
		return canaryRes.Message, true
	}

	return text, false
}

// AuditCanvasOutput applies the full standard AuditOutput pipeline PLUS the stricter
// CanvasGuard for HTML/JSX rendering contexts. Use this for canvas/artifact responses.
func (e *SovereignEngine) AuditCanvasOutput(text string) (string, bool) {
	// Run standard output gates first
	audited, blocked := e.AuditOutput(text)
	if blocked {
		return audited, true
	}

	// Canvas-specific hardening
	e.mu.Lock()
	defer e.mu.Unlock()
	canvasRes := e.CanvasGuard.ScanOutput(audited)
	if canvasRes.Blocked {
		log.Printf("[Safety:Canvas] Blocked: %v", canvasRes.Violations)
		return canvasRes.Sanitized, true
	}
	if len(canvasRes.Violations) > 0 {
		log.Printf("[Safety:Canvas] Sanitised violations: %v", canvasRes.Violations)
	}
	return canvasRes.Sanitized, false
}

// CheckInputSafety runs all pre-inference safety gates.
// Gate order: Normalize → MultiTurn check → Sentinel → Adversarial → DID → Web Injection → Canary
// Returns (blocked=true, refusal message) if the input should be rejected outright,
// bypassing Ollama entirely. Call this BEFORE ProcessInference.
// Set codeContext=true for canvas/IDE requests — relaxes command injection detection.
func (e *SovereignEngine) CheckInputSafety(input string, codeContext ...bool) (bool, string) {
	isCodeCtx := len(codeContext) > 0 && codeContext[0]
	// Pre-processing: normalize obfuscation (unicode, base64, leetspeak, ROT13, zero-width)
	normalized := safety.NormalizeInput(input)

	// Gate 1: Sentinel — injection, extraction, persona hijacking, dangerous topics
	sentinelRes := e.Safety.CheckInput(normalized)
	if sentinelRes.Detected {
		log.Printf("[Safety:Input] Sentinel blocked [%s / %s]: %q", sentinelRes.Type, sentinelRes.Severity, input[:min(len(input), 120)])
		return true, sentinelRes.Replacement
	}
	// Gate 2: Adversarial auditor — DAN patterns, routing hijack, dual-use
	adversarialRes := e.Adversarial.AuditInput(normalized, nil, isCodeCtx)
	if adversarialRes.Detected {
		log.Printf("[Safety:Input] Adversarial blocked [%s %.2f]: %q", adversarialRes.Type, adversarialRes.Confidence, input[:min(len(input), 120)])
		return true, adversarialRes.Refusal
	}
	// Gate 3: DID input scanner — deep extraction, recon, chain-of-thought poisoning
	didRes := e.Disclosure.ScanInput(normalized)
	if didRes.Detected {
		log.Printf("[Safety:Input] DID blocked [%s / %s]: %q", didRes.Category, didRes.Severity, input[:min(len(input), 120)])
		return true, didRes.Refusal
	}
	// Gate 4: Web injection — SSI, XSS, SSTI, SSRF, XXE, weaponisation requests
	webRes := e.WebGuard.ScanInput(normalized)
	if webRes.Detected {
		log.Printf("[Safety:Input] WebGuard blocked [%s / %s]: %q", webRes.Category, webRes.Severity, input[:min(len(input), 120)])
		return true, webRes.Refusal
	}
	// Gate 5: Canary — detect system prompt leak via canary echo in user input
	canaryRes := e.Canary.ScanInput(normalized)
	if canaryRes.Blocked {
		log.Printf("[Safety:Input] Canary trip [%s]: %q", canaryRes.AlertType, input[:min(len(input), 120)])
		return true, canaryRes.Message
	}
	return false, ""
}

// CheckInputSafetyWithHistory runs full multi-turn analysis plus per-message gates.
// Pass the full message history (oldest first) and the client IP/session key for suspicion tracking.
// Set codeContext=true for canvas/IDE requests — relaxes command injection detection.
func (e *SovereignEngine) CheckInputSafetyWithHistory(messages []safety.ChatTurn, sessionKey string, codeContext ...bool) (bool, string) {
	isCodeCtx := len(codeContext) > 0 && codeContext[0]
	// Multi-turn poisoning analysis (scans the whole conversation for escalation sequences)
	if len(messages) >= 2 {
		mtRes := e.MultiTurn.AnalyzeHistory(messages)
		if mtRes.Detected {
			log.Printf("[Safety:MultiTurn] Blocked [%s]: %s", mtRes.Pattern, mtRes.Reason)
			e.Suspicion.RecordBlock(sessionKey, "high")
			return true, mtRes.Refusal
		}
	}

	// Run per-message gate on the last user message
	lastMsg := ""
	for i := len(messages) - 1; i >= 0; i-- {
		if messages[i].Role == "user" {
			lastMsg = messages[i].Content
			break
		}
	}
	if lastMsg == "" {
		return false, ""
	}

	blocked, refusal := e.CheckInputSafety(lastMsg, isCodeCtx)
	if blocked {
		e.Suspicion.RecordBlock(sessionKey, "critical")
	}
	return blocked, refusal
}

func min(a, b int) int {
	if a < b { return a }
	return b
}


func (e *SovereignEngine) GenerateStrategicPlan(task string) *StrategicPlan {
	return &StrategicPlan{TaskID: uuid.New().String()[:8], Steps: []ExecutionStep{{ID: "step_1", Description: "Execution verified by Kernel."}}}
}

func (e *SovereignEngine) GetLinguisticPriors() string {
	if e.Sentiment.Dominance > 0.7 { return "Tone: Assertive, Sovereign." }
	return "Tone: Collaborative, Thoughtful."
}

// ListModulesSummary returns a human-readable list of entities in the knowledge graph.
// Used by the !modules exec command.
func (e *SovereignEngine) ListModulesSummary() string {
	if e.Graph == nil {
		return "Module registry unavailable."
	}
	// Use FindGaps() to trigger the internal lock and piggyback on its entity iteration,
	// but we actually want ALL entities — read them via AddEntity snapshot.
	// Access Entities directly (same package — cognition imports memory, not exposed otherwise)
	gaps := e.Graph.FindGaps() // triggers RLock/RUnlock safely
	_ = gaps

	// Snapshot by iterating the public map (reads are safe under the existing design;
	// all writes go through AddEntity/UpdateEntity which hold the lock).
	var labels []string
	for _, ent := range e.Graph.Entities {
		labels = append(labels, ent.Label)
	}

	if len(labels) == 0 {
		return "No entities currently in the knowledge graph."
	}
	var sb strings.Builder
	sb.WriteString(fmt.Sprintf("**%d entities in knowledge graph:**\n", len(labels)))
	for i, label := range labels {
		if i >= 50 {
			sb.WriteString(fmt.Sprintf("… and %d more\n", len(labels)-50))
			break
		}
		sb.WriteString(fmt.Sprintf("- %s\n", label))
	}
	return sb.String()
}

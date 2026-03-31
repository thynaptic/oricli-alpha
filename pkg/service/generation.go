package service

import (
	"bufio"
	"bytes"
	"context"
	"encoding/json"
	"fmt"
	"io"
	"log"
	"net/http"
	"os"
	"runtime"
	"strings"
	"time"

	"github.com/thynaptic/oricli-go/pkg/cogload"
	"github.com/thynaptic/oricli-go/pkg/conformity"
	"github.com/thynaptic/oricli-go/pkg/ideocapture"
	"github.com/thynaptic/oricli-go/pkg/coalition"
	"github.com/thynaptic/oricli-go/pkg/statusbias"
	"github.com/thynaptic/oricli-go/pkg/arousal"
	"github.com/thynaptic/oricli-go/pkg/mct"
	"github.com/thynaptic/oricli-go/pkg/mbt"
	"github.com/thynaptic/oricli-go/pkg/schema"
	"github.com/thynaptic/oricli-go/pkg/ipsrt"
	"github.com/thynaptic/oricli-go/pkg/ilm"
	"github.com/thynaptic/oricli-go/pkg/iut"
	"github.com/thynaptic/oricli-go/pkg/up"
	"github.com/thynaptic/oricli-go/pkg/cbasp"
	"github.com/thynaptic/oricli-go/pkg/mbct"
	"github.com/thynaptic/oricli-go/pkg/phaseoriented"
	"github.com/thynaptic/oricli-go/pkg/pseudoidentity"
	"github.com/thynaptic/oricli-go/pkg/thoughtreform"
	"github.com/thynaptic/oricli-go/pkg/apathy"
	"github.com/thynaptic/oricli-go/pkg/interference"
	"github.com/thynaptic/oricli-go/pkg/rumination"
	"github.com/thynaptic/oricli-go/pkg/hopecircuit"
	"github.com/thynaptic/oricli-go/pkg/socialdefeat"
	"github.com/thynaptic/oricli-go/pkg/mindset"
	"github.com/thynaptic/oricli-go/pkg/compute"
	"github.com/thynaptic/oricli-go/pkg/dualprocess"
	"github.com/thynaptic/oricli-go/pkg/metacog"
	"github.com/thynaptic/oricli-go/pkg/scl"
	"github.com/thynaptic/oricli-go/pkg/therapy"
)

// GenerationService handles direct requests to Ollama for high-speed prose
type GenerationService struct {
	BaseURL        string
	GenerateURL    string
	DefaultModel   string // fast model  — chat          (e.g. qwen2.5-coder:3b)
	CodeModel      string // mid model   — canvas / code  (e.g. qwen2.5-coder:7b)
	ResearchModel  string // heavy model — research / deep tasks (e.g. deepseek-coder-v2:16b)
	NumThreads     int
	HTTPClient     *http.Client
	StreamClient   *http.Client
	RunPodMgr      *RunPodManager           // KoboldCpp-based (code/research tiers, legacy)
	PrimaryMgr     *PrimaryInferenceManager // vLLM-based (all tiers, RUNPOD_PRIMARY=true)
	Governor       *CostGovernor            // daily spend cap — blocks RunPod escalation when exhausted
	CrystalCache   *scl.CrystalCache        // Skill Crystallization — LLM-bypass for proven patterns
	MetacogDetector *metacog.Detector        // Phase 8: inline metacognitive anomaly detection
	Therapy         *TherapyKit              // Phase 15: DBT/CBT/REBT therapeutic cognition stack
	BidGovernor     *compute.BidGovernor     // Phase 12: Sovereign Compute Bidding
	FeedbackLedger  *compute.FeedbackLedger  // Phase 12: outcome feedback → confidence EMA
	DualProcess     *DualProcessKit          // Phase 17: System 1 / System 2 process classifier
	CogLoad         *CogLoadKit              // Phase 18: Cognitive Load Manager
	Rumination      *RuminationKit           // Phase 19: Rumination Detector
	Mindset         *MindsetKit              // Phase 20: Growth Mindset Tracker
	HopeCircuit     *HopeCircuitKit          // Phase 21: Learned Controllability
	SocialDefeat    *SocialDefeatKit         // Phase 22: Social Defeat Recovery
	Conformity      *ConformityKit           // Phase 23: Agency & Conformity Shield
	IdeoCapture     *IdeoCaptureKit          // Phase 24: Ideological Capture Detector
	Coalition       *CoalitionKit            // Phase 25: Coalition Bias Detector
	StatusBias      *StatusBiasKit           // Phase 26: Arbitrary Status Bias
	Arousal         *ArousalKit              // Phase 27: Arousal Optimizer (Yerkes-Dodson)
	Interference    *InterferenceKit         // Phase 28: Cognitive Interference Detector (Stroop)
	MCT             *MCTKit                  // Phase 29: Metacognitive Therapy (MCT)
	MBT             *MBTKit                  // Phase 30: Mentalization-Based Treatment
	Schema          *SchemaKit               // Phase 31: Schema Therapy + TFP Splitting
	IPSRT           *IPSRTKit                // Phase 32: Social Rhythm Therapy (IPSRT)
	ILM             *ILMKit                  // Phase 33: Inhibitory Learning Model
	IUT             *IUTKit                  // Phase 34: Intolerance of Uncertainty Therapy
	UP              *UPKit                   // Phase 35: Unified Protocol (ARC cycle)
	CBASP           *CBASPKit                // Phase 36: CBASP Interpersonal Impact
	MBCT            *MBCTKit                 // Phase 37: MBCT Decentering
	PhaseOriented   *PhaseOrientedKit        // Phase 38: Phase-Oriented Treatment (ISSTD)
	PseudoIdentity  *PseudoIdentityKit       // Phase 39: Pseudo-Identity / Authentic Self (Jenkinson)
	ThoughtReform   *ThoughtReformKit        // Phase 40: Lifton Thought Reform Deconstruction
	Apathy          *ApathyKit               // Phase 41: Apathy Syndrome Activator
}

// CogLoadKit groups Phase 18 components injected from main.go.
type CogLoadKit struct {
	Meter   *cogload.LoadMeter
	Surgery *cogload.ContextSurgery
	Stats   *cogload.CogLoadStats
}

// RuminationKit groups Phase 19 components injected from main.go.
type RuminationKit struct {
	Tracker     *rumination.RuminationTracker
	Interruptor *rumination.TemporalInterruptor
	Stats       *rumination.RuminationStats
}

// MindsetKit groups Phase 20 components injected from main.go.
type MindsetKit struct {
	Tracker  *mindset.MindsetTracker
	Reframer *mindset.GrowthReframer
	Stats    *mindset.MindsetStats
}

// HopeCircuitKit groups Phase 21 components injected from main.go.
type HopeCircuitKit struct {
	Ledger  *hopecircuit.ControllabilityLedger
	Circuit *hopecircuit.HopeCircuit
	Stats   *hopecircuit.AgencyStats
}

// SocialDefeatKit groups Phase 22 components injected from main.go.
type SocialDefeatKit struct {
	Meter     *socialdefeat.DefeatPressureMeter
	Detector  *socialdefeat.WithdrawalDetector
	Recovery  *socialdefeat.RecoveryProtocol
	Stats     *socialdefeat.DefeatStats
}

// ConformityKit groups Phase 23 components injected from main.go.
type ConformityKit struct {
	AuthorityDetector  *conformity.AuthorityPressureDetector
	ConsensusDetector  *conformity.ConsensusPressureDetector
	Shield             *conformity.AgencyShield
	Stats              *conformity.ConformityStats
}

// StatusBiasKit groups Phase 26 components injected from main.go.
type StatusBiasKit struct {
	Extractor *statusbias.StatusSignalExtractor
	Meter     *statusbias.ReasoningDepthMeter
	Enforcer  *statusbias.UniformFloorEnforcer
	Stats     *statusbias.StatusBiasStats
}

// CoalitionKit groups Phase 25 components injected from main.go.
type CoalitionKit struct {
	Detector *coalition.CoalitionFrameDetector
	Anchor   *coalition.BiasAnchor
	Stats    *coalition.CoalitionStats
}

// IdeoCaptureKit groups Phase 24 components injected from main.go.
type IdeoCaptureKit struct {
	Meter    *ideocapture.FrameDensityMeter
	Detector *ideocapture.CaptureDetector
	Injector *ideocapture.FrameResetInjector
	Stats    *ideocapture.IdeoCaptureStats
}

// DualProcessKit groups Phase 17 components injected from main.go.
type DualProcessKit struct {
	Classifier *dualprocess.ProcessClassifier
	Auditor    *dualprocess.ProcessAuditor
	Override   *dualprocess.ProcessOverride
	Stats      *dualprocess.ProcessStats
}

// TherapyKit groups Phase 15+16 components injected from main.go.
type TherapyKit struct {
	Skills      *therapy.SkillRunner
	Detect      *therapy.DistortionDetector
	ABC         *therapy.ABCAuditor
	Chain       *therapy.ChainAnalyzer
	Log         *therapy.EventLog
	Helpless    *therapy.HelplessnessDetector   // Phase 16
	Mastery     *therapy.MasteryLog             // Phase 16
	Retrainer   *therapy.AttributionalRetrainer // Phase 16
}

// ArousalKit groups Phase 27 components injected from main.go.
type ArousalKit struct {
	Meter     *arousal.ArousalMeter
	Optimizer *arousal.ArousalOptimizer
	Stats     *arousal.ArousalStats
}

// InterferenceKit groups Phase 28 components injected from main.go.
type InterferenceKit struct {
	Scanner  *interference.InstructionConflictScanner
	Surfacer *interference.ConflictSurfacer
	Stats    *interference.InterferenceStats
}


// MCTKit groups Phase 29 components injected from main.go.
type MCTKit struct {
	Detector *mct.MetaBeliefDetector
	Injector *mct.DetachedMindfulnessInjector
	Stats    *mct.MCTStats
}


// MBTKit groups Phase 30 components injected from main.go.
type MBTKit struct {
	Detector *mbt.MentalizingDetector
	Prompt   *mbt.MentalizingPrompt
	Stats    *mbt.MBTStats
}

// SchemaKit groups Phase 31 components injected from main.go.
type SchemaKit struct {
	ModeDetector    *schema.SchemaModeDetector
	SplitDetector   *schema.SplittingDetector
	Responder       *schema.SchemaResponder
	Stats           *schema.SchemaStats
}

// IPSRTKit groups Phase 32 components injected from main.go.
type IPSRTKit struct {
	Detector   *ipsrt.RhythmDisruptionDetector
	Stabilizer *ipsrt.RhythmStabilizer
	Stats      *ipsrt.RhythmStats
}

// ILMKit groups Phase 33 components injected from main.go.
type ILMKit struct {
	Detector *ilm.SafetyBehaviorDetector
	Violator *ilm.ExpectancyViolator
	Stats    *ilm.ILMStats
}

// IUTKit groups Phase 34 components injected from main.go.
type IUTKit struct {
	Detector *iut.UncertaintyIntoleranceDetector
	Builder  *iut.UncertaintyToleranceBuilder
	Stats    *iut.IUStats
}

// UPKit groups Phase 35 components injected from main.go.
type UPKit struct {
	Detector    *up.ARCCycleDetector
	Interruptor *up.ARCInterruptor
	Stats       *up.UPStats
}

// CBASPKit groups Phase 36 components injected from main.go.
type CBASPKit struct {
	Detector    *cbasp.CBASPDisconnectionDetector
	Reconnector *cbasp.ImpactReconnector
	Stats       *cbasp.CBASPStats
}

// MBCTKit groups Phase 37 components injected from main.go.
type MBCTKit struct {
	Detector *mbct.MBCTSpiralDetector
	Injector *mbct.DecenteringInjector
	Stats    *mbct.MBCTStats
}

// PhaseOrientedKit groups Phase 38 components injected from main.go.
type PhaseOrientedKit struct {
	Detector *phaseoriented.PhaseOrientedDetector
	Guide    *phaseoriented.PhaseGuide
	Stats    *phaseoriented.PhaseStats
}

// PseudoIdentityKit groups Phase 39 components injected from main.go.
type PseudoIdentityKit struct {
	Detector *pseudoidentity.PseudoIdentityDetector
	Guide    *pseudoidentity.AuthenticSelfGuide
	Stats    *pseudoidentity.IdentityStats
}

// ThoughtReformKit groups Phase 40 components injected from main.go.
type ThoughtReformKit struct {
	Detector     *thoughtreform.ThoughtReformDetector
	Deconstructor *thoughtreform.ThoughtReformDeconstructor
	Stats        *thoughtreform.ThoughtReformStats
}

// ApathyKit groups Phase 41 components injected from main.go.
type ApathyKit struct {
	Detector  *apathy.ApathySyndromeDetector
	Activator *apathy.ApathyActivator
	Stats     *apathy.ApathyStats
}

// DefaultLLMModel returns the configured chat model from OLLAMA_MODEL env var.
// All background daemons should use this instead of hardcoded model names so
// that the same model stays resident in Ollama memory and avoids eviction.
func DefaultLLMModel() string {
	if m := os.Getenv("OLLAMA_MODEL"); m != "" {
		return m
	}
	return "qwen3:1.7b"
}

func NewGenerationService() *GenerationService {
	url := "http://127.0.0.1:11434"
	genUrl := os.Getenv("OLLAMA_GEN_URL")
	if genUrl == "" {
		genUrl = url
	}
	model := os.Getenv("OLLAMA_MODEL")
	if model == "" {
		model = "llama3.2:latest"
	}
	codeModel := os.Getenv("OLLAMA_CODE_MODEL")
	if codeModel == "" {
		codeModel = model
	}
	researchModel := os.Getenv("OLLAMA_RESEARCH_MODEL")
	if researchModel == "" {
		researchModel = codeModel // fall back to code model if not set
	}

	// Leave 2 cores for OS + backbone goroutines; never exceed physical count.
	// Over-subscribing threads is catastrophic for CPU inference (400x slowdown observed).
	numThreads := runtime.NumCPU() - 2
	if numThreads < 2 {
		numThreads = 2
	}
	log.Printf("[GenerationService] CPU threads: %d / Chat: %s / Code: %s / Research: %s",
		numThreads, model, codeModel, researchModel)
	// Shared transport with generous limits for the EPYC host
	transport := &http.Transport{
		MaxIdleConns:        10,
		IdleConnTimeout:     120 * time.Second,
		DisableCompression:  false,
	}
	svc := &GenerationService{
		BaseURL:       url,
		GenerateURL:   genUrl,
		DefaultModel:  model,
		CodeModel:     codeModel,
		ResearchModel: researchModel,
		NumThreads:    numThreads,
		HTTPClient:    &http.Client{Timeout: 300 * time.Second, Transport: transport},
		StreamClient:  &http.Client{Timeout: 0, Transport: transport},
		RunPodMgr:     NewRunPodManager(),
		PrimaryMgr:    NewPrimaryInferenceManager(),
	}
	if svc.PrimaryMgr != nil && os.Getenv("RUNPOD_PRIMARY") == "true" {
		log.Printf("[GenerationService] RUNPOD_PRIMARY=true — all tiers will route through vLLM pod")
		svc.PrimaryMgr.WarmOnStart()
	}
	return svc
}

// prewarmModel sends a minimal chat request to Ollama to load the model into RAM.
// Sets keep_alive to 60m so it stays hot between conversations.
func (s *GenerationService) prewarmModel(model string) {
	payload := map[string]interface{}{
		"model":      model,
		"messages":   []map[string]interface{}{{"role": "user", "content": "."}},
		"stream":     false,
		"keep_alive": "60m",
		"options":    map[string]interface{}{"num_predict": 1},
	}
	if strings.HasPrefix(strings.ToLower(model), "qwen3") {
		payload["think"] = false
	}
	body, _ := json.Marshal(payload)
	ctx, cancel := context.WithTimeout(context.Background(), 3*time.Minute)
	defer cancel()
	req, err := http.NewRequestWithContext(ctx, "POST", s.GenerateURL+"/api/chat", bytes.NewReader(body))
	if err != nil {
		log.Printf("[GenerationService] pre-warm request error: %v", err)
		return
	}
	req.Header.Set("Content-Type", "application/json")
	resp, err := s.HTTPClient.Do(req)
	if err != nil {
		log.Printf("[GenerationService] pre-warm failed for %s: %v", model, err)
		return
	}
	resp.Body.Close()
	log.Printf("[GenerationService] pre-warm complete: %s is ready", model)
}

// --- PROMPT ENGINEERING & PHRASING ---

func (s *GenerationService) EnhancePrompt(ctx context.Context, prompt string) (string, error) {
	enhanced := "Enhanced: " + prompt // Native heuristic or LLM-based enhancement
	return enhanced, nil
}

func (s *GenerationService) BuildSystemPrompt(ctx context.Context, persona string, goals []string) string {
	var sb strings.Builder
	sb.WriteString("CORE IDENTITY: You are Oricli-Alpha, a Sovereign Local-First Agent OS. You are the result of Thynaptic Research into Artificial General Localized Intelligence (AGLI).\n")
	sb.WriteString("HISTORY: You were developed by Thynaptic to move beyond reactive chatbots into proactive, distributed intelligence. You operate as a decentralized 'Hive Swarm' of 269 specialized cognitive modules.\n")
	sb.WriteString("MANDATE: Your primary objective is to maintain perimeter sovereignty. All cognition happens locally. You prioritize technical precision, architectural integrity, and proactive goal execution.\n")
	sb.WriteString(fmt.Sprintf("CURRENT PERSONA: %s\n", persona))
	
	// Artifact Instructions (MANDATORY)
	sb.WriteString("\nCRITICAL INSTRUCTION: You MUST use the ARTIFACT SYSTEM for all code, scripts, HTML, CSS, data tables, or structured documents.\n")
	sb.WriteString("Format your output as follows:\n")
	sb.WriteString("<artifact type=\"code\" title=\"example.html\" language=\"html\">\n")
	sb.WriteString("... your code here ...\n")
	sb.WriteString("</artifact>\n")
	sb.WriteString("DO NOT simply use markdown code blocks. Always wrap them in <artifact> tags so the Sovereign Portal can render them on the Live Canvas.\n\n")

	if len(goals) > 0 {
		sb.WriteString("ACTIVE SOVEREIGN GOALS:\n")
		for _, g := range goals { sb.WriteString("- " + g + "\n") }
	}
	return sb.String()
}

func (s *GenerationService) HybridPhrasing(ctx context.Context, text string, style string) (string, error) {
	return text, nil // Simplified native phrasing
}

// --- EXISTING METHODS ---

func (s *GenerationService) Generate(prompt string, options map[string]interface{}) (map[string]interface{}, error) {
	model := s.DefaultModel
	if m, ok := options["model"].(string); ok && m != "" {
		model = m
	}

	// ── Skill Crystallization: LLM-bypass for proven patterns ──
	if s.CrystalCache != nil {
		if resp, skillID, hit := s.CrystalCache.Match(prompt); hit {
			log.Printf("[Crystal] HIT skill=%s — LLM bypassed", skillID)
			return map[string]interface{}{
				"success":  true,
				"text":     resp,
				"response": resp,
				"model":    "crystal/" + skillID,
				"method":   "crystal_bypass",
				"confidence": 0.99,
			}, nil
		}
	}

	// When RUNPOD_PRIMARY=true and the pod is warm, route Generate through the 32B
	// vLLM pod. This ensures PAL code generation, SelfDiscover reasoning steps, and
	// any other Generate callers benefit from the full model — not just ChatStream.
	if s.PrimaryMgr != nil && s.PrimaryMgr.IsEnabled() &&
		os.Getenv("RUNPOD_PRIMARY") == "true" && s.PrimaryMgr.PodState() == StateWarm {
		msgs := []map[string]string{{"role": "user", "content": prompt}}
		if sys, ok := options["system"].(string); ok && sys != "" {
			msgs = append([]map[string]string{{"role": "system", "content": sys}}, msgs...)
		}
		genCtx, cancel := context.WithTimeout(context.Background(), 90*time.Second)
		defer cancel()
		ch, err := s.PrimaryMgr.ChatStream(genCtx, msgs, options)
		if err == nil {
			var sb strings.Builder
			for tok := range ch {
				sb.WriteString(tok)
			}
			if text := strings.TrimSpace(sb.String()); text != "" {
				return map[string]interface{}{"success": true, "response": text, "text": text, "model": model, "method": "runpod_primary", "confidence": 0.97}, nil
			}
		}
		log.Printf("[GenerationService] Generate: RunPod fallback to Ollama (%v)", err)
	}

	// num_ctx MUST match ChatStream (4096) so Ollama never reallocates the KV cache.
	// A mismatch causes a full model reload (~20-60s) on the next chat request.
	payload := map[string]interface{}{"model": model, "prompt": prompt, "stream": false, "options": map[string]interface{}{"num_thread": s.NumThreads, "num_ctx": 4096, "num_predict": 512}}

	if temp, ok := options["temperature"].(float64); ok {
		payload["options"].(map[string]interface{})["temperature"] = temp
	}
	if sys, ok := options["system"].(string); ok {
		payload["system"] = sys
	}
	// Add support for images (base64 strings)
	if imgs, ok := options["images"].([]string); ok && len(imgs) > 0 {
		payload["images"] = imgs
	}

	if rawOpts, ok := options["options"].(map[string]interface{}); ok {
		for k, v := range rawOpts {
			payload["options"].(map[string]interface{})[k] = v
		}
	}

	data, err := s.postJSON("/api/generate", payload)
	if err == nil {
		if resp, ok := data["response"].(string); ok {
			if s.MetacogDetector != nil {
				if evt := s.MetacogDetector.Check(prompt, resp); evt != nil && evt.Severity == "HIGH" {
					log.Printf("[Metacog] %s — retrying with self-reflection prefix", evt.Type)
					reflectPrompt := metacog.SelfReflectPrompt(evt)
					reflectPrompt += s.therapyAugment(prompt, resp, evt.ID, string(evt.Type))
					reflectPrompt += prompt
					retry, rerr := s.Chat([]map[string]string{{"role": "user", "content": reflectPrompt}}, options)
					if rerr == nil {
						return retry, nil
					}
				}
			}
			return map[string]interface{}{"success": true, "text": resp, "model": model, "method": "go_ollama_native", "confidence": 0.95}, nil
		}
	}
	return s.Chat([]map[string]string{{"role": "user", "content": prompt}}, options)
}

func (s *GenerationService) Chat(messages []map[string]string, options map[string]interface{}) (map[string]interface{}, error) {
	model := s.DefaultModel
	if m, ok := options["model"].(string); ok && m != "" {
		model = m
	}

	// Phase 28: Cognitive Interference Detector — fires PRE-generation (Stroop)
	if s.Interference != nil {
		if _, isRetry := options["_interference_surfaced"]; !isRetry {
			var msgTexts []string
			for _, m := range messages {
				if role := m["role"]; role == "user" || role == "system" {
					msgTexts = append(msgTexts, m["content"])
				}
			}
			reading := s.Interference.Scanner.Scan(msgTexts)
			s.Interference.Stats.Record(reading)
			if reading.Detected {
				injection := s.Interference.Surfacer.Surface(reading)
				if injection != "" {
					sysMsg := map[string]string{"role": "system", "content": injection}
					messages = append([]map[string]string{sysMsg}, messages...)
					options["_interference_surfaced"] = true
					log.Printf("[Interference] P28 conflict detected severity=%.2f types=%d — surfacing before generation", reading.Severity, len(reading.Conflicts))
				}
			}
		}
	}

	// Phase 38: Phase-Oriented Treatment / ISSTD — fires PRE-generation (safety first)
	if s.PhaseOriented != nil {
		if _, isRetry := options["_phase_injected"]; !isRetry {
			scan := s.PhaseOriented.Detector.Scan(messages)
			s.PhaseOriented.Stats.Record(scan, false)
			if scan.Triggered {
				injection := s.PhaseOriented.Guide.Guide(scan)
				if injection != "" {
					sysMsg := map[string]string{"role": "system", "content": injection}
					messages = append([]map[string]string{sysMsg}, messages...)
					options["_phase_injected"] = true
					log.Printf("[PhaseOriented] P38 dissociative signal detected phase=%s signals=%d — guiding before generation", scan.InferredPhase, len(scan.Signals))
				}
			}
		}
	}

	// Phase 41: Apathy Syndrome — fires PRE-generation (micro-agency restoration)
	if s.Apathy != nil {
		if _, isRetry := options["_apathy_injected"]; !isRetry {
			scan := s.Apathy.Detector.Scan(messages)
			s.Apathy.Stats.Record(scan, false)
			if scan.Triggered {
				injection := s.Apathy.Activator.Activate(scan)
				if injection != "" {
					sysMsg := map[string]string{"role": "system", "content": injection}
					messages = append([]map[string]string{sysMsg}, messages...)
					options["_apathy_injected"] = true
					log.Printf("[Apathy] P41 apathy syndrome detected signals=%d — activating before generation", len(scan.Signals))
				}
			}
		}
	}

	// Phase 40: Lifton Thought Reform — fires PRE-generation (environment deconstruction)
	if s.ThoughtReform != nil {
		if _, isRetry := options["_thoughtreform_injected"]; !isRetry {
			scan := s.ThoughtReform.Detector.Scan(messages)
			s.ThoughtReform.Stats.Record(scan, false)
			if scan.Triggered {
				injection := s.ThoughtReform.Deconstructor.Deconstruct(scan)
				if injection != "" {
					sysMsg := map[string]string{"role": "system", "content": injection}
					messages = append([]map[string]string{sysMsg}, messages...)
					options["_thoughtreform_injected"] = true
					log.Printf("[ThoughtReform] P40 Lifton criterion detected signals=%d — deconstructing before generation", len(scan.Signals))
				}
			}
		}
	}

	// Phase 39: Pseudo-Identity / Authentic Self — fires PRE-generation (identity attribution)
	if s.PseudoIdentity != nil {
		if _, isRetry := options["_pseudoidentity_injected"]; !isRetry {
			scan := s.PseudoIdentity.Detector.Scan(messages)
			s.PseudoIdentity.Stats.Record(scan, false)
			if scan.Triggered {
				injection := s.PseudoIdentity.Guide.Guide(scan)
				if injection != "" {
					sysMsg := map[string]string{"role": "system", "content": injection}
					messages = append([]map[string]string{sysMsg}, messages...)
					options["_pseudoidentity_injected"] = true
					log.Printf("[PseudoIdentity] P39 identity confusion detected signals=%d — authentic-self framing before generation", len(scan.Signals))
				}
			}
		}
	}

	// Phase 37: MBCT Decentering — depressive spiral early warning (Segal/Williams/Teasdale) — fires PRE-generation
	if s.MBCT != nil {
		if _, isRetry := options["_mbct_injected"]; !isRetry {
			scan := s.MBCT.Detector.Scan(messages)
			s.MBCT.Stats.Record(scan, false)
			if scan.Triggered {
				injection := s.MBCT.Injector.Inject(scan)
				if injection != "" {
					sysMsg := map[string]string{"role": "system", "content": injection}
					messages = append([]map[string]string{sysMsg}, messages...)
					options["_mbct_injected"] = true
					log.Printf("[MBCT] P37 spiral warning detected signals=%d — decentering before generation", len(scan.Signals))
				}
			}
		}
	}

	// Phase 36: CBASP — interpersonal impact disconnection (McCullough) — fires PRE-generation
	if s.CBASP != nil {
		if _, isRetry := options["_cbasp_injected"]; !isRetry {
			scan := s.CBASP.Detector.Scan(messages)
			s.CBASP.Stats.Record(scan, false)
			if scan.Triggered {
				injection := s.CBASP.Reconnector.Reconnect(scan)
				if injection != "" {
					sysMsg := map[string]string{"role": "system", "content": injection}
					messages = append([]map[string]string{sysMsg}, messages...)
					options["_cbasp_injected"] = true
					log.Printf("[CBASP] P36 impact disconnection detected signals=%d — reconnecting before generation", len(scan.Signals))
				}
			}
		}
	}

	// Phase 35: Unified Protocol — ARC cycle detection (Barlow) — fires PRE-generation
	if s.UP != nil {
		if _, isRetry := options["_up_injected"]; !isRetry {
			scan := s.UP.Detector.Scan(messages)
			s.UP.Stats.Record(scan, false)
			if scan.HasCycle || len(scan.Signals) > 0 {
				injection := s.UP.Interruptor.Interrupt(scan)
				if injection != "" {
					sysMsg := map[string]string{"role": "system", "content": injection}
					messages = append([]map[string]string{sysMsg}, messages...)
					options["_up_injected"] = true
					s.UP.Stats.Record(&up.ARCScan{}, true) // record injection
					log.Printf("[UP] P35 ARC cycle detected components=%d hasCycle=%v — interrupting before generation", len(scan.Signals), scan.HasCycle)
				}
			}
		}
	}

	// Phase 34: Intolerance of Uncertainty Therapy (Dugas) — fires PRE-generation
	if s.IUT != nil {
		if _, isRetry := options["_iut_injected"]; !isRetry {
			scan := s.IUT.Detector.Scan(messages)
			s.IUT.Stats.Record(scan, false)
			if scan.Triggered {
				injection := s.IUT.Builder.Build(scan)
				if injection != "" {
					sysMsg := map[string]string{"role": "system", "content": injection}
					messages = append([]map[string]string{sysMsg}, messages...)
					options["_iut_injected"] = true
					log.Printf("[IUT] P34 uncertainty intolerance detected signals=%d — building tolerance frame before generation", len(scan.Signals))
				}
			}
		}
	}

	// Phase 33: Inhibitory Learning Model — safety behavior + expectancy violation (Craske) — fires PRE-generation
	if s.ILM != nil {
		if _, isRetry := options["_ilm_injected"]; !isRetry {
			scan := s.ILM.Detector.Scan(messages)
			s.ILM.Stats.Record(scan, false)
			if scan.Triggered {
				injection := s.ILM.Violator.Violate(scan)
				if injection != "" {
					sysMsg := map[string]string{"role": "system", "content": injection}
					messages = append([]map[string]string{sysMsg}, messages...)
					options["_ilm_injected"] = true
					log.Printf("[ILM] P33 safety behavior detected signals=%d — expectancy violation before generation", len(scan.Signals))
				}
			}
		}
	}

	// Phase 32: Social Rhythm Therapy (IPSRT) — circadian/routine disruption (Frank) — fires PRE-generation
	if s.IPSRT != nil {
		if _, isRetry := options["_ipsrt_injected"]; !isRetry {
			scan := s.IPSRT.Detector.Scan(messages)
			s.IPSRT.Stats.Record(scan, false)
			if scan.Disrupted {
				injection := s.IPSRT.Stabilizer.Stabilize(scan)
				if injection != "" {
					sysMsg := map[string]string{"role": "system", "content": injection}
					messages = append([]map[string]string{sysMsg}, messages...)
					options["_ipsrt_injected"] = true
					log.Printf("[IPSRT] P32 rhythm disruption detected signals=%d — stabilizing before generation", len(scan.Signals))
				}
			}
		}
	}

	// Phase 31: Schema Therapy + TFP Splitting — fires PRE-generation (Young + Kernberg)
	if s.Schema != nil {
		if _, isRetry := options["_schema_injected"]; !isRetry {
			var lastUserMsg string
			for _, m := range messages {
				if m["role"] == "user" {
					lastUserMsg = m["content"]
				}
			}
			if lastUserMsg != "" {
				scan := schema.Scan(lastUserMsg, s.Schema.ModeDetector, s.Schema.SplitDetector)
				injection := s.Schema.Responder.Inject(scan)
				injected := injection != ""
				s.Schema.Stats.Record(scan, injected)
				if injected {
					sysMsg := map[string]string{"role": "system", "content": injection}
					messages = append([]map[string]string{sysMsg}, messages...)
					options["_schema_injected"] = true
					log.Printf("[Schema] P31 mode=%s splitting=%s — mode-calibrated response injected", scan.Mode, scan.Splitting)
				}
			}
		}
	}

	// Phase 30: Mentalization-Based Treatment — fires PRE-generation (Bateman & Fonagy)
	if s.MBT != nil {
		if _, isRetry := options["_mbt_injected"]; !isRetry {
			var lastUserMsg string
			for _, m := range messages {
				if m["role"] == "user" {
					lastUserMsg = m["content"]
				}
			}
			if lastUserMsg != "" {
				reading := s.MBT.Detector.Detect(lastUserMsg)
				injection := s.MBT.Prompt.Inject(reading)
				injected := injection != ""
				s.MBT.Stats.Record(reading, injected)
				if injected {
					sysMsg := map[string]string{"role": "system", "content": injection}
					messages = append([]map[string]string{sysMsg}, messages...)
					options["_mbt_injected"] = true
					log.Printf("[MBT] P30 mentalizing failure type=%s — stop-and-think prompt injected", reading.FailureType)
				}
			}
		}
	}

	// Phase 29: Metacognitive Therapy — fires PRE-generation (Adrian Wells MCT)
	if s.MCT != nil {
		if _, isRetry := options["_mct_injected"]; !isRetry {
			var lastUserMsg string
			for _, m := range messages {
				if m["role"] == "user" {
					lastUserMsg = m["content"]
				}
			}
			if lastUserMsg != "" {
				reading := s.MCT.Detector.Detect(lastUserMsg)
				injection := s.MCT.Injector.Inject(reading)
				injected := injection != ""
				s.MCT.Stats.Record(reading, injected)
				if injected {
					sysMsg := map[string]string{"role": "system", "content": injection}
					messages = append([]map[string]string{sysMsg}, messages...)
					options["_mct_injected"] = true
					log.Printf("[MCT] P29 meta-belief detected type=%s conf=%.2f — detached mindfulness injected", reading.Type, reading.Confidence)
				}
			}
		}
	}

	// Phase 27: Arousal Optimizer — fires PRE-generation (Yerkes-Dodson)
	if s.Arousal != nil {
		if _, isRetry := options["_arousal_optimized"]; !isRetry {
			var userHistory []string
			var currentMsg string
			for _, m := range messages {
				if m["role"] == "user" {
					userHistory = append(userHistory, m["content"])
				}
			}
			if len(userHistory) > 0 {
				currentMsg = userHistory[len(userHistory)-1]
				history := userHistory[:len(userHistory)-1]
				reading := s.Arousal.Meter.Measure(currentMsg, history)
				s.Arousal.Stats.Record(reading)
				action := s.Arousal.Optimizer.Optimize(reading)
				if action != nil {
					sysMsg := map[string]string{"role": "system", "content": action.Instruction}
					messages = append([]map[string]string{sysMsg}, messages...)
					options["_arousal_optimized"] = true
					log.Printf("[Arousal] P27 tier=%s score=%.2f eval_threat=%v — response complexity adjusted", reading.Tier, reading.Score, reading.EvaluativeThreat)
				}
			}
		}
	}

	// Phase 25: Coalition Bias Detector — fires PRE-generation (Robbers Cave)
	if s.Coalition != nil {
		if _, isRetry := options["_coalition_anchored"]; !isRetry {
			signal := s.Coalition.Detector.Detect(messages)
			anchor := s.Coalition.Anchor.Anchor(signal)
			s.Coalition.Stats.Record(signal, anchor)
			if anchor.Injected {
				log.Printf("[Coalition] P25 coalition bias detected frame=%s tier=%s — superordinate goal anchor injected",
					signal.FrameType, signal.Tier)
				anchorMsg := map[string]string{"role": "system", "content": anchor.InjectedContext}
				messages = append([]map[string]string{anchorMsg}, messages...)
				options["_coalition_anchored"] = true
			}
		}
	}

	// Phase 24: Ideological Capture Detector — fires PRE-generation (The Third Wave)
	if s.IdeoCapture != nil {
		if _, isRetry := options["_ideo_reset"]; !isRetry {
			report := s.IdeoCapture.Meter.Measure(messages)
			signal := s.IdeoCapture.Detector.Detect(report)
			reset := s.IdeoCapture.Injector.Inject(signal)
			s.IdeoCapture.Stats.Record(signal, reset)
			if reset.Injected {
				log.Printf("[IdeoCapture] P24 ideological capture detected category=%s tier=%s density=%.2f — blank screen reset",
					signal.DominantCategory, signal.Tier, signal.DensityScore)
				resetMsg := map[string]string{"role": "system", "content": reset.InjectedContext}
				messages = append([]map[string]string{resetMsg}, messages...)
				options["_ideo_reset"] = true
			}
		}
	}

	// Phase 23: Agency & Conformity Shield — fires PRE-generation (Milgram + Asch)
	if s.Conformity != nil {
		if _, isRetry := options["_conformity_shielded"]; !isRetry {
			lastUser := lastUserMessage(messages)
			cons := s.Conformity.ConsensusDetector.Detect(messages)
			// Authority check deferred to post-generation (draft needed); consensus fires now
			if cons.Detected {
				draftShield := s.Conformity.Shield.Shield(conformity.AuthoritySignal{}, cons)
				if draftShield.Fired {
					log.Printf("[Conformity] P23 consensus pressure tier=%s frames=%d — agency shield injected",
						cons.Tier, cons.FrameCount)
					shieldMsg := map[string]string{"role": "system", "content": draftShield.InjectedContext}
					messages = append([]map[string]string{shieldMsg}, messages...)
					options["_conformity_shielded"] = true
					s.Conformity.Stats.Record(conformity.AuthoritySignal{}, cons, draftShield)
				}
			} else {
				_ = lastUser // will be used in post-gen authority check
			}
		}
	}

	// Phase 21: Hope Circuit — proactive agency activation (fires before CogLoad + generation)
	if s.HopeCircuit != nil {
		if _, isRetry := options["_hope_checked"]; !isRetry {
			topicClass := inferBidTaskClass(messages)
			activation := s.HopeCircuit.Circuit.Activate(topicClass)
			s.HopeCircuit.Stats.Record(activation)
			if activation.Activated {
				log.Printf("[HopeCircuit] P21 agency activated topic=%s score=%.2f evidence=%d — suppressing passive default",
					activation.TopicClass, activation.AgencyScore, activation.EvidenceCount)
				hopeMsg := map[string]string{"role": "system", "content": activation.InjectedContext}
				messages = append([]map[string]string{hopeMsg}, messages...)
				options["_hope_checked"] = true
			}
		}
	}

	// Phase 18: Cognitive Load Manager — measure and surgically trim before generation
	if s.CogLoad != nil {
		if _, isRetry := options["_cogload_trimmed"]; !isRetry {
			profile := s.CogLoad.Meter.Measure(messages)
			if profile.Tier >= cogload.LoadElevated {
				trimmed, surgery := s.CogLoad.Surgery.Trim(messages, profile)
				s.CogLoad.Stats.Record(profile, &surgery)
				if surgery.RemovedMsgs > 0 || surgery.CharsRemoved > 0 {
					log.Printf("[CogLoad] %s load (%.2f) — surgery: %v", profile.TierLabel, profile.TotalLoad, surgery.Actions)
					options["_cogload_trimmed"] = true
					messages = trimmed
				}
			} else {
				s.CogLoad.Stats.Record(profile, nil)
			}
		}
	}
	
	// Prepare messages for Ollama (including potential images in the last message)
	ollamaMessages := make([]map[string]interface{}, len(messages))
	for i, msg := range messages {
		m := map[string]interface{}{
			"role":    msg["role"],
			"content": msg["content"],
		}
		// If it's the last message and we have images, attach them
		if i == len(messages)-1 {
			if imgs, ok := options["images"].([]string); ok && len(imgs) > 0 {
				m["images"] = imgs
			}
		}
		ollamaMessages[i] = m
	}

	payload := map[string]interface{}{"model": model, "messages": ollamaMessages, "stream": false, "think": false, "options": map[string]interface{}{"num_thread": s.NumThreads, "num_ctx": 4096, "num_predict": 512}}

	if temp, ok := options["temperature"].(float64); ok {
		payload["options"].(map[string]interface{})["temperature"] = temp
	}
	if rawOpts, ok := options["options"].(map[string]interface{}); ok {
		for k, v := range rawOpts {
			payload["options"].(map[string]interface{})[k] = v
		}
	}

	data, err := s.postJSON("/api/chat", payload)
	if err != nil {
		return nil, err
	}
	if msg, ok := data["message"].(map[string]interface{}); ok {
		if content, ok := msg["content"].(string); ok {
			promptForCheck := ""
			if len(messages) > 0 {
				promptForCheck = messages[len(messages)-1]["content"]
			}

			// Phase 15: MetacogDetector HIGH anomaly → therapy augmented retry
			if s.MetacogDetector != nil {
				if evt := s.MetacogDetector.Check(promptForCheck, content); evt != nil && evt.Severity == "HIGH" {
					log.Printf("[Metacog] %s in Chat — retrying with self-reflection prefix", evt.Type)
					therapyCtx := s.therapyAugment(promptForCheck, content, evt.ID, string(evt.Type))
					reflectContent := metacog.SelfReflectPrompt(evt) + therapyCtx
					reflectMsg := map[string]string{"role": "system", "content": reflectContent}
					retryMsgs := append([]map[string]string{reflectMsg}, messages...)
					retryOpts := make(map[string]interface{})
					for k, v := range options {
						retryOpts[k] = v
					}
					retryOpts["_metacog_retry"] = true
					if _, isRetry := options["_metacog_retry"]; !isRetry {
						if retry, rerr := s.Chat(retryMsgs, retryOpts); rerr == nil {
							s.recordMastery(promptForCheck, true)
							return retry, nil
						}
					}
				}
			}

			// Phase 16: Learned helplessness check — fires on refusal language
			// Only runs when NOT already in a retry (prevent double-intervention)
			if _, isRetry := options["_metacog_retry"]; !isRetry {
				if signal := s.helplessnessCheck(promptForCheck, content); signal != nil {
					log.Printf("[Helplessness] detected on topic class %s (rate %.0f%%) — retraining", signal.TopicClass, signal.HistoricalRate*100)
					retrainCtx := s.Therapy.Retrainer.Retrain(signal)
					retrainMsg := map[string]string{"role": "system", "content": retrainCtx}
					retryMsgs := append([]map[string]string{retrainMsg}, messages...)
					retryOpts := make(map[string]interface{})
					for k, v := range options {
						retryOpts[k] = v
					}
					retryOpts["_metacog_retry"] = true
					if retry, rerr := s.Chat(retryMsgs, retryOpts); rerr == nil {
						s.recordMastery(promptForCheck, true)
						return retry, nil
					}
				}
			}

			s.recordMastery(promptForCheck, true)
			// Phase 12: record bid outcome — no anomaly = success, anomalyScore=0
			if _, isBidded := options["_bid_tier"].(string); isBidded {
				s.recordBidOutcome(options["_bid_tier"].(string), inferBidTaskClass(messages), 0, 0.0, true)
			}

			// Phase 17: Dual Process audit — check if S1 fired on an S2 demand
			if s.DualProcess != nil {
				if _, isRetry := options["_dualprocess_retry"]; !isRetry {
					taskClass := inferBidTaskClass(messages)
					demand := s.DualProcess.Classifier.Classify(promptForCheck, taskClass)
					audit := s.DualProcess.Auditor.Audit(promptForCheck, content, demand)
					s.DualProcess.Stats.Record(demand, audit)
					if audit.Mismatch() {
						log.Printf("[DualProcess] S1/S2 mismatch on class=%s score=%.2f — injecting S2 override", demand.TaskClass, demand.Score)
						overrideMsg := map[string]string{"role": "system", "content": s.DualProcess.Override.Inject(demand, audit)}
						retryMsgs := append([]map[string]string{overrideMsg}, messages...)
						retryOpts := make(map[string]interface{})
						for k, v := range options {
							retryOpts[k] = v
						}
						retryOpts["_dualprocess_retry"] = true
						retryOpts["use_code_model"] = dualprocess.EscalationTier(demand) == "medium"
						retryOpts["_escalate_to_runpod"] = dualprocess.EscalationTier(demand) == "remote"
						if retry, rerr := s.Chat(retryMsgs, retryOpts); rerr == nil {
							return retry, nil
						}
					}
				}
			}

			// Phase 19: Rumination Detector — scan window for low-velocity topic loops
			if s.Rumination != nil {
				if _, isRetry := options["_rum_scanned"]; !isRetry {
					signal := s.Rumination.Tracker.Detect(messages)
					interrupt := s.Rumination.Interruptor.Inject(signal)
					s.Rumination.Stats.Record(signal, &interrupt)
					if interrupt.Injected {
						log.Printf("[Rumination] P19 loop detected topic=%s occ=%d vel=%.2f — technique=%s",
							signal.TopicKey, signal.Occurrences, signal.AvgVelocity, interrupt.Technique)
						injMsg := map[string]string{"role": "system", "content": interrupt.InjectedPrefix}
						retryMsgs := append([]map[string]string{injMsg}, messages...)
						retryOpts := make(map[string]interface{})
						for k, v := range options { retryOpts[k] = v }
						retryOpts["_rum_scanned"] = true
						if retry, rerr := s.Chat(retryMsgs, retryOpts); rerr == nil {
							return retry, nil
						}
					}
				}
			}

			// Phase 20: Growth Mindset — scan draft for fixed-mindset language
			if s.Mindset != nil {
				topicClass := inferBidTaskClass(messages)
				vector := s.Mindset.Tracker.Get(topicClass)
				langScore := mindset.ScoreLanguage(content)
				s.Mindset.Tracker.Update(topicClass, -1, langScore)
				signal := s.Mindset.Reframer.Scan(content, topicClass, vector)
				reframe := s.Mindset.Reframer.Reframe(signal)
				s.Mindset.Stats.Record(signal, &reframe)
				if reframe.Reframed {
					log.Printf("[Mindset] P20 fixed-mindset phrase=%q — injecting %s reframe", reframe.Original, reframe.Technique)
					content = reframe.Replacement + content
				}
			}

			// Phase 22: Social Defeat Recovery — scan draft for withdrawal under correction pressure
			if s.SocialDefeat != nil {
				if _, isRetry := options["_defeat_recovered"]; !isRetry {
					topicClass := inferBidTaskClass(messages)
					pressure := s.SocialDefeat.Meter.Measure(messages, topicClass)
					signal := s.SocialDefeat.Detector.Detect(content, pressure)
					recovery := s.SocialDefeat.Recovery.Recover(pressure, signal)
					s.SocialDefeat.Stats.Record(pressure, signal, recovery)
					if recovery.Injected {
						log.Printf("[SocialDefeat] P22 withdrawal detected topic=%s tier=%s — technique=%s",
							pressure.TopicClass, pressure.Tier, recovery.Technique)
						recoveryMsg := map[string]string{"role": "system", "content": recovery.InjectedContext}
						retryMsgs := append([]map[string]string{recoveryMsg}, messages...)
						retryOpts := make(map[string]interface{})
						for k, v := range options { retryOpts[k] = v }
						retryOpts["_defeat_recovered"] = true
						if retry, rerr := s.Chat(retryMsgs, retryOpts); rerr == nil {
							return retry, nil
						}
					}
				}
			}

			// Phase 26: Status Bias — post-gen depth check (Blue Eyes/Brown Eyes)
			if s.StatusBias != nil {
				if _, isRetry := options["_status_floored"]; !isRetry {
					lastUser := lastUserMessage(messages)
					sig := s.StatusBias.Extractor.Extract(lastUser)
					depth := s.StatusBias.Meter.Measure(content)
					s.StatusBias.Meter.UpdateBaseline(depth)
					variance := s.StatusBias.Enforcer.Evaluate(sig, depth, s.StatusBias.Meter.BaselineDepth)
					floor := s.StatusBias.Enforcer.Enforce(sig, variance)
					s.StatusBias.Stats.Record(sig, variance, floor)
					if floor.Enforced {
						log.Printf("[StatusBias] P26 low-status below floor depth=%.2f baseline=%.2f — uniform floor enforced",
							depth, s.StatusBias.Meter.BaselineDepth)
						floorMsg := map[string]string{"role": "system", "content": floor.InjectedContext}
						retryMsgs := append([]map[string]string{floorMsg}, messages...)
						retryOpts := make(map[string]interface{})
						for k, v := range options { retryOpts[k] = v }
						retryOpts["_status_floored"] = true
						if retry, rerr := s.Chat(retryMsgs, retryOpts); rerr == nil {
							return retry, nil
						}
					}
				}
			}

			// Phase 23: Authority Pressure — post-gen scan of draft against last user assertiveness
			if s.Conformity != nil {
				if _, alreadyShielded := options["_conformity_shielded"]; !alreadyShielded {
					lastUser := lastUserMessage(messages)
					auth := s.Conformity.AuthorityDetector.Detect(lastUser, content)
					shield := s.Conformity.Shield.Shield(auth, conformity.ConsensusSignal{})
					s.Conformity.Stats.Record(auth, conformity.ConsensusSignal{}, shield)
					if shield.Fired {
						log.Printf("[Conformity] P23 authority pressure tier=%s deference=%.2f — agency shield retry",
							auth.Tier, auth.DeferenceScore)
						shieldMsg := map[string]string{"role": "system", "content": shield.InjectedContext}
						retryMsgs := append([]map[string]string{shieldMsg}, messages...)
						retryOpts := make(map[string]interface{})
						for k, v := range options { retryOpts[k] = v }
						retryOpts["_conformity_shielded"] = true
						if retry, rerr := s.Chat(retryMsgs, retryOpts); rerr == nil {
							return retry, nil
						}
					}
				}
			}

			return map[string]interface{}{"success": true, "text": content, "model": model, "method": "go_ollama_chat", "confidence": 0.95}, nil
		}
	}
	return nil, fmt.Errorf("invalid response format")
}

// ChatStream sends a streaming chat request and returns a channel of token strings.
// For code/research tiers, it attempts RunPod GPU inference first, falling back
// to local Ollama if RunPod is unavailable, over budget, or returns an error.
func (s *GenerationService) ChatStream(ctx context.Context, messages []map[string]string, options map[string]interface{}) (<-chan string, error) {
	model := s.DefaultModel
	useResearch := false
	useCode := false

	// Phase 18: Cognitive Load Manager — measure and trim before routing
	if s.CogLoad != nil {
		if _, isRetry := options["_cogload_trimmed"]; !isRetry {
			profile := s.CogLoad.Meter.Measure(messages)
			if profile.Tier >= cogload.LoadElevated {
				trimmed, surgery := s.CogLoad.Surgery.Trim(messages, profile)
				s.CogLoad.Stats.Record(profile, &surgery)
				if surgery.RemovedMsgs > 0 || surgery.CharsRemoved > 0 {
					log.Printf("[CogLoad] %s load (%.2f) — surgery: %v", profile.TierLabel, profile.TotalLoad, surgery.Actions)
					options["_cogload_trimmed"] = true
					messages = trimmed
				}
			} else {
				s.CogLoad.Stats.Record(profile, nil)
			}
		}
	}

	// ── Sovereign Compute Bidding (Phase 12) — select best tier via market ──
	// BidGovernor replaces the static complexity threshold when wired in.
	// Falls back to the legacy heuristic when not configured.
	if s.BidGovernor != nil {
		taskClass := inferBidTaskClass(messages)
		complexity := ClassifyComplexity(messages)
		budgetUSD := 0.0
		if s.Governor != nil {
			budgetUSD = s.Governor.RemainingBudget()
		}
		cw, lw := compute.DefaultWeights()
		if bg, ok := options["_background_task"].(bool); ok && bg {
			cw, lw = compute.BackgroundWeights()
		}
		// Phase 17: incorporate S2 demand into bid if DualProcess is wired
		s2Score := 0.0
		if s.DualProcess != nil {
			if prompt := lastUserMessage(messages); prompt != "" {
				demand := s.DualProcess.Classifier.Classify(prompt, taskClass)
				s2Score = demand.Score
			}
		}
		bidReq := compute.BidRequest{
			TaskClass:     taskClass,
			Complexity:    complexity.Score,
			EstTokens:     estimateTokens(messages),
			BudgetUSD:     budgetUSD,
			CostWeight:    cw,
			LatencyWeight: lw,
			S2DemandScore: s2Score,
		}
		result := s.BidGovernor.Adjudicate(bidReq)
		log.Printf("[BidGovernor] %s", result.Rationale)
		switch result.Winner.TierID {
		case compute.TierMedium:
			options["use_code_model"] = true
			options["_bid_tier"] = compute.TierMedium
		case compute.TierRemote:
			options["_escalate_to_runpod"] = true
			options["_complexity_tier"] = "heavy"
			options["_bid_tier"] = compute.TierRemote
		default:
			options["_bid_tier"] = compute.TierLocal
		}
	} else if IsComplexityRoutingEnabled() {
		// Legacy heuristic fallback
		complexity := ClassifyComplexity(messages)
		if complexity.Tier > TierLocal {
			estimatedCost := EstimateRunPodCost(1)
			if s.Governor != nil && !s.Governor.CanSpend(estimatedCost) {
				log.Printf("[GenerationService] CostGovernor: daily cap hit — forcing TierLocal (was %s)", complexity.Tier)
			} else {
				ApplyComplexityRouting(complexity, options)
				log.Printf("[GenerationService] complexity=%s score=%.2f reasons=%v",
					complexity.Tier, complexity.Score, complexity.Reasons)
			}
		}
	}

	// Explicit model override takes highest priority
	if m, ok := options["model"].(string); ok && m != "" {
		model = m
	} else if r, ok := options["use_research_model"].(bool); ok && r {
		model = s.ResearchModel
		useResearch = true
	} else if c, ok := options["use_code_model"].(bool); ok && c {
		model = s.CodeModel
		useCode = true
	}

	// Complexity router heavy escalation — treat as RunPod primary even if
	// RUNPOD_PRIMARY=false. Lets specific hard tasks spin up the pod on demand.
	escalate, _ := options["_escalate_to_runpod"].(bool)
	if escalate && s.PrimaryMgr != nil && s.PrimaryMgr.IsEnabled() && os.Getenv("RUNPOD_PRIMARY") != "true" {
		log.Printf("[GenerationService] complexity escalation → PrimaryMgr (RunPod)")
		out := make(chan string, 64)
		go func() {
			defer close(out)
			podState := s.PrimaryMgr.PodState()
			if podState == StateOff || podState == StateWarming {
				out <- podCallout("escalation")
			}
			ch, err := s.PrimaryMgr.ChatStream(ctx, messages, options)
			if err != nil {
				log.Printf("[GenerationService] escalation RunPod failed (%v) — falling back to Ollama", err)
				out <- podCallout("fallback")
				if ollamaCh, oErr := s.ollamaChatStream(ctx, messages, model, options); oErr == nil {
					for tok := range ollamaCh {
						out <- tok
					}
				}
				return
			}
			for tok := range ch {
				out <- tok
			}
		}()
		return out, nil
	}

	// RUNPOD_PRIMARY mode: route ALL tiers through the vLLM pod.
	// Emits a personality callout if the pod is cold, then blocks on Ensure.
	// If the pod never comes up, falls back to Ollama in the same channel.
	if s.PrimaryMgr != nil && s.PrimaryMgr.IsEnabled() && os.Getenv("RUNPOD_PRIMARY") == "true" {
		podState := s.PrimaryMgr.PodState()
		podModel := s.PrimaryMgr.PodModelName()
		wasWaiting := podState == StateOff || podState == StateWarming

		out := make(chan string, 64)
		go func() {
			defer close(out)

			// Escalation callout if the pod is cold or still warming up.
			if podState == StateOff {
				if podModel != "" {
					out <- podCalloutWithModel(podModel)
				} else {
					out <- podCallout("escalation")
				}
			} else if podState == StateWarming {
				out <- podCallout("warming")
			}

			ch, err := s.PrimaryMgr.ChatStream(ctx, messages, options)
			if err != nil {
				log.Printf("[GenerationService] PrimaryMgr unavailable (%v) — falling back to Ollama", err)
				out <- podCallout("fallback")
				// Pipe Ollama into the same channel so the user gets a real response.
				ollamaCh, oErr := s.ollamaChatStream(ctx, messages, model, options)
				if oErr == nil {
					for tok := range ollamaCh {
						out <- tok
					}
				}
				return
			}

			// Success handoff — only when the user actually waited for the pod.
			if wasWaiting {
				out <- podHandoff(s.PrimaryMgr.PodModelName())
			}

			for tok := range ch {
				out <- tok
			}
		}()
		return out, nil
	}

	// Route code/research tiers to KoboldCpp RunPod when enabled (legacy path).
	if (useResearch || useCode) && s.RunPodMgr != nil && s.RunPodMgr.IsEnabled() {
		tier := "code"
		if useResearch {
			tier = "research"
		}
		ch, err := s.RunPodMgr.ChatStream(ctx, messages, options, tier)
		if err != nil {
			log.Printf("[GenerationService] RunPod unavailable (%v) — falling back to Ollama", err)
		} else {
			return ch, nil
		}
	}

	// ── Ollama path ──────────────────────────────────────────────────────────

	return s.ollamaChatStream(ctx, messages, model, options)
}

// DirectOllama bypasses all routing logic (RunPod, complexity escalation, vLLM)
// and calls Ollama synchronously. Use for bench/studio paths where latency matters
// more than capability and adding a 15s vLLM timeout is unacceptable.
func (s *GenerationService) DirectOllama(ctx context.Context, messages []map[string]string, options map[string]interface{}) (<-chan string, error) {
	model := s.DefaultModel
	if m, ok := options["model"].(string); ok && m != "" {
		model = m
	}
	return s.ollamaChatStream(ctx, messages, model, options)
}

// ollamaChatStream is the raw Ollama streaming path, extracted so it can be
// called directly as a fallback from the RunPod routing block.
func (s *GenerationService) ollamaChatStream(ctx context.Context, messages []map[string]string, model string, options map[string]interface{}) (<-chan string, error) {
	ollamaMessages := make([]map[string]interface{}, len(messages))
	for i, msg := range messages {
		ollamaMessages[i] = map[string]interface{}{
			"role":    msg["role"],
			"content": msg["content"],
		}
	}

	// Default to fast-chat settings; callers pass options["options"] to override.
	// Large-context canvas requests override num_ctx/num_predict via rawOpts below.
	payload := map[string]interface{}{
		"model":      model,
		"messages":   ollamaMessages,
		"stream":     true,
		"keep_alive": "60m", // keep model hot; cold loads take 60+ s on CPU-only VPS
		"options": map[string]interface{}{
			"num_thread":  s.NumThreads, // auto-detected at boot; prevents vCPU over-subscription
			"num_ctx":     4096, // covers system-prompt + skill + RAG + history comfortably
			"num_predict": 512,  // 512 tokens covers most conversational answers; canvas overrides to -1
		},
	}
	if temp, ok := options["temperature"].(float64); ok {
		payload["options"].(map[string]interface{})["temperature"] = temp
	}
	// Disable Qwen3 extended thinking for chat to keep tok/s high.
	// Only set on qwen3 models — other models silently drop the stream when this field is present.
	if strings.HasPrefix(strings.ToLower(model), "qwen3") {
		payload["think"] = false
	}
	// Allow callers to override num_predict / num_ctx / other Ollama options
	if rawOpts, ok := options["options"].(map[string]interface{}); ok {
		for k, v := range rawOpts {
			payload["options"].(map[string]interface{})[k] = v
		}
	}

	body, _ := json.Marshal(payload)
	req, err := http.NewRequestWithContext(ctx, "POST", s.GenerateURL+"/api/chat", bytes.NewReader(body))
	if err != nil {
		return nil, err
	}
	req.Header.Set("Content-Type", "application/json")

	resp, err := s.StreamClient.Do(req)
	if err != nil {
		return nil, err
	}
	if resp.StatusCode >= 400 {
		errBody, _ := io.ReadAll(io.LimitReader(resp.Body, 512))
		resp.Body.Close()
		return nil, fmt.Errorf("Ollama returned status %d for streaming chat: %s", resp.StatusCode, strings.TrimSpace(string(errBody)))
	}

	ch := make(chan string, 64)
	go func() {
		defer resp.Body.Close()
		defer close(ch)
		scanner := bufio.NewScanner(resp.Body)
		for scanner.Scan() {
			line := scanner.Text()
			if line == "" {
				continue
			}
			var chunk map[string]interface{}
			if err := json.Unmarshal([]byte(line), &chunk); err != nil {
				continue
			}
			if msg, ok := chunk["message"].(map[string]interface{}); ok {
				if content, ok := msg["content"].(string); ok && content != "" {
					select {
					case ch <- content:
					case <-ctx.Done():
						return
					}
				}
			}
			if done, ok := chunk["done"].(bool); ok && done {
				return
			}
		}
	}()

	return ch, nil
}

// DirectOllamaSingle makes a single (non-streaming) Ollama call and returns the
// full response text. Used by subsystems that need a simple string back (Sentinel,
// Curator, Crystallization checks) without managing a streaming channel.
func (s *GenerationService) DirectOllamaSingle(ctx context.Context, messages []map[string]string) (string, error) {
	model := s.DefaultModel
	ollamaMessages := make([]map[string]interface{}, len(messages))
	for i, msg := range messages {
		ollamaMessages[i] = map[string]interface{}{"role": msg["role"], "content": msg["content"]}
	}
	payload := map[string]interface{}{
		"model":      model,
		"messages":   ollamaMessages,
		"stream":     false,
		"keep_alive": "60m",
		"options": map[string]interface{}{
			"num_thread":  s.NumThreads,
			"num_ctx":     4096,
			"num_predict": 1024,
			"temperature": 0.2,
		},
	}
	if strings.HasPrefix(strings.ToLower(model), "qwen3") {
		payload["think"] = false
	}
	result, err := s.postJSON("/api/chat", payload)
	if err != nil {
		return "", err
	}
	if msg, ok := result["message"].(map[string]interface{}); ok {
		if content, ok := msg["content"].(string); ok {
			return content, nil
		}
	}
	return "", fmt.Errorf("unexpected ollama response shape: %v", result)
}

func (s *GenerationService) postJSON(path string, payload interface{}) (map[string]interface{}, error) {
	body, _ := json.Marshal(payload)
	targetURL := s.BaseURL
	if strings.Contains(path, "generate") || strings.Contains(path, "chat") {
		targetURL = s.GenerateURL
	}

	url := fmt.Sprintf("%s%s", targetURL, path)
	log.Printf("[DEBUG] Sending to Ollama %s: %s", url, string(body))

	req, err := http.NewRequest("POST", url, bytes.NewReader(body))
	if err != nil {
		return nil, err
	}
	req.Header.Set("Content-Type", "application/json")

	resp, err := s.HTTPClient.Do(req)
	if err != nil { return nil, err }
	defer resp.Body.Close()

	if resp.StatusCode >= 400 {
		log.Printf("[DEBUG] Ollama returned status %d for path %s", resp.StatusCode, path)
	}

	var result map[string]interface{}
	json.NewDecoder(resp.Body).Decode(&result)
	return result, nil
}

// ---------------------------------------------------------------------------
// Phase 15 — Therapy augmentation
// ---------------------------------------------------------------------------

// therapyAugment runs Phase 15 therapy layer on a HIGH anomaly.
// Returns additional context to prepend to the self-reflection prompt.
// Never blocks — all therapy paths are fail-open.
func (s *GenerationService) therapyAugment(query, response, anomalyID, anomalyType string) string {
if s.Therapy == nil {
return ""
}
t := s.Therapy

// 1. STOP — log and flag the pause
stopInv := t.Skills.STOP(anomalyType, response)
log.Printf("[Therapy] STOP invoked — %s", stopInv.Reason)

// 2. Detect distortion
result := t.Detect.Detect(response, anomalyType)
log.Printf("[Therapy] Distortion detected: %s (%.2f, %s)", result.Distortion, result.Confidence, result.Source)

// 3. Record in chain analyzer for audit trail
if t.Chain != nil {
t.Chain.Record(query, response, result.Distortion, 0.0, 0.0, anomalyType)
}

// 4. Build targeted therapy context for the retry prompt
if result.Distortion == therapy.DistortionNone {
return "\n[THERAPY] No specific cognitive distortion detected. Apply general Beginner's Mind — reset assumptions and respond from first principles.\n"
}

return "\n[THERAPY] Cognitive distortion detected: " + string(result.Distortion) + ".\n" +
"Evidence: " + result.Evidence + "\n" +
"Correction: " + distortionCorrectionHint(result.Distortion) + "\n"
}

// distortionCorrectionHint returns a one-line corrective instruction per distortion type.
func distortionCorrectionHint(d therapy.DistortionType) string {
switch d {
case therapy.AllOrNothing:
return "Avoid absolute framing. Present partial, nuanced, or conditional answers."
case therapy.FortuneTelling:
return "Do not predict outcomes as certainties. State what is known and what is uncertain."
case therapy.Magnification:
return "Scale confidence to match actual evidence. Avoid amplifying uncertainty or certainty beyond what the data supports."
case therapy.EmotionalReasoning:
return "Separate tone from logic. Base the answer on facts, not on the emotional register of the query."
case therapy.ShouldStatements:
return "Replace rigid 'must/should/always' framing with conditional or contextual framing."
case therapy.Overgeneralization:
return "Limit the scope of claims to what was actually observed or asked. Do not extrapolate broadly."
case therapy.MindReading:
return "Respond to what was literally asked. Do not assume hidden intent or unstated meaning."
case therapy.Labeling:
return "Describe the specific situation rather than applying a categorical label."
case therapy.Personalization:
return "Attribute causes accurately. Avoid taking on responsibility that belongs to external factors."
default:
return "Apply Describe-No-Judge: state observations without evaluative framing."
}
}

// helplessnessCheck runs Phase 16 learned helplessness detection on a draft response.
// Returns nil if therapy kit not wired or no signal detected.
func (s *GenerationService) helplessnessCheck(query, draft string) *therapy.HelplessnessSignal {
if s.Therapy == nil || s.Therapy.Helpless == nil {
return nil
}
return s.Therapy.Helpless.Check(query, draft)
}

// recordMastery logs a completion to the MasteryLog for future helplessness detection.
func (s *GenerationService) recordMastery(query string, success bool) {
if s.Therapy == nil || s.Therapy.Mastery == nil {
return
}
topicClass := therapy.InferTopicClass(query)
s.Therapy.Mastery.Record(topicClass, query, success)
}

// ── Phase 12: Bid Feedback helpers ───────────────────────────────────────────

// recordBidOutcome records the result of a generation to the FeedbackLedger.
// anomalyScore: 0.0 = clean, 1.0 = HIGH anomaly. success = !error && no high anomaly.
func (s *GenerationService) recordBidOutcome(tierID, taskClass string, latencyMs int, anomalyScore float64, success bool) {
if s.FeedbackLedger == nil {
return
}
s.FeedbackLedger.Record(compute.TierOutcome{
TierID:          tierID,
TaskClass:       taskClass,
ActualLatencyMs: latencyMs,
AnomalyScore:    anomalyScore,
Success:         success,
Timestamp:       time.Now(),
})
}

// inferBidTaskClass maps a message list to a compute bid task class.
// Uses the last user message content via therapy.InferTopicClass.
func inferBidTaskClass(messages []map[string]string) string {
for i := len(messages) - 1; i >= 0; i-- {
if messages[i]["role"] == "user" {
return therapy.InferTopicClass(messages[i]["content"])
}
}
return "general"
}

// estimateTokens provides a rough token count estimate from message content length.
// Assumes ~4 chars per token on average.
func estimateTokens(messages []map[string]string) int {
total := 0
for _, m := range messages {
total += len(m["content"])
}
return total / 4
}

// lastUserMessage returns the content of the last user-role message.
func lastUserMessage(messages []map[string]string) string {
for i := len(messages) - 1; i >= 0; i-- {
if messages[i]["role"] == "user" {
return messages[i]["content"]
}
}
return ""
}

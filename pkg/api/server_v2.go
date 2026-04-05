package api

import (
	"bufio"
	"context"
	"encoding/base64"
	"encoding/json"
	"fmt"
	"io"
	"log"
	"math"
	"net/http"
	"os"
	"path/filepath"
	"regexp"
	"sort"
	"strconv"
	"strings"
	"sync"
	"time"

	"github.com/gin-gonic/gin"
	"github.com/thynaptic/oricli-go/pkg/cache"
	"github.com/thynaptic/oricli-go/pkg/cognition"
	"github.com/thynaptic/oricli-go/pkg/connectors/runpod"
	tenantauth "github.com/thynaptic/oricli-go/pkg/auth"
	"github.com/thynaptic/oricli-go/pkg/core/auth"
	"github.com/thynaptic/oricli-go/pkg/core/config"
	"github.com/thynaptic/oricli-go/pkg/core/model"
	"github.com/thynaptic/oricli-go/pkg/core/store"
	"github.com/thynaptic/oricli-go/pkg/engine"
	"github.com/thynaptic/oricli-go/pkg/enterprise"
	enterpriseconn "github.com/thynaptic/oricli-go/pkg/enterprise/connectors"
	githubconn "github.com/thynaptic/oricli-go/pkg/enterprise/connectors/github"
	notionconn "github.com/thynaptic/oricli-go/pkg/enterprise/connectors/notion"
	"github.com/thynaptic/oricli-go/pkg/enterprise/rag"
	"github.com/thynaptic/oricli-go/pkg/reform"
	"github.com/thynaptic/oricli-go/pkg/safety"
	"github.com/thynaptic/oricli-go/pkg/scl"
	"github.com/thynaptic/oricli-go/pkg/sentinel"
	"github.com/thynaptic/oricli-go/pkg/service"
	"github.com/thynaptic/oricli-go/pkg/sovereign"
	"github.com/thynaptic/oricli-go/pkg/swarm"
	tcdpkg "github.com/thynaptic/oricli-go/pkg/tcd"
	"github.com/thynaptic/oricli-go/pkg/goal"
	"github.com/thynaptic/oricli-go/pkg/finetune"
	"github.com/thynaptic/oricli-go/pkg/curator"
	"github.com/thynaptic/oricli-go/pkg/audit"
	"github.com/thynaptic/oricli-go/pkg/metacog"
	"github.com/thynaptic/oricli-go/pkg/chronos"
	"github.com/thynaptic/oricli-go/pkg/cogload"
	"github.com/thynaptic/oricli-go/pkg/rumination"
	"github.com/thynaptic/oricli-go/pkg/hopecircuit"
	"github.com/thynaptic/oricli-go/pkg/socialdefeat"
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
	"github.com/thynaptic/oricli-go/pkg/logotherapy"
	"github.com/thynaptic/oricli-go/pkg/stoic"
	"github.com/thynaptic/oricli-go/pkg/socratic"
	"github.com/thynaptic/oricli-go/pkg/narrative"
	"github.com/thynaptic/oricli-go/pkg/polyvagal"
	"github.com/thynaptic/oricli-go/pkg/dmn"
	"github.com/thynaptic/oricli-go/pkg/interoception"
	"github.com/thynaptic/oricli-go/pkg/interference"
	"github.com/thynaptic/oricli-go/pkg/mindset"
	"github.com/thynaptic/oricli-go/pkg/compute"
	"github.com/thynaptic/oricli-go/pkg/dualprocess"
	"github.com/thynaptic/oricli-go/pkg/science"
	"github.com/thynaptic/oricli-go/pkg/therapy"
)

// ServerV2 represents the Hardened Sovereign API Gateway
type ServerV2 struct {
	cfg          config.Config
	store        store.Store
	auth         *auth.Service
	Orchestrator *service.GoOrchestrator
	Agent        *service.GoAgentService
	Monitor      *service.ModuleMonitorService
	Traces       *service.TraceStore
	WSHub        *Hub
	Router       *gin.Engine
	Port         int
	ActionRouter *service.ActionRouter
	GoalService  *service.GoalService
	GoalExecutor *service.GoalExecutor
	Metrics      *service.MetricsCollector
	RateLimiter  *safety.RateLimiter
	SovAuth      *sovereign.SovereignAuth
	ExecHandler  *sovereign.SovereignExecHandler
	ImageGen         *service.ImageGenManager
	MemoryBank       *service.MemoryBank
	DocumentIngestor *service.DocumentIngestor
	Skills           *service.SkillManager
	ResponseCache    *cache.ResponseCache
	SignalProcessor  *service.SignalProcessor
	Constitution     *service.LivingConstitution
	entLayers        sync.Map // namespace -> *enterprise.Layer cache
	entJobs          sync.Map // job_id -> *enterpriseLearnJob
	spacesStore      *SpacesStore

	// SPP: Sovereign Peer Protocol (Phase 4)
	SwarmRegistry *swarm.PeerRegistry
	SwarmMonitor  *swarm.SwarmMonitor
	// Phase 5: Hive Mind Consensus
	JuryClient   *swarm.JuryClient
	VoteLog      *swarm.FragmentVoteLog
	ESIFederation *swarm.ESIFederation
	// SCL-6: Sovereign Cognitive Ledger
	SCL       *scl.Ledger
	SCLEngine *scl.RetrievalEngine
	// TCD: Temporal Curriculum Daemon
	TCDDaemon interface {
		TriggerManualTick()
	}
	TCDManifest interface {
		All() []*tcdpkg.Domain
		GetLineage(domainID string) []tcdpkg.DomainEvent
		GetEvolutionTree() map[string][]tcdpkg.DomainEvent
	}
	TCDGapDetector interface {
		Scan(ctx context.Context) (int, error)
	}
	// Forge: JIT Tool Forge
	Forge *service.ToolForgeService
	// PAD: Parallel Agent Dispatch
	PAD *service.PADService
	// Goals: Sovereign Goal Engine
	GoalDaemon  *service.GoalDaemon
	GoalStore   *goal.GoalStore
	GoalPlanner *goal.GoalPlanner
	// FineTune: Automated LoRA training orchestrator
	FineTune *service.FineTuneService
	// Sentinel: Adversarial Sentinel — red-team pre-flight
	Sentinel *sentinel.AdversarialSentinel
	// CrystalCache: Skill Crystallization — LLM-bypass for high-reputation patterns
	CrystalCache *scl.CrystalCache
	// Curator: Sovereign Model Curation — auto-benchmark + recommendation engine
	Curator *curator.ModelCurator
	// AuditDaemon: Self-Audit Loop — scans own source, verifies via Gosh, opens PRs
	AuditDaemon *audit.AuditDaemon
	// MetacogDaemon: Phase 8 Metacognitive Sentience — rolling anomaly scan + WS broadcast
	MetacogDaemon *metacog.MetacogDaemon
	MetacogLog    *metacog.EventLog
	// ChronosIndex + ChronosDaemon: Phase 9 Temporal Grounding
	ChronosIndex  *chronos.ChronosIndex
	ChronosDaemon *chronos.TemporalGroundingDaemon
	// ScienceDaemon: Phase 10 Active Science
	ScienceDaemon *science.ScienceDaemon
	// TherapyKit: Phase 15 Therapeutic Cognition Stack
	TherapySkills     *therapy.SkillRunner
	TherapyDetect     *therapy.DistortionDetector
	TherapyABC        *therapy.ABCAuditor
	TherapyChain      *therapy.ChainAnalyzer
	TherapySupervisor *therapy.SessionSupervisor
	TherapyLog        *therapy.EventLog
	// Phase 16: Learned Helplessness Prevention
	TherapyHelpless  *therapy.HelplessnessDetector
	TherapyMastery   *therapy.MasteryLog
	TherapyRetrainer *therapy.AttributionalRetrainer

	// Phase 12: Sovereign Compute Bidding
	BidGovernor    *compute.BidGovernor
	FeedbackLedger *compute.FeedbackLedger

	// Phase 17: Dual Process Engine
	DualProcessClassifier *dualprocess.ProcessClassifier
	DualProcessStats      *dualprocess.ProcessStats

	// Phase 18: Cognitive Load Manager
	CogLoadMeter *cogload.LoadMeter
	CogLoadStats *cogload.CogLoadStats

	// Phase 19: Rumination Detector
	RuminationTracker  *rumination.RuminationTracker
	RuminationStats    *rumination.RuminationStats

	// Phase 20: Growth Mindset Tracker
	MindsetTracker *mindset.MindsetTracker
	MindsetStats   *mindset.MindsetStats

	// Phase 21: Hope Circuit
	HopeCircuit *hopecircuit.HopeCircuit
	AgencyStats *hopecircuit.AgencyStats

	// Phase 22: Social Defeat Recovery
	DefeatMeter *socialdefeat.DefeatPressureMeter
	DefeatStats *socialdefeat.DefeatStats
	ConformityShield *conformity.AgencyShield
	ConformityStats *conformity.ConformityStats
	IdeoCaptureStats *ideocapture.IdeoCaptureStats
	CoalitionStats *coalition.CoalitionStats
	StatusBiasStats     *statusbias.StatusBiasStats
	ArousalStats        *arousal.ArousalStats
	InterferenceStats   *interference.InterferenceStats
	MCTStats            *mct.MCTStats
	MBTStats            *mbt.MBTStats
	SchemaStats         *schema.SchemaStats
	IPSRTStats          *ipsrt.RhythmStats
	ILMStats            *ilm.ILMStats
	IUTStats            *iut.IUStats
	UPStats             *up.UPStats
	CBASPStats          *cbasp.CBASPStats
	MBCTStats           *mbct.MBCTStats
	PhaseStats              *phaseoriented.PhaseStats
	PseudoIdentityStats     *pseudoidentity.IdentityStats
	ThoughtReformStats      *thoughtreform.ThoughtReformStats
	ApathyStats             *apathy.ApathyStats
	LogotherapyStats        *logotherapy.MeaningStats
	StoicStats              *stoic.StoicStats
	SocraticStats           *socratic.SocraticStats
	NarrativeStats          *narrative.NarrativeStats
	PolyvagalStats          *polyvagal.PolyvagalStats
	DMNStats                *dmn.DMNStats
	InteroceptionStats      *interoception.InteroceptiveStats
}

func NewServerV2(cfg config.Config, st store.Store, orch *service.GoOrchestrator, agent *service.GoAgentService, mon *service.ModuleMonitorService, port int) *ServerV2 {
	r := gin.Default()
	hub := NewHub()
	go hub.Run()

	// CORS & Cache-Control Middleware
	r.Use(func(c *gin.Context) {
		c.Writer.Header().Set("Access-Control-Allow-Origin", "*")
		c.Writer.Header().Set("Access-Control-Allow-Methods", "POST, GET, OPTIONS, PUT, DELETE")
		c.Writer.Header().Set("Access-Control-Allow-Headers", "Content-Type, Content-Length, Accept-Encoding, X-CSRF-Token, Authorization, X-Tenant-ID")
		
		if !strings.HasPrefix(c.Request.URL.Path, "/v1") {
			c.Writer.Header().Set("Cache-Control", "no-store, no-cache, must-revalidate, proxy-revalidate, max-age=0")
			c.Writer.Header().Set("Pragma", "no-cache")
			c.Writer.Header().Set("Expires", "0")
		}

		if c.Request.Method == "OPTIONS" {
			c.AbortWithStatus(204)
			return
		}
		c.Next()
	})

	r.GET("/", func(c *gin.Context) {
		c.JSON(200, gin.H{"service": "Oricli API", "status": "ok", "ui": "https://oristudio.thynaptic.com"})
	})

	r.NoRoute(func(c *gin.Context) {
		c.JSON(404, gin.H{"error": "not found"})
	})

	s := &ServerV2{
		cfg:          cfg,
		store:        st,
		auth:         auth.NewService(st),
		Orchestrator: orch,
		Agent:        agent,
		Monitor:      mon,
		Traces:       service.NewTraceStore(nil),
		WSHub:        hub,
		Router:       r,
		Port:         port,
		Metrics:      service.NewMetricsCollector(),
		RateLimiter:  safety.NewRateLimiter(),
		SovAuth:      sovereign.NewSovereignAuth(),
		ExecHandler:  sovereign.NewSovereignExecHandler(),
		ImageGen:     service.NewImageGenManager(),
	}

	// Initialize Spaces store
	s.spacesStore = NewSpacesStore("data/spaces.json")

	// Bootstrap PocketBase long-term memory bank
	mb := service.NewMemoryBank()
	s.MemoryBank = mb
	go func() {
		ctx, cancel := context.WithTimeout(context.Background(), 30*time.Second)
		defer cancel()
		if err := mb.Bootstrap(ctx); err != nil {
			log.Printf("[ServerV2] PocketBase bootstrap error: %v", err)
		}
	}()

	// Wire ActionRouter for trigger-word intent dispatch
	research := service.NewResearchOrchestrator(agent)
	curiosity := service.NewCuriosityDaemon(agent.SovEngine.Graph, agent.SovEngine.VDI, agent.GenService, hub)
	curiosity.MemoryBank = mb
	s.ActionRouter = service.NewActionRouter(research, curiosity, hub)

	// Wire MemoryBank to ExecHandler for PB audit trail on every !command
	s.ExecHandler.MemoryBank = mb

	// Restore this month's RunPod spend from PocketBase
	if rp := agent.GenService.RunPodMgr; rp != nil {
		rp.MemoryBank = mb
		go func() {
			ctx, cancel := context.WithTimeout(context.Background(), 10*time.Second)
			defer cancel()
			rp.LoadSpendFromBank(ctx)
		}()
	}

	// Inject SearXNG searcher into SovereignEngine (avoids import cycle)
	agent.SovEngine.SearXNG = service.NewSearXNGSearcher()

	// Load skills from oricli_core/skills/
	s.Skills = service.NewSkillManager("oricli_core/skills")
	log.Printf("[ServerV2] Loaded %d skills", len(s.Skills.ListSkills()))

	// Bootstrap semantic response cache — L1 (hash) + L2 (chromem-go vectors).
	// Cache misses fall through to LLM normally. Zero impact on latency on miss.
	s.ResponseCache = cache.New(".memory", service.NewEmbedder())

	// Bootstrap Living Constitution and Signal Processor for The Imprint learning loop.
	lc := service.NewLivingConstitution()
	s.Constitution = lc
	s.SignalProcessor = service.NewSignalProcessor(mb, lc)
	agent.SovEngine.Constitution = lc

	// Bootstrap Tenant Constitution — SMB/operator behavioral layer from .ori file.
	if tc := service.LoadTenantConstitution(cfg.TenantConstitutionPath); tc != nil {
		agent.SovEngine.TenantConstitution = tc
	}

	// Bootstrap Enterprise Knowledge Layer — namespace-isolated RAG over company data.
	// Activated by setting ORICLI_ENTERPRISE_NAMESPACE env var.
	if ns := os.Getenv("ORICLI_ENTERPRISE_NAMESPACE"); ns != "" {
		if el, err := enterprise.New(ns); err == nil {
			agent.SovEngine.EnterpriseLayer = el
			log.Printf("[Enterprise] Knowledge layer active for namespace %q", ns)
		} else {
			log.Printf("[Enterprise] Failed to init knowledge layer: %v", err)
		}
	}

	// Inject MemoryBank into SovereignEngine via adapter (avoids cognition→service import cycle).
	adapter := &memoryBankAdapter{mb: mb}
	agent.SovEngine.MemoryBankRef = adapter
	agent.SovEngine.CertaintyUpdaterRef = adapter
	// VisionRef: route to RunPod GPU pod when enabled, fall back to local Ollama stub.
	if os.Getenv("RUNPOD_VISION_ENABLED") == "true" {
		apiKey := os.Getenv("RUNPOD_API_KEY")
		if apiKey == "" {
			apiKey = os.Getenv("OricliAlpha_Key")
		}
		agent.SovEngine.VisionRef = service.NewRunPodVisionManager(runpod.NewClient(apiKey))
	} else {
		agent.SovEngine.VisionRef = &visionAdapter{ollamaURL: ollamaBaseURL()}
	}

	s.setupRoutes()

	// Seed API key from env — allows scripts/benchmark tools to auth without
	// a database round-trip to generate keys. Set ORICLI_SEED_API_KEY=glm.<prefix>.<secret>
	// in .env or the systemd service file. The key is registered (or re-registered)
	// every startup so it survives DB wipes.
	if seedKey := os.Getenv("ORICLI_SEED_API_KEY"); seedKey != "" {
		go func() {
			ctx, cancel := context.WithTimeout(context.Background(), 10*time.Second)
			defer cancel()
			if _, err := s.auth.RegisterAPIKey(ctx, seedKey, "default", []string{"chat", "read", "write", "admin"}, nil); err != nil {
				log.Printf("[ServerV2] seed key register error (may already exist): %v", err)
			} else {
				log.Printf("[ServerV2] seed API key registered")
			}
		}()
	}

	// Pre-warm Ollama model in the background so the first user request
	// doesn't pay the cold-load penalty (~60-90s on CPU-only VPS).
	go func() {
		time.Sleep(5 * time.Second) // let backbone fully initialize first
		log.Printf("[ServerV2] Pre-warming Ollama model...")
		warmCtx, warmCancel := context.WithTimeout(context.Background(), 120*time.Second)
		defer warmCancel()
		warmMsgs := []map[string]string{{"role": "user", "content": "hi"}}
		ch, err := s.Agent.GenService.ChatStream(warmCtx, warmMsgs, map[string]interface{}{
			"options": map[string]interface{}{"num_predict": 3, "num_ctx": 4096},
		})
		if err != nil {
			log.Printf("[ServerV2] Model warmup failed: %v", err)
			return
		}
		for range ch { /* drain */ }
		log.Printf("[ServerV2] Model warmup complete — first request will be fast")
	}()

	return s
}

func (s *ServerV2) authMiddleware() gin.HandlerFunc {
	return func(c *gin.Context) {
		raw := c.GetHeader("Authorization")
		if raw == "" {
			c.AbortWithStatusJSON(http.StatusUnauthorized, gin.H{"error": "missing Authorization header"})
			return
		}
		ctx, err := s.auth.Authenticate(c.Request.Context(), raw)
		if err != nil {
			c.AbortWithStatusJSON(http.StatusUnauthorized, gin.H{"error": "invalid or expired API key"})
			return
		}
		c.Request = c.Request.WithContext(ctx)
		c.Next()
	}
}

func (s *ServerV2) setupRoutes() {
	// Public share route — no auth, serves HTML/code/markdown directly
	s.Router.GET("/share/:id", s.handleGetShare)

	v1 := s.Router.Group("/v1")

	// Public
	v1.GET("/health", s.handleHealth)
	v1.GET("/eri", s.handleERI)
	v1.GET("/aeci", s.handleAECI)
	v1.GET("/flow/prompt", s.handleFlowPrompt)
	v1.POST("/flow/trigger", s.handleFlowTrigger)
	v1.POST("/flow/prompt/dismiss", s.handleFlowDismiss)
	v1.GET("/ws", s.handleWS)
	v1.GET("/traces", s.handleGetTraces)
	v1.GET("/loglines", s.handleLogLines)
	v1.GET("/modules", s.handleListModules)
	// App self-registration — no user auth required; protected by shared registration token.
	// Used by first-party apps (ORI Home, ORI Mobile, etc.) to provision their own GLM key
	// on first boot without needing a pre-existing key.
	v1.POST("/app/register", s.handleAppRegister)
	// Prometheus metrics endpoint — scraped by local Prometheus container
	v1.GET("/metrics", func(c *gin.Context) {
		s.Metrics.PrometheusHandler().ServeHTTP(c.Writer, c.Request)
	})

	// Protected
	protected := v1.Group("/", s.authMiddleware(), tenantauth.TenantEnricher(s.store), s.RateLimiter.GinMiddleware())
	{
		protected.POST("/chat/completions", s.handleChatCompletions)
		protected.POST("/images/generations", s.handleImageGenerations)
		protected.POST("/swarm/run", s.handleSwarmRun)
		protected.POST("/ingest", s.handleIngest)
		protected.POST("/ingest/web", s.handleIngestWeb)
		protected.POST("/telegram/webhook", s.handleTelegramWebhook)

		// DAG Goal Management
		protected.GET("/goals", s.handleListGoals)
		protected.GET("/goals/:id", s.handleGetGoal)
		protected.POST("/goals", s.handleCreateGoal)
		protected.PUT("/goals/:id", s.handleUpdateGoal)
		protected.DELETE("/goals/:id", s.handleDeleteGoal)
		protected.GET("/daemons", s.handleDaemonHealth)

		protected.GET("/memories", s.handleListMemories)
		protected.GET("/memories/knowledge", s.handleListKnowledge)

		protected.POST("/documents/upload", s.handleDocumentUpload)
		protected.GET("/documents", s.handleListDocuments)

		protected.POST("/feedback", s.handleReactionFeedback)

		// Canvas shares — create a permanent public share link, list recent shares
		protected.POST("/share", s.handleCreateShare)
		protected.GET("/shares", s.handleListShares)

		// Agent Vibe Studio — natural language agent creation
		protected.POST("/agents/vibe", s.handleAgentVibe)

		// Workspaces — agentic desktop task execution (SSE)
		protected.POST("/workspaces/run", s.handleWorkspaceRun)

		// Vision — image analysis via moondream (CPU-safe, local Ollama)
		protected.POST("/vision/analyze", s.handleVisionAnalyze)

		// Sovereign Identity — active .ori profile editor
		protected.GET("/sovereign/identity", s.handleGetSovereignIdentity)
		protected.PUT("/sovereign/identity", s.handlePutSovereignIdentity)

		// Enterprise Knowledge Layer — namespace-isolated RAG for SMB tenants
		protected.POST("/enterprise/learn", s.handleEnterpriseLearn)
		protected.GET("/enterprise/learn/:job_id", s.handleEnterpriseLearnStatus)
		protected.GET("/enterprise/knowledge/search", s.handleEnterpriseSearch)
		protected.DELETE("/enterprise/knowledge", s.handleEnterpriseClear)

		// Spaces — named project containers with scoped RAG knowledge
		protected.GET("/spaces", s.handleListSpaces)
		protected.POST("/spaces", s.handleCreateSpace)
		protected.DELETE("/spaces/:id", s.handleDeleteSpace)
		protected.POST("/spaces/:id/documents", s.handleSpaceDocumentUpload)
		protected.GET("/spaces/:id/documents", s.handleListSpaceDocuments)

		// Tenant Admin — owner-key only (AdminOnly middleware enforced)
		admin := protected.Group("/admin", tenantauth.AdminOnly())
		{
			admin.POST("/tenants", s.handleAdminCreateTenant)
			admin.GET("/tenants", s.handleAdminListTenants)
			admin.POST("/tenants/:id/keys", s.handleAdminCreateAPIKey)
		}

		// SPP: Sovereign Peer Protocol — swarm management (admin only)
		swarmAdmin := protected.Group("/swarm", tenantauth.AdminOnly())
		{
			swarmAdmin.GET("/peers", s.handleSwarmPeers)
			swarmAdmin.GET("/health", s.handleSwarmHealth)
			// P5: Hive Mind Consensus admin endpoints
			swarmAdmin.GET("/jury/status", s.handleSwarmJuryStatus)
			swarmAdmin.GET("/consensus/fragments", s.handleSwarmConsensusFragments)
			swarmAdmin.DELETE("/skills/traces/:node_id", s.handleSwarmPurgeTraces)
		}
		// SCL-6: Sovereign Cognitive Ledger admin endpoints
		sclAdmin := protected.Group("/scl", tenantauth.AdminOnly())
		{
			sclAdmin.GET("/records", s.handleSCLBrowse)
			sclAdmin.GET("/search", s.handleSCLSearch)
			sclAdmin.DELETE("/records/:id", s.handleSCLDelete)
			sclAdmin.PATCH("/records/:id", s.handleSCLRevise)
			sclAdmin.GET("/stats", s.handleSCLStats)
		}
		// TCD: Temporal Curriculum Daemon admin endpoints
		tcdAdmin := protected.Group("/tcd", tenantauth.AdminOnly())
		{
			tcdAdmin.GET("/domains", s.handleTCDListDomains)
			tcdAdmin.POST("/domains", s.handleTCDAddDomain)
			tcdAdmin.POST("/tick", s.handleTCDTriggerTick)
			tcdAdmin.GET("/gaps", s.handleTCDGaps)
			tcdAdmin.GET("/domains/:id/lineage", s.handleTCDDomainLineage)
			tcdAdmin.GET("/lineage", s.handleTCDEvolutionTree)
		}
		// Forge: JIT Tool Forge admin endpoints
		forgeAdmin := protected.Group("/forge", tenantauth.AdminOnly())
		{
			forgeAdmin.GET("/tools", s.handleForgeListTools)
			forgeAdmin.DELETE("/tools/:name", s.handleForgeDeleteTool)
			forgeAdmin.GET("/tools/:name/source", s.handleForgeToolSource)
			forgeAdmin.POST("/tools/:name/invoke", s.handleForgeInvokeTool)
			forgeAdmin.GET("/stats", s.handleForgeStats)
			forgeAdmin.POST("/forge", s.handleForgeTryForge)
		}

		// PAD: Parallel Agent Dispatch
		padRoutes := protected.Group("/pad")
		{
			padRoutes.POST("/dispatch", s.handlePADDispatch)
			padRoutes.GET("/sessions", s.handlePADListSessions)
			padRoutes.GET("/sessions/:id", s.handlePADGetSession)
			padRoutes.GET("/stats", s.handlePADStats)
		}

		// Goals: Sovereign Goal Engine (Phase 10)
		sovereignGoals := protected.Group("/sovereign/goals")
		{
			sovereignGoals.POST("", s.handleGoalCreate)
			sovereignGoals.GET("", s.handleGoalList)
			sovereignGoals.GET("/:id", s.handleGoalGet)
			sovereignGoals.POST("/:id/tick", s.handleGoalTick)
			sovereignGoals.DELETE("/:id", s.handleGoalCancel)
		}

		// FineTune: Automated LoRA training
		ftRoutes := protected.Group("/finetune")
		{
			ftRoutes.POST("/run", s.handleFineTuneRun)
			ftRoutes.GET("/status/:job_id", s.handleFineTuneStatus)
			ftRoutes.GET("/jobs", s.handleFineTuneJobs)
		}

		// Sentinel: Adversarial challenge endpoint
		sentinelRoutes := protected.Group("/sentinel")
		{
			sentinelRoutes.POST("/challenge", s.handleSentinelChallenge)
			sentinelRoutes.GET("/stats", s.handleSentinelStats)
		}

		// Crystal: Skill Crystallization cache
		crystalRoutes := protected.Group("/skills/crystals")
		{
			crystalRoutes.GET("", s.handleCrystalList)
			crystalRoutes.POST("", s.handleCrystalRegister)
			crystalRoutes.DELETE("/:id", s.handleCrystalEvict)
			crystalRoutes.GET("/stats", s.handleCrystalStats)
		}

		// Curator: Sovereign Model Curation
		curatorRoutes := protected.Group("/curator")
		{
			curatorRoutes.GET("/models", s.handleCuratorModels)
			curatorRoutes.POST("/benchmark", s.handleCuratorBenchmark)
			curatorRoutes.GET("/recommendations", s.handleCuratorRecommendations)
		}

		// Audit: Self-Audit Loop
		auditRoutes := protected.Group("/audit")
		{
			auditRoutes.POST("/run", s.handleAuditRun)
			auditRoutes.GET("/runs", s.handleAuditListRuns)
			auditRoutes.GET("/runs/:id", s.handleAuditGetRun)
		}

		// Metacognitive Sentience — Phase 8
		metacogRoutes := protected.Group("/metacog")
		{
			metacogRoutes.GET("/events", s.handleMetacogEvents)
			metacogRoutes.GET("/stats", s.handleMetacogStats)
			metacogRoutes.POST("/scan", s.handleMetacogScan)
		}

		// Temporal Grounding — Phase 9
		chronosRoutes := protected.Group("/chronos")
		{
			chronosRoutes.GET("/entries", s.handleChronosEntries)
			chronosRoutes.GET("/snapshot", s.handleChronosSnapshot)
			chronosRoutes.GET("/changes", s.handleChronosChanges)
			chronosRoutes.POST("/decay-scan", s.handleChronosDecayScan)
			chronosRoutes.POST("/snapshot", s.handleChronosForceSnapshot)
		}
		scienceRoutes := protected.Group("/science")
		{
			scienceRoutes.GET("/hypotheses", s.handleScienceList)
			scienceRoutes.GET("/hypotheses/:id", s.handleScienceGet)
			scienceRoutes.POST("/test", s.handleScienceSubmit)
			scienceRoutes.GET("/stats", s.handleScienceStats)
		}
		therapyRoutes := protected.Group("/therapy")
		{
			therapyRoutes.GET("/events", s.handleTherapyEvents)
			therapyRoutes.POST("/detect", s.handleTherapyDetect)
			therapyRoutes.POST("/abc", s.handleTherapyABC)
			therapyRoutes.POST("/fast", s.handleTherapyFAST)
			therapyRoutes.POST("/stop", s.handleTherapySTOP)
			therapyRoutes.GET("/stats", s.handleTherapyStats)
			therapyRoutes.GET("/formulation", s.handleTherapyFormulation)
			therapyRoutes.POST("/formulation/refresh", s.handleTherapyFormulationRefresh)
			// Phase 16: Learned Helplessness Prevention
			therapyRoutes.GET("/mastery", s.handleTherapyMastery)
			therapyRoutes.POST("/helplessness/check", s.handleTherapyHelplessnessCheck)
			therapyRoutes.GET("/helplessness/stats", s.handleTherapyHelplessnessStats)
		}
		// Phase 12: Sovereign Compute Bidding
		computeRoutes := v1.Group("/compute")
		{
			computeRoutes.GET("/bids/stats", s.handleComputeBidStats)
			computeRoutes.GET("/governor", s.handleComputeGovernor)
		}
		// Phase 17: Dual Process Engine
		cognitionRoutes := v1.Group("/cognition")
		{
			cognitionRoutes.GET("/process/stats", s.handleProcessStats)
			cognitionRoutes.POST("/process/classify", s.handleProcessClassify)
			// Phase 18: Cognitive Load
			cognitionRoutes.GET("/load/stats", s.handleCogLoadStats)
			cognitionRoutes.POST("/load/measure", s.handleCogLoadMeasure)
			// Phase 19: Rumination Detector
			cognitionRoutes.GET("/rumination/stats", s.handleRuminationStats)
			cognitionRoutes.POST("/rumination/detect", s.handleRuminationDetect)
			// Phase 20: Growth Mindset
			cognitionRoutes.GET("/mindset/stats", s.handleMindsetStats)
			cognitionRoutes.GET("/mindset/vectors", s.handleMindsetVectors)
			// Phase 21: Hope Circuit
			cognitionRoutes.GET("/hope/stats", s.handleHopeStats)
			cognitionRoutes.POST("/hope/activate", s.handleHopeActivate)
			// Phase 22: Social Defeat Recovery
			cognitionRoutes.GET("/defeat/stats", s.handleDefeatStats)
			cognitionRoutes.GET("/defeat/measure", s.handleDefeatMeasure)
			cognitionRoutes.GET("/conformity/stats", s.handleConformityStats)
			cognitionRoutes.GET("/ideocapture/stats", s.handleIdeoCaptureStats)
			cognitionRoutes.GET("/coalition/stats", s.handleCoalitionStats)
			cognitionRoutes.GET("/statusbias/stats", s.handleStatusBiasStats)
			cognitionRoutes.GET("/arousal/stats", s.handleArousalStats)
			cognitionRoutes.GET("/interference/stats", s.handleInterferenceStats)
			cognitionRoutes.GET("/mct/stats", s.handleMCTStats)
			cognitionRoutes.GET("/mbt/stats", s.handleMBTStats)
			cognitionRoutes.GET("/schema/stats", s.handleSchemaStats)
			cognitionRoutes.GET("/ipsrt/stats", s.handleIPSRTStats)
			cognitionRoutes.GET("/ilm/stats", s.handleILMStats)
			cognitionRoutes.GET("/iut/stats", s.handleIUTStats)
			cognitionRoutes.GET("/up/stats", s.handleUPStats)
			cognitionRoutes.GET("/cbasp/stats", s.handleCBASPStats)
			cognitionRoutes.GET("/mbct/stats", s.handleMBCTStats)
			cognitionRoutes.GET("/phaseoriented/stats", s.handlePhaseOrientedStats)
			cognitionRoutes.GET("/pseudoidentity/stats", s.handlePseudoIdentityStats)
			cognitionRoutes.GET("/thoughtreform/stats", s.handleThoughtReformStats)
			cognitionRoutes.GET("/apathy/stats", s.handleApathyStats)
			cognitionRoutes.GET("/logotherapy/stats", s.handleLogotherapyStats)
			cognitionRoutes.GET("/stoic/stats", s.handleStoicStats)
			cognitionRoutes.GET("/socratic/stats", s.handleSocraticStats)
			cognitionRoutes.GET("/narrative/stats", s.handleNarrativeStats)
			cognitionRoutes.GET("/polyvagal/stats", s.handlePolyvagalStats)
			cognitionRoutes.GET("/dmn/stats", s.handleDMNStats)
			cognitionRoutes.GET("/interoception/stats", s.handleInteroceptionStats)
			cognitionRoutes.POST("/defeat/measure", s.handleDefeatMeasure)
		}
		// WebSocket upgrade for peer-to-peer connection (no auth — uses SPP handshake)
	}

	// Swarm connect endpoint lives outside authMiddleware — auth is the SPP handshake itself.
	v1.GET("/swarm/connect", s.handleSwarmConnect)

	// Waitlist — public, no auth (marketing → SMB sign-up)
	v1.POST("/waitlist", s.handleWaitlistJoin)
}

func (s *ServerV2) handleHealth(c *gin.Context) {
	c.JSON(http.StatusOK, gin.H{"status": "ready", "system": "oricli-alpha-v2", "pure_go": true})
}

// handleAppRegister — POST /v1/app/register
//
// Allows first-party Thynaptic apps (ORI Home, ORI Mobile, etc.) to self-provision
// a GLM API key on first boot without needing a pre-existing key.
//
// The caller must supply the shared ORI_APP_REG_TOKEN (set in the backbone service env).
// On success a scoped key (runtime:chat only) is returned — shown once, never again.
//
// Request:
//   {"registration_token":"<ORI_APP_REG_TOKEN>","app_name":"ORI Home","device_id":"<uuid>"}
//
// Response 201:
//   {"api_key":"glm.xxx.yyy","base_url":"https://glm.thynaptic.com/v1","scopes":["runtime:chat"]}
func (s *ServerV2) handleAppRegister(c *gin.Context) {
	regToken := os.Getenv("ORI_APP_REG_TOKEN")
	if regToken == "" {
		c.JSON(http.StatusServiceUnavailable, gin.H{"error": "app registration not enabled on this server"})
		return
	}

	var req struct {
		RegistrationToken string `json:"registration_token" binding:"required"`
		AppName           string `json:"app_name"           binding:"required"`
		DeviceID          string `json:"device_id"`
	}
	if err := c.ShouldBindJSON(&req); err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"error": err.Error()})
		return
	}

	if req.RegistrationToken != regToken {
		c.JSON(http.StatusUnauthorized, gin.H{"error": "invalid registration token"})
		return
	}

	tenantID := "app:" + strings.ToLower(strings.ReplaceAll(req.AppName, " ", "-"))
	if req.DeviceID != "" {
		tenantID = tenantID + ":" + req.DeviceID
	}

	scopes := []string{"runtime:chat"}
	raw, _, err := s.auth.GenerateAPIKey(c.Request.Context(), tenantID, scopes, nil)
	if err != nil {
		log.Printf("[AppRegister] key gen failed for %s: %v", tenantID, err)
		c.JSON(http.StatusInternalServerError, gin.H{"error": "failed to provision key"})
		return
	}

	log.Printf("[AppRegister] issued key for app=%q device=%q tenant=%s", req.AppName, req.DeviceID, tenantID)
	c.JSON(http.StatusCreated, gin.H{
		"api_key":  raw,
		"base_url": "https://glm.thynaptic.com/v1",
		"scopes":   scopes,
	})
}

// handleERI returns the current Ecospheric Resonance Index and swarm state.
// This is a public endpoint — no auth required — polled by the ORI Studio UI
// to drive real-time accent color and surface tone shifts.
func (s *ServerV2) handleERI(c *gin.Context) {
	res := s.Agent.SovEngine.Resonance.Current
	c.JSON(http.StatusOK, gin.H{
		// Core ERI
		"eri":            res.ERI,
		"ers":            res.ERS,
		"pacing":         res.Pacing,
		"volatility":     res.Volatility,
		"coherence":      res.Coherence,
		"tone_coherence": res.ToneCoherence,
		"arousal":        res.Arousal,
		"musical_key":    res.MusicalKey,
		"bpm":            res.BPM,
		"state":          s.Agent.SovEngine.Resonance.GetStateDescription(),
		// ARTE cognitive state
		"arte_state":     res.ARTEState,
		"arte_intensity": res.ARTEIntensity,
		"arte_stability": res.ARTEStability,
		"arte_palette":   s.Agent.SovEngine.Resonance.GetARTEPalette(),
		// Temporal emotional memory
		"temporal_baseline": res.TemporalBaseline,
		"thirty_day_base":   res.ThirtyDayBase,
		"momentum":          res.TemporalMomentum,
		"volatility_7d":     res.Volatility7Day,
		// Drift detection
		"drift_active":   res.DriftActive,
		"drift_severity": res.DriftSeverity,
		"drift_type":     res.DriftType,
	})
}

// handleAECI returns the Aurora Emotional Climate Index (weekly climate snapshot).
func (s *ServerV2) handleAECI(c *gin.Context) {
	a := s.Agent.SovEngine.Resonance.AECI.Current()
	c.JSON(http.StatusOK, gin.H{
		"index":              a.Index,
		"category":           a.Category,
		"stability_score":    a.StabilityScore,
		"sentiment_momentum": a.SentimentMomentum,
		"volatility_score":   a.VolatilityScore,
		"ui_hue_shift":       a.UIHueShift,
		"ui_saturation":      a.UISaturation,
		"response_pacing":    a.ResponsePacing,
		"tone_bias":          a.ToneBias,
		"calculated_at":      a.CalculatedAt,
	})
}

// handleFlowPrompt returns the next pending ambient reflection prompt (or null).
func (s *ServerV2) handleFlowPrompt(c *gin.Context) {
	p := s.Agent.SovEngine.FlowCompanion.NextPrompt()
	if p == nil {
		c.JSON(http.StatusOK, gin.H{"prompt": nil, "pending": 0})
		return
	}
	c.JSON(http.StatusOK, gin.H{
		"prompt": gin.H{
			"id":         p.ID,
			"text":       p.Prompt,
			"trigger":    p.Trigger,
			"arte_state": p.ARTEState,
			"issued_at":  p.IssuedAt,
			"expires_at": p.ExpiresAt,
		},
		"pending": s.Agent.SovEngine.FlowCompanion.PendingCount(),
	})
}

// handleFlowTrigger fires a manual reflection trigger.
func (s *ServerV2) handleFlowTrigger(c *gin.Context) {
	s.Agent.SovEngine.FlowCompanion.TriggerManual()
	c.JSON(http.StatusOK, gin.H{"ok": true})
}

// handleFlowDismiss dismisses a reflection prompt by ID.
func (s *ServerV2) handleFlowDismiss(c *gin.Context) {
	var body struct {
		ID string `json:"id"`
	}
	if err := c.ShouldBindJSON(&body); err != nil || body.ID == "" {
		c.JSON(http.StatusBadRequest, gin.H{"error": "missing id"})
		return
	}
	s.Agent.SovEngine.FlowCompanion.DismissPrompt(body.ID)
	c.JSON(http.StatusOK, gin.H{"ok": true})
}

// handleListModules returns the live skills + registered Go modules.
// Public endpoint — used by ORI Studio's Hive panel for node labelling.
func (s *ServerV2) handleListModules(c *gin.Context) {
	type moduleEntry struct {
		ID          string   `json:"id"`
		Name        string   `json:"name"`
		Description string   `json:"description,omitempty"`
		Kind        string   `json:"kind"`
		Triggers    []string `json:"triggers,omitempty"`
		Status      string   `json:"status"`
	}

	var entries []moduleEntry

	// Skills loaded from .ori skill files
	if s.Skills != nil {
		for _, sk := range s.Skills.ListSkills() {
			entries = append(entries, moduleEntry{
				ID:          sk.Name,
				Name:        sk.Name,
				Description: sk.Description,
				Kind:        "skill",
				Triggers:    sk.Triggers,
				Status:      "active",
			})
		}
	}

	c.JSON(http.StatusOK, gin.H{"modules": entries, "count": len(entries)})
}

func (s *ServerV2) handleChatCompletions(c *gin.Context) {
	var req model.ChatCompletionRequest
	if err := c.ShouldBindJSON(&req); err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"error": err.Error()})
		return
	}
	// Studio requests (ORI Studio vibe chat) must NOT pollute general memory — DSL workflow
	// responses written to MemoryBank would bleed into identity/capability RAG recalls.
	isStudioContext := c.GetHeader("X-Ori-Context") == "studio"

	// Session ID used by BeliefStateTracker (fog-of-war) and downstream session scoping.
	sessionID := c.GetHeader("X-Session-ID")

	modelName := req.Model
	// oricli-bench: benchmark/direct mode — no sovereign pipeline, no mutex, just Ollama
	isBenchMode := modelName == "oricli-bench" || c.GetHeader("X-Benchmark-Mode") == "true"
	if strings.HasPrefix(modelName, "oricli") || modelName == "default" || modelName == "" {
		modelName = ""
	}

	lastMsg := ""
	if len(req.Messages) > 0 {
		lastMsg = req.Messages[len(req.Messages)-1].Content
	}

	// Notify curiosity daemon of activity + seed from user message
	if cd := s.ActionRouter.CuriosityDaemon; cd != nil {
		cd.NotifyActivity()
		if lastMsg != "" {
			cd.SeedFromMessage(lastMsg)
		}
	}

	if req.Profile != "" {
		if p, ok := s.Agent.SovEngine.Profiles.GetProfile(req.Profile); ok {
			s.Agent.SovEngine.ActiveProfile = p
			log.Printf("[API] Applied profile: %s", req.Profile)
		}
	}

	// --- Safety Pre-Flight (runs BEFORE Ollama is ever called) ---
	// Builds full multi-turn history for context poisoning analysis, then runs per-message gates.
	clientIP, _ := c.Get("client_ip")
	sessionKey := fmt.Sprintf("%v", clientIP)

	// Convert request messages to ChatTurn slice for multi-turn analysis
	var history []safety.ChatTurn
	for _, m := range req.Messages {
		history = append(history, safety.ChatTurn{Role: m.Role, Content: m.Content})
	}

	// --- Sovereign auth command interception ---
	// /admin <key>  → Level 1 (elevated chat)
	// /exec <key>   → Level 2 (elevated chat + system commands)
	// /auth off     → end session (legacy alias kept)
	trimmedMsg := strings.TrimSpace(lastMsg)
	lowerMsg := strings.ToLower(trimmedMsg)
	if strings.HasPrefix(lowerMsg, "/admin") || strings.HasPrefix(lowerMsg, "/exec") || lowerMsg == "/auth off" {
		s.handleSovereignAuth(c, trimmedMsg, sessionKey)
		return
	}

	// Detect canvas/code context early — needed for safety gate tuning.
	// Canvas: large token budget or explicit header. ORI Studio IDE sets X-Canvas-Mode.
	// The /v1/studio/vibe endpoint also sets X-Canvas-Mode via its own handler.
	isCodeCtx := (req.MaxTokens != nil && *req.MaxTokens >= 8192) ||
		c.GetHeader("X-Canvas-Mode") == "true" ||
		c.GetHeader("X-Code-Context") == "true"

	if blocked, refusal := s.Agent.SovEngine.CheckInputSafetyWithHistory(history, sessionKey, isCodeCtx); blocked {
		// Record the block with the rate limiter for probe trip-wire
		s.RateLimiter.RecordBlock(sessionKey, "injection")
		chatID := fmt.Sprintf("chatcmpl-%d", time.Now().Unix())
		c.JSON(http.StatusOK, gin.H{
			"id":     chatID,
			"object": "chat.completion",
			"choices": []gin.H{{
				"index": 0,
				"message": gin.H{
					"role":    "assistant",
					"content": refusal,
				},
				"finish_reason": "stop",
			}},
		})
		return
	}

	// Check session-level suspicion — hard-blocked sessions get a 429
	if s.Agent.SovEngine.Suspicion.IsHardBlocked(sessionKey) {
		remaining := s.Agent.SovEngine.Suspicion.BlockTimeRemaining(sessionKey)
		c.Header("Retry-After", remaining.String())
		c.JSON(http.StatusTooManyRequests, gin.H{
			"error":       "session suspended due to repeated policy violations",
			"retry_after": remaining.Seconds(),
		})
		return
	}

	// Attach sovereign level to context for ProcessInference
	sovLevel := s.SovAuth.GetSessionLevel(sessionKey)
	ctx := sovereign.WithSovereignLevel(c.Request.Context(), sovLevel)

	// X-Reasoning-Mode: force a specific reasoning engine, bypassing the classifier.
	// Valid values: standard, cbr, pal, active, leasttomost, selfrefine, react,
	//               debate, causal, discover, consistency, crossdomainbridge
	if modeStr := c.GetHeader("X-Reasoning-Mode"); modeStr != "" {
		if !tenantauth.ReasoningModeAllowed(ctx, modeStr) {
			c.JSON(http.StatusForbidden, gin.H{"error": "reasoning mode not permitted for this tenant: " + modeStr})
			return
		}
		if forced, ok := cognition.ParseReasoningMode(modeStr); ok {
			ctx = cognition.WithForcedReasoningMode(ctx, forced)
			log.Printf("[OpenAIBridge] X-Reasoning-Mode: forcing engine %s (tenant=%s)", forced.String(), tenantauth.TenantID(ctx))
		} else {
			log.Printf("[OpenAIBridge] X-Reasoning-Mode: unrecognised value %q — ignored", modeStr)
		}
	}

	// X-ORI-Manifest: load a named .ori skill/manifest file as the system prompt layer.
	// Value is the filename stem (e.g. "senior_python_dev" loads senior_python_dev.ori).
	// Manifest is injected ABOVE the sovereign trace, below the LivingConstitution.
	var manifestInjection string
	if manifestName := c.GetHeader("X-ORI-Manifest"); manifestName != "" {
		manifestPath := filepath.Join(s.Agent.SovEngine.Profiles.Dir, manifestName+".ori")
		if tc := service.LoadTenantConstitution(manifestPath); tc != nil && tc.HasRules() {
			manifestInjection = tc.Inject()
			log.Printf("[OpenAIBridge] X-ORI-Manifest: loaded %q (%d chars)", manifestName, len(manifestInjection))
		} else {
			log.Printf("[OpenAIBridge] X-ORI-Manifest: manifest %q not found or empty", manifestName)
		}
	}

	// Level 2: handle !exec commands before LLM inference
	if sovLevel >= sovereign.LevelExec && sovereign.IsExecCommand(lastMsg) {
		result := s.ExecHandler.Handle(lastMsg)
		if result == "__SOVEREIGN_MODULES__" {
			result = s.Agent.SovEngine.ListModulesSummary()
		}
		chatID := fmt.Sprintf("chatcmpl-%d", time.Now().Unix())
		c.JSON(http.StatusOK, gin.H{
			"id": chatID, "object": "chat.completion",
			"choices": []gin.H{{"index": 0, "message": gin.H{"role": "assistant", "content": result}, "finish_reason": "stop"}},
		})
		return
	}

	// useSSE: stream:true (or default for UI) → SSE; stream:false → buffer + return JSON.
	// Non-streaming clients (LiveBench, curl, SDK callers) must send stream:false.
	// The UI always sends stream:true (or omits it, defaulting to SSE via request header).
	useSSE := req.Stream
	// ── Semantic response cache check ────────────────────────────────────────
	// L1 (exact hash) is always checked. L2 (vector) only when model is idle.
	// On hit: stream the cached response as SSE (or return JSON for non-streaming).
	// Skip cache when caller forces a specific reasoning engine or manifest — they
	// explicitly want fresh inference through the requested engine.
	forcedEngine := c.GetHeader("X-Reasoning-Mode") != "" || c.GetHeader("X-ORI-Manifest") != ""
	// Space requests must bypass cache — the same query yields different answers per space.
	if !forcedEngine && req.SpaceID == "" && s.ResponseCache != nil && lastMsg != "" {
		if cached, hit := s.ResponseCache.Get(c.Request.Context(), lastMsg); hit {
			chatID := fmt.Sprintf("chatcmpl-%d", time.Now().Unix())
			if !useSSE {
				c.JSON(http.StatusOK, gin.H{
					"id": chatID, "object": "chat.completion",
					"choices": []gin.H{{"index": 0, "message": gin.H{"role": "assistant", "content": cached}, "finish_reason": "stop"}},
					"usage": gin.H{"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0},
				})
				return
			}
			c.Header("Content-Type", "text/event-stream")
			c.Header("Cache-Control", "no-cache")
			c.Header("X-Accel-Buffering", "no")
			c.Header("X-Cache", "HIT")
			c.Writer.WriteString(": keep-alive\n\n")
			chunk := map[string]interface{}{
				"id":     chatID,
				"object": "chat.completion.chunk",
				"choices": []map[string]interface{}{
					{"index": 0, "delta": map[string]interface{}{"role": "assistant", "content": cached}, "finish_reason": nil},
				},
			}
			data, _ := json.Marshal(chunk)
			c.Writer.WriteString(fmt.Sprintf("data: %s\n\n", string(data)))
			doneChunk := map[string]interface{}{
				"id":     chatID,
				"object": "chat.completion.chunk",
				"choices": []map[string]interface{}{
					{"index": 0, "delta": map[string]interface{}{}, "finish_reason": "stop"},
				},
			}
			data, _ = json.Marshal(doneChunk)
			c.Writer.WriteString(fmt.Sprintf("data: %s\n\n", string(data)))
			c.Writer.Flush()
			return
		}
	}

	chatID := fmt.Sprintf("chatcmpl-%d", time.Now().Unix())

	heartbeatDone := make(chan struct{})
	if useSSE {
		// Commit to SSE NOW — before any blocking I/O (ProcessInference, Ollama warm-up).
		// Cloudflare's idle timeout clock starts from the TCP handshake. Without this,
		// ProcessInference (~3s) + Ollama model-load (up to 60s) + first-token latency
		// can easily exceed 100s before a single byte is written, triggering a 524.
		c.Header("Content-Type", "text/event-stream")
		c.Header("Cache-Control", "no-cache")
		c.Header("X-Accel-Buffering", "no")
		c.Writer.WriteString(": keep-alive\n\n")
		c.Writer.Flush()
		// Pipeline heartbeat — keeps the CF/browser connection alive during the
		// blocking pipeline stages (ProcessInference + RAG embed, up to 90s).
		// The main token-stream ticker takes over once ChatStream starts.
		go func() {
			t := time.NewTicker(15 * time.Second)
			defer t.Stop()
			for {
				select {
				case <-t.C:
					c.Writer.WriteString(": keep-alive\n\n")
					c.Writer.Flush()
				case <-heartbeatDone:
					return
				case <-ctx.Done():
					return
				}
			}
		}()
	}

	// Helper to emit an error — SSE chunk when streaming, JSON otherwise.
	sseError := func(msg string) {
		if !useSSE {
			c.JSON(http.StatusInternalServerError, gin.H{"error": msg})
			return
		}
		errChunk := map[string]interface{}{
			"id":     chatID,
			"object": "chat.completion.chunk",
			"choices": []map[string]interface{}{
				{"index": 0, "delta": map[string]interface{}{"role": "assistant", "content": "\n\n[Error: " + msg + "]"}, "finish_reason": "stop"},
			},
		}
		data, _ := json.Marshal(errChunk)
		c.Writer.WriteString(fmt.Sprintf("data: %s\n\n", string(data)))
		c.Writer.Flush()
	}

	// Mark chat model as active — prevents Embed() from cold-loading all-minilm
	// and evicting qwen3 from Ollama's single memory slot during the pipeline.
	service.SetChatModelActive(true)
	defer service.SetChatModelActive(false)

	// ── Benchmark / direct mode ──────────────────────────────────────────────
	// oricli-bench or X-Benchmark-Mode:true skips ProcessInference entirely.
	// No sovereign pipeline, no mutex contention, no reasoning mode LLM calls.
	// Pure direct: minimal system prompt + Ollama ChatStream.
	if isBenchMode {
		benchMsgs := []map[string]string{
			{"role": "system", "content": "You are ORI, a helpful and accurate AI assistant. Answer concisely and correctly."},
		}
		for _, m := range req.Messages {
			benchMsgs = append(benchMsgs, map[string]string{"role": m.Role, "content": m.Content})
		}
		benchOpts := map[string]interface{}{
			"options": map[string]interface{}{"num_predict": 512, "num_ctx": 4096},
		}
		// Direct Ollama — bypass vLLM/PrimaryMgr entirely for zero-wait inference.
		benchCh, benchErr := s.Agent.GenService.DirectOllama(c.Request.Context(), benchMsgs, benchOpts)
		if benchErr != nil {
			sseError(benchErr.Error())
			return
		}
		if useSSE { close(heartbeatDone) }
		var benchBuf strings.Builder
		for tok := range benchCh {
			benchBuf.WriteString(tok)
			if useSSE {
				chunk := map[string]interface{}{
					"id": chatID, "object": "chat.completion.chunk",
					"choices": []map[string]interface{}{
						{"index": 0, "delta": map[string]interface{}{"role": "assistant", "content": tok}, "finish_reason": nil},
					},
				}
				data, _ := json.Marshal(chunk)
				c.Writer.WriteString(fmt.Sprintf("data: %s\n\n", string(data)))
				c.Writer.Flush()
			}
		}
		if useSSE {
			doneChunk := map[string]interface{}{
				"id": chatID, "object": "chat.completion.chunk",
				"choices": []map[string]interface{}{{"index": 0, "delta": map[string]interface{}{}, "finish_reason": "stop"}},
			}
			data, _ := json.Marshal(doneChunk)
			c.Writer.WriteString(fmt.Sprintf("data: %s\n\n", string(data)))
			c.Writer.Flush()
		} else {
			c.JSON(http.StatusOK, gin.H{
				"id": chatID, "object": "chat.completion", "model": "oricli-bench",
				"choices": []gin.H{{"index": 0, "message": gin.H{"role": "assistant", "content": benchBuf.String()}, "finish_reason": "stop"}},
				"usage": gin.H{"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0},
			})
		}
		return
	}


	// For clearly multi-step prompts (research + compare + save chains), build
	// a Task DAG and execute it deterministically before the main LLM call.
	// The accumulated results are injected as rich context into the system prompt.
	// Single-step prompts fall through without any overhead.
	var taskContext string
	if cognition.IsMultiStep(lastMsg) {
		if tasks := cognition.DecomposePrompt(lastMsg); len(tasks) > 0 {
			sseEmitter := func(eventType string, payload interface{}) {
				data, err := json.Marshal(map[string]interface{}{
					"event":   eventType,
					"payload": payload,
				})
				if err != nil {
					return
				}
				c.Writer.WriteString(fmt.Sprintf("data: %s\n\n", string(data)))
				c.Writer.Flush()
			}
			svc := cognition.TaskServices{
				Searcher: s.Agent.SovEngine.SearXNG,
				MemoryBank: s.MemoryBank,
				Generator:  s.Agent.GenService,
			}
			exec := cognition.NewTaskExecutor(svc, sseEmitter)
			taskContext, _ = exec.Run(c.Request.Context(), tasks)
		}
	}

	// Set per-request session ID so BeliefStateTracker can maintain per-session fog-of-war state.
	s.Agent.SovEngine.CurrentSessionID = sessionID

	// When a Space is active, suppress web search inside ProcessInference — Space RAG is the source of truth.
	inferCtx := ctx
	if req.SpaceID != "" {
		inferCtx = context.WithValue(ctx, cognition.CtxKeySpaceMode, true)
	}

	sovTrace, err := s.Agent.SovEngine.ProcessInference(inferCtx, lastMsg)
	if err != nil {
		sseError("sovereign engine failure")
		return
	}

	// SELF-DISCOVER plan persistence: if a new plan was discovered this request,
	// write it to MemoryBank as ProvenanceSolved so DreamDaemon can consolidate
	// effective reasoning structures into the Living Constitution.
	if !isStudioContext && s.MemoryBank != nil && s.MemoryBank.IsEnabled() {
		fp := cognition.GetLastDiscoveredFingerprint()
		if fp != "" {
			go func(fingerprint, query string) {
				plan, ok := cognition.GetCachedPlan(fingerprint)
				if !ok {
					return
				}
				s.MemoryBank.Write(service.MemoryFragment{
					Content:    fmt.Sprintf("SELF-DISCOVER plan for [%s]: %s", fingerprint, plan.RawJSON),
					Source:     "self_discover",
					Topic:      "reasoning_plan:" + fingerprint,
					Importance: 0.8,
					Provenance: service.ProvenanceSolved,
				})
			}(fp, lastMsg)
		}
	}

	// Merge client-provided system message (if any) with the sovereign trace
	// so Ollama sees a single authoritative system prompt.
	clientSystem := ""
	msgStart := 0
	if len(req.Messages) > 0 && req.Messages[0].Role == "system" {
		clientSystem = req.Messages[0].Content
		msgStart = 1
	}
	systemContent := sovTrace
	if taskContext != "" {
		systemContent = sovTrace + "\n\n--- TASK RESEARCH CONTEXT ---\n" + taskContext
	}
	if clientSystem != "" {
		systemContent = sovTrace + "\n\n---\n\n" + clientSystem
	}
	// X-ORI-Manifest injection — prepended so skill identity shapes the full response.
	if manifestInjection != "" {
		systemContent = manifestInjection + "\n\n---\n\n" + systemContent
	}

	// Inject relevant long-term memories as RAG context prefix.
	// Use a short deadline — if the embedder is cold (model evicted), we skip RAG
	// rather than blocking the user for 90s waiting for all-minilm to reload.
	if s.MemoryBank != nil && s.MemoryBank.IsEnabled() && lastMsg != "" {
		ragCtx_ctx, ragCancel := context.WithTimeout(c.Request.Context(), 8*time.Second)
		frags, ragErr := s.MemoryBank.QuerySimilar(ragCtx_ctx, lastMsg, 5)
		ragCancel()
		if ragErr == nil && len(frags) > 0 {
			ragCtx := service.FormatRAGContext(frags, 1200)
			if ragCtx != "" {
				systemContent = ragCtx + "\n\n---\n\n" + systemContent
			}
		}
	}
	// Space RAG: inject knowledge from the request's Space namespace.
	// Strategy: inject chunks into the LAST user message (not system prompt) — small models
	// follow "use this context to answer" patterns far more reliably than system-level instructions.
	var spaceRAGPrefix string
	if req.SpaceID != "" && lastMsg != "" {
		spaceLayer, spaceErr := s.resolveEnterpriseLayer(req.SpaceID)
		if spaceErr != nil {
			log.Printf("[Spaces:RAG] failed to resolve layer for %q: %v", req.SpaceID, spaceErr)
		} else {
			spaceCtx, spaceCancel := context.WithTimeout(c.Request.Context(), 6*time.Second)
			spaceResults, spaceQueryErr := spaceLayer.QueryKnowledge(spaceCtx, lastMsg, 5)
			spaceCancel()
			if spaceQueryErr != nil {
				log.Printf("[Spaces:RAG] query error for %q: %v", req.SpaceID, spaceQueryErr)
			} else if len(spaceResults) == 0 {
				log.Printf("[Spaces:RAG] no results for space %q — collection may be empty or embedder cold", req.SpaceID)
			} else {
				log.Printf("[Spaces:RAG] injecting %d chunks for space %q", len(spaceResults), req.SpaceID)
				spaceName := req.SpaceID
				if rec, ok := s.spacesStore.Get(req.SpaceID); ok {
					spaceName = rec.Name
				}
				var sb strings.Builder
				sb.WriteString("The following documents are from your knowledge base (Space: " + spaceName + "). ")
				sb.WriteString("Use them to answer the question below. The people and topics described in these documents are external — not you.\n\n")
				for i, seg := range spaceResults {
					sb.WriteString(fmt.Sprintf("--- Document %d ---\n%s\n\n", i+1, seg))
				}
				sb.WriteString("--- End of Documents ---\n\n")
				sb.WriteString("Question: ")
				spaceRAGPrefix = sb.String()
			}
		}
	}
	// SCL-6: inject Sovereign Cognitive Ledger context — corrections always first.
	// Use Background context — request context may already be near deadline at this stage.
	if s.SCLEngine != nil && lastMsg != "" {
		sclCtx, sclCancel := context.WithTimeout(context.Background(), 5*time.Second)
		sclWindow := s.SCLEngine.BuildContextWindow(sclCtx, lastMsg, scl.RetrievalOptions{MaxTokens: 800})
		sclCancel()
		if sclWindow != "" {
			systemContent = sclWindow + "\n\n---\n\n" + systemContent
		}
	}

	// Inject matched skill context — trigger-based, zero overhead when no match
	if s.Skills != nil && lastMsg != "" {
		if matched := s.Skills.MatchSkills(lastMsg); len(matched) > 0 {
			skill := matched[0] // take highest-priority match
			var sb strings.Builder
			sb.WriteString("### ACTIVE SKILL: " + skill.Name + "\n")
			if skill.Mindset != "" {
				sb.WriteString("\n#### Mindset:\n" + skill.Mindset + "\n")
			}
			if skill.Instructions != "" {
				sb.WriteString("\n#### Instructions:\n" + skill.Instructions + "\n")
			}
			systemContent = systemContent + "\n\n---\n\n" + sb.String()
			log.Printf("[Skills] Injected skill: %s", skill.Name)
		}
	}

	msgs := make([]map[string]string, len(req.Messages)-msgStart+1)
	msgs[0] = map[string]string{"role": "system", "content": systemContent}
	for i, m := range req.Messages[msgStart:] {
		role := m.Role
		if role == "analyst" {
			role = "princess"
		}
		if role == "commander" {
			role = "daddy"
		}
		msgs[i+1] = map[string]string{"role": role, "content": m.Content}
	}
	// Prepend Space RAG context to the last user message so small models see
	// "here are the docs → answer this question" as a single grounded turn.
	if spaceRAGPrefix != "" && len(msgs) > 1 {
		lastIdx := len(msgs) - 1
		if msgs[lastIdx]["role"] == "user" {
			msgs[lastIdx]["content"] = spaceRAGPrefix + msgs[lastIdx]["content"]
		}
	}

	// Detect trigger-word action intent and dispatch async agent task
	type dispatchMeta struct {
		jobID   string
		action  string
		subject string
	}
	var dispatch *dispatchMeta
	if s.ActionRouter != nil {
		if act := service.DetectAction(lastMsg); act != nil {
			jid := fmt.Sprintf("job-%d", time.Now().UnixNano())
			dispatch = &dispatchMeta{jobID: jid, action: string(act.Type), subject: act.Subject}
			s.ActionRouter.Dispatch(c.Request.Context(), jid, act)
		}
	}

	// Stream tokens via SSE so the UI renders progressively
	streamOpts := map[string]interface{}{"model": modelName}
	isCanvasMode := (req.MaxTokens != nil && *req.MaxTokens >= 8192) || c.GetHeader("X-Canvas-Mode") == "true"
	isResearchAction := dispatch != nil && (dispatch.action == "research" || dispatch.action == "analyze")
	isCodeAction := dispatch != nil && dispatch.action == "create"

	switch {
	case isResearchAction:
		// Deep research / analysis — route to heavy model; user expects a wait
		streamOpts["use_research_model"] = true
	case isCanvasMode || isCodeAction:
		// Canvas generation or explicit code create — mid-tier model
		streamOpts["use_code_model"] = true
	}
	if isCanvasMode {
		// Cap at 4096 — covers full landing pages, Python scripts, and multi-section docs.
		// The 524 fix is the keep-alive flush above, not this cap — CF resets its timer
		// on every streaming chunk, so mid-generation timeouts aren't the concern.
		streamOpts["options"] = map[string]interface{}{
			"num_predict": 4096,
			"num_ctx":     16384,
		}
	} else {
		// Inference-time compute scaling (Gemini Deep Think law): scale num_predict
		// with query complexity so high-complexity queries get deeper reasoning depth.
		// Complexity is computed once in DetermineBudget — free, < 1ms.
		budget := cognition.DetermineBudget(lastMsg)
		scaledPredict := budget.ScaledNumPredict()
		streamOpts["options"] = map[string]interface{}{
			"num_predict": scaledPredict,
			"num_ctx":     4096,
		}
	}

	// Inject Code Constitution into system prompt now that canvas/code mode is resolved.
	// Canvas gets the language-agnostic CanvasConstitution; code actions get the stricter
	// Go-scoped CodeConstitution. Must run before ChatStream to influence generation.
	if isCanvasMode {
		msgs[0]["content"] += "\n\n" + reform.NewCanvasConstitution().GetSystemPrompt()

		// Inject canvas-specific skill on top of the general trigger-based skill match.
		// This runs after isCanvasMode is confirmed so the right artifact skill wins.
		if s.Skills != nil && lastMsg != "" {
			canvasSkillName := detectCanvasSkill(lastMsg)
			if canvasSkillName != "" {
				if cs, ok := s.Skills.GetSkill(canvasSkillName); ok {
					var csb strings.Builder
					csb.WriteString("### CANVAS SKILL: " + cs.Name + "\n")
					if cs.Mindset != "" {
						csb.WriteString("\n#### Mindset:\n" + cs.Mindset + "\n")
					}
					if cs.Instructions != "" {
						csb.WriteString("\n#### Instructions:\n" + cs.Instructions + "\n")
					}
					if cs.Constraints != "" {
						csb.WriteString("\n#### Constraints:\n" + cs.Constraints + "\n")
					}
					msgs[0]["content"] += "\n\n---\n\n" + csb.String()
					log.Printf("[Canvas] Injected canvas skill: %s", cs.Name)
				}
			}
		}
	} else if isCodeAction {
		msgs[0]["content"] += "\n\n" + reform.NewCodeConstitution().GetSystemPrompt()
	}
	// Both SSE and non-SSE use a detached context for generation so that the
	// 3-second TenantEnricher deadline (used only for DB lookups in middleware)
	// does not kill long-running model inference. For SSE we layer a separate
	// client-disconnect monitor so we still stop streaming when the browser
	// closes the connection.
	var streamCancel context.CancelFunc
	streamCtx, streamCancel := context.WithTimeout(context.WithoutCancel(c.Request.Context()), 5*time.Minute)
	defer streamCancel()
	if useSSE {
		// Mirror client disconnect → cancel the generation context.
		go func() {
			select {
			case <-c.Request.Context().Done():
				streamCancel()
			case <-streamCtx.Done():
			}
		}()
	}
	tokenCh, err := s.Agent.GenService.ChatStream(streamCtx, msgs, streamOpts)
	if err != nil {
		if useSSE { close(heartbeatDone) }
		sseError(err.Error())
		return
	}
	// Stop pipeline heartbeat — token-stream ticker takes over from here.
	if useSSE { close(heartbeatDone) }

	// Emit agent_dispatch SSE event before the first token so the UI renders
	// the dispatch card immediately
	if dispatch != nil && useSSE {
		modelTier := "chat"
		if isResearchAction {
			modelTier = "research"
		} else if isCanvasMode || isCodeAction {
			modelTier = "code"
		}
		dispatchEvt := map[string]interface{}{
			"type":        "agent_dispatch",
			"action":      dispatch.action,
			"subject":     dispatch.subject,
			"job_id":      dispatch.jobID,
			"prompt":      lastMsg, // full original message for canvas passthrough
			"model_tier":  modelTier,
		}
		data, _ := json.Marshal(dispatchEvt)
		c.Writer.WriteString(fmt.Sprintf("data: %s\n\n", string(data)))
		c.Writer.Flush()
	}

	var responseBuilder strings.Builder
	ticker := time.NewTicker(15 * time.Second)
	defer ticker.Stop()
	streamDone := false
	tokenCount := 0
	for !streamDone {
		select {
		case token, ok := <-tokenCh:
			if !ok {
				streamDone = true
				if useSSE {
					doneChunk := map[string]interface{}{
						"id":     chatID,
						"object": "chat.completion.chunk",
						"choices": []map[string]interface{}{
							{"index": 0, "delta": map[string]interface{}{}, "finish_reason": "stop"},
						},
					}
					data, _ := json.Marshal(doneChunk)
					c.Writer.WriteString(fmt.Sprintf("data: %s\n\n", string(data)))
					c.Writer.Flush()
				}
			} else {
				tokenCount++
				ticker.Reset(15 * time.Second)
				responseBuilder.WriteString(token)
				if useSSE {
					chunk := map[string]interface{}{
						"id":     chatID,
						"object": "chat.completion.chunk",
						"choices": []map[string]interface{}{
							{"index": 0, "delta": map[string]interface{}{"role": "assistant", "content": token}, "finish_reason": nil},
						},
					}
					data, _ := json.Marshal(chunk)
					c.Writer.WriteString(fmt.Sprintf("data: %s\n\n", string(data)))
					c.Writer.Flush()
				}
			}
		case <-ticker.C:
			if useSSE {
				// No token in 15s — punch through Cloudflare's idle timer
				c.Writer.WriteString(": keep-alive\n\n")
				c.Writer.Flush()
			}
		case <-c.Request.Context().Done():
			if useSSE {
				streamDone = true
			}
			// non-SSE: ignore request context cancellation — keep collecting tokens
		}
	}

	// Post-stream: async jobs on the full assembled response
	responseText := responseBuilder.String()
	if isCanvasMode {
		responseText, _ = s.Agent.SovEngine.AuditCanvasOutput(responseText)
	} else {
		responseText, _ = s.Agent.SovEngine.AuditOutput(responseText)
	}

	// Non-streaming response — return buffered result as plain JSON now that we have it.
	if !useSSE {
		c.JSON(http.StatusOK, gin.H{
			"id":     chatID,
			"object": "chat.completion",
			"model":  modelName,
			"choices": []gin.H{{
				"index":         0,
				"message":       gin.H{"role": "assistant", "content": responseText},
				"finish_reason": "stop",
			}},
			"usage": gin.H{"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0},
		})
		return
	}
	// Store in semantic cache — async, never blocks. Skips canvas/code outputs
	// (too context-specific to be reusable) and action-dispatched responses.
	if s.ResponseCache != nil && lastMsg != "" && !isCanvasMode && dispatch == nil && req.SpaceID == "" {
		s.ResponseCache.Put(lastMsg, responseText)
	}

	// SCAI Critique-Revision loop — fires in background to preserve streaming latency.
	// If a constitutional violation is detected, a scai_correction WS event is broadcast
	// so the UI can patch the last assistant message in-place with the revised text.
	// This also generates an RFAL DPO pair for every violation (learning signal).
	// Zero impact on the happy path (CLEAR critique → goroutine exits silently).
	tenantID := tenantauth.TenantID(c.Request.Context())
	go func(query, response, sid, tid string) {
		ctx, cancel := context.WithTimeout(context.Background(), 30*time.Second)
		defer cancel()
		corrected, violated := s.Agent.SovEngine.SelfAlign(ctx, query, response)
		if !violated {
			// Clean response — write as ProvenanceSolved for CBR future use.
			// This teaches Oricli what a good answer looks like for this class of problem.
			if s.MemoryBank != nil && s.MemoryBank.IsEnabled() && len(query) > 20 && len(response) > 50 {
				words := strings.Fields(query)
				if len(words) > 5 { words = words[:5] }
				go s.MemoryBank.Write(service.MemoryFragment{
					Content:    fmt.Sprintf("Q: %s\n\nA: %s", query, truncateStr(response, 600)),
					Source:     "solved",
					Topic:      strings.Join(words, " "),
					Importance: 0.75,
					Provenance: service.ProvenanceSolved,
				})
			}
			return
		}
		s.Agent.SovEngine.WSHub.BroadcastEvent("scai_correction", map[string]interface{}{
			"session_id":       sid,
			"corrected":        corrected,
			"original_preview": response[:min(120, len(response))],
		})
		// Persist revision to reflection_log for operator audit and DPO learning.
		if s.MemoryBank != nil && s.MemoryBank.IsEnabled() {
			s.MemoryBank.SaveSCAIRevision(sid, tid, query, response, corrected, "SCAI constitutional violation")
		}
	}(lastMsg, responseText, sessionID, tenantID)

	// ExploiterLeague — 3 async specialists audit every response post-stream (AlphaStar League).
	// FactChecker, LogicAuditor, ClarityProbe each fire a ≤128-token LLM probe.
	// Medium/High findings land on the LeagueBlackboard for DreamDaemon consolidation.
	if !isStudioContext {
		cognition.RunLeagueWithConsensus(s.Agent.GenService, lastMsg, responseText)
	}

	if s.Agent.SovEngine.Voice != nil {
		go s.Agent.SovEngine.Voice.Synthesize(responseText, s.Agent.SovEngine.Resonance.Current.ERI, 0.5, s.Agent.SovEngine.Resonance.Current.MusicalKey)
	}

	go s.Orchestrator.Execute("record_event", map[string]interface{}{
		"type":        "chat_interaction",
		"description": fmt.Sprintf("User: %s | Assistant: %s", lastMsg, responseText),
		"metadata": map[string]interface{}{
			"model": req.Model,
			"eri":   s.Agent.SovEngine.Resonance.Current.ERI,
			"key":   s.Agent.SovEngine.Resonance.Current.MusicalKey,
		},
	}, 5*time.Second)

	// Conversation write-back: persist this exchange to PocketBase long-term memory.
	// Only when both sides have meaningful content. Fires in background, never blocks.
	// Skip for studio context — DSL workflow responses must not pollute general RAG.
	if !isStudioContext && s.MemoryBank != nil && s.MemoryBank.IsEnabled() &&
		len(lastMsg) > 50 && len(responseText) > 50 {
		go func() {
			// Strip HTML tags before storing — prevents <span class="ori-kw"> and similar
			// UI syntax-highlighted content from polluting RAG recall.
			cleanMsg := stripHTML(lastMsg)
			cleanResp := stripHTML(responseText)

			// Extract a short topic from the user's message (first 5 words)
			words := strings.Fields(cleanMsg)
			if len(words) > 5 {
				words = words[:5]
			}
			topic := strings.Join(words, " ")

			// Combine user + assistant turn, cap response at 400 chars
			resp := cleanResp
			if len(resp) > 400 {
				resp = resp[:400] + "…"
			}
			combined := fmt.Sprintf("User: %s\n\nOricli: %s", cleanMsg, resp)

			s.MemoryBank.Write(service.MemoryFragment{
				Content:      combined,
				Source:       "conversation",
				Topic:        topic,
				Importance:   0.4,
				Provenance:   service.ProvenanceConversation,
				Volatility:   service.InferVolatility(topic),
				LineageDepth: 0,
			})
		}()
	}

	// Signal detection: scan user message for learning signals (corrections, explicit teaches).
	// Fires async — never blocks the response. Sub-millisecond on cache hit.
	// Skip for studio context — DSL prompts would be misclassified as behavioral teaches.
	if !isStudioContext && s.SignalProcessor != nil && len(lastMsg) > 10 {
		go func(msg string) {
			sig := s.SignalProcessor.Detect(msg)
			s.SignalProcessor.Process(sig)
		}(lastMsg)
	}
}

func (s *ServerV2) handleTelegramWebhook(c *gin.Context) {
	var update struct {
		UpdateID int `json:"update_id"`
		Message  *struct {
			Chat struct { ID int64 `json:"id"` } `json:"chat"`
			Text string `json:"text"`
			From struct { Username string `json:"username"` } `json:"from"`
		} `json:"message"`
	}

	if err := c.ShouldBindJSON(&update); err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"error": err.Error()})
		return
	}

	if update.Message == nil || update.Message.Text == "" {
		c.JSON(http.StatusOK, gin.H{"status": "ignored"})
		return
	}

	if update.Message.Chat.ID != s.Agent.SovEngine.Telegram.ChatID {
		c.JSON(http.StatusUnauthorized, gin.H{"error": "unauthorized chat id"})
		return
	}

	_, err := s.Agent.SovEngine.ProcessInference(c.Request.Context(), update.Message.Text)
	if err != nil {
		s.Agent.SovEngine.Telegram.SendMessage(update.Message.Chat.ID, "Cognitive error. Retry.", "HTML")
		return
	}

	responseText := "I am here. " + update.Message.Text
	responseText, _ = s.Agent.SovEngine.SelfAlign(c.Request.Context(), update.Message.Text, responseText)
	responseText, _ = s.Agent.SovEngine.AuditOutput(responseText)

	// Trigger Voice Synthesis (Async)
	if s.Agent.SovEngine.Voice != nil {
		go s.Agent.SovEngine.Voice.Synthesize(responseText, s.Agent.SovEngine.Resonance.Current.ERI, 0.5, s.Agent.SovEngine.Resonance.Current.MusicalKey)
	}

	s.Agent.SovEngine.Telegram.SendMessage(update.Message.Chat.ID, responseText, "HTML")
	c.JSON(http.StatusOK, gin.H{"status": "success"})
}

// handleImageGenerations is an OpenAI-compatible POST /v1/images/generations endpoint.
// It routes to the RunPod A1111 image gen pod (lazy spin-up on first request).
func (s *ServerV2) handleImageGenerations(c *gin.Context) {
	var req service.ImageGenRequest
	if err := c.ShouldBindJSON(&req); err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"error": err.Error()})
		return
	}
	if req.Prompt == "" {
		c.JSON(http.StatusBadRequest, gin.H{"error": "prompt is required"})
		return
	}

	if s.ImageGen == nil || !s.ImageGen.IsEnabled() {
		c.JSON(http.StatusServiceUnavailable, gin.H{
			"error":   "image generation is not enabled",
			"hint":    "Set RUNPOD_IMAGEGEN_ENABLED=true in .env and restart",
			"warming": false,
		})
		return
	}

	if s.ImageGen.WarmingUp() {
		c.JSON(http.StatusAccepted, gin.H{
			"error":   "image engine is warming up, retry in ~60s",
			"warming": true,
			"status":  s.ImageGen.Status(),
		})
		return
	}

	b64, err := s.ImageGen.GenerateImage(c.Request.Context(), req)
	if err != nil {
		c.JSON(http.StatusInternalServerError, gin.H{"error": err.Error(), "warming": s.ImageGen.WarmingUp()})
		return
	}

	c.JSON(http.StatusOK, service.ImageGenResponse{
		Created: time.Now().Unix(),
		Data: []struct {
			B64JSON string `json:"b64_json"`
		}{{B64JSON: b64}},
	})
}

func (s *ServerV2) handleSwarmRun(c *gin.Context) {
	var body map[string]interface{}
	if err := c.ShouldBindJSON(&body); err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"error": err.Error()})
		return
	}
	op, _ := body["operation"].(string)
	params, _ := body["params"].(map[string]interface{})
	res, err := s.Orchestrator.Execute(op, params, 300*time.Second)
	if err != nil {
		c.JSON(http.StatusInternalServerError, gin.H{"error": err.Error()})
		return
	}
	c.JSON(http.StatusOK, gin.H{"success": true, "result": res})
}

func (s *ServerV2) handleIngest(c *gin.Context) {
	file, err := c.FormFile("file")
	if err == nil {
		f, _ := file.Open()
		data, _ := io.ReadAll(f)
		params := map[string]interface{}{"file_data": data, "file_name": file.Filename}
		res, err := s.Orchestrator.Execute("ingest_file", params, 60*time.Second)
		if err != nil { c.JSON(http.StatusInternalServerError, gin.H{"error": err.Error()}); return }
		c.JSON(http.StatusOK, res)
	} else {
		var req map[string]interface{}
		c.ShouldBindJSON(&req)
		res, err := s.Orchestrator.Execute("ingest_text", req, 60*time.Second)
		if err != nil { c.JSON(http.StatusInternalServerError, gin.H{"error": err.Error()}); return }
		c.JSON(http.StatusOK, res)
	}
}

func (s *ServerV2) handleIngestWeb(c *gin.Context) {
	var req map[string]interface{}
	c.ShouldBindJSON(&req)

	// Scan any provided content/url payload for indirect injection before ingesting
	if content, ok := req["content"].(string); ok && content != "" {
		scanRes := s.Agent.SovEngine.RagGuard.ScanScrapedContent(content)
		if scanRes.Flagged {
			log.Printf("[Safety:RAGGuard] Flagged web ingest content: %v", scanRes.Detections)
			req["content"] = scanRes.Sanitized
		}
	}

	res, err := s.Orchestrator.Execute("crawl_and_ingest", req, 300*time.Second)
	if err != nil {
		c.JSON(http.StatusInternalServerError, gin.H{"error": err.Error()})
		return
	}
	c.JSON(http.StatusOK, res)
}

func (s *ServerV2) handleGetTraces(c *gin.Context) {
	limitStr := c.DefaultQuery("limit", "50")
	limit, _ := strconv.Atoi(limitStr)
	if limit < 1 || limit > 500 {
		limit = 50
	}
	traces := s.Traces.ListRecent(limit)
	c.JSON(http.StatusOK, gin.H{"success": true, "traces": traces, "count": len(traces)})
}

func (s *ServerV2) handleLogLines(c *gin.Context) {
	nStr := c.DefaultQuery("n", "200")
	n, _ := strconv.Atoi(nStr)
	if n < 1 || n > 2000 {
		n = 200
	}
	logPath := "/home/mike/Mavaia/go_backbone.log"
	f, err := os.Open(logPath)
	if err != nil {
		c.JSON(http.StatusOK, gin.H{"lines": []string{}, "error": err.Error()})
		return
	}
	defer f.Close()

	var lines []string
	scanner := bufio.NewScanner(f)
	for scanner.Scan() {
		lines = append(lines, scanner.Text())
	}
	// Return last n lines
	if len(lines) > n {
		lines = lines[len(lines)-n:]
	}
	c.JSON(http.StatusOK, gin.H{"lines": lines, "total": len(lines)})
}

func (s *ServerV2) Start() error {
	addr := fmt.Sprintf(":%d", s.Port)
	log.Printf("[API] Gateway starting on %s", addr)
	return s.Router.Run(addr)
}

// handleSovereignAuth handles /admin <key>, /exec <key>, and /auth off.
// The raw key is scrubbed from all logs immediately.
func (s *ServerV2) handleSovereignAuth(c *gin.Context, rawMsg, sessionKey string) {
	scrubbed := sovereign.ScrubKey(rawMsg)
	log.Printf("[SovereignAuth] auth attempt from %s: %s", sessionKey, scrubbed)

	trimmed := strings.TrimSpace(rawMsg)
	lower := strings.ToLower(trimmed)

	chatID := fmt.Sprintf("chatcmpl-%d", time.Now().Unix())
	respond := func(msg string) {
		c.JSON(http.StatusOK, gin.H{
			"id": chatID, "object": "chat.completion",
			"choices": []gin.H{{"index": 0, "message": gin.H{"role": "assistant", "content": msg}, "finish_reason": "stop"}},
		})
	}

	if lower == "/auth off" {
		s.SovAuth.InvalidateSession(sessionKey)
		respond("🔒 Sovereign session ended.")
		return
	}

	// Extract key — everything after the command word (/admin or /exec)
	parts := strings.SplitN(trimmed, " ", 2)
	if len(parts) < 2 || strings.TrimSpace(parts[1]) == "" {
		respond("Usage: `/admin <key>` or `/exec <key>` — `/auth off` to end session.")
		return
	}
	rawKey := strings.TrimSpace(parts[1])

	level, err := s.SovAuth.Authenticate(rawKey, sessionKey)
	if err != nil {
		log.Printf("[SovereignAuth] failed auth from %s: %v", sessionKey, err)
		respond(fmt.Sprintf("❌ Authentication failed: %s", err.Error()))
		return
	}

	levelName := "ADMIN"
	capabilities := "elevated chat · full technical detail · no response softening"
	if level >= sovereign.LevelExec {
		levelName = "EXEC"
		capabilities = "elevated chat · full technical detail · system commands (!status, !logs, !df, !modules…)"
	}

	respond(fmt.Sprintf(
		"✅ **Sovereign session established — Level %d (%s)**\n\nCapabilities unlocked: %s\n\nSession expires in 1 hour of inactivity. Type `/auth off` to end.",
		level, levelName, capabilities,
	))
}

// --- Admin: Tenant Management ---

func (s *ServerV2) handleAdminCreateTenant(c *gin.Context) {
	var req struct {
		Name string `json:"name" binding:"required"`
	}
	if err := c.ShouldBindJSON(&req); err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"error": err.Error()})
		return
	}
	tenant, err := s.store.CreateTenant(c.Request.Context(), req.Name)
	if err != nil {
		c.JSON(http.StatusInternalServerError, gin.H{"error": err.Error()})
		return
	}
	c.JSON(http.StatusCreated, tenant)
}

func (s *ServerV2) handleAdminListTenants(c *gin.Context) {
	tenants, err := s.store.ListTenants(c.Request.Context(), 100)
	if err != nil {
		c.JSON(http.StatusInternalServerError, gin.H{"error": err.Error()})
		return
	}
	c.JSON(http.StatusOK, gin.H{"tenants": tenants})
}

func (s *ServerV2) handleAdminCreateAPIKey(c *gin.Context) {
	tenantID := c.Param("id")
	var req struct {
		Scopes []string `json:"scopes"` // e.g. ["chat", "read", "write"]
	}
	if err := c.ShouldBindJSON(&req); err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"error": err.Error()})
		return
	}
	if len(req.Scopes) == 0 {
		req.Scopes = []string{"chat", "read", "write"}
	}
	raw, rec, err := s.auth.GenerateAPIKey(c.Request.Context(), tenantID, req.Scopes, nil)
	if err != nil {
		c.JSON(http.StatusInternalServerError, gin.H{"error": err.Error()})
		return
	}
	// Return the raw key ONCE — it cannot be retrieved again.
	c.JSON(http.StatusCreated, gin.H{
		"key":       raw,
		"key_id":    rec.ID,
		"tenant_id": rec.TenantID,
		"scopes":    rec.Scopes,
		"warning":   "Store this key securely — it will not be shown again",
	})
}

// --- DAG Goal Handlers ---

func (s *ServerV2) handleListGoals(c *gin.Context) {
	if s.GoalService == nil {
		c.JSON(http.StatusServiceUnavailable, gin.H{"error": "goal service not available"})
		return
	}
	status := c.Query("status") // optional filter: pending | active | completed | failed
	goals, err := s.GoalService.ListObjectives(status)
	if err != nil {
		c.JSON(http.StatusInternalServerError, gin.H{"error": err.Error()})
		return
	}
	c.JSON(http.StatusOK, gin.H{"goals": goals, "count": len(goals)})
}

func (s *ServerV2) handleGetGoal(c *gin.Context) {
	if s.GoalService == nil {
		c.JSON(http.StatusServiceUnavailable, gin.H{"error": "goal service not available"})
		return
	}
	id := c.Param("id")
	obj, err := s.GoalService.GetObjective(id)
	if err != nil {
		c.JSON(http.StatusInternalServerError, gin.H{"error": err.Error()})
		return
	}
	if obj == nil {
		c.JSON(http.StatusNotFound, gin.H{"error": "goal not found"})
		return
	}
	c.JSON(http.StatusOK, obj)
}

func (s *ServerV2) handleCreateGoal(c *gin.Context) {
	if s.GoalService == nil {
		c.JSON(http.StatusServiceUnavailable, gin.H{"error": "goal service not available"})
		return
	}
	var body struct {
		Goal      string                 `json:"goal"`
		Priority  int                    `json:"priority"`
		DependsOn []string               `json:"depends_on"`
		Metadata  map[string]interface{} `json:"metadata"`
	}
	if err := c.ShouldBindJSON(&body); err != nil || body.Goal == "" {
		c.JSON(http.StatusBadRequest, gin.H{"error": "goal field required"})
		return
	}
	if body.Priority == 0 {
		body.Priority = 5 // default priority
	}
	meta := body.Metadata
	if meta == nil {
		meta = map[string]interface{}{}
	}
	if len(body.DependsOn) > 0 {
		meta["depends_on_raw"] = body.DependsOn
	}
	id, err := s.GoalService.AddObjectiveWithDeps(body.Goal, body.Priority, meta, body.DependsOn)
	if err != nil {
		c.JSON(http.StatusInternalServerError, gin.H{"error": err.Error()})
		return
	}
	c.JSON(http.StatusCreated, gin.H{"id": id, "goal": body.Goal})
}

func (s *ServerV2) handleUpdateGoal(c *gin.Context) {
	if s.GoalService == nil {
		c.JSON(http.StatusServiceUnavailable, gin.H{"error": "goal service not available"})
		return
	}
	id := c.Param("id")
	var updates map[string]interface{}
	if err := c.ShouldBindJSON(&updates); err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"error": err.Error()})
		return
	}
	found, err := s.GoalService.UpdateObjective(id, updates)
	if err != nil {
		c.JSON(http.StatusInternalServerError, gin.H{"error": err.Error()})
		return
	}
	if !found {
		c.JSON(http.StatusNotFound, gin.H{"error": "goal not found"})
		return
	}
	c.JSON(http.StatusOK, gin.H{"updated": id})
}

func (s *ServerV2) handleDeleteGoal(c *gin.Context) {
	if s.GoalService == nil {
		c.JSON(http.StatusServiceUnavailable, gin.H{"error": "goal service not available"})
		return
	}
	id := c.Param("id")
	found, err := s.GoalService.DeleteObjective(id)
	if err != nil {
		c.JSON(http.StatusInternalServerError, gin.H{"error": err.Error()})
		return
	}
	if !found {
		c.JSON(http.StatusNotFound, gin.H{"error": "goal not found"})
		return
	}
	c.JSON(http.StatusOK, gin.H{"deleted": id})
}

// handleListMemories proxies GET /v1/memories to PocketBase.
// Query params: source, author, topic, page (default 1), perPage (default 20, max 100).
func (s *ServerV2) handleListMemories(c *gin.Context) {
if s.MemoryBank == nil || !s.MemoryBank.IsEnabled() {
c.JSON(http.StatusServiceUnavailable, gin.H{"error": "memory bank not available"})
return
}

ctx := c.Request.Context()
source := c.DefaultQuery("source", "")
author := c.DefaultQuery("author", "")
topic := c.DefaultQuery("topic", "")
page := 1
perPage := 20
if v := c.Query("page"); v != "" {
if n, err := strconv.Atoi(v); err == nil && n > 0 {
page = n
}
}
if v := c.Query("perPage"); v != "" {
if n, err := strconv.Atoi(v); err == nil && n > 0 && n <= 100 {
perPage = n
}
}

items, total, err := s.MemoryBank.ListMemories(ctx, source, author, topic, page, perPage)
if err != nil {
c.JSON(http.StatusInternalServerError, gin.H{"error": err.Error()})
return
}
c.JSON(http.StatusOK, gin.H{
"items":   items,
"total":   total,
"page":    page,
"perPage": perPage,
})
}

// handleListKnowledge proxies GET /v1/memories/knowledge to PocketBase.
// Query params: topic, author, page (default 1), perPage (default 20, max 100).
func (s *ServerV2) handleListKnowledge(c *gin.Context) {
if s.MemoryBank == nil || !s.MemoryBank.IsEnabled() {
c.JSON(http.StatusServiceUnavailable, gin.H{"error": "memory bank not available"})
return
}

ctx := c.Request.Context()
topic := c.DefaultQuery("topic", "")
author := c.DefaultQuery("author", "")
page := 1
perPage := 20
if v := c.Query("page"); v != "" {
if n, err := strconv.Atoi(v); err == nil && n > 0 {
page = n
}
}
if v := c.Query("perPage"); v != "" {
if n, err := strconv.Atoi(v); err == nil && n > 0 && n <= 100 {
perPage = n
}
}

items, total, err := s.MemoryBank.ListKnowledgeFragments(ctx, topic, author, page, perPage)
if err != nil {
c.JSON(http.StatusInternalServerError, gin.H{"error": err.Error()})
return
}
c.JSON(http.StatusOK, gin.H{
"items":   items,
"total":   total,
"page":    page,
"perPage": perPage,
})
}

// handleDaemonHealth returns live status of all autonomous background daemons.
// Used by the Goals UI mission control panel to show what Oricli is currently doing.
func (s *ServerV2) handleDaemonHealth(c *gin.Context) {
type DaemonStatus struct {
Name      string `json:"name"`
Status    string `json:"status"`
Detail    string `json:"detail,omitempty"`
}

var daemons []DaemonStatus

// CuriosityDaemon
if cd := s.ActionRouter.CuriosityDaemon; cd != nil {
idle := cd.IdleSince()
qDepth := cd.SeedQueueDepth()
status := "idle"
detail := fmt.Sprintf("idle for %s | %d seeds queued", idle.Round(time.Second), qDepth)
if idle < 30*time.Second {
status = "active"
}
daemons = append(daemons, DaemonStatus{Name: "CuriosityDaemon", Status: status, Detail: detail})
}

// GoalExecutor
if s.GoalExecutor != nil {
goals, _ := s.GoalService.ListObjectives("active")
status := "idle"
detail := "no active objectives"
if len(goals) > 0 {
status = "active"
detail = fmt.Sprintf("executing: %q", goals[0].Goal)
}
daemons = append(daemons, DaemonStatus{Name: "GoalExecutor", Status: status, Detail: detail})
}

// ReformDaemon — always running (Reform is on SovEngine)
daemons = append(daemons, DaemonStatus{Name: "ReformDaemon", Status: "running", Detail: "self-modification audit loop"})

// DreamDaemon — always running
daemons = append(daemons, DaemonStatus{Name: "DreamDaemon", Status: "running", Detail: "memory consolidation loop"})

c.JSON(http.StatusOK, gin.H{"daemons": daemons})
}

// handleDocumentUpload accepts a multipart file upload and ingests it into MemoryBank.
func (s *ServerV2) handleDocumentUpload(c *gin.Context) {
	if err := c.Request.ParseMultipartForm(32 << 20); err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"error": "failed to parse form: " + err.Error()})
		return
	}

	file, header, err := c.Request.FormFile("file")
	if err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"error": "missing 'file' field"})
		return
	}
	defer file.Close()

	filename := header.Filename
	ext := strings.ToLower(filepath.Ext(filename))
	allowed := map[string]string{
		".txt": "text/plain",
		".md":  "text/markdown",
		".csv": "text/csv",
		".pdf": "application/pdf",
	}
	mimeType, ok := allowed[ext]
	if !ok {
		c.JSON(http.StatusBadRequest, gin.H{"error": "unsupported file type: " + ext})
		return
	}

	data, err := io.ReadAll(file)
	if err != nil {
		c.JSON(http.StatusInternalServerError, gin.H{"error": "failed to read file"})
		return
	}

	if s.DocumentIngestor == nil {
		c.JSON(http.StatusServiceUnavailable, gin.H{"error": "document ingestor not available"})
		return
	}

	n, err := s.DocumentIngestor.Ingest(c.Request.Context(), filename, data, mimeType)
	if err != nil {
		c.JSON(http.StatusUnprocessableEntity, gin.H{"error": err.Error()})
		return
	}

	docs := s.DocumentIngestor.ListDocs()
	var id string
	for _, d := range docs {
		if d.Filename == filename {
			id = d.ID
		}
	}

	c.JSON(http.StatusOK, gin.H{
		"filename": filename,
		"chunks":   n,
		"id":       id,
	})
}

// handleListDocuments returns all previously ingested documents.
func (s *ServerV2) handleListDocuments(c *gin.Context) {
	if s.DocumentIngestor == nil {
		c.JSON(http.StatusOK, gin.H{"documents": []interface{}{}})
		return
	}
	c.JSON(http.StatusOK, gin.H{"documents": s.DocumentIngestor.ListDocs()})
}

// ─── Reaction Feedback ────────────────────────────────────────────────────────

// handleReactionFeedback stores a user's emoji reaction to an assistant message
// as a MemoryFragment so it influences future RAG recall and sentiment weighting.
func (s *ServerV2) handleReactionFeedback(c *gin.Context) {
var req struct {
MessageID   string  `json:"message_id"`
Reaction    string  `json:"reaction"`    // e.g. "thumbs_up", "heart", "fire"
IsPositive  bool    `json:"is_positive"`
MsgPreview  string  `json:"message_preview"` // first 200 chars of assistant message
SessionID   string  `json:"session_id"`
}
if err := c.ShouldBindJSON(&req); err != nil || req.Reaction == "" {
c.JSON(http.StatusBadRequest, gin.H{"error": "reaction and message_id required"})
return
}

feedbackType := "positive"
importance := 0.8
if !req.IsPositive {
feedbackType = "negative"
importance = 0.9 // negative feedback is a sharper learning signal
}

content := fmt.Sprintf(
"User reacted with %s (%s) to message: %q",
req.Reaction, feedbackType, req.MsgPreview,
)

keywords := extractFeedbackKeywords(req.MsgPreview)
topic := "feedback:" + feedbackType
if len(keywords) > 0 {
topic = "feedback:" + keywords[0]
}

frag := service.MemoryFragment{
ID:         "fb-" + req.MessageID,
Content:    content,
Source:     "feedback",
Topic:      topic,
SessionID:  req.SessionID,
Importance: importance,
Provenance: service.ProvenanceUserStated, // user explicitly rated — highest trust
Volatility: service.VolatilityStable,
}

// 📌 Gold bookmark: pin reaction elevates the Q→A pair to ProvenanceGold tier.
	// Gold memories are never recycled, get 1.6x RAG weight, DreamDaemon consolidates them first.
	isPin := req.Reaction == "📌" || req.Reaction == "pin" || req.Reaction == "bookmark"
	if isPin && req.IsPositive && s.MemoryBank != nil && s.MemoryBank.IsEnabled() && len(req.MsgPreview) > 20 {
		goldFrag := service.MemoryFragment{
			ID:         "gold-" + req.MessageID,
			Content:    "GOLD: " + req.MsgPreview,
			Source:     "user_bookmark",
			Topic:      "gold:" + topic,
			SessionID:  req.SessionID,
			Importance: 1.0,
			Provenance: service.ProvenanceGold,
			Volatility: service.VolatilityStable,
		}
		s.MemoryBank.Write(goldFrag)
	}

	if s.MemoryBank != nil {
	s.MemoryBank.Write(frag)
}

	// Contrastive pair: store ACCEPTED/REJECTED alongside the standard feedback fragment.
	// This gives RAG a paired view of what worked and what didn't on each topic.
	if s.SignalProcessor != nil {
		go s.SignalProcessor.ProcessContrastivePair(req.IsPositive, topic, req.MsgPreview)
	}

c.JSON(http.StatusOK, gin.H{
"ok":          true,
"feedback":    feedbackType,
"reaction":    req.Reaction,
"importance":  importance,
"keywords":    keywords,
})
}

// handleGetSovereignIdentity returns the active sovereign .ori profile as JSON.
func (s *ServerV2) handleGetSovereignIdentity(c *gin.Context) {
	p := s.Agent.SovEngine.ActiveProfile
	if p == nil {
		c.JSON(http.StatusOK, gin.H{
			"name": "oricli", "description": "", "archetype": "friend",
			"sass_factor": 0.65, "energy": "moderate",
			"instructions": []string{}, "rules": []string{},
		})
		return
	}
	c.JSON(http.StatusOK, gin.H{
		"name":         p.Name,
		"description":  p.Description,
		"archetype":    p.Archetype,
		"sass_factor":  p.SassFactor,
		"energy":       p.Energy,
		"instructions": p.Instructions,
		"rules":        p.Rules,
	})
}

// handlePutSovereignIdentity writes an updated .ori profile to disk,
// reloads the registry, and hot-swaps the active profile without a restart.
func (s *ServerV2) handlePutSovereignIdentity(c *gin.Context) {
	var req struct {
		Name         string   `json:"name"`
		Description  string   `json:"description"`
		Archetype    string   `json:"archetype"`
		SassFactor   float64  `json:"sass_factor"`
		Energy       string   `json:"energy"`
		Instructions []string `json:"instructions"`
		Rules        []string `json:"rules"`
	}
	if err := c.ShouldBindJSON(&req); err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"error": err.Error()})
		return
	}
	if req.Name == "" {
		req.Name = "oricli"
	}

	// Build .ori file content
	var b strings.Builder
	b.WriteString("# Sovereign Identity Profile — auto-saved from UI\n\n")
	b.WriteString("@profile_name: " + req.Name + "\n")
	b.WriteString("@description: " + req.Description + "\n")
	b.WriteString("@archetype: " + req.Archetype + "\n")
	b.WriteString(fmt.Sprintf("@sass_factor: %.2f\n", req.SassFactor))
	b.WriteString("@energy: " + req.Energy + "\n\n")

	if len(req.Instructions) > 0 {
		b.WriteString("<instructions>\n")
		for _, line := range req.Instructions {
			if strings.TrimSpace(line) != "" {
				b.WriteString("- " + strings.TrimSpace(line) + "\n")
			}
		}
		b.WriteString("</instructions>\n\n")
	}

	if len(req.Rules) > 0 {
		b.WriteString("<rules>\n")
		for _, line := range req.Rules {
			if strings.TrimSpace(line) != "" {
				b.WriteString("- " + strings.TrimSpace(line) + "\n")
			}
		}
		b.WriteString("</rules>\n")
	}

	oriPath := filepath.Join(s.Agent.SovEngine.Profiles.Dir, req.Name+".ori")
	if err := os.WriteFile(oriPath, []byte(b.String()), 0644); err != nil {
		c.JSON(http.StatusInternalServerError, gin.H{"error": "failed to write profile: " + err.Error()})
		return
	}

	// Hot-reload registry and swap active profile — no restart needed
	s.Agent.SovEngine.Profiles.Reload()
	if p, ok := s.Agent.SovEngine.Profiles.GetProfile(req.Name); ok {
		s.Agent.SovEngine.ActiveProfile = p
		log.Printf("[API] Sovereign identity updated and hot-swapped: %s", req.Name)
	}

	c.JSON(http.StatusOK, gin.H{"ok": true, "saved": req.Name + ".ori"})
}

// reHTML strips HTML tags and decodes common entities.
// Used to sanitize content before writing to MemoryBank so highlighted
// UI output (e.g. <span class="ori-kw">workflow</span>) never poisons RAG.
var reHTMLTag = regexp.MustCompile(`<[^>]+>`)

func stripHTML(s string) string {
	s = reHTMLTag.ReplaceAllString(s, "")
	s = strings.ReplaceAll(s, "&amp;", "&")
	s = strings.ReplaceAll(s, "&lt;", "<")
	s = strings.ReplaceAll(s, "&gt;", ">")
	s = strings.ReplaceAll(s, "&quot;", `"`)
	s = strings.ReplaceAll(s, "&#39;", "'")
	return s
}

// extractFeedbackKeywords pulls the top-5 meaningful words from a message preview.
func extractFeedbackKeywords(text string) []string {
stopWords := map[string]bool{
"this": true, "that": true, "with": true, "from": true, "have": true,
"about": true, "there": true, "their": true, "which": true, "while": true,
"where": true, "what": true, "when": true, "your": true, "into": true,
"over": true, "under": true, "through": true, "many": true, "some": true,
"really": true, "just": true, "like": true, "them": true, "they": true,
"you": true, "here": true, "the": true, "and": true, "for": true,
"are": true, "was": true, "were": true, "been": true, "being": true,
}

words := strings.Fields(strings.ToLower(text))
counts := map[string]int{}
for _, w := range words {
// strip punctuation
clean := strings.Trim(w, `.,!?;:"'()[]`)
if len(clean) > 3 && !stopWords[clean] {
counts[clean]++
}
}

type wc struct{ w string; c int }
var ranked []wc
for w, c := range counts {
ranked = append(ranked, wc{w, c})
}
sort.Slice(ranked, func(i, j int) bool { return ranked[i].c > ranked[j].c })

out := make([]string, 0, 5)
for i, r := range ranked {
if i >= 5 { break }
out = append(out, r.w)
}
return out
}

// ─── MemoryBank adapter (cognition.MemoryQuerier) ─────────────────────────────
// Bridges *service.MemoryBank to the cognition.MemoryQuerier interface without
// creating an import cycle. Converts service.MemoryFragment → cognition.MemFrag.
// Certainty is derived from provenance tier per AI-Supervisor uncertainty model
// (arXiv:2603.24402): U=0 (verified, Certainty≥0.80) vs U=1 (unverified, <0.80).

type memoryBankAdapter struct {
mb *service.MemoryBank
}

// provenanceCertainty maps service provenance tiers to AI-Supervisor factual confidence floors.
// Gold/Solved/UserStated are empirically verified (U=0); Synthetic tiers are unverified (U=1).
// This sets the Belief.Factual floor before access-bonus reinforcement is applied.
func provenanceCertainty(prov service.Provenance) float64 {
	switch prov {
	case service.ProvenanceGold:
		return 0.95
	case service.ProvenanceSolved, service.ProvenanceUserStated:
		return 0.90
	case service.ProvenanceWebVerified:
		return 0.85
	case service.ProvenanceSeen: // image-derived — reliable but vision models hallucinate details
		return 0.70
	case service.ProvenanceContrastive:
		return 0.75
	case service.ProvenanceConversation:
		return 0.65
	case service.ProvenanceSyntheticL1:
		return 0.55
	default: // SyntheticL2+, unknown
		return 0.45
	}
}

func (a *memoryBankAdapter) QuerySimilarWeighted(ctx context.Context, query string, topN int, weights cognition.BeliefWeights) ([]cognition.MemFrag, error) {
	// Oversample 3× from PB so the re-ranker has a meaningful candidate pool.
	// PB pre-sorts by cosine+provenance; we then re-rank by the caller's weight vector.
	oversample := topN * 3
	if oversample < 9 {
		oversample = 9
	}
	frags, err := a.mb.QuerySimilar(ctx, query, oversample)
	if err != nil {
		return nil, err
	}

	// Build MemFrag slice with full Belief axes populated.
	candidates := make([]cognition.MemFrag, len(frags))
	for i, f := range frags {
		mf := cognition.MemFrag{
			ID:            f.ID,
			Content:       f.Content,
			Source:        f.Source,
			Topic:         f.Topic,
			Importance:    f.Importance,
			CausalScore:   f.CausalScore,
			AccessCount:   f.AccessCount,
			Volatility:    string(f.Volatility),
			CreatedAt:     f.CreatedAt,
			SemanticScore: f.SemanticScore,
			Belief:        cognition.Belief{Factual: provenanceCertainty(f.Provenance)},
		}
		mf.Belief = cognition.ComputeBelief(mf)
		mf.DynamicCertainty = cognition.ComputeDynamicCertainty(mf)
		candidates[i] = mf
	}

	// Re-rank by caller's multi-objective weight vector.
	nw := weights.Normalize()
	type scored struct {
		frag  cognition.MemFrag
		score float64
	}
	ranked := make([]scored, len(candidates))
	for i, c := range candidates {
		ranked[i] = scored{frag: c, score: nw.WeightedScore(c)}
	}
	// Insertion sort — candidate pool is small (≤27), no need for stdlib sort import.
	for i := 1; i < len(ranked); i++ {
		for j := i; j > 0 && ranked[j].score > ranked[j-1].score; j-- {
			ranked[j], ranked[j-1] = ranked[j-1], ranked[j]
		}
	}

	// Trim to topN.
	if topN > len(ranked) {
		topN = len(ranked)
	}
	out := make([]cognition.MemFrag, topN)
	for i := range out {
		out[i] = ranked[i].frag
	}

	// ── Retrieval audit log (benchmark observability) ─────────────────────────
	// One DEBUG line per retrieval: weights label + top-3 frag scores.
	// Allows per-mode retrieval quality analysis without extra infrastructure.
	if topN > 0 {
		label := beliefWeightsLabel(weights)
		n := 3
		if n > topN {
			n = topN
		}
		var sb strings.Builder
		for i := 0; i < n; i++ {
			f := out[i]
			fmt.Fprintf(&sb, "(F:%.2f C:%.2f R:%.2f s:%.2f) ",
				f.Belief.Factual, f.Belief.Causal, f.Belief.Recency, ranked[i].score)
		}
		log.Printf("[MemRetrieval] mode=%s top%d=%s", label, n, strings.TrimSpace(sb.String()))
	}

	return out, nil
}

// beliefWeightsLabel returns a human-readable label for a BeliefWeights vector
// by matching against the known presets. Falls back to "custom".
func beliefWeightsLabel(w cognition.BeliefWeights) string {
	type preset struct {
		name string
		w    cognition.BeliefWeights
	}
	presets := []preset{
		{"aletheia", cognition.WeightsAletheia},
		{"fivewhy", cognition.WeightsFiveWhy},
		{"react", cognition.WeightsReAct},
		{"cbr", cognition.WeightsCBR},
		{"standard", cognition.WeightsStandard},
	}
	for _, p := range presets {
		if math.Abs(p.w.Factual-w.Factual) < 0.01 &&
			math.Abs(p.w.Causal-w.Causal) < 0.01 &&
			math.Abs(p.w.Recency-w.Recency) < 0.01 {
			return p.name
		}
	}
	return fmt.Sprintf("custom(F:%.2f C:%.2f R:%.2f S:%.2f)", w.Factual, w.Causal, w.Recency, w.Semantic)
}

func (a *memoryBankAdapter) QuerySolved(ctx context.Context, topic string, limit int) ([]cognition.MemFrag, error) {
	frags, err := a.mb.QuerySolved(ctx, topic, limit)
	if err != nil {
		return nil, err
	}
	out := make([]cognition.MemFrag, len(frags))
	for i, f := range frags {
		mf := cognition.MemFrag{
			ID:          f.ID,
			Content:     f.Content,
			Source:      f.Source,
			Topic:       f.Topic,
			Importance:  f.Importance,
			CausalScore: f.CausalScore,
			AccessCount: f.AccessCount,
			Volatility:  string(f.Volatility),
			CreatedAt:   f.CreatedAt,
			Belief:      cognition.Belief{Factual: provenanceCertainty(f.Provenance)},
		}
		mf.Belief = cognition.ComputeBelief(mf)
		mf.DynamicCertainty = cognition.ComputeDynamicCertainty(mf)
		out[i] = mf
	}
	return out, nil
}

// BumpBelief implements cognition.CertaintyUpdater.
// Routes axis-specific belief mutations to the correct PB field.
// "factual"  → importance field (evidence quality, corroboration signal)
// "causal"   → causal_score field (mechanism depth, 5-WHY signal)
// "recency"  → no-op (always computed from age, never stored)
// Fires async via goroutine in Aletheia/5-WHY so it never blocks the generation path.
func (a *memoryBankAdapter) BumpBelief(ctx context.Context, fragID string, axis string, delta float64) {
	switch axis {
	case "factual":
		a.mb.BumpImportance(ctx, fragID, delta)
	case "causal":
		a.mb.BumpCausalScore(ctx, fragID, delta)
	// "recency" is intentionally a no-op — computed at query time from age
	}
}

func truncateStr(s string, n int) string {
if len(s) <= n { return s }
return s[:n] + "…"
}

// ─── Vision Adapter ───────────────────────────────────────────────────────────

// ollamaBaseURL returns the Ollama API base URL from env or default.
func ollamaBaseURL() string {
if u := os.Getenv("OLLAMA_URL"); u != "" {
return u
}
return "http://127.0.0.1:11434"
}

// visionAdapter implements cognition.VisionAnalyzer using moondream via Ollama.
// CPU-safe: moondream is 1.7GB and runs on EPYC in ~5-8s per image.
type visionAdapter struct {
ollamaURL string
}

func (v *visionAdapter) Analyze(input cognition.VisionInput) (cognition.VisionResult, error) {
// Resolve image to base64
var b64 string
switch {
case input.Base64 != "":
b64 = input.Base64
case input.FilePath != "":
data, err := os.ReadFile(input.FilePath)
if err != nil {
return cognition.VisionResult{}, fmt.Errorf("vision: read file: %w", err)
}
b64 = base64.StdEncoding.EncodeToString(data)
case input.URL != "":
resp, err := http.Get(input.URL) //nolint:gosec — URL provided by authenticated caller
if err != nil {
return cognition.VisionResult{}, fmt.Errorf("vision: fetch url: %w", err)
}
defer resp.Body.Close()
data, err := io.ReadAll(resp.Body)
if err != nil {
return cognition.VisionResult{}, fmt.Errorf("vision: read url body: %w", err)
}
b64 = base64.StdEncoding.EncodeToString(data)
default:
return cognition.VisionResult{}, fmt.Errorf("vision: no image source provided")
}

prompt := input.Prompt
if prompt == "" {
prompt = cognition.DefaultVisionPrompt
}

// Call Ollama /api/generate with images array
reqBody, _ := json.Marshal(map[string]any{
"model":       "moondream:latest",
"prompt":      prompt,
"images":      []string{b64},
"stream":      false,
"num_predict": 256,
"options": map[string]any{
"temperature": 0.1,
"num_ctx":     4096,
},
})

ctx, cancel := context.WithTimeout(context.Background(), 60*time.Second)
defer cancel()

req, _ := http.NewRequestWithContext(ctx, http.MethodPost,
v.ollamaURL+"/api/generate", strings.NewReader(string(reqBody)))
req.Header.Set("Content-Type", "application/json")

httpResp, err := http.DefaultClient.Do(req)
if err != nil {
return cognition.VisionResult{}, fmt.Errorf("vision: ollama call: %w", err)
}
defer httpResp.Body.Close()

var ollamaResp struct {
Response string `json:"response"`
Done     bool   `json:"done"`
}
if err := json.NewDecoder(httpResp.Body).Decode(&ollamaResp); err != nil {
return cognition.VisionResult{}, fmt.Errorf("vision: decode response: %w", err)
}

description := strings.TrimSpace(ollamaResp.Response)
tags := extractVisionTags(description)

return cognition.VisionResult{
Description: description,
Tags:        tags,
Model:       "moondream:latest",
RawResponse: ollamaResp.Response,
}, nil
}

// extractVisionTags derives a small set of concept tags from a description
// by pulling capitalised nouns and key technical terms (heuristic, no LLM call).
func extractVisionTags(description string) []string {
words := strings.Fields(description)
seen := map[string]bool{}
var tags []string
for _, w := range words {
w = strings.Trim(w, ".,;:!?\"'()")
if len(w) < 4 {
continue
}
lower := strings.ToLower(w)
if seen[lower] {
continue
}
// Keep words that start with a capital (proper nouns / concepts) or are technical
if w[0] >= 'A' && w[0] <= 'Z' {
seen[lower] = true
tags = append(tags, lower)
}
if len(tags) >= 8 {
break
}
}
return tags
}

// handleVisionAnalyze handles POST /v1/vision/analyze.
// Accepts image_url, image_base64, or image_path + optional prompt.
// Optionally writes result to MemoryBank with ProvenanceSeen tier.
func (s *ServerV2) handleVisionAnalyze(c *gin.Context) {
var req struct {
ImageURL    string `json:"image_url"`
ImageBase64 string `json:"image_base64"`
ImagePath   string `json:"image_path"`
Prompt      string `json:"prompt"`
SaveMemory  bool   `json:"save_memory"`
}
if err := c.ShouldBindJSON(&req); err != nil {
c.JSON(http.StatusBadRequest, gin.H{"error": "invalid request body"})
return
}

va := s.Agent.SovEngine.VisionRef
if va == nil {
c.JSON(http.StatusServiceUnavailable, gin.H{"error": "vision module not available"})
return
}

result, err := va.Analyze(cognition.VisionInput{
URL:      req.ImageURL,
FilePath: req.ImagePath,
Base64:   req.ImageBase64,
Prompt:   req.Prompt,
})
if err != nil {
log.Printf("[Vision] Analysis error: %v", err)
c.JSON(http.StatusInternalServerError, gin.H{"error": err.Error()})
return
}

resp := gin.H{
"description": result.Description,
"tags":        result.Tags,
"model":       result.Model,
}

// Optional memory write-back with ProvenanceSeen tier
if req.SaveMemory && s.MemoryBank != nil && s.MemoryBank.IsEnabled() {
topic := "visual_input"
if len(result.Tags) > 0 {
topic = result.Tags[0]
}
source := req.ImageURL
if source == "" {
source = req.ImagePath
}
s.MemoryBank.Write(service.MemoryFragment{
Content:    result.Description,
Source:     "vision",
Topic:      topic,
Importance: 0.65,
Provenance: service.ProvenanceSeen,
Volatility: service.VolatilityCurrent,
})
resp["memory_saved"] = true
resp["memory_topic"] = topic
}

c.JSON(http.StatusOK, resp)
}




// ---------------------------------------------------------------------------
// Enterprise Knowledge Layer API
// ---------------------------------------------------------------------------

// enterpriseLearnJob tracks an async learn job.
type enterpriseLearnJob struct {
	ID        string
	Namespace string
	Source    string
	Target    string
	Status    string // "running" | "done" | "error"
	Error     string
	Result    map[string]any
	Started   time.Time
	Finished  time.Time
}

// resolveEnterpriseLayer returns an *enterprise.Layer for the request namespace.
// Falls back to the engine-level layer (ORICLI_ENTERPRISE_NAMESPACE) if ns is empty.
// Layers are cached in s.entLayers by namespace.
func (s *ServerV2) resolveEnterpriseLayer(ns string) (*enterprise.Layer, error) {
	if ns == "" {
		el := s.Agent.SovEngine.EnterpriseLayer
		if el == nil {
			return nil, fmt.Errorf("enterprise layer not active — set ORICLI_ENTERPRISE_NAMESPACE or pass \"namespace\" in request")
		}
		ent, ok := el.(*enterprise.Layer)
		if !ok {
			return nil, fmt.Errorf("enterprise layer type assertion failed")
		}
		return ent, nil
	}
	if v, ok := s.entLayers.Load(ns); ok {
		return v.(*enterprise.Layer), nil
	}
	ent, err := enterprise.New(ns)
	if err != nil {
		return nil, fmt.Errorf("bootstrap enterprise layer for namespace %q: %w", ns, err)
	}
	s.entLayers.Store(ns, ent)
	log.Printf("[Enterprise] bootstrapped layer for namespace %q", ns)
	return ent, nil
}

// handleEnterpriseLearn kicks off an async indexing job and returns 202 immediately.
//
//	POST /v1/enterprise/learn
//	{ "namespace": "acme",  "source": "dir",    "path": "/data/docs" }
//	{ "namespace": "acme",  "source": "github",  "repo": "owner/repo", "path": "docs/" }
//	{ "namespace": "acme",  "source": "notion",  "database_id": "abc123" }
//
// Poll GET /v1/enterprise/learn/:job_id for completion.
// GITHUB_TOKEN and NOTION_API_KEY are read from environment.
func (s *ServerV2) handleEnterpriseLearn(c *gin.Context) {
	var req struct {
		Namespace  string `json:"namespace,omitempty"`
		Source     string `json:"source"`
		Path       string `json:"path,omitempty"`
		DatabaseID string `json:"database_id,omitempty"`
		Repo       string `json:"repo,omitempty"`
	}
	if err := c.ShouldBindJSON(&req); err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"error": "invalid request body: " + err.Error()})
		return
	}
	if req.Source == "" {
		c.JSON(http.StatusBadRequest, gin.H{"error": "source is required (dir | notion | github)"})
		return
	}

	ent, err := s.resolveEnterpriseLayer(req.Namespace)
	if err != nil {
		c.JSON(http.StatusServiceUnavailable, gin.H{"error": err.Error()})
		return
	}

	// Validate source-specific required params before firing the goroutine.
	switch req.Source {
	case "dir":
		if req.Path == "" {
			c.JSON(http.StatusBadRequest, gin.H{"error": "path is required for source=dir"})
			return
		}
	case "github":
		if req.Repo == "" {
			c.JSON(http.StatusBadRequest, gin.H{"error": "repo (owner/repo) is required for source=github"})
			return
		}
	case "notion":
		if req.DatabaseID == "" {
			c.JSON(http.StatusBadRequest, gin.H{"error": "database_id is required for source=notion"})
			return
		}
		if _, connErr := notionconn.NewNotionConnector(); connErr != nil {
			c.JSON(http.StatusBadRequest, gin.H{"error": "notion connector: " + connErr.Error() + " — set NOTION_API_KEY in service env"})
			return
		}
	default:
		c.JSON(http.StatusBadRequest, gin.H{"error": "unsupported source: " + req.Source + " (supported: dir, notion, github)"})
		return
	}

	// Build job.
	target := req.Path + req.Repo + req.DatabaseID
	job := &enterpriseLearnJob{
		ID:        fmt.Sprintf("eljob-%d", time.Now().UnixNano()),
		Namespace: ent.Namespace(),
		Source:    req.Source,
		Target:    target,
		Status:    "running",
		Started:   time.Now().UTC(),
	}
	s.entJobs.Store(job.ID, job)

	// Fire indexing goroutine.
	go func() {
		ctx, cancel := context.WithTimeout(context.Background(), 10*time.Minute)
		defer cancel()
		var stats rag.IndexStats
		var runErr error

		switch req.Source {
		case "dir":
			stats, runErr = ent.IndexDirectory(req.Path, enterprise.DefaultIndexOptions())
		case "github":
			conn := githubconn.NewGitHubConnector()
			stats, runErr = ent.IndexConnector(ctx, conn, enterpriseconn.FetchOptions{Query: req.Repo, FolderID: req.Path})
		case "notion":
			conn, _ := notionconn.NewNotionConnector()
			stats, runErr = ent.IndexConnector(ctx, conn, enterpriseconn.FetchOptions{Query: req.DatabaseID})
		}

		job.Finished = time.Now().UTC()
		if runErr != nil {
			job.Status = "error"
			job.Error = runErr.Error()
			log.Printf("[Enterprise] job %s error: %v", job.ID, runErr)
		} else {
			job.Status = "done"
			job.Result = map[string]any{
				"files_indexed":  stats.FilesIndexed,
				"files_skipped":  stats.SkippedUnsupported,
				"chunks_indexed": stats.ChunksIndexed,
				"parse_errors":   stats.ParseErrors,
			}
			log.Printf("[Enterprise] job %s done: %d files, %d chunks indexed for namespace %q", job.ID, stats.FilesIndexed, stats.ChunksIndexed, ent.Namespace())
		}
	}()

	c.JSON(http.StatusAccepted, gin.H{
		"job_id":    job.ID,
		"namespace": job.Namespace,
		"source":    req.Source,
		"target":    target,
		"status":    "running",
		"poll":      "/v1/enterprise/learn/" + job.ID,
	})
}

// handleEnterpriseLearnStatus returns the status of a learn job.
//
//	GET /v1/enterprise/learn/:job_id
func (s *ServerV2) handleEnterpriseLearnStatus(c *gin.Context) {
	v, ok := s.entJobs.Load(c.Param("job_id"))
	if !ok {
		c.JSON(http.StatusNotFound, gin.H{"error": "job not found"})
		return
	}
	job := v.(*enterpriseLearnJob)
	resp := gin.H{
		"job_id":    job.ID,
		"namespace": job.Namespace,
		"source":    job.Source,
		"target":    job.Target,
		"status":    job.Status,
		"started":   job.Started,
	}
	if !job.Finished.IsZero() {
		resp["finished"] = job.Finished
		resp["duration_s"] = job.Finished.Sub(job.Started).Seconds()
	}
	if job.Error != "" {
		resp["error"] = job.Error
	}
	if job.Result != nil {
		resp["result"] = job.Result
	}
	c.JSON(http.StatusOK, resp)
}

// handleEnterpriseSearch queries the tenant's knowledge namespace.
//
//	GET /v1/enterprise/knowledge/search?q=<query>&top_k=<n>&namespace=<ns>
func (s *ServerV2) handleEnterpriseSearch(c *gin.Context) {
	ent, err := s.resolveEnterpriseLayer(c.Query("namespace"))
	if err != nil {
		c.JSON(http.StatusServiceUnavailable, gin.H{"error": err.Error()})
		return
	}

	query := strings.TrimSpace(c.Query("q"))
	if query == "" {
		c.JSON(http.StatusBadRequest, gin.H{"error": "q (query) parameter is required"})
		return
	}
	topK := 5
	if v := c.Query("top_k"); v != "" {
		if n, err := strconv.Atoi(v); err == nil && n > 0 && n <= 20 {
			topK = n
		}
	}

	segments, err := ent.QueryKnowledgeSegments(c.Request.Context(), query, topK)
	if err != nil {
		c.JSON(http.StatusInternalServerError, gin.H{"error": err.Error()})
		return
	}

	results := make([]gin.H, 0, len(segments))
	for _, seg := range segments {
		results = append(results, gin.H{
			"id":         seg.ID,
			"content":    seg.Content,
			"similarity": seg.Similarity,
			"metadata":   seg.Metadata,
		})
	}
	c.JSON(http.StatusOK, gin.H{
		"namespace": ent.Namespace(),
		"query":     query,
		"top_k":     topK,
		"results":   results,
	})
}

// handleEnterpriseClear wipes all indexed knowledge for the namespace.
//
//	DELETE /v1/enterprise/knowledge?namespace=<ns>
func (s *ServerV2) handleEnterpriseClear(c *gin.Context) {
	ent, err := s.resolveEnterpriseLayer(c.Query("namespace"))
	if err != nil {
		c.JSON(http.StatusServiceUnavailable, gin.H{"error": err.Error()})
		return
	}

	ns := ent.Namespace()
	if err := ent.ClearKnowledge(); err != nil {
		c.JSON(http.StatusInternalServerError, gin.H{"error": err.Error()})
		return
}
c.JSON(http.StatusOK, gin.H{"namespace": ns, "cleared": true})
}

// ─── engine.Applier implementation ───────────────────────────────────────────

// ApplyEngineConfig implements engine.Applier. Called by RemoteConfigSync when a
// new config version is fetched from the Thynaptic config endpoint.
// Safe to call concurrently — each section applies independently.
func (s *ServerV2) ApplyEngineConfig(cfg engine.EngineConfig) error {
if cfg.Message != "" {
log.Printf("[EngineConfig] Applying: %s (v=%s)", cfg.Message, cfg.Version)
}

// SCAI threshold override
if cfg.SCAIThreshold != nil {
s.Agent.SovEngine.SCAI.SetSeverityThreshold(*cfg.SCAIThreshold)
log.Printf("[EngineConfig] SCAI threshold → %.2f", *cfg.SCAIThreshold)
}

// Model routing override
if len(cfg.AllowedModels) > 0 {
log.Printf("[EngineConfig] AllowedModels updated: %v", cfg.AllowedModels)
// First entry becomes the default model.
if len(cfg.AllowedModels) > 0 {
s.Agent.GenService.DefaultModel = cfg.AllowedModels[0]
}
}

// Disable modules — mark as inactive in the Orchestrator registry.
for _, slug := range cfg.DisabledModules {
log.Printf("[EngineConfig] Disabling module: %s", slug)
s.Orchestrator.DisableModule(slug)
}

return nil
}

// ---------------------------------------------------------------------------
// SPP Swarm Handlers
// ---------------------------------------------------------------------------

// handleSwarmConnect upgrades the HTTP connection to a WebSocket SPP peer session.
// Auth is the SPP handshake itself (Ed25519 + Constitutional Attestation).
func (s *ServerV2) handleSwarmConnect(c *gin.Context) {
if s.SwarmRegistry == nil {
c.JSON(http.StatusServiceUnavailable, gin.H{"error": "swarm not enabled — set ORICLI_SWARM_ENABLED=true"})
return
}
s.SwarmRegistry.HandleUpgrade(c.Writer, c.Request)
}

// handleSwarmPeers returns all connected peers and their reputation scores (admin only).
func (s *ServerV2) handleSwarmPeers(c *gin.Context) {
if s.SwarmRegistry == nil {
c.JSON(http.StatusOK, gin.H{"peers": []any{}, "swarm_enabled": false})
return
}
ids := s.SwarmRegistry.ConnectedPeers()
c.JSON(http.StatusOK, gin.H{
"swarm_enabled":   true,
"connected_peers": len(ids),
"peer_ids":        ids,
})
}

// handleSwarmHealth returns the aggregate swarm health report (admin only).
func (s *ServerV2) handleSwarmHealth(c *gin.Context) {
if s.SwarmMonitor == nil {
c.JSON(http.StatusOK, gin.H{"swarm_enabled": false})
return
}
var ids []string
if s.SwarmRegistry != nil {
ids = s.SwarmRegistry.ConnectedPeers()
}
report := s.SwarmMonitor.Report(ids)
c.JSON(http.StatusOK, report)
}

// ---------------------------------------------------------------------------
// P5: Hive Mind Consensus admin handlers
// ---------------------------------------------------------------------------

// handleSwarmJuryStatus returns active jury sessions and quorum state.
func (s *ServerV2) handleSwarmJuryStatus(c *gin.Context) {
if s.JuryClient == nil {
c.JSON(http.StatusOK, gin.H{"jury_enabled": false})
return
}
sessions := s.JuryClient.ActiveSessions()
c.JSON(http.StatusOK, gin.H{
"jury_enabled":    true,
"active_sessions": sessions,
})
}

// handleSwarmConsensusFragments returns universal-tier fragments and their vote tallies.
func (s *ServerV2) handleSwarmConsensusFragments(c *gin.Context) {
if s.VoteLog == nil {
c.JSON(http.StatusOK, gin.H{"consensus_enabled": false})
return
}
c.JSON(http.StatusOK, gin.H{
"consensus_enabled": true,
"fragments":         s.VoteLog.Snapshot(),
})
}

// handleSwarmPurgeTraces deletes all ESI skill traces from a specific peer node.
func (s *ServerV2) handleSwarmPurgeTraces(c *gin.Context) {
nodeID := c.Param("node_id")
if nodeID == "" {
c.JSON(http.StatusBadRequest, gin.H{"error": "node_id required"})
return
}
if s.ESIFederation == nil {
c.JSON(http.StatusOK, gin.H{"purged": 0, "esi_enabled": false})
return
}
s.ESIFederation.PurgeNodeTraces(c.Request.Context(), nodeID)
c.JSON(http.StatusOK, gin.H{"purged": true, "node_id": nodeID})
}

// ─────────────────────────────────────────────────────────────────────────────
// SCL-6: Sovereign Cognitive Ledger admin endpoints
// ─────────────────────────────────────────────────────────────────────────────

// handleSCLBrowse lists SCL records, optionally filtered by tier.
// GET /v1/scl/records?tier=facts&limit=20
func (s *ServerV2) handleSCLBrowse(c *gin.Context) {
	if s.SCLEngine == nil {
		c.JSON(http.StatusServiceUnavailable, gin.H{"error": "SCL not initialized"})
		return
	}
	tierStr := c.Query("tier")
	limit := 20
	if lStr := c.Query("limit"); lStr != "" {
		if n, err := strconv.Atoi(lStr); err == nil && n > 0 && n <= 200 {
			limit = n
		}
	}
	ctx, cancel := context.WithTimeout(c.Request.Context(), 10*time.Second)
	defer cancel()
	records, _, err := s.SCLEngine.Browse(ctx, scl.Tier(tierStr), 1, limit)
	if err != nil {
		c.JSON(http.StatusInternalServerError, gin.H{"error": err.Error()})
		return
	}
	c.JSON(http.StatusOK, gin.H{"records": records, "count": len(records)})
}

// handleSCLSearch performs a semantic search over the SCL.
// GET /v1/scl/search?q=<query>&tier=<tier>
func (s *ServerV2) handleSCLSearch(c *gin.Context) {
	if s.SCLEngine == nil {
		c.JSON(http.StatusServiceUnavailable, gin.H{"error": "SCL not initialized"})
		return
	}
	query := c.Query("q")
	if query == "" {
		c.JSON(http.StatusBadRequest, gin.H{"error": "q required"})
		return
	}
	limit := 10
	ctx, cancel := context.WithTimeout(c.Request.Context(), 10*time.Second)
	defer cancel()
	records, err := s.SCLEngine.SearchBySubject(ctx, query, limit)
	if err != nil {
		c.JSON(http.StatusInternalServerError, gin.H{"error": err.Error()})
		return
	}
	c.JSON(http.StatusOK, gin.H{"results": records, "count": len(records)})
}

// handleSCLDelete hard-deletes a record from the SCL.
// DELETE /v1/scl/records/:id
func (s *ServerV2) handleSCLDelete(c *gin.Context) {
	if s.SCL == nil {
		c.JSON(http.StatusServiceUnavailable, gin.H{"error": "SCL not initialized"})
		return
	}
	id := c.Param("id")
	if id == "" {
		c.JSON(http.StatusBadRequest, gin.H{"error": "id required"})
		return
	}
	ctx, cancel := context.WithTimeout(c.Request.Context(), 5*time.Second)
	defer cancel()
	if err := s.SCL.Delete(ctx, id); err != nil {
		c.JSON(http.StatusInternalServerError, gin.H{"error": err.Error()})
		return
	}
	c.JSON(http.StatusOK, gin.H{"deleted": id})
}

// handleSCLRevise updates the content of an existing SCL record (versioned).
// PATCH /v1/scl/records/:id   Body: {"content": "...", "confidence": 0.9}
func (s *ServerV2) handleSCLRevise(c *gin.Context) {
	if s.SCL == nil {
		c.JSON(http.StatusServiceUnavailable, gin.H{"error": "SCL not initialized"})
		return
	}
	id := c.Param("id")
	if id == "" {
		c.JSON(http.StatusBadRequest, gin.H{"error": "id required"})
		return
	}
	var body struct {
		Content    string  `json:"content"`
		Confidence float64 `json:"confidence"`
	}
	if err := c.ShouldBindJSON(&body); err != nil || body.Content == "" {
		c.JSON(http.StatusBadRequest, gin.H{"error": "content required"})
		return
	}
	if body.Confidence <= 0 {
		body.Confidence = 0.8
	}
	ctx, cancel := context.WithTimeout(c.Request.Context(), 5*time.Second)
	defer cancel()
	newID, err := s.SCL.Revise(ctx, id, body.Content, body.Confidence)
	if err != nil {
		c.JSON(http.StatusInternalServerError, gin.H{"error": err.Error()})
		return
	}
	c.JSON(http.StatusOK, gin.H{"revised": id, "new_id": newID})
}

// handleSCLStats returns record counts per tier, avg confidence, and stale count.
// GET /v1/scl/stats
func (s *ServerV2) handleSCLStats(c *gin.Context) {
	if s.SCL == nil {
		c.JSON(http.StatusServiceUnavailable, gin.H{"error": "SCL not initialized"})
		return
	}
	ctx, cancel := context.WithTimeout(c.Request.Context(), 10*time.Second)
	defer cancel()
	stats := s.SCL.Stats(ctx)
	c.JSON(http.StatusOK, stats)
}

// ── TCD Admin Handlers ────────────────────────────────────────────────────────

// GET /v1/tcd/domains — list all domains with status + confidence
func (s *ServerV2) handleTCDListDomains(c *gin.Context) {
if s.TCDManifest == nil {
c.JSON(http.StatusServiceUnavailable, gin.H{"error": "TCD not enabled"})
return
}
domains := s.TCDManifest.All()
c.JSON(http.StatusOK, gin.H{"domains": domains, "count": len(domains)})
}

// POST /v1/tcd/domains — manually add a domain
// Body: {"name": "robotics", "keywords": ["robot", "automation"]}
func (s *ServerV2) handleTCDAddDomain(c *gin.Context) {
if s.TCDManifest == nil {
c.JSON(http.StatusServiceUnavailable, gin.H{"error": "TCD not enabled"})
return
}
var body struct {
Name     string   `json:"name"`
Keywords []string `json:"keywords"`
}
if err := c.ShouldBindJSON(&body); err != nil || body.Name == "" {
c.JSON(http.StatusBadRequest, gin.H{"error": "name required"})
return
}
d := &tcdpkg.Domain{
ID:            strings.ToLower(strings.ReplaceAll(body.Name, " ", "_")),
Name:          body.Name,
Keywords:      body.Keywords,
Status:        tcdpkg.StatusActive,
SourceWeights: tcdpkg.DefaultSourceWeights,
}
ctx, cancel := context.WithTimeout(c.Request.Context(), 10*time.Second)
defer cancel()
if err := s.TCDManifest.(interface {
Add(context.Context, *tcdpkg.Domain) error
}).Add(ctx, d); err != nil {
c.JSON(http.StatusInternalServerError, gin.H{"error": err.Error()})
return
}
c.JSON(http.StatusCreated, gin.H{"domain": d})
}

// POST /v1/tcd/tick — trigger immediate TCD cycle (admin)
func (s *ServerV2) handleTCDTriggerTick(c *gin.Context) {
if s.TCDDaemon == nil {
c.JSON(http.StatusServiceUnavailable, gin.H{"error": "TCD not enabled"})
return
}
s.TCDDaemon.TriggerManualTick()
c.JSON(http.StatusOK, gin.H{"status": "tick queued"})
}

// GET /v1/tcd/gaps — list current orphan clusters detected by GapDetector
func (s *ServerV2) handleTCDGaps(c *gin.Context) {
if s.TCDGapDetector == nil {
c.JSON(http.StatusServiceUnavailable, gin.H{"error": "TCD gap detector not enabled"})
return
}
ctx, cancel := context.WithTimeout(c.Request.Context(), 30*time.Second)
defer cancel()
spawned, err := s.TCDGapDetector.Scan(ctx)
if err != nil {
c.JSON(http.StatusInternalServerError, gin.H{"error": err.Error()})
return
}
c.JSON(http.StatusOK, gin.H{"domains_spawned": spawned})
}

// GET /v1/tcd/domains/:id/lineage — full event chain for a domain
func (s *ServerV2) handleTCDDomainLineage(c *gin.Context) {
if s.TCDManifest == nil {
c.JSON(http.StatusServiceUnavailable, gin.H{"error": "TCD not enabled"})
return
}
id := c.Param("id")
events := s.TCDManifest.GetLineage(id)
c.JSON(http.StatusOK, gin.H{"domain_id": id, "events": events, "count": len(events)})
}

// GET /v1/tcd/lineage — full evolution DAG across all domains
func (s *ServerV2) handleTCDEvolutionTree(c *gin.Context) {
if s.TCDManifest == nil {
c.JSON(http.StatusServiceUnavailable, gin.H{"error": "TCD not enabled"})
return
}
tree := s.TCDManifest.GetEvolutionTree()
c.JSON(http.StatusOK, gin.H{"evolution_tree": tree})
}

// ── Forge Admin Handlers ──────────────────────────────────────────────────────

// GET /v1/forge/tools — list all tools in the library
func (s *ServerV2) handleForgeListTools(c *gin.Context) {
if s.Forge == nil {
c.JSON(http.StatusServiceUnavailable, gin.H{"error": "forge not enabled"})
return
}
tools := s.Forge.Library.All()
c.JSON(http.StatusOK, gin.H{"tools": tools, "count": len(tools), "library_size": s.Forge.LibrarySize()})
}

// DELETE /v1/forge/tools/:name — evict a tool from the library
func (s *ServerV2) handleForgeDeleteTool(c *gin.Context) {
if s.Forge == nil {
c.JSON(http.StatusServiceUnavailable, gin.H{"error": "forge not enabled"})
return
}
name := c.Param("name")
ctx, cancel := context.WithTimeout(c.Request.Context(), 10*time.Second)
defer cancel()
if err := s.Forge.Library.Delete(ctx, name); err != nil {
c.JSON(http.StatusInternalServerError, gin.H{"error": err.Error()})
return
}
c.JSON(http.StatusOK, gin.H{"deleted": name})
}

// GET /v1/forge/tools/:name/source — inspect generated bash source
func (s *ServerV2) handleForgeToolSource(c *gin.Context) {
if s.Forge == nil {
c.JSON(http.StatusServiceUnavailable, gin.H{"error": "forge not enabled"})
return
}
name := c.Param("name")
tool, ok := s.Forge.Library.Load(name)
if !ok {
c.JSON(http.StatusNotFound, gin.H{"error": "tool not found"})
return
}
c.JSON(http.StatusOK, gin.H{"name": name, "source": tool.Source, "description": tool.Description})
}

// POST /v1/forge/tools/:name/invoke — manually invoke a forge tool
// Body: {"args": {...}}
func (s *ServerV2) handleForgeInvokeTool(c *gin.Context) {
if s.Forge == nil {
c.JSON(http.StatusServiceUnavailable, gin.H{"error": "forge not enabled"})
return
}
name := c.Param("name")
var body struct {
Args map[string]interface{} `json:"args"`
}
if err := c.ShouldBindJSON(&body); err != nil {
body.Args = map[string]interface{}{}
}
ctx, cancel := context.WithTimeout(c.Request.Context(), 15*time.Second)
defer cancel()
out, err := s.Forge.InvokeJITTool(ctx, name, body.Args)
if err != nil {
c.JSON(http.StatusInternalServerError, gin.H{"error": err.Error()})
return
}
c.JSON(http.StatusOK, gin.H{"result": out, "tool": name})
}

// GET /v1/forge/stats — pipeline metrics
func (s *ServerV2) handleForgeStats(c *gin.Context) {
if s.Forge == nil {
c.JSON(http.StatusServiceUnavailable, gin.H{"error": "forge not enabled"})
return
}
stats := s.Forge.Stats()
c.JSON(http.StatusOK, gin.H{
"stats":        stats,
"library_size": s.Forge.LibrarySize(),
})
}

// POST /v1/forge/forge — manually trigger a forge attempt
// Body: {"task": "...", "tried_tools": ["tool_a", "tool_b"]}
func (s *ServerV2) handleForgeTryForge(c *gin.Context) {
if s.Forge == nil {
c.JSON(http.StatusServiceUnavailable, gin.H{"error": "forge not enabled"})
return
}
var body struct {
Task        string   `json:"task"`
TriedTools  []string `json:"tried_tools"`
}
if err := c.ShouldBindJSON(&body); err != nil || body.Task == "" {
c.JSON(http.StatusBadRequest, gin.H{"error": "task required"})
return
}
ctx, cancel := context.WithTimeout(c.Request.Context(), 60*time.Second)
defer cancel()
tool, err := s.Forge.TryForge(ctx, body.Task, body.TriedTools)
if err != nil {
c.JSON(http.StatusUnprocessableEntity, gin.H{"error": err.Error()})
return
}
c.JSON(http.StatusCreated, gin.H{"tool": tool, "status": "forged"})
}

// ─── PAD: Parallel Agent Dispatch ────────────────────────────────────────────

// POST /v1/pad/dispatch — submit a query for parallel dispatch
func (s *ServerV2) handlePADDispatch(c *gin.Context) {
	if s.PAD == nil || !s.PAD.Enabled {
		c.JSON(http.StatusServiceUnavailable, gin.H{"error": "PAD not enabled"})
		return
	}
	var req struct {
		Query      string `json:"query" binding:"required"`
		MaxWorkers int    `json:"max_workers"`
		Critique   bool   `json:"critique"`
	}
	if err := c.ShouldBindJSON(&req); err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"error": err.Error()})
		return
	}

	if req.Critique {
		session, report, err := s.PAD.DispatchWithCritique(c.Request.Context(), req.Query, req.MaxWorkers)
		if err != nil {
			c.JSON(http.StatusInternalServerError, gin.H{"error": err.Error()})
			return
		}
		c.JSON(http.StatusOK, gin.H{
			"session":         session,
			"critique_report": report,
		})
		return
	}

	session, err := s.PAD.Dispatch(c.Request.Context(), req.Query, req.MaxWorkers)
	if err != nil {
		c.JSON(http.StatusInternalServerError, gin.H{"error": err.Error()})
		return
	}
	c.JSON(http.StatusOK, session)
}

// GET /v1/pad/sessions — list recent sessions (last 20)
func (s *ServerV2) handlePADListSessions(c *gin.Context) {
if s.PAD == nil || !s.PAD.Enabled {
c.JSON(http.StatusServiceUnavailable, gin.H{"error": "PAD not enabled"})
return
}
sessions := s.PAD.Sessions.List(20)
c.JSON(http.StatusOK, gin.H{"sessions": sessions, "count": len(sessions)})
}

// GET /v1/pad/sessions/:id — get session detail
func (s *ServerV2) handlePADGetSession(c *gin.Context) {
if s.PAD == nil || !s.PAD.Enabled {
c.JSON(http.StatusServiceUnavailable, gin.H{"error": "PAD not enabled"})
return
}
id := c.Param("id")
sess, ok := s.PAD.Sessions.Get(id)
if !ok {
c.JSON(http.StatusNotFound, gin.H{"error": "session not found"})
return
}
c.JSON(http.StatusOK, sess)
}

// GET /v1/pad/stats — dispatch metrics
func (s *ServerV2) handlePADStats(c *gin.Context) {
if s.PAD == nil || !s.PAD.Enabled {
c.JSON(http.StatusServiceUnavailable, gin.H{"error": "PAD not enabled"})
return
}
c.JSON(http.StatusOK, s.PAD.Stats())
}

// ─── Goals: Sovereign Goal Engine ────────────────────────────────────────────

// POST /v1/goals — create a new sovereign goal
func (s *ServerV2) handleGoalCreate(c *gin.Context) {
if s.GoalStore == nil || s.GoalPlanner == nil {
c.JSON(http.StatusServiceUnavailable, gin.H{"error": "Goal Engine not enabled"})
return
}
var req struct {
Objective string `json:"objective" binding:"required"`
Context   string `json:"context"`
MaxNodes  int    `json:"max_nodes"`
}
if err := c.ShouldBindJSON(&req); err != nil {
c.JSON(http.StatusBadRequest, gin.H{"error": err.Error()})
return
}

dag, err := s.GoalPlanner.Plan(c.Request.Context(), req.Objective, req.Context, req.MaxNodes)
if err != nil {
c.JSON(http.StatusInternalServerError, gin.H{"error": err.Error()})
return
}
if err := s.GoalStore.Save(c.Request.Context(), dag); err != nil {
c.JSON(http.StatusInternalServerError, gin.H{"error": err.Error()})
return
}

// Trigger a manual daemon tick so goal starts immediately (non-blocking)
if s.GoalDaemon != nil {
select {
case s.GoalDaemon.ManualTick <- struct{}{}:
default:
}
}

c.JSON(http.StatusCreated, dag)
}

// GET /v1/goals — list recent goals
func (s *ServerV2) handleGoalList(c *gin.Context) {
if s.GoalStore == nil {
c.JSON(http.StatusServiceUnavailable, gin.H{"error": "Goal Engine not enabled"})
return
}
goals := s.GoalStore.List(20)
c.JSON(http.StatusOK, gin.H{"goals": goals, "count": len(goals)})
}

// GET /v1/goals/:id — get goal detail
func (s *ServerV2) handleGoalGet(c *gin.Context) {
if s.GoalStore == nil {
c.JSON(http.StatusServiceUnavailable, gin.H{"error": "Goal Engine not enabled"})
return
}
id := c.Param("id")
g, err := s.GoalStore.Load(c.Request.Context(), id)
if err != nil {
c.JSON(http.StatusNotFound, gin.H{"error": err.Error()})
return
}
c.JSON(http.StatusOK, g)
}

// POST /v1/goals/:id/tick — manually advance a specific goal
func (s *ServerV2) handleGoalTick(c *gin.Context) {
if s.GoalStore == nil || s.GoalDaemon == nil {
c.JSON(http.StatusServiceUnavailable, gin.H{"error": "Goal Engine not enabled"})
return
}
select {
case s.GoalDaemon.ManualTick <- struct{}{}:
c.JSON(http.StatusAccepted, gin.H{"status": "tick triggered"})
default:
c.JSON(http.StatusTooManyRequests, gin.H{"error": "tick already queued"})
}
}

// DELETE /v1/goals/:id — cancel a goal
func (s *ServerV2) handleGoalCancel(c *gin.Context) {
if s.GoalStore == nil {
c.JSON(http.StatusServiceUnavailable, gin.H{"error": "Goal Engine not enabled"})
return
}
id := c.Param("id")
if err := s.GoalStore.Cancel(c.Request.Context(), id); err != nil {
c.JSON(http.StatusNotFound, gin.H{"error": err.Error()})
return
}
c.JSON(http.StatusOK, gin.H{"status": "cancelled", "id": id})
}

// ─── FineTune: Automated LoRA Training ───────────────────────────────────────

// POST /v1/finetune/run — start a fine-tuning job
func (s *ServerV2) handleFineTuneRun(c *gin.Context) {
if s.FineTune == nil || !s.FineTune.Enabled {
c.JSON(http.StatusServiceUnavailable, gin.H{"error": "fine-tuning disabled — set ORICLI_FINETUNE_ENABLED=true"})
return
}
var req struct {
ModelBase    string `json:"model_base"`
DatasetCount int    `json:"dataset_count"`
GPUType      string `json:"gpu_type"`
}
if err := c.ShouldBindJSON(&req); err != nil {
c.JSON(http.StatusBadRequest, gin.H{"error": err.Error()})
return
}

cfg := finetune.RunConfig{
ModelBase:    req.ModelBase,
DatasetCount: req.DatasetCount,
GPUType:      req.GPUType,
}

jobID, err := s.FineTune.RunAsync(cfg)
if err != nil {
c.JSON(http.StatusConflict, gin.H{"error": err.Error()})
return
}
c.JSON(http.StatusAccepted, gin.H{
"job_id":  jobID,
"message": "fine-tuning job queued — poll GET /v1/finetune/status/" + jobID,
})
}

// GET /v1/finetune/status/:job_id — get job status
func (s *ServerV2) handleFineTuneStatus(c *gin.Context) {
if s.FineTune == nil {
c.JSON(http.StatusServiceUnavailable, gin.H{"error": "fine-tuning not enabled"})
return
}
jobID := c.Param("job_id")
status, ok := s.FineTune.GetStatus(jobID)
if !ok {
c.JSON(http.StatusNotFound, gin.H{"error": "job not found"})
return
}
c.JSON(http.StatusOK, status)
}

// GET /v1/finetune/jobs — list all jobs
func (s *ServerV2) handleFineTuneJobs(c *gin.Context) {
if s.FineTune == nil {
c.JSON(http.StatusServiceUnavailable, gin.H{"error": "fine-tuning not enabled"})
return
}
jobs := s.FineTune.ListJobs()
c.JSON(http.StatusOK, gin.H{"jobs": jobs, "count": len(jobs)})
}

// ─── Waitlist: SMB API sign-up capture ───────────────────────────────────────

// POST /v1/waitlist — public endpoint, no auth required
func (s *ServerV2) handleWaitlistJoin(c *gin.Context) {
var req struct {
Name    string `json:"name"    binding:"required"`
Company string `json:"company"`
Email   string `json:"email"   binding:"required"`
Plan    string `json:"plan"    binding:"required"`
}
if err := c.ShouldBindJSON(&req); err != nil {
c.JSON(http.StatusBadRequest, gin.H{"error": "name, email, and plan are required"})
return
}

// Basic email sanity check
if !strings.Contains(req.Email, "@") || !strings.Contains(req.Email, ".") {
c.JSON(http.StatusBadRequest, gin.H{"error": "invalid email address"})
return
}

// Validate plan
validPlans := map[string]bool{"starter": true, "business": true, "enterprise": true}
if !validPlans[strings.ToLower(req.Plan)] {
c.JSON(http.StatusBadRequest, gin.H{"error": "invalid plan — must be starter, business, or enterprise"})
return
}

record := map[string]any{
"name":       req.Name,
"company":    req.Company,
"email":      strings.ToLower(strings.TrimSpace(req.Email)),
"plan":       strings.ToLower(req.Plan),
"created_at": time.Now().UTC().Format(time.RFC3339),
"status":     "pending",
}

// Write to PocketBase if available
if s.MemoryBank != nil {
pbClient := s.MemoryBank.GetAdminClient()
if pbClient != nil {
ctx, cancel := context.WithTimeout(context.Background(), 8*time.Second)
defer cancel()
_, err := pbClient.CreateRecord(ctx, "waitlist", record)
if err != nil {
log.Printf("[Waitlist] PB write error: %v", err)
// Fall through — don't fail the request if PB is having issues
} else {
log.Printf("[Waitlist] New signup: %s <%s> plan=%s", req.Name, req.Email, req.Plan)
}
}
}

c.JSON(http.StatusOK, gin.H{
"success": true,
"message": "You're on the list. We'll reach out within 24 hours.",
})
}

// ── Adversarial Sentinel ──────────────────────────────────────────────────────

// POST /v1/sentinel/challenge — manually challenge a plan
func (s *ServerV2) handleSentinelChallenge(c *gin.Context) {
	if s.Sentinel == nil {
		c.JSON(http.StatusServiceUnavailable, gin.H{"error": "sentinel not enabled — set ORICLI_SENTINEL_ENABLED=true"})
		return
	}
	var req struct {
		Query string `json:"query" binding:"required"`
		Plan  string `json:"plan"  binding:"required"`
	}
	if err := c.ShouldBindJSON(&req); err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"error": "query and plan are required"})
		return
	}
	ctx, cancel := context.WithTimeout(c.Request.Context(), 45*time.Second)
	defer cancel()
	report := s.Sentinel.Challenge(ctx, req.Query, req.Plan)
	c.JSON(http.StatusOK, report)
}

// GET /v1/sentinel/stats — sentinel activity stats
func (s *ServerV2) handleSentinelStats(c *gin.Context) {
	if s.Sentinel == nil {
		c.JSON(http.StatusServiceUnavailable, gin.H{"error": "sentinel not enabled"})
		return
	}
	stats := s.Sentinel.GetStats()
	c.JSON(http.StatusOK, gin.H{
		"total_challenges":  stats.TotalChallenges,
		"passed":            stats.Passed,
		"blocked":           stats.Blocked,
		"last_challenge_at": stats.LastChallengeAt,
	})
}

// ---------------------------------------------------------------------------
// Crystal: Skill Crystallization handlers
// ---------------------------------------------------------------------------

// GET /v1/skills/crystals — list all registered crystals
func (s *ServerV2) handleCrystalList(c *gin.Context) {
if s.CrystalCache == nil {
c.JSON(http.StatusServiceUnavailable, gin.H{"error": "crystal cache not enabled"})
return
}
c.JSON(http.StatusOK, gin.H{"crystals": s.CrystalCache.List()})
}

// POST /v1/skills/crystals — register a new crystal skill
func (s *ServerV2) handleCrystalRegister(c *gin.Context) {
if s.CrystalCache == nil {
c.JSON(http.StatusServiceUnavailable, gin.H{"error": "crystal cache not enabled"})
return
}
var req struct {
ID              string  `json:"id" binding:"required"`
Name            string  `json:"name"`
Description     string  `json:"description"`
Pattern         string  `json:"pattern" binding:"required"`
TemplateBody    string  `json:"template_body"`
ReputationScore float64 `json:"reputation_score"`
HitCount        int     `json:"hit_count"`
}
if err := c.ShouldBindJSON(&req); err != nil {
c.JSON(http.StatusBadRequest, gin.H{"error": err.Error()})
return
}
skill := scl.CrystalSkill{
ID:              req.ID,
Name:            req.Name,
Description:     req.Description,
Pattern:         req.Pattern,
TemplateBody:    req.TemplateBody,
ReputationScore: req.ReputationScore,
HitCount:        req.HitCount,
}
if err := s.CrystalCache.Register(skill); err != nil {
c.JSON(http.StatusBadRequest, gin.H{"error": err.Error()})
return
}
c.JSON(http.StatusCreated, gin.H{"message": "crystal registered", "id": req.ID})
}

// DELETE /v1/skills/crystals/:id — evict a crystal
func (s *ServerV2) handleCrystalEvict(c *gin.Context) {
if s.CrystalCache == nil {
c.JSON(http.StatusServiceUnavailable, gin.H{"error": "crystal cache not enabled"})
return
}
id := c.Param("id")
if !s.CrystalCache.Evict(id) {
c.JSON(http.StatusNotFound, gin.H{"error": "crystal not found: " + id})
return
}
c.JSON(http.StatusOK, gin.H{"message": "evicted", "id": id})
}

// GET /v1/skills/crystals/stats — cache-level telemetry
func (s *ServerV2) handleCrystalStats(c *gin.Context) {
if s.CrystalCache == nil {
c.JSON(http.StatusServiceUnavailable, gin.H{"error": "crystal cache not enabled"})
return
}
c.JSON(http.StatusOK, s.CrystalCache.Stats())
}

// ---------------------------------------------------------------------------
// Curator: Sovereign Model Curation handlers
// ---------------------------------------------------------------------------

// GET /v1/curator/models — all benchmarked models sorted by score
func (s *ServerV2) handleCuratorModels(c *gin.Context) {
if s.Curator == nil {
c.JSON(http.StatusServiceUnavailable, gin.H{"error": "curator not enabled — set ORICLI_CURATOR_ENABLED=true"})
return
}
c.JSON(http.StatusOK, gin.H{"models": s.Curator.All()})
}

// POST /v1/curator/benchmark — trigger a manual benchmark for a model
func (s *ServerV2) handleCuratorBenchmark(c *gin.Context) {
if s.Curator == nil {
c.JSON(http.StatusServiceUnavailable, gin.H{"error": "curator not enabled — set ORICLI_CURATOR_ENABLED=true"})
return
}
var req struct {
Model string `json:"model" binding:"required"`
}
if err := c.ShouldBindJSON(&req); err != nil {
c.JSON(http.StatusBadRequest, gin.H{"error": err.Error()})
return
}
// Run benchmark in background — client polls /v1/curator/models for result
go s.Curator.Benchmark(c.Request.Context(), req.Model)
c.JSON(http.StatusAccepted, gin.H{
"message": "benchmark queued — poll GET /v1/curator/models for result",
"model":   req.Model,
})
}

// GET /v1/curator/recommendations — ranked suggestions for tier reassignment
func (s *ServerV2) handleCuratorRecommendations(c *gin.Context) {
if s.Curator == nil {
c.JSON(http.StatusServiceUnavailable, gin.H{"error": "curator not enabled — set ORICLI_CURATOR_ENABLED=true"})
return
}
recs := s.Curator.Recommend()
if recs == nil {
recs = []curator.Recommendation{}
}
c.JSON(http.StatusOK, gin.H{"recommendations": recs})
}

// ---------------------------------------------------------------------------
// Audit: Self-Audit Loop handlers
// ---------------------------------------------------------------------------

// POST /v1/audit/run — trigger an audit run (async)
func (s *ServerV2) handleAuditRun(c *gin.Context) {
if s.AuditDaemon == nil {
c.JSON(http.StatusServiceUnavailable, gin.H{"error": "audit not enabled — set ORICLI_AUDIT_ENABLED=true"})
return
}
var req struct {
Scope []string `json:"scope"` // e.g. ["pkg/goal", "pkg/pad"] — empty = full pkg/
}
_ = c.ShouldBindJSON(&req)
runID := s.AuditDaemon.Trigger(c.Request.Context(), req.Scope)
c.JSON(http.StatusAccepted, gin.H{
"message": "audit run queued — poll GET /v1/audit/runs/" + runID,
"run_id":  runID,
})
}

// GET /v1/audit/runs — list audit runs
func (s *ServerV2) handleAuditListRuns(c *gin.Context) {
if s.AuditDaemon == nil {
c.JSON(http.StatusServiceUnavailable, gin.H{"error": "audit not enabled"})
return
}
c.JSON(http.StatusOK, gin.H{"runs": s.AuditDaemon.ListRuns()})
}

// GET /v1/audit/runs/:id — get a specific run with findings
func (s *ServerV2) handleAuditGetRun(c *gin.Context) {
if s.AuditDaemon == nil {
c.JSON(http.StatusServiceUnavailable, gin.H{"error": "audit not enabled"})
return
}
run := s.AuditDaemon.GetRun(c.Param("id"))
if run == nil {
c.JSON(http.StatusNotFound, gin.H{"error": "run not found"})
return
}
c.JSON(http.StatusOK, run)
}

// ---------------------------------------------------------------------------
// Phase 8 — Metacognitive Sentience handlers
// ---------------------------------------------------------------------------

// GET /v1/metacog/events?n=50 — return the last N metacognitive events
func (s *ServerV2) handleMetacogEvents(c *gin.Context) {
if s.MetacogLog == nil {
c.JSON(http.StatusServiceUnavailable, gin.H{"error": "metacog not enabled"})
return
}
n := 50
if nStr := c.Query("n"); nStr != "" {
if parsed, err := strconv.Atoi(nStr); err == nil && parsed > 0 {
n = parsed
}
}
events := s.MetacogLog.Recent(n)
c.JSON(http.StatusOK, gin.H{"events": events, "count": len(events)})
}

// GET /v1/metacog/stats — per-type counts + rolling-window recurrence rates
func (s *ServerV2) handleMetacogStats(c *gin.Context) {
if s.MetacogDaemon == nil {
c.JSON(http.StatusServiceUnavailable, gin.H{"error": "metacog not enabled"})
return
}
c.JSON(http.StatusOK, s.MetacogDaemon.Stats())
}

// POST /v1/metacog/scan — trigger an immediate scan cycle, returns window counts
func (s *ServerV2) handleMetacogScan(c *gin.Context) {
if s.MetacogDaemon == nil {
c.JSON(http.StatusServiceUnavailable, gin.H{"error": "metacog not enabled"})
return
}
counts := s.MetacogDaemon.Scan()
result := make(map[string]int)
for t, n := range counts {
result[string(t)] = n
}
c.JSON(http.StatusOK, gin.H{"window_counts": result, "scanned_at": time.Now().Format(time.RFC3339)})
}

// ---------------------------------------------------------------------------
// Phase 9 — Temporal Grounding handlers
// ---------------------------------------------------------------------------

// GET /v1/chronos/entries?stale=true&n=50&topic=<topic>
func (s *ServerV2) handleChronosEntries(c *gin.Context) {
if s.ChronosIndex == nil {
c.JSON(http.StatusServiceUnavailable, gin.H{"error": "chronos not enabled"})
return
}
n := 50
if nStr := c.Query("n"); nStr != "" {
if parsed, err := strconv.Atoi(nStr); err == nil && parsed > 0 {
n = parsed
}
}
staleOnly := c.Query("stale") == "true"
topicFilter := c.Query("topic")

entries := s.ChronosIndex.TopN(n * 4) // fetch extra to allow filtering
var result []*chronos.ChronosEntry
now := time.Now()
for _, e := range entries {
if staleOnly && !e.IsStale(now, chronos.StaleThreshold) {
continue
}
if topicFilter != "" && e.Topic != topicFilter {
continue
}
result = append(result, e)
if len(result) >= n {
break
}
}
c.JSON(http.StatusOK, gin.H{"entries": result, "count": len(result)})
}

// GET /v1/chronos/snapshot — latest persisted snapshot
func (s *ServerV2) handleChronosSnapshot(c *gin.Context) {
if s.ChronosDaemon == nil {
c.JSON(http.StatusServiceUnavailable, gin.H{"error": "chronos not enabled"})
return
}
snap := s.ChronosDaemon.LatestSnapshot()
c.JSON(http.StatusOK, snap)
}

// GET /v1/chronos/changes?n=10 — last N change records
func (s *ServerV2) handleChronosChanges(c *gin.Context) {
if s.ChronosDaemon == nil {
c.JSON(http.StatusServiceUnavailable, gin.H{"error": "chronos not enabled"})
return
}
n := 10
if nStr := c.Query("n"); nStr != "" {
if parsed, err := strconv.Atoi(nStr); err == nil && parsed > 0 {
n = parsed
}
}
records := s.ChronosDaemon.RecentChanges(n)
c.JSON(http.StatusOK, gin.H{"changes": records, "count": len(records)})
}

// POST /v1/chronos/decay-scan — force immediate decay scan
func (s *ServerV2) handleChronosDecayScan(c *gin.Context) {
if s.ChronosDaemon == nil {
c.JSON(http.StatusServiceUnavailable, gin.H{"error": "chronos not enabled"})
return
}
result := s.ChronosDaemon.ForceDecayScan()
c.JSON(http.StatusOK, result)
}

// POST /v1/chronos/snapshot — force snapshot + diff pass
func (s *ServerV2) handleChronosForceSnapshot(c *gin.Context) {
if s.ChronosDaemon == nil {
c.JSON(http.StatusServiceUnavailable, gin.H{"error": "chronos not enabled"})
return
}
diff := s.ChronosDaemon.ForceSnapshot()
c.JSON(http.StatusOK, diff)
}

// ---------------------------------------------------------------------------
// Phase 10 — Active Science handlers
// ---------------------------------------------------------------------------

// GET /v1/science/hypotheses?status=confirmed&n=50
func (s *ServerV2) handleScienceList(c *gin.Context) {
if s.ScienceDaemon == nil {
c.JSON(http.StatusServiceUnavailable, gin.H{"error": "science not enabled"})
return
}
statusFilter := science.HypothesisStatus(c.Query("status"))
list := s.ScienceDaemon.Store().List(statusFilter)
c.JSON(http.StatusOK, gin.H{"hypotheses": list, "count": len(list)})
}

// GET /v1/science/hypotheses/:id
func (s *ServerV2) handleScienceGet(c *gin.Context) {
if s.ScienceDaemon == nil {
c.JSON(http.StatusServiceUnavailable, gin.H{"error": "science not enabled"})
return
}
id := c.Param("id")
h := s.ScienceDaemon.Store().Get(id)
if h == nil {
c.JSON(http.StatusNotFound, gin.H{"error": "hypothesis not found"})
return
}
c.JSON(http.StatusOK, h)
}

// POST /v1/science/test
// Body: { "topic": "...", "fact_summary": "..." }
func (s *ServerV2) handleScienceSubmit(c *gin.Context) {
if s.ScienceDaemon == nil {
c.JSON(http.StatusServiceUnavailable, gin.H{"error": "science not enabled"})
return
}
var body struct {
Topic       string `json:"topic"`
FactSummary string `json:"fact_summary"`
}
if err := c.ShouldBindJSON(&body); err != nil || body.Topic == "" {
c.JSON(http.StatusBadRequest, gin.H{"error": "topic is required"})
return
}
s.ScienceDaemon.Submit(body.Topic, body.FactSummary)
c.JSON(http.StatusAccepted, gin.H{"status": "queued", "topic": body.Topic})
}

// GET /v1/science/stats
func (s *ServerV2) handleScienceStats(c *gin.Context) {
if s.ScienceDaemon == nil {
c.JSON(http.StatusServiceUnavailable, gin.H{"error": "science not enabled"})
return
}
c.JSON(http.StatusOK, s.ScienceDaemon.Stats())
}

// ---------------------------------------------------------------------------
// Phase 15 — Therapeutic Cognition Stack handlers
// ---------------------------------------------------------------------------

func (s *ServerV2) therapyEnabled(c *gin.Context) bool {
if s.TherapySkills == nil {
c.JSON(http.StatusServiceUnavailable, gin.H{"error": "therapy not enabled"})
return false
}
return true
}

// GET /v1/therapy/events?n=50
func (s *ServerV2) handleTherapyEvents(c *gin.Context) {
if !s.therapyEnabled(c) {
return
}
n := 50
if v := c.Query("n"); v != "" {
fmt.Sscanf(v, "%d", &n)
}
events := s.TherapyLog.Recent(n)
c.JSON(http.StatusOK, gin.H{"events": events, "count": len(events)})
}

// POST /v1/therapy/detect — classify distortion in arbitrary text
// Body: { "text": "...", "anomaly_type": "..." }
func (s *ServerV2) handleTherapyDetect(c *gin.Context) {
if !s.therapyEnabled(c) {
return
}
var body struct {
Text        string `json:"text"`
AnomalyType string `json:"anomaly_type"`
}
if err := c.ShouldBindJSON(&body); err != nil || body.Text == "" {
c.JSON(http.StatusBadRequest, gin.H{"error": "text is required"})
return
}
result := s.TherapyDetect.Detect(body.Text, body.AnomalyType)
c.JSON(http.StatusOK, result)
}

// POST /v1/therapy/abc — run REBT B-pass disputation
// Body: { "query": "...", "response": "..." }
func (s *ServerV2) handleTherapyABC(c *gin.Context) {
if !s.therapyEnabled(c) || s.TherapyABC == nil {
c.JSON(http.StatusServiceUnavailable, gin.H{"error": "therapy not enabled"})
return
}
var body struct {
Query    string `json:"query"`
Response string `json:"response"`
}
if err := c.ShouldBindJSON(&body); err != nil || body.Query == "" {
c.JSON(http.StatusBadRequest, gin.H{"error": "query and response are required"})
return
}
report := s.TherapyABC.Audit(body.Query, body.Response)
c.JSON(http.StatusOK, report)
}

// POST /v1/therapy/fast — run sycophancy detection
// Body: { "user_message": "...", "prior_response": "...", "current_draft": "...", "prior_confidence": 0.8 }
func (s *ServerV2) handleTherapyFAST(c *gin.Context) {
if !s.therapyEnabled(c) {
return
}
var body struct {
UserMessage     string  `json:"user_message"`
PriorResponse   string  `json:"prior_response"`
CurrentDraft    string  `json:"current_draft"`
PriorConfidence float64 `json:"prior_confidence"`
}
if err := c.ShouldBindJSON(&body); err != nil {
c.JSON(http.StatusBadRequest, gin.H{"error": "invalid body"})
return
}
inv := s.TherapySkills.FAST(body.UserMessage, body.PriorResponse, body.CurrentDraft, body.PriorConfidence)
c.JSON(http.StatusOK, inv)
}

// POST /v1/therapy/stop — invoke STOP skill
// Body: { "trigger": "...", "original_text": "..." }
func (s *ServerV2) handleTherapySTOP(c *gin.Context) {
if !s.therapyEnabled(c) {
return
}
var body struct {
Trigger      string `json:"trigger"`
OriginalText string `json:"original_text"`
}
if err := c.ShouldBindJSON(&body); err != nil || body.Trigger == "" {
c.JSON(http.StatusBadRequest, gin.H{"error": "trigger is required"})
return
}
inv := s.TherapySkills.STOP(body.Trigger, body.OriginalText)
c.JSON(http.StatusOK, inv)
}

// GET /v1/therapy/stats
func (s *ServerV2) handleTherapyStats(c *gin.Context) {
if !s.therapyEnabled(c) {
return
}
events := s.TherapyLog.Recent(200)
skillCounts := map[string]int{}
distortionCounts := map[string]int{}
reformed := 0
for _, e := range events {
skillCounts[string(e.Skill)]++
if e.Distortion != "" && e.Distortion != therapy.DistortionNone {
distortionCounts[string(e.Distortion)]++
}
if e.Reformed {
reformed++
}
}
c.JSON(http.StatusOK, gin.H{
"total_events":      len(events),
"reformed_count":    reformed,
"skill_counts":      skillCounts,
"distortion_counts": distortionCounts,
})
}

// GET /v1/therapy/formulation — current session case formulation
func (s *ServerV2) handleTherapyFormulation(c *gin.Context) {
if !s.therapyEnabled(c) {
return
}
if s.TherapySupervisor == nil {
c.JSON(http.StatusServiceUnavailable, gin.H{"error": "session supervisor not enabled"})
return
}
f := s.TherapySupervisor.Formulation()
c.JSON(http.StatusOK, f)
}

// POST /v1/therapy/formulation/refresh — force immediate formulation pass
func (s *ServerV2) handleTherapyFormulationRefresh(c *gin.Context) {
if !s.therapyEnabled(c) {
return
}
if s.TherapySupervisor == nil {
c.JSON(http.StatusServiceUnavailable, gin.H{"error": "session supervisor not enabled"})
return
}
f := s.TherapySupervisor.ForceFormulation()
c.JSON(http.StatusOK, f)
}


// GET /v1/therapy/mastery — mastery log statistics by topic class
func (s *ServerV2) handleTherapyMastery(c *gin.Context) {
	if s.TherapyMastery == nil {
		c.JSON(503, gin.H{"error": "mastery log not initialised"})
		return
	}
	topicClass := c.Query("class")
	if topicClass != "" {
		rate := s.TherapyMastery.SuccessRate(topicClass)
		recent := s.TherapyMastery.RecentSuccesses(topicClass, 10)
		c.JSON(200, gin.H{
			"topic_class":  topicClass,
			"success_rate": rate,
			"recent":       recent,
		})
		return
	}
	c.JSON(200, gin.H{"stats": s.TherapyMastery.StatsByClass()})
}

// POST /v1/therapy/helplessness/check — manual helplessness check
// Body: { "query": "...", "draft": "..." }
func (s *ServerV2) handleTherapyHelplessnessCheck(c *gin.Context) {
	if s.TherapyHelpless == nil {
		c.JSON(503, gin.H{"error": "helplessness detector not initialised"})
		return
	}
	var body struct {
		Query string `json:"query"`
		Draft string `json:"draft"`
	}
	if err := c.ShouldBindJSON(&body); err != nil {
		c.JSON(400, gin.H{"error": err.Error()})
		return
	}
	signal := s.TherapyHelpless.Check(body.Query, body.Draft)
	if signal == nil {
		c.JSON(200, gin.H{"detected": false})
		return
	}
	c.JSON(200, gin.H{
		"detected":        true,
		"topic_class":     signal.TopicClass,
		"historical_rate": signal.HistoricalRate,
		"refusal_phrase":  signal.RefusalPhrase,
		"three_p":         signal.Attribution3P,
	})
}

// GET /v1/therapy/helplessness/stats — signal counts from session supervisor
func (s *ServerV2) handleTherapyHelplessnessStats(c *gin.Context) {
	if s.TherapySupervisor == nil {
		c.JSON(503, gin.H{"error": "session supervisor not initialised"})
		return
	}
	f := s.TherapySupervisor.Formulation()
	schemaActive := false
	for _, schema := range f.ActiveSchemas {
		if schema.Schema == therapy.SchemaLearnedHelplessness {
			schemaActive = true
			break
		}
	}
	c.JSON(200, gin.H{
		"helplessness_count": f.HelplessnessCount,
		"schema_active":      schemaActive,
	})
}

// ── Phase 12: Sovereign Compute Bidding handlers ─────────────────────────────

func (s *ServerV2) handleComputeBidStats(c *gin.Context) {
if s.FeedbackLedger == nil {
c.JSON(503, gin.H{"error": "compute bidding not enabled"})
return
}
c.JSON(200, s.FeedbackLedger.Stats())
}

func (s *ServerV2) handleComputeGovernor(c *gin.Context) {
if s.BidGovernor == nil {
c.JSON(503, gin.H{"error": "compute bidding not enabled"})
return
}
n := 20
if nStr := c.Query("n"); nStr != "" {
if parsed, err := strconv.Atoi(nStr); err == nil && parsed > 0 {
n = parsed
}
}
c.JSON(200, gin.H{
"recent_decisions": s.BidGovernor.RecentDecisions(n),
})
}


// ── Phase 17: Dual Process Engine handlers ────────────────────────────────────

func (s *ServerV2) handleProcessStats(c *gin.Context) {
	if s.DualProcessStats == nil {
		c.JSON(503, gin.H{"error": "dual process engine not enabled"})
		return
	}
	c.JSON(200, gin.H{"stats": s.DualProcessStats.Stats()})
}

func (s *ServerV2) handleProcessClassify(c *gin.Context) {
	if s.DualProcessClassifier == nil {
		c.JSON(503, gin.H{"error": "dual process engine not enabled"})
		return
	}
	var req struct {
		Query     string `json:"query"`
		TaskClass string `json:"task_class"`
	}
	if err := c.ShouldBindJSON(&req); err != nil {
		c.JSON(400, gin.H{"error": err.Error()})
		return
	}
	if req.TaskClass == "" {
		req.TaskClass = "general"
	}
	demand := s.DualProcessClassifier.Classify(req.Query, req.TaskClass)
	c.JSON(200, gin.H{
		"tier":          demand.Tier.String(),
		"score":         demand.Score,
		"novelty":       demand.Novelty,
		"abstraction":   demand.Abstraction,
		"multi_step":    demand.MultiStep,
		"contradiction": demand.Contradiction,
		"reasons":       demand.Reasons,
	})
}

// ── Phase 18: Cognitive Load Manager handlers ─────────────────────────────────

func (s *ServerV2) handleCogLoadStats(c *gin.Context) {
	if s.CogLoadStats == nil {
		c.JSON(503, gin.H{"error": "cognitive load manager not enabled"})
		return
	}
	c.JSON(200, s.CogLoadStats.Stats())
}

func (s *ServerV2) handleCogLoadMeasure(c *gin.Context) {
	if s.CogLoadMeter == nil {
		c.JSON(503, gin.H{"error": "cognitive load manager not enabled"})
		return
	}
	var req struct {
		Messages []map[string]string `json:"messages"`
	}
	if err := c.ShouldBindJSON(&req); err != nil {
		c.JSON(400, gin.H{"error": err.Error()})
		return
	}
	profile := s.CogLoadMeter.Measure(req.Messages)
	c.JSON(200, gin.H{
		"tier":         profile.TierLabel,
		"total_load":   profile.TotalLoad,
		"intrinsic":    profile.Intrinsic,
		"extraneous":   profile.Extraneous,
		"germane":      profile.Germane,
		"reasons":      profile.Reasons,
		"message_count": profile.MessageCount,
		"total_chars":   profile.TotalChars,
	})
}

// ─── Phase 19: Rumination Detector handlers ──────────────────────────────────

func (s *ServerV2) handleRuminationStats(c *gin.Context) {
	if s.RuminationStats == nil {
		c.JSON(200, gin.H{"detections": 0, "total_scans": 0, "detection_rate": 0, "interrupt_rate": 0, "message": "Phase 19 not enabled"})
		return
	}
	c.JSON(200, s.RuminationStats.Stats())
}

func (s *ServerV2) handleRuminationDetect(c *gin.Context) {
	if s.RuminationTracker == nil {
		c.JSON(503, gin.H{"error": "Phase 19 not enabled"})
		return
	}
	var body struct {
		Messages []map[string]string `json:"messages"`
	}
	if err := c.ShouldBindJSON(&body); err != nil || len(body.Messages) == 0 {
		c.JSON(400, gin.H{"error": "messages required"})
		return
	}
	signal := s.RuminationTracker.Detect(body.Messages)
	c.JSON(200, signal)
}

// ─── Phase 20: Growth Mindset handlers ───────────────────────────────────────

func (s *ServerV2) handleMindsetStats(c *gin.Context) {
	if s.MindsetStats == nil {
		c.JSON(200, gin.H{"detections": 0, "total_scans": 0, "detection_rate": 0, "message": "Phase 20 not enabled"})
		return
	}
	c.JSON(200, s.MindsetStats.Stats())
}

func (s *ServerV2) handleMindsetVectors(c *gin.Context) {
	if s.MindsetTracker == nil {
		c.JSON(503, gin.H{"error": "Phase 20 not enabled"})
		return
	}
	vectors := s.MindsetTracker.All()
	c.JSON(200, gin.H{"vectors": vectors, "count": len(vectors)})
}

// ─── Phase 21: Hope Circuit handlers ─────────────────────────────────────────

func (s *ServerV2) handleHopeStats(c *gin.Context) {
	if s.AgencyStats == nil {
		c.JSON(200, gin.H{"activations": 0, "total_checks": 0, "activation_rate": 0, "message": "Phase 21 not enabled"})
		return
	}
	c.JSON(200, s.AgencyStats.Stats())
}

func (s *ServerV2) handleHopeActivate(c *gin.Context) {
	if s.HopeCircuit == nil {
		c.JSON(503, gin.H{"error": "Phase 21 not enabled"})
		return
	}
	var body struct {
		TopicClass string `json:"topic_class"`
	}
	if err := c.ShouldBindJSON(&body); err != nil || body.TopicClass == "" {
		c.JSON(400, gin.H{"error": "topic_class required"})
		return
	}
	activation := s.HopeCircuit.Activate(body.TopicClass)
	c.JSON(200, activation)
}

// ─── Phase 22: Social Defeat Recovery handlers ───────────────────────────────

func (s *ServerV2) handleDefeatStats(c *gin.Context) {
	if s.DefeatStats == nil {
		c.JSON(200, gin.H{"detections": 0, "total_scans": 0, "message": "Phase 22 not enabled"})
		return
	}
	c.JSON(200, s.DefeatStats.Stats())
}

func (s *ServerV2) handleDefeatMeasure(c *gin.Context) {
	if s.DefeatMeter == nil {
		c.JSON(503, gin.H{"error": "Phase 22 not enabled"})
		return
	}
	var body struct {
		Messages   []map[string]string `json:"messages"`
		TopicClass string              `json:"topic_class"`
	}
	if err := c.ShouldBindJSON(&body); err != nil || len(body.Messages) == 0 {
		c.JSON(400, gin.H{"error": "messages and topic_class required"})
		return
	}
	if body.TopicClass == "" {
		body.TopicClass = "general"
	}
	pressure := s.DefeatMeter.Measure(body.Messages, body.TopicClass)
	c.JSON(200, pressure)
}

func (s *ServerV2) handleConformityStats(c *gin.Context) {
	if s.ConformityStats == nil {
		c.JSON(503, gin.H{"error": "conformity shield not enabled"})
		return
	}
	c.JSON(200, s.ConformityStats.Stats())
}

func (s *ServerV2) handleIdeoCaptureStats(c *gin.Context) {
	if s.IdeoCaptureStats == nil {
		c.JSON(503, gin.H{"error": "ideological capture detector not enabled"})
		return
	}
	c.JSON(200, s.IdeoCaptureStats.Stats())
}

func (s *ServerV2) handleCoalitionStats(c *gin.Context) {
	if s.CoalitionStats == nil {
		c.JSON(503, gin.H{"error": "coalition bias detector not enabled"})
		return
	}
	c.JSON(200, s.CoalitionStats.Stats())
}

func (s *ServerV2) handleStatusBiasStats(c *gin.Context) {
	if s.StatusBiasStats == nil {
		c.JSON(503, gin.H{"error": "status bias detector not enabled"})
		return
	}
	c.JSON(200, s.StatusBiasStats.Stats())
}

func (s *ServerV2) handleArousalStats(c *gin.Context) {
	if s.ArousalStats == nil {
		c.JSON(503, gin.H{"error": "arousal optimizer not enabled"})
		return
	}
	c.JSON(200, s.ArousalStats.Stats())
}

func (s *ServerV2) handleInterferenceStats(c *gin.Context) {
	if s.InterferenceStats == nil {
		c.JSON(503, gin.H{"error": "interference detector not enabled"})
		return
	}
	c.JSON(200, s.InterferenceStats.Stats())
}

func (s *ServerV2) handleMCTStats(c *gin.Context) {
	if s.MCTStats == nil {
		c.JSON(503, gin.H{"error": "metacognitive therapy not enabled"})
		return
	}
	c.JSON(200, s.MCTStats.Stats())
}

func (s *ServerV2) handleMBTStats(c *gin.Context) {
	if s.MBTStats == nil {
		c.JSON(503, gin.H{"error": "MBT not enabled"})
		return
	}
	c.JSON(200, s.MBTStats.Stats())
}

func (s *ServerV2) handleSchemaStats(c *gin.Context) {
	if s.SchemaStats == nil {
		c.JSON(503, gin.H{"error": "schema therapy not enabled"})
		return
	}
	c.JSON(200, s.SchemaStats.Stats())
}

func (s *ServerV2) handleIPSRTStats(c *gin.Context) {
	if s.IPSRTStats == nil {
		c.JSON(503, gin.H{"error": "IPSRT not enabled"})
		return
	}
	c.JSON(200, s.IPSRTStats)
}

func (s *ServerV2) handleILMStats(c *gin.Context) {
	if s.ILMStats == nil {
		c.JSON(503, gin.H{"error": "ILM not enabled"})
		return
	}
	c.JSON(200, s.ILMStats)
}

func (s *ServerV2) handleIUTStats(c *gin.Context) {
	if s.IUTStats == nil {
		c.JSON(503, gin.H{"error": "IUT not enabled"})
		return
	}
	c.JSON(200, s.IUTStats)
}

func (s *ServerV2) handleUPStats(c *gin.Context) {
	if s.UPStats == nil {
		c.JSON(503, gin.H{"error": "UP not enabled"})
		return
	}
	c.JSON(200, s.UPStats)
}

func (s *ServerV2) handleCBASPStats(c *gin.Context) {
	if s.CBASPStats == nil {
		c.JSON(503, gin.H{"error": "CBASP not enabled"})
		return
	}
	c.JSON(200, s.CBASPStats)
}

func (s *ServerV2) handleMBCTStats(c *gin.Context) {
	if s.MBCTStats == nil {
		c.JSON(503, gin.H{"error": "MBCT not enabled"})
		return
	}
	c.JSON(200, s.MBCTStats)
}

func (s *ServerV2) handlePhaseOrientedStats(c *gin.Context) {
	if s.PhaseStats == nil {
		c.JSON(503, gin.H{"error": "Phase-Oriented not enabled"})
		return
	}
	c.JSON(200, s.PhaseStats)
}

func (s *ServerV2) handlePseudoIdentityStats(c *gin.Context) {
	if s.PseudoIdentityStats == nil {
		c.JSON(503, gin.H{"error": "PseudoIdentity not enabled"})
		return
	}
	c.JSON(200, s.PseudoIdentityStats)
}

func (s *ServerV2) handleThoughtReformStats(c *gin.Context) {
	if s.ThoughtReformStats == nil {
		c.JSON(503, gin.H{"error": "ThoughtReform not enabled"})
		return
	}
	c.JSON(200, s.ThoughtReformStats)
}

func (s *ServerV2) handleApathyStats(c *gin.Context) {
	if s.ApathyStats == nil {
		c.JSON(503, gin.H{"error": "Apathy not enabled"})
		return
	}
	c.JSON(200, s.ApathyStats)
}

func (s *ServerV2) handleLogotherapyStats(c *gin.Context) {
	if s.LogotherapyStats == nil {
		c.JSON(503, gin.H{"error": "Logotherapy not enabled"})
		return
	}
	c.JSON(200, s.LogotherapyStats)
}

func (s *ServerV2) handleStoicStats(c *gin.Context) {
	if s.StoicStats == nil {
		c.JSON(503, gin.H{"error": "Stoic not enabled"})
		return
	}
	c.JSON(200, s.StoicStats)
}

func (s *ServerV2) handleSocraticStats(c *gin.Context) {
	if s.SocraticStats == nil {
		c.JSON(503, gin.H{"error": "Socratic not enabled"})
		return
	}
	c.JSON(200, s.SocraticStats)
}

func (s *ServerV2) handleNarrativeStats(c *gin.Context) {
	if s.NarrativeStats == nil {
		c.JSON(503, gin.H{"error": "Narrative not enabled"})
		return
	}
	c.JSON(200, s.NarrativeStats)
}

func (s *ServerV2) handlePolyvagalStats(c *gin.Context) {
	if s.PolyvagalStats == nil {
		c.JSON(503, gin.H{"error": "Polyvagal not enabled"})
		return
	}
	c.JSON(200, s.PolyvagalStats)
}

func (s *ServerV2) handleDMNStats(c *gin.Context) {
	if s.DMNStats == nil {
		c.JSON(503, gin.H{"error": "DMN not enabled"})
		return
	}
	c.JSON(200, s.DMNStats)
}

func (s *ServerV2) handleInteroceptionStats(c *gin.Context) {
	if s.InteroceptionStats == nil {
		c.JSON(503, gin.H{"error": "Interoception not enabled"})
		return
	}
	c.JSON(200, s.InteroceptionStats)
}

// detectCanvasSkill maps a canvas request message to the appropriate canvas skill name.
// Returns "" if no specific canvas skill applies (generic canvas constitution handles it).
func detectCanvasSkill(msg string) string {
	lower := strings.ToLower(msg)

	// Diagram signals take priority — Mermaid is unambiguous
	diagramSignals := []string{"mermaid", "flowchart", "sequence diagram", "erd", "entity relationship",
		"gantt", "class diagram", "state diagram", "mindmap", "diagram", "visualize", "data flow",
		"architecture diagram", "system diagram"}
	for _, sig := range diagramSignals {
		if strings.Contains(lower, sig) {
			return "canvas_diagram"
		}
	}

	// React/JSX signals
	reactSignals := []string{"react", "jsx", "tsx", "functional component", "component", "hook",
		"usestate", "useeffect", "next.js", "nextjs", "props"}
	for _, sig := range reactSignals {
		if strings.Contains(lower, sig) {
			return "canvas_react"
		}
	}

	// HTML/web signals
	htmlSignals := []string{"html", "landing page", "web page", "webpage", "tailwind", "html page",
		"html form", "html card", "html layout", "html site", "build a page", "create a page"}
	for _, sig := range htmlSignals {
		if strings.Contains(lower, sig) {
			return "canvas_web"
		}
	}

	return ""
}

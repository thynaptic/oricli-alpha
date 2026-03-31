package main

import (
	"context"
	"fmt"
	"log"
	"os"
	"os/signal"
	"path/filepath"
	"strings"
	"syscall"
	"time"

	"github.com/joho/godotenv"
	"github.com/thynaptic/oricli-go/pkg/api"
	"github.com/thynaptic/oricli-go/pkg/bus"
	"github.com/thynaptic/oricli-go/pkg/cognition"
	"github.com/thynaptic/oricli-go/pkg/core/auth"
	"github.com/thynaptic/oricli-go/pkg/core/config"
	"github.com/thynaptic/oricli-go/pkg/core/model"
	"github.com/thynaptic/oricli-go/pkg/core/store/memory"
	"github.com/thynaptic/oricli-go/pkg/kernel"
	"github.com/thynaptic/oricli-go/pkg/node"
	pb "github.com/thynaptic/oricli-go/pkg/connectors/pocketbase"
	"github.com/thynaptic/oricli-go/pkg/scl"
	"github.com/thynaptic/oricli-go/pkg/service"
	"github.com/thynaptic/oricli-go/pkg/tcd"
	"github.com/thynaptic/oricli-go/pkg/forge"
	"github.com/thynaptic/oricli-go/pkg/pad"
	"github.com/thynaptic/oricli-go/pkg/goal"
	"github.com/thynaptic/oricli-go/pkg/sovereign"
	"github.com/thynaptic/oricli-go/pkg/swarm"
	"github.com/thynaptic/oricli-go/pkg/finetune"
	"github.com/thynaptic/oricli-go/pkg/sentinel"
	"github.com/thynaptic/oricli-go/pkg/curator"
	"github.com/thynaptic/oricli-go/pkg/audit"
	"github.com/thynaptic/oricli-go/pkg/metacog"
	"github.com/thynaptic/oricli-go/pkg/chronos"
	"github.com/thynaptic/oricli-go/pkg/science"
	"github.com/thynaptic/oricli-go/pkg/compute"
	"github.com/thynaptic/oricli-go/pkg/dualprocess"
	"github.com/thynaptic/oricli-go/pkg/therapy"
	"github.com/thynaptic/oricli-go/pkg/searchintent"
)

func bootstrapAPIKey(st *memory.MemoryStore) string {
	apiKeyDir := "/home/mike/Mavaia/.oricli"
	apiKeyFile := apiKeyDir + "/api_key"

	if data, err := os.ReadFile(apiKeyFile); err == nil {
		raw := strings.TrimSpace(string(data))
		if len(raw) > 4 {
			log.Printf("[Auth] Loading existing API key from %s", apiKeyFile)
			authSvc := auth.NewService(st)
			if _, err := authSvc.RegisterAPIKey(context.Background(), raw, "local", []string{"*"}, nil); err != nil {
				log.Printf("[Auth] Warning: could not re-seed existing key: %v", err)
			} else {
				return raw
			}
		}
	}
	authSvc := auth.NewService(st)
	raw, _, err := authSvc.GenerateAPIKey(context.Background(), "local", []string{"*"}, nil)
	if err != nil {
		log.Fatalf("[Auth] Failed to generate API key: %v", err)
	}
	os.MkdirAll(apiKeyDir, 0700)
	os.WriteFile(apiKeyFile, []byte(raw), 0600)
	return raw
}

// runGenKeys generates a sovereign key pair, prints the raw keys once, and writes
// them to .oricli/sovereign_keys.env ready to paste into .env.
func runGenKeys() {
	adminKey, execKey, err := sovereign.GenerateKeyPair()
	if err != nil {
		fmt.Fprintf(os.Stderr, "keygen failed: %v\n", err)
		os.Exit(1)
	}

	dir := "/home/mike/Mavaia/.oricli"
	os.MkdirAll(dir, 0700)
	outFile := filepath.Join(dir, "sovereign_keys.env")

	content := fmt.Sprintf(
		"# Sovereign keys — add these to your .env file\n"+
			"# Set these as SOVEREIGN_ADMIN_KEY and SOVEREIGN_EXEC_KEY.\n\n"+
			"SOVEREIGN_ADMIN_KEY=%s\n"+
			"SOVEREIGN_EXEC_KEY=%s\n",
		adminKey, execKey,
	)
	if err := os.WriteFile(outFile, []byte(content), 0600); err != nil {
		fmt.Fprintf(os.Stderr, "could not write %s: %v\n", outFile, err)
		os.Exit(1)
	}

	fmt.Println("=== SOVEREIGN KEY PAIR GENERATED ===")
	fmt.Println()
	fmt.Printf("  ADMIN KEY  (Level 1 — elevated chat):  %s\n", adminKey)
	fmt.Printf("  EXEC  KEY  (Level 2 — system commands): %s\n", execKey)
	fmt.Println()
	fmt.Printf("Keys written to: %s\n", outFile)
	fmt.Println("Add SOVEREIGN_ADMIN_KEY and SOVEREIGN_EXEC_KEY to your .env, then restart the backbone.")
	fmt.Println()
	fmt.Println("⚠  These keys will NOT be shown again. Store them securely NOW.")
}

func main() {
	// --gen-keys: print sovereign key pair and exit (no server startup)
	for _, arg := range os.Args[1:] {
		if arg == "--gen-keys" {
			runGenKeys()
			return
		}
	}

	log.Println("--- BOOTING ORICLI-ALPHA HIVE OS (RING 0 MERGE) ---")

	// 1. Load Environment & Safety Caps
	godotenv.Load(".env")
	apiKeyEnv := os.Getenv("OricliAlpha_Key")
	encKey := os.Getenv("ORICLI_ENCRYPTION_KEY")
	if encKey == "" {
		encKey = "YWJjZGVmZ2hpamtsbW5vcHFyc3R1dnd4eXoxMjM0NTY=" 
	}

	// 2. Core Infrastructure (Bus & Safety)
	swarmBus := bus.NewSwarmBus(5000)
	safetyFramework := kernel.NewSafetyFramework(100.0) // $100.00 Daily Spend Cap
	ghost := service.NewGhostClusterService(apiKeyEnv)
	log.Println("[Boot] Ring 0 Infrastructure and Safety online.")

	// 3. Storage Ring (LMDB + Chronos)
	log.Println("[Boot] Opening Memory Bridge...")
	memPath := "/home/mike/Mavaia/.memory/lmdb"
	mb, err := service.NewMemoryBridge(memPath, encKey)
	if err != nil {
		log.Fatalf("[Kernel Panic] Failed to init MemoryBridge: %v", err)
	}
	log.Println("[Boot] Storage Ring (Chronos-Indexed LMDB) secured.")

	// 4. Standard Services
	st := memory.New()
	genService := service.NewGenerationService()
	apiKey := bootstrapAPIKey(st)
	_ = apiKey

	traceStore := service.NewTraceStore(genService)
	codeMetrics := service.NewCodeMetricsService(nil) // Orchestrator injected later if needed

	// 5. Intelligence Synthesis (Sovereign Engine)
	log.Println("[Boot] Initializing Sovereign Engine...")
	sovEngine := cognition.NewSovereignEngine(genService, swarmBus)
	
	// Initialize GoalService + GoalExecutor (DAG Autonomous Execution)
	goalDataPath := "/home/mike/Mavaia/.oricli/global_objectives.jsonl"
	goalService := service.NewGoalService(goalDataPath)
	goalService.PBClient = pb.NewClientFromEnv()
	goalExecutor := service.NewGoalExecutor(goalService, nil, 30*time.Second) // Router injected below
	log.Println("[Boot] DAG GoalService initialized.")
	reform := service.NewReformDaemon(traceStore, codeMetrics, genService, nil)
	sovEngine.Reform = reform
	go reform.Run(context.Background())
	log.Println("[Boot] Reform Daemon (Self-Modifier) loop engaged.")

	// Initialize Curiosity Daemon (Epistemic Foraging)
	curiosity := service.NewCuriosityDaemon(sovEngine.Graph, sovEngine.VDI, genService, nil)
	sovEngine.Curiosity = curiosity
	go curiosity.Run(context.Background())
	log.Println("[Boot] Curiosity Daemon (Epistemic Foraging) loop engaged.")

	// Initialize World Traveler + Benchmark Gap Detector
	costGovernor := service.NewCostGovernor(nil)
	curiosity.Governor = costGovernor
	genService.Governor = costGovernor // gate RunPod escalation on daily budget
	if os.Getenv("WORLD_TRAVELER_USE_RUNPOD") == "true" {
		curiosity.UseRunPodSynthesis = true
		log.Println("[Boot] RunPod synthesis enabled for CuriosityDaemon.")
	}
	benchGap := service.NewBenchmarkGapDetector(curiosity)
	worldTraveler := service.NewWorldTravelerDaemon(curiosity, costGovernor)
	if worldTraveler != nil {
		go worldTraveler.Run(context.Background())
		// Seed gaps from any prior benchmark results at boot
		go func() {
			n, err := benchGap.IngestLatestResults(context.Background(), "arc_results")
			if err != nil {
				log.Printf("[Boot] BenchmarkGap ingest error: %v", err)
			} else if n > 0 {
				log.Printf("[Boot] BenchmarkGap injected %d gap seeds from last benchmark run.", n)
			}
		}()
		log.Println("[Boot] World Traveler Daemon engaged.")
	} else {
		_ = benchGap // available for manual use; not started automatically
	}
	
	// Initialize VDI (Virtual Device Interface)
	log.Println("[Boot] Initializing Sovereign VDI...")
	if err := sovEngine.VDI.Start(); err != nil {
		log.Printf("[Boot] Warning: Failed to start VDI browser: %v", err)
	}
	sovEngine.VDI.RegisterTools(sovEngine.Toolbox, sovEngine.Vision, sovEngine.Scheduler, sovEngine.Indexer)

	// Initialize MCP Bridge (async — non-blocking, each server has its own 2-min budget)
	go func() {
		log.Println("[Boot] Initializing MCP servers...")
		if err := sovEngine.MCP.StartAll(context.Background()); err != nil {
			log.Printf("[Boot] Warning: Some MCP servers failed to start: %v", err)
		}
		toolCtx, toolCancel := context.WithTimeout(context.Background(), 30*time.Second)
		if err := sovEngine.Toolbox.RegisterMCPTools(toolCtx, sovEngine.MCP); err != nil {
			log.Printf("[Boot] Warning: Failed to bridge MCP tools: %v", err)
		}
		toolCancel()
	}()

	registry := service.NewModuleRegistry("")
	goshMod, _ := service.NewGoshModule("hive_sandbox", "/home/mike/Mavaia")
	orch := service.NewGoOrchestrator(swarmBus, registry)
	precog := service.NewMetacogDaemon("/home/mike/Mavaia", orch, goshMod)
	
	graphService, _ := service.NewGraphService()
	node.NewGraphModule(swarmBus, graphService).Start()
	temporalSvc := service.NewTemporalService(graphService)
	node.NewTemporalModule(swarmBus, temporalSvc).Start()
	node.NewNativeGenerationModule(swarmBus, genService).Start()

	log.Println("[Boot] Sovereign Cognition & Precog active.")

	// 6. BOOT KERNEL (The Master Arbiter)
	k := kernel.NewMicroKernel(mb, ghost, precog, safetyFramework)
	log.Println("[System] Kernel Ring 0 is ACTIVE.")

	// 7. Fleets & Autonomic Services
	scaler := kernel.NewScalingService(swarmBus, k)
	go scaler.Run()
	
	dream := service.NewDreamDaemon(3600, 60, graphService, mb, goshMod, ghost, orch)
	go dream.Run()
	log.Println("[System] Autonomic Scaling and Dream consolidation active.")

	// 8. API Gateway
	personaPath := "/home/mike/Mavaia/scripts/agent_profiles.json"
	personaService, _ := service.NewPersonaService(personaPath)
	agentService := service.NewGoAgentService(orch, genService, personaService, sovEngine)
	monitor := service.NewModuleMonitorService(registry)
	
	apiPort := 8089
	apiServer := api.NewServerV2(config.Load(), st, orch, agentService, monitor, apiPort)
	apiServer.Traces = traceStore
	apiServer.GoalService = goalService

	// Inject WS Hub into Sovereign Engine for real-time broadcasts
	sovEngine.SetWSHub(apiServer.WSHub)
	reform.WSHub = apiServer.WSHub

	// Wire ActionRouter into GoalExecutor (router created inside NewServerV2)
	goalExecutor.Router = apiServer.ActionRouter
	apiServer.GoalExecutor = goalExecutor
	go goalExecutor.Start(context.Background())
	log.Println("[Boot] DAG GoalExecutor autonomous execution loop started.")

	docIngestor := &service.DocumentIngestor{
		MemoryBank:      apiServer.MemoryBank,
		CuriosityDaemon: curiosity,
	}
	apiServer.DocumentIngestor = docIngestor
	log.Println("[Boot] Document Ingestor wired.")

	// Wire The Imprint learning loop into DreamDaemon now that MemoryBank + Constitution exist.
	dream.GenService = genService
	dream.MemoryBank = apiServer.MemoryBank
	dream.Constitution = apiServer.Constitution

	// Seed Oricli's self-knowledge (idempotent — skips if already present).
	go service.SeedIdentity(apiServer.MemoryBank)
	log.Println("[Boot] Identity seed queued.")
	
	// ── SPP: Sovereign Peer Protocol (opt-in via ORICLI_SWARM_ENABLED=true) ──
	if os.Getenv("ORICLI_SWARM_ENABLED") == "true" {
		stateDir := "/home/mike/Mavaia/.oricli"
		nodeIdentity, err := swarm.LoadOrCreateIdentity(stateDir)
		if err != nil {
			log.Printf("[Swarm] identity load error: %v — swarm disabled", err)
		} else {
			constitutionText := apiServer.Constitution.Inject()

			reputation := swarm.NewReputationStore(nil, nil) // LMDB writeback wired after mb.Close() is plumbed
			monitor := swarm.NewSwarmMonitor(nodeIdentity, reputation, nil)

			marketplace := swarm.NewMarketplace(nodeIdentity, nil, nil, nil) // registry injected below

			combinedHandler := swarm.MessageHandler(func(peer *swarm.PeerConn, env swarm.SwarmEnvelope) {
				switch env.Type {
				case swarm.EnvTypeHealthBeacon:
					var beacon swarm.SwarmHealthBeacon
					if b, err := env.UnmarshalPayload(&beacon); b && err == nil {
						monitor.IngestBeacon(beacon)
					}
				default:
					marketplace.HandleEnvelope(peer, env)
				}
			})

			registry := swarm.NewPeerRegistry(nodeIdentity, constitutionText, combinedHandler)
			marketplace.SetRegistry(registry)
			apiServer.SwarmRegistry = registry
			apiServer.SwarmMonitor = monitor

			// P5-1: Jury — multi-node SCAI verification
			juryDeadlineMS := int64(4000)
			resolver := swarm.NewQuorumResolver(swarm.QuorumMajority, juryDeadlineMS)
			juryClient := swarm.NewJuryClient(nodeIdentity, registry, reputation, resolver, nil)
			registry.RegisterAuxHandler(swarm.EnvTypeJuryRequest, func(peer *swarm.PeerConn, env swarm.SwarmEnvelope) {
				juryClient.HandleJuryRequest(peer, env)
			})
			registry.RegisterAuxHandler(swarm.EnvTypeJuryVerdict, func(peer *swarm.PeerConn, env swarm.SwarmEnvelope) {
				juryClient.HandleJuryVerdict(peer, env)
			})
			apiServer.JuryClient = juryClient
			// Wire jury into SCAI auditor if present
			if apiServer.Agent != nil && apiServer.Agent.SovEngine != nil && apiServer.Agent.SovEngine.SCAI != nil {
				apiServer.Agent.SovEngine.SCAI.Jury = juryClient
			}

			// P5-2: Fragment Vote Log — Universal Truth promotion
			voteLog := swarm.NewFragmentVoteLog(apiServer.MemoryBank) // MemoryBank implements swarm.FragmentPromoter
			apiServer.VoteLog = voteLog
			dream.VoteLog = voteLog

			// P5-3: ESI — Epistemic Skill Inheritance
			esiFed := swarm.NewESIFederation(nodeIdentity, registry)
			if apiServer.MemoryBank != nil {
				esiFed.SetIngester(apiServer.MemoryBank)
			}
			registry.RegisterAuxHandler(swarm.EnvTypeSkillTrace, func(peer *swarm.PeerConn, env swarm.SwarmEnvelope) {
				esiFed.HandleSkillTrace(context.Background(), peer, env)
			})
			registry.RegisterAuxHandler(swarm.EnvTypeSkillManifest, func(peer *swarm.PeerConn, env swarm.SwarmEnvelope) {
				esiFed.HandleSkillManifest(peer, env)
			})
			apiServer.ESIFederation = esiFed

			swarmCtx, swarmCancel := context.WithCancel(context.Background())
			_ = swarmCancel

			if seedURL := os.Getenv("THYNAPTIC_PEER_REGISTRY_URL"); seedURL != "" {
				go registry.Bootstrap(swarmCtx, seedURL)
			}
			go monitor.RunBeaconPublisher(swarmCtx, registry, func() int { return 0 })

			log.Printf("[Swarm] Node %s online — SPP+P5 active", nodeIdentity.ShortID())
		}
	}

	// ── SCL-6: Sovereign Cognitive Ledger (opt-in; default enabled) ──
	if os.Getenv("ORICLI_SCL_ENABLED") != "false" {
		pbClient := pb.NewClientFromEnv()
		sclLedger := scl.New(pbClient, nil)
		sclBootCtx, sclBootCancel := context.WithTimeout(context.Background(), 15*time.Second)
		if err := sclLedger.Bootstrap(sclBootCtx); err != nil {
			log.Printf("[SCL] Bootstrap warning: %v — SCL will retry lazily", err)
		}
		sclBootCancel()

		sclWriter := scl.NewLedgerWriter(sclLedger)

		apiServer.SCL = sclLedger
		apiServer.SCLEngine = scl.NewRetrievalEngine(sclLedger)

		if apiServer.DocumentIngestor != nil {
			apiServer.DocumentIngestor.SCL = sclWriter
		}
		if curiosity != nil {
			curiosity.SCL = sclWriter
		}
		if dream != nil {
			dream.SCLLedger = sclLedger
		}

		pbURL := os.Getenv("PB_BASE_URL")
		if pbURL == "" {
			pbURL = "http://127.0.0.1:8090"
		}
		log.Printf("[SCL] Sovereign Cognitive Ledger active — PB: %s", pbURL)
	}

	// ── TCD: Temporal Curriculum Daemon (opt-in via ORICLI_TCD_ENABLED=true) ──
	if os.Getenv("ORICLI_TCD_ENABLED") == "true" {
		tcdPB := pb.NewClientFromEnv()
		tcdManifest := tcd.NewDomainManifest(tcdPB)
		tcdAuditor := tcd.NewFreshnessAuditor(tcdManifest)

		var tcdIngestor *tcd.DomainIngestor
		var tcdWriter tcd.FactWriter
		if apiServer.SCL != nil {
			tcdWriter = scl.NewLedgerWriter(apiServer.SCL)
			tcdIngestor = tcd.NewDomainIngestor(tcdManifest, nil, tcdWriter)
		}

		tcdMaintainer := tcd.NewManifestMaintainer(tcdManifest, nil)

		tcdDetector := tcd.NewGapDetector(tcdManifest, nil)

		tcdDaemon := service.NewTCDDaemon(tcdManifest, tcdAuditor, tcdIngestor, tcdMaintainer, tcdDetector)
		apiServer.TCDDaemon = tcdDaemon
		apiServer.TCDManifest = tcdManifest
		apiServer.TCDGapDetector = tcdDetector
		go tcdDaemon.Run()
		log.Println("[TCD] Temporal Curriculum Daemon starting")
	}

	// ── Forge: JIT Tool Forge (opt-in via ORICLI_FORGE_ENABLED=true) ──────────
	if os.Getenv("ORICLI_FORGE_ENABLED") == "true" {
		forgePB := pb.NewClientFromEnv()
		forgeLib := forge.NewToolLibrary(forgePB, forge.DefaultMaxTools)
		forgeCtx, forgeCancel := context.WithTimeout(context.Background(), 15*time.Second)
		if err := forgeLib.Bootstrap(forgeCtx); err != nil {
			log.Printf("[Forge] library bootstrap warning: %v", err)
		}
		forgeCancel()

		constitution := forge.NewCodeConstitution()

		// Wire GoshModule as the sandbox verifier.
		var verifier *forge.ToolVerifier
		if goshMod != nil {
			verifier = forge.NewToolVerifier(goshMod)
		}

		// Create a standalone ToolService for the forge (registered tools
		// live here and are invocable via the forge endpoints).
		forgeTool := service.NewToolService(orch)

		gate := forge.NewPOCGate(nil, nil, constitution)
		generator := forge.NewToolGenerator(nil, constitution)

		forgeSvc := service.NewToolForgeService(gate, generator, constitution, verifier, forgeLib, forgeTool)
		forgeBootCtx, forgeBootCancel := context.WithTimeout(context.Background(), 30*time.Second)
		forgeSvc.LoadDefaultTools(forgeBootCtx)
		forgeBootCancel()

		apiServer.Forge = forgeSvc
		log.Printf("[Forge] JIT Tool Forge active — library: %d tools, max: %d", forgeLib.Size(), forge.DefaultMaxTools)
	}

	// ── PAD: Parallel Agent Dispatch (opt-in via ORICLI_PAD_ENABLED=true) ────
	if os.Getenv("ORICLI_PAD_ENABLED") == "true" {
		padDecomposer := pad.NewTaskDecomposer(genService, pad.MaxWorkerConcurrency)
		padPool := pad.NewWorkerPool(genService, swarmBus, 0) // 0 → uses DefaultWorkerConcurrency
		padSynthesizer := pad.NewSynthesizer(genService)
		padPBClient := pb.NewClientFromEnv()
		padSessions := pad.NewSessionStore(padPBClient)
		if err := padSessions.Bootstrap(context.Background()); err != nil {
			log.Printf("[PAD] session store bootstrap warning: %v", err)
		}
		apiServer.PAD = service.NewPADService(padDecomposer, padPool, padSynthesizer, padSessions, swarmBus)
		apiServer.PAD.EnableCritique(genService)
		log.Printf("[PAD] Parallel Agent Dispatch active — concurrency: %d/%d",
			apiServer.PAD.MaxWorkers, pad.MaxWorkerConcurrency)
	}

	// ── Goal Engine: Sovereign Goal Engine (opt-in via ORICLI_GOALS_ENABLED=true) ──
	if os.Getenv("ORICLI_GOALS_ENABLED") == "true" {
		goalPBClient := pb.NewClientFromEnv()
		goalStore := goal.NewGoalStore(goalPBClient)
		if err := goalStore.Bootstrap(context.Background()); err != nil {
			log.Printf("[Goals] store bootstrap warning: %v", err)
		}
		goalPlanner := goal.NewGoalPlanner(genService)
		goalAcceptor := goal.NewGoalAcceptor(genService)

		// PADDispatcher adapter — bridges GoalExecutor to PADService
		var padDispatcher goal.PADDispatcher
		if apiServer.PAD != nil {
			padDispatcher = &padServiceAdapter{pad: apiServer.PAD}
		}

		goalExecutor := goal.NewGoalExecutor(padDispatcher, goalStore)
		goalDaemon := service.NewGoalDaemon(goalExecutor, goalAcceptor, goalStore)

		apiServer.GoalDaemon = goalDaemon
		apiServer.GoalStore = goalStore
		apiServer.GoalPlanner = goalPlanner

		go goalDaemon.Run()
		log.Printf("[Goals] Sovereign Goal Engine active — interval: %s", os.Getenv("ORICLI_GOAL_INTERVAL"))
	}

	// ── FineTune: Automated LoRA Orchestrator (opt-in via ORICLI_FINETUNE_ENABLED=true) ──
	if os.Getenv("ORICLI_FINETUNE_ENABLED") == "true" {
		repoRoot, _ := filepath.Abs(".")
		apiServer.FineTune = service.NewFineTuneService(repoRoot)
		log.Printf("[FineTune] Orchestrator active — default GPU: %s", finetune.DefaultGPUType)
	}

	// ── Sentinel: Adversarial pre-flight (opt-in via ORICLI_SENTINEL_ENABLED=true) ──
	if os.Getenv("ORICLI_SENTINEL_ENABLED") == "true" {
		s := sentinel.New(agentService.GenService.DirectOllamaSingle)
		apiServer.Sentinel = s
		// Wire into GoalExecutor so every goal tick is challenged
		if apiServer.GoalDaemon != nil && apiServer.GoalDaemon.Executor != nil {
			apiServer.GoalDaemon.Executor.Sentinel = sentinel.NewGoalAdapter(s)
		}
		log.Printf("[Sentinel] Adversarial Sentinel active — red-teaming goal ticks + manual /v1/sentinel/challenge")
	}

	// ── Crystal Cache: Skill Crystallization (always-on, zero-overhead when empty) ──
	crystalCache := scl.NewCrystalCache()
	apiServer.CrystalCache = crystalCache
	agentService.GenService.CrystalCache = crystalCache
	log.Printf("[Crystal] Skill Crystallization Cache active — LLM bypass ready for high-reputation patterns")

	// ── Curator: Sovereign Model Curation (opt-in via ORICLI_CURATOR_ENABLED=true) ──
	if os.Getenv("ORICLI_CURATOR_ENABLED") == "true" {
		c := curator.New()
		apiServer.Curator = c
		c.StartDaemon(context.Background())
		log.Printf("[Curator] Sovereign Model Curation active — auto-benchmarking Ollama models every 6h")
	}

	// ── Audit: Self-Audit Loop (opt-in via ORICLI_AUDIT_ENABLED=true) ──
	if os.Getenv("ORICLI_AUDIT_ENABLED") == "true" {
		ghToken := os.Getenv("GITHUB_TOKEN")
		botToken := os.Getenv("ORICLI_BOT_GITHUB_TOKEN")
		auditDaemon := audit.NewAuditDaemon(agentService.GenService.DirectOllamaSingle, ghToken, botToken)
		apiServer.AuditDaemon = auditDaemon
		auditDaemon.StartDaemon(context.Background())
		log.Printf("[Audit] Self-Audit Loop active — scanning own source, verifying via Gosh, PRs via oricli-bot")
	}

	// ── Metacog: Phase 8 Metacognitive Sentience (opt-in via ORICLI_METACOG_ENABLED=true) ──
	var metacogEvtLog *metacog.EventLog
	if os.Getenv("ORICLI_METACOG_ENABLED") == "true" {
		metacogEvtLog = metacog.NewEventLog(0)
		detector := metacog.NewDetector(metacogEvtLog)
		agentService.GenService.MetacogDetector = detector
		mcDaemon := metacog.NewMetacogDaemon(metacogEvtLog, apiServer.WSHub)
		apiServer.MetacogDaemon = mcDaemon
		apiServer.MetacogLog = metacogEvtLog
		mcDaemon.StartDaemon(context.Background())
		log.Printf("[Metacog] Sentience layer active — inline loop/hallucination detection + 5-min rolling scan")
	}

	// ── Chronos: Phase 9 Temporal Grounding (opt-in via ORICLI_CHRONOS_ENABLED=true) ──
	if os.Getenv("ORICLI_CHRONOS_ENABLED") == "true" {
		chronosIdx := chronos.NewChronosIndex(0)
		// Hook into MemoryBank — translate MemoryFragment → ObserveInput transparently
		apiServer.MemoryBank.WriteHook = func(frag service.MemoryFragment) {
			chronosIdx.Observe(chronos.ObserveInput{
				ID:         frag.ID,
				Content:    frag.Content,
				Topic:      frag.Topic,
				Source:     frag.Source,
				Importance: frag.Importance,
				Volatility: string(frag.Volatility),
				CreatedAt:  frag.CreatedAt,
			})
		}
		snapDir := "/home/mike/Mavaia/data/chronos/snapshots"
		chDaemon := chronos.NewTemporalGroundingDaemon(
			chronosIdx, snapDir,
			agentService.GenService, // LLMSummarizer interface
			nil,                     // CuriositySeeder — wire below if curiosity daemon exposed
			metacogEvtLog,           // nil-safe: phases 8+9 bridge
		)
		apiServer.ChronosIndex = chronosIdx
		apiServer.ChronosDaemon = chDaemon
		chDaemon.StartDaemon(context.Background())
		log.Printf("[Chronos] Temporal Grounding active — 30-min decay scan + 6-hour snapshot pass")
	}

	// ── Science: Phase 10 Active Science (opt-in via ORICLI_SCIENCE_ENABLED=true) ──
	if os.Getenv("ORICLI_SCIENCE_ENABLED") == "true" {
		sciHypothesisStore := science.NewHypothesisStore("/home/mike/Mavaia/data/science/hypotheses.json")

		// SearXNG adapter — thin closure over the searxng instance from CuriosityDaemon
		var sciSearcher science.SearXNGAdapter
		if curiosity.SearXNG != nil {
			sciSearcher = &scienceSearchAdapter{searcher: curiosity.SearXNG}
		}

		sciTester := science.NewTester(genService, sciSearcher, nil /* PAD adapter optional */)
		sciEngine := science.NewScienceEngine(sciTester, sciHypothesisStore, nil /* knowledge writer optional */, nil /* WSHub optional */)
		sciFormulator := science.NewFormulator(genService)
		sciDaemon := science.NewScienceDaemon(sciFormulator, sciEngine, sciHypothesisStore)

		apiServer.ScienceDaemon = sciDaemon
		sciDaemon.StartDaemon(context.Background())

		// Bridge Phase 9→10: wire ScienceDaemon as Chronos curiosity seeder
		if apiServer.ChronosDaemon != nil {
			apiServer.ChronosDaemon.SetCuriositySeeder(sciDaemon)
		}

		log.Printf("[Science] Phase 10 Active Science online — hypothesis engine + 2h re-test loop")
	}

	// ── Therapy: Phase 15 Therapeutic Cognition Stack (opt-in via ORICLI_THERAPY_ENABLED=true) ──
	if os.Getenv("ORICLI_THERAPY_ENABLED") == "true" {
		therapyGen := &therapyGenAdapter{gen: genService}

		therapyLog := therapy.NewEventLog(200)
		therapyDetect := therapy.NewDistortionDetector(therapyGen)
		therapySkills := therapy.NewSkillRunner(therapyGen, therapyLog)
		therapyABC := therapy.NewABCAuditor(therapyGen)
		therapyChain := therapy.NewChainAnalyzer(therapyGen, 20)
		therapySupervisor := therapy.NewSessionSupervisor(therapyLog, therapyGen, "data/therapy/session_report.json", 10)

		// Wire observer: every TherapyEvent automatically feeds the SessionSupervisor
		therapyLog.SetObserver(therapySupervisor.Ingest)

		apiServer.TherapyLog = therapyLog
		apiServer.TherapyDetect = therapyDetect
		apiServer.TherapySkills = therapySkills
		apiServer.TherapyABC = therapyABC
		apiServer.TherapyChain = therapyChain
		apiServer.TherapySupervisor = therapySupervisor

		// Wire into GenerationService — therapy fires automatically on MetacogDetector HIGH anomaly
		genService.Therapy = &service.TherapyKit{
			Skills: therapySkills,
			Detect: therapyDetect,
			ABC:    therapyABC,
			Chain:  therapyChain,
			Log:    therapyLog,
		}

		// Phase 16: Learned Helplessness Prevention
		masteryLog := therapy.NewMasteryLog(500, "data/therapy/mastery_log.json")
		helplessDetect := therapy.NewHelplessnessDetector(masteryLog, therapySupervisor)
		helplessRetrain := therapy.NewAttributionalRetrainer()

		apiServer.TherapyMastery = masteryLog
		apiServer.TherapyHelpless = helplessDetect
		apiServer.TherapyRetrainer = helplessRetrain

		// Inject into TherapyKit so GenerationService has access
		genService.Therapy.Mastery = masteryLog
		genService.Therapy.Helpless = helplessDetect
		genService.Therapy.Retrainer = helplessRetrain

		// Persist session report on clean shutdown
		go func() {
			sigCh := make(chan os.Signal, 1)
			signal.Notify(sigCh, os.Interrupt)
			<-sigCh
			therapySupervisor.Close()
		}()

		log.Printf("[Therapy] Phase 15+16 Therapeutic Cognition Stack online — distortion detector, DBT skills, REBT auditor, chain analysis, session supervisor, learned helplessness prevention")
	}

	// ── Phase 12: Sovereign Compute Bidding (always on — market routing) ──
	{
		os.MkdirAll("data/compute", 0755)
		feedbackLedger := compute.NewFeedbackLedger("data/compute/feedback.json")
		localBidder := compute.NewLocalBidder("mistral:3b", feedbackLedger)
		mediumBidder := compute.NewMediumBidder("qwen2.5-coder:3b", feedbackLedger)
		// RemoteBidder: available=true only when RUNPOD_API_KEY is set
		remoteBidder := compute.NewRemoteBidder("runpod-vllm", feedbackLedger, os.Getenv("RUNPOD_API_KEY") != "", 2.50)
		bidGovernor := compute.NewBidGovernor(localBidder, mediumBidder, remoteBidder)
		genService.BidGovernor = bidGovernor
		genService.FeedbackLedger = feedbackLedger
		apiServer.BidGovernor = bidGovernor
		apiServer.FeedbackLedger = feedbackLedger
		log.Printf("[Compute] Phase 12 Sovereign Compute Bidding online — local/medium/remote tiers, EMA feedback ledger")
	}

	// ── Phase 17: Dual Process Engine (opt-in via ORICLI_DUALPROCESS_ENABLED=true) ──
	if os.Getenv("ORICLI_DUALPROCESS_ENABLED") == "true" {
		os.MkdirAll("data/dualprocess", 0755)
		dpClassifier := dualprocess.NewProcessClassifier()
		dpAuditor := dualprocess.NewProcessAuditor()
		dpOverride := dualprocess.NewProcessOverride()
		dpStats := dualprocess.NewProcessStats("data/dualprocess/stats.json")
		genService.DualProcess = &service.DualProcessKit{
			Classifier: dpClassifier,
			Auditor:    dpAuditor,
			Override:   dpOverride,
			Stats:      dpStats,
		}
		apiServer.DualProcessClassifier = dpClassifier
		apiServer.DualProcessStats = dpStats
		log.Printf("[DualProcess] Phase 17 Dual Process Engine online — S1/S2 classifier, post-gen auditor, S2 override injection")
	}

	go apiServer.Start()
	log.Printf("[Main] Sovereign Gateway active on port %d", apiPort)

	// 9. Spawn Core Process
	coordProfile := model.AgentProfile{Name: "Kernel_Orchestrator"}
	k.SpawnProcess(coordProfile, 1000000.0, "echo 'Hive OS Orchestrator Online.'")

	log.Println("--- HIVE OS FULL MERGE COMPLETE. SOVEREIGNTY ENGAGED. ---")

	// Wait for termination
	stop := make(chan os.Signal, 1)
	signal.Notify(stop, syscall.SIGINT, syscall.SIGTERM)
	<-stop

	log.Println("[System] Initiating graceful shutdown...")
	sovEngine.VDI.Stop()
	sovEngine.MCP.StopAll()
	mb.Close()
	swarmBus.Stop()
	log.Println("[System] Oricli-Alpha Hive OS Offline.")
}

// ─── PAD → Goal adapter ───────────────────────────────────────────────────────

// padServiceAdapter adapts *service.PADService to goal.PADDispatcher.
type padServiceAdapter struct {
pad *service.PADService
}

func (a *padServiceAdapter) Dispatch(ctx context.Context, query string, maxWorkers int) (goal.PADSession, error) {
session, err := a.pad.Dispatch(ctx, query, maxWorkers)
if err != nil || session == nil {
return goal.PADSession{}, err
}
return goal.PADSession{
ID:        session.ID,
Synthesis: session.Synthesis,
Status:    string(session.Status),
}, nil
}

// ---------------------------------------------------------------------------
// scienceSearchAdapter — wraps *service.SearXNGSearcher to satisfy science.SearXNGAdapter
// ---------------------------------------------------------------------------

type scienceSearchAdapter struct {
searcher *service.SearXNGSearcher
}

func (a *scienceSearchAdapter) Search(query string) ([]string, error) {
results, err := a.searcher.SearchWithURLs(searchintent.SearchQuery{
RawTopic:       query,
FormattedQuery: query,
MaxPasses:      1,
Category:       searchintent.CategoryGeneral,
})
if err != nil {
return nil, err
}
out := make([]string, 0, len(results))
for _, r := range results {
out = append(out, r.Title+": "+r.Snippet)
}
return out, nil
}

// therapyGenAdapter — wraps *service.GenerationService to satisfy therapy.LLMGenerator.
type therapyGenAdapter struct {
gen *service.GenerationService
}

func (a *therapyGenAdapter) Generate(prompt string, params map[string]interface{}) (map[string]interface{}, error) {
resp, err := a.gen.Chat([]map[string]string{
{"role": "user", "content": prompt},
}, params)
if err != nil {
return nil, err
}
return resp, nil
}

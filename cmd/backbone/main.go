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
	"github.com/thynaptic/oricli-go/pkg/service"
	"github.com/thynaptic/oricli-go/pkg/sovereign"
	"github.com/thynaptic/oricli-go/pkg/swarm"
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

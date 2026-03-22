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
	"github.com/thynaptic/oricli-go/pkg/service"
	"github.com/thynaptic/oricli-go/pkg/sovereign"
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
// the bcrypt hashes to .oricli/sovereign_keys.env ready to paste into .env.
func runGenKeys() {
	adminKey, execKey, adminHash, execHash, err := sovereign.GenerateKeyPair()
	if err != nil {
		fmt.Fprintf(os.Stderr, "keygen failed: %v\n", err)
		os.Exit(1)
	}

	dir := "/home/mike/Mavaia/.oricli"
	os.MkdirAll(dir, 0700)
	outFile := filepath.Join(dir, "sovereign_keys.env")

	content := fmt.Sprintf(
		"# Sovereign key hashes — add these to your .env file\n"+
			"# The raw keys below are printed ONCE. Store them securely.\n\n"+
			"SOVEREIGN_ADMIN_KEY_HASH=%s\n"+
			"SOVEREIGN_EXEC_KEY_HASH=%s\n",
		adminHash, execHash,
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
	fmt.Printf("Hashes written to: %s\n", outFile)
	fmt.Println("Add those two SOVEREIGN_*_KEY_HASH lines to your .env, then restart the backbone.")
	fmt.Println()
	fmt.Println("⚠  These raw keys will NOT be shown again. Store them in your password manager NOW.")
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
	
	// Initialize Reform Daemon (The Self-Modifier)
	reform := service.NewReformDaemon(traceStore, codeMetrics, genService, nil)
	sovEngine.Reform = reform
	go reform.Run(context.Background())
	log.Println("[Boot] Reform Daemon (Self-Modifier) loop engaged.")

	// Initialize Curiosity Daemon (Epistemic Foraging)
	curiosity := service.NewCuriosityDaemon(sovEngine.Graph, sovEngine.VDI, genService, nil)
	sovEngine.Curiosity = curiosity
	go curiosity.Run(context.Background())
	log.Println("[Boot] Curiosity Daemon (Epistemic Foraging) loop engaged.")
	
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
	
	// Inject WS Hub into Sovereign Engine for real-time broadcasts
	sovEngine.SetWSHub(apiServer.WSHub)
	reform.WSHub = apiServer.WSHub
	
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

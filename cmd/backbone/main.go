package main

import (
	"context"
	"log"
	"os"
	"os/signal"
	"strings"
	"syscall"

	"github.com/joho/godotenv"
	"github.com/thynaptic/oricli-go/pkg/api"
	"github.com/thynaptic/oricli-go/pkg/bus"
	"github.com/thynaptic/oricli-go/pkg/cognition"
	"github.com/thynaptic/oricli-go/pkg/core/auth"
	"github.com/thynaptic/oricli-go/pkg/core/config"
	"github.com/thynaptic/oricli-go/pkg/core/store/memory"
	"github.com/thynaptic/oricli-go/pkg/kernel"
	"github.com/thynaptic/oricli-go/pkg/node"
	"github.com/thynaptic/oricli-go/pkg/service"
)

const (
	apiKeyFile = "/home/mike/Mavaia/.oricli/api_key"
	apiKeyDir  = "/home/mike/Mavaia/.oricli"
)

func bootstrapAPIKey(st *memory.MemoryStore) string {
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

func main() {
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
	safety := kernel.NewSafetyFramework(100.0) // $100.00 Daily Spend Cap
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

	// 4. Intelligence Synthesis (Sovereign Engine)
	log.Println("[Boot] Initializing Sovereign Engine...")
	sovEngine := cognition.NewSovereignEngine()
	_ = sovEngine // referenced below
	registry := service.NewModuleRegistry("")
	goshMod, _ := service.NewGoshModule("hive_sandbox", "/home/mike/Mavaia")
	orch := service.NewGoOrchestrator(swarmBus, registry)
	precog := service.NewMetacogDaemon("/home/mike/Mavaia", orch, goshMod)
	log.Println("[Boot] Sovereign Cognition & Precog active.")

	// 5. BOOT KERNEL (The Master Arbiter)
	k := kernel.NewMicroKernel(mb, ghost, precog, safety)
	log.Println("[System] Kernel Ring 0 is ACTIVE.")

	// 6. Initialize Standard Services
	st := memory.New()
	genService := service.NewGenerationService()
	apiKey := bootstrapAPIKey(st)
	_ = apiKey
	
	graphService, _ := service.NewGraphService()
	node.NewGraphModule(swarmBus, graphService).Start()
	temporalSvc := service.NewTemporalService(graphService)
	node.NewTemporalModule(swarmBus, temporalSvc).Start()
	node.NewNativeGenerationModule(swarmBus, genService).Start()

	// 7. Fleets & Autonomic Services
	scaler := kernel.NewScalingService(swarmBus, k)
	go scaler.Run()
	
	dream := service.NewDreamDaemon(3600, 60, graphService, mb, goshMod, ghost, orch)
	go dream.Run()
	log.Println("[System] Autonomic Scaling and Dream consolidation active.")

	// 8. API Gateway
	personaPath := "/home/mike/Mavaia/scripts/agent_profiles.json"
	personaService, _ := service.NewPersonaService(personaPath)
	agentService := service.NewGoAgentService(orch, genService, personaService)
	monitor := service.NewModuleMonitorService(registry)
	
	apiPort := 8089
	apiServer := api.NewServerV2(config.Load(), st, orch, agentService, monitor, apiPort)
	go apiServer.Start()
	log.Printf("[Main] Sovereign Gateway active on port %d", apiPort)

	// 9. Spawn Core Process
	coordProfile := service.AgentProfile{Name: "Kernel_Orchestrator"}
	k.SpawnProcess(coordProfile, 1000000.0, "echo 'Hive OS Orchestrator Online.'")

	log.Println("--- HIVE OS FULL MERGE COMPLETE. SOVEREIGNTY ENGAGED. ---")

	// Wait for termination
	stop := make(chan os.Signal, 1)
	signal.Notify(stop, syscall.SIGINT, syscall.SIGTERM)
	<-stop

	log.Println("[System] Initiating graceful shutdown...")
	mb.Close()
	swarmBus.Stop()
	log.Println("[System] Oricli-Alpha Hive OS Offline.")
}

package main

import (
"context"
"log"
"os"
"os/signal"
"strings"
"syscall"

"github.com/thynaptic/oricli-go/pkg/api"
"github.com/thynaptic/oricli-go/pkg/bus"
"github.com/thynaptic/oricli-go/pkg/core/auth"
"github.com/thynaptic/oricli-go/pkg/core/config"
"github.com/thynaptic/oricli-go/pkg/core/store/memory"
"github.com/thynaptic/oricli-go/pkg/node"
"github.com/thynaptic/oricli-go/pkg/service"
)

const (
apiKeyFile = "/home/mike/Mavaia/.oricli/api_key"
apiKeyDir  = "/home/mike/Mavaia/.oricli"
)

// bootstrapAPIKey loads the persisted API key or generates a new one.
// The raw glm.* token is written to apiKeyFile on first run and reused on
// subsequent starts so the key survives service restarts.
func bootstrapAPIKey(st *memory.MemoryStore) string {
	// Try to load existing key
	if data, err := os.ReadFile(apiKeyFile); err == nil {
		raw := strings.TrimSpace(string(data))
		if len(raw) > 4 {
			log.Printf("[Auth] Loading existing API key from %s", apiKeyFile)
			authSvc := auth.NewService(st)
			if _, err := authSvc.RegisterAPIKey(context.Background(), raw, "local", []string{"*"}, nil); err != nil {
				log.Printf("[Auth] Warning: could not re-seed existing key: %v — generating new key", err)
			} else {
				return raw
			}
		}
	}

	// Generate a fresh key
	authSvc := auth.NewService(st)
	raw, _, err := authSvc.GenerateAPIKey(context.Background(), "local", []string{"*"}, nil)
	if err != nil {
		log.Fatalf("[Auth] Failed to generate API key: %v", err)
	}

	// Persist to file
	if err := os.MkdirAll(apiKeyDir, 0700); err != nil {
		log.Fatalf("[Auth] Cannot create key dir: %v", err)
	}
	if err := os.WriteFile(apiKeyFile, []byte(raw), 0600); err != nil {
		log.Fatalf("[Auth] Cannot write key file: %v", err)
	}

	log.Printf("[Auth] New API key generated and stored at %s", apiKeyFile)
	return raw
}


func main() {
log.Println("Starting Oricli-Alpha Pure-Go Backbone v2.0...")

// 1. Initialize Swarm Bus
swarmBus := bus.NewSwarmBus(5000)

// 2. Initialize Module Registry
registry := service.NewModuleRegistry("")

// 3. Initialize Core Services
cfg := config.Load()
st := memory.New()
genService := service.NewGenerationService()

// 3a. Bootstrap API key (generate or load from file, seed into store)
apiKey := bootstrapAPIKey(st)
log.Printf("[Auth] Sovereign Gateway secured. Key prefix: %.12s...", apiKey)

graphService, _ := service.NewGraphService()
node.NewGraphModule(swarmBus, graphService).Start()
temporalSvc := service.NewTemporalService(graphService)
node.NewTemporalModule(swarmBus, temporalSvc).Start()

// Register Native Go Modules
node.NewNativeGenerationModule(swarmBus, genService).Start()

// 4. Initialize RAG System
ragSvc, err := service.NewRagService()
if err == nil {
node.NewRagModule(swarmBus, ragSvc).Start()
log.Println("[Hive] Go-Native RAG System active.")
}

// 5. Initialize Orchestration & Intelligence
orch := service.NewGoOrchestrator(swarmBus, registry)
personaPath := "/home/mike/Mavaia/scripts/agent_profiles.json"
personaService, _ := service.NewPersonaService(personaPath)
agentService := service.NewGoAgentService(orch, genService, personaService)

// 6. Initialize Reasoning Strategies
reasoningStratSvc := service.NewReasoningStrategyService(genService)
node.NewReasoningStrategiesModule(swarmBus, reasoningStratSvc).Start()

// ARC-AGI Native Solver
arcSolverSvc := service.NewARCSolverService(genService, orch)
node.NewARCSwarmModule(swarmBus, arcSolverSvc).Start()

// 7. Initialize Tools & Utilities
toolService := service.NewToolService(orch)
node.NewToolModule(swarmBus, toolService).Start()
webService := service.NewWebFetchService()
node.NewWebModule(swarmBus, webService).Start()

// 8. Initialize Web Ingestion (Native)
if ragSvc != nil {
webIngestSvc := service.NewWebIngestionService(webService, ragSvc)
node.NewWebIngestionModule(swarmBus, webIngestSvc).Start()
} else {
log.Println("[Hive] Warning: Web Ingestion disabled (RAG system not available)")
}

// 9. Initialize Vision (Native)
node.NewVisionModule(swarmBus, genService).Start()

// 10. Initialize System Introspection
monitor := service.NewModuleMonitorService(registry)

// 11. Initialize Goal & Fleet Coordination
goalSvc := service.NewGoalService("/home/mike/Mavaia/.oricli/goals.json")
node.NewGoalModule(swarmBus, goalSvc).Start()

agentCoord := service.NewAgentCoordinator(swarmBus)
node.NewAgentModule(swarmBus, agentCoord).Start()

node.NewResearchAgentModule(swarmBus, genService, webService, ragSvc).Start()

// 12. Start Hardened API Gateway
apiPort := 8089
apiServer := api.NewServerV2(cfg, st, orch, agentService, monitor, apiPort)

go func() {
if err := apiServer.Start(); err != nil {
log.Fatalf("Failed to start API Gateway: %v", err)
}
}()
log.Printf("[Main] Sovereign Gateway active on port %d", apiPort)
_ = apiKey // referenced for logging above; key lives in store

// 13. Start Autonomic Daemons
root := "/home/mike/Mavaia"
go service.NewJITDaemon(root, orch).Run()
go service.NewMetacogDaemon(root, orch).Run()
go service.NewToolDaemon(root).Run()

// Wait for termination
stop := make(chan os.Signal, 1)
signal.Notify(stop, syscall.SIGINT, syscall.SIGTERM)
<-stop

log.Println("Shutting down Oricli-Alpha Backbone...")
swarmBus.Stop()
}

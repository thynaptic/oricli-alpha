package main

import (
	"log"
	"os"
	"os/signal"
	"syscall"

	"github.com/thynaptic/oricli-go/pkg/bus"
	"github.com/thynaptic/oricli-go/pkg/node"
	"github.com/thynaptic/oricli-go/pkg/service"
	"github.com/thynaptic/oricli-go/pkg/api"
	"github.com/thynaptic/oricli-go/pkg/core/config"
	"github.com/thynaptic/oricli-go/pkg/core/store/memory"
)

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
	personaPath := "/home/mike/Mavaia/scripts/agent_profiles.json" // Update to new path if needed
	personaService, _ := service.NewPersonaService(personaPath)
	agentService := service.NewGoAgentService(orch, genService, personaService)

	// 6. Initialize Reasoning Strategies
	reasoningStratSvc := service.NewReasoningStrategyService(genService)
	node.NewReasoningStrategiesModule(swarmBus, reasoningStratSvc).Start()

	// 7. Initialize Tools & Utilities
	toolService := service.NewToolService(orch)
	node.NewToolModule(swarmBus, toolService).Start()
	webService := service.NewWebFetchService()
	node.NewWebModule(swarmBus, webService).Start()

	// 8. Initialize System Introspection
	monitor := service.NewModuleMonitorService(registry)
	
	// 9. Start Hardened API Gateway
	apiPort := 8089
	apiServer := api.NewServerV2(cfg, st, orch, agentService, monitor, apiPort)
	
	go func() {
		if err := apiServer.Start(); err != nil {
			log.Fatalf("Failed to start API Gateway: %v", err)
		}
	}()
	log.Printf("[Main] Sovereign Gateway active on port %d", apiPort)

	// 10. Start Autonomic Daemons
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

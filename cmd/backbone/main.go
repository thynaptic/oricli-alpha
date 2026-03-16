package main

import (
	"context"
	"log"
	"os"
	"os/signal"
	"syscall"
	"time"

	"github.com/thynaptic/oricli-go/pkg/api"
	"github.com/thynaptic/oricli-go/pkg/bus"
	"github.com/thynaptic/oricli-go/pkg/node"
	"github.com/thynaptic/oricli-go/pkg/service"
	pb "github.com/thynaptic/oricli-go/pkg/rpc"
	"google.golang.org/grpc"
	"google.golang.org/grpc/credentials/insecure"
)

func main() {
	log.Println("Starting Oricli-Alpha Go Backbone...")

	// 1. Initialize Swarm Bus
	swarmBus := bus.NewSwarmBus(1000)

	// 2. Connect to Python Worker to fetch manifest
	workerAddr := os.Getenv("ORICLI_WORKER_ADDR")
	if workerAddr == "" {
		workerAddr = "localhost:50051"
	}

	conn, err := grpc.NewClient(workerAddr, grpc.WithTransportCredentials(insecure.NewCredentials()))
	if err != nil {
		log.Fatalf("Failed to connect to Python worker: %v", err)
	}
	defer conn.Close()

	client := pb.NewModuleServiceClient(conn)
	
	// Wait for worker to be ready
	log.Println("Waiting for Python worker to be ready...")
	for i := 0; i < 30; i++ {
		ctx, cancel := context.WithTimeout(context.Background(), time.Second)
		_, err := client.HealthCheck(ctx, &pb.HealthCheckRequest{})
		cancel()
		if err == nil {
			log.Println("Python worker is ready.")
			break
		}
		time.Sleep(1 * time.Second)
	}

	// 3. Fetch Manifest
	ctx, cancel := context.WithTimeout(context.Background(), 120*time.Second)
	defer cancel()
	manifest, err := client.GetManifest(ctx, &pb.ManifestRequest{})
	if err != nil {
		log.Fatalf("Failed to fetch manifest: %v", err)
	}

	log.Printf("Discovered %d modules from Python worker.", len(manifest.Modules))

	// 4. Initialize Core Services
	profilePath := os.Getenv("ORICLI_PROFILES_PATH")
	if profilePath == "" {
		profilePath = "/home/mike/Mavaia/oricli_core/data/agent_profiles.json"
	}
	profileService := service.NewAgentProfileService(profilePath)
	log.Printf("Loaded %d agent profiles.", len(profileService.ListProfiles()))

	monitor := service.NewMonitorService()
	monitor.Start(func() {
		log.Println("[Monitor] Running scheduled health checks...")
		start := time.Now()
		ctx, cancel := context.WithTimeout(context.Background(), 2*time.Second)
		resp, err := client.HealthCheck(ctx, &pb.HealthCheckRequest{})
		cancel()
		latency := float64(time.Since(start).Milliseconds())
		
		if err != nil {
			monitor.UpdateStatus("python_worker", service.StateOffline, latency, err.Error())
		} else if !resp.Ready {
			monitor.UpdateStatus("python_worker", service.StateDegraded, latency, resp.StatusMessage)
		} else {
			monitor.UpdateStatus("python_worker", service.StateOnline, latency, "")
		}
	})

	// 5. Start Orchestrator (Needed by other services)
	orch := service.NewGoOrchestrator(swarmBus)
	log.Println("Go Orchestrator started. Hive is now active.")

	// 6. Spawn Go Sidecars for each module
	nodes := make([]*node.GoHiveNode, 0)
	for _, m := range manifest.Modules {
		n, err := node.NewGoHiveNode(m.Name, m.Operations, workerAddr, swarmBus, profileService, monitor)
		if err != nil {
			log.Printf("Warning: Failed to create sidecar for %s: %v", m.Name, err)
			continue
		}
		n.Start()
		nodes = append(nodes, n)
	}

	log.Printf("Spawned %d Go sidecars. Total Goroutines: ~%d", len(nodes), len(nodes)+30)

	// 7. Start Native Go Modules
	genService := service.NewGenerationService()
	node.NewNativeGenerationModule(swarmBus, genService).Start()

	lmdbPath := "/home/mike/Mavaia/.oricli/memory.lmdb"
	encKey := os.Getenv("MAVAIA_MEMORY_ENCRYPTION_KEY")
	var memoryBridge *service.MemoryBridge
	if encKey != "" {
		memoryBridge, err = service.NewMemoryBridge(lmdbPath, encKey)
		if err == nil {
			node.NewMemoryModule(swarmBus, memoryBridge).Start()
		}
	}

	webService := service.NewWebFetchService()
	node.NewWebModule(swarmBus, webService).Start()

	graphService, err := service.NewGraphService()
	if err == nil {
		node.NewGraphModule(swarmBus, graphService).Start()
	}

	codeAnalyzer := service.NewCodeAnalyzer()
	sandboxService := service.NewSandboxService("")
	node.NewCodeModule(swarmBus, codeAnalyzer, sandboxService).Start()

	node.NewZebraModule(swarmBus, genService).Start()
	node.NewSpatialModule(swarmBus, genService).Start()

	// Initialize ARC Solver
	arcSolver := service.NewARCSolver()
	node.NewARCModule(swarmBus, arcSolver).Start()

	complexityService := service.NewComplexityService()
	node.NewComplexityModule(swarmBus, complexityService).Start()

	safetyService := service.NewSafetyService()
	node.NewSafetyModule(swarmBus, safetyService).Start()

	holisticSafety := service.NewHolisticSafetyService()
	node.NewHolisticSafetyModule(swarmBus, holisticSafety).Start()

	proSafety := service.NewProfessionalSafetyService()
	codeSafety := service.NewCodeSafetyService()
	node.NewComprehensiveSafetyModule(swarmBus, proSafety, codeSafety).Start()

	goalPath := "/home/mike/Mavaia/oricli_core/data/global_objectives.jsonl"
	goalService := service.NewGoalService(goalPath)
	node.NewGoalModule(swarmBus, goalService).Start()

	agentCoordinator := service.NewAgentCoordinator(swarmBus)
	node.NewAgentModule(swarmBus, agentCoordinator).Start()

	// Adaptation & Routing
	adaptSvc := service.NewAdaptationService()
	routerSvc := service.NewAdapterRouterService(orch)
	node.NewAdaptationModule(swarmBus, adaptSvc, routerSvc).Start()

	// Initialize Subconscious & NLP
	subconsciousPath := "/home/mike/Mavaia/oricli_core/data/subconscious_state.json"
	subconsciousSvc := service.NewSubconsciousService(subconsciousPath)
	node.NewSubconsciousModule(swarmBus, subconsciousSvc).Start()

	nlpSvc := service.NewNLPService()
	node.NewNLPModule(swarmBus, nlpSvc).Start()

	// Initialize Memory Graph & Semantic Engine
	memGraphSvc := service.NewMemoryGraphService(graphService, memoryBridge)
	node.NewMemoryGraphModule(swarmBus, memGraphSvc).Start()
	node.NewSemanticModule(swarmBus, nlpSvc, subconsciousSvc).Start()

	// Initialize Reasoning Services
	cotSvc := service.NewCoTReasoningService(genService)
	totSvc := service.NewToTReasoningService(genService)
	mctsSvc := service.NewMCTSReasoningService(genService)
	node.NewReasoningModule(swarmBus, cotSvc, totSvc, mctsSvc).Start()

	// 8. Start Agent Loop
	personaPath := "/home/mike/Mavaia/oricli_core/brain/modules/personality_config.json"
	personaService, _ := service.NewPersonaService(personaPath)
	agentService := service.NewGoAgentService(orch, genService, personaService)

	// 9. Start Tool Master
	toolService := service.NewToolService(orch)
	node.NewToolModule(swarmBus, toolService).Start()

	// Initialize Planner
	plannerSvc := service.NewPlannerService(orch, toolService)
	node.NewPlannerModule(swarmBus, plannerSvc).Start()

	// Register Native Tools
	toolService.RegisterTool(service.Tool{Name: "memory_search", ModuleName: "memory_bridge", Operation: "vector_search"})
	toolService.RegisterTool(service.Tool{Name: "web_fetch", ModuleName: "web_fetch_service", Operation: "fetch_url"})
	toolService.RegisterTool(service.Tool{Name: "graph_query", ModuleName: "neo4j_service", Operation: "execute_query"})
	toolService.RegisterTool(service.Tool{Name: "code_analyze", ModuleName: "code_service", Operation: "analyze_code"})

	apiPort := 8089
	apiServer := api.NewServer(orch, agentService, monitor, apiPort)
	go func() {
		if err := apiServer.Start(); err != nil {
			log.Fatalf("Failed to start API Gateway: %v", err)
		}
	}()
	log.Printf("API Gateway active on port %d", apiPort)

	// Wait for termination
	stop := make(chan os.Signal, 1)
	signal.Notify(stop, syscall.SIGINT, syscall.SIGTERM)
	<-stop

	log.Println("Shutting down Oricli-Go Backbone...")
	for _, n := range nodes {
		n.Stop()
	}
	swarmBus.Stop()
}

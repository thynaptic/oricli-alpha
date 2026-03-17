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
	registry := service.NewModuleRegistry("/home/mike/Mavaia/oricli_core/brain/modules")
	metrics := service.NewMetricsCollector()

	profilePath := os.Getenv("ORICLI_PROFILES_PATH")
	if profilePath == "" {
		profilePath = "/home/mike/Mavaia/oricli_core/data/agent_profiles.json"
	}
	profileService := service.NewAgentProfileService(profilePath)
	log.Printf("Loaded %d agent profiles.", len(profileService.ListProfiles()))

	monitor := service.NewModuleMonitorService(registry)
	healthSvc := service.NewModuleHealthDiagnosticsService(registry, monitor)
	classifier := service.NewDegradedModeClassifier(registry)
	recovery := service.NewModuleRecoveryService(registry, monitor)
	availability := service.NewModuleAvailabilityManager(registry, monitor, recovery, classifier)
	availability.Start(context.Background())

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

	// Register Python modules in the registry
	for _, m := range manifest.Modules {
		registry.RegisterNativeModule(m.Name, &service.PythonModuleProxy{
			ModuleMetadata: service.ModuleMetadata{
				Name:       m.Name,
				Operations: m.Operations,
			},
			Client: client,
		})
	}

	// 5. Start Orchestrator (Needed by other services)
	orch := service.NewGoOrchestrator(swarmBus, registry)
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
	traceStore := service.NewTraceStore(genService)
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

	// Initialize Memory Pipeline (Context & Processor)
	if memoryBridge != nil {
		memPipelineSvc := service.NewMemoryPipelineService(memoryBridge)
		node.NewConversationalMemoryModule(swarmBus, memPipelineSvc).Start()
		node.NewMemoryProcessorModule(swarmBus, memPipelineSvc).Start()
	}

	webService := service.NewWebFetchService()
	node.NewWebModule(swarmBus, webService).Start()

	graphService, err := service.NewGraphService()
	if err == nil {
		node.NewGraphModule(swarmBus, graphService).Start()
		node.NewCogsModule(swarmBus, graphService).Start()
	}

	codeAnalyzer := service.NewCodeAnalyzer()
	sandboxService := service.NewSandboxService("")
	node.NewCodeModule(swarmBus, codeAnalyzer, sandboxService).Start()

	// Initialize the massive Code Engine (replacing 107k lines of Python)
	codeEngine := service.NewCodeEngineService(genService, codeAnalyzer)
	node.NewReasoningCodeModule(swarmBus, codeEngine).Start()
	node.NewCodeToCodeModule(swarmBus, codeEngine).Start()

	// Initialize the Real-Time Code Suite
	realtimeCodeService := service.NewRealtimeCodeService(genService)
	node.NewReasoningCodeCompletionModule(swarmBus, realtimeCodeService).Start()
	node.NewProgramBehaviorModule(swarmBus, realtimeCodeService).Start()
	node.NewTestGenerationModule(swarmBus, realtimeCodeService).Start()

	node.NewZebraModule(swarmBus, genService).Start()
	node.NewSpatialModule(swarmBus, genService).Start()

	// Initialize Game Theory Solver
	gameTheoryService := service.NewGameTheoryService()
	node.NewGameTheoryModule(swarmBus, gameTheoryService).Start()

	// Initialize Symbolic Solver
	symbolicManager := service.NewSymbolicSolverManager(orch)
	node.NewSymbolicModule(swarmBus, symbolicManager).Start()

	// Initialize ARC Solver
	arcSolverSvc := service.NewARCSolverService(genService, orch)
	node.NewARCSwarmModule(swarmBus, arcSolverSvc).Start()

	complexityService := service.NewComplexityService()
	node.NewComplexityModule(swarmBus, complexityService).Start()

	safetyService := service.NewSafetyService(genService)
	node.NewSafetyModule(swarmBus, safetyService).Start()

	holisticSafety := service.NewHolisticSafetyService()
	node.NewHolisticSafetyModule(swarmBus, holisticSafety).Start()

	proSafety := service.NewProfessionalSafetyService()
	codeSafety := service.NewCodeSafetyService()
	node.NewComprehensiveSafetyModule(swarmBus, proSafety, codeSafety).Start()

	// Initialize High-Speed Meta Evaluator
	metaEvaluator := service.NewMetaEvaluatorService(genService)
	node.NewMetaEvaluatorModule(swarmBus, metaEvaluator).Start()

	// Initialize Fast Embedding Engine
	embeddingEngine := service.NewEmbeddingEngineService(genService)
	node.NewEmbeddingsModule(swarmBus, embeddingEngine).Start()
	node.NewConceptEmbeddingsModule(swarmBus, embeddingEngine).Start()
	node.NewPhraseEmbeddingsModule(swarmBus, embeddingEngine).Start()

	// Initialize Voice Engine & Persona Routing
	voiceEngine := service.NewVoiceEngineService(genService)
	node.NewVoiceEngineModule(swarmBus, voiceEngine).Start()

	// Initialize Text Generation Wrappers
	genWrappers := service.NewGenerationWrappersService(genService, voiceEngine)
	node.NewTextGenerationEngineModule(swarmBus, genWrappers).Start()
	node.NewCoreResponseModule(swarmBus, genWrappers).Start()

	// Initialize State & Memory Tools
	stateMemoryTools := service.NewStateMemoryToolsService(memoryBridge)
	node.NewStateManagerModule(swarmBus, stateMemoryTools).Start()
	node.NewMemoryToolModule(swarmBus, stateMemoryTools).Start()

	goalPath := "/home/mike/Mavaia/oricli_core/data/global_objectives.jsonl"
	goalService := service.NewGoalService(goalPath)
	node.NewGoalModule(swarmBus, goalService).Start()

	agentCoordinator := service.NewAgentCoordinator(swarmBus)
	node.NewAgentModule(swarmBus, agentCoordinator).Start()

	// Initialize Native Swarm Agents
	swarmAgentSvc := service.NewSwarmAgentService(genService)
	node.NewRetrieverAgentModule(swarmBus, swarmAgentSvc).Start()
	node.NewVerifierAgentModule(swarmBus, swarmAgentSvc).Start()
	node.NewCreativeWritingModule(swarmBus, swarmAgentSvc).Start()

	// Initialize Agent Pipeline (orchestrates all agents)
	agentPipelineSvc := service.NewAgentPipelineService(orch, genService)
	node.NewAgentPipelineModule(swarmBus, agentPipelineSvc).Start()

	// Initialize Native MCTS & ToT
	mctsService := service.NewMCTSReasoningService(genService)
	totService := service.NewToTReasoningService(genService)
	node.NewTreeReasoningModule(swarmBus, mctsService, totService).Start()

	// Adaptation & Routing
	adaptSvc := service.NewAdaptationService()
	routerSvc := service.NewAdapterRouterService(orch)
	node.NewAdaptationModule(swarmBus, adaptSvc, routerSvc).Start()

	// Initialize Subconscious & NLP
	subconsciousPath := "/home/mike/Mavaia/oricli_core/data/subconscious_state.json"
	subconsciousSvc := service.NewSubconsciousService(subconsciousPath)
	node.NewSubconsciousModule(swarmBus, subconsciousSvc).Start()

	// Initialize Rules & Skills
	rulesDir := "/home/mike/Mavaia/oricli_core/rules"
	rulesEngine := service.NewRulesEngine(rulesDir)
	skillsDir := "/home/mike/Mavaia/oricli_core/skills"
	skillManager := service.NewSkillManager(skillsDir)

	// Initialize Budget
	budgetPath := "/home/mike/Mavaia/oricli_core/data/compute_budget.json"
	budgetManager := service.NewBudgetManager(budgetPath)

	// Initialize Insights
	insightPath := "/home/mike/Mavaia/oricli_core/data/synthetic_insights.jsonl"
	insightService := service.NewInsightService(insightPath)

	// Initialize Precog
	precogService := service.NewPrecogService(600)

	// Initialize Absorption
	absorptionPath := "/home/mike/Mavaia/oricli_core/data/jit_absorption.jsonl"
	absorptionService := service.NewAbsorptionService(absorptionPath)

	nlpSvc := service.NewNLPService()
	node.NewNLPModule(swarmBus, nlpSvc).Start()

	// Initialize Memory Graph & Semantic Engine
	memGraphSvc := service.NewMemoryGraphService(graphService, memoryBridge)
	
	// Initialize World Knowledge
	knowledgeSvc := service.NewWorldKnowledgeService("", graphService, memoryBridge, genService)

	node.NewMemoryGraphModule(swarmBus, memGraphSvc).Start()
	node.NewSemanticModule(swarmBus, nlpSvc, subconsciousSvc).Start()

	// Initialize Reasoning Services

	// Initialize Step Safety Filter
	stepSafetySvc := service.NewStepSafetyFilterService(safetyService)
	node.NewStepSafetyModule(swarmBus, stepSafetySvc).Start()

	// Initialize Intent Detection
	intentSvc := service.NewIntentService()
	node.NewIntentModule(swarmBus, intentSvc).Start()

	// Initialize Reasoning Strategies
	reasoningStratSvc := service.NewReasoningStrategyService(genService)
	node.NewReasoningStrategiesModule(swarmBus, reasoningStratSvc).Start()

	// Initialize Swarm Consensus
	consensusSvc := service.NewSwarmConsensusService(genService)
	node.NewConsensusModule(swarmBus, consensusSvc).Start()

	// Initialize Orchestrator Module
	node.NewOrchestratorModule(swarmBus, orch).Start()

	// Initialize Conversational Module
	convSvc := service.NewConversationalService()
	node.NewConversationalModule(swarmBus, convSvc).Start()

	// 8. Start Agent Loop
	personaPath := "/home/mike/Mavaia/oricli_core/brain/modules/personality_config.json"
	personaService, _ := service.NewPersonaService(personaPath)
	agentService := service.NewGoAgentService(orch, genService, personaService)

	// 9. Start Tool Master
	toolService := service.NewToolService(orch)
	node.NewToolModule(swarmBus, toolService).Start()

	// Initialize Pipeline
	pipelineSvc := service.NewMultiAgentPipelineService(orch)

	// Initialize Reasoning Orchestrator
	reasoningOrch := service.NewCognitiveOrchestrator(orch)

	// Initialize Code Review
	codeReviewSvc := service.NewCodeReviewService(orch)

	// Initialize Code Metrics
	codeMetricsSvc := service.NewCodeMetricsService(orch)

	// Initialize Security Analysis
	securitySvc := service.NewSecurityAnalysisService(orch)

	// Initialize Documentation Generator
	docGenSvc := service.NewDocumentationGeneratorService(orch)

	// Initialize Document Service
	documentSvc := service.NewDocumentService(genService)

	// Initialize Semantic Understanding
	semanticUnderSvc := service.NewSemanticUnderstandingService(orch)

	// Initialize Thought to Text
	thoughtToTextSvc := service.NewThoughtToTextService(orch)

	// Initialize Emotional Inference
	emotionSvc := service.NewEmotionalInferenceService()

	// Initialize Refactoring
	refactoringSvc := service.NewRefactoringService(orch)

	// Initialize Codebase Search
	searchSvc := service.NewCodebaseSearchService(orch)

	// Initialize Code Explanation
	explainSvc := service.NewCodeExplanationService(orch)

	// Initialize Migration Assistant
	migrationSvc := service.NewMigrationAssistantService(orch)

	// Initialize Style Adaptation
	styleSvc := service.NewStyleAdaptationService(orch)

	// Initialize Learning System
	learningSvc := service.NewLearningSystemService(orch, "")

	// Initialize Code Memory
	codeMemorySvc := service.NewCodeMemoryService(graphService, memoryBridge, orch, "")

	// Initialize Code Embeddings
	codeEmbedSvc := service.NewCodeEmbeddingsService(orch)

	// Initialize Project Understanding
	projectUnderSvc := service.NewProjectUnderstandingService(orch)

	// Initialize Conversational Orchestrator
	convOrch := service.NewConversationalOrchestrator(orch)

	// Initialize Planner
	plannerSvc := service.NewPlannerService(orch, toolService, genService)
	node.NewPlannerModule(swarmBus, plannerSvc).Start()

	// Register Native Tools
	toolService.RegisterTool(service.Tool{Name: "memory_search", ModuleName: "memory_bridge", Operation: "vector_search"})
	toolService.RegisterTool(service.Tool{Name: "web_fetch", ModuleName: "web_fetch_service", Operation: "fetch_url"})
	toolService.RegisterTool(service.Tool{Name: "graph_query", ModuleName: "neo4j_service", Operation: "execute_query"})
	toolService.RegisterTool(service.Tool{Name: "code_analyze", ModuleName: "code_service", Operation: "analyze_code"})

	// 10. Start API Gateway
	apiPort := 8089
	apiServer := api.NewServer(orch, agentService, monitor, goalService, profileService, subconsciousSvc, rulesEngine, skillManager, budgetManager, insightService, precogService, absorptionService, agentCoordinator, pipelineSvc, reasoningOrch, convOrch, knowledgeSvc, codeReviewSvc, projectUnderSvc, codeMetricsSvc, securitySvc, docGenSvc, semanticUnderSvc, thoughtToTextSvc, emotionSvc, refactoringSvc, searchSvc, explainSvc, migrationSvc, styleSvc, learningSvc, codeMemorySvc, codeEmbedSvc, metrics, traceStore, healthSvc, reasoningStratSvc, documentSvc, apiPort)
	go func() {
		if err := apiServer.Start(); err != nil {
			log.Fatalf("Failed to start API Gateway: %v", err)
		}
	}()
	log.Printf("API Gateway active on port %d", apiPort)

	// 11. Start Autonomic Daemon Fleet
	root := "/home/mike/Mavaia"
	jitDaemon := service.NewJITDaemon(root, orch)
	dreamDaemon := service.NewDreamDaemon(300, 60, graphService, orch)
	metacogDaemon := service.NewMetacogDaemon(root, orch)
	toolDaemon := service.NewToolDaemon(root)

	go jitDaemon.Run()
	go dreamDaemon.Run()
	go metacogDaemon.Run()
	go toolDaemon.Run()
	log.Println("[Main] Autonomic Daemon Fleet active (JIT, Dream, Metacog, Tool)")

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

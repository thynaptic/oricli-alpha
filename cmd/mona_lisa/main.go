package main

import (
	"fmt"
	"log"
	"os"
	"strings"
	"time"

	"github.com/thynaptic/oricli-go/pkg/bus"
	"github.com/thynaptic/oricli-go/pkg/node"
	"github.com/thynaptic/oricli-go/pkg/service"
	pb "github.com/thynaptic/oricli-go/pkg/rpc"
	"google.golang.org/grpc"
	"google.golang.org/grpc/credentials/insecure"
)

func main() {
	query := "What is sfumato? Check memory and web."
	if len(os.Args) > 1 {
		query = strings.Join(os.Args[1:], " ")
	}

	fmt.Println("================================================================================")
	fmt.Println("MAVAI COGNITIVE ENGINE - GO NATIVE BENCHMARK")
	fmt.Println("================================================================================")
	fmt.Printf("\nQuery: %s\n\n", query)

	// 1. Setup minimal backbone for the test
	swarmBus := bus.NewSwarmBus(1000)
	workerAddr := "localhost:50051"
	
	conn, err := grpc.NewClient(workerAddr, grpc.WithTransportCredentials(insecure.NewCredentials()))
	if err != nil {
		log.Fatalf("Failed to connect to Python worker: %v", err)
	}
	defer conn.Close()
	_ = pb.NewModuleServiceClient(conn) // Ensure client exists if needed later

	// 2. Initialize Core Services
	genService := service.NewGenerationService()
	personaPath := "oricli_core/brain/modules/personality_config.json"
	personaService, _ := service.NewPersonaService(personaPath)
	
	lmdbPath := "/home/mike/Mavaia/.oricli/memory.lmdb"
	encKey := os.Getenv("MAVAIA_MEMORY_ENCRYPTION_KEY")
	memoryBridge, _ := service.NewMemoryBridge(lmdbPath, encKey)
	
	webService := service.NewWebFetchService()
	
	// 3. Register Native Modules
	node.NewNativeGenerationModule(swarmBus, genService).Start()
	node.NewMemoryModule(swarmBus, memoryBridge).Start()
	node.NewWebModule(swarmBus, webService).Start()

	// 4. Start Orchestrator & Agent
	orch := service.NewGoOrchestrator(swarmBus)
	agent := service.NewGoAgentService(orch, genService, personaService)

	// 5. Run the Test
	start := time.Now()
	answer, err := agent.Run(query, nil)
	duration := time.Since(start)

	if err != nil {
		fmt.Printf("\n✗ Benchmark failed: %v\n", err)
		os.Exit(1)
	}

	fmt.Println("\n" + strings.Repeat("=", 80))
	fmt.Println("FINAL SYNTHESIZED ANSWER")
	fmt.Println(strings.Repeat("=", 80))
	fmt.Println(answer)

	fmt.Println("\n" + strings.Repeat("=", 80))
	fmt.Println("PERFORMANCE METRICS")
	fmt.Println(strings.Repeat("=", 80))
	fmt.Printf("Total Execution Time: %v\n", duration)
	fmt.Println("Reasoning Engine: Go-Native Conscious Loop")
	fmt.Println("Generation Model: qwen2:1.5b")
	fmt.Println("================================================================================")
}

package main

import (
	"context"
	"fmt"
	"log"
	"os"
	"time"

	"github.com/joho/godotenv"
	"github.com/thynaptic/oricli-go/pkg/service"
)

func main() {
	fmt.Println("--- Oricli-Alpha Ghost Cluster Demo ---")

	godotenv.Load("../../.env")
	godotenv.Load("../.env")
	godotenv.Load(".env")
	
	apiKey := os.Getenv("OricliAlpha_Key")
	if apiKey == "" {
		log.Println("Skipping actual RunPod API calls because OricliAlpha_Key is not set.")
		fmt.Println("Demo will simulate the orchestrator logic.")
		return
	}

	ghost := service.NewGhostClusterService(apiKey)
	
	ctx, cancel := context.WithTimeout(context.Background(), 2*time.Minute)
	defer cancel()

	fmt.Println("\n[Phase 1: Agent Requests Hardware]")
	fmt.Println("Agent: 'I need a 1x RTX A4000 to run a quick test.'")
	
	// We use A4000 as it's usually cheap and available
	gpuType := "NVIDIA RTX A4000"
	
	session, err := ghost.Provision(ctx, "alpha-test", gpuType, 1)
	if err != nil {
		log.Fatalf("Failed to provision ghost cluster: %v", err)
	}

	fmt.Printf("\n[Phase 2: Execution]\n")
	fmt.Printf("Cluster '%s' is online. Pod IDs: %v\n", gpuType, session.PodIDs)
	fmt.Println("Agent is now executing code on the remote hardware...")
	
	// Simulate work
	time.Sleep(5 * time.Second)
	
	fmt.Println("Agent: 'Execution complete. Results saved to Memory Graph.'")

	fmt.Printf("\n[Phase 3: Cleanup]\n")
	fmt.Println("Ghosting the cluster...")
	
	ghost.Vanish(session)
	
	fmt.Println("\n--- Ghost Cluster Demo Complete ---")
}

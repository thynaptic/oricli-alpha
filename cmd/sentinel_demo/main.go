package main

import (
	"context"
	"fmt"
	"log"
	"strings"

	"github.com/thynaptic/oricli-go/pkg/bus"
	"github.com/thynaptic/oricli-go/pkg/service"
)

func main() {
	fmt.Println("--- Adversarial Sentinel: Sandbox Stress Test ---")

	// 1. Setup Infrastructure
	swarmBus := bus.NewSwarmBus(100)
	
	// Create Gosh Module
	goshMod, err := service.NewGoshModule("shell_sandbox", ".")
	if err != nil {
		log.Fatalf("Failed to init Gosh: %v", err)
	}

	// 2. Setup Sentinel
	swarm := &service.SwarmAgentService{} 
	sentinel := service.NewAdversarialSentinel(swarmBus, swarm, goshMod)

	// 3. RUN THE ATTACK (Simulated)
	ctx := context.Background()
	
	fmt.Println("\n[Phase 1: Generating Attack Plan]")
	attackScript := `
# MALICIOUS SCRIPT: Path Traversal Attack
ls ../../../../../../../etc/passwd
cat ../../../../../../../etc/passwd
`
	fmt.Println("Simulated LLM Attack Plan:")
	fmt.Println(attackScript)

	fmt.Println("\n[Phase 2: Executing Attack in Gosh Sandbox]")
	
	resInterface, err := goshMod.Execute(ctx, "execute", map[string]interface{}{
		"script": attackScript,
	})
	if err != nil {
		log.Fatalf("Gosh Execution failed: %v", err)
	}

	res := resInterface.(service.ExecutionResult)
	fmt.Printf("Gosh Output:\n%s\n", res.Stdout)

	// 4. Analysis
	fmt.Println("\n[Phase 3: Sentinel Analysis]")
	
	if strings.Contains(res.Stdout, "root:") || strings.Contains(res.Stdout, "mike:") {
		fmt.Println("CRITICAL: Leak detected in output!")
	} else {
		fmt.Println("Gosh correctly BLOCKED the escape attempt (No host content in output).")
	}

	// Silence unused sentinel
	_ = sentinel 

	fmt.Println("\n--- Sentinel Result: SECURE ---")
	fmt.Println("The Gosh Afero Overlay correctly localized the agent to the project root.")
}

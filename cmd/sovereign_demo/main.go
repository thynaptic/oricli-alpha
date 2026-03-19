package main

import (
	"context"
	"fmt"

	"github.com/thynaptic/oricli-go/pkg/cognition"
)

func main() {
	fmt.Println("--- Oricli-Alpha Sovereign Cognition Demo ---")

	// 1. Initialize Sovereign Engine
	engine := cognition.NewSovereignEngine()
	ctx := context.Background()

	// 2. Scenario: Stimulus Modulation
	fmt.Println("\n[Scenario 1: Normal Thought Modulation]")
	fmt.Printf("Initial Linguistic Prior: %s\n", engine.GetLinguisticPriors())
	
	thought, _ := engine.ProcessInference(ctx, "I need to optimize the memory bridge.")
	fmt.Printf("Engine Result: %s\n", thought)

	// 3. Scenario: Cognitive Stress and Metacognitive Reset
	fmt.Println("\n[Scenario 2: Cognitive Stress (Panic Stimulus)]")
	fmt.Println("Stimulus: 'Kernel Syscall Failure - Immediate Attention Required'")
	
	// Triggers imbalance internally
	engine.ProcessInference(ctx, "panic")
	
	// The next inference will show the reset in logs and the result
	engine.ProcessInference(ctx, "Stability restored.")

	// 4. Scenario: Strategic Planning
	fmt.Println("\n[Scenario 3: Autonomous Strategic Planning]")
	plan := engine.GenerateStrategicPlan("Migrate Python legacy to Go-native Ring 0.")
	
	fmt.Printf("Plan ID: %s\n", plan.TaskID)
	for _, step := range plan.Steps {
		fmt.Printf("- [%s] %s (Bounty: %.2f tokens)\n", step.ID, step.Description, step.Bounty)
	}

	fmt.Println("\n--- Sovereign Cognition Demo Complete ---")
}

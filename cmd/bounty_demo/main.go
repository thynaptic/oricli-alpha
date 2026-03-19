package main

import (
	"fmt"
	"log"
	"time"

	"github.com/thynaptic/oricli-go/pkg/bus"
	"github.com/thynaptic/oricli-go/pkg/service"
)

func main() {
	fmt.Println("--- Oricli-Alpha Swarm Bounty System Demo ---")

	// 1. Setup Swarm Bus and Coordinator
	swarmBus := bus.NewSwarmBus(100)
	coordinator := service.NewAgentCoordinator(swarmBus)

	// 2. Define a High-Value Code Task
	task := service.AgentTask{
		ID:          "task_alpha",
		AgentType:   service.AgentSynthesis,
		Query:       "Optimize LMDB Write Batching",
		RequireGosh: true,
		Bounty:      500.0,
	}

	// 3. Start Task Execution in a goroutine so we can publish bids asynchronously
	fmt.Println("\n[Execution Started]")
	
	resultCh := make(chan service.AgentResult, 1)
	errCh := make(chan error, 1)

	go func() {
		res, err := coordinator.ExecuteTask(task, 5*time.Second)
		if err != nil {
			errCh <- err
			return
		}
		resultCh <- res
	}()

	// 4. Simulate Agents Bidding after the CFP is published
	time.Sleep(500 * time.Millisecond) // Wait for coordinator to publish CFP
	
	fmt.Println("[Agents detected CFP. Submitting Bids...]")
	
	// Rookie Agent: Low bid, No Gosh Trace
	swarmBus.Publish(bus.Message{
		Protocol: bus.BID,
		Topic:    "agent.bid.task_alpha",
		SenderID: "rookie_agent",
		Payload: map[string]interface{}{
			"confidence": 0.75,
			"token_bid":  10.0,
			"reason":      "I'll try my best.",
		},
	})

	// Veteran Agent: High bid, Gosh Trace included
	swarmBus.Publish(bus.Message{
		Protocol: bus.BID,
		Topic:    "agent.bid.task_alpha",
		SenderID: "veteran_agent",
		Payload: map[string]interface{}{
			"confidence": 0.95,
			"token_bid":  100.0,
			"gosh_trace": "GOSH_VERIFIED_TRACE_V1.0",
			"reason":      "I've pre-flighted this optimization in the sandbox.",
		},
	})

	// 5. Simulate Result reporting from the winner (Veteran)
	// We wait for the ACCEPT message to simulate realistic timing
	swarmBus.Subscribe("tasks.accept", func(msg bus.Message) {
		if msg.RecipientID == "veteran_agent" {
			fmt.Println("[Veteran Agent accepted task. Executing...]")
			time.Sleep(1 * time.Second)
			swarmBus.Publish(bus.Message{
				Protocol: bus.RESULT,
				Topic:    "agent.result.task_alpha",
				SenderID: "veteran_agent",
				Payload: map[string]interface{}{
					"result": "LMDB Batching Optimized by 45%.",
				},
			})
		}
	})

	// 6. Wait for completion
	select {
	case res := <-resultCh:
		fmt.Printf("\nRESULT: %v\n", res.Output)
		fmt.Println("\n--- Swarm Bounty System Demo Complete ---")
	case err := <-errCh:
		log.Fatalf("Task execution failed: %v", err)
	case <-time.After(10 * time.Second):
		log.Fatalf("Demo timed out.")
	}
}
